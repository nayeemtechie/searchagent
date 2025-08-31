from typing import List, Dict, Any

EXEC_PROMPT = """You are writing an Executive Insights brief.
- Keep it strategic, concise, non-technical.
- Focus on business impact, risks, opportunities, trends.
- Return 5–8 bullets max.

INPUT:
{content}
"""

CONS_PROMPT = """You are writing a Consulting Insights brief.
- Provide actionable recommendations and brief rationale.
- Use sections: Insights, Recommendations, Risks.
- Keep it practical for partial-technical readers.

INPUT:
{content}
"""

LI_PROMPT = """Convert to a LinkedIn-ready post:
- Start with a strong hook (1 line).
- 3–5 crisp bullets with insights.
- No competitor mentions.
- End with a question to drive comments.

INPUT:
{content}
"""

def _join_items(items: List[Dict[str, Any]]) -> str:
    lines = []
    for it in items:
        t = it.get("title", "")
        s = it.get("summary", "")
        u = ""
        for c in (it.get("citations") or []):
            if c.get("url"):
                u = c["url"]; break
        line = f"- {t}: {s}"
        if u:
            line += f" [{u}]"
        lines.append(line)
    return "\n".join(lines)

def summarize_items_llm(items: List[Dict[str, Any]], audience: str, llm=None) -> List[str]:
    """
    audience: 'executive' | 'consulting' | 'linkedin'
    llm: instance of src.llm.provider.LLMProvider (optional). If None, a local one is created.
    Returns: list[str] paragraphs/bullets suitable for pdf sections.
    """
    if llm is None:
        # lazy import to avoid circulars
        from src.llm.provider import LLMProvider
        llm = LLMProvider()

    content = _join_items(items)
    if audience == "executive":
        prompt = EXEC_PROMPT.format(content=content)
        temperature, max_tokens = 0.3, 1200
    elif audience == "consulting":
        prompt = CONS_PROMPT.format(content=content)
        temperature, max_tokens = 0.5, 1400
    else:
        prompt = LI_PROMPT.format(content=content)
        temperature, max_tokens = 0.7, 800

    text = llm.query_openai(prompt, temperature=temperature, max_tokens=max_tokens)
    # split into paragraphs for PDF
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts[:12]
