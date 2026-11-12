# Pipeline (`src/nibs_speech`), v0.2

Run with `simnibs_python` (s00 to s07). s08 and later analysis run in the analysis env.
Every stage writes `run_manifest.json`. Scripts take `--head` (alias `--subject`).

| Stage | Script | Output |
|---|---|---|
| 0 | s00_setup_check.py [--head ernie] | verify_report.md (API-CHECK sweep; local only) |
| 1 | s01_make_headmodel.py | data/m2m/m2m_<head> |
| 1b | s01b_lesion.py (Stage 5, to write) | ARC `_lesion` and `_filled` heads |
| 2 | s02_define_rois.py | roi_masks.npz (primary, homolog, variants), roi_covariates.csv, roi_centres.csv |
| 3 | s03_run_tdcs_montages.py | results/tdcs/<head>/<family>__<roi>[__<cond_set>] |
| 4 | s04_run_tms_grid.py (--sweep-at-optimum / --grid / --quick) | results/tms/<head>/<roi>/<coil>/<mode> |
| 5 | s05_optimize_tdcs.py (--build-leadfield, --ksweep) | results/optimization, results/ksweep |
| 6 | s06_optimize_tms.py | best_matsimnibs.npy + optimized field |
| 7 | s07_extract_roi_metrics.py | results/roi_metrics/<head>/metrics.csv |
| 8 | s08_group_analysis.py | descriptive pooling (models in Stage 11) |

## One head, end to end
```bash
H=ernie
simnibs_python src/nibs_speech/s00_setup_check.py --head $H
simnibs_python src/nibs_speech/s02_define_rois.py --head $H
simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --head $H
simnibs_python src/nibs_speech/s05_optimize_tdcs.py --head $H --build-leadfield
simnibs_python src/nibs_speech/s05_optimize_tdcs.py --head $H --ksweep
for R in L_IFG L_pSTG L_dLMC L_vLMC; do
  simnibs_python src/nibs_speech/s06_optimize_tms.py --head $H --roi $R
  simnibs_python src/nibs_speech/s04_run_tms_grid.py --head $H --roi $R --sweep-at-optimum
done
simnibs_python src/nibs_speech/s07_extract_roi_metrics.py --head $H
```
ARC lesion heads pick the `lesion_csf` conductivity set automatically; add
`--cond-set lesion_0p5` or `lesion_1p0` for the sweep.
