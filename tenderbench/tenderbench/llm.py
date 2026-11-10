"""LLM client for the LLM steps (requirement / safety extraction, answering questions).

Claude is the default. With an Anthropic credential in the environment (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN
or an `ant auth login` profile) and no other setting, the bench uses Claude Opus 5.5 on the Claude API.

Settings (all optional):
  TB_LLM_PROVIDER   anthropic (default when a credential exists) | bedrock | openai
  TB_LLM_MODEL      default claude-opus-5-5 (Bedrock: anthropic.claude-opus-5-5)
  TB_LLM_EFFORT     low | medium | high | xhigh | max (default medium, Opus 5.5's own default, set explicitly)
  TB_LLM_REGION     bedrock region; ap-southeast-2 (Sydney) keeps inference onshore
  TB_LLM_BASE_URL   openai: an OpenAI-compatible server for self-hosted non-Claude models
  TB_LLM_PROVIDER=session   no API: tasks are written to data/session_llm/tasks.jsonl, answered inside a
                    Claude Code session (on a Claude subscription), and read back from responses.jsonl on the
                    next run. Two passes: run once to queue tasks, answer them, run again to score.

The Claude API path opts into server-side refusal fallback ("default" routing) so a safety-classifier decline is
re-run on a fallback model instead of failing the item. Token usage and estimated cost are tracked for the report.
If no provider is configured, `get_llm()` returns None and LLM steps are skipped, never simulated.
"""
from __future__ import annotations

import json
import os
import urllib.request

# USD per million tokens (input, output), Claude API list prices; used only for the cost line in reports.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


class LLMRefusal(RuntimeError):
    pass


class LLMPending(LLMRefusal):
    """Session provider: the task is queued for answering in a Claude Code session, not answered yet."""


class LLM:
    def __init__(self, provider: str, model: str, effort: str = "medium", region: str | None = None,
                 base_url: str | None = None):
        self.provider, self.model, self.effort, self.region, self.base_url = provider, model, effort, region, base_url
        self._client = None
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "refusals": 0}

    @property
    def residency(self) -> str:
        if self.provider == "session":
            return "offshore (Claude Code session)"
        if self.provider == "bedrock":
            return "cloud-au" if (self.region or "").startswith("ap-southeast") else "offshore"
        if self.provider == "openai":
            return "self-hosted"
        return "offshore"

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model} (effort {self.effort})"

    @property
    def cost_usd(self) -> float | None:
        p = PRICES.get(self.model.removeprefix("anthropic."))
        if not p:
            return None
        return (self.usage["input_tokens"] * p[0] + self.usage["output_tokens"] * p[1]) / 1e6

    # -------------------------------------------------------------- Claude

    def _claude(self, prompt: str, system: str, max_tokens: int, schema: dict | None) -> str:
        import anthropic
        if self._client is None:
            self._client = (anthropic.AnthropicBedrockMantle(aws_region=self.region) if self.provider == "bedrock"
                            else anthropic.Anthropic())
        output_config: dict = {"effort": self.effort}
        if schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs = dict(model=self.model, max_tokens=max_tokens, output_config=output_config,
                      messages=[{"role": "user", "content": prompt}])
        if system:
            kwargs["system"] = system
        if self.provider == "anthropic":
            # Server-side refusal fallback: not available on Bedrock, so only on the Claude API.
            resp = self._client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                                                     **kwargs)
        else:
            resp = self._client.messages.create(**kwargs)
        self.usage["calls"] += 1
        self.usage["input_tokens"] += resp.usage.input_tokens
        self.usage["output_tokens"] += resp.usage.output_tokens
        if resp.stop_reason == "refusal":
            self.usage["refusals"] += 1
            category = getattr(resp.stop_details, "category", None) if resp.stop_details else None
            raise LLMRefusal(f"declined (category {category})")
        return "".join(b.text for b in resp.content if b.type == "text")

    # -------------------------------------------------------------- self-hosted (non-Claude) models

    def _openai(self, prompt: str, system: str, max_tokens: int) -> str:
        body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens,
                "messages": ([{"role": "system", "content": system}] if system else []) +
                            [{"role": "user", "content": prompt}]}
        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {os.environ.get('TB_LLM_API_KEY', 'none')}"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        self.usage["calls"] += 1
        return data["choices"][0]["message"]["content"]

    # -------------------------------------------------------------- public

    # -------------------------------------------------------------- Claude Code session (subscription)

    def _session(self, prompt: str, system: str, schema: dict | None):
        import hashlib
        from .corpus import DATA
        d = DATA / "session_llm"
        d.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(json.dumps([system, prompt, schema], sort_keys=True).encode()).hexdigest()[:24]
        if not hasattr(self, "_answers"):
            self._answers = {}
            rp = d / "responses.jsonl"
            if rp.exists():
                for line in rp.read_text().splitlines():
                    if line.strip():
                        r = json.loads(line)
                        self._answers[r["key"]] = r["response"]
            self._queued = set()
            tp = d / "tasks.jsonl"
            if tp.exists():
                self._queued = {json.loads(l)["key"] for l in tp.read_text().splitlines() if l.strip()}
        if key in self._answers:
            self.usage["calls"] += 1
            return self._answers[key]
        if key not in self._queued:
            with (d / "tasks.jsonl").open("a") as f:
                f.write(json.dumps({"key": key, "system": system, "prompt": prompt, "schema": schema},
                                   ensure_ascii=False) + "\n")
            self._queued.add(key)
        self.usage["pending"] = self.usage.get("pending", 0) + 1
        raise LLMPending(key)

    def complete(self, prompt: str, system: str = "", max_tokens: int = 4000) -> str:
        if self.provider == "session":
            r = self._session(prompt, system, None)
            return r if isinstance(r, str) else json.dumps(r)
        if self.provider in ("anthropic", "bedrock"):
            return self._claude(prompt, system, max_tokens, None)
        return self._openai(prompt, system, max_tokens)

    def complete_json(self, prompt: str, schema: dict, system: str = "", max_tokens: int = 16000):
        """JSON matching `schema` (structured outputs on Claude, so the result always parses)."""
        if self.provider == "session":
            r = self._session(prompt, system, schema)
            return json.loads(r) if isinstance(r, str) else r
        if self.provider in ("anthropic", "bedrock"):
            return json.loads(self._claude(prompt, system, max_tokens, schema))
        text = self._openai(prompt + "\n\nReturn only JSON matching this schema:\n" + json.dumps(schema), system,
                            max_tokens)
        start = min([i for i in (text.find("["), text.find("{")) if i >= 0], default=0)
        return json.loads(text[start:text.rfind("}") + 1] if text[start:].startswith("{") else text[start:])


def _has_anthropic_credential() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.environ.get("ANTHROPIC_PROFILE")
                or os.path.isdir(os.path.expanduser("~/.config/anthropic")))


def get_llm() -> LLM | None:
    provider = os.environ.get("TB_LLM_PROVIDER") or ("anthropic" if _has_anthropic_credential() else None)
    if not provider:
        return None
    if provider == "session":
        return LLM("session", os.environ.get("TB_LLM_MODEL", "claude-code-session"), "session")
    default_model = "anthropic.claude-opus-5-5" if provider == "bedrock" else "claude-opus-5-5"
    model = os.environ.get("TB_LLM_MODEL") or (default_model if provider in ("anthropic", "bedrock") else None)
    if not model:
        return None
    return LLM(provider, model, os.environ.get("TB_LLM_EFFORT", "medium"), os.environ.get("TB_LLM_REGION"),
               os.environ.get("TB_LLM_BASE_URL"))
