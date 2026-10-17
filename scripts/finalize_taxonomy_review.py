import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "interim" / "category_mapping_review_v2.csv"
OUTPUT = ROOT / "data" / "interim" / "category_mapping_review_v3.csv"

# Explicit review overrides keyed by the full source label, not ID alone.
OVERRIDES = {
    "storm water drains": (
        "STORMWATER",
        "Stormwater and Flood Management",
        "Manual review: preserve stormwater distinction",
        "PENDING_HUMAN_REVIEW",
    ),
    "proibition & sale of tobacco products, plastic carry bags": (
        "REGULATORY_ENFORCEMENT",
        "Regulatory and Enforcement Services",
        "Mixed regulatory and plastic-restriction label; verify manually",
        "MANUAL_REVIEW_REQUIRED",
    ),
    "covid 19": (
        "PUBLIC_HEALTH",
        "Public Health",
        "Provisional classification; verify source meaning and project scope",
        "MANUAL_REVIEW_REQUIRED",
    ),
    "others": (
        "OTHER_REVIEW",
        "Other / Needs Review",
        "Catch-all source category; do not force into a specific service",
        "MANUAL_REVIEW_REQUIRED",
    ),
}

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing file: {SOURCE}")

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    fields = [
        "source_category_id",
        "source_category_title",
        "source_record_count",
        "proposed_target_category_code",
        "proposed_target_category",
        "proposal_basis",
        "mapping_status",
        "reviewer_notes",
    ]

    output_rows = []
    skipped = 0

    for row in rows:
        label = (row.get("source_category_title") or "").strip()

        # Exclude blank and placeholder inventory records.
        if label.casefold() in {"", "null", "none", "nan", "n/a"}:
            skipped += 1
            continue

        key = " ".join(label.casefold().split())

        if key in OVERRIDES:
            code, target, rationale, status = OVERRIDES[key]
            row["proposed_target_category_code"] = code
            row["proposed_target_category"] = target
            row["proposal_basis"] = rationale
            row["mapping_status"] = status
            row["reviewer_notes"] = rationale

        output_rows.append({field: row.get(field, "") for field in fields})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Created: {OUTPUT.relative_to(ROOT)}")
    print(f"Review rows retained: {len(output_rows)}")
    print(f"Blank/placeholder rows skipped: {skipped}")
    print("Mappings are proposals; review-required labels remain unapproved.")

if __name__ == "__main__":
    main()
