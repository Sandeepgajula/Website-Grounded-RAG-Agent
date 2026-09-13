"""
Text chunking service using LangChain's RecursiveCharacterTextSplitter.

Each chunk carries rich metadata for citation and filtering:
  - source_url: page URL (used for citations in RAG answers)
  - title:      page title
  - chunk_index: position within the page
  - char_count:  length of the chunk
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_SIZE, CHUNK_OVERLAP


# ─────────────────────────────────────────────
# Splitter (instantiated once, reused)
# ─────────────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    # Priority order: paragraph → line → sentence → word
    separators=["\n\n", "\n", ". ", ", ", " ", ""],
    is_separator_regex=False,
    strip_whitespace=True,
)


def _derive_section(url: str) -> str:
    """
    Derive a human-readable section label from the URL path.
    e.g. https://example.com/products/prime-mdm → 'Products'
    """
    try:
        path = urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]
        if parts:
            return parts[0].replace("-", " ").replace("_", " ").title()
    except Exception:
        pass
    return "General"


def chunk_page(page: dict) -> List[Dict[str, Any]]:
    """
    Chunk a single page dict {url, title, text} into LangChain chunks.
    Returns list of {text, metadata} dicts ready for ChromaDB ingestion.
    """
    url = page.get("url", "")
    title = page.get("title", "")
    text = page.get("text", "").strip()

    if not text or len(text) < 30:
        return []

    raw_chunks = _splitter.split_text(text)

    result = []
    for idx, chunk in enumerate(raw_chunks):
        chunk = chunk.strip()
        if not chunk or len(chunk) < 20:
            continue

        result.append({
            "text": chunk,
            "metadata": {
                "source_url": url,
                "title": title,
                "section": _derive_section(url),
                "chunk_index": idx,
                "char_count": len(chunk),
            },
        })

    return result


def chunk_pages(pages: List[dict]) -> List[Dict[str, Any]]:
    """
    Chunk all pages and return a flat list of chunk dicts.
    """
    all_chunks = []
    for page in pages:
        all_chunks.extend(chunk_page(page))
    return all_chunks
