import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"
MANIFEST = ROOT / "data/interim/experimental_privacy_exclusion_manifest.csv"
OUTPUT = ROOT / "data/processed/translated_bengaluru_text_only_unflagged_v1.csv"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    for path in (SOURCE, MANIFEST):
        if not path.exists():
            raise FileNotFoundError(path)

    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing output: {OUTPUT}"
        )

    corpus = read_csv(SOURCE)
    manifest = read_csv(MANIFEST)

    privacy_held_ids = {r["record_id"] for r in manifest}

    fields = [
        "record_id",
        "source_record_id",
        "source_city",
        "dataset_type",
        "source_title",
        "source_description",
        "telugu_title",
        "telugu_description",
        "target_category_code",
        "target_category",
        "source_category_id",
        "source_category_title",
        "mapping_status",
        "mapping_rationale",
        "translation_quality_status",
        "title_translation_match_status",
        "description_translation_match_status",
        "translation_reconstruction_status",
        "experimental_candidate",
        "privacy_screening_status",
        "training_eligibility",
        "release_status"
    ]

    output_rows = []

    for row in corpus:
        if row["experimental_candidate"] != "True":
            continue

        if row["record_id"] in privacy_held_ids:
            continue

        output_rows.append({
            "record_id": row["record_id"],
            "source_record_id": row["source_record_id"],
            "source_city": row["source_city"],
            "dataset_type": row["dataset_type"],
            "source_title": row["source_title"],
            "source_description": row["source_description"],
            "telugu_title": row["telugu_title"],
            "telugu_description": row["telugu_description"],
            "target_category_code": row["target_category_code"],
            "target_category": row["target_category"],
            "source_category_id": row["source_category_id"],
            "source_category_title": row["source_category_title"],
            "mapping_status": row["mapping_status"],
            "mapping_rationale": row["mapping_rationale"],
            "translation_quality_status": row["translation_quality_status"],
            "title_translation_match_status": row["title_translation_match_status"],
            "description_translation_match_status": row["description_translation_match_status"],
            "translation_reconstruction_status": row["translation_reconstruction_status"],
            "experimental_candidate": "True",
            "privacy_screening_status": "NO_REGEX_MATCH_PENDING_MANUAL_REVIEW",
            "training_eligibility": "PROVISIONAL_NOT_CLEARED",
            "release_status": "HOLD"
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    print("=== TEXT-ONLY EXPERIMENTAL DATASET ===")
    print("Original corpus records:", len(corpus))
    print("Privacy-held candidates:", len(privacy_held_ids))
    print("Text-only records generated:", len(output_rows))
    print("Output:", OUTPUT.relative_to(ROOT))

    print("\nLocation metadata excluded:")
    print("Ward IDs, ward names, locations, addresses and coordinates")

    print("\nPrivacy clearance: NOT GRANTED")
    print("Training eligibility: PROVISIONAL_NOT_CLEARED")
    print("Release status: HOLD")
    print("Original corpus modified: NO")

if __name__ == "__main__":
    main()
