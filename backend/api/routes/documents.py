from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import Document

router = APIRouter()


class DocumentInfo(BaseModel):
    id: int
    source_type: str
    source_identifier: str
    title: str | None
    chunk_count: int
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    source_type: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    query = select(Document)
    if source_type:
        query = query.where(Document.source_type == source_type)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    documents = result.scalars().all()

    doc_infos = [
        DocumentInfo(
            id=doc.id,
            source_type=doc.source_type,
            source_identifier=doc.source_identifier,
            title=doc.title,
            chunk_count=len(doc.chunks) if doc.chunks else 0,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
        for doc in documents
    ]

    return DocumentListResponse(documents=doc_infos, total=len(doc_infos))


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "source_type": document.source_type,
        "source_identifier": document.source_identifier,
        "title": document.title,
        "content": document.content,
        "metadata": document.metadata_,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(document)
    return {"status": "deleted", "document_id": document_id}
