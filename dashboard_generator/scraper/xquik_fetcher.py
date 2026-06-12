"""
Xquik X (Twitter) fetcher.

Fetches recent tweets from an X user via the Xquik REST API. Returns
articles in the same shape as scraper.fetcher.fetch_rss so the rest of
the pipeline (classifier, dedup, build) does not need to change.

Auth
----
Requires environment variable XQUIK_API_KEY. If not set, the fetcher
returns [] for every call without raising — the pipeline keeps running
on RSS sources only.

Endpoint
--------
GET https://xquik.com/api/v1/x/users/{username}/tweets?limit=N
Header: X-API-Key: <key>
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

_BASE = "https://xquik.com/api/v1"
_DEFAULT_LIMIT = 25


def _api_key() -> Optional[str]:
    key = os.environ.get("XQUIK_API_KEY", "").strip()
    return key or None


def _parse_x_date(raw: str) -> str:
    """Parse 'Fri Jun 12 10:08:42 +0000 2026' style → ISO-8601 UTC."""
    if not raw:
        return ""
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        try:
            dt = datetime.strptime(raw, "%a %b %d %H:%M:%S %z %Y")
            return dt.astimezone(timezone.utc).isoformat()
        except Exception:
            return ""


def fetch_xquik_user(
    handle: str,
    source_name: str,
    timeout: int = 20,
    limit: int = _DEFAULT_LIMIT,
) -> list:
    """
    Fetch recent tweets for an X user via Xquik.

    Returns a list of article dicts {title, description, url, pub_date}
    matching the shape produced by scraper.fetcher.fetch_rss.

    Never raises — returns [] on any failure (missing key, HTTP error,
    parse error, etc.).
    """
    if not _HAS_REQUESTS:
        print("  ✗ requests not installed — Xquik fetcher disabled", file=sys.stderr)
        return []

    key = _api_key()
    if not key:
        print(f"  ↳ {source_name}: XQUIK_API_KEY not set — skipping", file=sys.stderr)
        return []

    username = handle.lstrip("@").strip()
    if not username:
        return []

    url = f"{_BASE}/x/users/{username}/tweets"
    try:
        resp = _requests.get(
            url,
            headers={"X-API-Key": key, "Accept": "application/json"},
            params={"limit": limit},
            timeout=timeout,
        )
    except _requests.exceptions.Timeout:
        print(f"  ✗ {source_name}: Xquik timed out after {timeout}s", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  ✗ {source_name}: Xquik request failed — {e}", file=sys.stderr)
        return []

    if resp.status_code == 402:
        print(f"  ✗ {source_name}: Xquik 402 — quota exhausted or plan required", file=sys.stderr)
        return []
    if resp.status_code == 401 or resp.status_code == 403:
        print(f"  ✗ {source_name}: Xquik {resp.status_code} — auth rejected", file=sys.stderr)
        return []
    if resp.status_code == 404:
        print(f"  ✗ {source_name}: Xquik 404 — @{username} not found", file=sys.stderr)
        return []
    if resp.status_code != 200:
        print(f"  ✗ {source_name}: Xquik HTTP {resp.status_code}", file=sys.stderr)
        return []

    try:
        data = resp.json()
    except Exception:
        print(f"  ✗ {source_name}: Xquik returned non-JSON", file=sys.stderr)
        return []

    tweets = data.get("tweets") or data.get("data") or []
    if not isinstance(tweets, list):
        return []

    articles = []
    for t in tweets:
        if not isinstance(t, dict):
            continue
        text = (t.get("text") or "").strip()
        link = t.get("url") or ""
        if not text or not link:
            continue
        # Use first line / first 90 chars as title; full text as description.
        title = text.split("\n", 1)[0].strip()
        if len(title) > 110:
            title = title[:107].rstrip() + "…"
        pub = _parse_x_date(t.get("createdAt") or t.get("created_at") or "")
        articles.append({
            "title":       title,
            "description": text[:600],
            "url":         link,
            "pub_date":    pub,
        })
    return articles
