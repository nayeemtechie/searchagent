import yaml
import os
from dotenv import load_dotenv
def load_config(cfg_path: str = 'config.yaml'):
    load_dotenv()
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)



# Perplexity API
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")

# OpenAI (cheap mini models)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Default models
EXEC_REPORT_MODEL = "perplexity/pplx-7b-online"  # retrieval + citations
CONSULT_REPORT_MODEL = "perplexity/pplx-7b-online"
LINKEDIN_MODEL = "gpt-4o-mini"  # cheaper for style/rewrites




