import os
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any

TW_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"  # alias domain; api.twitter.com works too

def _headers():
    bearer = os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer:
        raise RuntimeError("Set X_BEARER_TOKEN (Twitter v2 Bearer token)")
    return {"Authorization": f"Bearer {bearer}"}

def fetch_tweets(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Recent search across public tweets.
    Example query: '(ecommerce OR retail) (search OR relevance) lang:en -is:retweet'
    """
    params = {
        "query": query,
        "max_results": min(limit, 100),
        "tweet.fields": "created_at,author_id,lang,public_metrics",
    }
    r = requests.get("https://api.twitter.com/2/tweets/search/recent", headers=_headers(), params=params, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", []) or []
    items: List[Dict, Any] = []
    for t in data[:limit]:
        tid = t.get("id", "")
        url = f"https://twitter.com/i/web/status/{tid}" if tid else ""
        title = (t.get("text") or "").split("\n")[0][:100]
        summary = (t.get("text") or "")[:400]
        created = t.get("created_at") or datetime.now(timezone.utc).isoformat()
        item = {
            "title": f"[X] {title}",
            "summary": summary,
            "url": url,
            "source": "Twitter",
            "date": created,
            "tags": ["twitter", "x", "search"],
            "citations": [{"title": title, "url": url}],
        }
        items.append(item)
    return items

if __name__ == "__main__":
    q = "(ecommerce OR retail) (search OR relevance) lang:en -is:retweet"
    for it in fetch_tweets(q, limit=5):
        print("-", it["title"], "→", it["url"])
