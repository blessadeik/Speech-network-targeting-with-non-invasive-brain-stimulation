"""Shared helpers: config/paths loading, head bookkeeping, logging, geometry.

Dependency-light: imports under plain python (numpy, yaml, pandas). SimNIBS is imported
lazily inside the functions that need it. Pure-geometry helpers at the bottom are unit
tested in tests/ without SimNIBS.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml

# ---------------------------------------------------------------------------
# Repo layout and config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"

# charm 4.x volume tissue tags (API-CHECK in Stage 1; surfaces are tag + 1000)
TAG = {"WM": 1, "GM": 2, "CSF": 3, "Bone": 4, "Scalp": 5, "Eye": 6,
       "Compact_bone": 7, "Spongy_bone": 8, "Blood": 9, "Muscle": 10}
SKIN_SURFACE_TAG = 1005
BONE_TAGS = (4, 7, 8)


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def load_config(name: str) -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / f"{name}.yaml")


def load_paths() -> dict[str, Any]:
    return load_config("paths")


def load_rois() -> dict[str, Any]:
    return load_config("rois")


def load_montages() -> dict[str, Any]:
    return load_config("montages")


def load_coils() -> dict[str, Any]:
    return load_config("coils")


def abspath(rel: str | Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (REPO_ROOT / p)


# ---------------------------------------------------------------------------
# Head bookkeeping. A "head" is one mesh: e.g. IXI-012_full, ARC-M2001_lesion, ernie.
# ---------------------------------------------------------------------------
@dataclass
class Subject:
    subid: str                      # head id (kept as `subid` for backward compatibility)
    paths: dict[str, Any] = field(default_factory=load_paths)

    @property
    def m2m_dir(self) -> Path:
        return abspath(self.paths["data"]["m2m"]) / f"m2m_{self.subid}"

    @property
    def mesh(self) -> Path:
        # FIX v0.2: charm 4.x writes <subid>.msh INSIDE m2m_<subid>/ (API-CHECK once).
        inside = self.m2m_dir / f"{self.subid}.msh"
        outside = self.m2m_dir.parent / f"{self.subid}.msh"
        return inside if inside.exists() or not outside.exists() else outside

    @property
    def tissues_nii(self) -> Path:
        return self.m2m_dir / "final_tissues.nii.gz"      # API-CHECK

    def result_dir(self, kind: str) -> Path:
        d = abspath(self.paths["results"][kind]) / self.subid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def require_headmodel(self) -> None:
        if not self.m2m_dir.exists():
            raise FileNotFoundError(f"No head model at {self.m2m_dir}. Run s01 first.")

    @property
    def info(self) -> dict[str, Any]:
        return head_info(self.subid)


def head_info(head_id: str) -> dict[str, Any]:
    """Cohort metadata for a head from data/derived/cohort.csv (written in Stage 3).

    Falls back to parsing the id ("{cohort}-{subject}_{version}") so exemplars work
    before the cohort table exists. face_metrics says whether orbit/muscle metrics apply.
    """
    cohort_csv = abspath(load_paths()["data"].get("derived", "data/derived")) / "cohort.csv"
    if cohort_csv.exists():
        with open(cohort_csv) as fh:
            for row in csv.DictReader(fh):
                if row.get("head_id") == head_id:
                    row["face_metrics"] = str(row.get("face_metrics", "")).lower() in ("1", "true", "yes")
                    return row
    cohort, subject, version = "exemplar", head_id, "full"
    if "-" in head_id:
        cohort, rest = head_id.split("-", 1)
        subject, _, version = rest.rpartition("_") if "_" in rest else (rest, "", "full")
    face = version == "full" or cohort == "exemplar"
    group = {"ARC": "lesioned", "IXI": "healthy", "ATLAS": "lesioned"}.get(cohort, "exemplar")
    return {"head_id": head_id, "cohort": cohort, "subject": subject, "version": version,
            "group": group, "face_metrics": face}


# ---------------------------------------------------------------------------
# Logging + run manifests
# ---------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=os.environ.get("NIBS_LOGLEVEL", "INFO"),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    return logging.getLogger(name)


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "no-git"


def config_hashes() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            for p in sorted(CONFIG_DIR.glob("*.yaml"))}


def write_manifest(out_dir: Path, payload: dict[str, Any]) -> Path:
    """Record versions, config hashes, host and args next to outputs."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload.setdefault("simnibs_version", _simnibs_version())
    payload.setdefault("git_sha", _git_sha())
    payload.setdefault("config_hashes", config_hashes())
    payload.setdefault("host", platform.node())
    payload.setdefault("platform", platform.platform())
    manifest = out_dir / "run_manifest.json"
    with open(manifest, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return manifest


def _simnibs_version() -> str:
    try:
        import simnibs
        return getattr(simnibs, "__version__", "unknown")
    except Exception:
        return "simnibs-not-importable"


# ---------------------------------------------------------------------------
# SimNIBS-backed geometry (lazy imports)
# ---------------------------------------------------------------------------
def mni_to_subject(mni_xyz, m2m_dir: Path) -> np.ndarray:
    from simnibs import mni2subject_coords
    return np.asarray(mni2subject_coords(list(mni_xyz), str(m2m_dir))).reshape(-1)


def central_surface(subject: Subject):
    """Return (nodes Nx3, node_areas N, node_normals Nx3, hemi labels N) for lh then rh.

    FIX v0.2: the old loader globbed '*central*.gii' AND '*central*', which loaded every
    file twice, so node arrays no longer matched subject_atlas masks. Order is now fixed
    to lh, rh to match subject_atlas (API-CHECK that order once on Ernie).
    """
    from simnibs import mesh_io
    surf_dir = subject.m2m_dir / "surfaces"
    nodes, areas, normals, hemi = [], [], [], []
    for h in ("lh", "rh"):
        f = surf_dir / f"{h}.central.gii"                   # API-CHECK filename
        if not f.exists():
            raise FileNotFoundError(f"Missing {f}. Check charm 4.6 surface layout.")
        m = mesh_io.read_gifti_surface(str(f))
        xyz = np.asarray(m.nodes.node_coord)
        tri = np.asarray(m.elm.node_number_list)[:, :3] - 1
        nodes.append(xyz)
        areas.append(triangle_node_areas(xyz, tri))
        normals.append(triangle_node_normals(xyz, tri))
        hemi.append(np.full(len(xyz), h))
    return np.vstack(nodes), np.concatenate(areas), np.vstack(normals), np.concatenate(hemi)


def load_central_surface_nodes(subject: Subject) -> np.ndarray:
    return central_surface(subject)[0]


def skin_surface_nodes(subject: Subject) -> np.ndarray:
    """Outer skin surface nodes (tag 1005).

    FIX v0.2: the old code cropped the scalp VOLUME (tag 5); its nearest node to a cortical
    point is usually on the inner scalp boundary, which shortened SCD by the scalp
    thickness and anchored electrodes/coils on the wrong surface.
    """
    from simnibs import read_msh
    mesh = read_msh(str(subject.mesh))
    skin = mesh.crop_mesh(tags=[SKIN_SURFACE_TAG])          # API-CHECK signature
    return np.asarray(skin.nodes.node_coord)


def project_to_scalp(coord_xyz, subject: Subject, skin_nodes: np.ndarray | None = None):
    skin_nodes = skin_surface_nodes(subject) if skin_nodes is None else skin_nodes
    return nearest_point(skin_nodes, coord_xyz)


def eeg_positions(subject: Subject, cap: str) -> dict[str, np.ndarray]:
    """10-10 positions charm wrote for this head (m2m/eeg_positions/<cap>.csv)."""
    f = subject.m2m_dir / "eeg_positions" / f"{cap}.csv"   # API-CHECK path/format
    out: dict[str, np.ndarray] = {}
    with open(f) as fh:
        for row in csv.reader(fh):
            if len(row) >= 5 and row[0].strip().lower() in ("electrode", "fiducial"):
                out[row[4].strip()] = np.array([float(row[1]), float(row[2]), float(row[3])])
    if not out:
        raise RuntimeError(f"No electrode rows parsed from {f}.")
    return out


def nearest_eeg_label(point, positions: dict[str, np.ndarray], exclude=()) -> str:
    best, dmin = None, np.inf
    for lab, xyz in positions.items():
        if lab in exclude:
            continue
        d = float(np.linalg.norm(xyz - np.asarray(point)))
        if d < dmin:
            best, dmin = lab, d
    return best


# ---------------------------------------------------------------------------
# ROI masks
# ---------------------------------------------------------------------------
def _atlas_mask(atlas: dict, labels: list[str], n_nodes: int) -> np.ndarray:
    """Union of atlas labels, matched tolerantly ('L_44' matches 'lh.L_44_ROI')."""
    mask = np.zeros(n_nodes, dtype=bool)
    hits = []
    for key, val in atlas.items():
        k = str(key)
        for lab in labels:
            if k == lab or k.endswith(lab) or f"{lab}_ROI" in k or k.endswith(f".{lab}"):
                arr = np.asarray(val, dtype=bool)
                if arr.shape[0] != n_nodes:
                    raise ValueError(f"Atlas mask length {arr.shape[0]} != surface nodes {n_nodes}")
                mask |= arr
                hits.append(k)
    if not hits:
        raise KeyError(f"No atlas keys matched {labels}. Example keys: {list(atlas)[:5]}")
    return mask


def roi_surface_mask(roi_name: str, roi_cfg: dict, subject: Subject,
                     nodes: np.ndarray | None = None, shift_mm=(0.0, 0.0, 0.0),
                     radius_mm: float | None = None, homolog: bool = False):
    """Boolean mask over central-surface nodes (lh+rh) for one ROI (or its homolog).

    definition: atlas  -> union of atlas_labels (homolog_labels if homolog)
                sphere -> sphere of radius around the MNI seed mapped to subject space
                          (x mirrored if homolog). Seeds outside GM are projected to the
                          nearest surface node when project_seed_to_gm is set.
    Returns (mask, info dict).
    """
    nodes = load_central_surface_nodes(subject) if nodes is None else nodes
    info: dict[str, Any] = {"roi": roi_name, "homolog": homolog}
    if roi_cfg["definition"] == "atlas" and not radius_mm:
        from simnibs import subject_atlas
        atlas = subject_atlas(load_rois().get("atlas", "HCP_MMP1"), str(subject.m2m_dir))
        labels = roi_cfg["homolog_labels"] if homolog else roi_cfg["atlas_labels"]
        mask = _atlas_mask(atlas, labels, len(nodes))
        info["center"] = nodes[mask].mean(axis=0)
        return mask, info
    if roi_cfg["definition"] == "atlas":     # sphere at label centroid (alternate)
        base, _ = roi_surface_mask(roi_name, roi_cfg, subject, nodes, homolog=homolog)
        center = nodes[base].mean(axis=0) + np.asarray(shift_mm)
    else:
        mni = np.asarray(roi_cfg["mni_seed"], dtype=float)
        if homolog:
            mni[0] = -mni[0]
        center = mni_to_subject(mni + np.asarray(shift_mm), subject.m2m_dir)
    if roi_cfg.get("project_seed_to_gm"):
        proj = nearest_point(nodes, center)
        info["seed_projection_mm"] = float(np.linalg.norm(proj - center))
        center = proj
    r = float(radius_mm or roi_cfg["radius_mm"])
    mask = sphere_mask(nodes, center, r)
    info["center"] = center
    return mask, info


# ---------------------------------------------------------------------------
# Pure geometry (unit tested, no SimNIBS)
# ---------------------------------------------------------------------------
def nearest_point(points: np.ndarray, query) -> np.ndarray:
    q = np.asarray(query, dtype=float).reshape(3)
    return points[int(np.argmin(np.linalg.norm(points - q, axis=1)))]


def sphere_mask(points: np.ndarray, center, radius: float) -> np.ndarray:
    return np.linalg.norm(points - np.asarray(center).reshape(3), axis=1) <= radius


def triangle_node_areas(xyz: np.ndarray, tri: np.ndarray) -> np.ndarray:
    """Per-node area = one third of the area of each incident triangle (mm^2)."""
    a, b, c = xyz[tri[:, 0]], xyz[tri[:, 1]], xyz[tri[:, 2]]
    tri_area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    areas = np.zeros(len(xyz))
    for k in range(3):
        np.add.at(areas, tri[:, k], tri_area / 3.0)
    return areas


def triangle_node_normals(xyz: np.ndarray, tri: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals (unit). Orientation follows triangle winding."""
    a, b, c = xyz[tri[:, 0]], xyz[tri[:, 1]], xyz[tri[:, 2]]
    n_tri = np.cross(b - a, c - a)
    normals = np.zeros_like(xyz)
    for k in range(3):
        np.add.at(normals, tri[:, k], n_tri)
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return normals / norm


def local_tangent_basis(surface_points: np.ndarray, center, radius: float = 15.0):
    """Orthonormal (u, v, n) at `center` on a surface, n = outward-ish normal from PCA.

    FIX v0.2: grids and HD rings were built by offsetting along world x/y, which collapses
    onto the scalp for lateral targets (IFG, pSTG, vLMC) where the scalp is near vertical.
    The normal is oriented away from the point cloud centroid (outward for a head).
    """
    c = np.asarray(center, dtype=float).reshape(3)
    near = surface_points[np.linalg.norm(surface_points - c, axis=1) <= radius]
    if len(near) < 6:
        near = surface_points[np.argsort(np.linalg.norm(surface_points - c, axis=1))[:30]]
    _, _, vt = np.linalg.svd(near - near.mean(axis=0), full_matrices=False)
    n = vt[-1]
    if np.dot(n, c - surface_points.mean(axis=0)) < 0:
        n = -n
    ref = np.array([0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(ref, n); u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v, n


def tangent_offsets(radius: float, step: float) -> list[tuple[float, float]]:
    if radius <= 0:
        return [(0.0, 0.0)]
    vals = np.arange(-radius, radius + 1e-9, step)
    return [(a, b) for a in vals for b in vals if a * a + b * b <= radius * radius + 1e-9]


def ring_points(center, u, v, radius: float, n: int = 4, phase_deg: float = 0.0):
    c = np.asarray(center, dtype=float)
    angs = np.deg2rad(phase_deg + np.arange(n) * 360.0 / n)
    return [c + radius * (np.cos(a) * u + np.sin(a) * v) for a in angs]


def rotate_matsimnibs(mat: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate a SimNIBS coil matrix about its own z axis (column 2) by angle_deg.

    matsimnibs columns: x, y (handle), z (into head), centre (API-CHECK convention).
    """
    m = np.array(mat, dtype=float).copy()
    a = np.deg2rad(angle_deg)
    x, y = m[:3, 0].copy(), m[:3, 1].copy()
    m[:3, 0] = np.cos(a) * x + np.sin(a) * y
    m[:3, 1] = -np.sin(a) * x + np.cos(a) * y
    return m


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    v, w = np.asarray(values, float), np.asarray(weights, float)
    if v.size == 0:
        return float("nan")
    order = np.argsort(v)
    v, w = v[order], w[order]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return float(np.interp(q, cw, v))


def default_cond_set(head_id: str, requested: str | None) -> str | None:
    """Lesion-modeled ARC meshes always need a lesion conductivity; default to the primary."""
    if requested:
        return requested
    return "lesion_csf" if head_info(head_id).get("version") == "lesion" else None


def tissue_lengths_along_ray(labels: np.ndarray, affine: np.ndarray, p0, p1,
                             step: float = 0.25) -> dict[int, float]:
    """Path length (mm) through each tissue tag on the segment p0 -> p1 (world mm)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    length = float(np.linalg.norm(p1 - p0))
    if length == 0:
        return {}
    n = max(int(length / step), 1)
    pts = p0 + np.outer((np.arange(n) + 0.5) / n, p1 - p0)
    ijk = np.rint(np.c_[pts, np.ones(n)] @ np.linalg.inv(affine).T)[:, :3].astype(int)
    ok = np.all((ijk >= 0) & (ijk < np.array(labels.shape[:3])), axis=1)
    tags = labels[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]].astype(int)
    seg = length / n
    out: dict[int, float] = {}
    for t in np.unique(tags):
        out[int(t)] = float((tags == t).sum() * seg)
    return out
