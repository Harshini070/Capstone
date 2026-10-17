import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data" / "external" / "bengaluru_complaints.csv"

if not DATA_FILE.is_file():
    raise SystemExit(
        f"Dataset not found: {DATA_FILE}\n"
        "Copy the original Bengaluru CSV into data/external/ first."
    )

ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
selected_encoding = None
rows = []
fieldnames = []

for encoding in ENCODINGS:
    try:
        with DATA_FILE.open("r", encoding=encoding, newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise ValueError("CSV has no header.")
            fieldnames = reader.fieldnames
            rows = list(reader)
        selected_encoding = encoding
        break
    except UnicodeDecodeError:
        continue

if selected_encoding is None:
    raise SystemExit("Could not decode CSV using the tested encodings.")

def normalize(value):
    return (value or "").strip()

print("\n=== SOURCE DATASET INSPECTION ===")
print(f"File: {DATA_FILE.name}")
print(f"File size: {DATA_FILE.stat().st_size:,} bytes")
print(f"Encoding: {selected_encoding}")
print(f"Rows: {len(rows):,}")
print(f"Columns: {len(fieldnames)}")

print("\n=== COLUMN NAMES ===")
for index, name in enumerate(fieldnames, start=1):
    print(f"{index:02d}. {name}")

print("\n=== MISSING VALUES BY COLUMN ===")
for column in fieldnames:
    missing = sum(not normalize(row.get(column)) for row in rows)
    percentage = (100 * missing / len(rows)) if rows else 0
    print(f"{column}: {missing:,} ({percentage:.2f}%)")

print("\n=== POTENTIAL TEXT AND CATEGORY COLUMNS ===")
for column in fieldnames:
    name = column.lower()
    if any(term in name for term in (
        "complaint", "description", "subject", "detail",
        "text", "remark", "comment", "category", "sub_category",
        "subcategory", "type", "department", "ward", "location",
        "area", "address", "status"
    )):
        print(f"- {column}")

print("\n=== CATEGORY VALUE COUNTS ===")
for column in fieldnames:
    name = column.lower()
    if any(term in name for term in ("category", "subcategory", "sub_category")):
        counts = Counter(
            normalize(row.get(column)) or "[MISSING]"
            for row in rows
        )
        print(f"\nColumn: {column}")
        for value, count in counts.most_common(15):
            # Limit output length; do not print complaint narratives.
            print(f"  {value[:100]}: {count:,}")
        print(f"  Unique values: {len(counts):,}")

print("\n=== DUPLICATE RECORD CHECK ===")
serialized = [
    json.dumps(row, ensure_ascii=False, sort_keys=True)
    for row in rows
]
print(f"Exact duplicate rows beyond first occurrences: {len(rows) - len(set(serialized)):,}")

print("\n=== TELUGU SCRIPT COVERAGE ===")
telugu_pattern = __import__("re").compile(r"[\u0C00-\u0C7F]")
for column in fieldnames:
    if any(term in column.lower() for term in (
        "complaint", "description", "subject", "detail", "text", "comment"
    )):
        count = sum(bool(telugu_pattern.search(row.get(column) or "")) for row in rows)
        print(f"{column}: {count:,}/{len(rows):,} rows contain Telugu script")

print("\nInspection complete. Complaint contents were not printed.")
