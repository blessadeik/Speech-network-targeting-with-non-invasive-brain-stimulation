# 06 — Environment Setup & First Run

Detected on this machine (2026-07-10): Python 3.13 via pyenv/homebrew, **no conda, no
SimNIBS**. You will install SimNIBS's self-contained bundle — it is **not** a plain `pip
install`.

## 1. Install SimNIBS 4.x
SimNIBS ships an installer that bundles its own Python and native binaries (`charm`,
`gmsh`, the FEM solver). Do not try to force it into your pyenv Python.

1. Download SimNIBS 4.x for macOS from the official site (SimNIBS.org → Downloads). Apple
   Silicon note: check the current macOS support/notes on the SimNIBS site and forum; some
   versions run under Rosetta or require specific steps. **Budget real time for this in Week 1.**
2. Run the installer / `install_simnibs`. It creates a SimNIBS install with:
   - `simnibs_python` — the bundled interpreter with `simnibs` importable.
   - `charm` — head segmentation/meshing (replaces the old `headreco`/`mri2mesh`).
   - GUI + example datasets (Ernie).
3. Add SimNIBS binaries to your `PATH` (the installer offers this). Then verify:

```bash
simnibs --version
charm --version
simnibs_python -c "import simnibs; print(simnibs.__version__)"
```

> **We run our pipeline with `simnibs_python`, not the system `python`.** The scripts import
> `simnibs`, which only exists in the bundled interpreter. If you want the bundled Python to
> also see our helper libs (pandas, statsmodels, seaborn, pyyaml), install them into it:
> `simnibs_python -m pip install -r env/requirements.txt`.

## 2. Locate the example data (Ernie)
SimNIBS installs example datasets. Find the Ernie MRI (`ernie_T1.nii.gz`, `ernie_T2.nii.gz`)
under the SimNIBS examples folder (path printed by the installer / in the docs). We use Ernie
for the Week-1 smoke test so you don't need any download.

## 3. First run — Ernie smoke test
```bash
cd "<this repo>"
# a) sanity check
simnibs_python src/nibs_speech/s00_setup_check.py

# b) build Ernie's head model (writes data/m2m/ernie/m2m_ernie)
#    (or point the script at the example T1/T2 paths it prints)
simnibs_python src/nibs_speech/s01_make_headmodel.py --subject ernie \
    --t1 <path>/ernie_T1.nii.gz --t2 <path>/ernie_T2.nii.gz

# c) define ROIs on Ernie
simnibs_python src/nibs_speech/s02_define_rois.py --subject ernie

# d) one tDCS montage + one TMS position
simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --subject ernie --only conventional_ifg
simnibs_python src/nibs_speech/s04_run_tms_grid.py --subject ernie --roi L_IFG --quick

# e) extract metrics
simnibs_python src/nibs_speech/s07_extract_roi_metrics.py --subject ernie
```
If step (e) writes a nonempty CSV under `results/roi_metrics/ernie/`, the pipeline works.

## 4. Compute notes
- `charm` per head: tens of minutes. tDCS leadfields and TMS grids: the heavy part —
  minutes-to-hours per subject depending on grid density. Start with `--quick` settings.
- Parallelize per subject (independent jobs). A Linux workstation or HPC cluster helps a lot
  for the full N-head run; the Ernie smoke test is fine on the laptop.

## 5. Config-first workflow
You should rarely edit Python. Edit [config/rois.yaml](../config/rois.yaml),
[config/montages.yaml](../config/montages.yaml), [config/coils.yaml](../config/coils.yaml).
The scripts read these. See [env/requirements.txt](../env/requirements.txt) and
[env/environment.yml](../env/environment.yml) for the analysis-side dependencies.

## 6. Troubleshooting pointers
- Import error `No module named simnibs` → you're using system python; use `simnibs_python`.
- `charm` not found → PATH not updated / installer step skipped.
- macOS Gatekeeper blocks binaries → allow in Security settings; see SimNIBS forum.
- Apple Silicon quirks → check the SimNIBS forum threads for your exact version.
