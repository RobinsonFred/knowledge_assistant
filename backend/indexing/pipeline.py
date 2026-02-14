from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.embeddings import get_embedding_service
from backend.core.mcp_client import get_filesystem_mcp_client
from backend.db.database import async_session_maker
from backend.db.models import Chunk, Document
from backend.indexing.chunker import get_chunker
from backend.indexing.processors import get_processor


class IndexingPipeline:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.chunker = get_chunker()

    async def index_filesystem(
        self,
        path: Path,
        patterns: list[str],
        recursive: bool = True,
        job_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mcp_client = get_filesystem_mcp_client(allowed_paths=[str(path)])

        try:
            await mcp_client.start()

            # Collect all files matching patterns
            all_files: list[dict] = []
            for pattern in patterns:
                result = await mcp_client.list_files(
                    path=str(path),
                    pattern=pattern,
                    recursive=recursive,
                )
                all_files.extend([f for f in result["files"] if f["is_file"]])

            total_files = len(all_files)
            indexed = 0
            errors: list[str] = []

            for i, file_info in enumerate(all_files):
                try:
                    file_path = file_info["path"]

                    # Read file content
                    file_data = await mcp_client.read_file(file_path)
                    content = file_data["content"]

                    # Get metadata
                    metadata = await mcp_client.get_file_metadata(file_path)

                    # Process and index
                    await self._index_document(
                        source_type="filesystem",
                        source_identifier=file_path,
                        title=file_info["name"],
                        content=content,
                        metadata=metadata,
                    )

                    indexed += 1

                    if job_status:
                        job_status["progress"] = (i + 1) / total_files
                        job_status["documents_indexed"] = indexed

                except Exception as e:
                    error_msg = f"Error indexing {file_info['path']}: {e}"
                    errors.append(error_msg)
                    if job_status:
                        job_status["errors"].append(error_msg)

            return {
                "total_files": total_files,
                "indexed": indexed,
                "errors": errors,
            }

        finally:
            await mcp_client.stop()

    async def _index_document(
        self,
        source_type: str,
        source_identifier: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        async with async_session_maker() as db:
            # Check if document already exists
            result = await db.execute(
                select(Document).where(Document.source_identifier == source_identifier)
            )
            existing_doc = result.scalar_one_or_none()

            if existing_doc:
                # Update existing document
                existing_doc.content = content
                existing_doc.title = title
                existing_doc.metadata_ = metadata

                # Delete old chunks
                await db.execute(
                    Chunk.__table__.delete().where(Chunk.document_id == existing_doc.id)
                )

                document = existing_doc
            else:
                # Create new document
                document = Document(
                    source_type=source_type,
                    source_identifier=source_identifier,
                    title=title,
                    content=content,
                    metadata_=metadata,
                )
                db.add(document)
                await db.flush()

            # Process content based on file type
            processor = get_processor(source_identifier)
            processed_content = processor.process(content)

            # Chunk the content
            chunk_results = self.chunker.chunk_text(
                processed_content,
                metadata={"source_identifier": source_identifier},
            )

            # Generate embeddings for all chunks
            chunk_texts = [c.text for c in chunk_results]
            embeddings = await self.embedding_service.embed_texts(chunk_texts)

            # Create chunk records
            for chunk_result, embedding in zip(chunk_results, embeddings):
                chunk = Chunk(
                    document_id=document.id,
                    chunk_text=chunk_result.text,
                    chunk_index=chunk_result.index,
                    embedding=embedding,
                    chunk_metadata=chunk_result.metadata,
                )
                db.add(chunk)

            await db.commit()
            return document

    async def index_single_document(
        self,
        source_type: str,
        source_identifier: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        return await self._index_document(
            source_type=source_type,
            source_identifier=source_identifier,
            title=title,
            content=content,
            metadata=metadata,
        )
