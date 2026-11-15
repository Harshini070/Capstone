"""S4-S6 - Resumable AI review batches.

Subcommands
-----------
build-queue  Merge the S1 random sample and S3 (then S2) flags into one
             review queue keyed by record_id. A sample record that is also
             flagged appears once, keeps review_origin=STRATIFIED_SAMPLE and
             its sampling weight, and gets also_flagged=True. Flagged-only
             records carry no sampling weight.
export       Write the next batch input file for a pass (1, 2 or
             ADJUDICATION). Pass-1 batches follow review priority; pass-2
             batches follow a seeded shuffle of all pass-1 records and never
             contain pass-1 answers. Model suggestions from S3 are never shown
             to the reviewer (to avoid anchoring).
validate     Validate a reviewer's output file for a batch against the schema
             and the batch input (same records, verbatim evidence, enums...).
             A validated batch is frozen: changing its output afterwards is
             an error.
merge        Combine all validated batches of a pass into review_pass<N>.csv.
status       Show completed batches and pending records for each pass.

Batch files live in data/interim/review/batches/<pass>/ (Git-ignored):
  <BATCH>_input.csv      records to review (identity + source + Telugu text)
  <BATCH>_output.json    reviewer output: JSON list, one object per record
  <BATCH>_manifest.json  batch metadata, hashes and validation status
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import phase5_review_common as common

PASS_PREFIX = {"1": "P1", "2": "P2", "ADJUDICATION": "ADJ"}

INPUT_COLUMNS = [
    "batch_id", "review_pass", "record_id", "given_category",
    "source_category_title", "source_title", "source_description",
    "telugu_title_cleaned", "telugu_description_cleaned",
]
ADJUDICATION_EXTRA = ["pass1_decision_summary", "pass2_decision_summary", "differing_fields"]
ADJUDICATION_QUEUE_PATH = common.REVIEW_DIR / "adjudication_queue.csv"


def pass_dir(review_pass: str) -> Path:
    return common.BATCH_DIR / f"pass{review_pass.lower()}"


def manifests(review_pass: str) -> list[dict]:
    folder = pass_dir(review_pass)
    if not folder.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(folder.glob("*_manifest.json"))]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


def build_queue(sample: pd.DataFrame, flags: pd.DataFrame, screens: pd.DataFrame,
                max_flagged: int = 1500) -> pd.DataFrame:
    """Combine sample and flagged records; one row per record_id."""
    sample = sample.copy()
    if not sample["record_id"].is_unique:
        raise AssertionError("Duplicate record_id in the sample.")
    s3 = flags[(flags["label_noise_status"] == "EVALUATED") & (flags["flagged"].astype(str) == "True")].copy()
    s3["flag_rank"] = pd.to_numeric(s3["flag_rank"])
    s3 = s3.sort_values("flag_rank", kind="stable")
    s3_ids = set(s3["record_id"])

    s2 = screens[screens["category_flags"].str.contains("both_signals_disagree_with_given_label", na=False)]
    s2 = s2[~s2["record_id"].isin(s3_ids)]

    sample_ids = set(sample["record_id"])
    rows = []
    for rec in sample.sort_values("sample_order", key=lambda s: s.astype(int)).to_dict("records"):
        also = rec["record_id"] in s3_ids
        rows.append({
            "record_id": rec["record_id"],
            "review_origin": common.ORIGIN_SAMPLE,
            "in_random_sample": True,
            "in_flagged_set": also,
            "also_flagged": also,
            "review_inclusion_reason": "SAMPLE_AND_FLAG" if also else "RANDOM_SAMPLE",
            "sampling_stratum": rec["sampling_stratum"],
            "stratum_population": rec["stratum_population"],
            "stratum_sample_size": rec["stratum_sample_size"],
            "inclusion_probability": rec["inclusion_probability"],
            "sampling_weight": rec["sampling_weight"],
        })
    added = 0
    flagged_only = [("S3_LABEL_NOISE_FLAG", r) for r in s3.to_dict("records")] + [
        ("S2_CATEGORY_SIGNAL_CONFLICT", r) for r in s2.to_dict("records")
    ]
    for reason, rec in flagged_only:
        if added >= max_flagged:
            break
        if rec["record_id"] in sample_ids:
            continue
        rows.append({
            "record_id": rec["record_id"],
            "review_origin": common.ORIGIN_FLAG,
            "in_random_sample": False,
            "in_flagged_set": True,
            "also_flagged": False,
            "review_inclusion_reason": reason,
            "sampling_stratum": "", "stratum_population": "",
            "stratum_sample_size": "", "inclusion_probability": "",
            "sampling_weight": "",
        })
        added += 1
    queue = pd.DataFrame(rows)
    queue["review_priority"] = np.arange(1, len(queue) + 1)
    if not queue["record_id"].is_unique:
        raise AssertionError("Queue contains duplicate record_id values.")
    return queue


def cmd_build_queue(args):
    if common.REVIEW_QUEUE_PATH.exists() and manifests("1") and not args.overwrite:
        raise SystemExit("Pass-1 batches already exist; refusing to rebuild the queue.")
    queue = build_queue(
        common.read_csv(common.SAMPLE_V2_PATH),
        common.read_csv(common.LABEL_NOISE_FLAGS_PATH),
        common.read_csv(common.SCREENS_PATH),
        max_flagged=args.max_flagged,
    )
    common.write_csv(queue, common.REVIEW_QUEUE_PATH)
    counts = queue["review_inclusion_reason"].value_counts().to_dict()
    common.write_json({
        "stage": "review_queue",
        "generated_at_utc": _now(),
        "records": int(len(queue)),
        "by_inclusion_reason": counts,
        "max_flagged": args.max_flagged,
        "note": "Flagged records are a non-random selection and never contribute to population estimates.",
    }, common.REPORT_DIR / "review_queue_summary.json")
    print(f"Queue: {len(queue)} records {counts}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _record_lookup() -> pd.DataFrame:
    data = common.read_csv(common.CANDIDATE_PATH)
    return data.rename(columns={"target_category_code": "given_category"}).set_index("record_id")


def pass2_order(record_ids: list[str], seed: int = common.RANDOM_SEED) -> list[str]:
    """Seeded shuffle, independent of pass-1 batch order."""
    ordered = sorted(record_ids)
    rng = np.random.default_rng(seed + 2)
    return [ordered[i] for i in rng.permutation(len(ordered))]


def next_batch_ids(review_pass: str, size: int) -> list[str]:
    done = {rid for m in manifests(review_pass) for rid in m["record_ids"]}
    if review_pass == "1":
        queue = common.read_csv(common.REVIEW_QUEUE_PATH)
        queue = queue.sort_values("review_priority", key=lambda s: s.astype(int))
        candidates = queue["record_id"].tolist()
    elif review_pass == "2":
        pass1 = common.review_pass_path("1")
        if not pass1.exists():
            raise SystemExit("Merge pass 1 before exporting pass-2 batches.")
        candidates = pass2_order(common.read_csv(pass1)["record_id"].tolist())
    else:
        if not ADJUDICATION_QUEUE_PATH.exists():
            raise SystemExit("Run phase5_review_consistency.py compare first.")
        candidates = common.read_csv(ADJUDICATION_QUEUE_PATH)["record_id"].tolist()
    return [rid for rid in candidates if rid not in done][:size]


def export_batch(review_pass: str, size: int) -> Path | None:
    ids = next_batch_ids(review_pass, size)
    if not ids:
        print(f"No pending records for pass {review_pass}.")
        return None
    number = len(manifests(review_pass)) + 1
    batch_id = f"{PASS_PREFIX[review_pass]}-B{number:04d}"
    lookup = _record_lookup()
    frame = lookup.loc[ids].reset_index()
    frame["batch_id"] = batch_id
    frame["review_pass"] = review_pass
    columns = list(INPUT_COLUMNS)
    if review_pass == "ADJUDICATION":
        adj = common.read_csv(ADJUDICATION_QUEUE_PATH).set_index("record_id")
        for column in ADJUDICATION_EXTRA:
            frame[column] = adj.loc[ids, column].values
        columns += ADJUDICATION_EXTRA
    folder = pass_dir(review_pass)
    folder.mkdir(parents=True, exist_ok=True)
    input_path = folder / f"{batch_id}_input.csv"
    if input_path.exists():
        raise FileExistsError(f"{input_path} already exists.")
    common.write_csv(frame[columns], input_path)
    manifest = {
        "batch_id": batch_id,
        "review_pass": review_pass,
        "protocol_version": common.PROTOCOL_VERSION,
        "created_at_utc": _now(),
        "record_ids": ids,
        "input_sha256": common.file_sha256(input_path),
        "status": "EXPORTED",
        "output_sha256": None,
        "validated_at_utc": None,
    }
    common.write_json(manifest, folder / f"{batch_id}_manifest.json")
    print(f"Exported {batch_id}: {len(ids)} records -> {input_path}")
    return input_path


# ---------------------------------------------------------------------------
# Validate and merge
# ---------------------------------------------------------------------------


def load_output(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Batch output must be a JSON list of review objects.")
    return data


def validate_batch_rows(rows: list[dict], batch_input: pd.DataFrame, batch_id: str,
                        review_pass: str, assignable: frozenset) -> list[str]:
    errors = []
    expected = list(batch_input["record_id"])
    got = [str(r.get("record_id", "")) for r in rows]
    if len(got) != len(set(got)):
        errors.append("duplicate record_id in output")
    missing = set(expected) - set(got)
    extra = set(got) - set(expected)
    if missing:
        errors.append(f"missing records: {sorted(missing)}")
    if extra:
        errors.append(f"records not in this batch: {sorted(extra)}")
    by_id = batch_input.set_index("record_id")
    for row in rows:
        rid = str(row.get("record_id", ""))
        if rid not in by_id.index:
            continue
        if row.get("batch_id") != batch_id:
            errors.append(f"{rid}: batch_id must be {batch_id}")
        if str(row.get("review_pass")) != review_pass:
            errors.append(f"{rid}: review_pass must be {review_pass}")
        rec = by_id.loc[rid]
        errors.extend(common.validate_review_record(
            {k: ("" if v is None else v) for k, v in row.items()},
            rec["given_category"], assignable,
            source_text=f"{rec['source_title']} {rec['source_description']}",
            telugu_text=f"{rec['telugu_title_cleaned']} {rec['telugu_description_cleaned']}",
        ))
    return errors


def validate_batch(review_pass: str, batch_id: str) -> list[str]:
    folder = pass_dir(review_pass)
    manifest_path = folder / f"{batch_id}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_path = folder / f"{batch_id}_output.json"
    if not output_path.exists():
        return [f"{output_path} not found"]
    output_hash = common.file_sha256(output_path)
    if manifest["status"] == "VALIDATED":
        if manifest["output_sha256"] != output_hash:
            return [f"{batch_id} was already validated and its output has changed; completed batches are frozen."]
        return []
    if common.file_sha256(folder / f"{batch_id}_input.csv") != manifest["input_sha256"]:
        return [f"{batch_id} input file changed after export."]
    batch_input = common.read_csv(folder / f"{batch_id}_input.csv")
    errors = validate_batch_rows(load_output(output_path), batch_input, batch_id,
                                 review_pass, common.load_assignable_codes())
    if not errors:
        manifest.update(status="VALIDATED", output_sha256=output_hash, validated_at_utc=_now())
        common.write_json(manifest, manifest_path)
    return errors


def merge_pass(review_pass: str) -> Path:
    frames, seen = [], {}
    for manifest in manifests(review_pass):
        if manifest["status"] != "VALIDATED":
            continue
        output_path = pass_dir(review_pass) / f"{manifest['batch_id']}_output.json"
        if common.file_sha256(output_path) != manifest["output_sha256"]:
            raise AssertionError(f"{manifest['batch_id']} output changed after validation.")
        rows = load_output(output_path)
        for row in rows:
            rid = row["record_id"]
            if rid in seen:
                raise AssertionError(f"{rid} appears in {seen[rid]} and {manifest['batch_id']}")
            seen[rid] = manifest["batch_id"]
        frame = pd.DataFrame(rows)
        frame["pii_spans"] = frame["pii_spans"].apply(
            lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, list) else (v or "[]"))
        frames.append(frame[list(common.REVIEW_FIELDS)])
    if not frames:
        raise SystemExit(f"No validated batches for pass {review_pass}.")
    merged = pd.concat(frames, ignore_index=True)
    path = (common.REVIEW_DIR / "review_adjudication.csv" if review_pass == "ADJUDICATION"
            else common.review_pass_path(review_pass))
    common.write_csv(merged, path)
    print(f"Merged {len(merged)} reviews from {len(frames)} batches -> {path}")
    return path


# ---------------------------------------------------------------------------
# Compile a reviewer-authored decision file into the JSON output schema
# ---------------------------------------------------------------------------
# The reviewer writes one line per record in <BATCH>_review.psv (pipe-
# separated, header line first) using the short codes below. Every judgement
# field is written explicitly for every record; there are no defaults.
# compile only expands the codes and fills the identity fields
# (batch_id, review_pass, review_method, reviewer_model, protocol_version,
# review_timestamp). The .psv file is kept as the authored record.

PSV_COLUMNS = ["record_id", "fid", "gram", "comp", "miss", "add", "cat", "corr",
               "sec", "geo", "priv", "dec", "err", "ev_src", "ev_tel", "expl", "pii"]
CODES = {
    "fid": ("translation_fidelity", {"P": "PASS", "PA": "PARTIAL", "F": "FAIL", "U": "UNCERTAIN"}),
    "gram": ("telugu_grammar", {"G": "GOOD", "MI": "MINOR_ISSUES", "MA": "MAJOR_ISSUES", "U": "UNCERTAIN"}),
    "comp": ("translation_completeness", {"C": "COMPLETE", "P": "PARTIAL", "I": "INCOMPLETE", "U": "UNCERTAIN"}),
    "miss": ("missing_information", {"N": "NONE", "MI": "MINOR", "MA": "MAJOR"}),
    "add": ("added_information", {"N": "NONE", "MI": "MINOR", "MA": "MAJOR"}),
    "cat": ("category_correctness", {"C": "CORRECT", "I": "INCORRECT", "A": "AMBIGUOUS", "U": "UNCERTAIN"}),
    "geo": ("geography_assessment", {"V": "SOURCE_REFERENCE_VALID", "R": "REQUIRES_CONTEXTUAL_REVIEW",
                                     "X": "INCORRECT_OR_MISTRANSLATED", "N": "NO_GEOGRAPHY_REFERENCE"}),
    "priv": ("privacy_assessment", {"N": "NO_OBVIOUS_PII", "P": "POTENTIAL_PII", "I": "PII_IDENTIFIED",
                                    "U": "UNCERTAIN"}),
    "dec": ("review_decision", {"A": "ACCEPT", "AM": "ACCEPT_WITH_MINOR_ISSUES", "RL": "RELABEL",
                                "AMB": "AMBIGUOUS", "REJ": "REJECT", "E": "ESCALATE"}),
    "err": ("error_type", {"N": "NONE", "SLN": "SOURCE_LABEL_NOISE", "CME": "CATEGORY_MAPPING_ERROR",
                           "TMS": "TRANSLATION_MEANING_SHIFT", "TA": "TRANSLATION_ARTIFACT",
                           "IC": "INSUFFICIENT_CONTEXT", "MULTI": "MULTI_ISSUE", "OOS": "OUT_OF_SCOPE",
                           "PII": "PII"}),
}


def parse_pii_cell(cell: str) -> list[dict]:
    """'TYPE~field~text;;TYPE~field~text' -> [{type, field, text}]."""
    spans = []
    for part in [p for p in cell.split(";;") if p.strip()]:
        pieces = part.split("~", 2)
        if len(pieces) != 3:
            raise ValueError(f"bad pii span {part!r}; expected TYPE~field~text")
        spans.append({"type": pieces[0].strip(), "field": pieces[1].strip(), "text": pieces[2].strip()})
    return spans


def compile_psv(text: str, batch_id: str, review_pass: str, reviewer_model: str,
                timestamp: str) -> list[dict]:
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    header = [h.strip() for h in lines[0].split("|")]
    if header != PSV_COLUMNS:
        raise ValueError(f"header must be {'|'.join(PSV_COLUMNS)}")
    rows = []
    for number, line in enumerate(lines[1:], start=2):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) != len(PSV_COLUMNS):
            raise ValueError(f"line {number}: expected {len(PSV_COLUMNS)} fields, got {len(cells)}")
        raw = dict(zip(PSV_COLUMNS, cells))
        row = {
            "record_id": raw["record_id"], "batch_id": batch_id, "review_pass": review_pass,
            "review_method": common.REVIEW_METHOD, "reviewer_model": reviewer_model,
            "protocol_version": common.PROTOCOL_VERSION, "review_timestamp": timestamp,
        }
        for short, (field, mapping) in CODES.items():
            if raw[short] not in mapping:
                raise ValueError(f"line {number}: {short}={raw[short]!r} not in {sorted(mapping)}")
            row[field] = mapping[raw[short]]
        row["corrected_category"] = raw["corr"].upper()
        row["secondary_category"] = raw["sec"].upper()
        row["evidence_source"] = raw["ev_src"]
        row["evidence_telugu"] = raw["ev_tel"]
        row["explanation"] = raw["expl"]
        row["pii_spans"] = parse_pii_cell(raw["pii"])
        rows.append(row)
    return rows


def cmd_compile(review_pass: str, batch_id: str, reviewer_model: str) -> Path:
    folder = pass_dir(review_pass)
    manifest = json.loads((folder / f"{batch_id}_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] == "VALIDATED":
        raise SystemExit(f"{batch_id} is already validated and frozen.")
    psv = folder / f"{batch_id}_review.psv"
    rows = compile_psv(psv.read_text(encoding="utf-8"), batch_id, review_pass, reviewer_model, _now())
    output = folder / f"{batch_id}_output.json"
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Compiled {len(rows)} reviews -> {output}")
    return output


def status() -> dict:
    report = {}
    for review_pass in common.REVIEW_PASSES:
        ms = manifests(review_pass)
        validated = [m for m in ms if m["status"] == "VALIDATED"]
        report[review_pass] = {
            "batches_exported": len(ms),
            "batches_validated": len(validated),
            "records_validated": sum(len(m["record_ids"]) for m in validated),
            "records_exported_not_validated": sum(len(m["record_ids"]) for m in ms if m["status"] != "VALIDATED"),
            "last_validated_batch": validated[-1]["batch_id"] if validated else None,
        }
    if common.REVIEW_QUEUE_PATH.exists():
        total = len(common.read_csv(common.REVIEW_QUEUE_PATH))
        report["1"]["queue_records"] = total
        report["1"]["records_not_yet_exported"] = total - sum(len(m["record_ids"]) for m in manifests("1"))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("build-queue")
    q.add_argument("--max-flagged", type=int, default=1500)
    q.add_argument("--overwrite", action="store_true")
    e = sub.add_parser("export")
    e.add_argument("--pass", dest="review_pass", choices=common.REVIEW_PASSES, required=True)
    e.add_argument("--size", type=int, default=25)
    v = sub.add_parser("validate")
    v.add_argument("--pass", dest="review_pass", choices=common.REVIEW_PASSES, required=True)
    v.add_argument("--batch-id", required=True)
    c = sub.add_parser("compile")
    c.add_argument("--pass", dest="review_pass", choices=common.REVIEW_PASSES, required=True)
    c.add_argument("--batch-id", required=True)
    c.add_argument("--reviewer-model", default=common.DEFAULT_REVIEWER_MODEL)
    m = sub.add_parser("merge")
    m.add_argument("--pass", dest="review_pass", choices=common.REVIEW_PASSES, required=True)
    sub.add_parser("status")
    args = parser.parse_args(argv)

    if args.command == "build-queue":
        cmd_build_queue(args)
    elif args.command == "export":
        export_batch(args.review_pass, args.size)
    elif args.command == "validate":
        errors = validate_batch(args.review_pass, args.batch_id)
        if errors:
            print(f"{args.batch_id}: {len(errors)} problem(s)")
            for error in errors[:50]:
                print("  -", error)
            return 1
        print(f"{args.batch_id}: VALIDATED")
    elif args.command == "compile":
        cmd_compile(args.review_pass, args.batch_id, args.reviewer_model)
    elif args.command == "merge":
        merge_pass(args.review_pass)
    elif args.command == "status":
        print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
