"""s04 — run a TMS coil position/orientation grid over one ROI for one head.

    simnibs_python src/nibs_speech/s04_run_tms_grid.py --subject ernie --roi L_IFG
    simnibs_python src/nibs_speech/s04_run_tms_grid.py --subject ernie --roi L_IFG --quick

Places a figure-8 coil at a grid of scalp positions (around the ROI-projected scalp point)
× handle orientations from config/coils.yaml, and simulates each. Outputs to
results/tms/<subject>/<roi>/<coil>/.

This is the "sweep" companion to s06 (formal TMSoptimize). Use --quick for the smoke test.

API-CHECK on first run: TMSLIST position API (centre / pos_ydir / matsimnibs / distance),
coil filename resolution, and how orientation is parameterized in your SimNIBS version.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from utils import (Subject, get_logger, load_coils, load_rois, mni_to_subject,
                   project_to_scalp, write_manifest)

log = get_logger("s04")


def orientation_ydir(center_xyz, angle_deg: float) -> list[float]:
    """A point defining the coil +y (handle) direction for a given in-plane angle.

    SimNIBS defines coil orientation via a second point (pos_ydir). We offset from the
    center in the scalp-tangent plane by the angle. This is an approximation of the tangent
    plane using world axes; refine with the true local scalp normal if needed (API-CHECK).
    """
    a = np.deg2rad(angle_deg)
    offset = np.array([np.cos(a), np.sin(a), 0.0]) * 20.0  # 20 mm reference point
    return list(np.asarray(center_xyz) + offset)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--roi", required=True)
    ap.add_argument("--coil", default="figure8", help="key in config/coils.yaml coils:")
    ap.add_argument("--quick", action="store_true", help="single position, 2 orientations")
    args = ap.parse_args()

    from simnibs import run_simnibs, sim_struct  # lazy

    subj = Subject(args.subject)
    subj.require_headmodel()
    coils = load_coils()
    coil = coils["coils"][args.coil]
    gs = coils["grid_search"]
    defaults = coils["defaults"]

    roi_cfg = load_rois()["rois"][args.roi]
    if -99 in (roi_cfg.get("mni_seed") or []):
        log.error("ROI %s has placeholder coords; fill config/rois.yaml.", args.roi)
        return 1
    seed_sub = mni_to_subject(roi_cfg["mni_seed"], subj.m2m_dir)
    center_scalp = np.asarray(project_to_scalp(seed_sub, subj))

    if args.quick:
        radius, step = gs["quick"]["search_radius_mm"], 5
        orientations = gs["quick"]["orientations_deg"]
    else:
        radius, step = gs["search_radius_mm"], gs["spatial_resolution_mm"]
        orientations = gs["orientations_deg"]

    # Build the position grid on the scalp-tangent plane (approx world xy), project each.
    offsets = [(0.0, 0.0)] if radius == 0 else [
        (dx, dy)
        for dx in np.arange(-radius, radius + 1e-6, step)
        for dy in np.arange(-radius, radius + 1e-6, step)
        if dx * dx + dy * dy <= radius * radius
    ]

    out_root = subj.result_dir("tms") / args.roi / args.coil
    S = sim_struct.SESSION()
    S.subpath = str(subj.m2m_dir)
    S.pathfem = str(out_root)
    S.fields = "eE"                       # |E| + vector on the mesh
    tmslist = S.add_tmslist()
    tmslist.fnamecoil = coil["fnamecoil"]  # API-CHECK filename in your coil library

    n = 0
    for (dx, dy) in offsets:
        pt = np.asarray(project_to_scalp(np.asarray(seed_sub) + [dx, dy, 0], subj))
        for ang in orientations:
            pos = tmslist.add_position()
            pos.centre = list(pt)
            pos.pos_ydir = orientation_ydir(pt, ang)
            pos.distance = defaults["coil_to_scalp_mm"]
            n += 1

    log.info("TMS grid: %d positions×orientations for ROI %s (%s coil)",
             n, args.roi, args.coil)
    try:
        run_simnibs(S)
    except Exception as exc:  # noqa: BLE001
        log.error("TMS grid FAILED: %s", exc)
        return 1
    write_manifest(out_root, {"stage": "s04_tms_grid", "subject": subj.subid,
                              "roi": args.roi, "coil": args.coil,
                              "n_sims": n, "orientations": orientations,
                              "radius_mm": radius, "step_mm": step})
    log.info("Done. Extract metrics with s07 (it will pick the best orientation per ROI).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
