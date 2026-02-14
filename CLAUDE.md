# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Knowledge Assistant is a RAG (Retrieval Augmented Generation) system with MCP (Model Context Protocol) integration for personal knowledge management.

## Architecture

- **Backend**: FastAPI with async SQLAlchemy
- **Database**: PostgreSQL with pgvector extension
- **Embedding**: sentence-transformers (bge-large-en-v1.5)
- **Reranking**: Cross-encoder model
- **LLM**: Anthropic Claude API
- **MCP Servers**: Filesystem access via JSON-RPC 2.0

## Development

### Setup
```bash
# Start PostgreSQL with pgvector
docker-compose up -d

# Install dependencies with uv
uv sync

# Run migrations
uv run alembic upgrade head

# Start the server
uv run uvicorn backend.main:app --reload
```

### Testing
```bash
uv run pytest
```

### Key Commands
- Index files: `POST /index/filesystem {"path": "./test_docs"}`
- Query: `POST /chat {"query": "What is RAG?"}`
- Check health: `GET /health`

## Project Structure

- `backend/` - FastAPI application
  - `api/routes/` - API endpoints (chat, documents, indexing)
  - `core/` - Core services (embeddings, search, reranker, LLM, MCP client)
  - `db/` - Database models and connection
  - `indexing/` - Document processing pipeline
- `mcp_servers/` - MCP server implementations
- `alembic/` - Database migrations
- `tests/` - Test suite

## Code Style

- Use `pathlib.Path` for all path handling (Windows compatibility)
- Async/await for all I/O operations
- Type hints required
- Follow existing patterns in the codebase
