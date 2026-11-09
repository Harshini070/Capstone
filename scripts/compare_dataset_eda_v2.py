from pathlib import Path
import json
import re
import unicodedata

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "aggregate" / "comparative_eda_v2"
CHARTS = OUT / "charts"
OUT.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)

FILES = {
    "original_english": (
        ROOT / "data/external/bengaluru_complaints.csv", "cp1252"
    ),
    "reconstructed_telugu": (
        ROOT / "data/processed/bengaluru_complaints_telugu_reconstructed.csv", "utf-8-sig"
    ),
    "experimental_telugu": (
        ROOT / "data/processed/translated_bengaluru_experimental_v1.csv", "utf-8-sig"
    ),
    "text_only_unflagged": (
        ROOT / "data/processed/translated_bengaluru_text_only_unflagged_v1.csv", "utf-8-sig"
    ),
    "translation_table": (
        ROOT / "data/interim/telugu_translation_completed.csv", "utf-8-sig"
    ),
}

TELUGU_RE = re.compile(r"[\u0C00-\u0C7F]")
LATIN_RE = re.compile(r"[A-Za-z]")
QUESTION_RE = re.compile(r"\?")
URL_RE = re.compile(r"https?://|www\.", re.I)


def read_csv(path, encoding):
    if not path.exists():
        raise FileNotFoundError(f"Required dataset not found: {path}")
    return pd.read_csv(path, encoding=encoding, low_memory=False)


def clean_text(value):
    if pd.isna(value):
        return ""
    value = unicodedata.normalize("NFC", str(value))
    return re.sub(r"\s+", " ", value).strip()


def text_metrics(series, label):
    values = series.fillna("").map(clean_text)
    nonempty = values[values.ne("")]
    lengths = nonempty.str.len()
    words = nonempty.str.split().str.len()
    normalized = values.str.lower()

    return {
        "field": label,
        "rows": int(len(values)),
        "missing_or_empty": int(values.eq("").sum()),
        "nonempty": int(values.ne("").sum()),
        "unique_nonempty_texts": int(nonempty.nunique()),
        "exact_duplicate_excess": int(len(nonempty) - nonempty.nunique()),
        "mean_characters": round(float(lengths.mean()), 2) if len(lengths) else 0,
        "median_characters": round(float(lengths.median()), 2) if len(lengths) else 0,
        "max_characters": int(lengths.max()) if len(lengths) else 0,
        "mean_words": round(float(words.mean()), 2) if len(words) else 0,
        "median_words": round(float(words.median()), 2) if len(words) else 0,
        "telugu_script_rows": int(values.map(lambda x: bool(TELUGU_RE.search(x))).sum()),
        "latin_script_rows": int(values.map(lambda x: bool(LATIN_RE.search(x))).sum()),
        "question_mark_rows": int(values.map(lambda x: bool(QUESTION_RE.search(x))).sum()),
        "url_pattern_rows": int(values.map(lambda x: bool(URL_RE.search(x))).sum()),
        "telugu_script_pct": round(
            100 * values.map(lambda x: bool(TELUGU_RE.search(x))).mean(), 2
        ) if len(values) else 0,
    }


def save_chart(x, y, title, ylabel, filename, rotation=0):
    plt.figure(figsize=(10, 5))
    plt.bar(x, y)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(CHARTS / filename, dpi=160)
    plt.close()


