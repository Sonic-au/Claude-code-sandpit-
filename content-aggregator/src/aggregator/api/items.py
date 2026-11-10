import csv
import io
import json
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from aggregator.api.deps import get_db
from aggregator.models.item import CurationStatus, Item

router = APIRouter(prefix="/api/v1/items", tags=["items"])


class ScoreSummary(BaseModel):
    topic_id: int
    topic_name: str
    relevance_score: float
    summary: str
    is_high_quality: bool

    model_config = {"from_attributes": True}


class ItemOut(BaseModel):
    id: int
    source_id: int
    url: str
    title: str
    author: str | None
    published_at: datetime | None
    item_type: str
    curation_status: CurationStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CurateRequest(BaseModel):
    status: CurationStatus
    approved_by: str | None = None


@router.get("/", response_model=list[ItemOut])
async def list_items(
    db: Annotated[AsyncSession, Depends(get_db)],
    topic_id: int | None = Query(None),
    status: CurationStatus | None = Query(None),
    min_score: float | None = Query(None, ge=0.0, le=1.0),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    query = select(Item).order_by(Item.created_at.desc()).limit(limit).offset(offset)

    if status:
        query = query.where(Item.curation_status == status)

    if topic_id or min_score is not None:
        from aggregator.models.score import Score
        query = query.join(Score, Score.item_id == Item.id)
        if topic_id:
            query = query.where(Score.topic_id == topic_id)
        if min_score is not None:
            query = query.where(Score.relevance_score >= min_score)

    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.patch("/{item_id}/curate", response_model=ItemOut)
async def curate_item(
    item_id: int, body: CurateRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.curation_status = body.status
    item.approved_by = body.approved_by
    item.curated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/export/json")
async def export_json(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: CurationStatus = Query(CurationStatus.approved),
):
    result = await db.execute(
        select(Item).where(Item.curation_status == status).order_by(Item.created_at.desc())
    )
    items = result.scalars().all()
    data = [
        {
            "id": i.id, "url": i.url, "title": i.title,
            "author": i.author, "published_at": str(i.published_at),
            "item_type": i.item_type, "curation_status": i.curation_status,
        }
        for i in items
    ]
    return StreamingResponse(
        io.StringIO(json.dumps(data, indent=2)),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=items.json"},
    )


@router.get("/export/csv")
async def export_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: CurationStatus = Query(CurationStatus.approved),
):
    result = await db.execute(
        select(Item).where(Item.curation_status == status).order_by(Item.created_at.desc())
    )
    items = result.scalars().all()

    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["id", "url", "title", "author", "published_at", "item_type"]
    )
    writer.writeheader()
    for i in items:
        writer.writerow({
            "id": i.id, "url": i.url, "title": i.title,
            "author": i.author, "published_at": i.published_at, "item_type": i.item_type,
        })

    return StreamingResponse(
        io.StringIO(output.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=items.csv"},
    )
