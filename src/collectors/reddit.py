import os
from datetime import datetime, timezone
from typing import List, Dict, Any


SUBS = ["ecommerce", "retail", "elasticsearch", "opensearch", "searchengine", "MachineLearning"]
# if a sub 404s, skip it silently instead of trying "hot" again


try:
    import praw  # pip install praw
except ImportError as e:
    raise RuntimeError("Missing dependency: praw (pip install praw)") from e

def _praw_client():
    cid = os.getenv("REDDIT_CLIENT_ID")
    secret = os.getenv("REDDIT_CLIENT_SECRET")
    ua = os.getenv("REDDIT_USER_AGENT", "search-intel-agent/1.0")
    if not (cid and secret and ua):
        raise RuntimeError("Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
    return praw.Reddit(
        client_id=cid,
        client_secret=secret,
        user_agent=ua,
    )

def fetch_reddit_posts(subreddits: List[str], query: str, limit: int = 10) -> List[Dict[str, Any]]:
    r = _praw_client()
    items: List[Dict[str, Any]] = []
    for sub in subreddits:
        sr = r.subreddit(sub)
        results = []
        try:
            # Try search first
            results = list(sr.search(query, sort="new", limit=limit))
            if not results:
                # Some subs return empty for search; fallback
                results = list(sr.hot(limit=limit))
        except Exception as e:
            # 404/403, etc. Fallback to hot
            print(f"[Reddit] search failed on r/{sub}: {e} -> falling back to hot")
            try:
                results = list(sr.hot(limit=limit))
            except Exception as e2:
                print(f"[Reddit] hot failed on r/{sub}: {e2}")
                results = []

        for post in results[:limit]:
            url = f"https://reddit.com{post.permalink}" if getattr(post, "permalink", None) else (getattr(post, "url", "") or "")
            title = getattr(post, "title", "") or ""
            summary = (getattr(post, "selftext", "") or "")[:400]
            created = datetime.fromtimestamp(getattr(post, "created_utc", 0), tz=timezone.utc).isoformat()
            items.append({
                "title": f"[Reddit] {title}",
                "summary": summary,
                "url": url,
                "source": "Reddit",
                "date": created,
                "tags": ["reddit", sub, "search"],
                "citations": [{"title": title, "url": url}],
            })
    return items


if __name__ == "__main__":
    # simple smoke test
    os.environ.setdefault("REDDIT_USER_AGENT", "search-intel-agent/1.0")
    test = fetch_reddit_posts(["elasticsearch", "ecommerce"], "search relevance", limit=3)
    for t in test:
        print("-", t["title"], "→", t["url"])
