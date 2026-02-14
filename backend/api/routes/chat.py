from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    include_sources: bool = True


class SourceInfo(BaseModel):
    document_id: int
    chunk_id: int
    source_identifier: str
    relevance_score: float
    text_snippet: str


class ChatResponse(BaseModel):
    response: str
    sources: list[SourceInfo]
    query_id: int


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    # Import here to avoid circular imports
    from backend.core.embeddings import get_embedding_service
    from backend.core.llm import get_llm_service
    from backend.core.reranker import get_reranker_service
    from backend.core.search import get_search_service

    embedding_service = get_embedding_service()
    search_service = get_search_service()
    reranker_service = get_reranker_service()
    llm_service = get_llm_service()

    # Embed the query
    query_embedding = await embedding_service.embed_text(request.query)

    # Hybrid search
    search_results = await search_service.hybrid_search(
        db=db,
        query_text=request.query,
        query_embedding=query_embedding,
        top_k=request.top_k * 4,  # Get more for reranking
    )

    if not search_results:
        raise HTTPException(status_code=404, detail="No relevant documents found")

    # Rerank
    reranked = await reranker_service.rerank(
        query=request.query,
        chunks=search_results,
        top_k=request.top_k,
    )

    # Build context and generate response
    response_text, sources = await llm_service.generate_response(
        query=request.query,
        context_chunks=reranked,
    )

    # Store query for debugging
    from backend.db.models import Query

    query_record = Query(
        query_text=request.query,
        query_embedding=query_embedding,
        retrieved_chunk_ids=[str(c["chunk_id"]) for c in reranked],
        response=response_text,
    )
    db.add(query_record)
    await db.flush()

    source_infos = [
        SourceInfo(
            document_id=s["document_id"],
            chunk_id=s["chunk_id"],
            source_identifier=s["source_identifier"],
            relevance_score=s["score"],
            text_snippet=s["text"][:200] + "..." if len(s["text"]) > 200 else s["text"],
        )
        for s in sources
    ]

    return ChatResponse(
        response=response_text,
        sources=source_infos,
        query_id=query_record.id,
    )
