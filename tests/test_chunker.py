import pytest

from backend.indexing.chunker import SemanticChunker


def test_chunker_basic():
    chunker = SemanticChunker(max_chunk_size=100, min_chunk_size=10, overlap=20)

    text = "This is a test paragraph. " * 20
    chunks = chunker.chunk_text(text)

    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk.text) >= 10
        assert chunk.index >= 0


def test_chunker_markdown_headers():
    chunker = SemanticChunker(max_chunk_size=500, min_chunk_size=10, overlap=0)

    text = """# Header 1

Some content under header 1.

## Header 2

Content under header 2.

### Header 3

Content under header 3."""

    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 1


def test_chunker_empty_text():
    chunker = SemanticChunker()
    chunks = chunker.chunk_text("")
    assert chunks == []


def test_chunker_preserves_metadata():
    chunker = SemanticChunker(max_chunk_size=100, min_chunk_size=10)
    text = "Test content. " * 20

    metadata = {"source": "test.md", "author": "test"}
    chunks = chunker.chunk_text(text, metadata=metadata)

    assert len(chunks) > 0
    for chunk in chunks:
        assert "source" in chunk.metadata
        assert chunk.metadata["source"] == "test.md"
