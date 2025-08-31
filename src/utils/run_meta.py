import os
from datetime import datetime
from typing import Dict, Any

def collect_run_meta(cfg: Dict[str, Any], counts: Dict[str, int]) -> Dict[str, Any]:
    """Create a dict of QA/run metadata to print into PDFs and footers."""
    tz = os.getenv("TZ", "Asia/Kolkata")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # LLM flags
    use_llm = bool(cfg.get("summarization", {}).get("use_llm", False))
    use_pplx = bool(cfg.get("research", {}).get("use_perplexity", False))

    # Models (from env; provider.py also uses these)
    exec_model = os.getenv("EXEC_REPORT_MODEL", "sonar-pro")
    cons_model = os.getenv("CONSULT_REPORT_MODEL", "sonar-pro")
    li_model   = os.getenv("LINKEDIN_MODEL", "gpt-4o-mini")

    return {
        "timestamp": f"{now} ({tz})",
        "use_llm": use_llm,
        "use_perplexity": use_pplx,
        "models": {
            "executive": exec_model,
            "consulting": cons_model,
            "linkedin": li_model,
        },
        "counts": {
            "sources_checked": int(counts.get("sources_checked", 0)),
            "items_kept": int(counts.get("items_kept", 0)),
            "citations": int(counts.get("citations", 0)),
        },
    }
