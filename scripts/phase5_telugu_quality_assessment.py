
from pathlib import Path
import json
import re
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v2_cleaning_candidate.csv"
)

REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42
REVIEW_SAMPLES_PER_CATEGORY = 10

TEXT_COLUMNS = [
    "telugu_title_cleaned",
    "telugu_description_cleaned",
]

# Known source-city references. These are review indicators,
# not automatic errors: some references may be legitimate context.
GEOGRAPHIC_TERMS = [
    "bengaluru",
    "bangalore",
    "mysore",
    "bbmp",
    "బెంగుళూరు",
    "బెంగళూరు",
    "మైసూరు",
    "బీబీఎంపీ",
    "వర్తూర్",
    "యలహంక",
    "జలహళ్లి",
    "దాసరహళ్లి",
]

# ---------------------------------------------------------
# Text analysis helpers
# ---------------------------------------------------------

TELUGU_PATTERN = re.compile(r"[\u0C00-\u0C7F]")
LATIN_PATTERN = re.compile(r"[A-Za-z]")
LETTER_PATTERN = re.compile(r"[^\W\d_]", re.UNICODE)

REPEATED_PUNCTUATION = re.compile(
    r"[.!?]{5,}|[-_]{5,}"
)

MULTIPLE_SPACES = re.compile(r"\s{2,}")

WORD_PATTERN = re.compile(r"\S+")


def safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def count_matches(pattern, text):
    return len(pattern.findall(text))


def calculate_language_metrics(text):
    telugu_chars = count_matches(TELUGU_PATTERN, text)
    latin_chars = count_matches(LATIN_PATTERN, text)
    letters = count_matches(LETTER_PATTERN, text)

    telugu_ratio = (
        telugu_chars / letters if letters else 0.0
    )

    latin_ratio = (
        latin_chars / letters if letters else 0.0
    )

    return {
        "telugu_characters": telugu_chars,
        "latin_characters": latin_chars,
        "letter_characters": letters,
        "telugu_letter_ratio": round(telugu_ratio, 4),
        "latin_letter_ratio": round(latin_ratio, 4),
        "contains_telugu": telugu_chars > 0,
        "contains_latin": latin_chars > 0,
    }


def find_geographic_terms(text):
    lower_text = text.casefold()

    return [
        term for term in GEOGRAPHIC_TERMS
        if term.casefold() in lower_text
    ]


def repeated_word_ratio(text):
    words = WORD_PATTERN.findall(text.casefold())

    if len(words) < 2:
        return 0.0

    repeated_count = len(words) - len(set(words))

    return round(repeated_count / len(words), 4)


def analyze_field(text, field_name):
    language = calculate_language_metrics(text)

    words = WORD_PATTERN.findall(text)
    geo_terms = find_geographic_terms(text)

    flags = []

    if not text:
        flags.append("EMPTY_TEXT")

    if not language["contains_telugu"]:
        flags.append("NO_TELUGU_SCRIPT")

    if language["contains_latin"]:
        flags.append("LATIN_SCRIPT_PRESENT")

    if field_name == "title" and len(text) < 3:
        flags.append("VERY_SHORT_TITLE")

    if field_name == "description" and len(text) < 20:
        flags.append("VERY_SHORT_DESCRIPTION")

    if field_name == "description" and len(text) > 5000:
        flags.append("UNUSUALLY_LONG_DESCRIPTION")

    if REPEATED_PUNCTUATION.search(text):
        flags.append("REPEATED_PUNCTUATION")

    if MULTIPLE_SPACES.search(text):
        flags.append("MULTIPLE_WHITESPACE")

    if repeated_word_ratio(text) > 0.20:
        flags.append("HIGH_REPEATED_WORD_RATIO")

    if geo_terms:
        flags.append("SOURCE_GEOGRAPHY_REFERENCE")

    result = {
        "character_count": len(text),
        "word_count": len(words),
        "repeated_word_ratio": repeated_word_ratio(text),
        "geographic_terms": ";".join(geo_terms),
        "quality_flags": ";".join(flags),
        "flag_count": len(flags),
    }

    result.update(language)

    return result


# ---------------------------------------------------------
# Main assessment
# ---------------------------------------------------------

