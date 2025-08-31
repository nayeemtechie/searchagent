<<<<<<< HEAD
# searchagent
=======
# Search Intel Agent — Bi‑Weekly (Baseline + LLM) with REAL Tests

Generates Executive, Consulting, and LinkedIn Kit PDFs. Includes test scripts for Outlook/Gmail SMTP, Reddit, Twitter/X, and GitHub.

## Quick Start (macOS)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && open .env
python -m src.tests.test_email
python -m src.tests.test_reddit   # optional
python -m src.tests.test_twitter  # optional
python -m src.tests.test_github   # optional
python -m src.main --simulate
```
LLM mode: set `summarization.use_llm: true` in `config.yaml` + set `OPENAI_API_KEY` in `.env`.
>>>>>>> cbd4216 (Initial project upload)
