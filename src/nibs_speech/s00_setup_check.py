"""s00: toolchain check and API-CHECK sweep (Stage 1). Writes docs/verify_report.md.

    simnibs_python src/nibs_speech/s00_setup_check.py [--head ernie]

Reports, for the installed SimNIBS: version, key entry points, attributes the pipeline sets
(TDCSLEADFIELD, TDCSoptimize targets/avoid, TMSoptimize incl. method/target_size), coil
files named in config/coils.yaml, default conductivities, and (with --head) the m2m
layout the code assumes: <head>.msh inside m2m, surfaces/lh|rh.central.gii,
eeg_positions/<cap>.csv, final_tissues.nii.gz, tissue tags present, HCP_MMP1 atlas keys.
Exits nonzero on critical failures. Nothing here is guessed: it inspects the install.
"""
from __future__ import annotations

import argparse
import importlib
import platform
import shutil
import sys
from pathlib import Path

from utils import (REPO_ROOT, Subject, get_logger, load_coils, load_config, load_montages,
                   load_rois)

log = get_logger("s00")
LINES: list[str] = []


def rec(label, passed, detail="", critical=False):
    mark = "PASS" if passed else ("FAIL" if critical else "WARN")
    LINES.append(f"| {label} | {mark} | {str(detail).replace('|', '/')} |")
    print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))
    return passed or not critical


