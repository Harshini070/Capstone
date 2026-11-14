from pathlib import Path
from datetime import datetime, timezone
import json
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "reports"
    / "phase5_telugu_quality_record_level.csv"
)

REPORT_DIR = ROOT / "reports"
REVIEW_DIR = ROOT / "data" / "interim" / "human_review"

REVIEW_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_PER_CATEGORY = 30
RANDOM_SEED = 42

REQUIRED_COLUMNS = [
    "target_category_code",
    "telugu_title_cleaned",
    "telugu_description_cleaned",
    "title_quality_flags",
    "description_quality_flags",
    "title_telugu_letter_ratio",
    "description_telugu_letter_ratio",
    "title_geographic_terms",
    "description_geographic_terms",
    "title_description_identical",
    "duplicate_text_group",
    "review_priority",
]


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Quality assessment report not found: {INPUT}"
        )

    df = pd.read_csv(
        INPUT,
        encoding="utf-8-sig",
        low_memory=False
    )

    missing = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    # -----------------------------------------------------
    # 1. Stratified random sampling
    # -----------------------------------------------------

    df["target_category_code"] = (
        df["target_category_code"]
        .fillna("UNKNOWN_CATEGORY")
        .astype(str)
        .str.strip()
    )

    samples = []
    category_statistics = []

    for category, group in df.groupby(
        "target_category_code",
        sort=True
    ):
        population_size = len(group)

        sample_size = min(
            SAMPLE_PER_CATEGORY,
            population_size
        )

        selected = group.sample(
            n=sample_size,
            random_state=RANDOM_SEED
        ).copy()

        selected["category_population"] = population_size
        selected["category_sample_size"] = sample_size

        # Weight each sampled record by the number of
        # population records it represents in its category.
        selected["sampling_weight"] = (
            population_size / sample_size
        )

        samples.append(selected)

        category_statistics.append({
            "category": category,
            "population_records": population_size,
            "sample_records": sample_size,
            "sampling_fraction": round(
                sample_size / population_size, 4
            ),
            "sampling_weight": round(
                population_size / sample_size, 4
            ),
            "full_category_review": (
                sample_size == population_size
            ),
        })

    review = pd.concat(
        samples,
        ignore_index=True
    )

    # -----------------------------------------------------
    # 2. Prepare human annotation fields
    # -----------------------------------------------------

    review.insert(
        0,
        "review_record_id",
        [
            f"GH-REVIEW-{i:04d}"
            for i in range(1, len(review) + 1)
        ]
    )

    review["reviewer_id"] = ""
    review["review_date"] = ""

    review["translation_fidelity"] = ""
    review["telugu_grammar"] = ""
    review["translation_completeness"] = ""
    review["category_correctness"] = ""
    review["geography_assessment"] = ""
    review["privacy_assessment"] = ""

    review["overall_human_decision"] = ""
    review["reviewer_comments"] = ""

    review["review_status"] = "PENDING_HUMAN_REVIEW"

    # -----------------------------------------------------
    # 3. Save the review CSV
    # -----------------------------------------------------

    output_columns = [
        "review_record_id",
        "target_category_code",
        "category_population",
        "category_sample_size",
        "sampling_weight",
        "review_priority",
        "telugu_title_cleaned",
        "telugu_description_cleaned",
        "title_quality_flags",
        "description_quality_flags",
        "title_telugu_letter_ratio",
        "description_telugu_letter_ratio",
        "title_geographic_terms",
        "description_geographic_terms",
        "title_description_identical",
        "duplicate_text_group",
        "reviewer_id",
        "review_date",
        "translation_fidelity",
        "telugu_grammar",
        "translation_completeness",
        "category_correctness",
        "geography_assessment",
        "privacy_assessment",
        "overall_human_decision",
        "reviewer_comments",
        "review_status",
    ]

    review = review[output_columns]

    review_path = (
        REVIEW_DIR / "phase5_telugu_human_review_sample.csv"
    )

    review.to_csv(
        review_path,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 4. Save category sampling statistics
    # -----------------------------------------------------

    category_report = pd.DataFrame(category_statistics)

    category_path = (
        REPORT_DIR / "phase5_human_review_sampling.csv"
    )

    category_report.to_csv(
        category_path,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 5. Annotation guidelines
    # -----------------------------------------------------

    guidelines = {
        "project": "GrievanceHub",
        "task": "Telugu Municipal Complaint Translation Review",
        "sampling_method": (
            "Stratified random sampling by target category"
        ),
        "random_seed": RANDOM_SEED,
        "maximum_sample_per_category": SAMPLE_PER_CATEGORY,
        "annotation_fields": {
            "translation_fidelity": [
                "PASS",
                "PARTIAL",
                "FAIL",
                "UNCERTAIN",
            ],
            "telugu_grammar": [
                "GOOD",
                "MINOR_ISSUES",
                "MAJOR_ISSUES",
                "UNCERTAIN",
            ],
            "translation_completeness": [
                "COMPLETE",
                "PARTIAL",
                "INCOMPLETE",
                "UNCERTAIN",
            ],
            "category_correctness": [
                "CORRECT",
                "INCORRECT",
                "AMBIGUOUS",
                "UNCERTAIN",
            ],
            "geography_assessment": [
                "SOURCE_REFERENCE_VALID",
                "REQUIRES_CONTEXTUAL_REVIEW",
                "INCORRECT_OR_MISTRANSLATED",
                "NO_GEOGRAPHY_REFERENCE",
            ],
            "privacy_assessment": [
                "NO_OBVIOUS_PII",
                "POTENTIAL_PII",
                "PII_IDENTIFIED",
                "UNCERTAIN",
            ],
            "overall_human_decision": [
                "ACCEPT",
                "ACCEPT_WITH_MINOR_ISSUES",
                "REJECT",
                "ESCALATE",
            ],
        },
        "review_instructions": [
            "Compare the Telugu title and description for semantic fidelity.",
            "Check whether the complaint meaning is preserved.",
            "Evaluate grammar, readability, and completeness.",
            "Check category correctness against the complaint content.",
            "Do not replace Bengaluru references with Hyderabad references.",
            "Flag personal names, addresses, phone numbers, and other identifiers.",
            "Do not mark privacy clearance based only on this linguistic review.",
            "Use UNCERTAIN or ESCALATE rather than guessing.",
            "Do not modify the original complaint text.",
        ],
        "important_limitations": [
            "The sample is a review pilot, not a complete corpus approval.",
            "Human reviewers should have Telugu language proficiency.",
            "Sampling weights are required for population-level estimates.",
            "One reviewer is insufficient to establish inter-annotator agreement.",
            "No record is automatically approved for model training.",
        ],
    }

    guideline_path = (
        REVIEW_DIR / "phase5_human_review_guidelines.json"
    )

    guideline_path.write_text(
        json.dumps(
            guidelines,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # 6. Save execution summary
    # -----------------------------------------------------

    summary = {
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "population_records": len(df),
        "categories": len(category_statistics),
        "review_sample_records": len(review),
        "maximum_sample_per_category": SAMPLE_PER_CATEGORY,
        "random_seed": RANDOM_SEED,
        "sampling_method": "STRATIFIED_RANDOM",
        "source_dataset_modified": False,
        "training_eligibility_changed": False,
        "review_status": "PENDING_HUMAN_REVIEW",
        "files": {
            "review_sample": str(review_path),
            "category_sampling": str(category_path),
            "guidelines": str(guideline_path),
        },
    }

    summary_path = (
        REPORT_DIR / "phase5_human_review_preparation.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=4,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # 7. Console summary
    # -----------------------------------------------------

    print("=" * 70)
    print("GRIEVANCEHUB - HUMAN REVIEW PREPARATION")
    print("=" * 70)

    print(f"Population records: {len(df)}")
    print(f"Categories: {len(category_statistics)}")
    print(f"Review sample records: {len(review)}")

    print("\nCATEGORY SAMPLING:")
    print(category_report.to_string(index=False))

    print("\nGENERATED FILES:")
    print("Review sample:", review_path)
    print("Sampling report:", category_path)
    print("Guidelines:", guideline_path)
    print("Summary:", summary_path)

    print("\nReview preparation completed.")
    print("All records remain pending human review.")
    print("No training eligibility was changed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
