"""
Async website crawler using httpx + BeautifulSoup.

Features:
- Follows only internal links (same domain)
- Respects robots.txt (politely)
- Configurable delay between requests
- Deduplicates URLs (normalized)
- Extracts title + raw HTML per page
- Saves result to data/<company_name>.json
- Reports live progress via shared state dict
"""

import asyncio
import json
import re
import time
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from backend.config import DATA_DIR, MAX_CRAWL_PAGES, CRAWL_DELAY, CRAWL_TIMEOUT
from backend.services.cleaner import clean_and_deduplicate_pages


# ─────────────────────────────────────────────
# TASK STATE (in-memory, keyed by task_id)
# ─────────────────────────────────────────────
_crawl_tasks: Dict[str, dict] = {}


def get_task_state(task_id: str) -> Optional[dict]:
    return _crawl_tasks.get(task_id)


def _make_task_id(company_name: str) -> str:
    ts = str(time.time()).encode()
    return f"{company_name}_{hashlib.md5(ts).hexdigest()[:8]}"


# ─────────────────────────────────────────────
# URL NORMALIZATION
# ─────────────────────────────────────────────
def _normalize_url(url: str, base: str = "") -> str:
    """
    Normalize a URL:
    - Resolve relative URLs against base
    - Remove fragments (#)
    - Remove trailing slash from path
    - Lowercase scheme + host
    """
    url = urljoin(base, url.strip())
    parsed = urlparse(url)

    # Drop fragment
    normalized = urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        parsed.params,
        parsed.query,
        "",   # no fragment
    ))
    return normalized


def _is_internal_link(url: str, base_domain: str) -> bool:
    """Return True if url belongs to base_domain."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower() == base_domain.lower()
    except Exception:
        return False


_SKIP_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp4", ".mp3", ".avi", ".mov",
    ".css", ".js", ".json", ".xml",
}


def _should_skip_url(url: str) -> bool:
    """Skip non-HTML resources."""
    path = urlparse(url).path.lower()
    _, ext = path.rsplit(".", 1) if "." in path.split("/")[-1] else ("", "")
    return f".{ext}" in _SKIP_EXTENSIONS if ext else False


# ─────────────────────────────────────────────
# ROBOTS.TXT
# ─────────────────────────────────────────────
def _load_robots(base_url: str) -> Optional[RobotFileParser]:
    try:
        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp
    except Exception:
        return None


# ─────────────────────────────────────────────
# PAGE FETCHER
# ─────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; WebsiteRAGBot/1.0; "
        "+https://github.com/website-rag-agent)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    """
    Fetch a URL, return {url, title, html} or None on failure.
    """
    try:
        response = await client.get(url, headers=_HEADERS, timeout=CRAWL_TIMEOUT, follow_redirects=True)

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return None

        if response.status_code != 200:
            return None

        html = response.text

        # Extract title
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        return {"url": str(response.url), "title": title, "html": html}

    except (httpx.TimeoutException, httpx.ConnectError, httpx.TooManyRedirects):
        return None
    except Exception:
        return None


def _extract_links(html: str, current_url: str) -> List[str]:
    """Extract all <a href> links from a page."""
    soup = BeautifulSoup(html, "lxml")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        normalized = _normalize_url(href, current_url)
        links.append(normalized)
    return links


# ─────────────────────────────────────────────
# MAIN CRAWLER
# ─────────────────────────────────────────────
async def crawl_website(
    start_url: str,
    company_name: str,
    max_pages: int = MAX_CRAWL_PAGES,
    task_id: Optional[str] = None,
) -> dict:
    """
    Crawl a website starting from start_url.
    Saves cleaned JSON to data/<company_name>.json.

    Returns summary dict with stats.
    """
    if task_id is None:
        task_id = _make_task_id(company_name)

    # Init task state
    _crawl_tasks[task_id] = {
        "status": "running",
        "pages_crawled": 0,
        "pages_saved": 0,
        "message": "Starting crawl...",
        "json_file": None,
    }

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc.lower()
    scheme = parsed_start.scheme

    # Robots.txt
    robots = _load_robots(f"{scheme}://{base_domain}")

    def allowed(url: str) -> bool:
        if robots is None:
            return True
        return robots.can_fetch("*", url)

    visited: Set[str] = set()
    queue: List[str] = [_normalize_url(start_url)]
    raw_pages: List[dict] = []

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5),
        verify=False,  # some corporate sites have self-signed certs
    ) as client:
        while queue and len(raw_pages) < max_pages:
            url = queue.pop(0)

            if url in visited:
                continue

            if _should_skip_url(url):
                continue

            if not _is_internal_link(url, base_domain):
                continue

            if not allowed(url):
                continue

            visited.add(url)
            _crawl_tasks[task_id]["pages_crawled"] = len(visited)
            _crawl_tasks[task_id]["message"] = f"Crawling: {url}"

            page = await _fetch_page(client, url)
            if not page:
                await asyncio.sleep(CRAWL_DELAY)
                continue

            # Extract links and add to queue
            links = _extract_links(page["html"], page["url"])
            for link in links:
                if link not in visited and link not in queue:
                    queue.append(link)

            raw_pages.append(page)
            await asyncio.sleep(CRAWL_DELAY)

    _crawl_tasks[task_id]["message"] = "Cleaning and deduplicating pages..."

    # Run cleaning pipeline
    cleaned_pages = clean_and_deduplicate_pages(raw_pages)

    # Save to JSON
    output_file = DATA_DIR / f"{_sanitize_name(company_name)}.json"
    output_data = {
        "company_name": company_name,
        "source_url": start_url,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "pages_crawled": len(raw_pages),
        "pages_saved": len(cleaned_pages),
        "pages": [
            {"url": p["url"], "title": p["title"], "text": p["text"]}
            for p in cleaned_pages
        ],
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    _crawl_tasks[task_id].update({
        "status": "done",
        "pages_crawled": len(raw_pages),
        "pages_saved": len(cleaned_pages),
        "message": f"Crawl complete. {len(cleaned_pages)} pages saved.",
        "json_file": str(output_file),
    })

    return _crawl_tasks[task_id]


def _sanitize_name(name: str) -> str:
    """Convert company name to a safe filename."""
    return re.sub(r"[^\w\-]", "_", name.lower()).strip("_")


def make_task_id(company_name: str) -> str:
    return _make_task_id(company_name)
