import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aggregator.config import settings
from aggregator.database import AsyncSessionLocal
from aggregator.ingestion.base import RawItem
from aggregator.ingestion.rss import PodcastAdapter, RSSAdapter
from aggregator.models.item import CurationStatus, Item, ItemType
from aggregator.models.score import Score
from aggregator.models.source import Source, SourceType
from aggregator.models.topic import Topic
from aggregator.pipeline.deduplicator import content_hash, is_duplicate, normalise_url
from aggregator.pipeline.scorer import score_item

logger = logging.getLogger(__name__)

_ADAPTER_MAP = {
    SourceType.rss: RSSAdapter,
    SourceType.website: RSSAdapter,
    SourceType.podcast: PodcastAdapter,
}


async def ingest_source(source_id: int) -> None:
    async with AsyncSessionLocal() as session:
        source = await session.get(Source, source_id)
        if not source or not source.is_active or source.is_blocked:
            return

        adapter_cls = _ADAPTER_MAP.get(source.source_type)
        if not adapter_cls:
            logger.warning("No adapter for source type %s", source.source_type)
            return

        try:
            settings.validate_for_source_types({source.source_type.value})
            adapter = adapter_cls({"url": source.url, **source.config})
            raw_items: list[RawItem] = await adapter.fetch()
        except Exception as e:
            source.fetch_error = str(e)
            source.last_fetched_at = datetime.now(timezone.utc)
            await session.commit()
            logger.error("Error fetching source %d: %s", source_id, e)
            return

        source.fetch_error = None
        source.last_fetched_at = datetime.now(timezone.utc)

        topics_result = await session.execute(select(Topic).where(Topic.is_active == True))
        topics = list(topics_result.scalars().all())

        new_items: list[Item] = []
        for raw in raw_items:
            canonical = normalise_url(raw.url)
            hash_ = content_hash(raw.title, raw.body)

            if await is_duplicate(session, canonical, hash_):
                continue

            item = Item(
                source_id=source_id,
                external_id=raw.external_id,
                url=raw.url,
                canonical_url=canonical,
                content_hash=hash_,
                title=raw.title,
                body=raw.body,
                author=raw.author,
                published_at=raw.published_at,
                item_type=ItemType(raw.item_type),
                metadata_=raw.metadata,
                curation_status=CurationStatus.pending,
            )
            session.add(item)
            new_items.append(item)

        await session.flush()

        for item in new_items:
            scores = await score_item(item, topics)
            for score in scores:
                session.add(score)

        await session.commit()
        logger.info("Ingested %d new items from source %d", len(new_items), source_id)
