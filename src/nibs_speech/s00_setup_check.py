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
    for name in ("sim_struct", "opt_struct", "run_simnibs", "mni2subject_coords",
                 "subject_atlas", "read_msh", "mesh_io"):
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
    except Exception as exc:  # noqa: BLE001
        rec("default conductivities", False, exc)

    coil_dir = Path(simnibs.__file__).parent / "resources" / "coil_models"   # API-CHECK path
    files = {p.name for p in coil_dir.rglob("*") if p.suffix in (".ccd", ".tcd", ".nii", ".gz")} if coil_dir.exists() else set()
    rec("coil library", bool(files), coil_dir)
    for key, c in load_coils()["coils"].items():
        rec(f"coil {key}", c["fnamecoil"] in files, c["fnamecoil"] if c["fnamecoil"] in files
            else f"{c['fnamecoil']} not found; candidates: " + ", ".join(sorted(f for f in files if key.split('_')[0][:4].lower() in f.lower())[:6]))
    rec("charm on PATH", shutil.which("charm") is not None, shutil.which("charm") or "")
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
        rec("charm.ini in m2m", (s.m2m_dir / "charm.ini").exists())
        try:
            atlas = simnibs.subject_atlas(load_rois()["atlas"], str(s.m2m_dir))
            keys = list(atlas)
            rec("HCP_MMP1 atlas", True, f"{len(keys)} keys, e.g. {keys[:4]}")
        except Exception as exc:  # noqa: BLE001
            rec("HCP_MMP1 atlas", False, exc)
        try:
            import nibabel as nib, numpy as np
            tags = np.unique(np.asarray(nib.load(str(s.tissues_nii)).dataobj)).astype(int)
            rec("tissue tags present", True, list(tags))
        except Exception as exc:  # noqa: BLE001
            rec("tissue tags present", False, exc)

    rep = REPO_ROOT / "docs" / "verify_report.md"
    rep.parent.mkdir(exist_ok=True)
    rep.write_text("# Verify report (s00)\n\n| Check | Result | Detail |\n|---|---|---|\n" + "\n".join(LINES) + "\n")
    print(f"Report: {rep}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
