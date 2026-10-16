# 03 — Three-Month Research Plan

Start date anchor: **2026-07-10** (today). Target manuscript submission: **~2026-10-10**.
Assumes ~part-time-to-full-time effort of one PhD student. Adjust week counts to your
reality; the *order* matters more than the exact dates.

Milestones are gated: do not start a phase until its predecessor's **exit check** passes.

---

## Phase 0 — Foundations (Week 1)
**Goal: a working toolchain and a locked plan.**
- [ ] Install SimNIBS 4.x; confirm `charm` and `simnibs_python` run. ([06_environment_setup.md](06_environment_setup.md))
- [ ] Run the pipeline smoke test on **Ernie** (bundled example) end-to-end: head model → one
      tDCS montage → one TMS position → extract ROI metrics. This proves the plumbing.
- [ ] **Systematic literature scan** (2–3 days): matched tDCS/TMS speech-network dosimetry;
      LMC NIBS targeting; montage-optimization prior art. Write findings into
      [01_scientific_background.md](01_scientific_background.md) and confirm/adjust the novelty wedge in [02_novelty_and_positioning.md](02_novelty_and_positioning.md).
- [ ] **Decide the head-model dataset** for the group analysis (Ernie + MNI + one open MRI
      source; N=10–20). Document the choice and reuse terms.
- [ ] **Freeze** ROI definitions, montage list, coil list, and the analysis plan
      ([04](04_methods_protocol.md), [05](05_roi_definitions.md), [07](07_analysis_plan.md)). Register on OSF as a preregistration.

**Exit check:** Ernie smoke test produces a nonempty ROI metrics CSV; preregistration drafted.

---

## Phase 1 — Head models (Weeks 2–3)
**Goal: N validated head meshes.**
- [ ] Acquire/organize MRIs into `data/raw_mri/`.
- [ ] Batch-run `charm` to build `m2m_*` head models. ([s01_make_headmodel.py](../src/nibs_speech/s01_make_headmodel.py))
- [ ] **QC every head model** (charm report, visual mesh check, tissue segmentation sanity).
      Log pass/fail per subject; exclude and document failures.
- [ ] Compute per-subject anatomical covariates (scalp-to-cortex distance per ROI,
      curvature/gyrification proxy, CSF/skull thickness). ([s02_define_rois.py](../src/nibs_speech/s02_define_rois.py) + utils)

**Exit check:** ≥ N_min (target 10) QC-passed head models with covariates tabulated.

---

## Phase 2 — ROIs (Week 3, parallel with Phase 1 tail)
**Goal: reproducible ROI masks on every head.**
- [ ] Map MNI ROI seeds → subject space (`mni2subject_coords`) and intersect with atlas
      labels (HCP-MMP1 for IFG/pSTG; coordinate-sphere for LMC). ([s02_define_rois.py](../src/nibs_speech/s02_define_rois.py))
- [ ] Save ROI node/element masks per subject; visualize overlays for a sanity check.
- [ ] Sensitivity check: does a ±5 mm shift or radius change materially move the metrics?
      (Robustness — reviewers will ask.)

**Exit check:** ROI overlay figures look anatomically correct on ≥3 heads; masks saved.

---

## Phase 3 — tDCS simulations & optimization (Weeks 4–6)
**Goal: full tDCS E-field database.**
- [ ] Run the fixed montage battery (conventional, HD-4×1, bilateral, extracephalic) for
      each ROI × head. ([s03_run_tdcs_montages.py](../src/nibs_speech/s03_run_tdcs_montages.py))
- [ ] Compute tDCS leadfields and run `TDCSoptimize` per ROI × head to get optimized
      montages under realistic electrode/current constraints. ([s05_optimize_tdcs.py](../src/nibs_speech/s05_optimize_tdcs.py))
- [ ] Extract standardized metrics (peak/median |E|, normal component, focality, off-target)
      into the metrics database. ([s07_extract_roi_metrics.py](../src/nibs_speech/s07_extract_roi_metrics.py))

**Exit check:** tDCS metrics CSV complete for all heads × montages × ROIs, no NaN gaps.

---

## Phase 4 — TMS simulations & optimization (Weeks 6–8)
**Goal: full TMS E-field database.**
- [ ] Run figure-8 coil position/orientation grids over each ROI × head. ([s04_run_tms_grid.py](../src/nibs_speech/s04_run_tms_grid.py))
- [ ] Run `TMSoptimize` per ROI × head (position + orientation search). ([s06_optimize_tms.py](../src/nibs_speech/s06_optimize_tms.py))
- [ ] For LMC, additionally test a deeper coil (double-cone) — depth/focality trade-off.
- [ ] Extract metrics into the database.

**Exit check:** TMS metrics CSV complete; optimal orientation per ROI identified per head.

---

## Phase 5 — Group analysis & figures (Weeks 8–10)
**Goal: the results.**
- [ ] Group summaries: distributions of on-target |E|, focality, off-target per
      montage/coil × ROI. ([s08_group_analysis.py](../src/nibs_speech/s08_group_analysis.py))
- [ ] Dose–anatomy regressions (E-field ~ SCD + curvature + CSF …), per the locked plan.
- [ ] Rank montages/coils per ROI; identify the "practical winner" and its anatomy sensitivity.
- [ ] Build publication figures (glass-brain E-field maps, metric forest/violin plots,
      dose–anatomy scatter, optimal-orientation polar plots). ([09 figure spec](08_paper_outline.md))

**Exit check:** All planned figures drafted; results support (or honestly revise) the claims.

---

## Phase 6 — Write-up & release (Weeks 10–13)
**Goal: submittable manuscript + released artifacts.**
- [ ] Draft manuscript from [08_paper_outline.md](08_paper_outline.md).
- [ ] Clean the repo, write the data/code release (Zenodo DOI), finalize the OSF prereg link.
- [ ] Internal review with advisor; revise.
- [ ] Draft the downstream clinical-pilot preregistration (the payoff).
- [ ] Submit to primary target journal.

**Exit check:** Manuscript submitted; artifacts archived with DOIs.

---

## Standing risks & mitigations
| Risk | Mitigation |
|---|---|
| SimNIBS install / `charm` failures on macOS | Budget install time in Week 1; have a Linux box / cluster fallback; SimNIBS docs + forum. |
| Compute time (leadfields, TMS grids are heavy) | Start small (Ernie), parallelize per-subject, run overnight/batch; consider a cluster. |
| Head-model QC failures shrink N | Over-recruit MRIs (aim N=15–20 to keep ≥10). |
| Novelty scooped | Week-1 lit scan; LMC angle is the resilient wedge. |
| Scope creep toward clinical claims | Hold the line: this is a dose-delivery paper. Validation is the next paper. |
| Metric/analysis p-hacking risk | Preregister the analysis plan before running Phase 3. |
