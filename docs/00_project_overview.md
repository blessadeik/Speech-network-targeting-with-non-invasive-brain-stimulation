# 00 — Project Overview

## Working title
**Targeting Speech Networks with Non-Invasive Brain Stimulation: A SimNIBS-Based
Electric-Field Mapping Study**

Alternative titles to A/B test with co-authors:
- *Where does the current actually go? Reproducible E-field targeting of the speech network for tDCS and TMS*
- *Simulation-guided montage and coil selection for non-invasive stimulation of Broca's, Wernicke's, and laryngeal motor cortex*
- *A reproducible E-field atlas for non-invasive brain stimulation of speech-network cortex*

## Core research question
For each canonical speech-network node — left IFG (Broca's), posterior STG (Wernicke's),
and laryngeal motor cortex (LMC) — **which practical, clinically deployable NIBS
configurations deliver the strongest, most focal on-target E-field with the least
off-target and muscle/nerve exposure, and how much does this vary across heads and why?**

## Deliverables
1. A **reproducible SimNIBS pipeline** (this repo): head model → ROI → simulate/optimize →
   metrics → group stats → figures.
2. An **E-field metric database** across N head models × montages/coils × ROIs (CSV).
3. A set of **recommended montages and coil placements** per ROI, with expected E-field,
   focality, and off-target profiles, and their sensitivity to anatomy.
4. A **preregistration-ready protocol** for a downstream clinical pilot (dose selection
   justified by simulation).
5. A **manuscript** targeting a specialist journal (see [02_novelty_and_positioning.md](02_novelty_and_positioning.md)).

## Scope boundaries (what this study is and is NOT)
- **IS:** a software-only, in-silico E-field mapping and montage/coil optimization study on
  existing/public MRI and template heads. No human data collection, no stimulation of
  participants. This keeps it IRB-light and achievable in ~3 months.
- **IS NOT:** a clinical efficacy trial, a behavioral study, or a claim that any montage
  *improves speech*. We characterize **dose delivery**, which is the necessary precondition
  for rational trial design. Keep every claim at the level of the physics + anatomy.

## Three primary outcome metrics (locked before running — see analysis plan)
1. **On-target E-field:** peak (99.9th percentile) and median |E| in each ROI (V/m per mA
   for tDCS; per unit dI/dt for TMS).
2. **Focality:** cortical GM area (or volume) with |E| ≥ 50% of the whole-brain 99.9th
   percentile; and the on-target/off-target ratio.
3. **Off-target exposure:** |E| in pre-specified avoidance regions (contralateral homolog,
   temporalis muscle region for TMS, eyes for tDCS montages).

## Why this can be strong (the honest version)
The novelty is not "simulate tDCS" (routine) — it is the **systematic, matched comparison
across both modalities and all three speech nodes, with the laryngeal motor cortex included
as a first-class target, plus a variability model tying dose to individual anatomy, all
released as a preregisterable, reproducible resource.** LMC targeting for speech-motor
restoration is genuinely under-characterized in the NIBS-simulation literature; that is the
sharpest wedge. See [02_novelty_and_positioning.md](02_novelty_and_positioning.md) for a
candid appraisal of impact ceiling and how to raise it.

## Reading order for a new collaborator
1. This file.
2. [01_scientific_background.md](01_scientific_background.md) — the biology and physics.
3. [02_novelty_and_positioning.md](02_novelty_and_positioning.md) — what's new, target journals, honest risks.
4. [03_research_plan_3month.md](03_research_plan_3month.md) — week-by-week plan.
5. [04_methods_protocol.md](04_methods_protocol.md) — the frozen methods (preregistration text).
6. [05_roi_definitions.md](05_roi_definitions.md) + [config/rois.yaml](../config/rois.yaml) — exact target definitions.
7. [07_analysis_plan.md](07_analysis_plan.md) — locked statistics.
8. [08_paper_outline.md](08_paper_outline.md) — the manuscript skeleton.
