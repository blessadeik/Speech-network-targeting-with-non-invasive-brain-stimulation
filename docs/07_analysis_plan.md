# 07 — Analysis Plan (Freeze before Phase 3)

Preregister this. The point is to decide the statistics **before** seeing the E-field
results, so the montage rankings are honest.

## Units and normalization (state once, use everywhere)
- **tDCS:** report |E| in **V/m** at the common reference current, and **V/m per mA**.
- **TMS:** report |E| in **V/m** at SimNIBS reference dI/dt; note the coil model. If a %MSO
  mapping is used, state the coil's dI/dt-to-%MSO conversion explicitly.
- All ROI metrics computed on the central GM surface, same sampling for every condition.

## Primary metrics (per ROI × condition × head) — recomputed by [s07_extract_roi_metrics.py](../src/nibs_speech/s07_extract_roi_metrics.py)
1. `peak_E` = 99.9th percentile |E| in ROI.
2. `median_E` = 50th percentile |E| in ROI.
3. `focality_area` = GM surface area with |E| ≥ 0.5 × (whole-brain 99.9th pct |E|).
4. `ontarget_offtarget_ratio` = ROI peak_E / avoidance-region peak_E.
5. `normal_E_mean` = mean of the cortical-normal component in ROI (signed; polarity).

## Descriptive layer (always report)
- Per condition × ROI: median and IQR (and full violin/box) of each metric across heads.
- Rank conditions within each ROI by (a) peak_E, (b) focality, (c) ratio. A "practical
  winner" must be defensible on the ratio and off-target profile, not peak alone.

## Inferential layer (linear mixed models)
Software: `statsmodels` / `pymer4` (`lme4` via R optional). Random intercept per subject.

**Model A — condition effects (per ROI):**
`E_metric ~ C(condition) + (1 | subject)`
Report estimated marginal means + 95% CI per condition; pairwise contrasts among conditions
with Holm correction within each ROI × metric family.

**Model B — dose–anatomy (per ROI, pooled over or stratified by condition):**
`peak_E ~ scalp_cortex_distance + roi_curvature + csf_thickness + skull_thickness + (1 | subject)`
(standardize predictors; report standardized betas + CI). Pre-specify SCD as the primary
covariate of interest (hypothesis: greater SCD → lower peak_E, steeper for TMS than tDCS).

**Model C — modality × ROI interaction (optional, if scaled comparably):**
Compare focality between tDCS-optimized and TMS-optimized within ROI.

## Multiple comparisons
Family = {metrics} × {ROIs}. Control with Holm–Bonferroni within each metric family across
the pairwise condition contrasts. Covariate models: report CIs; treat SCD as confirmatory,
others as exploratory. State this split in the prereg.

## Effect sizes & practical thresholds
- Report differences in V/m (and %) between best and standard montage, not just p-values.
- If a putative neuromodulation threshold is used (e.g., a nominal |E| level), justify it and
  report robustness to ±20%.

## Pre-specified hypotheses (directional)
- H1: HD-tDCS and optimized montages achieve higher focality than conventional bipolar (all ROIs).
- H2: Optimized/individualized targeting reduces cross-subject variance of peak_E vs fixed
  scalp landmarks.
- H3: LMC achieves lower TMS peak_E and steeper SCD dependence than IFG/pSTG (depth effect).
- H4: TMS coil orientation materially changes ROI peak_E (orientation is not negligible).
- H5: Off-target/temporalis exposure differs across coil types (double-cone worse focality).

## Negative-result handling
A target that no tested configuration reaches selectively (ratio ≤ pre-set bound) is reported
as **not selectively reachable** — a real finding. No metric or model is dropped post hoc;
all pre-specified outputs are reported regardless of significance.

## Reproducibility outputs
- One tidy `metrics.csv` (long format: subject, roi, modality, condition, metric, value).
- Analysis notebook that regenerates every figure/number from `metrics.csv`.
- Seeds, versions, and config hashes recorded in a run manifest.
