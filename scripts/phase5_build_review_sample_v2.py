"""S1 - Rebuild the Phase 5 stratified review sample with source fields.

The original sample (phase5_prepare_human_review.py) dropped record_id and
the English source text, so translation fidelity could not be judged from
it. This script re-runs exactly the same sampling design and attaches the
missing fields.

Sampling design (unchanged from phase5_prepare_human_review.py):
  * Population: reports/phase5_telugu_quality_record_level.csv (15,374 rows)
  * Strata: target_category_code (missing values -> "UNKNOWN_CATEGORY")
  * Strata visited in sorted order (pandas groupby sort=True)
  * n_h = min(30, N_h); records drawn with DataFrame.sample(n_h,
    random_state=42), i.e. simple random sampling without replacement
    within each stratum. A stratum with N_h <= 30 is taken in full.
  * Inclusion probability pi = n_h / N_h; sampling weight = N_h / n_h.

The rebuilt sample is verified against the original sample file: the
cleaned Telugu texts must match exactly and in the same order. Text fields
are taken from the cleaning-candidate dataset by record_id and checked
against the record-level file. Nothing is written to the source datasets.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import pandas as pd

import phase5_review_common as common

TEXT_KEY_COLUMNS = ("telugu_title_cleaned", "telugu_description_cleaned")

OUTPUT_COLUMNS = [
    "record_id",
    "source_record_id",
    "review_origin",
    "in_random_sample",
    "sampling_stratum",
    "stratum_population",
    "stratum_sample_size",
    "inclusion_probability",
    "sampling_weight",
    "sample_order",
    "given_category",
    "source_category_id",
    "source_category_title",
    "source_title",
    "source_description",
    "telugu_title",
    "telugu_description",
    "telugu_title_cleaned",
    "telugu_description_cleaned",
]


def draw_stratified_sample(
    population: pd.DataFrame,
    per_stratum: int = common.SAMPLE_PER_CATEGORY,
    seed: int = common.RANDOM_SEED,
    stratum_column: str = "target_category_code",
) -> pd.DataFrame:
    """Reproduce the original stratified sampling exactly."""
    population = population.copy()
    population[stratum_column] = (
        population[stratum_column].replace("", pd.NA)
        .fillna("UNKNOWN_CATEGORY").astype(str).str.strip()
    )
    parts = []
    for stratum, group in population.groupby(stratum_column, sort=True):
        n_pop = len(group)
        n_sample = min(per_stratum, n_pop)
        picked = group.sample(n=n_sample, random_state=seed).copy()
        picked["sampling_stratum"] = stratum
        picked["stratum_population"] = n_pop
        picked["stratum_sample_size"] = n_sample
        picked["inclusion_probability"] = n_sample / n_pop
        picked["sampling_weight"] = n_pop / n_sample
        parts.append(picked)
    sample = pd.concat(parts, ignore_index=True)
    sample["sample_order"] = range(1, len(sample) + 1)
    return sample


def text_keys(df: pd.DataFrame) -> list[str]:
    return (
        df[TEXT_KEY_COLUMNS[0]].astype(str) + "\x1f"
        + df[TEXT_KEY_COLUMNS[1]].astype(str)
    ).tolist()


def build(overwrite: bool = False) -> dict:
    if common.SAMPLE_V2_PATH.exists() and not overwrite:
        raise FileExistsError(
            f"{common.SAMPLE_V2_PATH} exists; pass --overwrite to rebuild it."
        )

    population = common.read_csv(common.RECORD_LEVEL_QUALITY_PATH)
    candidate = common.read_csv(common.CANDIDATE_PATH)
    old_sample = common.read_csv(common.OLD_SAMPLE_PATH)

    sample = draw_stratified_sample(population)

    # Verification 1: same texts, same order, as the original sample.
    same_order = text_keys(sample) == text_keys(old_sample)
    same_multiset = sorted(text_keys(sample)) == sorted(text_keys(old_sample))
    if not same_order:
        raise AssertionError(
            "Rebuilt sample does not reproduce the original sample texts "
            f"(same multiset: {same_multiset})."
        )
    if not sample["record_id"].is_unique:
        raise AssertionError("Duplicate record_id in rebuilt sample.")

    # Attach text and source fields from the cleaning candidate by record_id.
    fields = [
        "record_id", "source_record_id", "source_category_id",
        "source_category_title", "source_title", "source_description",
        "telugu_title", "telugu_description",
        "telugu_title_cleaned", "telugu_description_cleaned",
    ]
    merged = sample[
        ["record_id", "sampling_stratum", "stratum_population",
         "stratum_sample_size", "inclusion_probability", "sampling_weight",
         "sample_order", "target_category_code"]
        + [c for c in TEXT_KEY_COLUMNS]
    ].rename(columns={c: f"_rl_{c}" for c in TEXT_KEY_COLUMNS}).merge(
        candidate[fields], on="record_id", how="left", validate="one_to_one"
    )
    if merged["source_title"].eq("").all() or merged["telugu_title_cleaned"].isna().any():
        raise AssertionError("Some sampled records are missing from the candidate dataset.")

    # Verification 2: the candidate's cleaned text equals the record-level text.
    for column in TEXT_KEY_COLUMNS:
        mismatch = int((merged[column] != merged[f"_rl_{column}"]).sum())
        if mismatch:
            raise AssertionError(f"{mismatch} rows differ in {column} between sources.")

    merged["given_category"] = merged["target_category_code"]
    merged["review_origin"] = common.ORIGIN_SAMPLE
    merged["in_random_sample"] = True
    out = merged[OUTPUT_COLUMNS].sort_values("sample_order", kind="stable")
    common.write_csv(out, common.SAMPLE_V2_PATH)

    strata = (
        out.groupby("sampling_stratum")
        .agg(N_h=("stratum_population", "first"), n_h=("stratum_sample_size", "first"))
        .reset_index()
    )
    summary = {
        "stage": "S1_review_sample_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "population_file": str(common.RECORD_LEVEL_QUALITY_PATH.relative_to(common.ROOT)),
        "population_records": int(len(population)),
        "sample_records": int(len(out)),
        "strata": int(len(strata)),
        "design": {
            "type": "stratified simple random sampling without replacement",
            "stratum_variable": "target_category_code (given label)",
            "per_stratum": common.SAMPLE_PER_CATEGORY,
            "rule": "n_h = min(30, N_h); strata with N_h <= 30 taken in full",
            "seed": common.RANDOM_SEED,
            "inclusion_probability": "n_h / N_h",
            "sampling_weight": "N_h / n_h",
        },
        "verification": {
            "matches_original_sample_texts_in_order": same_order,
            "record_id_unique": True,
            "candidate_text_matches_record_level_text": True,
        },
        "strata_table": strata.astype({"N_h": int, "n_h": int}).to_dict("records"),
        "fully_enumerated_strata": strata.loc[
            strata.N_h.astype(int) == strata.n_h.astype(int), "sampling_stratum"
        ].tolist(),
    }
    common.write_json(summary, common.REPORT_DIR / "sample_v2_summary.json")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    summary = build(overwrite=args.overwrite)
    print(
        f"S1 complete: {summary['sample_records']} records in "
        f"{summary['strata']} strata; matches original sample: "
        f"{summary['verification']['matches_original_sample_texts_in_order']}"
    )


if __name__ == "__main__":
    sys.exit(main())
