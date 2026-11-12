"""s03: run the fixed tDCS montage families for every ROI on one head.

    simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --head IXI-012_full
    simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --head ARC-M2001_lesion --cond-set lesion_csf
    simnibs_python src/nibs_speech/s03_run_tdcs_montages.py --head ernie --only conventional:L_IFG

Families come from config/montages.yaml and are applied per ROI. The target electrode sits
on the 10-10 position nearest the scalp projection of the ROI centre (per head). Every
return electrode has its own channel, so listed currents are exactly delivered.

Outputs: results/tdcs/<head>/<family>__<roi>[__<cond_set>]/

v0.2 fixes vs v0.1:
- HD returns were on ONE shared channel, so SimNIBS split -2 mA by impedance, not -0.5 each.
- ROI-anchored HD montages injected +2 mA but only -0.5 mA returned (unbalanced).
- HD ring and pads used world-axis offsets; now built in the local scalp tangent plane.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from utils import (Subject, default_cond_set, eeg_positions, get_logger, load_config, load_montages,
                   load_rois, local_tangent_basis, nearest_eeg_label, project_to_scalp,
                   ring_points, roi_surface_mask, skin_surface_nodes, write_manifest,
                   central_surface)

log = get_logger("s03")
MA = 1e-3


def _electrode(tdcs, channel: int, centre, spec: dict):
    el = tdcs.add_electrode()
    el.channelnr = channel
    el.centre = centre if isinstance(centre, str) else list(map(float, centre))
    el.shape = spec["shape"]
    el.dimensions = spec["dimensions_mm"]
    el.thickness = spec["thickness_mm"]
    return el


def apply_conductivity_set(tdcs, set_name: str | None):
    """Set the lesion-tag conductivity for lesion-modeled ARC meshes.

    4.6.0: `.cond` on TDCSLIST/TMSLIST/TDCSLEADFIELD/TMSoptimize is a 1000-entry list of
    COND indexed by tag-1; tags 13-99 are unused by ElementTags, so tag 20 is free.
    """
    if not set_name:
        return
    cond_cfg = load_config("conductivity")
    tag = int(cond_cfg["lesion_tag"])
    value = float(cond_cfg["sets"][set_name]["lesion"])
    from simnibs import sim_struct
    while len(tdcs.cond) < tag:
        tdcs.cond.append(sim_struct.COND())
    tdcs.cond[tag - 1].value = value
    tdcs.cond[tag - 1].name = "Lesion"


def build(S, family: str, fam: dict, roi: str, ctx: dict, cond_set: str | None):
    defaults = ctx["defaults"]
    elec = {"pad": defaults["pad"], "hd": defaults["hd"]}
    tdcs = S.add_tdcslist()
    apply_conductivity_set(tdcs, cond_set)
    center = ctx["roi_centre"][roi]
    scalp_pt = project_to_scalp(center, ctx["subj"], ctx["skin"])
    target_label = nearest_eeg_label(scalp_pt, ctx["eeg"])
    currents, ch = [], 1
    tgt = fam["target"]
    _electrode(tdcs, ch, target_label, elec[tgt["electrode"]])
    currents.append(tgt["current_mA"] * MA)
    placed = {"target": target_label}

    rets = fam["returns"]
    if isinstance(rets, dict) and "ring" in rets:
        ring = rets["ring"]
        u, v, _ = local_tangent_basis(ctx["skin"], ctx["eeg"][target_label])
        pts = ring_points(ctx["eeg"][target_label], u, v, ring["radius_mm"], ring["n"])
        for p in pts:
            ch += 1
            _electrode(tdcs, ch, project_to_scalp(p, ctx["subj"], ctx["skin"]), elec[ring["electrode"]])
            currents.append(ring["current_mA_each"] * MA)
        placed["ring_radius_mm"] = ring["radius_mm"]
    else:
        for r in rets:
            ch += 1
            if r["at"] == "label":
                centre = r["label"]
            elif r["at"] == "homolog_projection":
                hp = project_to_scalp(ctx["homolog_centre"][roi], ctx["subj"], ctx["skin"])
                centre = nearest_eeg_label(hp, ctx["eeg"], exclude={target_label})
            elif r["at"] == "subject_coords":
                if r.get("coords") is None:
                    raise ValueError("extracephalic return coords not set in montages.yaml")
                centre = r["coords"]
            else:
                raise ValueError(f"unknown return placement {r['at']}")
            _electrode(tdcs, ch, centre, elec[r["electrode"]])
            currents.append(r["current_mA"] * MA)
            placed[f"return_{ch}"] = centre if isinstance(centre, str) else list(centre)

    if abs(sum(currents)) > 1e-9:
        raise ValueError(f"{family}/{roi}: currents do not sum to zero: {currents}")
    tdcs.currents = currents
    return placed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    ap.add_argument("--only", nargs="*", help="family:ROI pairs, e.g. conventional:L_IFG")
    ap.add_argument("--cond-set", default=None, help="conductivity set (ARC lesion meshes)")
    args = ap.parse_args()

    from simnibs import run_simnibs, sim_struct

    subj = Subject(args.head)
    subj.require_headmodel()
    args.cond_set = default_cond_set(args.head, args.cond_set)
    cfg = load_montages()
    rois = load_rois()["rois"]
    nodes = central_surface(subj)[0]
    ctx = {"subj": subj, "defaults": cfg["defaults"], "skin": skin_surface_nodes(subj),
           "eeg": eeg_positions(subj, cfg["defaults"]["cap"]),
           "roi_centre": {}, "homolog_centre": {}}
    for roi in cfg["apply_to_rois"]:
        _, info = roi_surface_mask(roi, rois[roi], subj, nodes)
        _, hinfo = roi_surface_mask(roi, rois[roi], subj, nodes, homolog=True)
        ctx["roi_centre"][roi], ctx["homolog_centre"][roi] = info["center"], hinfo["center"]

    jobs = [(f, r) for f in cfg["families"] for r in cfg["apply_to_rois"]]
    if args.only:
        wanted = {tuple(x.split(":")) for x in args.only}
        jobs = [j for j in jobs if j in wanted]
    out_root = subj.result_dir("tdcs")
    fails = 0
    for family, roi in jobs:
        fam = cfg["families"][family]
        if fam.get("only_heads") and args.head not in fam["only_heads"]:
            continue
        name = f"{family}__{roi}" + (f"__{args.cond_set}" if args.cond_set else "")
        S = sim_struct.SESSION()
        S.subpath = str(subj.m2m_dir)
        S.pathfem = str(out_root / name)
        S.fields = "eEjJ"
        S.map_to_surf = True               # central-surface overlays used by s07
        S.open_in_gmsh = False             # 4.6.0 default True opens a GUI per run
        try:
            placed = build(S, family, fam, roi, ctx, args.cond_set)
            log.info("tDCS %s on %s -> %s", name, args.head, S.pathfem)
            run_simnibs(S)
        except Exception as exc:  # noqa: BLE001
            log.error("%s FAILED: %s", name, exc)
            fails += 1
            continue
        write_manifest(out_root / name, {"stage": "s03_tdcs", "head": args.head,
                                         "family": family, "roi": roi,
                                         "cond_set": args.cond_set, "placement": placed})
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
