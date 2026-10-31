import csv
import re
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"

PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "INDIAN_MOBILE": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "URL": re.compile(r"\bhttps?://\S+", re.I),
    "AADHAAR_LIKE_12_DIGIT": re.compile(r"(?<!\d)\d{12}(?!\d)"),
}

TEXT_FIELDS = [
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

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    record_counts = Counter()
    field_counts = defaultdict(Counter)
    candidate_counts = Counter()

    for row in rows:
        record_id = row["record_id"]
        is_candidate = row["experimental_candidate"] == "True"

        for field in TEXT_FIELDS:
            value = row.get(field, "") or ""

            for name, pattern in PATTERNS.items():
                if pattern.search(value):
                    record_counts[name] += 1
                    field_counts[field][name] += 1

                    if is_candidate:
                        candidate_counts[name] += 1

    print("=== EXPERIMENTAL CORPUS PII SCREENING ===")
    print("Records scanned:", len(rows))
    print("Fields scanned:", len(TEXT_FIELDS))
    print("Candidate records:", sum(
        r["experimental_candidate"] == "True" for r in rows
    ))

    print("\n=== PATTERN-FIELD MATCH OCCURRENCES BY TYPE ===")
    for name in PATTERNS:
        print(f"{name}: {record_counts[name]}")

    print("\n=== FLAGGED FIELD COUNTS ===")
    for field in TEXT_FIELDS:
        total = sum(field_counts[field].values())
        print(f"{field}: {total}")
        for name, count in field_counts[field].items():
            print(f"  {name}: {count}")

    print("\n=== CANDIDATE PATTERN-FIELD MATCH OCCURRENCES ===")
    for name in PATTERNS:
        print(f"{name}: {candidate_counts[name]}")

    print("\n=== PRIVACY SCREENING DECISION ===")
    total_flags = sum(record_counts.values())

    if total_flags:
        print("REVIEW_REQUIRED")
        print("Flagged records require privacy review before release.")
    else:
        print("NO_REGEX_MATCHES")
        print("This does not establish that the corpus is PII-free.")

    print("\nNo complaint text or detected personal information was printed.")
    print("Regex screening cannot reliably detect names or all personal data.")

if __name__ == "__main__":
    main()
