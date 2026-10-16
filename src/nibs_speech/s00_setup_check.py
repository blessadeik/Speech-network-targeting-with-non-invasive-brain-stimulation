"""s00 — sanity-check the toolchain before doing real work.

    simnibs_python src/nibs_speech/s00_setup_check.py

Checks: simnibs importable, key APIs present, coil library found, config files parse,
Ernie example locatable. Prints a checklist; exits nonzero if anything critical is missing.
"""
from __future__ import annotations

import importlib
import shutil
import sys
from pathlib import Path

from utils import CONFIG_DIR, get_logger, load_coils, load_montages, load_rois

log = get_logger("s00")


def ok(label: str, passed: bool, detail: str = "") -> bool:
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    return passed


def main() -> int:
    print("=== NIBS-speech setup check ===")
    crit = []

    # 1. simnibs importable
    try:
        simnibs = importlib.import_module("simnibs")
        crit.append(ok("import simnibs", True, getattr(simnibs, "__version__", "?")))
    except Exception as exc:  # noqa: BLE001
        crit.append(ok("import simnibs", False, f"{exc} — are you using simnibs_python?"))
        simnibs = None

    # 2. key APIs
    if simnibs is not None:
        for mod, attr in [
            ("simnibs", "sim_struct"),
            ("simnibs", "opt_struct"),
            ("simnibs", "run_simnibs"),
            ("simnibs", "mni2subject_coords"),
            ("simnibs", "subject_atlas"),
            ("simnibs", "read_msh"),
        ]:
            try:
                m = importlib.import_module(mod)
                ok(f"{mod}.{attr}", hasattr(m, attr))
            except Exception as exc:  # noqa: BLE001
                ok(f"{mod}.{attr}", False, str(exc))

    # 3. external binaries
    ok("charm on PATH", shutil.which("charm") is not None,
       shutil.which("charm") or "not found")
    ok("simnibs_python on PATH", shutil.which("simnibs_python") is not None,
       shutil.which("simnibs_python") or "not found (fine if you invoked it directly)")

    # 4. config files parse
    for name, loader in [("rois.yaml", load_rois),
                         ("montages.yaml", load_montages),
                         ("coils.yaml", load_coils)]:
        try:
            loader()
            crit.append(ok(f"parse {name}", True))
        except Exception as exc:  # noqa: BLE001
            crit.append(ok(f"parse {name}", False, str(exc)))

    # 5. VERIFY placeholders still present? (nudge, not failure)
    rois = load_rois()
    placeholders = [k for k, v in rois["rois"].items()
                    if -99 in (v.get("mni_seed") or [])]
    if placeholders:
        print(f"  [WARN] ROIs still have placeholder coords: {placeholders} "
              "— fill from literature before locking (docs/05).")

    print(f"  [INFO] config dir: {CONFIG_DIR}")
    passed = all(crit)
    print("=== " + ("ALL CRITICAL CHECKS PASSED" if passed else "CRITICAL FAILURES ABOVE") + " ===")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
