# src/ingest/perplexity_agent.py

import os, time, json, requests, re
from typing import List, Dict, Any

PPLX_URL = "https://api.perplexity.ai/chat/completions"

def _headers():
    key = os.getenv("PPLX_API_KEY") or os.getenv("PERPLEXITY_API_KEY")
    if not key:
        raise RuntimeError("PPLX_API_KEY / PERPLEXITY_API_KEY not set")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

def _mk_payload(model: str, user_prompt: str, recency: str = None,
                search_mode: str = None, include_domains: List[str] = None,
                exclude_domains: List[str] = None, user_location: str = None) -> Dict[str, Any]:
    sys_msg = (
        "You are a research agent for an e-commerce search SaaS product architect. "
        "Return concise, factual findings with citations. Prefer primary sources."
    )
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_msg},
            {
                "role": "user",
                "content": (
                    f"Research topic:\n{user_prompt}\n\n"
                    "Return:\n"
                    "1) 5–8 crisp bullets (business-friendly)\n"
                    "2) A final JSON object named RESEARCH with fields: "
                    "{'headline': str, 'summary': str, 'takeaways': [str], 'tags': [str]}\n"
                    "Always ground claims with sources."
                ),
            },
        ],
    }
    if search_mode:
        payload["search_mode"] = search_mode
    if recency:
        payload["search_recency_filter"] = recency
    domain_filter = []
    if include_domains:
        domain_filter += include_domains
    if exclude_domains:
        domain_filter += [f"-{d}" for d in exclude_domains]
    if domain_filter:
        payload["search_domain_filter"] = domain_filter
    if user_location:
        payload["web_search_options"] = {"user_location": user_location}
    return payload

def ask_perplexity(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(PPLX_URL, headers=_headers(), data=json.dumps(payload), timeout=180)
    r.raise_for_status()
    return r.json()

def extract_citations(resp: Dict[str, Any]):
    cites = []
    for sr in resp.get("search_results", []) or []:
        cites.append({"title": sr.get("title") or "", "url": sr.get("url") or "", "date": sr.get("date") or ""})
    return cites

def extract_text(resp: Dict[str, Any]) -> str:
    choices = resp.get("choices") or []
    if not choices:
        return ""
    return choices[0]["message"]["content"]

def parse_json_block(text: str):
    m = re.search(r"RESEARCH\s*(\{[\s\S]*\})", text)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {}

def research_topics(topics: List[str], model: str = "sonar-pro", recency: str = "week",
                    search_mode: str = None, include_domains: List[str] = None,
                    exclude_domains: List[str] = None, user_location: str = None):
    out = []
    for t in topics:
        payload = _mk_payload(model, t, recency, search_mode, include_domains, exclude_domains, user_location)
        resp = ask_perplexity(payload)
        text = extract_text(resp)
        cites = extract_citations(resp)
        obj = parse_json_block(text)
        out.append({
            "topic": t,
            "text": text,
            "summary": obj.get("summary") or "",
            "headline": obj.get("headline") or "",
            "takeaways": obj.get("takeaways") or [],
            "tags": obj.get("tags") or [],
            "citations": cites,
            "raw": resp,
        })
        time.sleep(0.5)
    return out
