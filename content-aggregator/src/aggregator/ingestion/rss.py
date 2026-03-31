import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx
import trafilatura

from aggregator.ingestion.base import AbstractSourceAdapter, RawItem
from aggregator.utils.rate_limiter import RateLimiter

_rate_limiter = RateLimiter(calls_per_second=0.5)


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_body(entry, full_text: str | None) -> str:
    if full_text:
        return full_text
    for attr in ("summary", "content"):
        val = getattr(entry, attr, None)
        if val:
            if isinstance(val, list):
                return val[0].get("value", "")
            return str(val)
    return ""


class RSSAdapter(AbstractSourceAdapter):
    """Handles RSS and Atom feeds. Optionally fetches full-text via trafilatura."""

    async def fetch(self) -> list[RawItem]:
        url: str = self.config["url"]
        fetch_full_text: bool = self.config.get("fetch_full_text", False)

        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)

        items: list[RawItem] = []
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            for entry in feed.entries:
                entry_url = getattr(entry, "link", None)
                if not entry_url:
                    continue

                full_text: str | None = None
                if fetch_full_text and entry_url:
                    await _rate_limiter.acquire(entry_url)
                    try:
                        resp = await client.get(entry_url)
                        full_text = trafilatura.extract(resp.text) or None
                    except Exception:
                        pass

                items.append(
                    RawItem(
                        url=entry_url,
                        title=getattr(entry, "title", "Untitled"),
                        body=_extract_body(entry, full_text),
                        item_type="article",
                        external_id=getattr(entry, "id", None),
                        author=getattr(entry, "author", None),
                        published_at=_parse_date(entry),
                    )
                )
        return items


class PodcastAdapter(AbstractSourceAdapter):
    """Handles podcast RSS feeds (iTunes/Spotify extensions via feedparser)."""

    async def fetch(self) -> list[RawItem]:
        url: str = self.config["url"]
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, url)

        items: list[RawItem] = []
        for entry in feed.entries:
            enclosures = getattr(entry, "enclosures", [])
            audio_url = next(
                (e.get("url") for e in enclosures if "audio" in e.get("type", "")),
                getattr(entry, "link", None),
            )
            if not audio_url:
                continue

            duration = getattr(entry, "itunes_duration", None)
            items.append(
                RawItem(
                    url=audio_url,
                    title=getattr(entry, "title", "Untitled Episode"),
                    body=getattr(entry, "summary", ""),
                    item_type="podcast_episode",
                    external_id=getattr(entry, "id", None),
                    author=getattr(entry, "author", feed.feed.get("author")),
                    published_at=_parse_date(entry),
                    metadata={"duration": duration, "show": feed.feed.get("title")},
                )
            )
        return items
