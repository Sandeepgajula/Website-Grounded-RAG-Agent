"""
LangGraph-based RAG pipeline with:
  - Retrieval from ChromaDB (with relevance gating)
  - Sufficiency check (route to "not enough info" if context is weak)
  - Grounded generation via OpenAI-compatible LLM
  - Citation extraction (source URLs + snippets)
  - Token usage tracking + cost estimation
  - Streaming SSE support
"""

import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Generator, TypedDict

import tiktoken
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

from backend.config import (
    LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY, get_llm_config,
    RAG_TOP_K, RAG_MIN_RELEVANCE_SCORE,
    COST_PER_1K_INPUT, COST_PER_1K_OUTPUT,
    TOKEN_LOG_FILE,
)
from backend.services.vector_store import similarity_search


# ─────────────────────────────────────────────
# TOKEN COUNTING
# ─────────────────────────────────────────────
try:
    _tokenizer = tiktoken.encoding_for_model("gpt-4o")
except Exception:
    _tokenizer = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    try:
        return len(_tokenizer.encode(text))
    except Exception:
        return len(text) // 4  # rough fallback


def _compute_cost(input_tokens: int, output_tokens: int) -> Dict[str, float]:
    """Compute estimated cost in USD."""
    input_cost = (input_tokens / 1000) * COST_PER_1K_INPUT
    output_cost = (output_tokens / 1000) * COST_PER_1K_OUTPUT
    return {
        "input_cost_usd": round(input_cost, 8),
        "output_cost_usd": round(output_cost, 8),
        "total_cost_usd": round(input_cost + output_cost, 8),
    }


# ─────────────────────────────────────────────
# TOKEN LOG (persist to JSONL)
# ─────────────────────────────────────────────
def _log_token_usage(
    company_name: str,
    query: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Append token usage entry to the JSONL log file."""
    try:
        costs = _compute_cost(input_tokens, output_tokens)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "company_name": company_name,
            "query": query[:200],  # truncate long queries
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            **costs,
        }
        with open(TOKEN_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # never let logging crash the main pipeline


# ─────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a precise, grounded assistant that answers questions STRICTLY using the provided website content.

RULES (follow exactly):
1. Answer ONLY from the [CONTEXT] below. Never use outside knowledge or training data.
2. If the context does not contain enough information, respond ONLY with:
   "I don't have enough information from the website to answer this question accurately."
3. Keep answers concise and well-structured. Use bullet points or numbered steps when helpful.
4. At the end, list ONLY the sources you directly referenced — never list sources you did not use.
5. Never fabricate facts, URLs, product names, or prices.
6. If the question contains a false premise, politely correct it using only context evidence.

Response format:
[Your grounded answer]

**Sources:**
- [Page Title] — [URL]"""

_NOT_ENOUGH_INFO_RESPONSE = (
    "I don't have enough information from the website to answer this question accurately. "
    "The retrieved content doesn't cover this topic. "
    "Please visit the website directly or try rephrasing your question."
)


# ─────────────────────────────────────────────
# LANGGRAPH STATE
# ─────────────────────────────────────────────
class RagState(TypedDict):
    query: str
    rewritten_query: str          # query after rewriting for better retrieval
    company_name: str
    history: List[Dict[str, str]]
    top_k: int
    # Retrieved
    chunks: List[Dict[str, Any]]
    has_sufficient_context: bool
    # Generated
    answer: str
    citations: List[Dict[str, str]]
    # Token stats
    input_tokens: int
    output_tokens: int


# ─────────────────────────────────────────────
# GRAPH NODES
# ─────────────────────────────────────────────
def _node_rewrite_query(state: RagState) -> RagState:
    """
    Node 0: Rewrite the user query into a clean, retrieval-optimised search phrase.
    This strips conversational filler and expands abbreviations, boosting recall.
    """
    query = state["query"]
    history = state.get("history") or []

    # Build a minimal rewriting prompt
    rewrite_prompt = (
        "Rewrite the following user question as a short, clear, keyword-rich search query "
        "suitable for a vector similarity search. Remove filler words. Keep it under 20 words. "
        "Return ONLY the rewritten query, nothing else.\n\n"
        f"Question: {query}\nRewritten:"
    )

    base_url, model_name, api_key = get_llm_config()
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        temperature=0,
        max_tokens=60,
    )
    try:
        result = llm.invoke([HumanMessage(content=rewrite_prompt)])
        rewritten = result.content.strip().strip('"').strip("'") or query
    except Exception:
        rewritten = query  # fall back to original on error

    state["rewritten_query"] = rewritten
    return state


