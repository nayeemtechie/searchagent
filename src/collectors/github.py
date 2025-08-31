import os
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

GH_SEARCH_URL = "https://api.github.com/search/issues"

def _headers():
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_ACCESS_TOKEN")
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def fetch_github_issues_repos(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search issues/PRs across GitHub. Example query: 'ecommerce search relevance language:Python created:>2025-08-01'
    """
    params = {"q": query, "per_page": min(limit, 30)}
    r = requests.get(GH_SEARCH_URL, headers=_headers(), params=params, timeout=30)
    r.raise_for_status()
    data = r.json().get("items", []) or []
    items: List[Dict[str, Any]] = []
    for x in data[:limit]:
        title = x.get("title") or ""
        url = x.get("html_url") or ""
        created = x.get("created_at") or datetime.now(timezone.utc).isoformat()
        summary = (x.get("body") or "")[:400]
        item = {
            "title": f"[GitHub] {title}",
            "summary": summary,
            "url": url,
            "source": "GitHub",
            "date": created,
            "tags": ["github", "search"],
            "citations": [{"title": title, "url": url}],
        }
        items.append(item)
    return items

if __name__ == "__main__":
    q = "ecommerce search relevance language:Python sort:created-desc"
    for it in fetch_github_issues_repos(q, limit=5):
        print("-", it["title"], "→", it["url"])
