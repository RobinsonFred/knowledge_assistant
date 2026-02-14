import re
from dataclasses import dataclass


@dataclass
class ChunkResult:
    text: str
    index: int
    metadata: dict


class SemanticChunker:
    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
        overlap: int = 100,
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[ChunkResult]:
        if not text.strip():
            return []

        base_metadata = metadata or {}
        chunks: list[ChunkResult] = []

        # Split by semantic boundaries (headers, paragraphs, etc.)
        sections = self._split_by_semantic_boundaries(text)

        current_chunk = ""
        chunk_index = 0

        for section in sections:
            if len(current_chunk) + len(section) <= self.max_chunk_size:
                current_chunk += section
            else:
                # Save current chunk if it meets minimum size
                if len(current_chunk) >= self.min_chunk_size:
                    chunks.append(
                        ChunkResult(
                            text=current_chunk.strip(),
                            index=chunk_index,
                            metadata={**base_metadata, "char_start": 0, "char_end": len(current_chunk)},
                        )
                    )
                    chunk_index += 1

                # Start new chunk with overlap
                if self.overlap > 0 and current_chunk:
                    overlap_text = current_chunk[-self.overlap :]
                    current_chunk = overlap_text + section
                else:
                    current_chunk = section

        # Don't forget the last chunk
        if current_chunk.strip() and len(current_chunk) >= self.min_chunk_size:
            chunks.append(
                ChunkResult(
                    text=current_chunk.strip(),
                    index=chunk_index,
                    metadata={**base_metadata},
                )
            )

        return chunks

    def _split_by_semantic_boundaries(self, text: str) -> list[str]:
        # Split by markdown headers, double newlines, or code blocks
        patterns = [
            r"(^#{1,6}\s+.+$)",  # Markdown headers
            r"(```[\s\S]*?```)",  # Code blocks
            r"(\n\n+)",  # Double newlines
        ]

        combined_pattern = "|".join(patterns)
        parts = re.split(combined_pattern, text, flags=re.MULTILINE)

        # Filter out None and empty strings
        sections = [p for p in parts if p and p.strip()]

        # If no semantic splits found, fall back to sentence splitting
        if len(sections) <= 1:
            sections = self._split_by_sentences(text)

        return sections

    def _split_by_sentences(self, text: str) -> list[str]:
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s for s in sentences if s.strip()]


def get_chunker(
    max_chunk_size: int = 1000,
    min_chunk_size: int = 100,
    overlap: int = 100,
) -> SemanticChunker:
    return SemanticChunker(
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
        overlap=overlap,
    )
