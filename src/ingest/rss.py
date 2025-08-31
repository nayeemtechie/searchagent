import feedparser
def fetch_rss(url: str, source_name: str):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:20]:
        items.append({
            'source': source_name,
            'title': getattr(e, 'title', ''),
            'url': getattr(e, 'link', ''),
            'published': getattr(e, 'published', '') or getattr(e, 'updated', ''),
            'summary': getattr(e, 'summary', ''),
            'content': getattr(e, 'summary', ''),
        })
    return items
