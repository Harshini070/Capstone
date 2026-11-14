
from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "processed" / "translated_bengaluru_preprocessed_v1.csv"
OUTPUT = ROOT / "reports"

OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT, encoding="utf-8-sig", low_memory=False)

text_columns = ["telugu_title", "telugu_description"]

for col in text_columns:
    if col not in df.columns:
        raise ValueError(f"Missing required column: {col}")

def inspect_text(value):
    text = str(value) if pd.notna(value) else ""

    trailing_dots = bool(re.search(r"\.{5,}\s*$", text))
    internal_dots = bool(re.search(r"\S\.{5,}\S", text))
    dot_count = len(re.findall(r"\.{5,}", text))

    cleaned_preview = re.sub(r"\.{5,}\s*$", "", text).strip()

    return {
        "trailing_dots": trailing_dots,
        "internal_dots": internal_dots,
        "long_dot_sequences": dot_count,
        "original_length": len(text),
        "preview_length": len(cleaned_preview),
        "preview": cleaned_preview,
    }

rows = []

for index, row in df.iterrows():
    title = inspect_text(row["telugu_title"])
    description = inspect_text(row["telugu_description"])

    rows.append({
        "source_row": index + 1,
        "record_id": row.get("record_id", ""),
        "category": row.get("target_category_code", ""),
        "title_trailing_dots": title["trailing_dots"],
        "description_trailing_dots": description["trailing_dots"],
        "title_internal_dots": title["internal_dots"],
        "description_internal_dots": description["internal_dots"],
        "title_dot_sequences": title["long_dot_sequences"],
        "description_dot_sequences": description["long_dot_sequences"],
        "original_title": str(row["telugu_title"]),
        "original_description": str(row["telugu_description"]),
        "title_preview_without_trailing_dots": title["preview"],
        "description_preview_without_trailing_dots": description["preview"],
    })

report = pd.DataFrame(rows)

report.to_csv(
    OUTPUT / "phase5_translation_artifact_review.csv",
    index=False,
    encoding="utf-8-sig"
)

summary = {
    "total_records": len(report),
    "title_trailing_dot_records": int(
        report["title_trailing_dots"].sum()
    ),
    "description_trailing_dot_records": int(
        report["description_trailing_dots"].sum()
    ),
    "title_internal_dot_records": int(
        report["title_internal_dots"].sum()
    ),
    "description_internal_dot_records": int(
        report["description_internal_dots"].sum()
    ),
    "records_with_any_trailing_dot_artifact": int(
        (
            report["title_trailing_dots"]
            | report["description_trailing_dots"]
        ).sum()
    ),
}

import json

(OUTPUT / "phase5_translation_artifact_summary.json").write_text(
    json.dumps(summary, indent=4, ensure_ascii=False),
    encoding="utf-8"
)

print("TRANSLATION ARTIFACT ANALYSIS")
print("=" * 55)

for key, value in summary.items():
    print(f"{key}: {value}")

print("\nFiles generated:")
print(OUTPUT / "phase5_translation_artifact_review.csv")
print(OUTPUT / "phase5_translation_artifact_summary.json")
print("\nOriginal dataset was not modified.")
