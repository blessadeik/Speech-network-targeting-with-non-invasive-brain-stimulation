"""s05: leadfield-based tDCS optimization per ROI, plus the electrode-budget (k) sweep.

    simnibs_python src/nibs_speech/s05_optimize_tdcs.py --head ernie --build-leadfield
    simnibs_python src/nibs_speech/s05_optimize_tdcs.py --head ernie                # optimized, k = 8
    simnibs_python src/nibs_speech/s05_optimize_tdcs.py --head ernie --ksweep       # k = 2..12 + unconstrained

Objective: maximize the cortical-normal field over the ROI (unreachable target intensity),
avoid the contralateral homolog, total 2 mA, 1 mA per electrode.
Outputs: results/optimization/<head>/tdcs/<roi>/ and results/ksweep/<head>/<roi>/k<k>/

The leadfield is interpolated to the middle GM surface by default in SimNIBS (API-CHECK), so
optimized outputs are surface meshes; s07 reads them directly.
Lesion-modeled ARC heads: the leadfield must be built with the lesion conductivity set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from utils import (Subject, abspath, default_cond_set, get_logger, load_config,
                   load_montages, load_paths, load_rois, roi_surface_mask, write_manifest,
                   central_surface)

log = get_logger("s05")
MA = 1e-3


def leadfield_dir(subj: Subject, cond_set: str | None) -> Path:
    return abspath(load_paths()["results"]["leadfield"]) / subj.subid / (cond_set or "default")


def build_leadfield(subj: Subject, ocfg: dict, cond_set: str | None) -> Path:
    from simnibs import run_simnibs, sim_struct
    from s03_run_tdcs_montages import apply_conductivity_set
    d = leadfield_dir(subj, cond_set)
    d.mkdir(parents=True, exist_ok=True)
    lf = sim_struct.TDCSLEADFIELD()
    lf.subpath = str(subj.m2m_dir)
    lf.pathfem = str(d)
    lf.eeg_cap = str(subj.m2m_dir / "eeg_positions" / f"{ocfg['electrode_set']}.csv")  # API-CHECK
    e = ocfg["electrode"]
    lf.electrode.shape = e["shape"]                     # API-CHECK electrode template attr
    lf.electrode.dimensions = e["dimensions_mm"]
    lf.electrode.thickness = e["thickness_mm"]
    apply_conductivity_set(lf, cond_set)
    log.info("Building leadfield for %s (%s): slow.", subj.subid, cond_set or "default")
    run_simnibs(lf)
    write_manifest(d, {"stage": "s05_leadfield", "head": subj.subid, "cond_set": cond_set,
                       "cap": ocfg["electrode_set"], "electrode": e})
    return d


def find_hdf(d: Path) -> Path:
    hits = sorted(d.glob("*leadfield*.hdf5")) or sorted(d.glob("*.hdf5"))
    if not hits:
        raise FileNotFoundError(f"No leadfield in {d}; run --build-leadfield.")
    return hits[0]


def optimize(subj, roi, centre, homolog_centre, radius, ocfg, hdf, out_dir: Path, k):
    from simnibs import opt_struct
    out_dir.mkdir(parents=True, exist_ok=True)
    opt = opt_struct.TDCSoptimize()
    opt.leadfield_hdf = str(hdf)
    opt.name = str(out_dir / "optimized")
    opt.max_total_current = ocfg["max_total_current_mA"] * MA
    opt.max_individual_current = ocfg["max_individual_current_mA"] * MA
    if k is not None:
        opt.max_active_electrodes = int(k)
    t = opt.add_target()
    t.positions = list(map(float, centre))
    t.directions = ocfg["target_direction"]
    t.intensity = float(ocfg["target_intensity_Vm"])
    t.radius = float(radius)
    a = opt.add_avoid()                                  # API-CHECK TDCSavoid attrs
    a.positions = list(map(float, homolog_centre))
    a.radius = float(radius)
    a.weight = float(ocfg["avoid_homolog"]["weight"])
    currents = opt.run()
    rec = {"head": subj.subid, "roi": roi, "k": k,
           "currents_A": None if currents is None else [float(c) for c in currents]}
    (out_dir / "optimization.json").write_text(json.dumps(rec, indent=2))
    write_manifest(out_dir, {"stage": "s05_tdcs_opt", **rec, "constraints": ocfg})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    ap.add_argument("--build-leadfield", action="store_true")
    ap.add_argument("--ksweep", action="store_true")
    ap.add_argument("--roi", nargs="*")
    ap.add_argument("--cond-set", default=None)
    args = ap.parse_args()

    subj = Subject(args.head)
    subj.require_headmodel()
    cond_set = default_cond_set(args.head, args.cond_set)
    ocfg = load_montages()["optimization"]
    rois = load_rois()["rois"]
    if args.build_leadfield:
        build_leadfield(subj, ocfg, cond_set)
    hdf = find_hdf(leadfield_dir(subj, cond_set))
    nodes = central_surface(subj)[0]
    ks = load_config("ksweep")
    fails = 0
    for roi in (args.roi or ocfg["run_for_rois"]):
        cfg = rois[roi]
        _, info = roi_surface_mask(roi, cfg, subj, nodes)
        _, hinfo = roi_surface_mask(roi, cfg, subj, nodes, homolog=True)
        radius = cfg.get("radius_mm") or 10.0
        tag = f"__{cond_set}" if cond_set else ""
        runs = ([(k, subj.result_dir("ksweep") / f"{roi}{tag}" / f"k{k}") for k in ks["k_values"]]
                + [(None, subj.result_dir("ksweep") / f"{roi}{tag}" / "kNone")]) if args.ksweep \
            else [(ocfg["max_active_electrodes"], subj.result_dir("optimization") / "tdcs" / f"{roi}{tag}")]
        for k, out in runs:
            try:
                optimize(subj, roi, info["center"], hinfo["center"], radius, ocfg, hdf, out, k)
            except Exception as exc:  # noqa: BLE001
                log.error("%s k=%s FAILED: %s", roi, k, exc)
                fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
