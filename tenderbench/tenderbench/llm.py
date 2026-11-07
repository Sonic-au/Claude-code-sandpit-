"""Minimal LLM client used by the LLM extractor, contextual chunking and answer judging.

Providers (pick with TB_LLM_PROVIDER):
  bedrock    Claude on Amazon Bedrock. Onshore with TB_LLM_REGION=ap-southeast-2 (Sydney).
             Needs `pip install 'anthropic[bedrock]'` and AWS credentials. TB_LLM_MODEL = model id
             or inference profile available in that region.
  anthropic  Anthropic API (offshore). ANTHROPIC_API_KEY, TB_LLM_MODEL.
  openai     Any OpenAI-compatible endpoint, e.g. a local vLLM/Ollama server keeping data on your
             hardware. TB_LLM_BASE_URL, TB_LLM_MODEL, optional TB_LLM_API_KEY.
If nothing is configured, `get_llm()` returns None and the LLM-dependent steps are skipped
(the report says so) - they are never faked.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request


class LLM:
    def __init__(self, provider: str, model: str, region: str | None = None, base_url: str | None = None):
        self.provider, self.model, self.region, self.base_url = provider, model, region, base_url
        self._client = None

    @property
    def residency(self) -> str:
        if self.provider == "bedrock":
            return "cloud-au" if (self.region or "").startswith("ap-southeast") else "offshore"
        if self.provider == "openai":
            return "self-hosted"
        return "offshore"

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"

    def complete(self, prompt: str, system: str = "", max_tokens: int = 4000) -> str:
        if self.provider in ("anthropic", "bedrock"):
            import anthropic
            if self._client is None:
                self._client = (anthropic.AnthropicBedrock(aws_region=self.region) if self.provider == "bedrock"
                                else anthropic.Anthropic())
            msg = self._client.messages.create(
                model=self.model, max_tokens=max_tokens, temperature=0,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}])
            return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens,
                "messages": ([{"role": "system", "content": system}] if system else []) +
                            [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {os.environ.get('TB_LLM_API_KEY', 'none')}"})
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]

    def complete_json(self, prompt: str, system: str = "", max_tokens: int = 4000):
        text = self.complete(prompt, system, max_tokens)
        m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
        raw = m.group(1) if m else text
        start = min([i for i in (raw.find("["), raw.find("{")) if i >= 0], default=0)
        return json.loads(raw[start:])


def get_llm() -> LLM | None:
    provider = os.environ.get("TB_LLM_PROVIDER")
    model = os.environ.get("TB_LLM_MODEL")
    if not provider or not model:
        return None
    return LLM(provider, model, os.environ.get("TB_LLM_REGION"), os.environ.get("TB_LLM_BASE_URL"))
