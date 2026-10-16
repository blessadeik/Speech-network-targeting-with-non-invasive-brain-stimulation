# 02 — Novelty, Positioning, and an Honest Word About "Nature-worthy"

You asked for a Nature-worthy paper. I'm going to be a straight collaborator with you here,
because aiming at the wrong target wastes months.

## The honest appraisal
A **software-only, in-silico E-field mapping study** — however clean and reproducible — is
very unlikely to land in *Nature* or *Nature Neuroscience*. Those venues want a new
biological discovery or a paradigm shift demonstrated with data, usually including
experimental/clinical validation. E-field simulation methods are established (SimNIBS,
ROAST); "we simulated montages and made recommendations" is, on its own, an incremental
methods contribution. Selling it as more than it is will get it desk-rejected and cost you
credibility.

**That is not a reason to be discouraged.** It is a reason to aim precisely. A genuinely
excellent version of *this* study is a strong, citable, career-building paper in the right
venue — and it is the credible, fundable foundation for the clinical work that *could* later
reach a top-tier journal.

## Realistic target journals (aim here)
| Tier | Journals | Fit |
|---|---|---|
| **Primary target** | *Brain Stimulation*; *Journal of Neural Engineering*; *NeuroImage* | Home turf for NIBS dosimetry and E-field modeling. A rigorous, reproducible, LMC-inclusive comparison is a natural fit. |
| **Strong alternates** | *Human Brain Mapping*; *Clinical Neurophysiology*; *NeuroImage: Clinical*; *Frontiers in Human Neuroscience* | Good homes for the variability/anatomy-covariate angle or a more clinical framing. |
| **Methods/reproducibility** | *Journal of Open Source Software* (the tool) + a data paper (*Scientific Data*) | Release the pipeline + the E-field database as citable artifacts alongside the main paper. |

A well-executed *Brain Stimulation* or *NeuroImage* paper here is an excellent PhD chapter.

## What would it take to credibly reach for higher impact?
To move from "solid specialist paper" toward genuinely high-impact, you'd need to add at
least one of these — and each adds scope beyond 3 months:
1. **Experimental validation:** show the simulated target predicts a *measured* effect —
   e.g., TMS motor-evoked potentials / speech-arrest mapping, or E-field predicting behavioral
   response in a (re)analyzed tDCS aphasia dataset. Even a small validation cohort transforms
   the paper.
2. **A real methodological advance:** e.g., a novel LMC-targeting algorithm, an
   individualization method that provably reduces dose variance, or an
   uncertainty-quantification framework over conductivities.
3. **A clinically actionable, validated dosing rule** adopted in a registered trial.

**Recommendation:** Execute the 3-month in-silico study as a self-contained *Brain
Stimulation*/*NeuroImage* paper, and design it so that item (1) — validation — is the
obvious, pre-scoped follow-up (Year-3 pilot). That sequencing is how strong programs are
built, and it is exactly what your abstract's "supports protocol design and preregistration
for subsequent clinical pilots" already promises.

## The four things that make THIS paper genuinely novel and worth publishing
1. **Laryngeal motor cortex as a first-class NIBS target.** Most speech-NIBS simulation work
   stops at Broca's/Wernicke's. A coordinate-based LMC ROI recipe + montage/coil
   recommendations for it is a real gap-filler with clear clinical relevance
   (dysarthria, hypophonia, dysphonia).
2. **Matched cross-modality comparison.** tDCS *and* TMS, same ROIs, same metrics, same
   heads, one pipeline. Reviewers value apples-to-apples.
3. **Dose–anatomy variability model.** Not just "here are montages," but "here's how much the
   dose varies and which anatomical features predict it" — turns a catalog into a model.
4. **Reproducibility as a feature.** Preregistered analysis plan, released code + ROI masks +
   meshes + metric database. This is increasingly a *requirement* at good venues and a
   genuine differentiator.

## The one-sentence contribution (put this in the abstract and cover letter)
> We provide the first matched, reproducible E-field characterization of tDCS and TMS
> targeting across the full speech-production network — including the laryngeal motor cortex —
> and a model of how delivered dose varies with individual anatomy, yielding
> preregisterable montage and coil recommendations for speech-restoration trials.

## Risks to the novelty claim (check these in Week 1 lit review)
- Someone may have already published matched tDCS/TMS speech-network dosimetry. **Do the
  systematic search first** (see research plan Week 1) and adjust the wedge if needed. The
  LMC angle is the most defensible even if Broca's/Wernicke's dosimetry exists.
- ROAST/SimNIBS montage-optimization papers are numerous — cite them and be explicit about
  the delta (cross-modality + LMC + variability + reproducibility bundle).
