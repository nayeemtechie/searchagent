import re
from typing import List
def split_sentences(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', text or '').strip()
    sents = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sents if len(s) > 0]
def summarize_text(text: str, max_sentences: int = 3) -> str:
    sents = split_sentences(text)
    if len(sents) <= max_sentences: return ' '.join(sents)
    words = re.findall(r'\w+', text.lower())
    freqs = {}
    for w in words:
        if len(w) <= 3: continue
        freqs[w] = freqs.get(w, 0) + 1
    def score_sent(s):
        ws = re.findall(r'\w+', s.lower()); return sum(freqs.get(w,0) for w in ws)
    ranked = sorted(sents, key=score_sent, reverse=True)
    return ' '.join(ranked[:max_sentences])
