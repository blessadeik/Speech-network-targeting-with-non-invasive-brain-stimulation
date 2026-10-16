"""s03 — run the fixed tDCS montage battery for one head.

    simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --subject ernie
    simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --subject ernie --only conventional_ifg

Reads config/montages.yaml, builds a SimNIBS SESSION with one TDCSLIST per montage, and
runs them. Outputs go to results/tdcs/<subject>/<montage>/ as .msh with E-field fields.

API-CHECK on first run: electrode field names (centre/shape/dimensions/thickness), current
sign/units (SimNIBS wants Amps), and how ROI-anchored montages place electrodes.
"""
from __future__ import annotations

import argparse
import sys

from utils import (Subject, get_logger, load_montages, mni_to_subject,
                   project_to_scalp, load_rois, write_manifest)

log = get_logger("s03")

MA_TO_A = 1e-3


def _add_electrode(tdcs, spec: dict, subj: Subject):
    """Add one electrode to a TDCSLIST from a config spec dict."""
    el = tdcs.add_electrode()
    el.channelnr = int(spec["channel"])
    if "centre" in spec:
        el.centre = spec["centre"]            # EEG 10-10 label
    elif "centre_coords_mni" in spec:
        el.centre = list(mni_to_subject(spec["centre_coords_mni"], subj.m2m_dir))
    el.shape = spec.get("shape", "rect")
    el.dimensions = spec.get("dimensions_mm", [50, 50])
    el.thickness = spec.get("thickness_mm", 5)


def build_montage(S, name: str, m: dict, subj: Subject):
    """Attach a TDCSLIST for one montage config to session S."""
    tdcs = S.add_tdcslist()
    if m.get("anchor_on_roi"):
        # ROI-anchored montage (e.g. LMC): center electrode over projected ROI seed.
        rois = load_rois()["rois"]
        roi_cfg = rois[m["roi"]]
        seed_sub = mni_to_subject(roi_cfg["mni_seed"], subj.m2m_dir)
        center_scalp = list(project_to_scalp(seed_sub, subj))
        currents = []
        # center anode
        el = tdcs.add_electrode()
        el.channelnr = 1
        el.centre = center_scalp
        el.shape = m.get("center_shape", "ellipse")
        el.dimensions = m.get("center_dimensions_mm", [12, 12])
        el.thickness = 5
        currents.append(m["center_current_mA"] * MA_TO_A)
        # returns: either a 4x1 ring or a single distant return
        if m["family"] == "hd_tdcs":
            # NOTE: a proper ring needs ring-node placement around center_scalp; here we
            # place 4 returns offset along +/- x,y on the scalp as a first approximation.
            # API-CHECK: replace with geodesic ring placement for the final run.
            import numpy as np
            surround = m["surround_current_mA"] * MA_TO_A
            r = m.get("surround_ring_radius_mm", 35)
            for dx, dy in [(r, 0), (-r, 0), (0, r), (0, -r)]:
                pt = list(project_to_scalp(np.asarray(seed_sub) + [dx, dy, 0], subj))
                e = tdcs.add_electrode()
                e.channelnr = 2
                e.centre = pt
                e.shape = "ellipse"
                e.dimensions = [12, 12]
                e.thickness = 5
            currents.append(surround)  # channel 2 total; SimNIBS splits per node? API-CHECK
        else:
            e = tdcs.add_electrode()
            e.channelnr = 2
            e.centre = m["return_centre"]
            e.shape = "rect"
            e.dimensions = [50, 50]
            e.thickness = 5
            currents.append(m["return_current_mA"] * MA_TO_A)
        tdcs.currents = currents
    else:
        currents_by_channel: dict[int, float] = {}
        for spec in m["electrodes"]:
            _add_electrode(tdcs, spec, subj)
            ch = int(spec["channel"])
            currents_by_channel[ch] = currents_by_channel.get(ch, 0.0) + spec["current_mA"] * MA_TO_A
        # SimNIBS wants one current per channel in channel order.
        tdcs.currents = [currents_by_channel[c] for c in sorted(currents_by_channel)]
    return tdcs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--only", nargs="*", help="run only these montage names")
    args = ap.parse_args()

    from simnibs import run_simnibs, sim_struct  # lazy

    subj = Subject(args.subject)
    subj.require_headmodel()
    cfg = load_montages()
    montages = cfg["montages"]
    if args.only:
        montages = {k: v for k, v in montages.items() if k in set(args.only)}
        if not montages:
            log.error("No montages match --only %s. Available: %s",
                      args.only, list(cfg["montages"]))
            return 1

    out_root = subj.result_dir("tdcs")
    for name, m in montages.items():
        S = sim_struct.SESSION()
        S.subpath = str(subj.m2m_dir)
        S.pathfem = str(out_root / name)
        S.fields = "eEjJ"            # e=|E|, E=vector, j/J current density  (API-CHECK)
        S.map_to_surf = True         # also produce central-surface overlays  (API-CHECK)
        build_montage(S, name, m, subj)
        log.info("Running tDCS montage '%s' -> %s", name, S.pathfem)
        try:
            run_simnibs(S)
        except Exception as exc:  # noqa: BLE001
            log.error("Montage %s FAILED: %s", name, exc)
            continue
        write_manifest(out_root / name, {"stage": "s03_tdcs", "subject": subj.subid,
                                         "montage": name, "config": m})
    log.info("Done. Extract metrics with s07_extract_roi_metrics.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
