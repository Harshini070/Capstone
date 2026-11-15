"""S3 - Out-of-fold label-noise detection (heuristic inspired by confident learning).

This is NOT a formal or complete implementation of confident learning. It is
a transparent heuristic that ranks *suspicious-label candidates* for AI
review. A flag is not a confirmed error.

Method
------
* Records: the 15,374-record working dataset; label = given (mapped) category.
* Primary classes: every given category except the rare classes
  EMPLOYEE_GRIEVANCES, SOCIAL_WELFARE and FIRE_EMERGENCY, which stay in the
  dataset and taxonomy but are excluded from the cross-validation model
  (label_noise_status = NOT_EVALUATED_RARE_CLASS).
* Features: TF-IDF character n-grams (2-5, char_wb) over cleaned Telugu
  title + description, fitted inside each training fold only.
* Model: multinomial logistic regression, class_weight="balanced".
* Folds: StratifiedGroupKFold(k=5, shuffle=True, seed 42) grouped by
  dedup_group_id from S2, so duplicates never sit on both sides of a fold.
* Fold validity is checked on the folds actually produced: every class must
  appear in every validation fold (>= 1) and every training fold (>= 5); no
  group may appear in both training and validation; every record must get
  exactly one out-of-fold prediction. Unsupported classes are reported and
  removed (records -> NOT_EVALUATED_UNSUPPORTED_CLASS); folds are rebuilt
  until all remaining classes are supported. No split is forced.
* Flag rule: t_k = mean out-of-fold p(k|x) over records labelled k. A record
  labelled y is flagged if some k != y has p(k|x) >= t_k and p(k|x) > p(y|x).
  Suggested class = the qualifying k with the highest p(k|x).
  Rank by margin p(k|x) - p(y|x); ties broken by S2 screen_flag_count.
* Mapping concentration: for each source category, the share of its records
  flagged toward the same suggested class. >= 40% => INVESTIGATE (an AI
  investigation in Gate 3). The taxonomy is never modified.
* Synthetic self-check: on a copy of the labels, flip 5% per class to a
  random other primary class, re-run, and report recall / precision@N of the
  injected flips. Synthetic only; it does not measure real label accuracy.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline

import phase5_review_common as common

N_SPLITS = 5
MIN_TRAIN_PER_CLASS = 5
MIN_VAL_PER_CLASS = 1
CONCENTRATION_THRESHOLD = 0.40
FLIP_RATE = 0.05


def primary_classes(labels) -> list[str]:
    """Classes eligible for the cross-validation model (rare classes excluded)."""
    return sorted(set(labels) - common.RARE_CLASSES)


# ---------------------------------------------------------------------------
# Folds
# ---------------------------------------------------------------------------


def make_folds(y, groups, n_splits=N_SPLITS, seed=common.RANDOM_SEED):
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros(len(y)), y, groups))


def validate_folds(y, groups, folds, min_train=MIN_TRAIN_PER_CLASS,
                   min_val=MIN_VAL_PER_CLASS) -> dict:
    """Check the folds actually produced. Returns a JSON-safe report."""
    y = np.asarray(y)
    groups = np.asarray(groups)
    classes = sorted(set(y.tolist()))
    counts = {c: {"train": [], "validation": []} for c in classes}
    leakage = []
    seen = np.zeros(len(y), dtype=int)
    for fold_no, (train_idx, val_idx) in enumerate(folds):
        seen[val_idx] += 1
        shared = set(groups[train_idx]) & set(groups[val_idx])
        if shared:
            leakage.append({"fold": fold_no, "shared_groups": len(shared)})
        for c in classes:
            counts[c]["train"].append(int((y[train_idx] == c).sum()))
            counts[c]["validation"].append(int((y[val_idx] == c).sum()))
    unsupported = {}
    for c in classes:
        reasons = []
        if min(counts[c]["validation"]) < min_val:
            reasons.append(f"a validation fold has < {min_val} records")
        if min(counts[c]["train"]) < min_train:
            reasons.append(f"a training fold has < {min_train} records")
        if reasons:
            unsupported[c] = reasons
    groups_per_class = {
        c: int(len(set(groups[y == c].tolist()))) for c in classes
    }
    return {
        "n_folds": len(folds),
        "classes": classes,
        "groups_per_class": groups_per_class,
        "per_class_fold_counts": counts,
        "group_leakage": leakage,
        "every_record_predicted_exactly_once": bool((seen == 1).all()),
        "unsupported_classes": unsupported,
        "valid": not leakage and bool((seen == 1).all()) and not unsupported,
    }


def supported_folds(y, groups, classes, n_splits=N_SPLITS):
    """Build folds, drop unsupported classes, repeat until valid.

    Returns (mask_of_evaluated_records, folds_relative_to_mask, reports,
    dropped_classes)."""
    y = np.asarray(y)
    groups = np.asarray(groups)
    active = set(classes)
    reports, dropped = [], {}
    while active:
        mask = np.isin(y, sorted(active))
        folds = make_folds(y[mask], groups[mask], n_splits=n_splits)
        report = validate_folds(y[mask], groups[mask], folds)
        reports.append(report)
        if report["group_leakage"] or not report["every_record_predicted_exactly_once"]:
            raise AssertionError(f"Invalid folds: {report['group_leakage']}")
        if not report["unsupported_classes"]:
            return mask, folds, reports, dropped
        for c, reasons in report["unsupported_classes"].items():
            dropped[c] = reasons
            active.discard(c)
    raise AssertionError("No class could be supported by the folds.")


# ---------------------------------------------------------------------------
# Model and flags
# ---------------------------------------------------------------------------


def build_model(seed=common.RANDOM_SEED):
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2,
                        sublinear_tf=True, max_features=200_000, dtype=np.float32),
        LogisticRegression(class_weight="balanced", max_iter=2000,
                           random_state=seed),
    )


def oof_probabilities(texts, y, folds, classes):
    texts = np.asarray(texts, dtype=object)
    y = np.asarray(y)
    probs = np.full((len(y), len(classes)), np.nan)
    for train_idx, val_idx in folds:
        model = build_model()
        model.fit(texts[train_idx], y[train_idx])
        fold_classes = list(model.classes_)
        if fold_classes != list(classes):
            raise AssertionError("A training fold is missing a class.")
        probs[val_idx] = model.predict_proba(texts[val_idx])
    if np.isnan(probs).any():
        raise AssertionError("Some records did not receive an out-of-fold prediction.")
    return probs


def flag_label_noise(probs: np.ndarray, y, classes) -> pd.DataFrame:
    """Apply the flag rule. Returns one row per record."""
    classes = list(classes)
    y = np.asarray(y)
    index = {c: i for i, c in enumerate(classes)}
    y_idx = np.array([index[v] for v in y])
    thresholds = np.array([
        probs[y_idx == k, k].mean() if (y_idx == k).any() else np.inf
        for k in range(len(classes))
    ])
    p_given = probs[np.arange(len(y)), y_idx]
    qualifies = (probs >= thresholds) & (probs > p_given[:, None])
    qualifies[np.arange(len(y)), y_idx] = False
    masked = np.where(qualifies, probs, -1.0)
    best = masked.argmax(axis=1)
    flagged = qualifies.any(axis=1)
    p_suggested = np.where(flagged, probs[np.arange(len(y)), best], np.nan)
    return pd.DataFrame({
        "flagged": flagged,
        "suggested_category": np.where(flagged, np.array(classes)[best], ""),
        "p_given": p_given.round(6),
        "p_suggested": np.round(p_suggested, 6),
        "margin": np.round(p_suggested - p_given, 6),
        "threshold_suggested": np.where(flagged, thresholds[best].round(6), np.nan),
    }), dict(zip(classes, thresholds.round(6).tolist()))


def rank_flags(flags: pd.DataFrame, tie_breaker: pd.Series) -> pd.Series:
    """Rank flagged records by margin desc, then S2 flag count desc."""
    order = flags.assign(_tb=tie_breaker.values).loc[flags["flagged"]].sort_values(
        ["margin", "_tb"], ascending=[False, False], kind="stable"
    )
    rank = pd.Series(np.nan, index=flags.index)
    rank.loc[order.index] = np.arange(1, len(order) + 1)
    return rank


def mapping_concentration(source_category: pd.Series, flags: pd.DataFrame,
                          threshold=CONCENTRATION_THRESHOLD) -> pd.DataFrame:
    rows = []
    frame = pd.DataFrame({"source": source_category.values,
                          "flagged": flags["flagged"].values,
                          "suggested": flags["suggested_category"].values})
    for source, group in frame.groupby("source"):
        n = len(group)
        toward = group.loc[group.flagged, "suggested"].value_counts()
        if toward.empty:
            rows.append({"source_category_title": source, "n_records": n,
                         "top_suggested_category": "", "n_flagged_toward": 0,
                         "share": 0.0, "status": "OK", "ai_recommendation": ""})
            continue
        top, count = toward.index[0], int(toward.iloc[0])
        share = count / n
        rows.append({
            "source_category_title": source, "n_records": n,
            "top_suggested_category": top, "n_flagged_toward": count,
            "share": round(share, 4),
            "status": "INVESTIGATE" if share >= threshold else "OK",
            "ai_recommendation": "PENDING_AI_INVESTIGATION" if share >= threshold else "",
        })
    return pd.DataFrame(rows).sort_values("share", ascending=False)


def inject_flips(y, classes, rate=FLIP_RATE, seed=common.RANDOM_SEED):
    """Flip `rate` of each class to a random other class (copy of labels)."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y).copy()
    flipped = np.zeros(len(y), dtype=bool)
    for c in classes:
        idx = np.flatnonzero(y == c)
        n_flip = int(round(rate * len(idx)))
        chosen = rng.choice(idx, size=n_flip, replace=False) if n_flip else []
        others = [k for k in classes if k != c]
        for i in chosen:
            y[i] = rng.choice(others)
            flipped[i] = True
    return y, flipped


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(self_check: bool = True) -> dict:
    started = time.time()
    taxonomy_hash = common.file_sha256(common.TAXONOMY_PATH)
    data = common.read_csv(common.CANDIDATE_PATH)
    screens = common.read_csv(common.SCREENS_PATH)[
        ["record_id", "dedup_group_id", "screen_flag_count"]
    ]
    df = data.merge(screens, on="record_id", how="left", validate="one_to_one")
    if df["dedup_group_id"].eq("").any() or df["dedup_group_id"].isna().any():
        raise AssertionError("Run S2 first: some records lack dedup_group_id.")
    sample_ids = set(common.read_csv(common.SAMPLE_V2_PATH)["record_id"])

    y_all = df["target_category_code"].to_numpy()
    groups_all = df["dedup_group_id"].to_numpy()
    texts_all = (df["telugu_title_cleaned"] + " " + df["telugu_description_cleaned"]).to_numpy()
    primary = primary_classes(y_all)

    mask, folds, fold_reports, dropped = supported_folds(y_all, groups_all, primary)
    classes = sorted(set(y_all[mask]))
    probs = oof_probabilities(texts_all[mask], y_all[mask], folds, classes)
    flags, thresholds = flag_label_noise(probs, y_all[mask], classes)
    flags.index = df.index[mask]

    out = df[["record_id", "target_category_code", "source_category_title"]].rename(
        columns={"target_category_code": "given_category"})
    out["label_noise_status"] = "EVALUATED"
    out.loc[np.isin(y_all, list(common.RARE_CLASSES)), "label_noise_status"] = "NOT_EVALUATED_RARE_CLASS"
    out.loc[np.isin(y_all, list(dropped)), "label_noise_status"] = "NOT_EVALUATED_UNSUPPORTED_CLASS"
    out = out.join(flags)
    out["flagged"] = out["flagged"].fillna(False).astype(bool)
    out["suggested_category"] = out["suggested_category"].fillna("")
    tie = pd.to_numeric(df["screen_flag_count"], errors="coerce").fillna(0)
    out["flag_rank"] = rank_flags(out.fillna({"margin": -1}), tie)
    out["in_random_sample"] = out["record_id"].isin(sample_ids)
    common.write_csv(out, common.LABEL_NOISE_FLAGS_PATH)

    concentration = mapping_concentration(
        out.loc[mask, "source_category_title"], out.loc[mask]
    )
    common.write_csv(concentration, common.REPORT_DIR / "mapping_concentration.csv")
    common.write_json({
        "stage": "S3_fold_support",
        "n_splits_requested": N_SPLITS,
        "min_train_per_class": MIN_TRAIN_PER_CLASS,
        "min_validation_per_class": MIN_VAL_PER_CLASS,
        "dropped_unsupported_classes": dropped,
        "iterations": fold_reports,
    }, common.REPORT_DIR / "fold_support_report.json")

    self_check_report = None
    if self_check:
        y_flip, injected = inject_flips(y_all[mask], classes)
        f_mask, f_folds, f_reports, f_dropped = supported_folds(
            y_flip, groups_all[mask], classes)
        if f_dropped:
            raise AssertionError(f"Self-check folds dropped classes: {f_dropped}")
        f_probs = oof_probabilities(texts_all[mask], y_flip, f_folds, classes)
        f_flags, _ = flag_label_noise(f_probs, y_flip, classes)
        f_rank = rank_flags(f_flags.fillna({"margin": -1}), pd.Series(np.zeros(len(f_flags))))
        n_inj = int(injected.sum())
        detected = int((f_flags["flagged"].to_numpy() & injected).sum())
        top_n = f_rank.notna() & (f_rank <= n_inj)
        self_check_report = {
            "flip_rate": FLIP_RATE,
            "injected_flips": n_inj,
            "flagged_total": int(f_flags["flagged"].sum()),
            "injected_flips_flagged": detected,
            "recall_of_injected_flips": round(detected / n_inj, 4) if n_inj else None,
            "precision_at_N_injected": round(float((top_n.to_numpy() & injected).sum()) / n_inj, 4) if n_inj else None,
            "note": "Synthetic labels on a copy; the original dataset is untouched. Real label noise already present also produces flags, so precision here is a lower bound for detecting injected flips only and says nothing about real label accuracy.",
        }

    if common.file_sha256(common.TAXONOMY_PATH) != taxonomy_hash:
        raise AssertionError("Taxonomy file changed during S3.")

    evaluated = out[out.label_noise_status == "EVALUATED"]
    flagged = evaluated[evaluated.flagged]
    summary = {
        "stage": "S3_label_noise_detection",
        "method": "Out-of-fold label-noise heuristic inspired by confident learning (not a formal confident-learning implementation)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "records_total": int(len(out)),
        "records_evaluated": int(len(evaluated)),
        "records_not_evaluated": out["label_noise_status"].value_counts().to_dict(),
        "primary_classes": classes,
        "rare_classes_excluded": sorted(common.RARE_CLASSES),
        "unsupported_classes_dropped": dropped,
        "model": "TF-IDF char_wb 2-5 (min_df=2, sublinear_tf, max_features=200000, fitted per training fold) + LogisticRegression(class_weight=balanced, max_iter=2000)",
        "folds": {"n_splits": len(folds), "grouping": "dedup_group_id", "seed": common.RANDOM_SEED,
                  "valid": fold_reports[-1]["valid"]},
        "per_class_thresholds": thresholds,
        "flagged_records": int(len(flagged)),
        "flagged_in_random_sample": int(flagged["in_random_sample"].sum()),
        "flagged_outside_random_sample": int((~flagged["in_random_sample"]).sum()),
        "flagged_by_given_category": flagged["given_category"].value_counts().to_dict(),
        "top_given_to_suggested_pairs": (
            flagged.groupby(["given_category", "suggested_category"]).size()
            .sort_values(ascending=False).head(15)
            .rename("n").reset_index().to_dict("records")
        ),
        "mapping_concentration_investigations": int((concentration.status == "INVESTIGATE").sum()),
        "synthetic_self_check": self_check_report,
        "taxonomy_sha256_unchanged": True,
        "runtime_seconds": round(time.time() - started, 1),
        "notice": "Flags are suspicious-label candidates for AI review, not confirmed errors.",
    }
    common.write_json(summary, common.REPORT_DIR / "label_noise_summary.json")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-self-check", action="store_true")
    args = parser.parse_args(argv)
    summary = run(self_check=not args.no_self_check)
    keys = ("records_evaluated", "records_not_evaluated", "unsupported_classes_dropped",
            "flagged_records", "flagged_outside_random_sample",
            "mapping_concentration_investigations", "synthetic_self_check", "runtime_seconds")
    for key in keys:
        print(f"{key}: {summary[key]}")


if __name__ == "__main__":
    sys.exit(main())
