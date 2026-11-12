"""s04: TMS position/orientation runs for one head x ROI.

Modes:
  --sweep-at-optimum  12 orientations at the s06 optimum (all heads; H4)
  --grid              full position x orientation grid (Ernie + 10 heads only)
  --quick             single position, 2 orientations (smoke test)

    simnibs_python src/nibs_speech/s04_run_tms_grid.py --head ernie --roi L_IFG --sweep-at-optimum
    simnibs_python src/nibs_speech/s04_run_tms_grid.py --head ernie --roi L_IFG --grid

Outputs: results/tms/<head>/<roi>/<coil>/<mode>/  (one simulation per pose; s07 reads each)

v0.2 fixes: grid offsets and handle directions now lie in the local scalp tangent plane
(world x/y offsets collapsed on lateral targets); orientation sweep rotates the optimized
coil matrix about its own axis instead of approximating a pos_ydir.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from utils import (Subject, abspath, default_cond_set, get_logger, load_coils, load_rois,
                   local_tangent_basis, project_to_scalp, roi_surface_mask,
                   rotate_matsimnibs, skin_surface_nodes, tangent_offsets, write_manifest)
from s03_run_tdcs_montages import apply_conductivity_set

log = get_logger("s04")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    ap.add_argument("--roi", required=True)
    ap.add_argument("--coil", default="figure8")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sweep-at-optimum", action="store_true")
    mode.add_argument("--grid", action="store_true")
    mode.add_argument("--quick", action="store_true")
    ap.add_argument("--cond-set", default=None)
    args = ap.parse_args()

    from simnibs import run_simnibs, sim_struct

    subj = Subject(args.head)
    subj.require_headmodel()
    cond_set = default_cond_set(args.head, args.cond_set)
    cfg = load_coils()
    coil = cfg["coils"][args.coil]
    if args.roi not in coil["use_for"]:
        log.error("Coil %s not configured for %s", args.coil, args.roi)
        return 1
    dist = cfg["defaults"]["coil_to_scalp_mm"]
    mode_name = "sweep" if args.sweep_at_optimum else ("grid" if args.grid else "quick")

    if args.grid:
        allowed = abspath(cfg["grid_search"]["heads_listed_in"])
        heads = allowed.read_text().split() if allowed.exists() else ["ernie"]
        if args.head not in heads:
            log.error("Full grid is limited to heads in %s (prereg). %s not listed.", allowed, args.head)
            return 1

    out = subj.result_dir("tms") / args.roi / args.coil / mode_name
    S = sim_struct.SESSION()
    S.subpath = str(subj.m2m_dir)
    S.pathfem = str(out)
    S.fields = "eE"
    S.map_to_surf = True
    tl = S.add_tmslist()
    tl.fnamecoil = coil["fnamecoil"]
    apply_conductivity_set(tl, cond_set)
    poses = []

    if args.sweep_at_optimum:
        best = subj.result_dir("optimization") / "tms" / args.roi / args.coil / "best_matsimnibs.npy"
        if not best.exists():
            log.error("No optimum at %s; run s06 first.", best)
            return 1
        mat0 = np.load(best)
        for ang in cfg["orientation_sweep"]["orientations_deg"]:
            pos = tl.add_position()
            pos.matsimnibs = rotate_matsimnibs(mat0, ang).tolist()
            poses.append({"angle_deg": ang})
    else:
        gs = cfg["grid_search"]["quick"] if args.quick else cfg["grid_search"]
        step = cfg["grid_search"]["spatial_resolution_mm"]
        skin = skin_surface_nodes(subj)
        _, info = roi_surface_mask(args.roi, load_rois()["rois"][args.roi], subj)
        c0 = project_to_scalp(info["center"], subj, skin)
        u, v, _ = local_tangent_basis(skin, c0)
        for (a, b) in tangent_offsets(gs["search_radius_mm"], step):
            pt = project_to_scalp(c0 + a * u + b * v, subj, skin)
            uu, vv, _ = local_tangent_basis(skin, pt)
            for ang in gs["orientations_deg"]:
                t = np.deg2rad(ang)
                pos = tl.add_position()
                pos.centre = list(map(float, pt))
                pos.pos_ydir = list(map(float, pt + 20.0 * (np.cos(t) * uu + np.sin(t) * vv)))
                pos.distance = dist
                poses.append({"offset_mm": [float(a), float(b)], "angle_deg": ang})

    log.info("TMS %s: %d poses, ROI %s, coil %s, head %s", mode_name, len(poses), args.roi,
             args.coil, args.head)
    try:
        run_simnibs(S)
    except Exception as exc:  # noqa: BLE001
        log.error("TMS %s FAILED: %s", mode_name, exc)
        return 1
    write_manifest(out, {"stage": "s04_tms", "mode": mode_name, "head": args.head,
                         "roi": args.roi, "coil": args.coil, "cond_set": cond_set,
                         "poses": poses})
    return 0


if __name__ == "__main__":
    sys.exit(main())
