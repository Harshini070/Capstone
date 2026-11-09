from pathlib import Path
from collections import Counter
import json
import re
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/bengaluru_complaints_telugu_reconstructed.csv"
OUT = ROOT / "reports/aggregate/preprocessing_p2_v2"
OUT.mkdir(parents=True, exist_ok=True)

FIELDS = {
    "telugu_title": "title_telugu",
    "telugu_description": "description_telugu",
}

TELUGU = re.compile(r"[\u0C00-\u0C7F]")
LATIN = re.compile(r"[A-Za-z]")
REPEATED_PUNCT = re.compile(r"([.,!?;:])\1{1,}")
LONG_PERIOD = re.compile(r"\.{10,}")
URL = re.compile(r"https?://|www\.", re.I)


def has_repeated_words(text):
    words = text.split()
    for n in range(2, min(8, len(words) // 2) + 1):
        for i in range(len(words) - 2 * n + 1):
            if words[i:i+n] == words[i+n:i+2*n]:
                return True
    return False


def inspect(series):
    text = series.fillna("").astype(str)
    result = []

    for value in text:
        length = len(value)
        punctuation = sum(
            unicodedata.category(ch).startswith("P") for ch in value
        )
        result.append({
            "empty": not value.strip(),
            "has_telugu": bool(TELUGU.search(value)),
            "has_latin": bool(LATIN.search(value)),
            "repeated_punctuation": bool(REPEATED_PUNCT.search(value)),
            "long_period_run": bool(LONG_PERIOD.search(value)),
            "period_dominated": bool(value) and value.count(".") / max(1, length) >= 0.5,
            "punctuation_density": punctuation / length if length else 0.0,
            "high_punctuation_density": bool(value) and punctuation / max(1, length) >= 0.5,
            "repeated_word_sequence": has_repeated_words(value),
            "contains_url": bool(URL.search(value)),
            "contains_control_character": any(
                unicodedata.category(ch) == "Cc" and ch not in "\t\n\r"
                for ch in value
            ),
            "contains_invisible_character": any(
                unicodedata.category(ch) == "Cf" for ch in value
            ),
            "over_500_characters": length > 500,
            "characters": length,
        })

    return pd.DataFrame(result)


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    df = pd.read_csv(SOURCE, encoding="utf-8-sig", low_memory=False)
    if not {"record_id", "source_row_id"}.intersection(df.columns):
        raise ValueError("Neither record_id nor source_row_id is available for traceability")

    field_summaries = {}
    record_flags = []

    for field, column in FIELDS.items():
        if column not in df.columns:
            raise ValueError(f"Missing column: {column}")

        metrics = inspect(df[column])
        field_summaries[field] = {
            "records": int(len(metrics)),
            "anomaly_counts": {
                col: int(metrics[col].sum())
                for col in metrics.columns
                if metrics[col].dtype == bool
            },
            "mean_characters": round(float(metrics["characters"].mean()), 2),
            "median_characters": round(float(metrics["characters"].median()), 2),
            "max_characters": int(metrics["characters"].max()),
            "mean_punctuation_density": round(
                float(metrics["punctuation_density"].mean()), 4
            ),
            "high_punctuation_density_row_fraction": round(
                float(metrics["high_punctuation_density"].mean()), 4
            ),
        }

        flags = metrics[["empty", "repeated_punctuation", "long_period_run", "period_dominated", "high_punctuation_density", "repeated_word_sequence", "contains_url", "contains_control_character", "contains_invisible_character", "over_500_characters"]].any(axis=1)
        record_flags.append(flags.rename(field))

    combined = pd.concat(record_flags, axis=1)
    combined["any_field_flagged"] = combined.any(axis=1)
    combined["both_fields_flagged"] = combined.iloc[:, :2].all(axis=1)

    overlap = {
        "records": int(len(df)),
        "title_flagged": int(combined["telugu_title"].sum()),
        "description_flagged": int(combined["telugu_description"].sum()),
        "either_field_flagged": int(combined["any_field_flagged"].sum()),
        "both_fields_flagged": int(combined["both_fields_flagged"].sum()),
        "neither_field_flagged": int((~combined["any_field_flagged"]).sum()),
    }

    # Aggregate-only outputs. No complaint text or record-level IDs exported.
    pd.DataFrame([
        {
            "field": field,
            "metric": metric,
            "count": count,
        }
        for field, values in field_summaries.items()
        for metric, count in values["anomaly_counts"].items()
    ]).to_csv(OUT / "p2_anomaly_counts.csv", index=False)

    summary = {
        "experiment": "P2 punctuation and formatting anomaly detection",
        "source": str(SOURCE.relative_to(ROOT)),
        "field_summaries": field_summaries,
        "record_overlap": overlap,
        "methodology": {
            "repeated_punctuation": "Two or more consecutive identical ASCII punctuation characters",
            "long_period_run": "At least 10 consecutive ASCII periods",
            "period_dominated": "At least 50 percent of code points are ASCII periods",
            "high_punctuation_density": "At least 50 percent of code points are Unicode punctuation",
            "repeated_word_sequence": "Repeated consecutive sequence of 2 to 7 whitespace-separated tokens",
            "release_effect": "None; detection only",
        },
        "limitations": [
            "Heuristic flags do not prove semantic translation errors.",
            "Latin characters may be valid names, abbreviations or technical terms.",
            "Punctuation thresholds are anomaly indicators, not automatic deletion rules.",
            "No text or record-level identifiers are exported.",
        ],
        "release_status": "HOLD_PENDING_TRANSLATION_QUALITY_REVIEW",
    }

    with open(OUT / "p2_anomaly_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("P2 ANOMALY AUDIT COMPLETED")
    print("Output:", OUT)
    print("\nField summaries:")
    for field, values in field_summaries.items():
        print(f"\n{field}:")
        for key, value in values.items():
            print(f"  {key}: {value}")

    print("\nRecord-level overlap:")
    for key, value in overlap.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
