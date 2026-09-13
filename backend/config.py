"""
Backend configuration — loads from .env via python-dotenv.
All settings are in one place; import from here everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (two levels up from backend/)
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", override=True)


# ── LLM ──────────────────────────────────────────────────────
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")


def get_llm_config() -> tuple[str, str, str]:
    """Dynamically re-read .env so edits take effect immediately without server restart."""
    load_dotenv(_ROOT / ".env", override=True)
    base_url = os.getenv("LLM_BASE_URL", LLM_BASE_URL)
    model_name = os.getenv("LLM_MODEL_NAME", LLM_MODEL_NAME)
    api_key = os.getenv("LLM_API_KEY", LLM_API_KEY)
    return base_url, model_name, api_key

# ── Storage ───────────────────────────────────────────────────
DATA_DIR: Path = _ROOT / os.getenv("DATA_DIR", "data")
CHROMA_PERSIST_DIR: Path = _ROOT / os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
TOKEN_LOG_FILE: Path = DATA_DIR / "token_log.jsonl"

# ── Crawler ───────────────────────────────────────────────────
MAX_CRAWL_PAGES: int = int(os.getenv("MAX_CRAWL_PAGES", "100"))
CRAWL_DELAY: float = float(os.getenv("CRAWL_DELAY_SECONDS", "0.5"))
CRAWL_TIMEOUT: int = int(os.getenv("CRAWL_TIMEOUT_SECONDS", "15"))

# ── Chunking ──────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

# ── RAG ───────────────────────────────────────────────────────
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "6"))
RAG_MIN_RELEVANCE_SCORE: float = float(os.getenv("RAG_MIN_RELEVANCE_SCORE", "0.30"))

# ── Cost Estimation ───────────────────────────────────────────
COST_PER_1K_INPUT: float = float(os.getenv("COST_PER_1K_INPUT_TOKENS", "0.00015"))
COST_PER_1K_OUTPUT: float = float(os.getenv("COST_PER_1K_OUTPUT_TOKENS", "0.00060"))

# ── Ensure directories exist ──────────────────────────────────
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
