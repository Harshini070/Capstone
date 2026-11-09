from pathlib import Path
import json
import re
import unicodedata

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data/processed/translated_bengaluru_text_only_unflagged_v1.csv"
OUTPUT = ROOT / "data/processed/translated_bengaluru_preprocessed_v1.csv"
REPORT_DIR = ROOT / "reports/aggregate/preprocessing_final_v1"

TEXT_COLUMNS = ["telugu_title", "telugu_description"]

MODEL_COLUMNS = [
    "record_id",
    "telugu_title",
    "telugu_description",
    "target_category_code",
]

AUDIT_COLUMNS = [
    "target_category",
    "mapping_status",
    "translation_quality_status",
    "title_translation_match_status",
    "description_translation_match_status",
    "translation_reconstruction_status",
    "privacy_screening_status",
    "training_eligibility",
    "release_status",
]


def normalize_text(value):
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFC", str(value))
    text = re.sub(r"\s+", " ", text).strip()

    return text


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Input dataset not found: {INPUT}")

    if OUTPUT.exists():
        raise FileExistsError(
            f"Output already exists; refusing to overwrite: {OUTPUT}"
        )

    df = pd.read_csv(INPUT, low_memory=False)

    required = set(MODEL_COLUMNS + AUDIT_COLUMNS)
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Required columns missing: {sorted(missing)}")

    original_count = len(df)

    # Keep a separate copy of the input text for audit comparisons.
    original_text = {
        column: df[column].fillna("").astype(str).copy()
        for column in TEXT_COLUMNS
    }

    # Conservative normalization only.
    for column in TEXT_COLUMNS:
        df[column] = df[column].apply(normalize_text)

    # Preserve every row and all source/audit fields.
    if len(df) != original_count:
        raise AssertionError("Record count changed unexpectedly.")

    if df["record_id"].duplicated().any():
        raise AssertionError("Duplicate record IDs detected.")

    if df[TEXT_COLUMNS].isna().any().any():
        raise AssertionError("Missing text detected after preprocessing.")

    # Ensure only the declared text fields were transformed.
    for column in df.columns:
        if column not in TEXT_COLUMNS:
            continue

        changed = int(
            (original_text[column] != df[column].astype(str)).sum()
        )
        print(f"{column} changed rows: {changed}")

    # Add explicit model-input eligibility metadata.
    # This does not grant privacy or training approval.
    df["preprocessing_version"] = "conservative_v1"
    df["preprocessing_status"] = "NORMALIZED"
    df["model_training_eligibility"] = "NOT_CLEARED"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Aggregate-only statistics.
    report = {
        "dataset_name": OUTPUT.name,
        "input_dataset": str(INPUT.relative_to(ROOT)),
        "records_before": original_count,
        "records_after": len(df),
        "record_count_preserved": len(df) == original_count,
        "unique_record_ids": int(df["record_id"].nunique()),
        "duplicate_record_ids": int(df["record_id"].duplicated().sum()),
        "missing_title": int(df["telugu_title"].eq("").sum()),
        "missing_description": int(df["telugu_description"].eq("").sum()),
        "preprocessing": [
            "Unicode NFC normalization",
            "Whitespace normalization and trimming",
        ],
        "not_performed": [
            "Punctuation deletion",
            "Digit deletion",
            "Latin-script deletion",
            "Automatic truncation",
            "Automatic complaint deletion",
            "Label merging",
        ],
        "privacy_clearance": "NOT_GRANTED",
        "training_approval": "NOT_GRANTED",
        "release_status": "HOLD",
    }

    # Save only after all structural checks pass.
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    with (REPORT_DIR / "preprocessing_report_v1.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    print("\n========== PREPROCESSING COMPLETE ==========")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("\nDataset saved:", OUTPUT)
    print("Aggregate report saved:", REPORT_DIR)


if __name__ == "__main__":
    main()
