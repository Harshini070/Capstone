import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "external" / "bengaluru_complaints.csv"
OUTPUT = ROOT / "data" / "interim"

if not SOURCE.is_file():
    raise SystemExit(f"Source dataset not found: {SOURCE}")

OUTPUT.mkdir(parents=True, exist_ok=True)

def read_source(path):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValueError("Missing CSV header")
                rows = list(reader)
            return reader.fieldnames, rows, encoding
        except UnicodeDecodeError:
            continue
    raise SystemExit("Unable to decode source CSV")

fields, rows, encoding = read_source(SOURCE)

required = {
    "category_id", "category_title",
    "sub_category_id", "sub_category_title",
}
missing = required - set(fields)
if missing:
    raise SystemExit(f"Missing required columns: {sorted(missing)}")

def clean(value):
    return (value or "").strip()

category_counts = Counter(
    (clean(r["category_id"]), clean(r["category_title"]))
    for r in rows
)

subcategory_counts = Counter(
    (
        clean(r["category_id"]),
        clean(r["category_title"]),
        clean(r["sub_category_id"]),
        clean(r["sub_category_title"]),
    )
    for r in rows
)

category_path = OUTPUT / "source_category_inventory.csv"
with category_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "source_category_id",
        "source_category_title",
        "record_count",
        "target_category_id",
        "target_category_title",
        "mapping_status",
        "mapping_rationale",
    ])
    for (category_id, title), count in sorted(
        category_counts.items(), key=lambda item: (-item[1], item[0])
    ):
        writer.writerow([
            category_id, title, count, "", "", "PENDING", ""
        ])

subcategory_path = OUTPUT / "source_subcategory_inventory.csv"
with subcategory_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "source_category_id",
        "source_category_title",
        "source_subcategory_id",
        "source_subcategory_title",
        "record_count",
        "target_category_id",
        "target_category_title",
        "target_subcategory_id",
        "target_subcategory_title",
        "mapping_status",
        "mapping_rationale",
    ])
    for key, count in sorted(
        subcategory_counts.items(), key=lambda item: (-item[1], item[0])
    ):
        category_id, category_title, sub_id, sub_title = key
        writer.writerow([
            category_id, category_title, sub_id, sub_title, count,
            "", "", "", "", "PENDING", ""
        ])

print("=== TAXONOMY INVENTORY COMPLETE ===")
print(f"Source encoding: {encoding}")
print(f"Source records: {len(rows):,}")
print(f"Unique source categories: {len(category_counts):,}")
print(f"Unique category/subcategory combinations: {len(subcategory_counts):,}")
print(f"Category inventory: {category_path}")
print(f"Subcategory inventory: {subcategory_path}")
print("All target mappings are PENDING; no GHMC IDs were invented.")