def has_attr(obj, name):
    return hasattr(obj, name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--head", default=None)
    args = ap.parse_args()
    ok = True
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        rec("platform", True, "Apple Silicon: run charm on Linux/HPC (SimNIBS issue #675)")
    try:
        simnibs = importlib.import_module("simnibs")
        ver = getattr(simnibs, "__version__", "?")
        ok &= rec("import simnibs", True, ver, critical=True)
        ok &= rec("version pinned", ver.startswith(load_config("study")["simnibs_version"]), ver, critical=True)
    except Exception as exc:  # noqa: BLE001
        rec("import simnibs", False, f"{exc}; use simnibs_python", critical=True)
        return 1

    from simnibs import opt_struct, sim_struct
    # 4.6.0 has no simnibs.subject_atlas; atlas2subject is the API (utils.subject_atlas_masks)
    for name in ("sim_struct", "opt_struct", "run_simnibs", "mni2subject_coords",
                 "atlas2subject", "read_msh", "mesh_io"):
        ok &= rec(f"simnibs.{name}", hasattr(simnibs, name), critical=True)
    checks = {
        "TDCSLEADFIELD": (sim_struct, ["eeg_cap", "electrode", "subpath", "pathfem", "cond", "interpolation"]),
        "TDCSoptimize": (opt_struct, ["leadfield_hdf", "max_total_current", "max_individual_current",
                                      "max_active_electrodes", "add_target", "add_avoid", "name"]),
        "TMSoptimize": (opt_struct, ["subpath", "fnamehead", "fnamecoil", "target", "target_size",
                                     "distance", "search_radius", "spatial_resolution",
                                     "search_angle", "angle_resolution", "method", "cond"]),
        "TMSLIST": (sim_struct, ["fnamecoil", "add_position", "cond"]),
        "TDCSLIST": (sim_struct, ["add_electrode", "currents", "cond"]),
    }
    for cls, (mod, attrs) in checks.items():
        try:
            inst = getattr(mod, cls)()
            for a in attrs:
                rec(f"{cls}.{a}", has_attr(inst, a))
        except Exception as exc:  # noqa: BLE001
            rec(cls, False, exc, critical=True)
    try:
        t = opt_struct.TDCSoptimize().add_target()
        for a in ("positions", "directions", "intensity", "radius"):
            rec(f"TDCStarget.{a}", has_attr(t, a))
        av = opt_struct.TDCSoptimize().add_avoid()
        for a in ("positions", "radius", "weight", "tissues"):
            rec(f"TDCSavoid.{a}", has_attr(av, a))
    except Exception as exc:  # noqa: BLE001
        rec("TDCS target/avoid", False, exc)
    try:
        c = sim_struct.TDCSLIST().cond
        rec("default conductivities", True, ", ".join(f"{x.name}={x.value}" for x in c if x.name))
        installed = {x.name: x.value for x in c if x.name}
        alias = {"Eye": "Eye_balls"}
        cfg = load_config("conductivity")["defaults"]
        diff = {k: (v, installed.get(alias.get(k, k))) for k, v in cfg.items()
                if installed.get(alias.get(k, k)) != v}
        rec("conductivity.yaml matches installed", not diff, diff or "")
    except Exception as exc:  # noqa: BLE001
        rec("default conductivities", False, exc)

    coil_dir = Path(simnibs.__file__).parent / "resources" / "coil_models"   # verified in 4.6.0 (searched recursively)
    files = {p.name for p in coil_dir.rglob("*") if p.suffix in (".ccd", ".tcd", ".nii", ".gz")} if coil_dir.exists() else set()
    rec("coil library", bool(files), coil_dir)
    for key, c in load_coils()["coils"].items():
        rec(f"coil {key}", c["fnamecoil"] in files, c["fnamecoil"] if c["fnamecoil"] in files
            else f"{c['fnamecoil']} not found; candidates: " + ", ".join(sorted(f for f in files if key.split('_')[0][:4].lower() in f.lower())[:6]))
    charm = shutil.which("charm")
    bundled = Path(sys.executable).resolve().parent.parent / "bin"     # <install>/bin (Windows)
    rec("charm on PATH", charm is not None, charm or (
        f"not on PATH; SimNIBS bin is {bundled}" if (bundled / "charm.cmd").exists()
        else "not found; only needed for s01"))
    for name in ("rois", "montages", "coils", "conductivity", "lesion", "ksweep", "study", "paths"):
        try:
            load_config(name)
            rec(f"config {name}.yaml", True)
        except Exception as exc:  # noqa: BLE001
            ok &= rec(f"config {name}.yaml", False, exc, critical=True)

    if args.head:
        s = Subject(args.head)
        rec("m2m folder", s.m2m_dir.exists(), s.m2m_dir, critical=True)
        rec("mesh inside m2m", (s.m2m_dir / f"{args.head}.msh").exists(), s.mesh)
        for h in ("lh", "rh"):
            rec(f"surfaces/{h}.central.gii", (s.m2m_dir / "surfaces" / f"{h}.central.gii").exists())
        cap = load_montages()["defaults"]["cap"]
        rec("eeg cap csv", (s.m2m_dir / "eeg_positions" / f"{cap}.csv").exists(), cap)
        rec("final_tissues.nii.gz", s.tissues_nii.exists())
        rec("charm settings.ini in m2m", s.charm_settings.exists(), s.charm_settings.name)
        try:
            from utils import _atlas_mask, central_surface, subject_atlas_masks
            atlas = subject_atlas_masks(s)
            keys = list(atlas)
            n_nodes = len(central_surface(s)[0])
            n_mask = len(next(iter(atlas.values())))
            rec("HCP_MMP1 atlas", n_mask == n_nodes,
                f"{len(keys)} keys, e.g. {keys[1:4]}; mask length {n_mask} vs surface {n_nodes}",
                critical=True)
            for roi, cfg in load_rois()["rois"].items():
                if cfg.get("definition") != "atlas":
                    continue
                for key in ("atlas_labels", "homolog_labels"):
                    labs = cfg.get(key) or []
                    missing = [l for l in labs if l not in atlas]
                    if not missing:
                        n = int(_atlas_mask(atlas, labs, n_nodes).sum())
                        rec(f"ROI {roi} {key}", True, f"{labs}: {n} nodes")
                    else:
                        rec(f"ROI {roi} {key}", False, f"not in atlas: {missing}")
        except Exception as exc:  # noqa: BLE001
            ok &= rec("HCP_MMP1 atlas", False, exc, critical=True)
        try:
            import nibabel as nib, numpy as np
            tags = np.unique(np.asarray(nib.load(str(s.tissues_nii)).dataobj)).astype(int)
            rec("tissue tags present", True, [int(t) for t in tags])
            from utils import TAG
            et = {t.name: int(t.value) for t in simnibs.ElementTags}
            want = {"WM": "WM", "GM": "GM", "CSF": "CSF", "Bone": "BONE", "Scalp": "SCALP",
                    "Eye": "EYE_BALLS", "Compact_bone": "COMPACT_BONE",
                    "Spongy_bone": "SPONGY_BONE", "Blood": "BLOOD", "Muscle": "MUSCLE"}
            bad = [k for k, v in want.items() if TAG[k] != et.get(v)]
            rec("utils.TAG matches ElementTags", not bad, bad or "", critical=True)
        except Exception as exc:  # noqa: BLE001
            rec("tissue tags present", False, exc)

    rep = REPO_ROOT / "docs" / "verify_report.md"
    rep.parent.mkdir(exist_ok=True)
    rep.write_text("# Verify report (s00)\n\n| Check | Result | Detail |\n|---|---|---|\n" + "\n".join(LINES) + "\n")
    print(f"Report: {rep}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
