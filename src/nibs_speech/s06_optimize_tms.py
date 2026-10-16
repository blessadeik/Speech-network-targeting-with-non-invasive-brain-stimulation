"""s06 — formal TMS position+orientation optimization for one head × ROI.

    simnibs_python src/nibs_speech/s06_optimize_tms.py --subject ernie --roi L_IFG

Uses simnibs.opt_struct.TMSoptimize to search coil position + orientation maximizing mean
|E| in the ROI. Complements the brute-force sweep in s04. Outputs to
results/optimization/<subject>/tms/<roi>/<coil>/.

API-CHECK on first run: TMSoptimize attributes (fnamehead/target/search_radius/
spatial_resolution/search_angle/angle_resolution) for your SimNIBS version.
"""
from __future__ import annotations

import argparse
import sys

from utils import (Subject, get_logger, load_coils, load_rois, mni_to_subject,
                   write_manifest)

log = get_logger("s06")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--roi", required=True)
    ap.add_argument("--coil", default="figure8")
    args = ap.parse_args()

    from simnibs import opt_struct  # lazy

    subj = Subject(args.subject)
    subj.require_headmodel()
    coils = load_coils()
    coil = coils["coils"][args.coil]
    ocfg = coils["optimization"]

    roi_cfg = load_rois()["rois"][args.roi]
    if -99 in (roi_cfg.get("mni_seed") or []):
        log.error("ROI %s placeholder coords; fill config/rois.yaml.", args.roi)
        return 1
    target = list(mni_to_subject(roi_cfg["mni_seed"], subj.m2m_dir))

    out_dir = subj.result_dir("optimization") / "tms" / args.roi / args.coil
    out_dir.mkdir(parents=True, exist_ok=True)

    opt = opt_struct.TMSoptimize()
    opt.fnamehead = str(subj.mesh)
    opt.pathfem = str(out_dir)
    opt.fnamecoil = coil["fnamecoil"]
    opt.target = target
    opt.search_radius = ocfg["search_radius_mm"]
    opt.spatial_resolution = ocfg["spatial_resolution_mm"]
    opt.search_angle = ocfg["search_angle_deg"]           # API-CHECK attribute names
    opt.angle_resolution = ocfg["angle_resolution_deg"]

    log.info("TMSoptimize ROI %s (%s) -> %s", args.roi, args.coil, out_dir)
    try:
        opt.run()
    except Exception as exc:  # noqa: BLE001
        log.error("TMSoptimize FAILED: %s", exc)
        return 1
    write_manifest(out_dir, {"stage": "s06_tms_opt", "subject": subj.subid,
                             "roi": args.roi, "coil": args.coil, "config": ocfg})
    log.info("Done. Optimal position/orientation + field saved under %s", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
