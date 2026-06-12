#!/usr/bin/env python3
"""
Security Intelligence Dashboard Generator
=========================================
Usage:
    python generate.py --scraped output/run_20260531_120000/scraped.json
    python generate.py --scraped output/run_20260531_120000/scraped.json --days 3
    python generate.py --scraped output/run_20260531_120000/scraped.json --run-dir output/run_20260531_120000

Country profiles, severity levels, regions, operational implications and
recommended actions are all built automatically from the scraped incidents.
No historical data is retained between runs.

Run pipeline.py instead of this script directly for the full automated workflow.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from collections import defaultdict

from data import COUNTRY_META, SOCIAL_MONITORS
from scraper import filter_incidents, build_country_profiles


# ── per-country sparkline history (last N days) ──────────────────────────────

def _load_history(window_days: int = 14, current_incidents: list = None) -> dict:
    """
    Scan past run folders (local output/run_* and repo site/runs/run_*) and
    return a per-country, per-day count map suitable for sparklines.

    Output: {"Sudan": [c0, c1, ..., c{N-1}], ...} where index 0 is the oldest
    day in the window and the last index is today.
    """
    repo_root = ROOT.parent
    daily = defaultdict(lambda: defaultdict(int))   # {country: {date: count}}

    # Past runs persisted in the repo (CI) + local output dir (dev)
    seen_runs = set()
    for base in (ROOT / "output", repo_root / "site" / "runs"):
        if not base.exists():
            continue
        for run in base.glob("run_*"):
            if not run.is_dir() or run.name in seen_runs:
                continue
            seen_runs.add(run.name)
            ij = run / "incidents.json"
            if not ij.exists():
                continue
            try:
                items = json.loads(ij.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(items, list):
                continue
            for inc in items:
                c = inc.get("country")
                d = (inc.get("date") or "")[:10]
                if c and d:
                    daily[c][d] += 1

    # Always include the current run's counts (in case it's the very first one)
    if current_incidents:
        for inc in current_incidents:
            c = inc.get("country")
            d = (inc.get("date") or "")[:10]
            if c and d:
                daily[c][d] = max(daily[c][d], 0)  # don't double-count; current run is in output/
                # use max — past run for the same date may exist if pipeline ran twice today

    # Build the trailing N-day window ending today
    today = datetime.now(timezone.utc).date()
    days = [(today - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(window_days - 1, -1, -1)]

    history = {}
    for country, counts in daily.items():
        history[country] = [counts.get(d, 0) for d in days]
    return history


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_scraped(path: Path) -> list:
    """Load a scraped JSON file (bare list or {incidents:[...]} dict)."""
    if not path.exists():
        print(f"  ⚠  File not found: {path}", file=sys.stderr)
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        items = raw.get("incidents", [])
    elif isinstance(raw, list):
        items = raw
    else:
        print(f"  ⚠  Unrecognised format: {path}", file=sys.stderr)
        return []
    # Strip internal metadata fields
    return [{k: v for k, v in i.items() if not k.startswith("_")} for i in items]


def _deduplicate(incidents: list) -> list:
    seen, out = set(), []
    for inc in incidents:
        key = inc.get("sourceUrl", "")
        if key and key in seen:
            continue
        seen.add(key)
        out.append(inc)
    return out


def _date_filter(incidents: list, days: int, now_utc: datetime) -> list:
    cutoff = (now_utc - timedelta(days=days)).strftime("%Y-%m-%d")
    kept = [i for i in incidents if i.get("date", "") >= cutoff]
    print(f"  ↳ Date filter : last {days} days (≥ {cutoff}) — {len(kept)}/{len(incidents)} kept")
    return kept


# ── generator ─────────────────────────────────────────────────────────────────

def generate(
    scraped_path: Path,
    run_dir: Optional[Path] = None,
    days: int = 3,
    report_date: Optional[str] = None,
) -> Path:
    """
    Generate the security dashboard HTML.

    Args:
        scraped_path : Path to raw scraped JSON (from scrape.py).
        run_dir      : Output directory. Defaults to output/run_YYYYMMDD_HHMMSS/
        days         : Reporting window in days; incidents outside are dropped.
        report_date  : Header date string. Defaults to current UTC datetime.

    Returns:
        Path to the generated HTML file.
    """
    now_utc = datetime.now(timezone.utc)

    if report_date is None:
        report_date = now_utc.strftime("%d %b %Y, %H:%M UTC")
    short_date = now_utc.strftime("%d %b %Y")

    # ── output folder ──────────────────────────────────────────────────────
    if run_dir is None:
        run_dir = ROOT / "output" / f"run_{now_utc.strftime('%Y%m%d_%H%M%S')}"
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # ── load → filter → deduplicate → date-window ─────────────────────────
    print(f"\n  Loading scraped data from {scraped_path.name}…")
    raw_incidents = _load_scraped(scraped_path)
    print(f"  Raw incidents  : {len(raw_incidents)}")

    filtered   = filter_incidents(raw_incidents)
    print(f"  After filter   : {len(filtered)}")

    deduped    = _deduplicate(filtered)
    incidents  = _date_filter(deduped, days, now_utc)

    # ── build country profiles ─────────────────────────────────────────────
    print(f"  Building country profiles…")
    countries = build_country_profiles(incidents, COUNTRY_META, days=days)

    # ── sort incidents: Critical first, then date desc ─────────────────────
    _sev = {"Critical": 0, "High": 1, "Medium": 2}
    incidents.sort(key=lambda i: (_sev.get(i.get("severity","Medium"), 2), i.get("date","")))

    # ── save clean incidents JSON to run folder ────────────────────────────
    clean_json = run_dir / "incidents.json"
    clean_json.write_text(json.dumps(incidents, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── load and fill template ─────────────────────────────────────────────
    template_path = ROOT / "template.html"
    if not template_path.exists():
        sys.exit(f"ERROR: template.html not found at {template_path}")

    template = template_path.read_text(encoding="utf-8")

    # ── source count (for header subtitle) ─────────────────────────────────
    try:
        from scraper.sources import SOURCES as _SRC
        total_sources = len(_SRC)
    except Exception:
        total_sources = 0

    # ── per-country 14-day history (sparklines + chart comparison) ─────────
    country_history = _load_history(window_days=14, current_incidents=incidents)

    html = (
        template
        .replace("__INCIDENTS_DATA__",       json.dumps(incidents,      ensure_ascii=False, separators=(",", ":")))
        .replace("__COUNTRIES_DATA__",       json.dumps(countries,      ensure_ascii=False, separators=(",", ":")))
        .replace("__SOCIAL_MONITORS_DATA__", json.dumps(SOCIAL_MONITORS,ensure_ascii=False, separators=(",", ":")))
        .replace("__GENERATED_DATE__",       report_date)
        .replace("__REPORT_DATE__",          short_date)
        .replace("__TOTAL_INCIDENTS__",      str(len(incidents)))
        .replace("__TOTAL_SOURCES__",        str(total_sources))
        .replace("__TIME_WINDOW_DAYS__",     str(days))
        .replace("__COUNTRY_HISTORY__",      json.dumps(country_history, ensure_ascii=False, separators=(",", ":")))
    )

    out_html = run_dir / f"security_dashboard_{now_utc.strftime('%Y%m%d_%H%M%S')}.html"
    out_html.write_text(html, encoding="utf-8")

    # ── summary ───────────────────────────────────────────────────────────
    by_country = {c["name"]: len([i for i in incidents if i.get("country")==c["name"]]) for c in countries}
    crit_n = sum(1 for i in incidents if i.get("severity") == "Critical")
    high_n = sum(1 for i in incidents if i.get("severity") == "High")

    print(f"\n✓  Dashboard generated")
    print(f"   Run folder : {run_dir.resolve()}")
    print(f"   File       : {out_html.name}")
    print(f"   Window     : last {days} days ({short_date})")
    print(f"   Incidents  : {len(incidents)} total  ({crit_n} Critical · {high_n} High)")
    print(f"   By country : {' · '.join(f'{k} {v}' for k,v in by_country.items() if v)}")

    return out_html


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the East Africa Security Intelligence Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scraped", "-s",
        metavar="JSON_PATH",
        required=True,
        help="Path to scraped JSON file from scrape.py",
    )
    parser.add_argument(
        "--days", "-n",
        type=int,
        default=3,
        metavar="N",
        help="Reporting window in days (default: 3)",
    )
    parser.add_argument(
        "--run-dir",
        metavar="DIR",
        default=None,
        help="Output directory (default: output/run_YYYYMMDD_HHMMSS/)",
    )
    parser.add_argument(
        "--date", "-d",
        metavar="DATE",
        default=None,
        help="Report date string for the header (default: current UTC datetime)",
    )
    args = parser.parse_args()
    generate(
        scraped_path=Path(args.scraped),
        run_dir=Path(args.run_dir) if args.run_dir else None,
        days=args.days,
        report_date=args.date,
    )


if __name__ == "__main__":
    main()
