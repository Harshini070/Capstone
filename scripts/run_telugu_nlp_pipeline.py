
"""Run the GrievanceHub Telugu NLP pipeline on a CSV dataset.

The output contains identifiers, category metadata, quality metadata,
and derived NLP features. Complaint text is not exported.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from grievancehub.nlp.pipeline import (
    PIPELINE_VERSION,
    process_record,
)


REQUIRED_COLUMNS = {
    "record_id",
    "telugu_title",
    "telugu_description",
    "target_category_code",
    "target_category",
    "release_status",
    "model_training_eligibility",
}


# Six metadata columns plus 26 derived features.
OUTPUT_FIELDS = [
    # Metadata
    "record_id",
    "target_category_code",
    "target_category",
    "release_status",
    "model_training_eligibility",
    "nlp_pipeline_version",

    # Title features
    "title_char_count",
    "title_telugu_token_count",
    "title_unique_token_count",
    "title_lexical_diversity",
    "title_telugu_letter_ratio",
    "title_latin_letter_ratio",
    "title_punctuation_ratio",
    "title_max_period_run",
    "title_max_repeated_character_run",
    "title_long_period_flag",
    "title_low_telugu_coverage_flag",

    # Description features
    "description_char_count",
    "description_telugu_token_count",
    "description_unique_token_count",
    "description_lexical_diversity",
    "description_telugu_letter_ratio",
    "description_latin_letter_ratio",
    "description_punctuation_ratio",
    "description_max_period_run",
    "description_max_repeated_character_run",
    "description_long_period_flag",
    "description_low_telugu_coverage_flag",

    # Combined features
    "combined_telugu_tokens",
    "combined_char_count",
    "combined_long_period_flag",
    "combined_low_telugu_coverage_flag",
]


def run_pipeline(input_path: Path, output_dir: Path) -> dict:
    """Process the complete input CSV and save derived features."""

    if not input_path.exists():
        raise FileNotFoundError(f"Input dataset not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    feature_path = (
        output_dir / "telugu_nlp_features_local_v1.csv"
    )

    report_path = (
        output_dir / "telugu_nlp_pipeline_report_v1.json"
    )

    total = 0
    seen_ids = set()

    release_counts = Counter()
    eligibility_counts = Counter()
    category_counts = Counter()

    title_period_flags = 0
    description_period_flags = 0

    low_telugu_title_flags = 0
    low_telugu_description_flags = 0

    combined_period_flags = 0
    combined_low_telugu_flags = 0

    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source:

        reader = csv.DictReader(source)

        missing_columns = REQUIRED_COLUMNS - set(
            reader.fieldnames or []
        )

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        with feature_path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as destination:

            writer = csv.DictWriter(
                destination,
                fieldnames=OUTPUT_FIELDS,
                extrasaction="ignore",
            )

            writer.writeheader()

            for row in reader:

                result = process_record(row)

                record_id = result["record_id"]

                if record_id in seen_ids:
                    raise ValueError(
                        f"Duplicate record ID: {record_id}"
                    )

                seen_ids.add(record_id)

                # Export only the explicitly approved fields.
                writer.writerow({
                    field: result[field]
                    for field in OUTPUT_FIELDS
                })

                total += 1

                release_counts[row["release_status"]] += 1

                eligibility_counts[
                    row["model_training_eligibility"]
                ] += 1

                category_counts[
                    row["target_category_code"]
                ] += 1

                title_period_flags += int(
                    result["title_long_period_flag"]
                )

                description_period_flags += int(
                    result["description_long_period_flag"]
                )

                low_telugu_title_flags += int(
                    result["title_low_telugu_coverage_flag"]
                )

                low_telugu_description_flags += int(
                    result["description_low_telugu_coverage_flag"]
                )

                combined_period_flags += int(
                    result["combined_long_period_flag"]
                )

                combined_low_telugu_flags += int(
                    result["combined_low_telugu_coverage_flag"]
                )

    report = {
        "pipeline_version": PIPELINE_VERSION,
        "input_file": input_path.name,

        "records_processed": total,
        "unique_record_ids": len(seen_ids),
        "duplicate_record_ids": total - len(seen_ids),

        "total_output_columns": len(OUTPUT_FIELDS),
        "metadata_columns": 6,
        "derived_feature_columns": 26,

        "release_status_counts": dict(release_counts),
        "training_eligibility_counts": dict(eligibility_counts),

        "category_count": len(category_counts),

        "title_long_period_records": title_period_flags,
        "description_long_period_records": description_period_flags,
        "combined_long_period_records": combined_period_flags,

        "low_telugu_title_records": low_telugu_title_flags,
        "low_telugu_description_records": low_telugu_description_flags,

        "combined_low_telugu_coverage_records": (
            combined_low_telugu_flags
        ),

        "training_eligible_records": eligibility_counts.get(
            "APPROVED", 0
        ),

        "complaint_text_in_output": False,
        "source_dataset_modified": False,
    }

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as report_file:

        json.dump(
            report,
            report_file,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 65)
    print("GRIEVANCEHUB TELUGU NLP PIPELINE")
    print("=" * 65)

    print(json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ))

    print("\nFeature output:", feature_path)
    print("Aggregate report:", report_path)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Run the GrievanceHub Telugu NLP pipeline."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the preprocessed Telugu complaint CSV.",
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for derived feature output and report.",
    )

    args = parser.parse_args()

    run_pipeline(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
