
from pathlib import Path
import json
import re
import sys
from datetime import datetime, timezone

import pandas as pd


# ---------------------------------------------------------
# GrievanceHub - Phase 5: Training Eligibility Audit
# Read-only audit. Does NOT modify the source dataset.
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "translated_bengaluru_preprocessed_v1.csv"
)

REPORT_DIR = PROJECT_ROOT / "reports"

REQUIRED_COLUMNS = [
    "telugu_title",
    "telugu_description",
    "target_category_code",
    "privacy_screening_status",
    "training_eligibility",
    "release_status",
    "model_training_eligibility",
]

# Only explicit approval states can pass each gate.
# Pending, provisional, unknown, and missing values fail closed.
APPROVED_PRIVACY_STATES = {
    "CLEARED",
    "APPROVED",
    "PRIVACY_CLEARED",
}

APPROVED_TRAINING_STATES = {
    "CLEARED",
    "APPROVED",
    "ELIGIBLE",
}

APPROVED_RELEASE_STATES = {
    "APPROVED",
    "RELEASED",
}

APPROVED_MODEL_STATES = {
    "CLEARED",
    "APPROVED",
    "ELIGIBLE",
}

EXCLUDED_CATEGORY_CODES = {
    "",
    "UNKNOWN_SOURCE_CATEGORY",
    "UNCLASSIFIED",
    "OTHER_REVIEW",
}


def normalize_status(series):
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )


def count_statuses(series):
    values = normalize_status(series)
    counts = values.value_counts(dropna=False)
    return {
        str(key) if str(key) else "<MISSING>": int(value)
        for key, value in counts.items()
    }


