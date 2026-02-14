from functools import lru_cache
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.models import Chunk, Document

settings = get_settings()


class SearchService:
    def __init__(self, top_k: int | None = None):
        self.top_k = top_k or settings.search_top_k

    async def vector_search(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        k = top_k or self.top_k

        # Use pgvector cosine distance operator
        query = (
            select(
                Chunk.id.label("chunk_id"),
                Chunk.document_id,
                Chunk.chunk_text,
                Chunk.chunk_index,
                Document.source_identifier,
                Document.source_type,
                Document.title,
                (1 - Chunk.embedding.cosine_distance(query_embedding)).label("vector_score"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.embedding.isnot(None))
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(k)
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "chunk_id": row.chunk_id,
                "document_id": row.document_id,
                "text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "source_identifier": row.source_identifier,
                "source_type": row.source_type,
                "title": row.title,
                "vector_score": float(row.vector_score),
            }
            for row in rows
        ]

    async def bm25_search(
        self,
        db: AsyncSession,
        query_text: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        k = top_k or self.top_k

        # Use PostgreSQL full-text search with ts_rank
        query = text("""
            SELECT
                c.id as chunk_id,
                c.document_id,
                c.chunk_text,
                c.chunk_index,
                d.source_identifier,
                d.source_type,
                d.title,
                ts_rank(to_tsvector('english', c.chunk_text), plainto_tsquery('english', :query)) as bm25_score
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE to_tsvector('english', c.chunk_text) @@ plainto_tsquery('english', :query)
            ORDER BY bm25_score DESC
            LIMIT :limit
        """)

        result = await db.execute(query, {"query": query_text, "limit": k})
        rows = result.all()

        return [
            {
                "chunk_id": row.chunk_id,
                "document_id": row.document_id,
                "text": row.chunk_text,
                "chunk_index": row.chunk_index,
                "source_identifier": row.source_identifier,
                "source_type": row.source_type,
                "title": row.title,
                "bm25_score": float(row.bm25_score),
            }
            for row in rows
        ]

    async def hybrid_search(
        self,
        db: AsyncSession,
        query_text: str,
        query_embedding: list[float],
        top_k: int | None = None,
        vector_weight: float = 0.5,
    ) -> list[dict[str, Any]]:
        k = top_k or self.top_k

        # Get results from both searches
        vector_results = await self.vector_search(db, query_embedding, k * 2)
        bm25_results = await self.bm25_search(db, query_text, k * 2)

        # Apply Reciprocal Rank Fusion (RRF)
        rrf_scores: dict[int, dict] = {}
        rrf_k = 60  # Standard RRF constant

        # Score vector results
        for rank, result in enumerate(vector_results):
            chunk_id = result["chunk_id"]
            rrf_score = vector_weight * (1 / (rrf_k + rank + 1))
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {**result, "rrf_score": 0.0}
            rrf_scores[chunk_id]["rrf_score"] += rrf_score

        # Score BM25 results
        bm25_weight = 1 - vector_weight
        for rank, result in enumerate(bm25_results):
            chunk_id = result["chunk_id"]
            rrf_score = bm25_weight * (1 / (rrf_k + rank + 1))
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {**result, "rrf_score": 0.0}
            rrf_scores[chunk_id]["rrf_score"] += rrf_score

        # Sort by RRF score and return top k
        sorted_results = sorted(
            rrf_scores.values(), key=lambda x: x["rrf_score"], reverse=True
        )[:k]

        return sorted_results


@lru_cache
def get_search_service() -> SearchService:
    return SearchService()
