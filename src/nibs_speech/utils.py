"""Shared helpers: config/paths loading, subject paths, logging, ROI geometry.

Kept dependency-light so it imports even before SimNIBS-only libs are needed. SimNIBS
imports are done lazily inside the functions that need them, so this module also imports
fine under a plain python for editing/linting.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Repo layout
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r") as fh:
        return yaml.safe_load(fh)


def load_paths() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "paths.yaml")


def load_rois() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "rois.yaml")


def load_montages() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "montages.yaml")


def load_coils() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "coils.yaml")


def abspath(rel: str | Path) -> Path:
    """Resolve a repo-relative path from paths.yaml to an absolute Path."""
    p = Path(rel)
    return p if p.is_absolute() else (REPO_ROOT / p)


# ---------------------------------------------------------------------------
# Subject bookkeeping
# ---------------------------------------------------------------------------
@dataclass
class Subject:
    subid: str
    paths: dict[str, Any] = field(default_factory=load_paths)

    @property
    def m2m_dir(self) -> Path:
        return abspath(self.paths["data"]["m2m"]) / f"m2m_{self.subid}"

    @property
    def mesh(self) -> Path:
        # charm writes <subid>.msh alongside m2m_<subid>
        return self.m2m_dir.parent / f"{self.subid}.msh"

    def result_dir(self, kind: str) -> Path:
        d = abspath(self.paths["results"][kind]) / self.subid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def require_headmodel(self) -> None:
        if not self.m2m_dir.exists():
            raise FileNotFoundError(
                f"No head model at {self.m2m_dir}. Run s01_make_headmodel.py first."
            )


# ---------------------------------------------------------------------------
# Logging + run manifests (reproducibility)
# ---------------------------------------------------------------------------
def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=os.environ.get("NIBS_LOGLEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    return logging.getLogger(name)


def write_manifest(out_dir: Path, payload: dict[str, Any]) -> Path:
    """Record versions/config/args next to outputs so any run is reconstructable."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload.setdefault("simnibs_version", _simnibs_version())
    manifest = out_dir / "run_manifest.json"
    with open(manifest, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return manifest


def _simnibs_version() -> str:
    try:
        import simnibs  # noqa: WPS433 (lazy import by design)

        return getattr(simnibs, "__version__", "unknown")
    except Exception:  # pragma: no cover - simnibs absent when editing
        return "simnibs-not-importable"


# ---------------------------------------------------------------------------
# ROI geometry helpers (SimNIBS imported lazily)
# ---------------------------------------------------------------------------
def mni_to_subject(mni_xyz, m2m_dir: Path):
    """Map an MNI coordinate (or Nx3 array) to subject space for one head model."""
    from simnibs import mni2subject_coords  # lazy

    return mni2subject_coords(list(mni_xyz), str(m2m_dir))


def roi_surface_mask(roi_name: str, roi_cfg: dict, subject: "Subject"):
    """Return a boolean node mask on the central GM surface for one ROI.

    Strategy (see docs/05_roi_definitions.md):
      1. Map the MNI seed to subject space, build a sphere of ``radius_mm`` around it on the
         central surface nodes.
      2. If ``atlas_labels`` is set, intersect the sphere with the union of those HCP-MMP1
         labels (via simnibs.subject_atlas).

    Returns (mask, node_coords) where mask is a boolean array over central-surface nodes.

    API-CHECK: confirm subject_atlas signature/label names and the central-surface loader
    on first run against your SimNIBS version; the shape of the returned structures is what
    downstream code depends on.
    """
    import numpy as np
    from simnibs import subject_atlas  # lazy

    nodes = load_central_surface_nodes(subject)  # (N, 3) subject-space coords
    seed = np.asarray(mni_to_subject(roi_cfg["mni_seed"], subject.m2m_dir)).reshape(3)
    radius = float(roi_cfg["radius_mm"])
    sphere = np.linalg.norm(nodes - seed, axis=1) <= radius

    labels = roi_cfg.get("atlas_labels")
    if labels:
        atlas = subject_atlas(subject.paths.get("atlas", "HCP_MMP1")
                              if isinstance(subject.paths, dict) else "HCP_MMP1",
                              str(subject.m2m_dir))
        lab_mask = np.zeros(nodes.shape[0], dtype=bool)
        for lab in labels:
            if lab in atlas:
                lab_mask |= np.asarray(atlas[lab], dtype=bool)
        mask = sphere & lab_mask
        # Fallback: if intersection is empty (label mismatch), warn and use sphere.
        if not mask.any():
            get_logger("utils").warning(
                "ROI %s: sphere∩atlas empty (check label names %s); using sphere only.",
                roi_name, labels,
            )
            mask = sphere
    else:
        mask = sphere
    return mask, nodes


def load_central_surface_nodes(subject: "Subject"):
    """Load central GM surface node coordinates (both hemispheres concatenated).

    API-CHECK: SimNIBS stores central surfaces under m2m_<sub>/surfaces/. This helper reads
    them via simnibs.mesh_io; confirm the exact filenames (e.g. lh.central.gii /
    <sub>.central.gii) for your version. Kept in one place so a version fix touches one line.
    """
    import numpy as np
    from simnibs import mesh_io  # lazy

    surf_dir = subject.m2m_dir / "surfaces"
    candidates = sorted(surf_dir.glob("*central*.gii")) + sorted(surf_dir.glob("*central*"))
    if not candidates:
        raise FileNotFoundError(
            f"No central surface found under {surf_dir}. "
            "Confirm charm output layout for your SimNIBS version (API-CHECK)."
        )
    coords = []
    for f in candidates:
        try:
            m = mesh_io.read_gifti_surface(str(f))
            coords.append(np.asarray(m.nodes.node_coord))
        except Exception:
            continue
    if not coords:
        raise RuntimeError(f"Could not read any central surface in {surf_dir}.")
    return np.vstack(coords)


def project_to_scalp(coord_xyz, subject: "Subject"):
    """Project a cortical coordinate outward to the nearest scalp mesh point.

    Used to anchor ROI-centered electrodes/coils that lack a 10-10 landmark (e.g. LMC).

    API-CHECK: implement via nearest scalp node on the head mesh (tag 5 = skin) using
    simnibs.read_msh; confirm skin tag for your version.
    """
    import numpy as np
    from simnibs import read_msh  # lazy

    mesh = read_msh(str(subject.mesh))
    skin = mesh.crop_mesh(5)  # API-CHECK: skin tissue tag
    skin_nodes = np.asarray(skin.nodes.node_coord)
    idx = int(np.argmin(np.linalg.norm(skin_nodes - np.asarray(coord_xyz), axis=1)))
    return skin_nodes[idx]
