import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from aggregator.database import AsyncSessionLocal
from aggregator.models.source import Source
from aggregator.pipeline.runner import ingest_source

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _refresh_source_jobs() -> None:
    """Sync APScheduler jobs with active sources in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Source).where(Source.is_active == True))
        sources = list(result.scalars().all())

    existing_ids = {
        job.id for job in scheduler.get_jobs() if job.id.startswith("source_")
    }
    active_ids = {f"source_{s.id}" for s in sources}

    # Remove jobs for deleted/deactivated sources
    for job_id in existing_ids - active_ids:
        scheduler.remove_job(job_id)
        logger.info("Removed scheduler job %s", job_id)

    # Add or reschedule jobs for active sources
    for source in sources:
        job_id = f"source_{source.id}"
        trigger = IntervalTrigger(minutes=source.poll_interval_minutes)
        if job_id in existing_ids:
            scheduler.reschedule_job(job_id, trigger=trigger)
        else:
            scheduler.add_job(
                ingest_source,
                trigger=trigger,
                id=job_id,
                args=[source.id],
                replace_existing=True,
                misfire_grace_time=300,
            )
            logger.info("Scheduled source %d every %dm", source.id, source.poll_interval_minutes)


async def start_scheduler() -> None:
    # Refresh job list every 10 minutes to pick up new/changed sources
    scheduler.add_job(
        _refresh_source_jobs,
        trigger=IntervalTrigger(minutes=10),
        id="refresh_jobs",
        replace_existing=True,
    )
    await _refresh_source_jobs()
    scheduler.start()
    logger.info("Scheduler started")


async def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
