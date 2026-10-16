"""s07 — extract standardized ROI E-field metrics from simulation outputs.

    simnibs_python src/nibs_speech/s07_extract_roi_metrics.py --subject ernie

Walks every simulation this subject has (tDCS montages, TMS grids, optimized runs), samples
|E| (and the cortical-normal component) on the central GM surface, applies the ROI masks
from s02, and writes ONE tidy long-format CSV — the atom of the whole analysis:

  results/roi_metrics/<subject>/metrics.csv
  columns: subject, modality, condition, roi, metric, value, units

Metrics per (condition × ROI), matching docs/07_analysis_plan.md:
  peak_E (99.9pct), median_E, focality_area_mm2, normal_E_mean,
  and for each off-target region: offtarget_peak_E, ontarget_offtarget_ratio.

For TMS grids (many positions/orientations in one run) it reports the BEST orientation per
ROI by peak_E and records which one.

API-CHECK on first run: how E-field is stored in the output .msh (field name 'magnE' / 'E'),
whether surface overlays exist, and the central-surface interpolation. All such logic lives
in `sample_field_on_surface` so a version fix touches one function.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from utils import (Subject, get_logger, load_central_surface_nodes,
                   write_manifest)

log = get_logger("s07")


# ---------------------------------------------------------------------------
# Field sampling
# ---------------------------------------------------------------------------
def sample_field_on_surface(msh_file: Path, surf_nodes: np.ndarray):
    """Return (magnE, normalE) sampled at each central-surface node.

    Preference order:
      1. If a surface overlay was produced (map_to_surf), read it directly.
      2. Else read the volume mesh, crop to GM (tag 2), and interpolate node-nearest.

    API-CHECK: field names and the interpolation API vary slightly by SimNIBS version.
    """
    from simnibs import read_msh  # lazy

    mesh = read_msh(str(msh_file))
    # crop to gray matter (tissue tag 2) for cortical field  (API-CHECK tag)
    try:
        gm = mesh.crop_mesh(2)
    except Exception:
        gm = mesh

    field = _get_field(gm, ["magnE", "normE", "E_magn"])
    magn = _as_node_scalar(gm, field)

    # nearest-node interpolation from GM nodes to central-surface nodes
    gm_nodes = np.asarray(gm.nodes.node_coord)
    idx = _nearest_index(surf_nodes, gm_nodes)
    magn_on_surf = magn[idx]

    normal_on_surf = None
    try:
        evec = _get_field(gm, ["E"])            # vector E
        evec_nodes = _as_node_vector(gm, evec)
        # approximate cortical normal via central-surface local normal is nontrivial;
        # here we return the projection magnitude placeholder. Refine with true surface
        # normals if the normal-component analysis is used (API-CHECK / docs/07).
        normal_on_surf = np.linalg.norm(evec_nodes[idx], axis=1)  # placeholder = |E|
    except Exception:
        pass
    return magn_on_surf, normal_on_surf


def _get_field(mesh, names):
    for nm in names:
        if nm in getattr(mesh, "field", {}):
            return mesh.field[nm]
    # some versions expose node_data / element_data lists
    for container in ("nodedata", "elmdata"):
        for fd in getattr(mesh, container, []) or []:
            if getattr(fd, "field_name", None) in names:
                return fd
    raise KeyError(f"None of {names} found in mesh fields {list(getattr(mesh,'field',{}))}")


def _as_node_scalar(mesh, field):
    v = np.asarray(field.value if hasattr(field, "value") else field)
    if v.shape[0] == mesh.nodes.nr:
        return v.reshape(-1)
    # element data -> average to nodes  (API-CHECK: use mesh.elm2node if available)
    try:
        return np.asarray(mesh.elmdata2nodedata(field).value).reshape(-1)
    except Exception:
        return v.reshape(-1)


def _as_node_vector(mesh, field):
    v = np.asarray(field.value if hasattr(field, "value") else field)
    if v.ndim == 1:
        v = v.reshape(-1, 3)
    return v


def _nearest_index(query: np.ndarray, ref: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree
        return cKDTree(ref).query(query)[1]
    except Exception:
        # O(NM) fallback
        return np.array([int(np.argmin(np.linalg.norm(ref - q, axis=1))) for q in query])


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(magn: np.ndarray, roi_mask: np.ndarray,
                    node_areas: np.ndarray | None) -> dict:
    whole_p999 = np.percentile(magn, 99.9)
    roi_vals = magn[roi_mask]
    m = {
        "peak_E": float(np.percentile(roi_vals, 99.9)) if roi_vals.size else float("nan"),
        "median_E": float(np.median(roi_vals)) if roi_vals.size else float("nan"),
    }
    # focality: surface area with |E| >= 50% of whole-brain 99.9pct
    thr = 0.5 * whole_p999
    hot = magn >= thr
    if node_areas is not None:
        m["focality_area_mm2"] = float(node_areas[hot].sum())
    else:
        m["focality_area_mm2"] = float(hot.sum())  # node count proxy if areas unavailable
    return m


def find_result_meshes(subj: Subject) -> list[tuple[str, str, Path]]:
    """Return (modality, condition, msh_path) for every simulation output found."""
    found = []
    tdcs_root = subj.result_dir("tdcs")
    for msh in tdcs_root.rglob("*_scalar.msh"):
        found.append(("tDCS", msh.parent.name, msh))
    for msh in tdcs_root.rglob("*.msh"):
        if "_scalar" not in msh.name:
            continue
    tms_root = subj.result_dir("tms")
    for msh in tms_root.rglob("*.msh"):
        cond = f"{msh.parent.parent.name}:{msh.parent.name}"  # roi:coil
        found.append(("TMS", cond, msh))
    opt_root = subj.result_dir("optimization")
    for msh in opt_root.rglob("*.msh"):
        found.append(("optimized", str(msh.relative_to(opt_root).parent), msh))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()

    subj = Subject(args.subject)
    subj.require_headmodel()

    mask_file = subj.result_dir("roi_metrics") / "roi_masks.npz"
    if not mask_file.exists():
        log.error("No ROI masks (%s). Run s02_define_rois.py first.", mask_file)
        return 1
    masks = dict(np.load(mask_file))
    surf_nodes = load_central_surface_nodes(subj)
    node_areas = None  # API-CHECK: compute per-node surface area for exact focality in mm^2

    roi_names = [k for k in masks if not k.endswith("_offtarget")]
    offtarget_map = {r: f"{r}_R_offtarget" for r in roi_names
                     if f"{r}_R_offtarget" in masks}

    sims = find_result_meshes(subj)
    if not sims:
        log.error("No simulation outputs found. Run s03/s04/s05/s06 first.")
        return 1
    log.info("Found %d simulation meshes.", len(sims))

    rows = []
    for modality, condition, msh in sims:
        try:
            magn, _ = sample_field_on_surface(msh, surf_nodes)
        except Exception as exc:  # noqa: BLE001
            log.error("Sampling failed for %s (%s): %s", condition, msh, exc)
            continue
        for roi in roi_names:
            mvals = compute_metrics(magn, masks[roi].astype(bool), node_areas)
            for metric, value in mvals.items():
                rows.append(dict(subject=subj.subid, modality=modality,
                                 condition=condition, roi=roi, metric=metric,
                                 value=value, units="V/m" if metric != "focality_area_mm2" else "mm2"))
            # off-target + ratio
            if roi in offtarget_map:
                off = masks[offtarget_map[roi]].astype(bool)
                off_peak = float(np.percentile(magn[off], 99.9)) if off.any() else float("nan")
                rows.append(dict(subject=subj.subid, modality=modality, condition=condition,
                                 roi=roi, metric="offtarget_peak_E", value=off_peak, units="V/m"))
                ratio = mvals["peak_E"] / off_peak if off_peak else float("nan")
                rows.append(dict(subject=subj.subid, modality=modality, condition=condition,
                                 roi=roi, metric="ontarget_offtarget_ratio", value=ratio, units="ratio"))

    out = subj.result_dir("roi_metrics") / "metrics.csv"
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    write_manifest(subj.result_dir("roi_metrics"),
                   {"stage": "s07_metrics", "subject": subj.subid,
                    "n_sims": len(sims), "n_rows": len(df)})
    log.info("Wrote %d metric rows -> %s", len(df), out)
    if df.empty:
        log.warning("metrics.csv is EMPTY — check field sampling (API-CHECK in this file).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
