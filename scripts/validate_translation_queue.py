import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "interim" / "telugu_translation_queue.csv"
REPORT = ROOT / "data" / "interim" / "translation_validation_report.csv"

TELUGU = re.compile(r"[\u0C00-\u0C7F]")
LATIN = re.compile(r"[A-Za-z]")

def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run scripts/prepare_translation_queue.py first."
        )

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    results = []
    counts = Counter()

    for row in rows:
        translated = (row.get("telugu_translation") or "").strip()
        provider = (row.get("translation_provider") or "").strip()
        status = (row.get("translation_status") or "").strip().upper()

        if not translated:
            result = "MISSING_TRANSLATION"
        elif not TELUGU.search(translated):
            result = "NO_TELUGU_SCRIPT"
        elif not provider:
            result = "MISSING_PROVIDER"
        elif LATIN.search(translated):
            result = "MIXED_SCRIPT_REVIEW"
        else:
            result = "TELUGU_SCRIPT_PRESENT_REVIEW_REQUIRED"

        counts[result] += 1
        results.append({
            "text_id": row.get("text_id", ""),
            "source_field": row.get("source_field", ""),
            "translation_status": status,
            "validation_result": result,
            "review_status": row.get("review_status", ""),
        })

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "text_id", "source_field", "translation_status",
        "validation_result", "review_status",
    ]

    with REPORT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print(f"Queue rows checked: {len(rows):,}")
    print(f"Report saved: {REPORT.relative_to(ROOT)}")
    for label, count in sorted(counts.items()):
        print(f"{label}: {count:,}")

if __name__ == "__main__":
    main()
