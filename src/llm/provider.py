# src/llm/provider.py
import os
import requests
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY") or os.getenv("PPLX_API_KEY", "")

LINKEDIN_MODEL = os.getenv("LINKEDIN_MODEL", "gpt-4o-mini")
EXEC_REPORT_MODEL = os.getenv("EXEC_REPORT_MODEL", "sonar-pro")
CONSULT_REPORT_MODEL = os.getenv("CONSULT_REPORT_MODEL", "sonar-pro")

PPLX_URL = "https://api.perplexity.ai/chat/completions"

class LLMProvider:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")
        # New SDK: let it read OPENAI_API_KEY from env internally
        self.openai_client = OpenAI()

    def _pplx_headers(self):
        if not PERPLEXITY_API_KEY:
            raise RuntimeError("PERPLEXITY_API_KEY / PPLX_API_KEY not set")
        return {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def query_perplexity(self, prompt: str, model: str = EXEC_REPORT_MODEL) -> dict:
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        r = requests.post(PPLX_URL, headers=self._pplx_headers(), json=payload, timeout=180)
        r.raise_for_status()
        return r.json()

    def get_exec_report(self, prompt: str) -> dict:
        return self.query_perplexity(prompt, model=EXEC_REPORT_MODEL)

    def get_consult_report(self, prompt: str) -> dict:
        return self.query_perplexity(prompt, model=CONSULT_REPORT_MODEL)

    def query_openai(self, prompt: str, model: str = LINKEDIN_MODEL,
                     temperature: float = 0.5, max_tokens: int = 1200) -> str:
        resp = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content

    def rewrite_for_linkedin(self, draft: str) -> str:
        return self.query_openai(
            "Polish this into a LinkedIn-ready professional post. "
            "Start with a hook, add 3–5 crisp bullets, avoid competitor mentions, "
            "and end with a question for engagement.\n\n" + draft,
            model=LINKEDIN_MODEL, temperature=0.7, max_tokens=800
        )


    def chat(self, *, system: str, user: str, model: str) -> str:
        """
        Simple chat wrapper so main.py can pass loaded prompt files.
        Uses OpenAI if model contains 'gpt', else Perplexity.
        """
        if "gpt" in model:
            resp = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.2,
            )
            return (resp.choices[0].message.content or "").strip()

        # Perplexity
        import requests
        headers = {"Authorization": f"Bearer {PERPLEXITY_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        r = requests.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except Exception:
         return str(data)
