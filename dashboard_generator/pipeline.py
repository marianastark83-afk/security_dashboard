#!/usr/bin/env python3
"""
East Africa Security Intelligence Pipeline
==========================================
Single command that runs the full workflow:

    1. Scrape all configured RSS sources (last N days)
    2. Filter noise, fix misclassifications
    3. Build country profiles dynamically from incidents
    4. Generate the dashboard HTML
    5. Save everything to a new timestamped run folder

Usage:
    python pipeline.py                # last 3 days, default settings
    python pipeline.py --days 7       # extend window
    python pipeline.py --confidence 0.6  # stricter classifier threshold
    python pipeline.py --open         # open dashboard in browser when done

Output:
    output/run_YYYYMMDD_HHMMSS/
        scraped.json        — raw scrape output (with _confidence metadata)
        incidents.json      — filtered, date-windowed incidents
        security_dashboard_YYYYMMDD_HHMMSS.html  — the dashboard
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full East Africa security intelligence pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=3,
        metavar="N",
        help="Reporting window in days (default: 3)",
    )
    parser.add_argument(
        "--confidence", "-c",
        type=float,
        default=0.50,
        metavar="SCORE",
        help="Minimum classifier confidence 0.0–1.0 (default: 0.50)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        metavar="SEC",
        help="Per-source HTTP timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the dashboard in the default browser when done",
    )
    args = parser.parse_args()

    now_utc   = datetime.now(timezone.utc)
    run_tag   = now_utc.strftime("%Y%m%d_%H%M%S")
    run_dir   = ROOT / "output" / f"run_{run_tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    scraped_json = run_dir / "scraped.json"

    print(f"\n{'━'*56}")
    print(f"  East Africa Security Intelligence Pipeline")
    print(f"  Run : {run_tag}  |  Window : last {args.days} day(s)")
    print(f"{'━'*56}")

    # ── STEP 1 : Scrape ───────────────────────────────────────────────────
    print(f"\n[1/2] Scraping sources…\n")
    t0 = time.time()

    from scraper import SOURCES, filter_incidents
    from scraper.fetcher     import fetch_source
    from scraper.classifier  import classify_article
    import json

    all_incidents = []
    seen_urls     = set()
    total_articles = 0

    for source in SOURCES:
        name             = source["name"]
        source_countries = source.get("countries", [])
        lang             = source.get("language", "en")
        tag              = f" [{lang.upper()}]" if lang != "en" else ""
        print(f"  → {name}{tag}")

        articles = fetch_source(source, timeout=args.timeout)
        total_articles += len(articles)
        classified = 0

        for art in articles:
            url = art["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            incident = classify_article(
                title=art["title"],
                description=art["description"],
                source_name=name,
                source_countries=source_countries,
                pub_date=art["pub_date"],
                url=url,
                max_age_days=args.days,
            )
            if incident and incident.get("_confidence", 0) >= args.confidence:
                all_incidents.append(incident)
                classified += 1

        status = f"{len(articles)} articles → {classified} incidents" if articles else "no articles returned"
        print(f"     {status}")

    elapsed = time.time() - t0

    # Sort before saving
    _sev = {"Critical": 0, "High": 1, "Medium": 2}
    all_incidents.sort(key=lambda i: (_sev.get(i.get("severity","Medium"), 2), i.get("date","")))

    # Save full scrape (with _confidence metadata)
    scraped_payload = {
        "scraped_at":     now_utc.isoformat(),
        "run":            run_tag,
        "days_back":      args.days,
        "min_confidence": args.confidence,
        "total_articles": total_articles,
        "total_raw":      len(all_incidents),
        "incidents":      all_incidents,
    }
    scraped_json.write_text(json.dumps(scraped_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n  Articles fetched : {total_articles}")
    print(f"  Raw incidents    : {len(all_incidents)}")
    print(f"  Elapsed          : {elapsed:.1f}s")
    print(f"  Saved            : {scraped_json.name}")

    # ── STEP 2 : Generate dashboard ───────────────────────────────────────
    print(f"\n[2/2] Generating dashboard…")

    from generate import generate

    dashboard_path = generate(
        scraped_path=scraped_json,
        run_dir=run_dir,
        days=args.days,
    )

    # ── Done ─────────────────────────────────────────────────────────────
    print(f"\n{'━'*56}")
    print(f"  Pipeline complete")
    print(f"  Run folder : output/run_{run_tag}/")
    print(f"  Dashboard  : {dashboard_path.name}")
    print(f"{'━'*56}\n")

    if args.open:
        import subprocess as sp
        sp.run(["open", str(dashboard_path.resolve())], check=False)


if __name__ == "__main__":
    main()
