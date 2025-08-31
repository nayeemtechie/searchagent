from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone
from src.utils.dates import parse_dt

def rank_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simple recency-first ranking for items.
    Later, you can extend with relevance, source weighting, etc.
    """
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    def _key(it: Dict[str, Any]):
        return parse_dt(it.get("date")) or epoch

    return sorted(items, key=_key, reverse=True)


def dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate items by URL or title.
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        key = (it.get("url") or it.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
