import json
import logging
from dataclasses import dataclass

import anthropic
from pydantic import BaseModel

from aggregator.config import settings
from aggregator.models.item import Item
from aggregator.models.score import Score
from aggregator.models.topic import Topic

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


class TopicScore(BaseModel):
    topic_id: int
    relevance_score: float
    summary: str
    is_high_quality: bool


class ScoringResponse(BaseModel):
    scores: list[TopicScore]


def _build_system_prompt(topics: list[Topic]) -> str:
    topic_lines = "\n".join(
        f"- id={t.id} name={t.name!r}: {t.description}" for t in topics
    )
    return f"""You are a content relevance analyst. You will receive a content item and a list of topics.

For each topic, assess:
1. relevance_score: float 0.0–1.0 (0 = not relevant, 1 = highly relevant)
2. summary: 2-sentence summary of why the item is or isn't relevant to the topic
3. is_high_quality: true if the item is original reporting, a primary source, or deep analysis

Topics:
{topic_lines}

Respond with valid JSON matching this schema:
{{"scores": [{{"topic_id": int, "relevance_score": float, "summary": str, "is_high_quality": bool}}]}}

Include one entry per topic, even if the score is 0."""


async def score_item(item: Item, topics: list[Topic]) -> list[Score]:
    """Score an item against all given topics in a single Claude API call."""
    if not topics:
        return []

    system_prompt = _build_system_prompt(topics)
    user_message = (
        f"Title: {item.title}\n"
        f"Source: {item.source.name if item.source else 'Unknown'}\n"
        f"Published: {item.published_at or 'Unknown'}\n\n"
        f"{item.body[:3000]}"
    )

    try:
        response = await client.messages.create(
            model=settings.scoring_model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as e:
        logger.error("Claude API error scoring item %d: %s", item.id, e)
        return []

    raw = response.content[0].text
    usage = response.usage

    try:
        data = ScoringResponse.model_validate(json.loads(raw))
    except Exception as e:
        logger.error("Failed to parse scoring response for item %d: %s\nRaw: %s", item.id, e, raw)
        return []

    scores: list[Score] = []
    topic_map = {t.id: t for t in topics}
    for ts in data.scores:
        if ts.topic_id not in topic_map:
            continue
        scores.append(
            Score(
                item_id=item.id,
                topic_id=ts.topic_id,
                relevance_score=max(0.0, min(1.0, ts.relevance_score)),
                summary=ts.summary,
                is_high_quality=ts.is_high_quality,
                claude_model=settings.scoring_model,
                prompt_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
        )
    return scores
