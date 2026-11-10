import hashlib
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aggregator.models.item import Item

# UTM and tracking params to strip from URLs
_STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
}


def normalise_url(url: str) -> str:
    parsed = urlparse(url.strip().lower())
    filtered = {k: v for k, v in parse_qs(parsed.query).items() if k not in _STRIP_PARAMS}
    clean_query = urlencode(filtered, doseq=True)
    return urlunparse(parsed._replace(query=clean_query, fragment=""))


def content_hash(title: str, body: str) -> str:
    text = f"{title.strip().lower()}{body[:500].strip().lower()}"
    return hashlib.sha256(text.encode()).hexdigest()


async def is_duplicate(session: AsyncSession, canonical_url: str, hash_: str) -> bool:
    result = await session.execute(
        select(Item.id).where(
            (Item.canonical_url == canonical_url) | (Item.content_hash == hash_)
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None
