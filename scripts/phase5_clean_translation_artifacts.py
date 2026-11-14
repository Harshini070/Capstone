
from pathlib import Path
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v1.csv"
)

OUTPUT = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v2_cleaning_candidate.csv"
)

REPORT = ROOT / "reports"
REPORT.mkdir(parents=True, exist_ok=True)

TEXT_COLUMNS = ["telugu_title", "telugu_description"]

# Only remove long terminal sequences.
# Normal punctuation such as ".." is preserved.
TRAILING_ARTIFACT = re.compile(r"(?:\.{5,}|-{5,})\s*$")


def clean_terminal_artifact(value):
    if pd.isna(value):
        return "", False

    original = str(value)
    cleaned = TRAILING_ARTIFACT.sub("", original).rstrip()

    return cleaned, cleaned != original


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    df = pd.read_csv(
        INPUT,
        encoding="utf-8-sig",
        low_memory=False
    )

    for column in TEXT_COLUMNS:
        if column not in df.columns:
            raise ValueError(f"Missing column: {column}")

    # Preserve originals; add separate candidate columns.
    summary = {}

    for column in TEXT_COLUMNS:
        results = df[column].apply(clean_terminal_artifact)

        cleaned_column = column + "_cleaned"
        flag_column = column + "_artifact_removed"

        df[cleaned_column] = results.apply(lambda x: x[0])
        df[flag_column] = results.apply(lambda x: x[1])

        summary[column] = {
            "records_modified": int(
                df[flag_column].sum()
            ),
            "records_unchanged": int(
                (~df[flag_column]).sum()
            ),
        }

    df["text_cleaning_version"] = "phase5_v1"
    df["text_cleaning_status"] = "CANDIDATE_NOT_HUMAN_APPROVED"

    # Do not change eligibility or release-status fields.
    df.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig"
    )

    import json

    report = {
        "total_records": len(df),
        "input_file": str(INPUT),
        "output_file": str(OUTPUT),
        "source_modified": False,
        "cleaning_rule": (
            "Remove terminal sequences of five or more periods "
            "or hyphens. Preserve ordinary punctuation and "
            "all internal text."
        ),
        "columns": summary,
        "training_eligibility_changed": False,
        "approval_status": "CANDIDATE_REQUIRES_VALIDATION",
    }

    report_path = REPORT / "phase5_cleaning_candidate_summary.json"

    report_path.write_text(
        json.dumps(report, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print("=" * 60)
    print("GRIEVANCEHUB - PHASE 5 CANDIDATE CLEANING")
    print("=" * 60)

    print(f"Records processed: {len(df)}")

    for column, values in summary.items():
        print(f"\n{column}")
        print(f"Modified: {values['records_modified']}")
        print(f"Unchanged: {values['records_unchanged']}")

    print("\nOutput:", OUTPUT)
    print("Report:", report_path)
    print("\nOriginal dataset preserved.")
    print("Training eligibility remains unchanged.")


if __name__ == "__main__":
    main()
