# 08 — Manuscript Outline & Figure Plan

Target: *Brain Stimulation* / *NeuroImage* / *Journal of Neural Engineering* (see
[02_novelty_and_positioning.md](02_novelty_and_positioning.md)). ~4000–6000 words + figures.

## Title (pick after results)
Primary: *Targeting Speech Networks with Non-Invasive Brain Stimulation: A SimNIBS-Based
Electric-Field Mapping Study.*

## Abstract (structured, ~250 words)
Background → objective (matched tDCS/TMS dosimetry across IFG, pSTG, LMC) → methods (N heads,
montages/coils, optimization, metrics) → key results (winning configs per ROI, focality,
LMC depth effect, anatomy predictors of dose) → conclusion (preregisterable recommendations;
released resource). Keep it dose-delivery-scoped; no efficacy claims.

## 1. Introduction
- Speech/language disorders + NIBS as adjunct; heterogeneity of effects.
- The targeting/dose problem: same scalp montage → different cortical dose.
- The speech network and the three nodes; LMC as under-targeted despite speech-motor role.
- Gap: no matched, reproducible tDCS+TMS dosimetry across the full network incl. LMC.
- Contributions (the 4 from the positioning doc). End with explicit aims/hypotheses.

## 2. Methods
Mirror [04_methods_protocol.md](04_methods_protocol.md): head models & QC; ROI definitions
(incl. LMC coordinate provenance); tDCS montages; TMS coils/orientations; optimization;
metrics; covariates; statistics. Cite the OSF preregistration and the code/data DOIs.

## 3. Results
- 3.1 Head-model sample & ROI validation (with covariate ranges).
- 3.2 tDCS: on-target E, focality, off-target per montage × ROI; optimized vs fixed.
- 3.3 TMS: position/orientation effects; optimal orientation per ROI; LMC depth trade-off.
- 3.4 Cross-modality comparison per ROI.
- 3.5 Dose–anatomy model: what predicts delivered dose; variance reduction from individualization.

## 4. Discussion
- Practical recommendations per ROI (the takeaway table).
- LMC targeting feasibility and caveats (depth, variability).
- Implications for trial design + dose selection; link to the planned pilot.
- Limitations: in-silico only, healthy template anatomy, conductivity uncertainty, no
  behavioral validation. Be explicit and generous here.
- Future work: experimental validation (MEP/speech-arrest), patient anatomy, uncertainty QC.

## 5. Data & code availability
Repo (Zenodo DOI), ROI masks, metric database, OSF preregistration.

---

## Figure plan (design with the `dataviz` skill; keep one visual system)
- **Fig 1 — Overview/pipeline schematic.** Head model → ROIs → sim/opt → metrics → group.
- **Fig 2 — ROI atlas.** The three nodes (+LMC dorsal/ventral) on an inflated/glass brain,
  with off-target regions.
- **Fig 3 — tDCS E-field maps.** Representative glass-brain |E| for each montage × ROI (one
  head), plus the optimized montage.
- **Fig 4 — tDCS metrics.** Violin/forest plots of peak_E, focality, off-target across heads,
  by montage, per ROI.
- **Fig 5 — TMS orientation.** Polar plot of ROI |E| vs coil orientation; map of optimal
  position; LMC double-cone vs figure-8 depth trade-off.
- **Fig 6 — Cross-modality + dose–anatomy.** tDCS vs TMS focality per ROI; scatter of peak_E
  vs scalp-to-cortex distance with mixed-model fit.
- **Table 1 — Recommendations.** Per ROI: best montage, best coil+orientation, expected E,
  focality, off-target, anatomy sensitivity.

## Reviewer-proofing checklist (address preemptively in text)
- [ ] Conductivity/model uncertainty acknowledged and, ideally, sensitivity-tested.
- [ ] ROI-definition robustness reported (seed shift / radius).
- [ ] Dose normalization convention stated unambiguously (per mA / per dI/dt / %MSO).
- [ ] Multiple comparisons handled per prereg.
- [ ] Healthy-anatomy generalizability limitation stated (lesioned brains differ).
- [ ] Clear statement that no efficacy is claimed.
