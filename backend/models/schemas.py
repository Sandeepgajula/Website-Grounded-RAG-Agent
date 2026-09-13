"""
Pydantic schemas for all API request/response models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


# ═════════════════════════════════════════════
# CRAWL
# ═════════════════════════════════════════════

class CrawlRequest(BaseModel):
    url: str = Field(..., description="Homepage URL to crawl (e.g. https://example.com)")
    company_name: str = Field(..., description="Identifier used for the JSON file and ChromaDB collection (e.g. 'python_docs')")
    max_pages: int = Field(100, ge=1, le=500, description="Maximum number of pages to crawl")

    model_config = {
        "json_schema_extra": {
            "examples": [{"url": "https://docs.python.org/3/", "company_name": "python_docs", "max_pages": 50}]
        }
    }


class CrawlStatusResponse(BaseModel):
    task_id: str
    status: str          # "running" | "done" | "failed"
    pages_crawled: int
    pages_saved: int
    message: str
    json_file: Optional[str] = None


# ═════════════════════════════════════════════
# INGEST
# ═════════════════════════════════════════════

class IngestRequest(BaseModel):
    company_name: str = Field(..., description="Company name — must match the JSON file in data/")

    model_config = {
        "json_schema_extra": {
            "examples": [{"company_name": "python_docs"}]
        }
    }


class IngestResponse(BaseModel):
    status: str
    company_name: str
    pages_ingested: int
    chunks_created: int
    chunks_skipped: int
    message: str
    errors: List[str] = []


# ═════════════════════════════════════════════
# RAG
# ═════════════════════════════════════════════

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str


class RagRequest(BaseModel):
    query: str = Field(..., description="Natural-language question")
    company_name: str = Field(..., description="Which website knowledge base to query")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Conversation history")
    stream: bool = Field(True, description="Stream the response via SSE")
    top_k: Optional[int] = Field(None, description="Override default number of chunks to retrieve")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "query": "What is a generator in Python?",
                "company_name": "python_docs",
                "history": [],
                "stream": True
            }]
        }
    }


class Citation(BaseModel):
    url: str
    title: str
    snippet: str


class RagResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    is_grounded: bool           # False = not enough info in the knowledge base
    token_usage: Dict[str, Any]


# ═════════════════════════════════════════════
# MANAGE / WEBSITES
# ═════════════════════════════════════════════

class WebsiteInfo(BaseModel):
    company_name: str
    collection_name: str
    chunk_count: int
    json_file_exists: bool
    json_file_path: Optional[str] = None


class WebsiteStatsResponse(BaseModel):
    company_name: str
    chunk_count: int
    unique_urls: int
    json_file_exists: bool


class DeleteResponse(BaseModel):
    status: str
    company_name: str
    message: str


# ═════════════════════════════════════════════
# TOKEN ANALYTICS
# ═════════════════════════════════════════════

class TokenLogEntry(BaseModel):
    timestamp: str
    company_name: str
    query: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
