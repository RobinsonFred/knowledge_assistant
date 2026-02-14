# Sample Document

This is a sample markdown document for testing the Knowledge Assistant.

## Introduction

The Knowledge Assistant is a RAG (Retrieval Augmented Generation) system that helps users query their personal knowledge base.

## Features

- **Semantic Search**: Uses vector embeddings for similarity search
- **Hybrid Search**: Combines vector search with BM25 for better results
- **Citation Support**: All responses include source citations
- **MCP Integration**: Uses Model Context Protocol for file access

## How It Works

1. Documents are indexed and split into chunks
2. Each chunk is embedded using a sentence transformer model
3. When a query is received, it's embedded and used for similarity search
4. Top results are reranked using a cross-encoder
5. The LLM generates a response with citations

## Conclusion

This system provides an efficient way to query and retrieve information from your personal knowledge base.
