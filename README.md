# Simulation-Guided Targeting for NIBS in Speech Networks

**A SimNIBS-based electric-field (E-field) mapping study of tDCS and TMS targeting of
speech-network cortex: left inferior frontal gyrus (Broca's), posterior superior temporal
gyrus (Wernicke's), and laryngeal motor cortex (LMC).**

This repository contains a fully reproducible, software-only computational pipeline that
generates head models, defines speech-network ROIs, simulates and optimizes tDCS montages
and TMS coil placements, extracts standardized E-field metrics, and runs group-level
statistics relating field delivery to anatomy. The end product is a preregisterable
protocol and a publication (target venues in [docs/02_novelty_and_positioning.md](docs/02_novelty_and_positioning.md)).

---

## The one-paragraph pitch

Precise, reproducible targeting is the bottleneck for translating non-invasive brain
stimulation (NIBS) into speech restoration. We characterize tDCS and TMS E-field
distributions across the canonical speech network using SimNIBS, over multiple head models,
multiple montages/coil placements, and formal optimization. We report which practical,
clinically deployable configurations maximize on-target E-field and focality while
minimizing off-target and muscle/nerve exposure — with special attention to the
under-studied **laryngeal motor cortex**, a key node for speech-motor restoration. All
meshes, scripts, ROI masks, and metrics are released to support protocol design and
preregistration of downstream clinical pilots.

## Repository map

| Path | What's in it |
|---|---|
| [docs/](docs/) | Project plan, scientific background, novelty/positioning, methods protocol, ROI definitions, analysis plan, paper outline. **Start here.** |
| [config/](config/) | Declarative YAML for ROIs, tDCS montages, and TMS coil placements. Edit these, not the code. |
| [src/nibs_speech/](src/nibs_speech/) | The pipeline: head models → ROIs → simulation → optimization → metrics → group stats. |
| [env/](env/) | Conda/pip environment specs and SimNIBS install notes. |
| [data/](data/) | Inputs (raw MRI, `m2m_*` head models, external templates). Git-ignored. |
| [results/](results/) | Simulation outputs, extracted metrics, figures. Large binaries git-ignored; metric tables tracked. |
| [.claude/skills/](.claude/skills/) | Project automation skills (run a subject, add an experiment, build a figure). |

## Quickstart

```bash
# 1. Read the plan
open docs/00_project_overview.md docs/03_research_plan_3month.md

# 2. Set up the environment (see env/README.md for SimNIBS install — it is NOT pip-only)
#    SimNIBS ships its own installer + bundled Python.

# 3. Sanity-check the toolchain
simnibs_python src/nibs_speech/s00_setup_check.py

# 4. Build a head model from the bundled Ernie example (no MRI download needed)
#    then run the pipeline end to end on that one subject as a smoke test.
```

See [docs/06_environment_setup.md](docs/06_environment_setup.md) for the full install and
first-run walkthrough.

## Status

Scaffolding stage. The scientific plan, config schema, and pipeline skeleton are complete
and self-consistent against the SimNIBS 4.x API. Next action: install SimNIBS and run the
Ernie smoke test (Week 1 in the research plan).
