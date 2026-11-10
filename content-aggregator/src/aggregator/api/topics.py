from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aggregator.api.deps import get_db
from aggregator.models.topic import Topic

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


class TopicCreate(BaseModel):
    name: str
    description: str
    keywords: list[str] = []
    score_threshold: float = 0.5


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    score_threshold: float | None = None
    is_active: bool | None = None


class TopicOut(BaseModel):
    id: int
    name: str
    description: str
    keywords: list[str]
    score_threshold: float
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[TopicOut])
async def list_topics(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Topic).order_by(Topic.name))
    return result.scalars().all()


@router.post("/", response_model=TopicOut, status_code=201)
async def create_topic(body: TopicCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    topic = Topic(**body.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


@router.get("/{topic_id}", response_model=TopicOut)
async def get_topic(topic_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    return topic


@router.patch("/{topic_id}", response_model=TopicOut)
async def update_topic(
    topic_id: int, body: TopicUpdate, db: Annotated[AsyncSession, Depends(get_db)]
):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(topic, field, value)
    await db.commit()
    await db.refresh(topic)
    return topic


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(topic_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    await db.delete(topic)
    await db.commit()
