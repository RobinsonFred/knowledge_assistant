from functools import lru_cache
from typing import Any

from sentence_transformers import CrossEncoder

from backend.config import get_settings

settings = get_settings()


class RerankerService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.reranker_model
        self._model: CrossEncoder | None = None

    @property
    def model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model

    async def rerank(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        if not chunks:
            return []

        k = top_k or settings.rerank_top_k

        # Prepare query-document pairs for cross-encoder
        pairs = [(query, chunk["text"]) for chunk in chunks]

        # Get scores from cross-encoder
        scores = self.model.predict(pairs)

        # Add rerank scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        # Sort by rerank score and return top k
        sorted_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        return sorted_chunks[:k]


@lru_cache
def get_reranker_service() -> RerankerService:
    return RerankerService()
