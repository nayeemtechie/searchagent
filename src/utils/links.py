# src/utils/links.py
from __future__ import annotations
from typing import List, Dict, Any
from urllib.parse import urlparse
from datetime import datetime, timezone
from src.utils.dates import parse_dt, within_days, fmt_short_date

# Never amplify competitor domains in public-facing places
COMPETITOR_DENYLIST = {
    "algolia.com","bloomreach.com","constructor.io","elastic.co","lucidworks.com",
    "klevu.com","searchspring.com","attraqt.com","reflektion.com","factfinder.de",
}

# “Social/dev” sources; OK for Consulting, avoided in Exec/LinkedIn
SOCIAL_HOSTS = {"reddit.com","old.reddit.com","x.com","twitter.com","github.com","gist.github.com"}

def _host(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def extract_links_from_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Collect links from item.citations and item.url, carrying best-guess date.
    Each element: {"title": str, "url": str, "date": datetime|None, "source": str|None}
    """
    out: List[Dict[str, Any]] = []
    for it in items:
        item_dt = parse_dt(it.get("date"))
        # Perplexity / curated citations
        for c in (it.get("citations") or []):
            url = (c.get("url") or "").strip()
            if not url:
                continue
            title = (c.get("title") or it.get("title") or url).strip()
            c_dt = parse_dt(c.get("published") or c.get("date")) or item_dt
            out.append({"title": title, "url": url, "date": c_dt, "source": it.get("source")})
        # direct URL on the item (Reddit/Twitter/GitHub/blog)
        u = (it.get("url") or "").strip()
        if u:
            out.append({"title": (it.get("title") or u).strip(), "url": u, "date": item_dt, "source": it.get("source")})
    return out

def dedupe_links(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out=[]
    for ln in links:
        url = (ln.get("url") or "").strip()
        if not url:
            continue
        key = url.split("#")[0].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(ln)
    return out

def sort_links_by_date_desc(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    epoch = datetime(1970,1,1,tzinfo=timezone.utc)
    return sorted(links, key=lambda x: x.get("date") or epoch, reverse=True)

def filter_exec(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [l for l in links if (h:=_host(l["url"])) and h not in COMPETITOR_DENYLIST and h not in SOCIAL_HOSTS]

def filter_cons(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [l for l in links if (h:=_host(l["url"])) and h not in COMPETITOR_DENYLIST]

def filter_li(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [l for l in links if (h:=_host(l["url"])) and h not in COMPETITOR_DENYLIST and h not in SOCIAL_HOSTS]

def filter_by_recency(links: List[Dict[str, Any]], days: int, allow_undated: bool, min_needed: int) -> List[Dict[str, Any]]:
    fresh = [l for l in links if within_days(l.get("date"), days)]
    if len(fresh) >= min_needed:
        return fresh
    if allow_undated:
        undated = [l for l in links if l.get("date") is None]
        fresh += undated
    if len(fresh) < min_needed:
        older = [l for l in links if l.get("date") and not within_days(l.get("date"), days)]
        fresh += sort_links_by_date_desc(older)
    return dedupe_links(fresh)

def add_date_suffix(links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out=[]
    for l in links:
        ds = fmt_short_date(l.get("date"))
        t = l.get("title") or l.get("url")
        out.append({"title": f"{t} ({ds})" if ds else t, "url": l["url"]})
    return out

def pick_top(links: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    """Small helper to make main.py more readable."""
    return links[:n]
