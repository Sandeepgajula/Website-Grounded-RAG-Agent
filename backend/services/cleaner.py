"""
Multi-stage text cleaning pipeline.
CRITICAL: Poor cleaning = poor embeddings = poor RAG quality.

Pipeline stages (applied per page):
  1. HTML structural noise removal (nav, header, footer, scripts, ads)
  2. Cross-page boilerplate detection and removal
  3. Text normalization (whitespace, unicode, encoding)
  4. Quality filters (min length, link-only lines, single-word lines)
  5. Cross-page deduplication (skip pages with identical content)
"""

import re
import hashlib
import unicodedata
from collections import Counter
from typing import List, Tuple, Optional

import ftfy
from bs4 import BeautifulSoup, Tag


# ─────────────────────────────────────────────
# CSS SELECTOR BLACKLIST
# Elements to strip before extracting text
# ─────────────────────────────────────────────
_NOISE_SELECTORS = [
    "nav", "header", "footer",
    "script", "style", "noscript",
    "iframe", "svg", "canvas",
    # Cookie / GDPR banners
    "[class*='cookie']", "[id*='cookie']",
    "[class*='gdpr']", "[id*='gdpr']",
    "[class*='consent']", "[id*='consent']",
    # Social share / follow
    "[class*='social']", "[class*='share']",
    "[class*='follow']",
    # Newsletter / CTA banners
    "[class*='newsletter']", "[class*='subscribe']",
    "[class*='popup']", "[class*='modal']",
    "[class*='overlay']",
    # Ads
    "[class*='ad-']", "[class*='ads-']", "[id*='ad-']",
    "[class*='advertisement']",
    # Breadcrumbs and pagination
    "[class*='breadcrumb']", "[class*='pagination']",
    "[aria-label='breadcrumb']",
    # Sidebar / related posts
    "[class*='sidebar']", "[class*='related']",
    "[class*='recommended']",
    # Comments section
    "[id='comments']", "[class*='comment']",
    # Print / accessibility
    "[class*='print-only']", "[class*='sr-only']",
    # Sticky bars
    "[class*='sticky']", "[class*='fixed-']",
]

# Minimum characters a page must have after cleaning
_MIN_PAGE_CHARS = 100

# If a text block appears in more than this fraction of pages, treat as boilerplate
_BOILERPLATE_THRESHOLD = 0.55


# ─────────────────────────────────────────────
# STAGE 1: HTML STRUCTURAL NOISE REMOVAL
# ─────────────────────────────────────────────
def _strip_html_noise(html: str) -> str:
    """Remove structural noise elements from HTML before text extraction."""
    soup = BeautifulSoup(html, "lxml")

    # Remove by selector
    for selector in _NOISE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # Remove hidden elements
    for el in soup.find_all(style=True):
        style = el.get("style", "")
        if "display:none" in style.replace(" ", "") or "visibility:hidden" in style.replace(" ", ""):
            el.decompose()

    # Remove elements with aria-hidden
    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        el.decompose()

    return str(soup)


# ─────────────────────────────────────────────
# STAGE 2: TEXT EXTRACTION
# ─────────────────────────────────────────────
def _extract_text(html: str) -> str:
    """Extract clean text from HTML, preserving paragraph structure."""
    soup = BeautifulSoup(html, "lxml")

    # Get text with separator to preserve blocks
    text = soup.get_text(separator="\n")
    return text


# ─────────────────────────────────────────────
# STAGE 3: TEXT NORMALIZATION
# ─────────────────────────────────────────────
def _normalize_text(text: str) -> str:
    """
    Normalize whitespace, fix encoding issues, remove control characters.
    """
    # Fix encoding problems (mojibake)
    text = ftfy.fix_text(text)

    # Normalize unicode to NFC form
    text = unicodedata.normalize("NFC", text)

    # Remove control characters (except newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Remove zero-width and invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", text)

    # Replace non-breaking spaces, thin spaces, etc. with regular space
    text = re.sub(r"[\u00a0\u202f\u2009\u2002\u2003]", " ", text)

    # Collapse multiple spaces / tabs into one
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Normalize multiple blank lines — max 2 consecutive
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────
# STAGE 4: LINE-LEVEL QUALITY FILTER
# ─────────────────────────────────────────────
_URL_PATTERN = re.compile(r"^https?://\S+$")
_PURE_PUNCT = re.compile(r"^[\W\d\s]+$")
_BULLET_ONLY = re.compile(r"^[\u2022\u2023\u25e6\u2043\u2219•◦‣⁃*\-–—]\s*$")


