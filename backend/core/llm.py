from functools import lru_cache
from typing import Any

from anthropic import Anthropic

from backend.config import get_settings

settings = get_settings()


class LLMService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self._client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    async def generate_response(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2048,
    ) -> tuple[str, list[dict[str, Any]]]:
        # Build context from chunks
        context_parts = []
        sources = []

        for i, chunk in enumerate(context_chunks):
            source_id = chunk.get("source_identifier", "unknown")
            text = chunk.get("text", "")

            context_parts.append(f"[Source {i + 1}: {source_id}]\n{text}")

            sources.append({
                "index": i + 1,
                "document_id": chunk.get("document_id"),
                "chunk_id": chunk.get("chunk_id"),
                "source_identifier": source_id,
                "title": chunk.get("title"),
                "text": text,
                "score": chunk.get("rerank_score", chunk.get("rrf_score", 0)),
            })

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """You are a helpful knowledge assistant. Answer questions based on the provided context.

Rules:
1. Only use information from the provided sources
2. Cite sources using [Source N] notation when using information from them
3. If the context doesn't contain enough information to answer, say so
4. Be concise but thorough
5. If multiple sources agree, you can combine their information"""

        user_message = f"""Context:
{context}

Question: {query}

Please provide a well-cited answer based on the sources above."""

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        # Extract which sources were actually cited
        cited_sources = []
        for source in sources:
            if f"[Source {source['index']}]" in response_text:
                cited_sources.append(source)

        # If no explicit citations, include all sources
        if not cited_sources:
            cited_sources = sources

        return response_text, cited_sources


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
