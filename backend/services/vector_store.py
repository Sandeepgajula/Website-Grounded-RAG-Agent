"""
ChromaDB vector store service.

Uses ChromaDB's built-in default embedding function (all-MiniLM-L6-v2)
— no external API keys, no configuration required.

Each website gets its own named collection:
  company_name → sanitized → e.g. "python_docs"

Design:
  - PersistentClient stores data to disk (CHROMA_PERSIST_DIR)
  - DefaultEmbeddingFunction is bundled with chromadb (onnxruntime backend)
  - Supports add, search, delete, list, and stats operations
"""

import re
import hashlib
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from backend.config import CHROMA_PERSIST_DIR, RAG_TOP_K, RAG_MIN_RELEVANCE_SCORE


# ─────────────────────────────────────────────
# SINGLETON CLIENT
# ─────────────────────────────────────────────
_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    return _client


def _get_embedding_fn():
    """Return ChromaDB's bundled default embedding function."""
    return DefaultEmbeddingFunction()


# ─────────────────────────────────────────────
# COLLECTION NAME SANITIZATION
# ─────────────────────────────────────────────
def _sanitize_collection_name(company_name: str) -> str:
    """
    Convert company name to a valid ChromaDB collection name.
    Rules: 3-63 chars, only [a-z0-9_-], start/end alphanumeric.
    """
    name = company_name.lower().strip()
    name = re.sub(r"[^\w\-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    # Ensure min length
    if len(name) < 3:
        name = name + "_kb"
    # Truncate to 63 chars
    return name[:63]


# ─────────────────────────────────────────────
# CHUNK ID GENERATION
# ─────────────────────────────────────────────
def _chunk_id(text: str, url: str, idx: int) -> str:
    """Deterministic ID for deduplication."""
    raw = f"{url}::{idx}::{text[:100]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
# ADD CHUNKS TO COLLECTION
# ─────────────────────────────────────────────
def add_chunks(company_name: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Embed and store chunks into the company's ChromaDB collection.

    Args:
        company_name: identifier for the collection
        chunks: list of {text, metadata} dicts from chunker

    Returns:
        stats dict
    """
    if not chunks:
        return {"added": 0, "skipped": 0, "errors": []}

    client = _get_client()
    collection_name = _sanitize_collection_name(company_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=_get_embedding_fn(),
        metadata={"company_name": company_name, "hnsw:space": "cosine"},
    )

    # Get existing IDs to avoid re-embedding duplicates
    existing_ids: set = set()
    try:
        existing = collection.get(include=[])
        existing_ids = set(existing["ids"])
    except Exception:
        pass

    texts, metadatas, ids = [], [], []
    skipped = 0

    for chunk in chunks:
        text = chunk.get("text", "").strip()
        meta = chunk.get("metadata", {})
        chunk_idx = meta.get("chunk_index", 0)
        source_url = meta.get("source_url", "")

        if not text:
            continue

        doc_id = _chunk_id(text, source_url, chunk_idx)

        if doc_id in existing_ids:
            skipped += 1
            continue

        # ChromaDB metadata values must be str | int | float | bool
        safe_meta = {
            k: str(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in meta.items()
        }

        texts.append(text)
        metadatas.append(safe_meta)
        ids.append(doc_id)

    if not texts:
        return {"added": 0, "skipped": skipped, "errors": []}

    errors = []
    added = 0
    # Batch in groups of 100 to avoid memory spikes
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        try:
            collection.add(
                documents=texts[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
                ids=ids[i:i + batch_size],
            )
            added += len(texts[i:i + batch_size])
        except Exception as e:
            errors.append(str(e))

    return {"added": added, "skipped": skipped, "errors": errors}


# ─────────────────────────────────────────────
# SIMILARITY SEARCH
# ─────────────────────────────────────────────
def similarity_search(
    company_name: str,
    query: str,
    top_k: int = RAG_TOP_K,
) -> List[Dict[str, Any]]:
    """
    Search the company's collection for relevant chunks.

    Returns list of {text, metadata, distance, score} sorted by relevance.
    score = 1 - cosine_distance (higher = more relevant).
    """
    client = _get_client()
    collection_name = _sanitize_collection_name(company_name)

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=_get_embedding_fn(),
        )
    except Exception:
        return []  # collection doesn't exist

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    output = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to relevance score (0 to 1)
        score = max(0.0, 1.0 - (dist / 2.0))
        output.append({
            "text": doc,
            "metadata": meta,
            "source_url": meta.get("source_url", "") if isinstance(meta, dict) else "",
            "title": meta.get("title", "") if isinstance(meta, dict) else "",
            "distance": dist,
            "score": score,
        })

    return output


# ─────────────────────────────────────────────
# DELETE COLLECTION
# ─────────────────────────────────────────────
def delete_collection(company_name: str) -> bool:
    """Delete the ChromaDB collection for a company. Returns True on success."""
    client = _get_client()
    collection_name = _sanitize_collection_name(company_name)
    try:
        client.delete_collection(collection_name)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────
# LIST COLLECTIONS
# ─────────────────────────────────────────────
def list_collections() -> List[Dict[str, Any]]:
    """Return all collections with their chunk counts."""
    client = _get_client()
    try:
        collections = client.list_collections()
        result = []
        for col in collections:
            coll = client.get_collection(
                name=col.name,
                embedding_function=_get_embedding_fn(),
            )
            meta = col.metadata or {}
            result.append({
                "collection_name": col.name,
                "company_name": meta.get("company_name", col.name),
                "chunk_count": coll.count(),
            })
        return result
    except Exception:
        return []


# ─────────────────────────────────────────────
# COLLECTION STATS
# ─────────────────────────────────────────────
def get_collection_stats(company_name: str) -> Optional[Dict[str, Any]]:
    """Return stats for a specific company's collection."""
    client = _get_client()
    collection_name = _sanitize_collection_name(company_name)
    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=_get_embedding_fn(),
        )
        count = collection.count()

        # Get unique URLs from metadata
        all_meta = collection.get(include=["metadatas"])
        urls = {m.get("source_url", "") for m in all_meta.get("metadatas", [])}

        return {
            "company_name": company_name,
            "collection_name": collection_name,
            "chunk_count": count,
            "unique_urls": len(urls),
        }
    except Exception:
        return None


def collection_exists(company_name: str) -> bool:
    """Check if a collection exists for the given company."""
    client = _get_client()
    collection_name = _sanitize_collection_name(company_name)
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False
