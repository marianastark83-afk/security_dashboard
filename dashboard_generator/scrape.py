#!/usr/bin/env python3
"""
Security Intelligence Scraper
==============================
Fetches recent articles from all configured RSS sources, classifies each
article into an incident candidate, and writes the results to a JSON file
that can be reviewed and merged into the dashboard.

Usage
-----
    # Scrape last 7 days (default), write to output/scraped_YYYYMMDD.json
    python scrape.py

    # Scrape last 14 days, require higher confidence
    python scrape.py --days 14 --min-confidence 0.75

    # Write to a specific file
    python scrape.py --output output/my_scrape.json

    # Scrape AND immediately regenerate the dashboard including scraped results
    python scrape.py --generate

    # Skip sources that cover more than one country (dedicated sources only)
    python scrape.py --dedicated-only

Review workflow
---------------
    1. python scrape.py
    2. Open output/scraped_YYYYMMDD.json — review / edit incidents
    3. python generate.py --include-scraped output/scraped_YYYYMMDD.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── package imports ────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from scraper import SOURCES, classify_article, fetch_source


# ── helpers ────────────────────────────────────────────────────────────────

def _clean_for_dashboard(inc: dict) -> dict:
    """Strip internal '_' fields so the dict is safe to inject into the dashboard."""
    return {k: v for k, v in inc.items() if not k.startswith("_")}


def _country_counts(incidents: list) -> dict:
    countries = ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"]
    return {c: sum(1 for i in incidents if i["country"] == c) for c in countries}


def _print_summary(incidents: list, total_articles: int, elapsed: float) -> None:
    print(f"\n{'─'*56}")
    print(f"  Articles fetched   : {total_articles}")
    print(f"  Incidents found    : {len(incidents)}")
    print(f"  Elapsed            : {elapsed:.1f}s")
    print()
    counts = _country_counts(incidents)
    for country, n in counts.items():
        bar = "█" * n
        print(f"  {country:<14} {n:>2}  {bar}")
    sev_c = sum(1 for i in incidents if i["severity"] == "Critical")
    sev_h = sum(1 for i in incidents if i["severity"] == "High")
    sev_m = sum(1 for i in incidents if i["severity"] == "Medium")
    print(f"\n  Critical: {sev_c}  High: {sev_h}  Medium: {sev_m}")
    print(f"{'─'*56}\n")


# ── main scraper ───────────────────────────────────────────────────────────

def scrape(
    days: int = 3,
    min_confidence: float = 0.55,
    dedicated_only: bool = False,
    timeout: int = 20,
) -> tuple:
    """
    Fetch all configured sources and classify articles.

    Returns (incidents: list[dict], total_articles: int).
    Each incident dict contains both dashboard fields and internal '_' metadata.
    """
    import time
    t0 = time.time()

    sources = SOURCES
    if dedicated_only:
        sources = [s for s in sources if len(s.get("countries", [])) <= 2]

    all_incidents = []
    seen_urls     = set()
    total_articles = 0

    print(f"\nScraping {len(sources)} sources — last {days} day(s)\n")

    for source in sources:
        name             = source["name"]
        source_countries = source.get("countries", [])
        lang             = source.get("language", "en")
        lang_tag         = f" [{lang.upper()}]" if lang != "en" else ""

        print(f"  → {name}{lang_tag}")
        articles = fetch_source(source, timeout=timeout)
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
                max_age_days=days,
            )

            if incident and incident["_confidence"] >= min_confidence:
                all_incidents.append(incident)
                classified += 1

        status = f"{len(articles)} articles → {classified} incidents" if articles else "no articles returned"
        print(f"     {status}")

    # Sort: Critical first, then by date descending
    _sev_order = {"Critical": 0, "High": 1, "Medium": 2}
    all_incidents.sort(
        key=lambda x: (_sev_order.get(x["severity"], 3), x["date"]),
        reverse=False,
    )
    all_incidents.sort(key=lambda x: x["date"], reverse=True)

    elapsed = time.time() - t0
    _print_summary(all_incidents, total_articles, elapsed)

    return all_incidents, total_articles


# ── output writers ─────────────────────────────────────────────────────────

def write_json(incidents: list, total_articles: int, output_path: Path, days: int, min_confidence: float) -> None:
    """Write full scrape results to JSON (includes internal '_' metadata)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "scraped_at":      datetime.now(timezone.utc).isoformat(),
        "days_back":       days,
        "min_confidence":  min_confidence,
        "total_articles":  total_articles,
        "total_incidents": len(incidents),
        "by_country":      _country_counts(incidents),
        # incidents include '_confidence' etc. so the analyst can filter/sort
        "incidents": incidents,
    }

    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"✓ Saved → {output_path.resolve()}")


def write_dashboard_json(incidents: list, output_path: Path) -> None:
    """Write a clean JSON (no '_' fields) ready for --include-scraped in generate.py."""
    clean = [_clean_for_dashboard(i) for i in incidents]
    output_path.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── entry point ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape East Africa news sources and classify security incidents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=3,
        metavar="N",
        help="Maximum article age in days to include (default: 3)",
    )
    parser.add_argument(
        "--min-confidence", "-c",
        type=float,
        default=0.55,
        metavar="SCORE",
        help="Minimum classifier confidence 0.0–1.0 (default: 0.55)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        metavar="PATH",
        help="Output JSON path (default: output/scraped_YYYYMMDD.json)",
    )
    parser.add_argument(
        "--dedicated-only",
        action="store_true",
        help="Only use sources dedicated to 1–2 countries (higher signal, lower volume)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        metavar="SEC",
        help="Per-source HTTP timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="After scraping, regenerate the dashboard including scraped incidents",
    )
    args = parser.parse_args()

    # ── run scraper ────────────────────────────────────────────────────────
    incidents, total_articles = scrape(
        days=args.days,
        min_confidence=args.min_confidence,
        dedicated_only=args.dedicated_only,
        timeout=args.timeout,
    )

    # ── write full JSON (with metadata) ────────────────────────────────────
    if args.output:
        output_path = Path(args.output)
    else:
        date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
        output_path = ROOT / "output" / f"scraped_{date_tag}.json"

    write_json(incidents, total_articles, output_path, args.days, args.min_confidence)

    # ── also write a clean version for generate.py ─────────────────────────
    clean_path = output_path.with_name(output_path.stem + "_clean.json")
    write_dashboard_json(incidents, clean_path)

    # ── next steps ─────────────────────────────────────────────────────────
    print("\nNext steps:")
    print(f"  1. Review  : {output_path}")
    print(f"  2. Generate: python generate.py --include-scraped {clean_path}")

    # ── optionally regenerate dashboard immediately ────────────────────────
    if args.generate:
        print("\nRegenerating dashboard…")
        from generate import generate
        gen_path = generate(scraped_path=str(clean_path))
        print(f"  Dashboard : {gen_path}")


if __name__ == "__main__":
    main()
