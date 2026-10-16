# 01 — Scientific Background

> This is a working brief, not the paper's intro. Every empirical claim below is marked
> `[verify]` if it needs a citation you should confirm before it goes in the manuscript.
> Do not paste `[verify]` statements into the paper without checking the primary source.

## 1. The clinical problem
Speech and language impairments — post-stroke aphasia, apraxia of speech, dysarthria,
Parkinsonian hypophonia, spasmodic dysphonia — are common and disabling. NIBS (tDCS and
TMS) is an attractive adjunct to behavioral speech therapy because it is non-invasive,
relatively cheap, and can be paired with training. Multiple trials report modest benefits,
but effects are **heterogeneous and poorly reproducible** `[verify]`. A leading suspected
cause is **targeting and dose uncertainty**: the same scalp montage delivers different
E-fields to different brains, and the intended cortical target is often not where the field
actually peaks.

## 2. The speech network (our three ROI nodes)
- **Left inferior frontal gyrus (IFG) — "Broca's area."** Pars opercularis (Brodmann 44)
  and pars triangularis (BA 45). Central to speech production, articulatory planning, and
  syntax. Standard NIBS aphasia target. HCP-MMP1 labels `L_44`, `L_45`.
- **Posterior superior temporal gyrus (pSTG) — "Wernicke's area."** Auditory-linguistic
  processing and comprehension; also implicated in phonological/feedback control of speech.
  Overlaps HCP-MMP1 `L_A4`, `L_A5`, `L_STGa`, and STS areas; we define it by MNI ROI +
  atlas intersection (see [05_roi_definitions.md](05_roi_definitions.md)).
- **Laryngeal motor cortex (LMC).** The cortical control of the larynx/vocal folds — the
  final common path for phonation. Humans have a **dorsal** LMC (dLMC) and a **ventral** LMC
  (vLMC) in/near the precentral gyrus `[verify: Brown et al. 2008; Bouchard et al. 2013;
  Dichter, Breshears, Leonard & Chang 2018 Nature]`. This node is central to *speech-motor*
  restoration (dysarthria, hypophonia, dysphonia) yet is rarely the explicit target in
  NIBS-simulation papers. **This is our differentiator.** LMC has no dedicated HCP-MMP1
  label, so we define it from published stereotactic coordinates (see ROI doc), which is
  itself a methodological contribution.

## 3. The physics SimNIBS models
SimNIBS solves the quasi-static approximation of Maxwell's equations on a tetrahedral
head mesh with tissue-specific conductivities.
- **tDCS:** a Laplace/current-conservation problem. Injected current at scalp electrodes →
  steady-state current density **J** and E-field **E = J/σ** in tissue. Output scales
  *linearly* with injected current, so we report **V/m per mA** and can superpose.
- **TMS:** a time-varying coil current induces **E** in tissue (primary + secondary from
  charge accumulation at conductivity boundaries). Output scales with **dI/dt**; SimNIBS
  reports |E| for a reference dI/dt (typically 1 A/µs) so we report **V/m per (A/µs)** or
  normalize to a stated %MSO given a coil model.
- **Key field quantities:** `magnE` (|E|, magnitude), `E` (vector), `normal`/`tangent`
  components relative to the cortical surface. For dose, |E| (magnitude) is the primary
  outcome; the **normal component** matters mechanistically for polarity-specific tDCS
  effects and for gyral-crown vs sulcal-wall selectivity — we report both.

## 4. Why individual anatomy matters (our covariate model)
The delivered E-field at a fixed scalp target varies across people because of:
- **Scalp-to-cortex distance (SCD):** thicker scalp/skull/CSF → more attenuation and
  spread. TMS field falls off steeply with depth. `[verify: standard TMS dosimetry]`
- **Gyral geometry / cortical folding:** the E-field magnitude and its normal component
  depend on the orientation of the gyrus relative to the field; sulcal walls vs gyral crowns
  receive very different doses.
- **Tissue conductivity and CSF thickness:** CSF is highly conductive and shunts/reshapes
  current.
- **Skull thickness and defects.**

We quantify SCD and a gyrification/curvature proxy per ROI per head, then regress ROI
E-field on these covariates. This turns "results vary" into a **predictive, explanatory**
statement — a meaningful step above a pure montage catalog.

## 5. tDCS montage families we compare
1. **Conventional bipolar** (two large pad electrodes, e.g. anode over target + cathodal
   return). High current reach, poor focality.
2. **High-definition tDCS (HD-tDCS)**, e.g. 4×1 ring around the target. Better focality,
   lower per-electrode current.
3. **Bilateral / dual-target** montages (e.g. anode left IFG + cathode right homolog) common
   in aphasia protocols.
4. **Extracephalic return** (return electrode off the head, e.g. shoulder) — larger, deeper
   fields, different safety profile.
5. **Optimized montages** from SimNIBS leadfield optimization (formal target-E maximization
   subject to current and electrode-count constraints).

## 6. TMS coil configurations we compare
- **Figure-8 (focal)** coil at a grid of positions/orientations over each ROI; report the
  optimal position and **coil-handle orientation** (the E-field is strongest roughly
  perpendicular to the coil handle / along the induced current direction). Orientation is a
  real, often-neglected knob — e.g. aligning induced current across a gyrus vs along it.
- **Double-cone / deep coils** for LMC (which sits deeper/more dorsomedial than typical
  hand-knob targets) — depth vs focality trade-off.
- **Formal `TMSoptimize`** grid search over position and orientation to maximize ROI |E|.

## 7. Head models / data sources
- **Ernie** (ships with SimNIBS) — the reference exemplar; used for the full smoke test and
  as one head in the group.
- **MNI152** template head — a standard reference.
- **A group of public structural MRIs** for the variability analysis. Candidate open
  sources: HCP (needs data-use terms), IXI, OpenNeuro datasets, or the SimNIBS example set.
  Pick one open source with clean T1(+T2) and defensible reuse terms; N = 10–20 heads is
  enough for a first variability model. **Decision required — see research plan Week 1.**

## 8. Where the field is (positioning against prior art)
Simulation of tDCS/TMS E-fields is mature (ROAST, SimNIBS, and many montage-optimization
papers). What remains comparatively open and is our contribution:
- Matched **tDCS-vs-TMS** comparison for the **same speech ROIs** under one framework.
- **LMC as an explicit NIBS target** with a coordinate-based ROI recipe.
- A **dose–anatomy variability model** with released covariates.
- A **preregisterable, fully reproducible** artifact (code + masks + meshes) built for
  downstream trial design, not just a one-off montage recommendation.

See [02_novelty_and_positioning.md](02_novelty_and_positioning.md) for the candid appraisal.
