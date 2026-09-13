"""Crawl router — trigger and monitor website crawl jobs."""

import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.models.schemas import CrawlRequest, CrawlStatusResponse
from backend.services.crawler import crawl_website, get_task_state, make_task_id

router = APIRouter(prefix="/crawl", tags=["Crawl"])


@router.post("", response_model=CrawlStatusResponse, summary="Start a website crawl")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Trigger an async crawl of the given homepage URL.

    - Crawls all internal pages (up to max_pages)
    - Cleans, deduplicates, and saves to data/<company_name>.json
    - Returns a task_id to poll for status

    The crawl runs as a background task — call GET /crawl/status/{task_id} to track progress.
    """
    task_id = make_task_id(request.company_name)

    background_tasks.add_task(
        crawl_website,
        start_url=str(request.url),
        company_name=request.company_name,
        max_pages=request.max_pages,
        task_id=task_id,
    )

    return CrawlStatusResponse(
        task_id=task_id,
        status="running",
        pages_crawled=0,
        pages_saved=0,
        message="Crawl started. Poll /crawl/status/{task_id} for updates.",
    )


@router.get("/status/{task_id}", response_model=CrawlStatusResponse, summary="Check crawl status")
async def crawl_status(task_id: str):
    """
    Poll the crawl status for a given task_id.

    Returns:
      - status: "running" | "done" | "failed"
      - pages_crawled: total pages visited
      - pages_saved: pages that passed cleaning
      - json_file: path to saved JSON (only when done)
    """
    state = get_task_state(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    return CrawlStatusResponse(
        task_id=task_id,
        status=state.get("status", "unknown"),
        pages_crawled=state.get("pages_crawled", 0),
        pages_saved=state.get("pages_saved", 0),
        message=state.get("message", ""),
        json_file=state.get("json_file"),
    )
