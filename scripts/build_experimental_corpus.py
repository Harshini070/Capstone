import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "external" / "bengaluru_complaints.csv"
TRANSLATIONS = ROOT / "data" / "interim" / "telugu_translation_queue.csv"
MAPPINGS = ROOT / "data" / "interim" / "category_mapping_review_v3.csv"
OUTPUT = ROOT / "data" / "processed" / "translated_bengaluru_experimental.csv"

def load_csv(path):
    for encoding in ("utf-8-sig", "cp1252", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"Cannot decode {path}")

def main():
    for path in (SOURCE, TRANSLATIONS, MAPPINGS):
        if not path.exists():
            raise FileNotFoundError(f"Required file missing: {path}")

    source = load_csv(SOURCE)
    translations = load_csv(TRANSLATIONS)
    mappings = load_csv(MAPPINGS)

    mapping_by_label = {}
    for row in mappings:
        label = (row.get("source_category_title") or "").strip()
        if label:
            mapping_by_label[label] = row

    translation_by_key = {}
    for row in translations:
        key = (
            row.get("source_field", ""),
            (row.get("source_text") or "").strip(),
        )
        translation_by_key[key] = row

    output_fields = [
        "source_record_index",
        "source_city",
        "target_city",
        "dataset_type",
        "source_title",
        "source_description",
        "telugu_title",
        "telugu_description",
        "source_category_id",
        "source_category_title",
        "proposed_target_category_code",
        "mapping_status",
        "source_ward_id",
        "source_ward_title",
        "source_location",
        "source_address",
        "source_latitude",
        "source_longitude",
        "translation_title_status",
        "translation_description_status",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    missing_translation = 0
    missing_mapping = 0

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()

        for index, row in enumerate(source, start=1):
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()

            title_translation = translation_by_key.get(("title", title), {})
            desc_translation = translation_by_key.get(("description", description), {})
            category = (row.get("category_title") or "").strip()
            mapping = mapping_by_label.get(category, {})

            if not title_translation.get("telugu_translation") or not desc_translation.get("telugu_translation"):
                missing_translation += 1
            if not mapping:
                missing_mapping += 1

            writer.writerow({
                "source_record_index": index,
                "source_city": "Bengaluru",
                "target_city": "Hyderabad (experimental adaptation; not verified)",
                "dataset_type": "Translated Bengaluru-derived experimental data; not authentic GHMC complaints",
                "source_title": title,
                "source_description": description,
                "telugu_title": title_translation.get("telugu_translation", ""),
                "telugu_description": desc_translation.get("telugu_translation", ""),
                "source_category_id": row.get("category_id", ""),
                "source_category_title": category,
                "proposed_target_category_code": mapping.get("proposed_target_category_code", ""),
                "mapping_status": mapping.get("mapping_status", "MISSING_MAPPING"),
                "source_ward_id": row.get("ward_id", ""),
                "source_ward_title": row.get("ward_title", ""),
                "source_location": row.get("location", ""),
                "source_address": row.get("address", ""),
                "source_latitude": row.get("latitude", ""),
                "source_longitude": row.get("longitude", ""),
                "translation_title_status": title_translation.get("review_status", "PENDING"),
                "translation_description_status": desc_translation.get("review_status", "PENDING"),
            })

    print(f"Experimental output written: {OUTPUT.relative_to(ROOT)}")
    print(f"Source records processed: {len(source):,}")
    print(f"Records with missing title or description translation: {missing_translation:,}")
    print(f"Records without a category mapping row: {missing_mapping:,}")
    print("Do not use this output as an authentic GHMC complaint dataset.")
    print("Source addresses, wards and coordinates remain Bengaluru source fields.")

if __name__ == "__main__":
    main()
