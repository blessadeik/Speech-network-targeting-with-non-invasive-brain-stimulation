# 05 — ROI Definitions

The machine-readable source of truth is [config/rois.yaml](../config/rois.yaml). This doc
explains the reasoning and the `[verify]` items you must confirm against primary sources
before locking.

## Design principles
- **Define once in MNI space, map per subject.** Every ROI has an MNI seed coordinate (and
  radius) plus, where a good atlas label exists, an intersection with HCP-MMP1 labels. Seeds
  are mapped to each head with `simnibs.mni2subject_coords`.
- **Analyze on the central gray-matter surface** (mid-cortical), where E-field sampling is
  most stable, rather than raw tetrahedra.
- **Left hemisphere is the target hemisphere** (language dominance assumption for the healthy
  sample). Contralateral homologs are the off-target/avoidance regions.

## The three targets

### 1. Left IFG — Broca's area
- **Atlas:** HCP-MMP1 `L_44` (pars opercularis) ∪ `L_45` (pars triangularis).
- **MNI seed (refinement center):** approximately `[-48, 16, 18]` `[verify against your
  preferred aphasia-NIBS literature; common Broca targets range ~x -45..-52]`.
- **Radius for seed sphere:** 10 mm (intersect with atlas labels).
- **Rationale:** canonical speech-production / articulatory-planning node; standard tDCS/TMS
  aphasia target.

### 2. Left pSTG — Wernicke's area
- **Atlas:** intersection of MNI seed sphere with posterior temporal HCP-MMP1 labels
  (candidates: `L_A4`, `L_A5`, `L_STGa`, `L_STSdp`, `L_STSvp`) `[verify which labels best
  cover your intended pSTG/Wernicke definition — the HCP parcellation splits this region]`.
- **MNI seed:** approximately `[-54, -42, 12]` `[verify]`.
- **Radius:** 10 mm.
- **Rationale:** auditory-linguistic comprehension and phonological feedback control.

### 3. Left laryngeal motor cortex (LMC) — the differentiator
No dedicated atlas label; **defined by published stereotactic coordinates** as spheres.
- **Dorsal LMC (dLMC):** MNI ≈ `‹fill exact›` `[verify — e.g., precentral gyrus larynx area;
  sources to check: Brown, Ngan & Liotti 2008; Bouchard et al. 2013; Dichter, Breshears,
  Leonard & Chang, Nature 2018; Eichert et al. laryngeal motor cortex work]`.
- **Ventral LMC (vLMC):** MNI ≈ `‹fill exact›` `[verify same sources]`.
- **Radius:** 8 mm (report sensitivity to 6/10 mm).
- **Analysis note:** LMC is deeper and more variable than crown targets — expect lower TMS
  |E| and steeper depth dependence; this is a substantive result, not a nuisance.

> **Action:** Before locking `config/rois.yaml`, open the primary sources above and paste the
> exact MNI coordinates + citations into both files. Do not ship placeholder coordinates in
> the paper. The coordinate provenance for LMC is itself part of the methods contribution.

## Off-target / avoidance regions
- **Contralateral homologs:** right-hemisphere mirror (negate x) of each target ROI.
- **Temporalis muscle region (TMS):** lateral scalp/temporal region overlying temporalis —
  relevant to TMS-evoked discomfort near temporal targets.
- **Orbit / eyes (tDCS):** for anterior/IFG montages with frontal returns.

## Robustness pre-checks (do before Phase 3)
- Shift each seed by ±5 mm along principal axes; confirm metrics don't swing wildly.
- Vary sphere radius (e.g., 8/10/12 mm); report metric stability.
- Confirm atlas-label coverage on ≥3 heads visually (overlay figure).