def _filter_lines(text: str) -> str:
    """
    Remove low-quality lines:
    - Pure URLs
    - Lines with only punctuation / symbols
    - Bullet symbols with no text
    - Very short lines (< 4 chars) that aren't part of context
    - Lines that are just numbers (page numbers, counts)
    """
    lines = text.split("\n")
    good_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty (we'll re-add controlled spacing)
        if not stripped:
            good_lines.append("")
            continue

        # Skip pure URL lines
        if _URL_PATTERN.match(stripped):
            continue

        # Skip bullet-only lines
        if _BULLET_ONLY.match(stripped):
            continue

        # Skip pure punctuation / digit-only lines
        if _PURE_PUNCT.match(stripped):
            continue

        # Skip lines that are only 1-3 characters (nav arrows, etc.)
        if len(stripped) < 4:
            continue

        good_lines.append(line)

    # Rebuild, collapsing runs of blank lines
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(good_lines))
    return result.strip()


# ─────────────────────────────────────────────
# BOILERPLATE DETECTION (cross-page)
# ─────────────────────────────────────────────
def detect_boilerplate(pages_texts: List[str]) -> set:
    """
    Detect text blocks that appear on too many pages (boilerplate).
    Returns a set of block hashes considered boilerplate.

    Strategy:
    - Split each page into paragraph blocks (split on double newline)
    - Hash each block
    - Count occurrences across all pages
    - Flag blocks appearing on > THRESHOLD fraction of pages
    """
    if not pages_texts:
        return set()

    total = len(pages_texts)
    block_counts: Counter = Counter()

    for text in pages_texts:
        blocks = set()  # unique blocks per page to avoid double-counting
        for block in text.split("\n\n"):
            block_clean = block.strip()
            if len(block_clean) < 20:
                continue
            bh = hashlib.md5(block_clean.encode("utf-8")).hexdigest()
            blocks.add(bh)

        for bh in blocks:
            block_counts[bh] += 1

    threshold_count = max(2, int(total * _BOILERPLATE_THRESHOLD))
    return {bh for bh, count in block_counts.items() if count >= threshold_count}


def remove_boilerplate_blocks(text: str, boilerplate_hashes: set) -> str:
    """Remove boilerplate paragraphs from a page's text."""
    if not boilerplate_hashes:
        return text

    kept = []
    for block in text.split("\n\n"):
        block_clean = block.strip()
        if len(block_clean) < 20:
            kept.append(block)
            continue
        bh = hashlib.md5(block_clean.encode("utf-8")).hexdigest()
        if bh not in boilerplate_hashes:
            kept.append(block)

    return "\n\n".join(kept).strip()


# ─────────────────────────────────────────────
# PAGE DEDUPLICATION
# ─────────────────────────────────────────────
def compute_content_hash(text: str) -> str:
    """MD5 hash of the cleaned text (for cross-page dedup)."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────
def clean_page_html(html: str) -> str:
    """
    Full per-page cleaning pipeline:
    HTML → structural strip → text extract → normalize → line filter.

    Returns clean text ready for boilerplate detection + chunking.
    """
    # Stage 1: Remove structural noise from HTML
    clean_html = _strip_html_noise(html)

    # Stage 2: Extract text
    text = _extract_text(clean_html)

    # Stage 3: Normalize
    text = _normalize_text(text)

    # Stage 4: Line-level quality filter
    text = _filter_lines(text)

    return text


def clean_and_deduplicate_pages(
    raw_pages: List[dict],
) -> List[dict]:
    """
    Full pipeline for a list of raw pages:
      [{url, title, html or text}, ...]

    Steps:
      1. Per-page clean (HTML or plain text)
      2. Cross-page boilerplate detection and removal
      3. Cross-page deduplication
      4. Min-length filter

    Returns list of cleaned pages: [{url, title, text}, ...]
    """
    # --- Step 1: Per-page cleaning ---
    stage1 = []
    for page in raw_pages:
        html = page.get("html", "")
        text = page.get("text", "")

        if html:
            clean = clean_page_html(html)
        elif text:
            # Plain text path (e.g., already-extracted JSON)
            clean = _normalize_text(text)
            clean = _filter_lines(clean)
        else:
            continue

        if len(clean) < _MIN_PAGE_CHARS:
            continue

        stage1.append({
            "url": page.get("url", ""),
            "title": page.get("title", ""),
            "text": clean,
        })

    if not stage1:
        return []

    # --- Step 2: Boilerplate detection ---
    boilerplate_hashes = detect_boilerplate([p["text"] for p in stage1])

    # --- Step 3: Remove boilerplate + dedup ---
    seen_hashes: set = set()
    final = []

    for page in stage1:
        text = remove_boilerplate_blocks(page["text"], boilerplate_hashes)

        # Normalize again after removal
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if len(text) < _MIN_PAGE_CHARS:
            continue

        content_hash = compute_content_hash(text)
        if content_hash in seen_hashes:
            continue  # duplicate page content

        seen_hashes.add(content_hash)
        final.append({**page, "text": text})

    return final
