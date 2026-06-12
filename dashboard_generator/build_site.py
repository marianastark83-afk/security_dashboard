#!/usr/bin/env python3
"""
build_site.py — Copy the newest pipeline run into the publishable site/ folder.

Layout produced:
    site/index.html              ← newest dashboard (replaces placeholder)
    site/runs/<run_tag>/         ← full run folder for archival access
    site/runs/index.html         ← simple browseable index of all runs

Safe to run when no output/run_* folders exist: leaves placeholder in place
and exits 0.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE      = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
SITE_DIR  = REPO_ROOT / "site"
RUNS_DIR  = SITE_DIR / "runs"
OUTPUT    = HERE / "output"


def newest_run() -> Path | None:
    if not OUTPUT.exists():
        return None
    runs = sorted(
        (p for p in OUTPUT.glob("run_*") if p.is_dir()),
        key=lambda p: p.name,
        reverse=True,
    )
    return runs[0] if runs else None


def find_dashboard_html(run_dir: Path) -> Path | None:
    matches = sorted(run_dir.glob("security_dashboard_*.html"))
    return matches[-1] if matches else None


def write_runs_index() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for run in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run.is_dir():
            continue
        dash = find_dashboard_html(run)
        if dash:
            link = f"runs/{run.name}/{dash.name}"
            rows.append(f'<li><a href="{link}">{run.name}</a></li>')
    html = (
        "<!doctype html><meta charset=utf-8>"
        "<title>Past runs</title>"
        "<style>body{font-family:sans-serif;max-width:640px;margin:2rem auto;"
        "padding:0 1rem;background:#0f172a;color:#e2e8f0}"
        "a{color:#fbbf24}</style>"
        "<h1>Past dashboard runs</h1><ul>"
        + ("".join(rows) if rows else "<li>No runs yet.</li>")
        + "</ul><p><a href='../index.html'>← latest</a></p>"
    )
    (RUNS_DIR / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    run = newest_run()
    if run is None:
        print("build_site: no output/run_* folders found — keeping placeholder.")
        return 0

    dash = find_dashboard_html(run)
    if dash is None:
        print(f"build_site: no dashboard HTML in {run.name} — keeping placeholder.")
        return 0

    # Copy whole run folder for archival
    dest_run = RUNS_DIR / run.name
    if dest_run.exists():
        shutil.rmtree(dest_run)
    shutil.copytree(run, dest_run)

    # Promote newest dashboard to index.html
    shutil.copy2(dash, SITE_DIR / "index.html")

    write_runs_index()

    print(f"build_site: published {run.name}/{dash.name} → site/index.html")
    print(f"build_site: archived  → site/runs/{run.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