def main():
    if not INPUT_FILE.exists():
        print(f"ERROR: Dataset not found:\n{INPUT_FILE}")
        return 1

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("GRIEVANCEHUB - PHASE 5 TRAINING ELIGIBILITY AUDIT")
    print("=" * 65)
    print(f"Input: {INPUT_FILE}")

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        low_memory=False
    )

    total_records = len(df)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        print("\nAUDIT BLOCKED: Required columns are missing.")
        print("Missing columns:", missing_columns)
        print("No training eligibility can be established.")

        report = {
            "audit_name": "GrievanceHub Phase 5 Training Eligibility Audit",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_file": str(INPUT_FILE),
            "total_records": total_records,
            "missing_required_columns": missing_columns,
            "eligible_records": 0,
            "gate_decision": "BLOCKED_MISSING_REQUIRED_COLUMNS",
        }

        report_path = REPORT_DIR / "phase5_training_eligibility_audit.json"
        report_path.write_text(
            json.dumps(report, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"\nReport saved: {report_path}")
        return 0

    # -----------------------------------------------------
    # 1. Eligibility checks
    # -----------------------------------------------------

    privacy_status = normalize_status(
        df["privacy_screening_status"]
    )
    training_status = normalize_status(
        df["training_eligibility"]
    )
    release_status = normalize_status(
        df["release_status"]
    )
    model_status = normalize_status(
        df["model_training_eligibility"]
    )

    privacy_approved = privacy_status.isin(
        APPROVED_PRIVACY_STATES
    )
    training_approved = training_status.isin(
        APPROVED_TRAINING_STATES
    )
    release_approved = release_status.isin(
        APPROVED_RELEASE_STATES
    )
    model_approved = model_status.isin(
        APPROVED_MODEL_STATES
    )

    # -----------------------------------------------------
    # 2. Text-quality checks
    # -----------------------------------------------------

    title = df["telugu_title"].fillna("").astype(str).str.strip()
    description = (
        df["telugu_description"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    text_present = (title.ne("")) & (description.ne(""))

    # Detect long dotted filler artifacts such as "..........."
    dotted_title = title.str.contains(r"\.{5,}", regex=True)
    dotted_description = description.str.contains(
        r"\.{5,}", regex=True
    )
    dotted_artifact = dotted_title | dotted_description

    # Detect rows where the title and description are identical.
    identical_title_description = (
        title.str.casefold() == description.str.casefold()
    ) & title.ne("")

    # Duplicate detection is diagnostic only.
    combined_text = (
        title.str.casefold() + " " + description.str.casefold()
    ).str.replace(r"\s+", " ", regex=True).str.strip()

    duplicate_text = (
        combined_text.ne("")
        & combined_text.duplicated(keep=False)
    )

    # -----------------------------------------------------
    # 3. Category validation
    # -----------------------------------------------------

    category = (
        df["target_category_code"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    category_valid = ~category.isin(EXCLUDED_CATEGORY_CODES)

    # -----------------------------------------------------
    # 4. Final fail-closed eligibility decision
    # -----------------------------------------------------

    eligible = (
        privacy_approved
        & training_approved
        & release_approved
        & model_approved
        & text_present
        & category_valid
        & ~dotted_artifact
    )

    eligible_count = int(eligible.sum())
    blocked_count = total_records - eligible_count

    # -----------------------------------------------------
    # 5. Category distribution
    # -----------------------------------------------------

    category_counts = (
        category.value_counts(dropna=False)
        .rename_axis("category_code")
        .reset_index(name="record_count")
    )

    category_counts["category_code"] = (
        category_counts["category_code"]
        .replace("", "<MISSING>")
    )

    category_counts["share_percent"] = (
        category_counts["record_count"] / max(total_records, 1) * 100
    ).round(2)

    category_counts["excluded_from_training_by_category_rule"] = (
        category_counts["category_code"].str.upper().isin(
            EXCLUDED_CATEGORY_CODES
        )
    )

    category_report_path = (
        REPORT_DIR / "phase5_category_distribution.csv"
    )
    category_counts.to_csv(
        category_report_path,
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 6. Build audit report
    # -----------------------------------------------------

    report = {
        "audit_name": "GrievanceHub Phase 5 Training Eligibility Audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(INPUT_FILE),
        "source_dataset_modified": False,
        "total_records": int(total_records),
        "eligible_records": eligible_count,
        "blocked_records": int(blocked_count),
        "eligible_percentage": round(
            eligible_count / max(total_records, 1) * 100, 2
        ),
        "gate_decision": (
            "ELIGIBLE_FOR_CONTROLLED_TRAINING_REVIEW"
            if eligible_count > 0
            else "HOLD_NO_RECORDS_CLEARED_FOR_TRAINING"
        ),
        "eligibility_policy": {
            "privacy_screening_must_be_explicitly_approved": True,
            "training_eligibility_must_be_approved": True,
            "release_status_must_be_approved_or_released": True,
            "model_training_eligibility_must_be_approved": True,
            "title_and_description_must_be_present": True,
            "category_must_not_be_unknown_or_review_only": True,
            "long_dotted_filler_artifacts_are_blocking": True,
        },
        "status_distributions": {
            "privacy_screening_status": count_statuses(
                df["privacy_screening_status"]
            ),
            "training_eligibility": count_statuses(
                df["training_eligibility"]
            ),
            "release_status": count_statuses(
                df["release_status"]
            ),
            "model_training_eligibility": count_statuses(
                df["model_training_eligibility"]
            ),
        },
        "data_quality": {
            "missing_title_or_description": int((~text_present).sum()),
            "long_dotted_filler_artifacts": int(dotted_artifact.sum()),
            "identical_title_description": int(
                identical_title_description.sum()
            ),
            "records_in_duplicate_text_groups": int(
                duplicate_text.sum()
            ),
            "invalid_or_review_only_categories": int(
                (~category_valid).sum()
            ),
        },
        "category_count": int(category.nunique()),
        "notes": [
            "This audit does not approve or clear any record.",
            "No regex match is not equivalent to privacy clearance.",
            "A record passes only when all eligibility gates pass.",
            "The source dataset is not modified.",
            "This dataset is Bengaluru-derived and machine-translated; "
            "it must not be represented as authentic GHMC complaint data.",
        ],
    }

    report_path = (
        REPORT_DIR / "phase5_training_eligibility_audit.json"
    )

    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    # -----------------------------------------------------
    # 7. Console summary
    # -----------------------------------------------------

    print("\n--- DATASET SUMMARY ---")
    print(f"Total records: {total_records}")
    print(f"Distinct categories: {category.nunique()}")

    print("\n--- ELIGIBILITY STATUS ---")
    print(f"Privacy status: {count_statuses(df['privacy_screening_status'])}")
    print(f"Training status: {count_statuses(df['training_eligibility'])}")
    print(f"Release status: {count_statuses(df['release_status'])}")
    print(
        "Model eligibility:",
        count_statuses(df["model_training_eligibility"])
    )

    print("\n--- DATA QUALITY ---")
    print(f"Missing Telugu title/description: {int((~text_present).sum())}")
    print(f"Dotted filler artifacts: {int(dotted_artifact.sum())}")
    print(
        "Identical title and description:",
        int(identical_title_description.sum())
    )
    print(f"Duplicate-text group records: {int(duplicate_text.sum())}")
    print(f"Unknown/review-only categories: {int((~category_valid).sum())}")

    print("\n--- FINAL TRAINING GATE ---")
    print(f"Eligible records: {eligible_count}")
    print(f"Blocked records: {blocked_count}")
    print(f"Decision: {report['gate_decision']}")

    print("\n--- OUTPUT FILES ---")
    print(f"JSON audit: {report_path}")
    print(f"Category report: {category_report_path}")

    print("\nAudit completed. Source dataset was not modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