def _node_retrieve(state: RagState) -> RagState:
    """Node 1: Retrieve relevant chunks from ChromaDB using the rewritten query."""
    search_query = state.get("rewritten_query") or state["query"]
    chunks = similarity_search(
        company_name=state["company_name"],
        query=search_query,
        top_k=state["top_k"],
    )

    # Filter by minimum relevance
    relevant = [c for c in chunks if c["score"] >= RAG_MIN_RELEVANCE_SCORE]
    state["chunks"] = relevant
    return state


def _node_check_sufficiency(state: RagState) -> str:
    """Node 2 (conditional): Determine if we have enough context."""
    if not state["chunks"]:
        return "insufficient"
    # At least one chunk with decent score
    best_score = max(c["score"] for c in state["chunks"])
    if best_score < RAG_MIN_RELEVANCE_SCORE:
        return "insufficient"
    return "sufficient"


def _node_generate_no_info(state: RagState) -> RagState:
    """Node 3a: Not enough info path."""
    state["answer"] = _NOT_ENOUGH_INFO_RESPONSE
    state["citations"] = []
    state["has_sufficient_context"] = False
    state["input_tokens"] = _count_tokens(state["query"])
    state["output_tokens"] = _count_tokens(_NOT_ENOUGH_INFO_RESPONSE)
    return state


def _node_generate(state: RagState) -> RagState:
    """Node 3b: Generate grounded answer with citations."""
    chunks = state["chunks"]

    # Build context string with source labels
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        title = meta.get("title", url)
        context_parts.append(f"[Source {i+1}: {title} ({url})]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)

    # Build messages
    system_content = f"{_SYSTEM_PROMPT}\n\n[CONTEXT]\n{context}"
    messages = [SystemMessage(content=system_content)]

    # Add history (last 5 turns)
    for msg in (state.get("history") or [])[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=state["query"]))

    # Count input tokens
    full_input = system_content + state["query"]
    for msg in state.get("history", [])[-5:]:
        full_input += msg.get("content", "")
    input_tokens = _count_tokens(full_input)

    # Call LLM with dynamic config
    base_url, model_name, api_key = get_llm_config()
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        temperature=0.2,
        max_tokens=1500,
    )

    try:
        response = llm.invoke(messages)
        answer = response.content
    except Exception as e:
        answer = f"Error generating response: {str(e)}"

    output_tokens = _count_tokens(answer)

    # Extract citations from used chunks
    seen_urls: set = set()
    citations = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        title = meta.get("title", url)
        snippet = chunk["text"][:200].strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append({
                "url": url,
                "title": title,
                "snippet": snippet,
            })

    state["answer"] = answer
    state["citations"] = citations
    state["has_sufficient_context"] = True
    state["input_tokens"] = input_tokens
    state["output_tokens"] = output_tokens

    return state


# ─────────────────────────────────────────────
# BUILD LANGGRAPH
# ─────────────────────────────────────────────
def _build_rag_graph():
    graph = StateGraph(RagState)

    graph.add_node("rewrite", _node_rewrite_query)
    graph.add_node("retrieve", _node_retrieve)
    graph.add_node("generate_no_info", _node_generate_no_info)
    graph.add_node("generate", _node_generate)

    graph.set_entry_point("rewrite")
    graph.add_edge("rewrite", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        _node_check_sufficiency,
        {
            "insufficient": "generate_no_info",
            "sufficient": "generate",
        },
    )
    graph.add_edge("generate_no_info", END)
    graph.add_edge("generate", END)

    return graph.compile()


