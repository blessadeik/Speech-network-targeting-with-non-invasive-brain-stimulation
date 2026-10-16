"""s08 — group-level analysis and figures across all subjects.

    python src/nibs_speech/s08_group_analysis.py            # (no SimNIBS needed here)

Aggregates every results/roi_metrics/<subject>/metrics.csv (+ roi_covariates.csv), then
per docs/07_analysis_plan.md:
  - pools into results/group/metrics_all.csv (tidy long) and a wide summary
  - descriptive tables (median/IQR per condition × ROI × metric)
  - Model A: condition effects per ROI (mixed model, subject random intercept)
  - Model B: dose–anatomy regression (peak_E ~ scalp_cortex_distance + curvature)
  - draft figures into results/figures/

Runs with plain python if statsmodels/seaborn are installed there; models degrade gracefully
to descriptive-only if statsmodels is missing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utils import abspath, get_logger, load_paths

log = get_logger("s08")


def gather_metrics() -> pd.DataFrame:
    root = abspath(load_paths()["results"]["roi_metrics"])
    frames = []
    for csv in root.glob("*/metrics.csv"):
        frames.append(pd.read_csv(csv))
    if not frames:
        raise FileNotFoundError(f"No metrics.csv under {root}. Run s07 per subject first.")
    return pd.concat(frames, ignore_index=True)


def gather_covariates() -> pd.DataFrame:
    root = abspath(load_paths()["results"]["roi_metrics"])
    frames = [pd.read_csv(c) for c in root.glob("*/roi_covariates.csv")]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def descriptive(df: pd.DataFrame, out_dir: Path) -> None:
    summ = (df.groupby(["modality", "condition", "roi", "metric"])["value"]
              .agg(["count", "median",
                    lambda s: s.quantile(0.25), lambda s: s.quantile(0.75)])
              .rename(columns={"<lambda_0>": "q25", "<lambda_1>": "q75"})
              .reset_index())
    summ.to_csv(out_dir / "descriptive_summary.csv", index=False)
    log.info("Wrote descriptive_summary.csv (%d rows)", len(summ))


def model_A_condition(df: pd.DataFrame, out_dir: Path) -> None:
    """Per-ROI condition effects on peak_E via mixed model (subject random intercept)."""
    try:
        import statsmodels.formula.api as smf
    except Exception:
        log.warning("statsmodels not available; skipping Model A. (install in this python)")
        return
    peak = df[df.metric == "peak_E"].copy()
    results = []
    for roi, g in peak.groupby("roi"):
        if g["condition"].nunique() < 2 or g["subject"].nunique() < 3:
            continue
        try:
            m = smf.mixedlm("value ~ C(condition)", g, groups=g["subject"]).fit(reml=True)
            for name, coef, pval, ci_l, ci_u in zip(
                    m.params.index, m.params.values, m.pvalues.values,
                    m.conf_int()[0].values, m.conf_int()[1].values):
                results.append(dict(roi=roi, term=name, coef=coef, pval=pval,
                                    ci_low=ci_l, ci_high=ci_u))
        except Exception as exc:  # noqa: BLE001
            log.warning("Model A failed for ROI %s: %s", roi, exc)
    if results:
        pd.DataFrame(results).to_csv(out_dir / "modelA_condition_effects.csv", index=False)
        log.info("Wrote modelA_condition_effects.csv")


def model_B_dose_anatomy(df: pd.DataFrame, cov: pd.DataFrame, out_dir: Path) -> None:
    """peak_E ~ scalp_cortex_distance + curvature_proxy, subject random intercept."""
    if cov.empty:
        log.warning("No covariates; skipping Model B.")
        return
    try:
        import statsmodels.formula.api as smf
    except Exception:
        log.warning("statsmodels not available; skipping Model B.")
        return
    peak = df[df.metric == "peak_E"].merge(cov, on=["subject", "roi"], how="left")
    peak = peak.dropna(subset=["scalp_cortex_distance_mm"])
    results = []
    for (modality, roi), g in peak.groupby(["modality", "roi"]):
        if g["subject"].nunique() < 4:
            continue
        g = g.assign(scd=_z(g["scalp_cortex_distance_mm"]),
                     curv=_z(g["curvature_proxy"]))
        try:
            m = smf.mixedlm("value ~ scd + curv", g, groups=g["subject"]).fit(reml=True)
            for term in ["scd", "curv"]:
                results.append(dict(modality=modality, roi=roi, term=term,
                                    beta_std=m.params.get(term, np.nan),
                                    pval=m.pvalues.get(term, np.nan)))
        except Exception as exc:  # noqa: BLE001
            log.warning("Model B failed for %s/%s: %s", modality, roi, exc)
    if results:
        pd.DataFrame(results).to_csv(out_dir / "modelB_dose_anatomy.csv", index=False)
        log.info("Wrote modelB_dose_anatomy.csv")


def _z(s: pd.Series) -> pd.Series:
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd else s * 0.0


def draft_figures(df: pd.DataFrame, cov: pd.DataFrame, fig_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns
    except Exception:
        log.warning("matplotlib/seaborn unavailable; skipping figures.")
        return
    peak = df[df.metric == "peak_E"]
    if not peak.empty:
        for roi, g in peak.groupby("roi"):
            plt.figure(figsize=(8, 4))
            sns.violinplot(data=g, x="condition", y="value", cut=0, inner="quartile")
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("peak |E| (V/m)")
            plt.title(f"On-target peak E-field — {roi}")
            plt.tight_layout()
            plt.savefig(fig_dir / f"fig_peakE_{roi}.png", dpi=150)
            plt.close()
    # dose–anatomy scatter
    if not cov.empty:
        merged = peak.merge(cov, on=["subject", "roi"], how="left")
        if "scalp_cortex_distance_mm" in merged:
            plt.figure(figsize=(6, 5))
            sns.scatterplot(data=merged, x="scalp_cortex_distance_mm", y="value",
                            hue="roi", style="modality")
            plt.ylabel("peak |E| (V/m)")
            plt.xlabel("scalp-to-cortex distance (mm)")
            plt.title("Dose vs anatomy")
            plt.tight_layout()
            plt.savefig(fig_dir / "fig_dose_vs_scd.png", dpi=150)
            plt.close()
    log.info("Figures written to %s", fig_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--figures", action="store_true", help="also draft figures")
    args = ap.parse_args()

    out_dir = abspath(load_paths()["results"]["group"])
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = abspath(load_paths()["results"]["figures"])
    fig_dir.mkdir(parents=True, exist_ok=True)

    df = gather_metrics()
    cov = gather_covariates()
    df.to_csv(out_dir / "metrics_all.csv", index=False)
    log.info("Pooled %d metric rows from %d subjects.", len(df), df["subject"].nunique())

    descriptive(df, out_dir)
    model_A_condition(df, out_dir)
    model_B_dose_anatomy(df, cov, out_dir)
    if args.figures:
        draft_figures(df, cov, fig_dir)
    log.info("Group analysis done -> %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
