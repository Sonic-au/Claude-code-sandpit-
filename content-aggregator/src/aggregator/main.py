import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from aggregator.api import items as items_router
from aggregator.api import sources as sources_router
from aggregator.api import topics as topics_router
from aggregator.database import AsyncSessionLocal, init_db
from aggregator.models.item import CurationStatus, Item
from aggregator.models.score import Score
from aggregator.models.source import Source
from aggregator.models.topic import Topic
from aggregator.pipeline.runner import ingest_source
from aggregator.scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "ui" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(title="Content Aggregator", lifespan=lifespan)

app.include_router(sources_router.router)
app.include_router(topics_router.router)
app.include_router(items_router.router)


# ── UI routes ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    topic_id: int | None = None,
    status: str | None = None,
    min_score: float | None = None,
):
    async with AsyncSessionLocal() as db:
        topics_result = await db.execute(select(Topic).order_by(Topic.name))
        topics = topics_result.scalars().all()

        query = (
            select(Item)
            .options(selectinload(Item.scores).selectinload(Score.topic), selectinload(Item.source))
            .order_by(Item.created_at.desc())
            .limit(100)
        )
        if status:
            query = query.where(Item.curation_status == CurationStatus(status))
        if topic_id or min_score is not None:
            query = query.join(Score, Score.item_id == Item.id)
            if topic_id:
                query = query.where(Score.topic_id == topic_id)
            if min_score is not None:
                query = query.where(Score.relevance_score >= min_score)

        items_result = await db.execute(query)
        raw_items = items_result.scalars().unique().all()

    # Flatten for template rendering
    display_items = []
    for item in raw_items:
        display_items.append({
            "id": item.id,
            "url": item.url,
            "title": item.title,
            "author": item.author,
            "published_at": item.published_at,
            "item_type": item.item_type.value,
            "curation_status": item.curation_status.value,
            "source_name": item.source.name if item.source else "Unknown",
            "scores": [
                {
                    "topic_name": s.topic.name if s.topic else "",
                    "relevance_score": s.relevance_score,
                    "summary": s.summary,
                    "is_high_quality": s.is_high_quality,
                }
                for s in item.scores
                if not topic_id or s.topic_id == topic_id
            ],
        })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "items": display_items,
        "topics": topics,
        "selected_topic": topic_id,
        "selected_status": status,
        "min_score": min_score,
    })


@app.post("/items/{item_id}/curate")
async def curate_item_ui(item_id: int, status: str = Form(...)):
    async with AsyncSessionLocal() as db:
        item = await db.get(Item, item_id)
        if item:
            item.curation_status = CurationStatus(status)
            item.curated_at = datetime.utcnow()
            await db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Source).order_by(Source.name))
        sources = result.scalars().all()
    return templates.TemplateResponse("sources.html", {"request": request, "sources": sources})


@app.post("/sources")
async def create_source_ui(
    name: str = Form(...),
    source_type: str = Form(...),
    url: str = Form(""),
    poll_interval_minutes: int = Form(60),
):
    async with AsyncSessionLocal() as db:
        source = Source(
            name=name, source_type=source_type,
            url=url or None, poll_interval_minutes=poll_interval_minutes,
        )
        db.add(source)
        await db.commit()
    return RedirectResponse("/sources", status_code=303)


@app.post("/sources/{source_id}/fetch")
async def fetch_source_ui(source_id: int):
    asyncio.create_task(ingest_source(source_id))
    return RedirectResponse("/sources", status_code=303)


@app.post("/sources/{source_id}/toggle")
async def toggle_source_ui(source_id: int):
    async with AsyncSessionLocal() as db:
        source = await db.get(Source, source_id)
        if source:
            source.is_active = not source.is_active
            await db.commit()
    return RedirectResponse("/sources", status_code=303)


@app.post("/sources/{source_id}/delete")
async def delete_source_ui(source_id: int):
    async with AsyncSessionLocal() as db:
        source = await db.get(Source, source_id)
        if source:
            await db.delete(source)
            await db.commit()
    return RedirectResponse("/sources", status_code=303)


@app.get("/topics", response_class=HTMLResponse)
async def topics_page(request: Request):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Topic).order_by(Topic.name))
        topics = result.scalars().all()
    return templates.TemplateResponse("topics.html", {"request": request, "topics": topics})


@app.post("/topics")
async def create_topic_ui(
    name: str = Form(...),
    description: str = Form(...),
    keywords: str = Form(""),
    score_threshold: float = Form(0.5),
):
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    async with AsyncSessionLocal() as db:
        topic = Topic(
            name=name, description=description,
            keywords=kw_list, score_threshold=score_threshold,
        )
        db.add(topic)
        await db.commit()
    return RedirectResponse("/topics", status_code=303)


@app.post("/topics/{topic_id}/toggle")
async def toggle_topic_ui(topic_id: int):
    async with AsyncSessionLocal() as db:
        topic = await db.get(Topic, topic_id)
        if topic:
            topic.is_active = not topic.is_active
            await db.commit()
    return RedirectResponse("/topics", status_code=303)


@app.post("/topics/{topic_id}/delete")
async def delete_topic_ui(topic_id: int):
    async with AsyncSessionLocal() as db:
        topic = await db.get(Topic, topic_id)
        if topic:
            await db.delete(topic)
            await db.commit()
    return RedirectResponse("/topics", status_code=303)
