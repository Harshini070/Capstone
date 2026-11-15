"""S7 - AI self-consistency comparison, adjudication and final review table.

Subcommands
-----------
compare    Compare pass 1 and pass 2 on the decision fields. Records that
           differ on any decision field get consistency_status =
           AI_DISAGREEMENT and are written to the adjudication queue.
finalize   Build review_final.csv:
             * CONSISTENT               -> pass-1 values
             * adjudicated disagreement -> adjudication values,
               RESOLVED_BY_ADJUDICATION (or UNRESOLVED_ESCALATED if the
               adjudication itself is ESCALATE)
             * disagreement, no adjudication -> UNRESOLVED, decision ESCALATE
           Then calibrates the optional LaBSE threshold on the sample.

Two passes from the same model measure *self-consistency only*. Agreement
is not inter-annotator reliability and not ground truth. Agreement is never
forced: an unresolved record is ESCALATE and excluded from the primary
ML dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import phase5_review_common as common

ADJUDICATION_QUEUE_PATH = common.REVIEW_DIR / "adjudication_queue.csv"
ADJUDICATION_PATH = common.REVIEW_DIR / "review_adjudication.csv"


def _norm(value) -> str:
    return str(value if value is not None else "").strip().upper()


def compare_passes(pass1: pd.DataFrame, pass2: pd.DataFrame) -> pd.DataFrame:
    """Return one row per record with consistency_status and differing fields."""
    if not pass1["record_id"].is_unique or not pass2["record_id"].is_unique:
        raise AssertionError("Each pass must have unique record_id values.")
    missing = set(pass1["record_id"]) - set(pass2["record_id"])
    if missing:
        raise AssertionError(f"{len(missing)} pass-1 records lack a pass-2 review.")
    merged = pass1.merge(pass2, on="record_id", suffixes=("_p1", "_p2"), validate="one_to_one")
    rows = []
    for rec in merged.to_dict("records"):
        differing = [f for f in common.DECISION_FIELDS
                     if _norm(rec[f"{f}_p1"]) != _norm(rec[f"{f}_p2"])]
        rows.append({
            "record_id": rec["record_id"],
            "consistency_status": "AI_DISAGREEMENT" if differing else "CONSISTENT",
            "differing_fields": ";".join(differing),
            "pass1_decision_summary": _summary(rec, "_p1"),
            "pass2_decision_summary": _summary(rec, "_p2"),
            "reviewer_model_p1": rec["reviewer_model_p1"],
            "reviewer_model_p2": rec["reviewer_model_p2"],
            **{f"{f}_p1": rec[f"{f}_p1"] for f in common.DECISION_FIELDS},
            **{f"{f}_p2": rec[f"{f}_p2"] for f in common.DECISION_FIELDS},
        })
    return pd.DataFrame(rows)


def _summary(rec: dict, suffix: str) -> str:
    return "; ".join(f"{f}={rec[f + suffix]}" for f in common.DECISION_FIELDS)


def agreement_report(comparison: pd.DataFrame, given: pd.Series) -> dict:
    """Per-field and per-class agreement. given: record_id -> given category."""
    report = {"records_compared": int(len(comparison)), "per_field_agreement": {}}
    for field in common.DECISION_FIELDS:
        same = (comparison[f"{field}_p1"].map(_norm) == comparison[f"{field}_p2"].map(_norm))
        report["per_field_agreement"][field] = round(float(same.mean()), 4) if len(same) else None
    consistent = comparison["consistency_status"].eq("CONSISTENT")
    report["all_decision_fields_agree"] = round(float(consistent.mean()), 4) if len(consistent) else None
    report["disagreements"] = int((~consistent).sum())
    by_class = comparison.assign(given=comparison["record_id"].map(given)).groupby("given")
    report["per_class_all_fields_agreement"] = {
        cls: {"n": int(len(g)), "agreement": round(float(g["consistency_status"].eq("CONSISTENT").mean()), 4)}
        for cls, g in by_class
    }
    report["reviewer_models"] = {
        "pass1": sorted(comparison["reviewer_model_p1"].unique().tolist()),
        "pass2": sorted(comparison["reviewer_model_p2"].unique().tolist()),
    }
    report["interpretation"] = (
        "AI self-consistency only. Both passes may share the same model and "
        "its biases; agreement is not inter-annotator reliability or ground truth."
    )
    return report


def finalize(pass1: pd.DataFrame, comparison: pd.DataFrame,
             adjudication: pd.DataFrame | None) -> pd.DataFrame:
    p1 = pass1.set_index("record_id")
    status = comparison.set_index("record_id")["consistency_status"]
    adj = adjudication.set_index("record_id") if adjudication is not None and len(adjudication) else None
    rows = []
    for rid in p1.index:
        if status[rid] == "CONSISTENT":
            row = p1.loc[rid].to_dict()
            row.update(consistency_status="CONSISTENT", final_review_pass="1")
        elif adj is not None and rid in adj.index:
            row = adj.loc[rid].to_dict()
            escalated = row["review_decision"] == "ESCALATE"
            row.update(
                consistency_status="UNRESOLVED_ESCALATED" if escalated else "RESOLVED_BY_ADJUDICATION",
                final_review_pass="ADJUDICATION",
            )
        else:
            row = p1.loc[rid].to_dict()
            row.update(
                consistency_status="UNRESOLVED",
                final_review_pass="NONE",
                review_decision="ESCALATE",
                explanation="Unresolved AI disagreement between pass 1 and pass 2; no adjudication recorded.",
            )
        row["record_id"] = rid
        rows.append(row)
    return pd.DataFrame(rows)


def calibrate_semantic_threshold(scores, fidelity, target_recall: float = 0.90,
                                 positive=("FAIL",)) -> dict:
    """Calibrate the LaBSE flag threshold against AI fidelity labels.

    Positive = translation_fidelity in `positive`. Returns the lowest
    threshold whose recall of positives is >= target_recall (flag when
    similarity <= threshold; lowest = fewest records flagged), plus AUC. If AUC < 0.7 the signal is weak and
    must not feed eligibility. Reference labels are AI decisions, so this
    measures agreement with the AI review, not true meaning preservation.
    """
    scores = pd.to_numeric(pd.Series(scores), errors="coerce")
    labels = pd.Series(fidelity).isin(positive)
    valid = scores.notna() & pd.Series(fidelity).isin(common.ENUMS["translation_fidelity"]) \
        & ~pd.Series(fidelity).eq("UNCERTAIN")
    scores, labels = scores[valid].to_numpy(), labels[valid].to_numpy()
    if len(scores) == 0:
        return {"status": "NOT_EVALUATED", "reason": "no semantic similarity scores available"}
    if labels.sum() == 0 or labels.sum() == len(labels):
        return {"status": "NOT_EVALUATED", "reason": "reviewed sample has only one fidelity class"}
    from sklearn.metrics import roc_auc_score
    auc = float(roc_auc_score(labels, -scores))  # low similarity => positive
    best = None
    for threshold in np.unique(scores):
        recall = float((scores[labels] <= threshold).mean())
        if recall >= target_recall:
            precision = float(labels[scores <= threshold].mean())
            best = {"threshold": float(threshold), "recall": round(recall, 4),
                    "precision": round(precision, 4)}
            break
    return {
        "status": "EVALUATED",
        "positive_definition": list(positive),
        "n": int(len(scores)), "n_positive": int(labels.sum()),
        "auc": round(auc, 4),
        "target_recall": target_recall,
        "selected": best,
        "weak_signal": auc < 0.7,
        "use_in_eligibility": False if auc < 0.7 else "review priority only unless separately approved",
        "limitation": "Reference labels are AI review decisions; this is agreement with the AI review, not proof of meaning preservation.",
    }


def cmd_compare(_args):
    pass1 = common.read_csv(common.review_pass_path("1"))
    pass2 = common.read_csv(common.review_pass_path("2"))
    comparison = compare_passes(pass1, pass2)
    common.write_csv(comparison, common.REVIEW_DIR / "consistency_comparison.csv")
    queue = comparison[comparison["consistency_status"] == "AI_DISAGREEMENT"]
    common.write_csv(queue[["record_id", "pass1_decision_summary", "pass2_decision_summary",
                            "differing_fields"]], ADJUDICATION_QUEUE_PATH)
    print(f"Compared {len(comparison)}; disagreements: {len(queue)}")


def cmd_finalize(_args):
    pass1 = common.read_csv(common.review_pass_path("1"))
    comparison = common.read_csv(common.REVIEW_DIR / "consistency_comparison.csv")
    adjudication = common.read_csv(ADJUDICATION_PATH) if ADJUDICATION_PATH.exists() else None
    final = finalize(pass1, comparison, adjudication)
    common.write_csv(final, common.REVIEW_FINAL_PATH)

    data = common.read_csv(common.CANDIDATE_PATH).set_index("record_id")
    report = agreement_report(comparison, data["target_category_code"])
    report.update({
        "stage": "S7_consistency",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_status_counts": final["consistency_status"].value_counts().to_dict(),
        "resolved_by_adjudication": int(final["consistency_status"].eq("RESOLVED_BY_ADJUDICATION").sum()),
        "unresolved": int(final["consistency_status"].isin(["UNRESOLVED", "UNRESOLVED_ESCALATED"]).sum()),
    })
    common.write_json(report, common.REPORT_DIR / "consistency_report.json")

    screens = common.read_csv(common.SCREENS_PATH).set_index("record_id")
    sample_ids = common.read_csv(common.SAMPLE_V2_PATH)["record_id"]
    sample_final = final.set_index("record_id").loc[sample_ids]
    calibration = calibrate_semantic_threshold(
        screens.loc[sample_ids, "semantic_similarity"].values,
        sample_final["translation_fidelity"].values,
    )
    common.write_json(calibration, common.REPORT_DIR / "semantic_threshold_calibration.json")
    print(json.dumps(report["final_status_counts"]), "| semantic:", calibration["status"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("compare")
    sub.add_parser("finalize")
    args = parser.parse_args(argv)
    {"compare": cmd_compare, "finalize": cmd_finalize}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
