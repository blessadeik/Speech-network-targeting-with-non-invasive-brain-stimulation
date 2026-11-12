"""s06: TMSoptimize (position + orientation) for one head x ROI x coil.

    simnibs_python src/nibs_speech/s06_optimize_tms.py --head ernie --roi L_IFG
    simnibs_python src/nibs_speech/s06_optimize_tms.py --head ernie --roi L_dLMC --coil double_cone

Maximizes mean |E| around the ROI centre (target_size = ROI radius, 10 mm for atlas ROIs).
Saves the optimal coil matrix to best_matsimnibs.npy for s04 --sweep-at-optimum.
Outputs: results/optimization/<head>/tms/<roi>/<coil>/
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from utils import (Subject, default_cond_set, get_logger, load_coils, load_rois,
                   roi_surface_mask, write_manifest)
from s03_run_tdcs_montages import apply_conductivity_set

log = get_logger("s06")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    ap.add_argument("--roi", required=True)
    ap.add_argument("--coil", default="figure8")
    ap.add_argument("--cond-set", default=None)
    args = ap.parse_args()

    from simnibs import opt_struct

    subj = Subject(args.head)
    subj.require_headmodel()
    cond_set = default_cond_set(args.head, args.cond_set)
    cfg = load_coils()
    coil, ocfg = cfg["coils"][args.coil], cfg["optimization"]
    if args.roi not in coil["use_for"]:
        log.error("Coil %s not configured for %s", args.coil, args.roi)
        return 1
    roi_cfg = load_rois()["rois"][args.roi]
    _, info = roi_surface_mask(args.roi, roi_cfg, subj)

    out = subj.result_dir("optimization") / "tms" / args.roi / args.coil
    out.mkdir(parents=True, exist_ok=True)
    opt = opt_struct.TMSoptimize()
    opt.subpath = str(subj.m2m_dir)                      # 4.6.0 derives fnamehead from subpath
    opt.pathfem = str(out)
    opt.fnamecoil = coil["fnamecoil"]
    opt.target = list(map(float, info["center"]))
    opt.target_size = float(roi_cfg.get("radius_mm") or 10.0)   # a radius in mm (4.6.0)
    opt.open_in_gmsh = False                             # 4.6.0 default True opens a GUI
    opt.distance = cfg["defaults"]["coil_to_scalp_mm"]
    opt.search_radius = ocfg["search_radius_mm"]
    opt.spatial_resolution = ocfg["spatial_resolution_mm"]
    opt.search_angle = ocfg["search_angle_deg"]
    opt.angle_resolution = ocfg["angle_resolution_deg"]
    # 4.6.0 accepts 'direct' or 'ADM'; ADM needs a dipole-based coil (.ccd is dipole-based)
    opt.method = ocfg.get("method", "direct")
    apply_conductivity_set(opt, cond_set)                # TMSoptimize.cond is a COND list (4.6.0)
    try:
        best = opt.run()
    except Exception as exc:  # noqa: BLE001
        log.error("TMSoptimize FAILED: %s", exc)
        return 1
    # 4.6.0: run() returns shape (return_n_max, 4, 4), best first. Save the single 4x4
    # matrix; s04 rotates it as a 4x4 and would silently mis-index a (1, 4, 4) array.
    best = np.asarray(best, dtype=float)
    if best.ndim == 3:
        best = best[0]
    if best.shape != (4, 4):
        log.error("Unexpected TMSoptimize result shape %s", best.shape)
        return 1
    np.save(out / "best_matsimnibs.npy", best)
    write_manifest(out, {"stage": "s06_tms_opt", "head": args.head, "roi": args.roi,
                         "coil": args.coil, "cond_set": cond_set, "config": ocfg})
    return 0


if __name__ == "__main__":
    sys.exit(main())
