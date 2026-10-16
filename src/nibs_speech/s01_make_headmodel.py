"""s01 — build a SimNIBS head model with charm.

    simnibs_python src/nibs_speech/s01_make_headmodel.py \
        --subject ernie --t1 <path>/ernie_T1.nii.gz [--t2 <path>/ernie_T2.nii.gz]

Wraps `charm <subject> <T1> [T2]`, writing m2m_<subject> under data/m2m/. charm does the
heavy lifting (segmentation + tetrahedral meshing). This script just standardizes paths,
logs a manifest, and points you at the QC report.

Batch mode: pass --manifest a CSV with columns subject,t1,t2 to build many heads.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

from utils import Subject, abspath, get_logger, load_paths, write_manifest

log = get_logger("s01")


def run_charm(subid: str, t1: str, t2: str | None, force: bool) -> Path:
    paths = load_paths()
    m2m_root = abspath(paths["data"]["m2m"])
    m2m_root.mkdir(parents=True, exist_ok=True)

    cmd = ["charm", subid, str(t1)]
    if t2:
        cmd.append(str(t2))
    if force:
        cmd.append("--forceqform")  # API-CHECK: adjust to your charm flags; --forcerun etc.

    log.info("Running: %s (cwd=%s)", " ".join(cmd), m2m_root)
    # charm writes m2m_<subid> into the CWD, so run it inside data/m2m.
    proc = subprocess.run(cmd, cwd=str(m2m_root))
    if proc.returncode != 0:
        raise RuntimeError(f"charm failed for {subid} (exit {proc.returncode}). "
                           "Check the charm log; common causes: bad NIfTI, RAM, PATH.")

    subj = Subject(subid)
    if not subj.m2m_dir.exists():
        raise RuntimeError(f"charm reported success but {subj.m2m_dir} missing.")
    write_manifest(subj.m2m_dir, {"stage": "s01_headmodel", "subject": subid,
                                  "t1": str(t1), "t2": str(t2), "cmd": " ".join(cmd)})
    report = subj.m2m_dir / "charm_report.html"
    log.info("Head model ready: %s", subj.m2m_dir)
    log.info("QC report (open in browser): %s", report if report.exists() else "(look for *_report.html)")
    return subj.m2m_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject")
    ap.add_argument("--t1")
    ap.add_argument("--t2", default=None)
    ap.add_argument("--manifest", help="CSV with columns subject,t1,t2 for batch mode")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.manifest:
        rows = list(csv.DictReader(open(args.manifest)))
        log.info("Batch: %d subjects from %s", len(rows), args.manifest)
        failures = []
        for r in rows:
            try:
                run_charm(r["subject"], r["t1"], r.get("t2") or None, args.force)
            except Exception as exc:  # noqa: BLE001
                log.error("Subject %s FAILED: %s", r.get("subject"), exc)
                failures.append(r.get("subject"))
        if failures:
            log.warning("Failed subjects (exclude & document): %s", failures)
            return 1
        return 0

    if not (args.subject and args.t1):
        ap.error("provide --subject and --t1 (or --manifest for batch)")
    run_charm(args.subject, args.t1, args.t2, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
