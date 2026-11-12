"""s02: ROI masks (primary, homolog, robustness variants) and covariates for one head.

    simnibs_python src/nibs_speech/s02_define_rois.py --head ernie

Outputs (results/roi_metrics/<head>/):
  roi_masks.npz       boolean masks over central-surface nodes (lh+rh), keys "<ROI>|<variant>"
                      variants: primary, homolog, shift_{x,y,z}{+,-}5, r6/r8/r10/r12, alt
  roi_covariates.csv  head, roi, n_nodes, area_cm2, scd_mm, scalp_mm, skull_mm, csf_mm,
                      curvature_proxy, seed_projection_mm, lesion_fraction, lesion_dist_mm
  roi_centres.csv     subject-space centres for QC overlays
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from utils import (BONE_TAGS, TAG, Subject, central_surface, get_logger, load_config,
                   load_rois, project_to_scalp, roi_surface_mask, skin_surface_nodes,
                   tissue_lengths_along_ray, write_manifest)

log = get_logger("s02")


def curvature_proxy(pts: np.ndarray) -> float:
    """RMS out-of-plane deviation of ROI nodes (mm); a folding proxy, documented as such."""
    if len(pts) < 4:
        return float("nan")
    c = pts - pts.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    return float(np.sqrt(np.mean((c @ vt[-1]) ** 2)))


def variants(cfg: dict, rcfg: dict):
    """Yield (variant_name, kwargs for roi_surface_mask)."""
    yield "primary", {}
    yield "homolog", {"homolog": True}
    s = float(cfg["robustness"]["seed_shifts_mm"])
    base_r = rcfg.get("radius_mm") or 10.0
    for ax, name in enumerate("xyz"):
        for sign in (+1, -1):
            sh = [0.0, 0.0, 0.0]
            sh[ax] = sign * s
            yield f"shift_{name}{'+' if sign > 0 else '-'}{int(s)}", {"shift_mm": sh, "radius_mm": base_r}
    for r in cfg["robustness"]["radii_mm"]:
        yield f"r{int(r)}", {"radius_mm": float(r)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", "--subject", dest="head", required=True)
    args = ap.parse_args()

    import nibabel as nib
    subj = Subject(args.head)
    subj.require_headmodel()
    cfg = load_rois()
    nodes, areas, _, _ = central_surface(subj)
    skin = skin_surface_nodes(subj)
    tis = nib.load(str(subj.tissues_nii))
    labels, aff = np.asarray(tis.dataobj), tis.affine
    lesion_tag = int(load_config("lesion")["lesion_tag"])
    lesion_vox = np.argwhere(labels == lesion_tag)
    lesion_xyz = (np.c_[lesion_vox, np.ones(len(lesion_vox))] @ aff.T)[:, :3] if len(lesion_vox) else None

    masks, cov, centres = {}, [], []
    for roi, rcfg in cfg["rois"].items():
        for vname, kw in variants(cfg, rcfg):
            try:
                m, info = roi_surface_mask(roi, rcfg, subj, nodes, **kw)
            except Exception as exc:  # noqa: BLE001
                log.error("%s|%s failed: %s", roi, vname, exc)
                continue
            masks[f"{roi}|{vname}"] = m
            centres.append({"head": args.head, "roi": roi, "variant": vname,
                            "x": info["center"][0], "y": info["center"][1], "z": info["center"][2]})
            if vname != "primary":
                continue
            sp = project_to_scalp(info["center"], subj, skin)
            centres[-1].update({"sx": sp[0], "sy": sp[1], "sz": sp[2]})
            seg = tissue_lengths_along_ray(labels, aff, info["center"], sp)
            row = {"head": args.head, "roi": roi, "n_nodes": int(m.sum()),
                   "area_cm2": float(areas[m].sum() / 100.0),
                   "scd_mm": float(np.linalg.norm(sp - info["center"])),
                   "scalp_mm": seg.get(TAG["Scalp"], 0.0),
                   "skull_mm": sum(seg.get(t, 0.0) for t in BONE_TAGS),
                   "csf_mm": seg.get(TAG["CSF"], 0.0),
                   "curvature_proxy": curvature_proxy(nodes[m]),
                   "seed_projection_mm": info.get("seed_projection_mm", 0.0)}
            if lesion_xyz is not None:
                from scipy.spatial import cKDTree
                d, _ = cKDTree(lesion_xyz).query(nodes[m])
                row["lesion_fraction"] = float((d <= 1.0).mean())
                row["lesion_dist_mm"] = float(d.min())
            cov.append(row)
            log.info("%s: %d nodes, SCD %.1f mm", roi, row["n_nodes"], row["scd_mm"])
        alt = rcfg.get("alternate")
        if alt:
            acfg = rcfg if alt.get("definition") == "sphere_at_label_centroid" else {**rcfg, **alt}
            try:
                masks[f"{roi}|alt"] = roi_surface_mask(roi, acfg, subj, nodes,
                                                       radius_mm=alt.get("radius_mm"))[0]
            except Exception as exc:  # noqa: BLE001
                log.error("%s|alt failed: %s", roi, exc)

    out = subj.result_dir("roi_metrics")
    np.savez_compressed(out / "roi_masks.npz", **masks)
    pd.DataFrame(cov).to_csv(out / "roi_covariates.csv", index=False)
    pd.DataFrame(centres).to_csv(out / "roi_centres.csv", index=False)
    write_manifest(out, {"stage": "s02_rois", "head": args.head, "masks": list(masks)})
    return 0 if masks else 1


if __name__ == "__main__":
    sys.exit(main())
