"""s02 — build ROI masks + anatomical covariates for one head.

    simnibs_python src/nibs_speech/s02_define_rois.py --subject ernie

For each ROI in config/rois.yaml: map MNI seed -> subject space, build the central-surface
node mask (sphere ∩ atlas), and save it. Also compute per-ROI anatomical covariates
(scalp-to-cortex distance, mean curvature proxy) used later in the dose–anatomy model.

Outputs (results/roi_metrics/<subject>/):
  roi_masks.npz         boolean node masks per ROI (+ off-target homologs)
  roi_covariates.csv    subject, roi, scalp_cortex_distance_mm, curvature_proxy, n_nodes
  roi_overlay_seeds.csv  subject-space seed coords for QC/visualization
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from utils import (Subject, get_logger, load_central_surface_nodes, load_rois,
                   mni_to_subject, project_to_scalp, roi_surface_mask, write_manifest)

log = get_logger("s02")


def scalp_cortex_distance(seed_subject_xyz, subject: Subject) -> float:
    """Distance from the ROI cortical seed to the nearest scalp point (mm)."""
    scalp_pt = project_to_scalp(seed_subject_xyz, subject)
    return float(np.linalg.norm(np.asarray(scalp_pt) - np.asarray(seed_subject_xyz)))


def curvature_proxy(mask, nodes) -> float:
    """Cheap gyrification proxy: RMS deviation of ROI nodes from their local plane fit.

    Not a formal curvature; a stand-in until you wire in SimNIBS/FreeSurfer curvature.
    Higher => more folded/curved patch. Documented as a proxy in the methods.
    API-CHECK: replace with true mean curvature from the central surface if available.
    """
    pts = nodes[mask]
    if len(pts) < 4:
        return float("nan")
    centered = pts - pts.mean(axis=0)
    # normal = smallest-singular-vector direction; residual along it ~ non-flatness
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    normal = vt[-1]
    resid = centered @ normal
    return float(np.sqrt(np.mean(resid ** 2)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    subj = Subject(args.subject)
    subj.require_headmodel()
    cfg = load_rois()
    nodes = load_central_surface_nodes(subj)

    masks: dict[str, np.ndarray] = {}
    seeds_rows, cov_rows = [], []

    for roi_name, roi_cfg in cfg["rois"].items():
        if -99 in (roi_cfg.get("mni_seed") or []):
            log.warning("ROI %s has placeholder coords — skipping. Fill config/rois.yaml.",
                        roi_name)
            continue
        mask, _ = roi_surface_mask(roi_name, roi_cfg, subj)
        masks[roi_name] = mask
        seed_sub = np.asarray(mni_to_subject(roi_cfg["mni_seed"], subj.m2m_dir)).reshape(3)
        seeds_rows.append({"roi": roi_name, "x": seed_sub[0], "y": seed_sub[1], "z": seed_sub[2]})
        cov_rows.append({
            "subject": subj.subid,
            "roi": roi_name,
            "n_nodes": int(mask.sum()),
            "scalp_cortex_distance_mm": scalp_cortex_distance(seed_sub, subj),
            "curvature_proxy": curvature_proxy(mask, nodes),
        })
        log.info("ROI %s: %d surface nodes", roi_name, int(mask.sum()))

        # Off-target contralateral homolog (mirror x): map mirrored seed, same radius.
        if cfg.get("avoidance", {}).get("contralateral_homologs"):
            mirror_mni = [-roi_cfg["mni_seed"][0]] + list(roi_cfg["mni_seed"][1:])
            homo_cfg = dict(roi_cfg, mni_seed=mirror_mni, atlas_labels=None)
            hmask, _ = roi_surface_mask(roi_name + "_R", homo_cfg, subj)
            masks[roi_name + "_R_offtarget"] = hmask

    if not masks:
        log.error("No ROIs built (all placeholders?). Fill config/rois.yaml and rerun.")
        return 1

    out = subj.result_dir("roi_metrics")
    np.savez_compressed(out / "roi_masks.npz", **{k: v for k, v in masks.items()})
    pd.DataFrame(cov_rows).to_csv(out / "roi_covariates.csv", index=False)
    pd.DataFrame(seeds_rows).to_csv(out / "roi_overlay_seeds.csv", index=False)
    write_manifest(out, {"stage": "s02_define_rois", "subject": subj.subid,
                         "rois": list(masks.keys())})
    log.info("Wrote masks + covariates to %s", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
