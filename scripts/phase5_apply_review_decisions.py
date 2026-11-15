"""S8 - Apply eligibility rules and write the reviewed dataset v3.

Input : cleaning-candidate dataset (15,374 records), S2 screens, S3 flags,
        review queue, review_final.csv (S7)
Output: data/processed/translated_bengaluru_reviewed_v3.csv  (record level, Git-ignored)
        reports/phase5_review/eligibility_summary.json        (aggregate)

Rules
-----
* Every input column is preserved unchanged; only new metadata columns are
  appended. The source_*, telugu_* and *_cleaned values are verified
  byte-identical to the input after writing.
* Exactly one eligibility state per record, assigned by
  phase5_review_common.assign_eligibility (privacy quarantine first).
* final_category = corrected_category for RELABEL decisions, otherwise the
  given category. The taxonomy and source-to-target mappings are untouched.
* Only AI_REVIEWED_ACCEPTED and AI_REVIEWED_RELABELLED are ml_eligible.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import pandas as pd

import phase5_review_common as common

DATASET_VERSION = "translated_bengaluru_reviewed_v3"
PROTECTED_PREFIXES = ("source_", "telugu_")
PROTECTED_SUFFIXES = ("_cleaned",)

SCREEN_COLUMNS = [
    "exact_dup_group", "dedup_group_id", "regex_pii_flag", "pii_types",
    "artifact_flags", "residual_dot_run", "empty_title", "empty_description",
    "title_description_identical", "low_telugu_ratio", "very_short_text",
    "number_mismatch_flag", "length_ratio_flag", "semantic_signal_status",
    "semantic_similarity", "category_flags", "screen_flag_count",
]
REVIEW_COLUMNS = [
    "review_method", "reviewer_model", "protocol_version", "review_timestamp",
    "final_review_pass", "consistency_status", "translation_fidelity",
    "telugu_grammar", "translation_completeness", "missing_information",
    "added_information", "category_correctness", "corrected_category",
    "secondary_category", "geography_assessment", "privacy_assessment",
    "review_decision", "error_type", "evidence_source", "evidence_telugu",
    "explanation",
]


def protected_columns(columns) -> list[str]:
    return [c for c in columns
            if c.startswith(PROTECTED_PREFIXES) or c.endswith(PROTECTED_SUFFIXES)]


def _bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes")


def build_v3(data: pd.DataFrame, screens: pd.DataFrame, flags: pd.DataFrame,
             queue: pd.DataFrame, final: pd.DataFrame) -> pd.DataFrame:
    if not data["record_id"].is_unique:
        raise AssertionError("record_id must be unique")
    if not final.empty and not final["record_id"].is_unique:
        raise AssertionError("review_final must have unique record_id values")
    unknown = set(final["record_id"]) - set(data["record_id"]) if not final.empty else set()
    if unknown:
        raise AssertionError(f"{len(unknown)} reviewed records are not in the dataset")

    v3 = data.copy()
    s = screens.set_index("record_id")
    for column in SCREEN_COLUMNS:
        v3[column] = v3["record_id"].map(s[column]) if column in s else ""
    f = flags.set_index("record_id")
    v3["label_noise_status"] = v3["record_id"].map(f["label_noise_status"])
    v3["label_noise_flagged"] = v3["record_id"].map(f["flagged"])
    q = queue.set_index("record_id") if not queue.empty else pd.DataFrame()
    for column in ("review_origin", "in_random_sample", "in_flagged_set", "also_flagged",
                   "review_inclusion_reason", "sampling_stratum", "inclusion_probability",
                   "sampling_weight"):
        v3[column] = v3["record_id"].map(q[column]) if column in q else ""
    v3["in_random_sample"] = v3["in_random_sample"].fillna(False)

    r = final.set_index("record_id") if not final.empty else pd.DataFrame(columns=REVIEW_COLUMNS)
    v3["reviewed"] = v3["record_id"].isin(r.index)
    for column in REVIEW_COLUMNS:
        v3[f"review_{column}" if not column.startswith("review_") else column] = (
            v3["record_id"].map(r[column]) if column in r else ""
        )
    v3 = v3.fillna("")

    states, reasons, finals, label_sources = [], [], [], []
    for rec in v3.to_dict("records"):
        given = rec["target_category_code"]
        decision = rec["review_decision"]
        corrected = str(rec["review_corrected_category"]).strip().upper()
        final_category = corrected if rec["reviewed"] and decision == "RELABEL" and corrected else given
        state, reason = common.assign_eligibility({
            "reviewed": rec["reviewed"],
            "final_category": final_category,
            "review_decision": decision,
            "privacy_assessment": rec["review_privacy_assessment"],
            "consistency_status": rec["review_consistency_status"],
            "translation_fidelity": rec["review_translation_fidelity"],
            "missing_information": rec["review_missing_information"],
            "added_information": rec["review_added_information"],
            "residual_dot_run": _bool(rec["residual_dot_run"]),
            "empty_title": _bool(rec["empty_title"]),
            "empty_description": _bool(rec["empty_description"]),
            "evidence_present": bool(rec["reviewed"])
            and bool(str(rec["review_evidence_source"]).strip())
            and bool(str(rec["review_evidence_telugu"]).strip()),
            "regex_pii_flag": _bool(rec["regex_pii_flag"]),
        })
        states.append(state)
        reasons.append(reason)
        finals.append(final_category)
        label_sources.append("AI_RELABEL" if final_category != given else "SOURCE_MAPPING")
    v3["final_category"] = finals
    v3["label_source"] = label_sources
    v3["eligibility_state"] = states
    v3["eligibility_reason"] = reasons
    v3["ml_eligible"] = v3["eligibility_state"].isin(common.ELIGIBLE_STATES)
    v3["dataset_version"] = DATASET_VERSION
    return v3


def verify_integrity(original: pd.DataFrame, written: pd.DataFrame) -> list[str]:
    """Protected text columns must be identical, value by value."""
    problems = []
    if list(original["record_id"]) != list(written["record_id"]):
        problems.append("record_id order or membership changed")
    for column in protected_columns(original.columns):
        if column not in written:
            problems.append(f"{column} missing from output")
        elif not original[column].equals(written[column]):
            problems.append(f"{column} values changed")
    return problems


def summarise(v3: pd.DataFrame) -> dict:
    eligible = v3[v3["ml_eligible"]]
    return {
        "stage": "S8_eligibility",
        "dataset_version": DATASET_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": int(len(v3)),
        "reviewed_records": int(v3["reviewed"].sum()),
        "eligibility_state_counts": v3["eligibility_state"].value_counts().to_dict(),
        "quarantine_reasons": v3.loc[v3.eligibility_state == common.STATE_QUARANTINED_PRIVACY,
                                     "eligibility_reason"].value_counts().to_dict(),
        "quality_blocked_reasons": v3.loc[v3.eligibility_state == common.STATE_QUALITY_BLOCKED,
                                          "eligibility_reason"].value_counts().to_dict(),
        "ml_eligible_records": int(len(eligible)),
        "ml_eligible_by_final_category": eligible["final_category"].value_counts().to_dict(),
        "ml_eligible_dedup_groups": int(eligible["dedup_group_id"].nunique()),
        "relabelled_records": int((v3["label_source"] == "AI_RELABEL").sum()),
        "notice": "AI-assisted review only (no human annotation). Translated experimental corpus derived from Bengaluru/BBMP data; not authentic Hyderabad/GHMC complaints.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    if common.DATASET_V3_PATH.exists() and not args.overwrite:
        raise SystemExit(f"{common.DATASET_V3_PATH} exists; pass --overwrite to rebuild it.")
    data = common.read_csv(common.CANDIDATE_PATH)
    v3 = build_v3(
        data,
        common.read_csv(common.SCREENS_PATH),
        common.read_csv(common.LABEL_NOISE_FLAGS_PATH),
        common.read_csv(common.REVIEW_QUEUE_PATH),
        common.read_csv(common.REVIEW_FINAL_PATH),
    )
    common.write_csv(v3, common.DATASET_V3_PATH)
    problems = verify_integrity(data, common.read_csv(common.DATASET_V3_PATH))
    if problems:
        raise AssertionError(f"Integrity check failed: {problems}")
    summary = summarise(v3)
    summary["integrity_check"] = "PASSED: source_*, telugu_* and *_cleaned values identical to input"
    common.write_json(summary, common.REPORT_DIR / "eligibility_summary.json")
    print(summary["eligibility_state_counts"])


if __name__ == "__main__":
    sys.exit(main())