_rag_graph = _build_rag_graph()


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────
def run_rag(
    query: str,
    company_name: str,
    history: Optional[List[Dict[str, str]]] = None,
    top_k: int = RAG_TOP_K,
) -> Dict[str, Any]:
    """
    Run the full RAG pipeline (non-streaming).
    Returns {answer, citations, is_grounded, token_usage}.
    """
    initial_state: RagState = {
        "query": query,
        "rewritten_query": "",
        "company_name": company_name,
        "history": history or [],
        "top_k": top_k,
        "chunks": [],
        "has_sufficient_context": False,
        "answer": "",
        "citations": [],
        "input_tokens": 0,
        "output_tokens": 0,
    }

    final_state = _rag_graph.invoke(initial_state)

    input_tokens = final_state["input_tokens"]
    output_tokens = final_state["output_tokens"]
    costs = _compute_cost(input_tokens, output_tokens)

    # Persist log
    _log_token_usage(company_name, query, input_tokens, output_tokens)

    return {
        "query": query,
        "answer": final_state["answer"],
        "citations": final_state["citations"],
        "is_grounded": final_state["has_sufficient_context"],
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            **costs,
        },
    }


def run_rag_stream(
    query: str,
    company_name: str,
    history: Optional[List[Dict[str, str]]] = None,
    top_k: int = RAG_TOP_K,
) -> Generator[str, None, None]:
    """
    Streaming RAG pipeline. Yields SSE-formatted chunks.

    Format:
      data: {"type": "chunk", "content": "..."}
      data: {"type": "citations", "citations": [...], "token_usage": {...}}
      data: {"type": "done"}
    """
    # 1. Retrieve context
    from backend.services.vector_store import similarity_search
    chunks = similarity_search(company_name=company_name, query=query, top_k=top_k)
    relevant = [c for c in chunks if c["score"] >= RAG_MIN_RELEVANCE_SCORE]

    # 2. Check sufficiency
    if not relevant:
        payload = json.dumps({
            "type": "chunk",
            "content": _NOT_ENOUGH_INFO_RESPONSE,
            "is_grounded": False,
        })
        yield f"data: {payload}\n\n"

        # Token log
        i_tok = _count_tokens(query)
        o_tok = _count_tokens(_NOT_ENOUGH_INFO_RESPONSE)
        _log_token_usage(company_name, query, i_tok, o_tok)

        costs = _compute_cost(i_tok, o_tok)
        token_payload = json.dumps({
            "type": "citations",
            "citations": [],
            "is_grounded": False,
            "token_usage": {
                "input_tokens": i_tok,
                "output_tokens": o_tok,
                "total_tokens": i_tok + o_tok,
                **costs,
            }
        })
        yield f"data: {token_payload}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"
        return

    # 3. Build context + messages
    context_parts = []
    for i, chunk in enumerate(relevant):
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        title = meta.get("title", url)
        context_parts.append(f"[Source {i+1}: {title} ({url})]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_parts)
    system_content = f"{_SYSTEM_PROMPT}\n\n[CONTEXT]\n{context}"

    messages = [SystemMessage(content=system_content)]
    for msg in (history or [])[-5:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=query))

    full_input = system_content + query + "".join(m.get("content", "") for m in (history or [])[-5:])
    input_tokens = _count_tokens(full_input)

    # 4. Stream LLM response with dynamic config
    base_url, model_name, api_key = get_llm_config()
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model_name,
        temperature=0.2,
        max_tokens=1500,
        streaming=True,
    )

    full_answer = ""
    try:
        for chunk in llm.stream(messages):
            delta = chunk.content if hasattr(chunk, "content") else ""
            if delta:
                full_answer += delta
                payload = json.dumps({"type": "chunk", "content": delta, "is_grounded": True})
                yield f"data: {payload}\n\n"
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        payload = json.dumps({"type": "chunk", "content": error_msg, "is_grounded": False})
        yield f"data: {payload}\n\n"
        full_answer = error_msg

    output_tokens = _count_tokens(full_answer)
    _log_token_usage(company_name, query, input_tokens, output_tokens)

    # 5. Send citations + token info
    seen_urls: set = set()
    citations = []
    for chunk in relevant:
        meta = chunk.get("metadata", {})
        url = meta.get("source_url", "")
        title = meta.get("title", url)
        snippet = chunk["text"][:200].strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            citations.append({"url": url, "title": title, "snippet": snippet})

    costs = _compute_cost(input_tokens, output_tokens)
    token_payload = json.dumps({
        "type": "citations",
        "citations": citations,
        "is_grounded": True,
        "token_usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            **costs,
        },
    })
    yield f"data: {token_payload}\n\n"
    yield "data: {\"type\": \"done\"}\n\n"
