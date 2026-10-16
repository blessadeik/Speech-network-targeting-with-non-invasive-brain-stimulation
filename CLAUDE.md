# CLAUDE.md — working notes for this repo

## What this project is
In-silico E-field mapping study: SimNIBS simulations of tDCS/TMS targeting three speech-network
ROIs — left IFG (Broca's), left pSTG (Wernicke's), laryngeal motor cortex (LMC). Goal is a
reproducible, preregisterable paper recommending practical montages/coil placements per ROI.
Full plan in [docs/](docs/); start at [docs/00_project_overview.md](docs/00_project_overview.md).

## How to work in this repo
- **Config-first.** Change targets/montages/coils in `config/*.yaml`, not in the scripts.
- **Two interpreters.** Simulation stages (`s01`–`s07`) run under **`simnibs_python`** (only it
  can import `simnibs`). Group analysis (`s08`) runs under plain `python`.
- **`# API-CHECK` comments** flag SimNIBS API details to confirm against the installed version
  during the Week-1 Ernie smoke test. The scripts were written without a live SimNIBS to run
  against — expect small fixes there, then the batch inherits them.
- **Reproducibility is a deliverable.** Every stage writes `run_manifest.json`. Keep the OSF
  preregistration and `docs/04_methods_protocol.md` in sync when conditions change.

## Scientific guardrails (important)
- This is a **dose-delivery** study. **Never** phrase results as speech/clinical *efficacy* —
  we characterize where the field goes, not whether stimulation helps.
- Don't put `[verify]` claims or `-99` placeholder coordinates into the manuscript. LMC
  coordinates must come from cited primary sources (see [docs/05_roi_definitions.md](docs/05_roi_definitions.md)).
- Target venue is a specialist journal (*Brain Stimulation*/*NeuroImage*/*JNE*), not *Nature* —
  see [docs/02_novelty_and_positioning.md](docs/02_novelty_and_positioning.md) for the honest positioning.

## Skills
- `run-subject` — run the pipeline end-to-end for one head model.
- `add-condition` — add a montage/coil/ROI consistently and keep the prereg in sync.
