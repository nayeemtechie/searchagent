import os
import argparse
import datetime
import json
from src.prompts import load_prompt, PromptNotFound
from datetime import datetime, timezone, timedelta

from src.utils.config import load_config
from src.utils.logging import get_logger
from src.utils.ranking import rank_items, dedupe_items

from src.ingest.rss import fetch_rss
from src.ingest.scrape import scrape_flipkart, scrape_target, scrape_generic
from src.utils.run_meta import collect_run_meta

from src.process.filter_rank import (
    is_relevant,
    compute_id,
    basic_score,
    clean_text,
)

from src.utils.links import (
    extract_links_from_items, dedupe_links, sort_links_by_date_desc,
    filter_exec, filter_cons, filter_li, filter_by_recency,
    add_date_suffix, pick_top
)

from src.utils.dates import fmt_short_date

def _cfg_links(cfg, key, default):
    return cfg.get("links", {}).get(key, default)

from src.process.summarize import summarize_text  # kept for future use

from src.ingest.perplexity_agent import research_topics


from src.output.pdf import make_pdf
from src.output.linkedin import generate_linkedin_posts
from src.emailer.smtp import send_email

from src.collectors.reddit import fetch_reddit_posts
from src.collectors.twitter import fetch_tweets
from src.collectors.github import fetch_github_issues_repos

# Safe domain filters for LinkedIn links
COMPETITOR_DENYLIST = {
    "algolia.com", "bloomreach.com", "constructor.io", "elastic.co", "lucidworks.com",
    "klevu.com", "searchspring.com", "attraqt.com", "reflektion.com", "factfinder.de",
}

from urllib.parse import urlparse

def enforce_length(paras, min_words=180, max_words=280):
    text = " ".join(paras)
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return text


def _normalize_paras(paras):
    """
    Ensure paras is a list[str]. Accepts str | list[str] | None.
    Trims blanks and drops empties.
    """
    if paras is None:
        return []
    if isinstance(paras, list):
        return [str(p).strip() for p in paras if str(p).strip()]
    # string or other scalar
    s = str(paras).strip()
    return [s] if s else []

def _normalize_links(links):
    """
    Ensure links is a list[{'title': str, 'url': str}].
    If it’s None or malformed, return [] instead of crashing PDF.
    """
    if not links:
        return []
    out = []
    for ln in links:
        try:
            title = (ln.get("title") or ln.get("url") or "").strip()
            url = (ln.get("url") or "").strip()
            if title and url:
                out.append({"title": title, "url": url})
        except Exception:
            continue
    return out


def is_allowed_for_linkedin(url: str) -> bool:
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return False
    if not netloc:
        return False
    # strip leading www.
    host = netloc[4:] if netloc.startswith("www.") else netloc
    return host not in COMPETITOR_DENYLIST

