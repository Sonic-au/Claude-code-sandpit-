"""Claude-powered domain name generator for AI startups."""

import json
import logging

import anthropic
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    anthropic_api_key: str
    model: str = "claude-sonnet-4-6"


settings = Settings()
client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are an expert in startup naming, linguistics, and domain strategy.

Your task is to generate memorable, verb-friendly domain name candidates for an AI startup.

## Naming criteria
- Maximum 8 characters (shorter is better)
- Works naturally as a verb: "just [name] it", "I'll [name] this"
- Globally pronounceable — no sounds that are unpronounceable in major languages
- Evokes the startup's value: collective intelligence, knowledge distillation, briefings, wisdom
- No negative connotations in major world languages (check mentally)
- .ai domain friendly — short, punchy, tech-credible

## Multilingual inspiration palette
Draw from (but don't limit to) these concepts and words:
- Norse: mimir (well of wisdom), runa (secret knowledge), fundr (gathering/discovery)
- Sanskrit: akash (cosmic knowledge ether), vidya (knowledge/learning), prajna (transcendental wisdom)
- Arabic: hikmah (wisdom + action combined), ilm (knowledge)
- Swahili: busara (community wisdom through discourse), baraza (gathering for collective intelligence), hekima (discernment wisdom)
- Greek: gnosis (direct transformative knowledge), sophia (divine wisdom), phron (practical wisdom)
- Japanese: soku (quick/rapid), chi (wisdom/knowledge), satoru (to understand/enlighten)
- Latin: consilium (collective deliberation), nexum (connection/bond)
- Hebrew: daat (deep knowledge), chokma (skill + wisdom)
- Māori: matau (to know/understand), hiringa (insight, initiative)
- Welsh: gwybod (to know), dysg (learning)

## Output format
Return a JSON array of exactly 25 candidates, sorted by your confidence score (highest first):
[
  {
    "name": "mimir",
    "origin": "Norse mythology",
    "reasoning": "Keeper of the well of wisdom; Odin sacrificed his eye for its waters",
    "verb": "just mimir it",
    "score": 9
  },
  ...
]

score: 1-10, where 10 = perfect fit, short, great verb, available-sounding
Return ONLY the JSON array, no other text."""


async def generate_names(description: str, seeds: str = "") -> list[dict]:
    """Generate domain name candidates using Claude."""
    seed_note = f"\n\nSeed names the founder likes: {seeds}" if seeds.strip() else ""
    user_message = f"Startup description: {description}{seed_note}"

    try:
        response = await client.messages.create(
            model=settings.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        candidates = json.loads(raw)
        return sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
    except Exception as e:
        logger.error("Name generation failed: %s", e)
        return []
