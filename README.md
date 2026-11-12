# Simulation-Guided Targeting for NIBS in Speech Networks

**A SimNIBS-based electric-field (E-field) mapping study of tDCS and TMS targeting of
speech-network cortex: left inferior frontal gyrus, posterior superior temporal
gyrus, and dorsal and ventral laryngeal motor cortex, in healthy and post-stroke heads.**

This repository contains a fully reproducible, software-only computational pipeline that
generates head models, defines speech-network ROIs, simulates and optimizes tDCS montages
and TMS coil placements, extracts standardized E-field metrics, and runs group-level
statistics relating field delivery to anatomy. The end product is a preregisterable
protocol and a peer-reviewed publication in a specialist brain-stimulation or neuroimaging journal.

---

## The one-paragraph pitch

Precise, reproducible targeting is the bottleneck for translating non-invasive brain
stimulation (NIBS) into speech restoration. We characterize tDCS and TMS E-field
distributions across the canonical speech network using SimNIBS, over multiple head models,
multiple montages/coil placements, and formal optimization. We report which practical,
clinically deployable configurations maximize on-target E-field and focality while
minimizing off-target and muscle/nerve exposure: with special attention to the
under-studied **laryngeal motor cortex**, a key node for speech-motor restoration. All
meshes, scripts, ROI masks, and metrics are released to support protocol design and
preregistration of downstream clinical pilots.

## Repository map

| Path | What's in it |
|---|---|
| [config/](config/) | Declarative YAML for ROIs, tDCS montages, and TMS coil placements. Edit these, not the code. |
| [src/nibs_speech/](src/nibs_speech/) | The pipeline: head models → ROIs → simulation → optimization → metrics → group stats. |
| [env/](env/) | Conda/pip environment specs and SimNIBS install notes. |
| [data/](data/) | Inputs (raw MRI, `m2m_*` head models, external templates). Git-ignored. |
| [results/](results/) | Simulation outputs, extracted metrics, figures. Large binaries git-ignored; metric tables tracked. |
| [tests/](tests/) | Unit tests for the geometry helpers (`python -m pytest -q`). |

The full study protocol and preregistration documents are maintained separately and will be
released with the preregistration.

## Quickstart

```bash
# 1. Set up the environment (see env/README.md for SimNIBS install: it is NOT pip-only)
#    SimNIBS ships its own installer + bundled Python.

# 2. Sanity-check the toolchain
simnibs_python src/nibs_speech/s00_setup_check.py

# 3. Build a head model from the bundled Ernie example (no MRI download needed)
#    then run the pipeline end to end on that one subject as a smoke test.
```

See [env/README.md](env/README.md) for environment setup and
[src/nibs_speech/README.md](src/nibs_speech/README.md) for the stage-by-stage run order.

## Status

v0.2: four ROIs, ARC + IXI cohorts, lesion and defacing versions, k sweep. Next action: Stage 1 on Linux/HPC.
