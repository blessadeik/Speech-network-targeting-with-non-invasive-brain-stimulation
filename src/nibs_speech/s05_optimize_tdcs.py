"""s05 — leadfield-based tDCS montage optimization for one head.

Two steps:
  1. Compute a tDCS leadfield once per head (heavy):  --build-leadfield
  2. Optimize montages per ROI from that leadfield:    (default)

    simnibs_python src/nibs_speech/s05_optimize_tdcs.py --subject ernie --build-leadfield
    simnibs_python src/nibs_speech/s05_optimize_tdcs.py --subject ernie

Uses simnibs.opt_struct.TDCSoptimize with constraints from config/montages.yaml
(optimization:). Writes optimized montage + predicted field to
results/optimization/<subject>/tdcs/<roi>/.

API-CHECK on first run: TDCSLEADFIELD + TDCSoptimize attribute names and the target
specification (positions vs node index) in your SimNIBS version.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from utils import (Subject, get_logger, load_montages, mni_to_subject,
                   write_manifest, abspath, load_paths)

log = get_logger("s05")
MA_TO_A = 1e-3


def leadfield_path(subj: Subject) -> Path:
    return abspath(load_paths()["results"]["leadfield"]) / subj.subid


def build_leadfield(subj: Subject, electrode_set: str) -> Path:
    from simnibs import run_simnibs, sim_struct  # lazy

    lf_dir = leadfield_path(subj)
    lf_dir.mkdir(parents=True, exist_ok=True)
    lf = sim_struct.TDCSLEADFIELD()
    lf.subpath = str(subj.m2m_dir)
    lf.pathfem = str(lf_dir)
    lf.eeg_cap = electrode_set          # API-CHECK: attribute may be eeg_cap / cap
    log.info("Building tDCS leadfield for %s (electrode set %s) — this is slow.",
             subj.subid, electrode_set)
    run_simnibs(lf)
    write_manifest(lf_dir, {"stage": "s05_leadfield", "subject": subj.subid,
                            "electrode_set": electrode_set})
    return lf_dir


def find_leadfield_hdf(lf_dir: Path) -> Path:
    hits = sorted(lf_dir.glob("*leadfield*.hdf5")) or sorted(lf_dir.glob("*.hdf5"))
    if not hits:
        raise FileNotFoundError(
            f"No leadfield .hdf5 in {lf_dir}. Run with --build-leadfield first.")
    return hits[0]


def optimize_roi(subj: Subject, roi_name: str, roi_cfg: dict, opt_cfg: dict, lf_hdf: Path):
    from simnibs import opt_struct  # lazy

    seed_sub = list(mni_to_subject(roi_cfg["mni_seed"], subj.m2m_dir))
    out_dir = subj.result_dir("optimization").parent  # results/optimization/<sub>
    out_dir = subj.result_dir("optimization") / "tdcs" / roi_name
    out_dir.mkdir(parents=True, exist_ok=True)

    opt = opt_struct.TDCSoptimize()
    opt.leadfield_hdf = str(lf_hdf)
    opt.name = str(out_dir / "optimized")
    opt.max_total_current = opt_cfg["max_total_current_mA"] * MA_TO_A
    opt.max_individual_current = opt_cfg["max_individual_current_mA"] * MA_TO_A
    opt.max_active_electrodes = int(opt_cfg["max_active_electrodes"])

    target = opt.add_target()
    target.positions = seed_sub                       # subject-space target coordinate
    target.intensity = float(opt_cfg["target_intensity_Vm"])
    target.radius = float(roi_cfg["radius_mm"])       # API-CHECK: attribute name

    log.info("Optimizing tDCS for ROI %s -> %s", roi_name, out_dir)
    opt.run()
    write_manifest(out_dir, {"stage": "s05_tdcs_opt", "subject": subj.subid,
                             "roi": roi_name, "constraints": opt_cfg})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--build-leadfield", action="store_true")
    ap.add_argument("--roi", nargs="*", help="subset of ROIs to optimize")
    args = ap.parse_args()

    subj = Subject(args.subject)
    subj.require_headmodel()
    cfg = load_montages()
    opt_cfg = cfg["optimization"]
    rois_all = __import__("utils").load_rois()["rois"]

    if args.build_leadfield:
        build_leadfield(subj, opt_cfg["electrode_set"])

    lf_hdf = find_leadfield_hdf(leadfield_path(subj))
    roi_names = args.roi or opt_cfg["run_for_rois"]
    for roi_name in roi_names:
        roi_cfg = rois_all[roi_name]
        if -99 in (roi_cfg.get("mni_seed") or []):
            log.warning("ROI %s placeholder coords; skipping.", roi_name)
            continue
        try:
            optimize_roi(subj, roi_name, roi_cfg, opt_cfg, lf_hdf)
        except Exception as exc:  # noqa: BLE001
            log.error("tDCS optimize ROI %s FAILED: %s", roi_name, exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
