"""Ingest router — load JSON data into ChromaDB vector store."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.models.schemas import IngestRequest, IngestResponse, DeleteResponse
from backend.config import DATA_DIR
from backend.services.chunker import chunk_pages
from backend.services.vector_store import add_chunks, delete_collection, collection_exists
from backend.services.crawler import _sanitize_name as sanitize_name

router = APIRouter(prefix="/ingest", tags=["Ingest"])


def _get_json_path(company_name: str) -> Path:
    """Return the expected JSON file path for a company, checking data/ and root."""
    primary = DATA_DIR / f"{sanitize_name(company_name)}.json"
    if primary.exists():
        return primary
    root_fallback = DATA_DIR.parent / f"{sanitize_name(company_name)}.json"
    if root_fallback.exists():
        return root_fallback
    return primary


@router.post("", response_model=IngestResponse, summary="Ingest website JSON into ChromaDB")
async def ingest_website(request: IngestRequest):
    """
    Ingest a previously crawled website JSON into ChromaDB.

    - Reads data/<company_name>.json (or existing cleaned dataset)
    - Chunks each page with configurable size/overlap
    - Embeds using ChromaDB's built-in model (no API key needed)
    - Deduplicates — already-ingested chunks are skipped

    **Run the crawl first** (POST /crawl) to generate the JSON file.
    """
    json_path = _get_json_path(request.company_name)

    if not json_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No data file found for '{request.company_name}'. "
                f"Expected: {json_path}. "
                "Please run POST /crawl first."
            ),
        )

    # Load JSON
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON file: {e}")

    if isinstance(data, list):
        pages = data
    elif isinstance(data, dict):
        pages = data.get("pages", [])
    else:
        pages = []

    if not pages:
        raise HTTPException(
            status_code=422,
            detail="JSON file contains no pages. The crawl may have failed or the site returned no content.",
        )

    # Chunk pages
    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No chunks were generated. Pages may be too short after cleaning.",
        )

    # Embed + store
    result = add_chunks(company_name=request.company_name, chunks=chunks)

    errors = result.get("errors", [])
    if result.get("added", 0) == 0 and errors:
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {errors[0]}",
        )

    return IngestResponse(
        status="success",
        company_name=request.company_name,
        pages_ingested=len(pages),
        chunks_created=result["added"],
        chunks_skipped=result["skipped"],
        message=(
            f"Ingested {result['added']} chunks from {len(pages)} pages "
            f"({result['skipped']} duplicate chunks skipped)."
        ),
        errors=errors,
    )


@router.delete("/{company_name}", response_model=DeleteResponse, summary="Delete a website knowledge base")
async def delete_website(company_name: str):
    """
    Delete the ChromaDB collection for the given company.

    This removes all embedded chunks. The source JSON file in data/ is kept.
    Re-ingest from the same JSON at any time with POST /ingest.
    """
    if not collection_exists(company_name):
        raise HTTPException(
            status_code=404,
            detail=f"No collection found for '{company_name}'. Nothing to delete.",
        )

    success = delete_collection(company_name)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete collection.")

    return DeleteResponse(
        status="success",
        company_name=company_name,
        message=f"ChromaDB collection for '{company_name}' deleted successfully.",
    )
