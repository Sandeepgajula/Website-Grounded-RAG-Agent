"""RAG router — query the knowledge base and get grounded answers."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.models.schemas import RagRequest, RagResponse, Citation
from backend.config import RAG_TOP_K
from backend.services.vector_store import collection_exists
from backend.services.rag_pipeline import run_rag, run_rag_stream

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("", summary="Ask a question against a website knowledge base")
async def rag_query(request: RagRequest):
    """
    RAG pipeline: retrieve → check → generate.

    - Retrieves relevant chunks from ChromaDB using semantic search
    - Routes to "not enough info" if context is insufficient
    - Generates a grounded answer with source citations
    - Tracks token usage and estimated cost

    Set `stream=true` for Server-Sent Events (SSE) streaming response.
    Set `stream=false` for a standard JSON response.

    **Streaming format** (SSE events):
    ```
    data: {"type": "chunk", "content": "...", "is_grounded": true}
    data: {"type": "citations", "citations": [...], "token_usage": {...}}
    data: {"type": "done"}
    ```
    """
    if not collection_exists(request.company_name):
        raise HTTPException(
            status_code=404,
            detail=(
                f"No knowledge base found for '{request.company_name}'. "
                "Please crawl and ingest the website first."
            ),
        )

    top_k = request.top_k or RAG_TOP_K
    history = [msg.model_dump() for msg in (request.history or [])]

    if request.stream:
        return StreamingResponse(
            run_rag_stream(
                query=request.query,
                company_name=request.company_name,
                history=history,
                top_k=top_k,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        result = run_rag(
            query=request.query,
            company_name=request.company_name,
            history=history,
            top_k=top_k,
        )
        return RagResponse(
            query=result["query"],
            answer=result["answer"],
            citations=[Citation(**c) for c in result["citations"]],
            is_grounded=result["is_grounded"],
            token_usage=result["token_usage"],
        )
