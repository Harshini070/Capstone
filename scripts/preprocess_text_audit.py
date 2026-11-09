from pathlib import Path
import json
import re
import unicodedata

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/bengaluru_complaints_telugu_reconstructed.csv"
OUT = ROOT / "reports/aggregate/preprocessing_audit_v1"
OUT.mkdir(parents=True, exist_ok=True)

FIELDS = {
    "english_title": "title",
    "english_description": "description",
    "telugu_title": "title_telugu",
    "telugu_description": "description_telugu",
}

TELUGU = re.compile(r"[\u0C00-\u0C7F]")
LATIN = re.compile(r"[A-Za-z]")
REPEATED_DOTS = re.compile(r"\.{2,}")
INVISIBLE = {"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"}


def normalize_text(value):
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFC", str(value))
    text = "".join(ch for ch in text if ch not in INVISIBLE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def inspect_field(series):
    raw = series.fillna("").astype(str)
    normalized = raw.map(normalize_text)

    raw_lengths = raw.str.len()
    clean_lengths = normalized.str.len()

    return {
        "records": int(len(raw)),
        "empty_before": int(raw.str.strip().eq("").sum()),
        "empty_after": int(normalized.eq("").sum()),
        "unicode_or_whitespace_changed": int(raw.ne(normalized).sum()),
        "mean_length_before": round(float(raw_lengths.mean()), 2),
        "mean_length_after": round(float(clean_lengths.mean()), 2),
        "unique_before": int(raw.nunique()),
        "unique_after": int(normalized.nunique()),
        "telugu_script_after": int(normalized.map(lambda x: bool(TELUGU.search(x))).sum()),
        "latin_script_after": int(normalized.map(lambda x: bool(LATIN.search(x))).sum()),
        "repeated_period_rows": int(normalized.map(lambda x: bool(REPEATED_DOTS.search(x))).sum()),
        "period_dominated_rows": int(
            normalized.map(
                lambda x: bool(x) and x.count(".") / len(x) >= 0.5
            ).sum()
        ),
    }


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    df = pd.read_csv(SOURCE, encoding="utf-8-sig", low_memory=False)

    results = {}
    for label, column in FIELDS.items():
        if column not in df.columns:
            raise ValueError(f"Missing required field: {column}")
        results[label] = inspect_field(df[column])

    # Safe preprocessing ablation: raw versus NFC + whitespace normalization.
    # No punctuation deletion, translation rewriting, or record deletion.
    summary = {
        "experiment": "P1 Unicode NFC and whitespace normalization",
        "source": str(SOURCE.relative_to(ROOT)),
        "records": int(len(df)),
        "normalization": [
            "Unicode NFC",
            "Removal of selected invisible formatting characters",
            "Whitespace collapse and trimming",
        ],
        "not_performed": [
            "No punctuation deletion",
            "No translation correction",
            "No complaint deletion",
            "No PII clearance",
            "No training eligibility approval",
        ],
        "field_metrics": results,
        "release_status": "HOLD_PENDING_TRANSLATION_AND_HUMAN_REVIEW",
    }

    with open(OUT / "preprocessing_audit_v1.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    pd.DataFrame([
        {"field": field, **metrics}
        for field, metrics in results.items()
    ]).to_csv(OUT / "preprocessing_metrics_v1.csv", index=False)

    print("PREPROCESSING AUDIT COMPLETED")
    print("Records:", len(df))
    print("Output:", OUT)
    print(pd.DataFrame([
        {"field": field, **metrics}
        for field, metrics in results.items()
    ]).to_string(index=False))


if __name__ == "__main__":
    main()
