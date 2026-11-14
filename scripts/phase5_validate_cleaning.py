
from pathlib import Path
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

SOURCE = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v1.csv"
)

CANDIDATE = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v2_cleaning_candidate.csv"
)

REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TEXT_COLUMNS = ["telugu_title", "telugu_description"]

STATUS_COLUMNS = [
    "privacy_screening_status",
    "training_eligibility",
    "release_status",
    "model_training_eligibility",
]

PATTERN = re.compile(r"(?:\.{5,}|-{5,})\s*$")


def expected_clean(value):
    if pd.isna(value):
        return ""
    return PATTERN.sub("", str(value)).rstrip()


def main():
    source = pd.read_csv(
        SOURCE, encoding="utf-8-sig", low_memory=False
    )
    candidate = pd.read_csv(
        CANDIDATE, encoding="utf-8-sig", low_memory=False
    )

    errors = []

    if len(source) != len(candidate):
        errors.append("Record count changed.")

    if not source.columns.isin(candidate.columns).all():
        errors.append("One or more original columns are missing.")

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print("-", error)
        return

    results = {}

    for column in TEXT_COLUMNS:
        cleaned_column = column + "_cleaned"
        flag_column = column + "_artifact_removed"

        original = source[column].fillna("").astype(str)
        actual = candidate[cleaned_column].fillna("").astype(str)

        expected = original.map(expected_clean)

        exact_transform_match = actual.equals(expected)

        original_preserved = (
            original.equals(
                candidate[column].fillna("").astype(str)
            )
        )

        remaining_artifacts = int(
            actual.str.contains(PATTERN, regex=True).sum()
        )

        new_empty_fields = int(
            ((original.str.strip() != "") & (actual.str.strip() == "")).sum()
        )

        flag_consistent = (
            candidate[flag_column].astype(bool).equals(
                original.ne(actual)
            )
        )

        results[column] = {
            "original_preserved": bool(original_preserved),
            "cleaning_rule_followed_exactly": bool(exact_transform_match),
            "remaining_terminal_artifacts": remaining_artifacts,
            "new_empty_fields": new_empty_fields,
            "change_flags_consistent": bool(flag_consistent),
            "modified_records": int(original.ne(actual).sum()),
        }

        if not original_preserved:
            errors.append(f"{column}: original field was modified.")

        if not exact_transform_match:
            errors.append(f"{column}: unexpected transformation detected.")

        if remaining_artifacts:
            errors.append(f"{column}: terminal artifacts remain.")

        if new_empty_fields:
            errors.append(f"{column}: new empty text fields detected.")

        if not flag_consistent:
            errors.append(f"{column}: modification flags are inconsistent.")

    # Verify eligibility and release fields have not changed.
    for column in STATUS_COLUMNS:
        if column not in source.columns:
            errors.append(f"Source missing status field: {column}")
            continue

        if column not in candidate.columns:
            errors.append(f"Candidate missing status field: {column}")
            continue

        before = source[column].fillna("<NA>").astype(str)
        after = candidate[column].fillna("<NA>").astype(str)

        if not before.equals(after):
            errors.append(f"Eligibility/status field changed: {column}")

    # Unique records with at least one cleaned field.
    title_changed = (
        source["telugu_title"].fillna("").astype(str)
        != candidate["telugu_title_cleaned"].fillna("").astype(str)
    )

    description_changed = (
        source["telugu_description"].fillna("").astype(str)
        != candidate["telugu_description_cleaned"].fillna("").astype(str)
    )

    unique_records_modified = int(
        (title_changed | description_changed).sum()
    )

    report = {
        "total_records": len(source),
        "unique_records_modified": unique_records_modified,
        "field_validation": results,
        "eligibility_fields_unchanged": not any(
            "Eligibility/status field changed" in error
            for error in errors
        ),
        "validation_status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "source_dataset_modified": False,
    }

    report_path = REPORT_DIR / "phase5_cleaning_validation.json"

    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print("=" * 60)
    print("PHASE 5 CLEANING VALIDATION")
    print("=" * 60)

    print(json.dumps(report, indent=4, ensure_ascii=False))
    print("\nReport saved:", report_path)


if __name__ == "__main__":
    main()
