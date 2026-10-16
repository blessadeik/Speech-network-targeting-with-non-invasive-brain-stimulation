# 04 — Methods Protocol (Preregistration Draft)

This is the frozen methods text. Once registered on OSF, changes are tracked as amendments.
Fill every `‹fill›`. Keep it in sync with [config/](../config/) — the config files are the
machine-readable version of this document.

## Study type
In-silico (computational) electric-field modeling study. No human participants are
prospectively stimulated or tested. Existing/public structural MRI and template head models
only.

## Software & versions (record exact versions before running)
- SimNIBS `‹fill, e.g. 4.1.x›`, charm segmentation.
- Python `‹fill›`; key libs pinned in [env/requirements.txt](../env/requirements.txt).
- Atlases: HCP-MMP1 (SimNIBS `subject_atlas`), and MNI152 for coordinate seeding.
- OS / hardware: `‹fill›`. Random seeds where applicable: `‹fill›`.

## Head models (sample)
- **Exemplars:** Ernie (SimNIBS example), MNI152 template.
- **Variability sample:** `‹fill: source, e.g. IXI / OpenNeuro accession›`, N = `‹fill, target ≥10›`
  T1-weighted (+T2 if available) structural MRIs of neurologically healthy adults.
- **Head-model generation:** `charm <subid> T1.nii.gz [T2.nii.gz]` with default settings.
- **QC & exclusion:** each `m2m_*` model reviewed via the charm report + visual mesh/tissue
  inspection. Exclusion criteria (pre-specified): segmentation failure, gross tissue
  mislabeling, missing ROI coverage. Exclusions logged with reason.

## Regions of interest (targets) — see [05_roi_definitions.md](05_roi_definitions.md)
Defined once in MNI space, mapped to each subject via `mni2subject_coords`, refined by atlas
labels where available. Analyzed on the **middle/central gray-matter surface**.
- **L-IFG (Broca's):** HCP-MMP1 `L_44` ∪ `L_45`, restricted to a sphere about the MNI seed.
- **L-pSTG (Wernicke's):** MNI seed sphere ∩ (`L_A4` ∪ `L_A5` ∪ `L_STGa` ∪ posterior STS labels).
- **Left LMC:** dorsal (dLMC) and ventral (vLMC) coordinate spheres from published values
  `‹fill exact MNI coords + citation›`; no atlas label, radius `‹fill, e.g. 8 mm›`.

## Avoidance / off-target regions (pre-specified)
Contralateral homolog of each ROI; temporalis-muscle scalp region (TMS); orbit/eyes region
(anterior tDCS montages). Off-target |E| reported for each.

## tDCS conditions — see [config/montages.yaml](../config/montages.yaml)
For each ROI, the fixed battery:
1. Conventional bipolar (anode over target, cathode `‹fill return›`), pad `‹e.g. 5×5 cm›`.
2. HD-tDCS 4×1 ring, ring radius `‹fill›`, `‹fill›` cm² electrodes.
3. Bilateral (anode target + cathode contralateral homolog).
4. Extracephalic return (return at `‹e.g. contralateral shoulder / neck›`).
5. **Optimized** montage from `TDCSoptimize` on a subject leadfield (EEG 10-10 electrode set),
   constraints: max total current `‹e.g. 2 mA›`, max per-electrode `‹e.g. 1 mA›`, max active
   electrodes `‹e.g. 8›`, target intensity `‹fill V/m›`.
- **Reference current:** all fixed montages simulated at a common injected current
  (`‹e.g. 2 mA total›`); results also reported normalized as **V/m per mA** (linear scaling).

## TMS conditions — see [config/coils.yaml](../config/coils.yaml)
For each ROI:
- **Figure-8 coil** (`‹model, e.g. Magstim_70mm_Fig8›`) on a position grid (search radius
  `‹e.g. 20 mm›`, resolution `‹e.g. 5 mm›`) × orientation grid (`‹e.g. every 30°, 0–330°›`),
  coil-to-scalp distance `‹e.g. 4 mm›`.
- **`TMSoptimize`** position+orientation search maximizing ROI mean |E|.
- **LMC only:** additionally a **double-cone/deep coil** for the depth/focality trade-off.
- **Dose normalization:** |E| reported per SimNIBS reference dI/dt; optionally scaled to a
  stated %MSO for the coil model. Report the convention explicitly.

## Primary outcome metrics (locked)
Computed on ROI GM surface nodes:
1. **On-target E-field:** peak = 99.9th-percentile |E| in ROI; and median |E| in ROI.
2. **Focality:** GM area with |E| ≥ 50% of the whole-brain 99.9th-percentile |E| (smaller =
   more focal); and on-target/off-target |E| ratio.
3. **Off-target exposure:** peak & median |E| in each avoidance region.
4. **Secondary:** ROI-mean **normal component** of E (polarity-relevant); % of ROI above a
   putative neuromodulation threshold `‹fill, if used›`.

## Anatomical covariates (per ROI × head)
Scalp-to-cortex distance (SCD); mean ROI curvature / gyrification proxy; local CSF thickness;
local skull thickness. Extraction method fixed in [s02_define_rois.py](../src/nibs_speech/s02_define_rois.py).

## Analysis — see [07_analysis_plan.md](07_analysis_plan.md)
Descriptive distributions per condition × ROI; linear mixed models for E-field ~ covariates
with subject random effects; pre-specified montage/coil rankings. Multiple-comparison
handling and exact model formulas are in the analysis plan and are **frozen before Phase 3**.

## What would change the conclusions (falsifiability)
If no montage/coil achieves ROI peak |E| meaningfully above off-target |E| (ratio ≤ `‹fill›`),
we report that target as **not selectively reachable** with the tested configurations — a
publishable negative result, not a failure.

## Deviations log
Record any deviation from this protocol here with date and rationale.
- `‹none yet›`
