from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aggregator.api.deps import get_db
from aggregator.models.source import Source, SourceType
from aggregator.scheduler.jobs import scheduler, ingest_source

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str
    source_type: SourceType
    url: str | None = None
    config: dict = {}
    poll_interval_minutes: int = 60
    is_trusted: bool = False


class SourceUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    config: dict | None = None
    poll_interval_minutes: int | None = None
    is_active: bool | None = None
    is_trusted: bool | None = None
    is_blocked: bool | None = None


class SourceOut(BaseModel):
    id: int
    name: str
    source_type: SourceType
    url: str | None
    is_active: bool
    is_trusted: bool
    is_blocked: bool
    poll_interval_minutes: int
    last_fetched_at: datetime | None
    fetch_error: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[SourceOut])
async def list_sources(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=201)
async def create_source(body: SourceCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    source = Source(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(source_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int, body: SourceUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    await db.commit()
    await db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    source = await db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/fetch", status_code=202)
async def trigger_fetch(source_id: int):
    """Manually trigger an immediate ingestion run for a source."""
    import asyncio
    asyncio.create_task(ingest_source(source_id))
    return {"status": "queued", "source_id": source_id}
