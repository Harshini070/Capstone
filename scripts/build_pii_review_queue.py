import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"
OUTPUT = ROOT / "data/interim/experimental_pii_review_queue.csv"

PATTERNS = {
    "EMAIL": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "INDIAN_MOBILE": r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)",
    "URL": r"\bhttps?://\S+",
    "AADHAAR_LIKE_12_DIGIT": r"(?<!\d)\d{12}(?!\d)",
}

import re
PATTERNS = {
    name: re.compile(pattern, re.I)
    for name, pattern in PATTERNS.items()
}

FIELDS = [
    "source_title",
    "source_description",
    "telugu_title",
    "telugu_description",
    "source_location",
    "source_address",
]

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing review queue: {OUTPUT}"
        )

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    queue = []
    unique_pattern_counts = Counter()
    unique_field_counts = Counter()
    affected_candidates = set()
    affected_all = set()

    for row in rows:
        matched_patterns = set()
        matched_fields = set()

        for field in FIELDS:
            value = row.get(field, "") or ""

            for name, pattern in PATTERNS.items():
                if pattern.search(value):
                    matched_patterns.add(name)
                    matched_fields.add(field)
                    unique_field_counts[(field, name)] += 1

        if not matched_patterns:
            continue

        record_id = row["record_id"]
        affected_all.add(record_id)

        if row["experimental_candidate"] == "True":
            affected_candidates.add(record_id)

        for name in matched_patterns:
            unique_pattern_counts[name] += 1

        queue.append({
            "record_id": record_id,
            "experimental_candidate": row["experimental_candidate"],
            "matched_patterns": ";".join(sorted(matched_patterns)),
            "matched_fields": ";".join(sorted(matched_fields)),
            "review_status": "PENDING_PRIVACY_REVIEW",
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "record_id",
        "experimental_candidate",
        "matched_patterns",
        "matched_fields",
        "review_status",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue)

    print("=== RECORD-LEVEL PRIVACY REVIEW QUEUE ===")
    print("Total source records:", len(rows))
    print("Unique affected records:", len(affected_all))
    print("Affected provisional candidates:", len(affected_candidates))
    print("Review queue rows:", len(queue))

    print("\n=== UNIQUE RECORDS BY PATTERN ===")
    for name in PATTERNS:
        print(f"{name}: {unique_pattern_counts[name]}")

    print("\n=== UNIQUE RECORDS BY FIELD AND PATTERN ===")
    for (field, name), count in sorted(unique_field_counts.items()):
        print(f"{field} | {name}: {count}")

    print("\nReview queue:", OUTPUT.relative_to(ROOT))
    print("No complaint text or detected values were exported.")
    print("All flagged records remain pending privacy review.")

if __name__ == "__main__":
    main()
