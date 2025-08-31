import re, hashlib
def clean_text(t: str) -> str:
    import re; return re.sub(r'\s+', ' ', (t or '')).strip()
def is_relevant(text: str, include, exclude) -> bool:
    t = (text or '').lower()
    if include and not any(k.lower() in t for k in include): return False
    if exclude and any(k.lower() in t for k in exclude): return False
    return True
def compute_id(item):
    key = f"{item.get('source','')}|{item.get('title','')}|{item.get('url','')}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()
def basic_score(item):
    title = item.get('title','') or ''
    score = min(len(title), 140) / 140.0; score += 0.2
    return round(score, 3)