def main():
    datasets = {}
    for name, (path, encoding) in FILES.items():
        datasets[name] = read_csv(path, encoding)

    specs = {
        "original_english": {
            "title": "title", "description": "description"
        },
        "reconstructed_telugu": {
            "title": "title_telugu", "description": "description_telugu"
        },
        "experimental_telugu": {
            "title": "telugu_title", "description": "telugu_description"
        },
        "text_only_unflagged": {
            "title": "telugu_title", "description": "telugu_description"
        },
    }

    dataset_rows = []
    text_rows = []

    for name, df in datasets.items():
        if name == "translation_table":
            continue

        dataset_rows.append({
            "dataset": name,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "duplicate_full_rows": int(df.duplicated().sum()),
            "missing_cells": int(df.isna().sum().sum()),
            "missing_cells_pct": round(
                100 * df.isna().sum().sum() / max(1, df.size), 2
            ),
        })

        for field, column in specs[name].items():
            if column not in df.columns:
                raise ValueError(f"{name}: expected column '{column}' is missing")
            result = text_metrics(df[column], field)
            result["dataset"] = name
            result["column"] = column
            text_rows.append(result)

    dataset_df = pd.DataFrame(dataset_rows)
    text_df = pd.DataFrame(text_rows)
    dataset_df.to_csv(OUT / "dataset_overview.csv", index=False)
    text_df.to_csv(OUT / "text_quality_metrics.csv", index=False)

    # Paired English-to-Telugu length comparison where source text is available.
    paired_rows = []
    paired_specs = {
        "reconstructed_telugu": (
            "title", "title_telugu", "description", "description_telugu"
        ),
        "experimental_telugu": (
            "source_title", "telugu_title",
            "source_description", "telugu_description"
        ),
        "text_only_unflagged": (
            "source_title", "telugu_title",
            "source_description", "telugu_description"
        ),
    }

    for name, cols in paired_specs.items():
        df = datasets[name]
        for source_col, target_col, field in (
            (cols[0], cols[1], "title"),
            (cols[2], cols[3], "description"),
        ):
            source = df[source_col].fillna("").map(clean_text)
            target = df[target_col].fillna("").map(clean_text)
            valid = source.ne("") & target.ne("")
            source_len = source[valid].str.len()
            target_len = target[valid].str.len()
            ratios = target_len / source_len.replace(0, np.nan)
            paired_rows.append({
                "dataset": name,
                "field": field,
                "paired_nonempty_rows": int(valid.sum()),
                "mean_source_characters": round(float(source_len.mean()), 2) if len(source_len) else 0,
                "mean_telugu_characters": round(float(target_len.mean()), 2) if len(target_len) else 0,
                "median_telugu_to_source_char_ratio": round(float(ratios.median()), 3) if ratios.notna().any() else None,
            })

    paired_df = pd.DataFrame(paired_rows)
    paired_df.to_csv(OUT / "paired_translation_length_metrics.csv", index=False)

    # Category distribution is descriptive only; registry labels are provisional.
    category_df = datasets["experimental_telugu"]
    if {"target_category", "target_category_code"}.issubset(category_df.columns):
        category_counts = (
            category_df.groupby(["target_category_code", "target_category"], dropna=False)
            .size().reset_index(name="record_count")
            .sort_values("record_count", ascending=False)
        )
        category_counts.to_csv(OUT / "provisional_category_distribution.csv", index=False)
        top = category_counts.head(15)
        save_chart(
            top["target_category"].fillna("Unspecified"),
            top["record_count"],
            "Top 15 provisional target categories",
            "Complaint records",
            "provisional_category_distribution.png",
            rotation=55,
        )

    # Translation-table status summary.
    translations = datasets["translation_table"]
    translation_summary = {
        "rows": int(len(translations)),
        "unique_source_texts": int(translations["source_text"].nunique()),
        "translation_status_counts": {
            str(k): int(v) for k, v in
            translations["translation_status"].fillna("MISSING").value_counts().items()
        },
        "review_status_counts": {
            str(k): int(v) for k, v in
            translations["review_status"].fillna("MISSING").value_counts().items()
        },
        "telugu_script_rows": int(
            translations["telugu_translation"].fillna("").map(
                lambda x: bool(TELUGU_RE.search(clean_text(x)))
            ).sum()
        ),
    }

    with open(OUT / "translation_table_summary.json", "w", encoding="utf-8") as f:
        json.dump(translation_summary, f, ensure_ascii=False, indent=2)

    # Dataset retention relative to the original source row count.
    baseline = len(datasets["original_english"])
    retention = []
    for name in specs:
        count = len(datasets[name])
        retention.append({
            "dataset": name,
            "records": int(count),
            "retention_vs_original_pct": round(100 * count / max(1, baseline), 2),
        })
    retention_df = pd.DataFrame(retention)
    retention_df.to_csv(OUT / "dataset_retention.csv", index=False)

    save_chart(
        retention_df["dataset"],
        retention_df["records"],
        "Record retention across corpus versions",
        "Records",
        "dataset_record_retention.png",
        rotation=25,
    )

    # Text-length comparison.
    chart_data = text_df[
        (text_df["field"] == "description") &
        (text_df["dataset"].isin(specs))
    ]
    save_chart(
        chart_data["dataset"],
        chart_data["mean_characters"],
        "Mean description length by dataset version",
        "Mean characters",
        "mean_description_length.png",
        rotation=25,
    )

    summary = {
        "purpose": "Aggregate comparative EDA; not a translation-quality certification.",
        "source_provenance": "Bengaluru-origin source dataset; translated Telugu derivative, not authentic GHMC data.",
        "datasets": dataset_rows,
        "text_metrics": text_rows,
        "paired_length_metrics": paired_rows,
        "translation_table": translation_summary,
        "retention": retention,
        "output_directory": "reports/aggregate/comparative_eda_v2",
        "privacy_note": "Only aggregate metrics are exported; complaint text and PII are not written to reports.",
    }

    with open(OUT / "comparative_eda_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\nCOMPARATIVE EDA COMPLETED")
    print(f"Output directory: {OUT}")
    print("\nDataset overview:")
    print(dataset_df.to_string(index=False))
    print("\nText quality metrics:")
    print(text_df.to_string(index=False))
    print("\nPaired translation length metrics:")
    print(paired_df.to_string(index=False))
    print("\nTranslation table summary:")
    print(json.dumps(translation_summary, ensure_ascii=False, indent=2))
    print("\nCharts:")
    for path in sorted(CHARTS.glob("*.png")):
        print(f" - {path.name}")


if __name__ == "__main__":
    main()
