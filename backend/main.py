"""
Website RAG Agent — FastAPI Backend
=====================================
Endpoints:
  POST /crawl              — Crawl a website and save JSON
  GET  /crawl/status/{id} — Poll crawl progress
  POST /ingest             — Ingest JSON into ChromaDB
  DELETE /ingest/{company} — Remove a knowledge base
  POST /rag                — Ask a question (streaming or JSON)
  GET  /websites           — List all ingested websites
  GET  /websites/json-files — List available JSON data files
  GET  /websites/{company} — Stats for one website
  GET  /websites/token-log/entries — Token usage log
"""

import sys
import os
# Add project root to path so backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import crawl, ingest, rag, manage

# ─────────────────────────────────────────────
# App
# ─────────────────────────────────────────────
app = FastAPI(
    title="Website RAG Agent API",
    description=(
        "AI agent that crawls websites, builds a vector knowledge base, "
        "and answers questions grounded in the website content.\n\n"
        "**Features:**\n"
        "- Crawl any public website (async, respects robots.txt)\n"
        "- Multi-stage text cleaning pipeline\n"
        "- ChromaDB vector store (built-in embeddings, no API key)\n"
        "- LangGraph RAG with citations and sufficiency check\n"
        "- Token usage tracking and cost estimation\n"
        "- Multi-website support (separate collection per site)"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.include_router(crawl.router)
app.include_router(ingest.router)
app.include_router(rag.router)
app.include_router(manage.router)


# ─────────────────────────────────────────────
# Health & Root
# ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Website RAG Agent API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Lightweight health check for monitoring."""
    return {"status": "ok"}


@app.get("/info", tags=["Health"])
async def get_info():
    """Return collection stats for sidebar status card."""
    from backend.services.vector_store import list_collections
    cols = list_collections()
    total_objects = sum(c.get("chunk_count", 0) for c in cols)
    primary_name = cols[0]["collection_name"] if cols else "None"
    return {
        "status": "online",
        "total_objects": total_objects,
        "collection_name": primary_name,
        "collections": cols,
    }

