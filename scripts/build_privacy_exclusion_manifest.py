import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

QUEUE = ROOT / "data/interim/experimental_pii_review_queue.csv"
CORPUS = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"

OUTPUT = ROOT / "data/interim/experimental_privacy_exclusion_manifest.csv"
SUMMARY = ROOT / "reports/aggregate/experimental_privacy_audit_v1.json"

for path in (QUEUE, CORPUS):
    if not path.exists():
        raise FileNotFoundError(path)

if OUTPUT.exists() or SUMMARY.exists():
    raise FileExistsError("Refusing to overwrite existing privacy audit outputs.")

with QUEUE.open("r", encoding="utf-8-sig", newline="") as f:
    queue = list(csv.DictReader(f))

with CORPUS.open("r", encoding="utf-8-sig", newline="") as f:
    corpus = list(csv.DictReader(f))

candidate_ids = {
    row["record_id"]
    for row in corpus
    if row["experimental_candidate"] == "True"
}

manifest = []
for row in queue:
    if row["experimental_candidate"] == "True":
        manifest.append({
            "record_id": row["record_id"],
            "privacy_review_status": "PENDING_MANUAL_REVIEW",
            "privacy_hold": "TRUE",
            "matched_patterns": row["matched_patterns"],
            "matched_fields": row["matched_fields"],
            "training_eligibility": "EXCLUDE_PENDING_PRIVACY_REVIEW"
        })

manifest_ids = {row["record_id"] for row in manifest}

if not manifest_ids.issubset(candidate_ids):
    raise ValueError("Privacy manifest contains IDs outside candidate pool.")

remaining = len(candidate_ids) - len(manifest_ids)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
SUMMARY.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
    fields = [
        "record_id",
        "privacy_review_status",
        "privacy_hold",
        "matched_patterns",
        "matched_fields",
        "training_eligibility"
    ]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(manifest)

summary = {
    "audit_name": "GrievanceHub Experimental Corpus Privacy Audit",
    "version": "1.0",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "total_corpus_records": len(corpus),
    "initial_provisional_candidates": len(candidate_ids),
    "unique_privacy_flagged_candidates": len(manifest_ids),
    "temporarily_excluded_pending_review": len(manifest_ids),
    "remaining_unflagged_provisional_candidates": remaining,
    "privacy_clearance": "NOT_GRANTED",
    "policy": "Regex-flagged candidates are held pending manual privacy review. Matches are not confirmed personal information.",
    "source_corpus_modified": False
}

SUMMARY.write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("=== PRIVACY EXCLUSION MANIFEST ===")
print("Manifest records:", len(manifest))
print("Flagged candidate IDs:", len(manifest_ids))
print("Remaining unflagged candidates:", remaining)
print("Output:", OUTPUT.relative_to(ROOT))
print("Summary:", SUMMARY.relative_to(ROOT))
print("Original corpus modified: NO")
print("Privacy clearance: NOT GRANTED")
