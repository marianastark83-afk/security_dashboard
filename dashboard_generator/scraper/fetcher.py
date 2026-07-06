"""
RSS / Atom feed fetcher with graceful error handling.

Uses feedparser for parsing and requests for the HTTP layer so we can
set a proper User-Agent and timeout. Falls back to feedparser's built-in
URL fetching if requests isn't available.
"""

import re
import sys
from datetime import datetime, timezone
from typing import Optional

# feedparser is required; requests is preferred but optional for the HTTP layer.
try:
    import feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# A realistic desktop-browser UA. The previous self-identifying bot string was
# rejected with HTTP 403 by Cloudflare-fronted sites (Sudan Tribune, Addis
# Standard, Daily Nation, The East African, Borkena, etc.).
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_TAG_RE   = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    return _SPACE_RE.sub(" ", _TAG_RE.sub(" ", text or "")).strip()


def _parse_date(entry) -> Optional[str]:
    """Return ISO-8601 UTC date string from a feedparser entry, or None."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return None


def _entries_to_articles(feed, source_name: str) -> list:
    """Convert feedparser entries into plain dicts."""
    articles = []
    for entry in feed.get("entries", []):
        title = _strip_html(entry.get("title", ""))
        # Try summary → content[0] → description for body text
        body = entry.get("summary", "")
        if not body and entry.get("content"):
            body = entry["content"][0].get("value", "")
        body = _strip_html(body)[:600]   # keep it bounded
        link = entry.get("link", "")

        if not title or not link:
            continue

        articles.append({
            "title":       title,
            "description": body,
            "url":         link,
            "pub_date":    _parse_date(entry) or "",
        })
    return articles


def fetch_rss(url: str, source_name: str, timeout: int = 20) -> list:
    """
    Fetch and parse a single RSS/Atom feed URL.

    Returns a list of article dicts:
      {title, description, url, pub_date (ISO str or '')}

    Never raises — returns [] on any failure.
    """
    if not _HAS_FEEDPARSER:
        print(
            "  ✗ feedparser not installed. Run: pip install feedparser",
            file=sys.stderr,
        )
        return []

    # Fetch raw bytes via requests so we control UA and timeout.
    if _HAS_REQUESTS:
        try:
            resp = _requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except _requests.exceptions.ConnectionError:
            print(f"  ✗ {source_name}: connection failed ({url})", file=sys.stderr)
            return []
        except _requests.exceptions.Timeout:
            print(f"  ✗ {source_name}: timed out after {timeout}s", file=sys.stderr)
            return []
        except _requests.exceptions.HTTPError as e:
            print(f"  ✗ {source_name}: HTTP {e.response.status_code}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"  ✗ {source_name}: {e}", file=sys.stderr)
            return []
    else:
        # Fallback: let feedparser handle the HTTP fetch directly
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"  ✗ {source_name}: {e}", file=sys.stderr)
            return []

    # feedparser sets bozo=True on malformed feeds but usually still parses them.
    if feed.get("bozo") and not feed.get("entries"):
        exc = feed.get("bozo_exception", "")
        print(f"  ✗ {source_name}: malformed feed — {exc}", file=sys.stderr)
        return []

    articles = _entries_to_articles(feed, source_name)
    return articles


def fetch_source(source: dict, timeout: int = 20) -> list:
    """
    Fetch a source config dict (from sources.py).

    Routing:
      - If the dict has 'x_handle', fetch via Xquik (X/Twitter API).
      - Otherwise fetch the primary RSS URL, falling back to rss_alt.
    """
    name = source["name"]

    # X/Twitter source — route through Xquik
    x_handle = source.get("x_handle", "")
    if x_handle:
        from .xquik_fetcher import fetch_xquik_user
        return fetch_xquik_user(x_handle, name, timeout=timeout)

    primary  = source.get("rss", "")
    fallback = source.get("rss_alt", "")

    articles = []
    if primary:
        articles = fetch_rss(primary, name, timeout=timeout)

    if not articles and fallback:
        print(f"    ↳ trying fallback URL for {name}…", file=sys.stderr)
        articles = fetch_rss(fallback, name, timeout=timeout)

    return articles
