"""s07: extract preregistered ROI metrics from every simulation of one head.

    simnibs_python src/nibs_speech/s07_extract_roi_metrics.py --head ernie

Writes results/roi_metrics/<head>/metrics.csv in long format:
  head, cohort, subject, group, version, modality, source, condition, roi, roi_variant,
  pose, metric, value, units

Metrics (OSF Prereg v0.2, 3.2), area-weighted on the central GM surface:
  median_E (primary), peak_E (99th pct), peak_E_999, normal_E_mean, focality_area_cm2,
  offtarget_median_E / offtarget_peak_E (homolog), ratio_on_off (medians),
  ratio_on_off_peak; face-dependent: eye_peak_E, muscle_local_peak_E (only if the head
  version keeps the face); lesion_median_E (lesion-modeled ARC only).

Field source, in order: map_to_surf overlay (E_magn, E_normal) > surface mesh whose node
count matches the central surface (optimizer outputs) > volume mesh, sampled from the
nearest GM element and projected on surface normals.

v0.2 fixes: normal component was a placeholder equal to |E|; node areas were missing, so
focality was a node count; 99.9th percentile on small ROIs equalled the max.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utils import (TAG, Subject, central_surface, get_logger, load_config, load_rois,
                   weighted_quantile, write_manifest)

log = get_logger("s07")
MAGN_NAMES = ("E_magn", "magnE", "normE")
NORMAL_NAMES = ("E_normal", "E_norm")
VEC_NAMES = ("E",)


def _field(mesh, names):
    for nm in names:
        if nm in getattr(mesh, "field", {}):
            return np.asarray(mesh.field[nm].value)
    return None


def surface_fields(msh: Path, n_nodes: int, normals: np.ndarray, surf_nodes: np.ndarray):
    """Return (magn, normal) per central-surface node, or raise."""
    from simnibs import read_msh
    overlay_dir = msh.parent / "subject_overlays"
    # 4.6.0 middle_gm_interpolation writes subject_overlays/<mesh stem>_central.msh
    overlay = overlay_dir / (msh.stem + "_central.msh")
    if overlay.exists():
        m = read_msh(str(overlay))
        mag, nrm = _field(m, MAGN_NAMES), _field(m, NORMAL_NAMES)
        if mag is not None and len(mag) == n_nodes:
            return mag.reshape(-1), (None if nrm is None else nrm.reshape(-1))
    m = read_msh(str(msh))
    if m.nodes.nr == n_nodes:                                     # surface output
        mag = _field(m, MAGN_NAMES)
        vec = _field(m, VEC_NAMES)
        if vec is not None and vec.shape[0] == n_nodes:
            vec = vec.reshape(-1, 3)
            return (np.linalg.norm(vec, axis=1) if mag is None else mag.reshape(-1),
                    np.einsum("ij,ij->i", vec, normals))
        if mag is not None:
            return mag.reshape(-1), None
    gm = m.crop_mesh(tags=[TAG["GM"]])                            # volume fallback
    vec = _field(gm, VEC_NAMES)
    if vec is None:
        raise KeyError(f"No E field in {msh}")
    from scipy.spatial import cKDTree
    _, idx = cKDTree(np.asarray(gm.elements_baricenters().value)).query(surf_nodes)
    v = vec.reshape(-1, 3)[idx]
    return np.linalg.norm(v, axis=1), np.einsum("ij,ij->i", v, normals)


def volume_tag_stats(msh: Path, tag: int, near=None, radius=None):
    """Peak (99th) and median |E| in a volume tissue tag, optionally within radius of a point."""
    from simnibs import read_msh
    m = read_msh(str(msh))
    try:
        sub = m.crop_mesh(tags=[tag])
    except Exception:
        return None
    mag = _field(sub, MAGN_NAMES)
    if mag is None:
        vec = _field(sub, VEC_NAMES)
        if vec is None:
            return None
        mag = np.linalg.norm(vec.reshape(-1, 3), axis=1)
    if near is not None:
        bc = np.asarray(sub.elements_baricenters().value)
        keep = np.linalg.norm(bc - np.asarray(near), axis=1) <= radius
        mag = mag[keep]
    if mag.size == 0:
        return None
    return float(np.percentile(mag, 99)), float(np.median(mag))


def roi_metrics(magn, normal, areas, mask, homolog_mask, whole_p999):
    w = areas[mask]
    out = {"median_E": weighted_quantile(magn[mask], w, 0.5),
           "peak_E": weighted_quantile(magn[mask], w, 0.99),
           "peak_E_999": weighted_quantile(magn[mask], w, 0.999)}
    if normal is not None and w.sum() > 0:
        out["normal_E_mean"] = float(np.sum(normal[mask] * w) / w.sum())
    hot = magn >= 0.5 * whole_p999
    out["focality_area_cm2"] = float(areas[hot].sum() / 100.0)
    if homolog_mask is not None and homolog_mask.any():
        wh = areas[homolog_mask]
        out["offtarget_median_E"] = weighted_quantile(magn[homolog_mask], wh, 0.5)
        out["offtarget_peak_E"] = weighted_quantile(magn[homolog_mask], wh, 0.99)
        out["ratio_on_off"] = out["median_E"] / out["offtarget_median_E"] if out["offtarget_median_E"] else np.nan
        out["ratio_on_off_peak"] = out["peak_E"] / out["offtarget_peak_E"] if out["offtarget_peak_E"] else np.nan
    return out


def find_sims(subj: Subject):
    """Yield (modality, source, condition, roi_hint, pose, mesh_path, volume_mesh_or_None)."""
    for msh in sorted(subj.result_dir("tdcs").glob("*/*.msh")):
        cond = msh.parent.name
        yield "tDCS", "fixed", cond, cond.split("__")[1], None, msh, msh
    for msh in sorted(subj.result_dir("tms").glob("*/*/*/*.msh")):
        roi, coil, mode = msh.parts[-4], msh.parts[-3], msh.parts[-2]
        mpose = re.search(r"-(\d{4})", msh.stem)
        yield "TMS", mode, f"{coil}__{mode}", roi, (int(mpose.group(1)) if mpose else None), msh, msh
    opt = subj.result_dir("optimization")
    for msh in sorted((opt / "tdcs").glob("*/*.msh")):
        yield "tDCS", "optimized", f"optimized__{msh.parent.name}", msh.parent.name.split("__")[0], None, msh, None
    for msh in sorted((opt / "tms").glob("*/*/*.msh")):
        yield "TMS", "optimized", f"{msh.parent.name}__optimized", msh.parts[-3], None, msh, msh
    for msh in sorted(subj.result_dir("ksweep").glob("*/k*/*.msh")):
        yield "tDCS", "ksweep", msh.parent.name, msh.parts[-3].split("__")[0], None, msh, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    args = ap.parse_args()

    subj = Subject(args.head)
    subj.require_headmodel()
    info = subj.info
    out_dir = subj.result_dir("roi_metrics")
    mf = out_dir / "roi_masks.npz"
    if not mf.exists():
        log.error("Run s02 first (%s missing).", mf)
        return 1
    masks = {k: v.astype(bool) for k, v in np.load(mf).items()}
    nodes, areas, normals, _ = central_surface(subj)
    rois_cfg = load_rois()
    av = rois_cfg["avoidance"]
    lesion_tag = int(load_config("lesion")["lesion_tag"])
    centres = pd.read_csv(out_dir / "roi_centres.csv") if (out_dir / "roi_centres.csv").exists() else None

    rows = []
    base = {k: info.get(k) for k in ("cohort", "subject", "group", "version")}
    n_sims = 0
    for modality, source, cond, roi_hint, pose, msh, vol in find_sims(subj):
        if "subject_overlays" in str(msh) or msh.name.endswith("_central.msh"):
            continue
        try:
            magn, normal = surface_fields(msh, len(nodes), normals, nodes)
        except Exception as exc:  # noqa: BLE001
            log.error("Sampling failed %s: %s", msh, exc)
            continue
        n_sims += 1
        whole = weighted_quantile(magn, areas, 0.999)
        for key, mask in masks.items():
            roi, variant = key.split("|")
            if variant == "homolog":
                continue
            hm = masks.get(f"{roi}|homolog")
            for metric, value in roi_metrics(magn, normal, areas, mask, hm, whole).items():
                rows.append({**base, "head": args.head, "modality": modality, "source": source,
                             "condition": cond, "roi": roi, "roi_variant": variant, "pose": pose,
                             "stimulated_roi": roi_hint, "metric": metric, "value": value,
                             "units": "cm2" if metric.endswith("cm2") else ("ratio" if metric.startswith("ratio") else "V/m")})
        if vol is None:
            continue
        extra = {}
        if info.get("face_metrics"):
            e = volume_tag_stats(vol, av["eyes"]["tissue_tag"])
            if e:
                extra["eye_peak_E"], extra["eye_median_E"] = e
            if centres is not None and roi_hint in set(centres.roi):
                c = centres[(centres.roi == roi_hint) & (centres.variant == "primary")][["sx", "sy", "sz"]].values[0]
                mu = volume_tag_stats(vol, av["local_muscle"]["tissue_tag"], near=c,
                                      radius=av["local_muscle"]["radius_mm"])   # around the scalp site
                if mu:
                    extra["muscle_local_peak_E"], extra["muscle_local_median_E"] = mu
        if info.get("version") == "lesion":
            lz = volume_tag_stats(vol, lesion_tag)
            if lz:
                extra["lesion_peak_E"], extra["lesion_median_E"] = lz
        for metric, value in extra.items():
            rows.append({**base, "head": args.head, "modality": modality, "source": source,
                         "condition": cond, "roi": roi_hint, "roi_variant": "na", "pose": pose,
                         "stimulated_roi": roi_hint, "metric": metric, "value": value, "units": "V/m"})

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "metrics.csv", index=False)
    write_manifest(out_dir, {"stage": "s07_metrics", "head": args.head, "n_sims": n_sims,
                             "n_rows": len(df), "head_info": info})
    log.info("%d rows from %d simulations -> %s", len(df), n_sims, out_dir / "metrics.csv")
    return 0 if len(df) else 1


if __name__ == "__main__":
    sys.exit(main())
