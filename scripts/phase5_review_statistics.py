"""S9 - Design-based estimates from the stratified random sample.

Subcommands
-----------
validate   Validate the estimators and interval methods on synthetic
           populations with known values, using the real sampling design
           (the N_h / n_h of the S1 sample). Writes statistics_validation.json.
           Real estimates are refused until this passes.
estimate   Population estimates from STRATIFIED_SAMPLE records only, plus
           given-vs-final confusion matrices (unweighted and weighted).

Design
------
Stratified simple random sampling without replacement (SRSWOR); strata =
the 20 given-label categories; N_h = stratum population, n_h = sample size,
f_h = n_h / N_h, W_h = N_h / N.

Point estimate (proportion):  p = sum_h W_h p_h
Design-based (Taylor) variance with finite-population correction:
    Var(p) = sum_h W_h^2 (1 - f_h) p_h (1 - p_h) / (n_h - 1)
    (s_h^2 = n_h p_h (1 - p_h) / (n_h - 1) for 0/1 data). A fully enumerated
    stratum (f_h = 1) contributes zero. A stratum with n_h = 1 < N_h makes
    the variance non-estimable (not present in this design).
Confidence interval (primary): Korn & Graubard (1998). Clopper-Pearson
    evaluated at the design effective sample size n_eff = p(1-p)/Var(p)
    (capped at n; n when p is 0/1), multiplied by (t_{n-1}/t_{n-H})^2.
    Chosen after synthetic validation showed the Taylor and Rao-Wu
    percentile intervals under-cover at low prevalence (coverage 0.896 and
    0.913 at a 5% true rate); see statistics_validation.json.
Cross-check 1: Rao-Wu (1988) rescaling bootstrap. In each
    stratum with f_h < 1 draw m_h = n_h - 1 units with replacement (counts
    r_hi); replicate weight factor a_hi = 1 - lambda_h + lambda_h (n_h/m_h) r_hi
    with lambda_h = sqrt(m_h (1 - f_h) / (n_h - 1)); replicate stratum mean =
    sum a_hi y_hi / sum a_hi. Fully enumerated strata are fixed. 95%
    percentile interval.
Cross-check 2: Taylor interval (p +/- 1.96 SE, clipped to [0, 1]).
Per-stratum rates: within one stratum the sample is SRSWOR, so a Wilson
    interval with finite-population correction is used: effective size
    n* = n (N - 1) / (N - n). Strata with n_h <= 10 are reported as counts
    without an interval. Fully enumerated strata are exact (census).

Flagged (non-random) records are never used: estimate() raises if any row
is not STRATIFIED_SAMPLE.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import phase5_review_common as common

Z95 = 1.959963984540054
VALIDATION_PATH = common.REPORT_DIR / "statistics_validation.json"
MIN_N_FOR_INTERVAL = 11  # n_h <= 10 -> counts only

CRITERIA = {
    "max_abs_bias": 0.005,
    "overall_coverage_range": [0.93, 0.97],
    "wilson_fpc_min_mean_coverage": 0.93,
}


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


def stratified_estimate(strata: list[tuple[int, np.ndarray]]) -> dict:
    """strata: list of (N_h, y_h) with y_h the sampled 0/1 values."""
    N = sum(N_h for N_h, _ in strata)
    p = 0.0
    var = 0.0
    estimable = True
    for N_h, y in strata:
        y = np.asarray(y, dtype=float)
        n_h = len(y)
        if n_h == 0:
            raise ValueError("empty stratum sample")
        if n_h > N_h:
            raise ValueError("sample larger than stratum population")
        W = N_h / N
        p_h = y.mean()
        p += W * p_h
        if n_h == N_h:
            continue
        if n_h == 1:
            estimable = False
            continue
        var += W ** 2 * (1 - n_h / N_h) * p_h * (1 - p_h) / (n_h - 1)
    se = math.sqrt(var) if estimable else float("nan")
    return {"estimate": p, "variance": var if estimable else float("nan"),
            "se": se, "N": N, "n": int(sum(len(y) for _, y in strata)),
            "variance_estimable": estimable}


def taylor_interval(estimate: float, se: float) -> tuple[float, float]:
    if math.isnan(se):
        return float("nan"), float("nan")
    return max(0.0, estimate - Z95 * se), min(1.0, estimate + Z95 * se)


def rao_wu_replicates(strata: list[tuple[int, np.ndarray]], reps: int,
                      rng: np.random.Generator) -> np.ndarray:
    N = sum(N_h for N_h, _ in strata)
    total = np.zeros(reps)
    for N_h, y in strata:
        y = np.asarray(y, dtype=float)
        n_h = len(y)
        W = N_h / N
        if n_h == N_h or n_h < 2:
            total += W * y.mean()
            continue
        m_h = n_h - 1
        f_h = n_h / N_h
        lam = math.sqrt(m_h * (1 - f_h) / (n_h - 1))
        r = rng.multinomial(m_h, np.full(n_h, 1.0 / n_h), size=reps)
        a = 1 - lam + lam * (n_h / m_h) * r
        total += W * (a @ y) / a.sum(axis=1)
    return total


def bootstrap_interval(strata, reps: int = 2000, seed: int = common.RANDOM_SEED):
    replicates = rao_wu_replicates(strata, reps, np.random.default_rng(seed))
    return float(np.quantile(replicates, 0.025)), float(np.quantile(replicates, 0.975))


def korn_graubard_interval(estimate: float, variance: float, n: int, n_strata: int,
                           alpha: float = 0.05) -> tuple[float, float]:
    """Korn & Graubard (1998) interval for a proportion from a complex sample.

    Clopper-Pearson interval evaluated at the design effective sample size
    n_eff = p(1-p)/Var(p) (capped at n; n_eff = n when p is 0/1 or the
    variance is 0), with the degrees-of-freedom adjustment
    n_eff * (t_{n-1} / t_{df})^2, df = n - n_strata.
    """
    from scipy.stats import beta, t

    if math.isnan(variance):
        return float("nan"), float("nan")
    p = estimate
    if variance <= 0 or p <= 0 or p >= 1:
        n_eff = float(n)
    else:
        n_eff = min(float(n), p * (1 - p) / variance)
    df = n - n_strata
    if df >= 1 and n > 1:
        n_eff *= (t.ppf(1 - alpha / 2, n - 1) / t.ppf(1 - alpha / 2, df)) ** 2
    x = n_eff * p
    low = 0.0 if x <= 0 else float(beta.ppf(alpha / 2, x, n_eff - x + 1))
    high = 1.0 if x >= n_eff else float(beta.ppf(1 - alpha / 2, x + 1, n_eff - x))
    return low, high


def wilson_fpc(x: int, n: int, N: int, z: float = Z95) -> tuple[float, float]:
    """Wilson interval with finite-population correction (effective n)."""
    if n <= 0 or n > N:
        raise ValueError("require 0 < n <= N")
    p = x / n
    if n == N:
        return p, p
    n_eff = n * (N - 1) / (N - n)
    denom = 1 + z ** 2 / n_eff
    centre = (p + z ** 2 / (2 * n_eff)) / denom
    half = z * math.sqrt(p * (1 - p) / n_eff + z ** 2 / (4 * n_eff ** 2)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------------------
# Validation on synthetic populations
# ---------------------------------------------------------------------------


def design_from_sample() -> list[tuple[str, int, int]]:
    sample = common.read_csv(common.SAMPLE_V2_PATH)
    table = sample.groupby("sampling_stratum").agg(
        N_h=("stratum_population", "first"), n_h=("stratum_sample_size", "first"))
    return [(s, int(r.N_h), int(r.n_h)) for s, r in table.iterrows()]


def synthetic_populations(design) -> dict[str, list[float]]:
    k = len(design)
    hetero = np.linspace(0.0, 1.0, k).tolist()  # includes 0 and 1 strata
    return {
        "uniform_5pct": [0.05] * k,
        "uniform_30pct": [0.30] * k,
        "heterogeneous_0_to_1": hetero,
        "boundary_all_zero": [0.0] * k,
    }


def simulate(design, rates, sims: int, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    populations = []
    for (_, N_h, n_h), rate in zip(design, rates):
        ones = int(round(rate * N_h))
        populations.append(np.array([1] * ones + [0] * (N_h - ones), dtype=float))
    N = sum(len(pop) for pop in populations)
    true_p = sum(pop.sum() for pop in populations) / N
    true_ph = [pop.mean() for pop in populations]
    estimates, cover_t, cover_b, cover_kg, width_b, width_kg = [], 0, 0, 0, [], []
    wilson_hits = np.zeros(len(design))
    wilson_eligible = np.array([n_h >= MIN_N_FOR_INTERVAL and n_h < N_h for _, N_h, n_h in design])
    for _ in range(sims):
        strata = []
        for idx, ((_, N_h, n_h), pop) in enumerate(zip(design, populations)):
            y = rng.choice(pop, size=n_h, replace=False)
            strata.append((N_h, y))
            if wilson_eligible[idx]:
                lo, hi = wilson_fpc(int(y.sum()), n_h, N_h)
                wilson_hits[idx] += lo - 1e-12 <= true_ph[idx] <= hi + 1e-12
        est = stratified_estimate(strata)
        estimates.append(est["estimate"])
        lo, hi = taylor_interval(est["estimate"], est["se"])
        cover_t += lo - 1e-12 <= true_p <= hi + 1e-12
        klo, khi = korn_graubard_interval(est["estimate"], est["variance"], est["n"], len(strata))
        cover_kg += klo - 1e-12 <= true_p <= khi + 1e-12
        width_kg.append(khi - klo)
        replicates = rao_wu_replicates(strata, reps, rng)
        blo, bhi = np.quantile(replicates, [0.025, 0.975])
        cover_b += blo - 1e-12 <= true_p <= bhi + 1e-12
        width_b.append(bhi - blo)
    wilson_cov = wilson_hits[wilson_eligible] / sims
    return {
        "true_proportion": round(float(true_p), 6),
        "mean_estimate": round(float(np.mean(estimates)), 6),
        "bias": round(float(np.mean(estimates) - true_p), 6),
        "empirical_sd": round(float(np.std(estimates)), 6),
        "coverage_korn_graubard": round(cover_kg / sims, 4),
        "mean_width_korn_graubard": round(float(np.mean(width_kg)), 6),
        "coverage_taylor": round(cover_t / sims, 4),
        "coverage_rao_wu_bootstrap": round(cover_b / sims, 4),
        "mean_width_bootstrap": round(float(np.mean(width_b)), 6),
        "wilson_fpc_mean_coverage": round(float(wilson_cov.mean()), 4) if len(wilson_cov) else None,
        "wilson_fpc_min_coverage": round(float(wilson_cov.min()), 4) if len(wilson_cov) else None,
        "degenerate": bool(true_p in (0.0, 1.0)),
    }


def hand_calculated_checks() -> dict:
    """Deterministic checks against hand-computed values."""
    strata = [(100, np.array([1] * 6 + [0] * 24)), (50, np.array([1] * 5 + [0] * 5))]
    est = stratified_estimate(strata)
    expected_p = (100 / 150) * 0.2 + (50 / 150) * 0.5
    expected_var = ((100 / 150) ** 2 * (1 - 30 / 100) * 0.2 * 0.8 / 29
                    + (50 / 150) ** 2 * (1 - 10 / 50) * 0.5 * 0.5 / 9)
    census = stratified_estimate([(10, np.array([1] * 3 + [0] * 7))])
    zero_lo, zero_hi = korn_graubard_interval(0.0, 0.0, 30, 1)
    return {
        "two_strata_estimate_ok": bool(abs(est["estimate"] - expected_p) < 1e-12),
        "two_strata_variance_ok": bool(abs(est["variance"] - expected_var) < 1e-12),
        "census_stratum_zero_variance_ok": bool(census["variance"] == 0.0),
        "wilson_census_exact_ok": bool(wilson_fpc(3, 10, 10) == (0.3, 0.3)),
        "korn_graubard_zero_events_ok": bool(zero_lo == 0.0 and 0.0 < zero_hi < 0.2),
    }


def validate(sims: int = 1000, reps: int = 500, seed: int = common.RANDOM_SEED) -> dict:
    design = design_from_sample()
    results = {}
    for offset, (name, rates) in enumerate(synthetic_populations(design).items()):
        results[name] = simulate(design, rates, sims, reps, seed + offset)
    hand = hand_calculated_checks()
    failures = [k for k, ok in hand.items() if not ok]
    lo, hi = CRITERIA["overall_coverage_range"]
    cross_check_notes = []
    for name, r in results.items():
        if abs(r["bias"]) > CRITERIA["max_abs_bias"]:
            failures.append(f"{name}: bias {r['bias']}")
        if r["degenerate"]:
            if r["coverage_korn_graubard"] < 1.0:
                failures.append(f"{name}: Korn-Graubard must cover a degenerate proportion")
            continue
        # Primary interval method: pass/fail criterion.
        if not lo <= r["coverage_korn_graubard"] <= hi:
            failures.append(f"{name}: coverage_korn_graubard {r['coverage_korn_graubard']} outside {lo}-{hi}")
        # Cross-checks: reported, not pass/fail.
        for key in ("coverage_taylor", "coverage_rao_wu_bootstrap"):
            if not lo <= r[key] <= hi:
                cross_check_notes.append(f"{name}: {key} {r[key]} outside {lo}-{hi}")
        if r["wilson_fpc_mean_coverage"] is not None and \
                r["wilson_fpc_mean_coverage"] < CRITERIA["wilson_fpc_min_mean_coverage"]:
            failures.append(f"{name}: Wilson-FPC mean coverage {r['wilson_fpc_mean_coverage']}")
    return {
        "stage": "S9_statistics_validation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "design": [{"stratum": s, "N_h": N, "n_h": n} for s, N, n in design],
        "simulations_per_population": sims,
        "bootstrap_replicates_per_simulation": reps,
        "seed": seed,
        "criteria": CRITERIA,
        "hand_calculated_checks": hand,
        "results": results,
        "primary_interval_method": "Korn-Graubard (1998) design-effective-size Clopper-Pearson",
        "cross_check_methods": ["Taylor (normal, design variance with FPC)", "Rao-Wu rescaling bootstrap, percentile"],
        "cross_check_notes": cross_check_notes,
        "failures": failures,
        "passed": not failures,
        "method_history": "v1 used the Rao-Wu percentile bootstrap as the primary interval; its synthetic coverage at a 5% true rate was 0.913 (Taylor 0.896), below the 0.93 criterion, so the primary method was changed to Korn-Graubard. Taylor and Rao-Wu are kept as cross-checks.",
        "note": "Synthetic populations with exactly known proportions, sampled with the real S1 design.",
    }


# ---------------------------------------------------------------------------
# Real estimates
# ---------------------------------------------------------------------------

METRICS = {
    "translation_pass_rate": lambda r: r["translation_fidelity"] == "PASS",
    "translation_partial_rate": lambda r: r["translation_fidelity"] == "PARTIAL",
    "translation_fail_rate": lambda r: r["translation_fidelity"] == "FAIL",
    "category_error_rate": lambda r: r["category_correctness"] == "INCORRECT",
    "relabel_rate": lambda r: r["review_decision"] == "RELABEL",
    "rejection_rate": lambda r: r["review_decision"] in ("REJECT", "ESCALATE"),
    "ambiguity_rate": lambda r: r["review_decision"] == "AMBIGUOUS",
    "privacy_flag_rate": lambda r: r["privacy_assessment"] != "NO_OBVIOUS_PII",
}


def sample_rows(final: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    rows = final.merge(queue, on="record_id", how="inner", validate="one_to_one")
    if (rows["review_origin"] != common.ORIGIN_SAMPLE).any():
        raise ValueError("Only STRATIFIED_SAMPLE records may be used for population estimates.")
    return rows


def estimate_metric(rows: pd.DataFrame, indicator, reps=2000) -> list[dict]:
    rows = rows.assign(_y=rows.apply(indicator, axis=1).astype(int))
    strata = []
    out = []
    for stratum, g in rows.groupby("sampling_stratum"):
        N_h, n_h = int(g["stratum_population"].iloc[0]), len(g)
        x = int(g["_y"].sum())
        strata.append((N_h, g["_y"].to_numpy()))
        record = {"scope": stratum, "N_h": N_h, "n_h": n_h, "count": x,
                  "estimate": round(x / n_h, 4)}
        if n_h == N_h:
            record.update(ci_low="", ci_high="", ci_method="census (stratum fully reviewed)")
        elif n_h < MIN_N_FOR_INTERVAL:
            record.update(ci_low="", ci_high="", ci_method="none: n_h <= 10, counts only")
        else:
            lo, hi = wilson_fpc(x, n_h, N_h)
            record.update(ci_low=round(lo, 4), ci_high=round(hi, 4), ci_method="Wilson with FPC")
        out.append(record)
    est = stratified_estimate(strata)
    klo, khi = korn_graubard_interval(est["estimate"], est["variance"], est["n"], len(strata))
    blo, bhi = bootstrap_interval(strata, reps=reps)
    tlo, thi = taylor_interval(est["estimate"], est["se"])
    out.insert(0, {"scope": "OVERALL", "N_h": est["N"], "n_h": est["n"],
                   "count": int(rows["_y"].sum()), "estimate": round(est["estimate"], 4),
                   "se_taylor": round(est["se"], 5), "ci_low": round(klo, 4), "ci_high": round(khi, 4),
                   "ci_method": "Korn-Graubard 95% (primary)",
                   "rao_wu_bootstrap_ci": f"[{blo:.4f}, {bhi:.4f}]",
                   "taylor_ci": f"[{tlo:.4f}, {thi:.4f}]"})
    return out


def confusion(rows: pd.DataFrame) -> pd.DataFrame:
    final_cat = np.where(rows["review_decision"].eq("RELABEL") & rows["corrected_category"].ne(""),
                         rows["corrected_category"], rows["given_category"])
    frame = pd.DataFrame({"given_category": rows["given_category"], "final_category": final_cat,
                          "weight": pd.to_numeric(rows["sampling_weight"])})
    unweighted = frame.groupby(["given_category", "final_category"]).size().rename("count_unweighted")
    weighted = frame.groupby(["given_category", "final_category"])["weight"].sum().rename("estimated_population_count")
    return pd.concat([unweighted, weighted.round(1)], axis=1).reset_index()


def estimate(reps: int = 2000) -> None:
    if not VALIDATION_PATH.exists() or not json.loads(VALIDATION_PATH.read_text(encoding="utf-8"))["passed"]:
        raise SystemExit("Statistics validation has not passed; real estimates are refused.")
    final = common.read_csv(common.REVIEW_FINAL_PATH)
    queue = common.read_csv(common.REVIEW_QUEUE_PATH)
    queue = queue[queue["review_origin"] == common.ORIGIN_SAMPLE]
    data = common.read_csv(common.CANDIDATE_PATH)[["record_id", "target_category_code"]]
    rows = sample_rows(final, queue).merge(
        data.rename(columns={"target_category_code": "given_category"}), on="record_id")
    records = []
    for name, indicator in METRICS.items():
        for rec in estimate_metric(rows, indicator, reps=reps):
            records.append({"metric": name, **rec})
    common.write_csv(pd.DataFrame(records), common.REPORT_DIR / "population_estimates.csv")
    common.write_csv(confusion(rows), common.REPORT_DIR / "given_vs_corrected_confusion.csv")
    print(f"Wrote {len(records)} estimate rows from {len(rows)} sample records.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--sims", type=int, default=1000)
    v.add_argument("--reps", type=int, default=500)
    e = sub.add_parser("estimate")
    e.add_argument("--reps", type=int, default=2000)
    args = parser.parse_args(argv)
    if args.command == "validate":
        report = validate(sims=args.sims, reps=args.reps)
        common.write_json(report, VALIDATION_PATH)
        print(json.dumps({"passed": report["passed"], "failures": report["failures"],
                          "results": report["results"]}, indent=1))
        return 0 if report["passed"] else 1
    estimate(reps=args.reps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
