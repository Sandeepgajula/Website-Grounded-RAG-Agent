"""Manage router — list and inspect ingested websites."""

import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from backend.models.schemas import WebsiteInfo, WebsiteStatsResponse
from backend.config import DATA_DIR
from backend.services.vector_store import list_collections, get_collection_stats
from backend.services.crawler import _sanitize_name as sanitize_name

router = APIRouter(prefix="/websites", tags=["Manage"])


@router.get("", response_model=List[WebsiteInfo], summary="List all ingested websites")
async def list_websites():
    """
    List all websites that have been ingested into ChromaDB.
    Also shows whether the source JSON file still exists in data/.
    """
    collections = list_collections()
    result = []

    for col in collections:
        company_name = col["company_name"]
        json_path = DATA_DIR / f"{sanitize_name(company_name)}.json"

        result.append(WebsiteInfo(
            company_name=company_name,
            collection_name=col["collection_name"],
            chunk_count=col["chunk_count"],
            json_file_exists=json_path.exists(),
            json_file_path=str(json_path) if json_path.exists() else None,
        ))

    return result


@router.get("/json-files", summary="List available JSON data files")
async def list_json_files():
    """
    List all JSON files in the data/ directory.
    These are crawled websites ready to be ingested.
    """
    files = []
    for path in DATA_DIR.glob("*.json"):
        if path.name == "token_log.jsonl":
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            files.append({
                "filename": path.name,
                "company_name": data.get("company_name", path.stem),
                "source_url": data.get("source_url", ""),
                "crawled_at": data.get("crawled_at", ""),
                "pages_saved": data.get("pages_saved", len(data.get("pages", []))),
                "file_size_kb": round(path.stat().st_size / 1024, 1),
            })
        except Exception:
            files.append({
                "filename": path.name,
                "company_name": path.stem,
                "source_url": "",
                "crawled_at": "",
                "pages_saved": 0,
                "file_size_kb": round(path.stat().st_size / 1024, 1),
            })
    return files


@router.get("/{company_name}", response_model=WebsiteStatsResponse, summary="Get stats for a specific website")
async def website_stats(company_name: str):
    """
    Get detailed stats for a specific company's knowledge base:
    - Chunk count
    - Unique source URLs
    - Whether the source JSON exists
    """
    stats = get_collection_stats(company_name)
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"No knowledge base found for '{company_name}'.",
        )

    json_path = DATA_DIR / f"{sanitize_name(company_name)}.json"

    return WebsiteStatsResponse(
        company_name=company_name,
        chunk_count=stats["chunk_count"],
        unique_urls=stats["unique_urls"],
        json_file_exists=json_path.exists(),
    )


@router.get("/token-log/entries", summary="Get token usage log entries")
async def get_token_log(limit: int = 100):
    """
    Return recent token usage log entries from data/token_log.jsonl.
    Used by the Token Analytics page.
    """
    log_file = DATA_DIR / "token_log.jsonl"
    if not log_file.exists():
        return {"entries": [], "total": 0}

    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read token log: {e}")

    # Return most recent first
    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}
