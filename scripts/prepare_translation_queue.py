import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "external" / "bengaluru_complaints.csv"
OUTPUT = ROOT / "data" / "interim" / "telugu_translation_queue.csv"

def read_source(path):
    for encoding in ("cp1252", "utf-8-sig", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f)), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeError("Could not decode the source CSV.")

def text_id(field, text):
    raw = field + "\0" + text
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source dataset not found: {SOURCE}")

    rows, encoding = read_source(SOURCE)
    if not rows:
        raise ValueError("The source CSV is empty.")

    required = {"title", "description"}
    missing = required - set(rows[0].keys())
    if missing:
        raise ValueError(f"Missing required source columns: {sorted(missing)}")

    unique = {}

    for row in rows:
        for field in ("title", "description"):
            original = (row.get(field) or "").strip()
            if not original:
                continue

            key = (field, original)
            if key not in unique:
                unique[key] = {
                    "text_id": text_id(field, original),
                    "source_field": field,
                    "source_text": original,
                    "target_language": "te",
                    "telugu_translation": "",
                    "translation_provider": "",
                    "translation_model": "",
                    "translation_status": "PENDING",
                    "review_status": "PENDING",
                }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "text_id", "source_field", "source_text", "target_language",
        "telugu_translation", "translation_provider", "translation_model",
        "translation_status", "review_status",
    ]

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(unique.values())

    print(f"Source encoding: {encoding}")
    print(f"Source records: {len(rows):,}")
    print(f"Unique title/description strings: {len(unique):,}")
    print(f"Queue saved: {OUTPUT.relative_to(ROOT)}")
    print("Translations have not been generated yet.")

if __name__ == "__main__":
    main()