def build_comment_kit_links(items, limit=6):
        """Pick non-competitor citations to show under LinkedIn as 'Comment Kit'."""
        seen = set()
        out = []
        for it in items:
            for c in (it.get("citations") or []):
                url = (c.get("url") or "").strip()
                title = (c.get("title") or "").strip() or url
                if not url or not is_allowed_for_linkedin(url):
                    continue
                key = (title.lower(), url.lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append({"title": title, "url": url})
                if len(out) >= limit:
                    return out
        return out

def _compact_items_for_llm(items):
            """
            Slim down items for prompts: title, brief summary, date, source, citations.
            """
            out = []
            for it in items:
                out.append({
                    "title": it.get("title"),
                    "summary": (it.get("summary") or "")[:400],
                    "date": it.get("date"),
                    "source": it.get("source"),
                    "citations": it.get("citations", []),
                })
            return out

def _ultralight_items_for_linkedin(items):
        out = []
        for it in items[:12]:  # cap to keep prompt small
            out.append({
                "title": it.get("title"),
                "summary": (it.get("summary") or "")[:200],
                "citations": [c for c in (it.get("citations") or [])[:1]],  # at most 1
            })
        return out
def in_biweekly_window(cfg) -> bool:
    """Return True only on the intended bi-weekly Monday."""
    anchor = datetime.date.fromisoformat(
        cfg["schedule"].get("biweekly_anchor_date", "2025-08-11")
    )
    today = datetime.date.today()
    is_monday = today.weekday() == 0
    delta_days = (today - anchor).days
    return is_monday and (delta_days % 14 == 0)


def collect_items(cfg, logger):
    """Fetch from vendor + retail tech sources defined in config.yaml."""
    items = []

    # Reddit
    rcfg = cfg.get("sources", {}).get("reddit", {})
    if rcfg.get("enabled"):
        try:
            items += fetch_reddit_posts(
                rcfg.get("subreddits", []),
                rcfg.get("query", "search relevance"),
                rcfg.get("limit", 5),
            )
        except Exception as e:
            logger.error(f"Reddit fetch failed: {e}")

    # Twitter (X)
    """     tcfg = cfg.get("sources", {}).get("twitter", {})
    if tcfg.get("enabled"):
        try:
            items += fetch_tweets(
                tcfg.get("query", "(ecommerce OR retail) search lang:en -is:retweet"),
                tcfg.get("limit", 5),
            )
        except Exception as e:
            logger.error(f"Twitter fetch failed: {e}") """

    # GitHub
    gcfg = cfg.get("sources", {}).get("github", {})
    if gcfg.get("enabled"):
        try:
            items += fetch_github_issues_repos(
                gcfg.get("query", "ecommerce search relevance sort:created-desc"),
                gcfg.get("limit", 5),
            )
        except Exception as e:
            logger.error(f"GitHub fetch failed: {e}")

    # Vendor blogs (RSS)
    for src in cfg.get("sources", {}).get("vendor_blogs", []):
        if src["type"] == "rss":
            try:
                items.extend(fetch_rss(src["url"], src["name"]))
            except Exception as e:
                logger.warning(f"RSS failed for {src['name']}: {e}")

    # Retail tech blogs (RSS or scrape)
    for src in cfg.get("sources", {}).get("retail_tech_blogs", []):
        try:
            if src["type"] == "rss":
                items.extend(fetch_rss(src["url"], src["name"]))
            elif src["type"] == "scrape":
                url = src["url"]
                if "flipkart" in url:
                    items.extend(scrape_flipkart(url))
                elif "tech.target.com" in url:
                    items.extend(scrape_target(url))
                else:
                    items.extend(scrape_generic(url))
        except Exception as e:
            label = src.get("name", src.get("url"))
            logger.warning(f"Scrape failed for {label}: {e}")


    rcfg = cfg.get("research", {})
    if rcfg.get("use_perplexity"):
        findings = research_topics(
            topics=rcfg.get("topics", []),
            model=rcfg.get("model", "sonar-pro"),
            recency=rcfg.get("search_recency_filter", "week"),
            search_mode=rcfg.get("search_mode"),
            include_domains=rcfg.get("include_domains"),
            exclude_domains=rcfg.get("exclude_domains"),
            user_location=rcfg.get("user_location"),
        )
        for f in findings:
            items.append({
                "title": f["headline"] or f["topic"],
                "summary": f["summary"],
                "content": f["text"],
                "source": "Perplexity",
                "citations": f["citations"],  # <-- must be present
                "tags": f["tags"],
            })

    return items


def filter_rank(items, cfg):
    """Keyword filter + basic dedupe/ranking."""
    include = cfg.get("filters", {}).get("include_keywords", [])
    exclude = cfg.get("filters", {}).get("exclude_keywords", [])

    uniq = {}
    results = []
    for it in items:
        title = clean_text(it.get("title", ""))
        text = " ".join(
            [title, clean_text(it.get("summary", "")), clean_text(it.get("content", ""))]
        )
        if not title or not is_relevant(text, include, exclude):
            continue

        it["id"] = compute_id(it)
        if it["id"] in uniq:
            continue
        uniq[it["id"]] = True

        it["score"] = basic_score(it)
        results.append(it)

    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[:30]
# --- Executive section shaping (keeps CEOs happy) ----------------------------
def _enforce_exec_shape(paras):
    """
    Ensures: trimmed bullets, cap length, and a mandatory 'Leadership takeaway:' line.
    Assumes paras is a list[str] produced by the LLM.
    """
    cleaned = [p.strip() for p in (paras or []) if isinstance(p, str) and p.strip()]

    # Cap content: keep the first 5 bullets max; we'll append takeaway after
    # (so the whole section stays tight & scannable)
    MAX_CORE_BULLETS = 5
    core = cleaned[:MAX_CORE_BULLETS]

    # Ensure the 'Leadership takeaway:' is present and last
    has_takeaway = any(p.lower().startswith("leadership takeaway:") for p in cleaned)
    if not has_takeaway and core:
        # Build a simple, non-technical, CEO-style takeaway from the first bullet's first sentence
        base = core[0].split("•")[-1].split("–")[-1].split("-")[-1].strip()
        base = base.split(".")[0].strip() if "." in base else base
        takeaway = f"Leadership takeaway: {base} — here’s the strategic impact."
        cleaned = core + [takeaway]
    else:
        # Keep the first MAX_CORE_BULLETS bullets and the last occurrence of the takeaway
        takeaway_line = next((p for p in reversed(cleaned) if p.lower().startswith("leadership takeaway:")), None)
        cleaned = core + ([takeaway_line] if takeaway_line else [])

    return cleaned
# ---------------------------------------------------------------------------


def _enforce_consulting_shape(paras):
    """
    Shapes Consulting section into 3 blocks:
    Market Radar, Competitive Watch, and Client-Winning Use Cases + Checklist.
    """
    if not paras:
        return ["(LLM disabled) No consulting content generated."]

    # Ensure block headers
    blocks = []
    joined = "\n".join(paras)

    if "Market Radar" not in joined:
        blocks.append("### Market Radar\n- (no updates parsed)")
    if "Competitive Watch" not in joined:
        blocks.append("### Competitive Watch\n- (no updates parsed)")
    if "Action Checklist" not in joined:
        blocks.append("### Client-Winning Use Cases + Checklist\n- (no updates parsed)\n\nAction Checklist:\n- Add top queries to pilot\n- Track SearchCVR\n- Watch competitor moves")

    # Merge user paras + missing blocks
    cleaned = [p.strip() for p in paras if isinstance(p, str) and p.strip()]
    return cleaned + blocks


def _now_ist_str() -> str:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M:%S (Asia/Kolkata)")

today_ist = _now_ist_str()

# Small helper: call LLM (explicit llm param), split lines, swallow failures
def _safe_llm_lines(llm_obj, system_prompt: str, user_prompt: str, model_id: str, label: str) -> list[str]:
    try:
        text = llm_obj.chat(system=system_prompt, user=user_prompt, model=model_id)
    except Exception as e:
        # Optional: swap 'print' for your logger if present
        print(f"[ERROR] LLM ({label}) failed: {e}")
        return []
    # Normalize to bullet lines; tolerate single-paragraph outputs
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    return lines[:200]  # hard cap to avoid pathological outputs

#def make_sections_for_pdfs(items, cfg, exec_llm=None, cons_llm=None, li_llm=None):
#def make_sections_for_pdfs(llm, items, cfg, models_exec, models_cons, models_li):
def make_sections_for_pdfs(llm, items, cfg, models):
    #exec_llm = exec_llm or []
    #cons_llm = cons_llm or []
    #li_llm   = li_llm   or []

    exec_llm: list[str] = []
    cons_llm: list[str] = []
    li_llm:   list[str] = []

    # ---- LLM prompt preparation ----

    # Step: rank + dedupe items
    items_ranked = rank_items(items)
    items_ranked_or_deduped = dedupe_items(items_ranked)

    #items_compact = _compact_items_for_llm(items_ranked_or_deduped)  # use your list
    #items_ul = _ultralight_items_for_linkedin(items_ranked_or_deduped)

    # Items already ranked/deduped BEFORE calling this function OR passed as-is.
    items_compact = _compact_items_for_llm(items)
    items_ul = _ultralight_items_for_linkedin(items)

    # Always compute IST timestamp
    from datetime import datetime, timezone, timedelta
    today_ist = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime(
    "%Y-%m-%d %H:%M:%S (Asia/Kolkata)"
    )
    #today_ist = qa_meta.get("timestamp") if "qa_meta" in locals() else ""
    product_focus = cfg.get("product_focus", "ecommerce search relevance")
    topics_csv = ", ".join(cfg.get("topics", []))
    denylist_domains_csv = ",".join(cfg.get("links", {}).get("denylist", []))
    recency_days_exec = cfg.get("links", {}).get("recency_days", {}).get("executive", 21)
    recency_days_cons = cfg.get("links", {}).get("recency_days", {}).get("consulting", 28)
    recency_days_li   = cfg.get("links", {}).get("recency_days", {}).get("linkedin", 21)

    # system prompt (single source of truth)
    try:
        system_prompt = load_prompt("system_master.txt")
    except PromptNotFound:
        system_prompt = (
            "You are Search Intel Agent, generating Executive, Consulting and LinkedIn content. "
            "Be concise, recent-first, KPI-oriented. Avoid competitor links in public content."
        )

    # EXECUTIVE
    try:
        user_exec = load_prompt("user_executive.txt")
    except PromptNotFound:
        user_exec = (
            "TASK=EXECUTIVE_INSIGHTS\n\n"
            "Inputs:\n- today_ist: {today_ist}\n- product_focus: {product_focus}\n"
            "- topics: {topics_csv}\n- recency_days: {recency_days_exec}\n"
            "- denylist_domains: {denylist_domains_csv}\n\nData:\n{items_json}\n\n"
            "Instructions: Produce 1–2 sections with KPI, competitor signal, risk/opportunity, "
            "and end each section with 'Leadership takeaway: ...'."
        )

    exec_prompt = user_exec.format(
        today_ist=today_ist,
        product_focus=product_focus,
        topics_csv=topics_csv,
        recency_days_exec=recency_days_exec,
        denylist_domains_csv=denylist_domains_csv,
        items_json_compact=json.dumps(items_compact, ensure_ascii=False),
    )
   
    
    
    exec_llm = _safe_llm_lines(llm, system_prompt, exec_prompt, models["executive"], "executive")


    # CONSULTING
    try:
        user_cons = load_prompt("user_consulting.txt")
    except PromptNotFound:
        user_cons = (
            "TASK=CONSULTING_NEWS\n\n"
            "Inputs:\n- today_ist: {today_ist}\n- product_focus: {product_focus}\n"
            "- topics: {topics_csv}\n- recency_days: {recency_days_cons}\n"
            "- denylist_domains: {denylist_domains_csv}\n\nData:\n{items_json}\n\n"
            "Instructions: Produce 3 blocks — Market Radar, Competitive Watch, "
            "Client-Winning Use Cases + Action Checklist. KPIs where possible."
        )

    cons_prompt = user_cons.format(
        today_ist=today_ist,
        product_focus=product_focus,
        topics_csv=topics_csv,
        recency_days_cons=recency_days_cons,
        denylist_domains_csv=denylist_domains_csv,
        items_json_compact=json.dumps(items_compact, ensure_ascii=False),
    )
    
    cons_llm = _safe_llm_lines(llm, system_prompt, cons_prompt, models["consulting"], "consulting")
    
    # LINKEDIN
    try:
        user_li = load_prompt("user_linkedin.txt")
    except PromptNotFound:
        user_li = (
            "TASK=LINKEDIN_DRAFT\n\n"
            "Inputs:\n- today_ist: {today_ist}\n- product_focus: {product_focus}\n"
            "- topics: {topics_csv}\n- recency_days: {recency_days_li}\n"
            "- denylist_domains: {denylist_domains_csv}\n\nData:\n{items_json}\n\n"
            "Instructions: Write a hook, 3–5 insights (no competitor mentions), "
            "one question, and a sign-off '— Curated by {author_name}, {author_title}'."
        )

    author_name  = cfg.get("branding", {}).get("author_name", "Your Name")
    author_title = cfg.get("branding", {}).get("author_title", "Principal Architect")

    li_prompt = user_li.format(
        today_ist=today_ist,
        product_focus=product_focus,
        topics_csv=topics_csv,
        recency_days_li=recency_days_li,
        denylist_domains_csv=denylist_domains_csv,
        items_json_ultralight=json.dumps(items_ul, ensure_ascii=False),
        author_name=author_name,
        author_title=author_title,
    )
   
    li_llm = _safe_llm_lines(llm, system_prompt, li_prompt, models["linkedin"], "linkedin")

    li_llm = enforce_length(li_llm)


    # 1) Build pool
    all_links = dedupe_links(extract_links_from_items(items))
    all_links = sort_links_by_date_desc(all_links)

    # 2) Recency config
    recency_days_exec = _cfg_links(cfg, "recency_days", {}).get("executive", 21)
    recency_days_cons = _cfg_links(cfg, "recency_days", {}).get("consulting", 28)
    recency_days_li   = _cfg_links(cfg, "recency_days", {}).get("linkedin", 21)

    min_exec = _cfg_links(cfg, "min_per_section", {}).get("executive", 6)
    min_cons = _cfg_links(cfg, "min_per_section", {}).get("consulting", 8)
    min_li   = _cfg_links(cfg, "min_per_section", {}).get("linkedin", 5)

    allow_undated = bool(_cfg_links(cfg, "allow_undated_backfill", True))

    # 3) Audience filters + recency
    exec_links = filter_by_recency(filter_exec(all_links), recency_days_exec, allow_undated, min_exec)
    cons_links = filter_by_recency(filter_cons(all_links), recency_days_cons, allow_undated, min_cons)
    li_links   = filter_by_recency(filter_li(all_links), recency_days_li, allow_undated, min_li)

    exec_links = pick_top(exec_links, 8)
    cons_links = pick_top(cons_links, 10)
    li_links   = pick_top(li_links, 6)

    # 4) Format titles with date suffix (e.g., "Title (25 Aug 2025)")
    def _add_date_suffix(lns):
        out = []
        for ln in lns:
            ds = fmt_short_date(ln.get("date"))
            title = ln.get("title") or ln.get("url")
            if ds:
                title = f"{title} ({ds})"
            out.append({"title": title, "url": ln["url"]})
        return out
    exec_links = _add_date_suffix(exec_links)
    cons_links = _add_date_suffix(cons_links)
    li_links   = _add_date_suffix(li_links)

    # 5) Sections

    # Executive (CEO-friendly)
    exec_paras = exec_llm if exec_llm else ["(LLM disabled) No executive content generated."]
    exec_paras = _enforce_exec_shape(exec_paras)

   

    exec_sections = [{
        "title": "Executive Insights",
        "paras": _normalize_paras(exec_paras if exec_paras else "(LLM disabled) No executive content generated."),
        "links": _normalize_links(exec_links),
    }]
   
    cons_paras = cons_llm if cons_llm else ["(LLM disabled) No consulting content generated."]
    cons_paras = _enforce_consulting_shape(cons_paras)


    consulting_sections = [{
     "title": "Consulting Team — What Changed & How to Use It",
    "paras": _normalize_paras(cons_paras if cons_paras else "(LLM disabled) No consulting content generated."),
    "links": _normalize_links(cons_links),
    }]

    linkedin_sections = [{
    "title": "LinkedIn Draft Kit",
    "paras": _normalize_paras(li_llm if li_llm else "(LLM disabled) No LinkedIn draft generated."),
    "links": _normalize_links(li_links),
    }]

    BANNER = "[Curated] by Nayeem"  # ASCII to avoid emoji glyph issues
    for sec in linkedin_sections:
        sec["paras"] = [BANNER] + _normalize_paras(sec["paras"])
        #sec["paras"].append("— Curated by Nayeemuddin Mohammed, Principal Architect (E-commerce Search & Recommendations)")

    return exec_sections, consulting_sections, linkedin_sections


def ensure_out_dir(cfg) -> str:
    out_dir = cfg.get("output", {}).get("dir", "output")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--cron", action="store_true")
    args = parser.parse_args()

    cfg = load_config("config.yaml")
    logger = get_logger()

    # Schedule guard (your existing logic)
    if args.schedule or args.cron:
        if not in_biweekly_window(cfg):
            print("Not the bi-weekly slot — exiting.")
            return

    # Collect + filter
    items = collect_items(cfg, logger)
    ranked = filter_rank(items, cfg)

    # ---- QA meta (unchanged) ----
    counts = {
        "sources_checked": len(items),
        "items_kept": len(ranked),
        "citations": sum(len(it.get("citations") or []) for it in items),
    }
    qa_meta = collect_run_meta(cfg, counts)
    print("[QA] Meta:", qa_meta)

    # ---- LLM prep: instantiate provider and compute LLM outputs (BEFORE sections) ----
    from src.llm.provider import LLMProvider
    llm = LLMProvider()

    # Resolve model ids (cfg → env → defaults)
    cfg_models = (cfg or {}).get("models", {})
    models = {
        "executive": cfg_models.get("executive") or os.getenv("EXEC_MODEL") or "sonar-pro",
        "consulting": cfg_models.get("consulting") or os.getenv("CONS_MODEL") or "sonar-pro",
        "linkedin":  cfg_models.get("linkedin")  or os.getenv("LI_MODEL")   or "gpt-4o-mini",
    }

    exec_llm, cons_llm, li_llm = [], [], []
    if cfg.get("summarization", {}).get("use_llm", False):
        from src.llm.provider import LLMProvider
        llm = LLMProvider()
        try:
            from src.process.llm_summarize import summarize_items_llm
            exec_llm = summarize_items_llm(ranked, "executive", llm=llm)
         #   cons_llm = summarize_items_llm(ranked, "consulting", llm=llm)

            cons_prompt = load_prompt("user_consulting.txt").format(
            today_ist=today_ist,
            product_focus=cfg["product_focus"],
            topics_csv=",".join(cfg["topics"]),
            recency_days_cons=cfg["links"]["recency_days"]["consulting"],
            denylist_domains_csv=",".join(cfg["links"]["denylist"]),
            items_json_compact=json.dumps(items_compact, ensure_ascii=False)
            )

            cons_llm = llm.chat(
                system=system_prompt,
                user=cons_prompt,
                model="sonar-pro"
            )

            li_llm   = summarize_items_llm(ranked, "linkedin",  llm=llm)
            print("[LLM] executive/consulting/linkedin texts generated")
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")

    # ---- Build sections (NOW pass the LLM lists) ----
    #""" exec_sections, consulting_sections, linkedin_sections = make_sections_for_pdfs(
    #   ranked, cfg, exec_llm=exec_llm, cons_llm=cons_llm, li_llm=li_llm
    #) """

    #exec_sections, consulting_sections, linkedin_sections = make_sections_for_pdfs(
    #    llm, items, cfg, models_exec, models_cons, models_li
    #)
   
    exec_sections, consulting_sections, linkedin_sections = make_sections_for_pdfs(
         llm, items, cfg, models
    )
    # OPTIONAL: inline QA markers for visual confirmation
   
    if exec_llm:
        exec_sections[0]["paras"].insert(0, "LLM OK (executive)")
    if cons_llm:
        consulting_sections[0]["paras"].insert(0, "LLM OK (consulting)")
    if li_llm:
        linkedin_sections[0]["paras"].insert(0, "LLM OK (linkedin)")


    # ---- Output paths (unchanged) ----
    out_dir = ensure_out_dir(cfg)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    exec_pdf = os.path.join(out_dir, f"Executive_Insights_{ts}.pdf")
    cons_pdf = os.path.join(out_dir, f"Consulting_News_{ts}.pdf")
    li_pdf   = os.path.join(out_dir, f"LinkedIn_Kit_{ts}.pdf")

    brand = cfg.get("output", {}).get("pdf_brand", {})
    title = brand.get("title", "Search Intel - Bi-Weekly")  # ASCII hyphen
    accent = tuple(brand.get("accent_rgb", [10, 102, 194]))

    # ---- Generate PDFs (pass qa=qa_meta) ----
    accent = (52, 152, 219)  # nice blue; RGB tuple

    make_pdf(exec_pdf, f"{title} - Executive Insights",   accent, exec_sections, qa=qa_meta)
    make_pdf(cons_pdf,  f"{title} - Consulting News",     accent, consulting_sections, qa=qa_meta)
    make_pdf(li_pdf,    f"{title} - LinkedIn Draft Kit",  accent, linkedin_sections, qa=qa_meta)

    print("Generated PDFs:", exec_pdf, cons_pdf, li_pdf)

    # Optional email (unchanged)
    if cfg.get("output", {}).get("email", {}).get("enabled"):
        subject = cfg["output"]["email"].get("subject", "Search Intel - Bi-Weekly Brief")
        body = "Attached: Executive Insights, Consulting News, and LinkedIn Draft Kit."
        to_addr = os.getenv("EMAIL_TO", os.getenv("SMTP_USERNAME"))
        if not to_addr:
            raise RuntimeError("EMAIL_TO or SMTP_USERNAME not set in .env")
        send_email(subject, body, to_addr, attachments=[exec_pdf, cons_pdf, li_pdf])
        print("Email sent to", to_addr)


def top_citations(items, source="Perplexity", limit=8):
    """Pick distinct, recent citations from items (prefer Perplexity-sourced)."""
    seen = set()
    out = []
    for it in items:
        if source and it.get("source") != source:
            continue
        for c in it.get("citations") or []:
            url = (c.get("url") or "").strip()
            title = (c.get("title") or "").strip() or url
            key = (title.lower(), url.lower())
            if not url or key in seen:
                continue
            seen.add(key)
            out.append({"title": title, "url": url, "date": c.get("date", "")})
            if len(out) >= limit:
                return out
    return out

def merge_links(existing_links, extra_links, max_total=10):
    """Combine and dedupe link dicts: {'title','url'}."""
    if not existing_links:
        existing_links = []
    seen = {(l["title"], l["url"]) for l in existing_links if l.get("url")}
    for l in extra_links:
        t, u = l.get("title"), l.get("url")
        if not u or (t, u) in seen:
            continue
        existing_links.append({"title": t, "url": u})
        seen.add((t, u))
        if len(existing_links) >= max_total:
            break
    return existing_links


if __name__ == "__main__":
    main()
