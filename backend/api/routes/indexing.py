from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db

router = APIRouter()

# Simple in-memory status tracking (would use Redis/DB in production)
_indexing_jobs: dict[str, dict] = {}


class FilesystemIndexRequest(BaseModel):
    path: str
    patterns: list[str] = ["*.md", "*.txt", "*.py"]
    recursive: bool = True


class IndexStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    documents_indexed: int
    errors: list[str]


@router.post("/filesystem")
async def index_filesystem(
    request: FilesystemIndexRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from backend.indexing.pipeline import IndexingPipeline

    path = Path(request.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {request.path}")

    # Generate job ID
    import uuid

    job_id = str(uuid.uuid4())

    _indexing_jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "documents_indexed": 0,
        "errors": [],
    }

    # Run indexing in background
    async def run_indexing() -> None:
        pipeline = IndexingPipeline()
        try:
            _indexing_jobs[job_id]["status"] = "running"
            await pipeline.index_filesystem(
                path=path,
                patterns=request.patterns,
                recursive=request.recursive,
                job_status=_indexing_jobs[job_id],
            )
            _indexing_jobs[job_id]["status"] = "completed"
            _indexing_jobs[job_id]["progress"] = 1.0
        except Exception as e:
            _indexing_jobs[job_id]["status"] = "failed"
            _indexing_jobs[job_id]["errors"].append(str(e))

    background_tasks.add_task(run_indexing)

    return {"job_id": job_id, "status": "pending"}


@router.get("/status/{job_id}", response_model=IndexStatusResponse)
async def get_indexing_status(job_id: str) -> IndexStatusResponse:
    if job_id not in _indexing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _indexing_jobs[job_id]
    return IndexStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        documents_indexed=job["documents_indexed"],
        errors=job["errors"],
    )
