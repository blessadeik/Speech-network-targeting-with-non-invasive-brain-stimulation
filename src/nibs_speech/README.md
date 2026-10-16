# Pipeline (`src/nibs_speech`)

Run everything with the **SimNIBS bundled interpreter** (`simnibs_python`) except `s08`
(plain `python` with pandas/statsmodels is fine). Each stage writes a `run_manifest.json`
next to its outputs for reproducibility.

| Stage | Script | Input | Output |
|---|---|---|---|
| 0 | [s00_setup_check.py](s00_setup_check.py) | — | toolchain checklist |
| 1 | [s01_make_headmodel.py](s01_make_headmodel.py) | T1(+T2) | `data/m2m/m2m_<sub>` |
| 2 | [s02_define_rois.py](s02_define_rois.py) | head model + `config/rois.yaml` | ROI masks + covariates |
| 3 | [s03_run_tdcs_montages.py](s03_run_tdcs_montages.py) | `config/montages.yaml` | tDCS E-field meshes |
| 4 | [s04_run_tms_grid.py](s04_run_tms_grid.py) | `config/coils.yaml` | TMS grid E-field meshes |
| 5 | [s05_optimize_tdcs.py](s05_optimize_tdcs.py) | leadfield + constraints | optimized tDCS montage |
| 6 | [s06_optimize_tms.py](s06_optimize_tms.py) | coil + target | optimal coil pose |
| 7 | [s07_extract_roi_metrics.py](s07_extract_roi_metrics.py) | meshes + masks | `metrics.csv` (per subject) |
| 8 | [s08_group_analysis.py](s08_group_analysis.py) | all `metrics.csv` | group tables + figures |

## Per-subject run (once head model exists)
```bash
S=ernie
simnibs_python src/nibs_speech/s02_define_rois.py       --subject $S
simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --subject $S
simnibs_python src/nibs_speech/s04_run_tms_grid.py      --subject $S --roi L_IFG
simnibs_python src/nibs_speech/s05_optimize_tdcs.py     --subject $S --build-leadfield
simnibs_python src/nibs_speech/s05_optimize_tdcs.py     --subject $S
simnibs_python src/nibs_speech/s06_optimize_tms.py      --subject $S --roi L_IFG
simnibs_python src/nibs_speech/s07_extract_roi_metrics.py --subject $S
# after all subjects:
python src/nibs_speech/s08_group_analysis.py --figures
```

## ⚠️ `API-CHECK` markers
The scripts follow the SimNIBS 4.x Python API, but they were written without a live SimNIBS
install to execute against. Every spot where the exact attribute/filename/tag should be
confirmed against *your* installed version is flagged with a `# API-CHECK` comment. Work
through them during the **Week-1 Ernie smoke test** — fix once, and the whole batch run
inherits it. Start with `s00_setup_check.py`, then `s01`→`s07` on Ernie before scaling to N heads.

## Design choices
- **Config-first:** targets/montages/coils live in `config/*.yaml`, not in code.
- **Lazy SimNIBS imports:** `utils.py` imports fine under plain python for editing/linting;
  `simnibs` is imported only inside the functions that need it.
- **One tidy CSV** (`metrics.csv`) is the analysis atom — everything downstream reads it.