def main():
    if not INPUT.exists():
        print("ERROR: Cleaning candidate not found:")
        print(INPUT)
        print("\nRun the Phase 5 cleaning script first.")
        return 1

    print("=" * 70)
    print("GRIEVANCEHUB - CONSOLIDATED TELUGU QUALITY ASSESSMENT")
    print("=" * 70)

    df = pd.read_csv(
        INPUT,
        encoding="utf-8-sig",
        low_memory=False
    )

    missing_columns = [
        col for col in TEXT_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing cleaned text columns: {missing_columns}"
        )

    if "target_category_code" not in df.columns:
        raise ValueError("Missing target_category_code column.")

    titles = df["telugu_title_cleaned"].map(safe_text)
    descriptions = df["telugu_description_cleaned"].map(safe_text)

    # -----------------------------------------------------
    # 1. Analyze titles and descriptions independently
    # -----------------------------------------------------

    title_results = [
        analyze_field(text, "title")
        for text in titles
    ]

    description_results = [
        analyze_field(text, "description")
        for text in descriptions
    ]

    title_df = pd.DataFrame(title_results).add_prefix("title_")
    description_df = pd.DataFrame(
        description_results
    ).add_prefix("description_")

    results = pd.concat(
        [df.reset_index(drop=True),
         title_df,
         description_df],
        axis=1
    )

    # -----------------------------------------------------
    # 2. Record-level quality indicators
    # -----------------------------------------------------

    results["title_description_identical"] = (
        titles.str.casefold() == descriptions.str.casefold()
    ) & titles.ne("")

    combined_text = (
        titles.str.casefold()
        + " "
        + descriptions.str.casefold()
    ).str.replace(r"\s+", " ", regex=True).str.strip()

    results["duplicate_text_group"] = (
        combined_text.ne("")
        & combined_text.duplicated(keep=False)
    )

    results["title_description_overlap_review"] = (
        results["title_description_identical"]
    )

    results["has_telugu_in_both_fields"] = (
        results["title_contains_telugu"]
        & results["description_contains_telugu"]
    )

    results["has_source_geography_reference"] = (
        results["title_quality_flags"].str.contains(
            "SOURCE_GEOGRAPHY_REFERENCE", regex=False
        )
        | results["description_quality_flags"].str.contains(
            "SOURCE_GEOGRAPHY_REFERENCE", regex=False
        )
    )

    results["has_quality_flags"] = (
        results["title_flag_count"].gt(0)
        | results["description_flag_count"].gt(0)
        | results["duplicate_text_group"]
        | results["title_description_identical"]
    )

    # These are review priorities, not automatic rejection labels.
    results["review_priority"] = "NORMAL"

    results.loc[
        ~results["has_telugu_in_both_fields"],
        "review_priority"
    ] = "HIGH"

    results.loc[
        results["has_source_geography_reference"],
        "review_priority"
    ] = "HIGH"

    results.loc[
        results["title_description_identical"],
        "review_priority"
    ] = "HIGH"

    # -----------------------------------------------------
    # 3. Overall metrics
    # -----------------------------------------------------

    total = len(results)

    def count_true(column):
        return int(results[column].fillna(False).sum())

    summary = {
        "assessment": "GrievanceHub Telugu Text Quality Assessment",
        "input_file": str(INPUT),
        "total_records": total,
        "cleaning_version": "phase5_v1",
        "language_metrics": {
            "titles_with_telugu": count_true(
                "title_contains_telugu"
            ),
            "descriptions_with_telugu": count_true(
                "description_contains_telugu"
            ),
            "records_with_telugu_in_both_fields": count_true(
                "has_telugu_in_both_fields"
            ),
            "titles_with_latin_script": count_true(
                "title_contains_latin"
            ),
            "descriptions_with_latin_script": count_true(
                "description_contains_latin"
            ),
        },
        "content_quality": {
            "identical_title_description": count_true(
                "title_description_identical"
            ),
            "duplicate_text_group_records": count_true(
                "duplicate_text_group"
            ),
            "source_geography_reference_records": count_true(
                "has_source_geography_reference"
            ),
            "records_with_any_quality_flags": count_true(
                "has_quality_flags"
            ),
            "high_priority_review_records": int(
                (results["review_priority"] == "HIGH").sum()
            ),
        },
        "text_length": {
            "average_title_characters": round(
                results["title_character_count"].mean(), 2
            ),
            "median_title_characters": round(
                results["title_character_count"].median(), 2
            ),
            "average_description_characters": round(
                results["description_character_count"].mean(), 2
            ),
            "median_description_characters": round(
                results["description_character_count"].median(), 2
            ),
        },
        "limitations": [
            "Telugu Unicode detection does not prove grammatical correctness.",
            "Latin script may represent names, acronyms, or code-switching.",
            "Geographic references are review indicators, not automatic errors.",
            "Duplicate text is not automatically invalid.",
            "Translation accuracy requires human linguistic assessment.",
            "This assessment does not approve privacy or training eligibility.",
        ],
    }

    # -----------------------------------------------------
    # 4. Category-wise report
    # -----------------------------------------------------

    category_report = (
        results.groupby(
            "target_category_code",
            dropna=False
        )
        .agg(
            record_count=("target_category_code", "size"),
            titles_with_telugu=("title_contains_telugu", "sum"),
            descriptions_with_telugu=(
                "description_contains_telugu", "sum"
            ),
            records_with_telugu_in_both=(
                "has_telugu_in_both_fields", "sum"
            ),
            identical_title_description=(
                "title_description_identical", "sum"
            ),
            duplicate_text_group_records=(
                "duplicate_text_group", "sum"
            ),
            geography_reference_records=(
                "has_source_geography_reference", "sum"
            ),
            flagged_records=("has_quality_flags", "sum"),
            average_title_length=("title_character_count", "mean"),
            average_description_length=(
                "description_character_count", "mean"
            ),
        )
        .reset_index()
    )

    percentage_columns = [
        "titles_with_telugu",
        "descriptions_with_telugu",
        "records_with_telugu_in_both",
        "identical_title_description",
        "duplicate_text_group_records",
        "geography_reference_records",
        "flagged_records",
    ]

    for column in percentage_columns:
        category_report[column + "_percent"] = (
            category_report[column]
            / category_report["record_count"] * 100
        ).round(2)

    for column in [
        "average_title_length",
        "average_description_length",
    ]:
        category_report[column] = (
            category_report[column].round(2)
        )

    category_report.to_csv(
        REPORT_DIR / "phase5_telugu_quality_by_category.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 5. Human review sample
    # -----------------------------------------------------

    # Select up to 10 records per category, prioritizing flagged
    # records. This is a review sample, not a statistically
    # representative validation set.
    review_parts = []

    for category, group in results.groupby(
        "target_category_code",
        dropna=False
    ):
        flagged = group[group["has_quality_flags"]]

        normal = group[~group["has_quality_flags"]]

        selected_flagged = flagged.sample(
            n=min(len(flagged), REVIEW_SAMPLES_PER_CATEGORY),
            random_state=RANDOM_SEED
        )

        remaining = (
            REVIEW_SAMPLES_PER_CATEGORY - len(selected_flagged)
        )

        if remaining > 0 and len(normal) > 0:
            selected_normal = normal.sample(
                n=min(len(normal), remaining),
                random_state=RANDOM_SEED
            )
            selected = pd.concat(
                [selected_flagged, selected_normal]
            )
        else:
            selected = selected_flagged

        review_parts.append(selected)

    review = pd.concat(
        review_parts,
        ignore_index=True
    ) if review_parts else pd.DataFrame()

    review_columns = [
        "target_category_code",
        "review_priority",
        "title_quality_flags",
        "description_quality_flags",
        "title_character_count",
        "description_character_count",
        "title_telugu_letter_ratio",
        "description_telugu_letter_ratio",
        "title_geographic_terms",
        "description_geographic_terms",
        "title_description_identical",
        "duplicate_text_group",
        "telugu_title_cleaned",
        "telugu_description_cleaned",
    ]

    review_columns = [
        col for col in review_columns
        if col in review.columns
    ]

    review[review_columns].to_csv(
        REPORT_DIR / "phase5_telugu_quality_review.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 6. Full record-level report
    # -----------------------------------------------------

    # Keep this file local because it contains complaint text.
    results.to_csv(
        REPORT_DIR / "phase5_telugu_quality_record_level.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # -----------------------------------------------------
    # 7. Save summary
    # -----------------------------------------------------

    summary_path = (
        REPORT_DIR / "phase5_telugu_quality_summary.json"
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
    # 8. Console output
    # -----------------------------------------------------

    print("\n--- DATASET ---")
    print(f"Total records: {total}")
    print(
        "Distinct categories:",
        results["target_category_code"].nunique()
    )

    print("\n--- TELUGU SCRIPT ---")
    for key, value in summary["language_metrics"].items():
        print(f"{key}: {value}")

    print("\n--- TEXT QUALITY ---")
    for key, value in summary["content_quality"].items():
        print(f"{key}: {value}")

    print("\n--- TEXT LENGTH ---")
    for key, value in summary["text_length"].items():
        print(f"{key}: {value}")

    print("\n--- CATEGORY DISTRIBUTION ---")
    print(
        category_report[
            [
                "target_category_code",
                "record_count",
                "records_with_telugu_in_both_percent",
                "flagged_records_percent",
            ]
        ].to_string(index=False)
    )

    print("\n--- GENERATED REPORTS ---")
    print("Summary:", summary_path)
    print(
        "Category report:",
        REPORT_DIR / "phase5_telugu_quality_by_category.csv"
    )
    print(
        "Human review sample:",
        REPORT_DIR / "phase5_telugu_quality_review.csv"
    )
    print(
        "Record-level report:",
        REPORT_DIR / "phase5_telugu_quality_record_level.csv"
    )

    print("\nAssessment completed.")
    print("No source or candidate dataset was modified.")
    print("No training eligibility was changed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
