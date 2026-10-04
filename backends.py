"""Language model backends and the backend factory.

All backends share one contract: take a ``ReasoningContext`` and return raw text. The
agent parses, validates and verifies that text identically regardless of where it came
from, so swapping providers changes one configuration value and nothing else.
"""
from __future__ import annotations

import json
import os
import urllib.request

from .base import Backend, ReasoningContext
from .chaos import ChaosBackend
from .offline import OfflineReasoner
from .prompts import SYSTEM_PROMPT, build_user_prompt


class AnthropicBackend:
    """Claude through the official ``anthropic`` Python SDK. Needs ANTHROPIC_API_KEY."""
    name = "anthropic"

    def __init__(self, cfg):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install the 'llm' extra to use the Anthropic backend") from exc
        self.client = anthropic.Anthropic()
        self.model = os.environ.get("ZONEMIND_ANTHROPIC_MODEL", cfg.llm.anthropic_model)
        self.max_tokens, self.temperature = cfg.llm.max_tokens, cfg.llm.temperature

    def propose(self, ctx: ReasoningContext) -> str:  # pragma: no cover - needs network
        message = self.client.messages.create(
            model=self.model, max_tokens=self.max_tokens, temperature=self.temperature,
            system=SYSTEM_PROMPT, messages=[{"role": "user", "content": build_user_prompt(ctx)}],
        )
        return "".join(block.text for block in message.content if block.type == "text")


class OpenAICompatibleBackend:
    """Any server that speaks the OpenAI chat completions protocol.

    Covers hosted OpenAI models and local servers such as Ollama, vLLM or LM Studio. Set
    ``llm.openai_base_url`` and ``llm.openai_model`` in the config; the key is read from
    OPENAI_API_KEY and may be empty for local servers.
    """
    name = "openai_compatible"

    def __init__(self, cfg):
        self.url = os.environ.get("ZONEMIND_OPENAI_BASE_URL", cfg.llm.openai_base_url).rstrip("/") + "/chat/completions"
        self.model = os.environ.get("ZONEMIND_OPENAI_MODEL", cfg.llm.openai_model)
        self.key = os.environ.get("OPENAI_API_KEY", "")
        self.max_tokens, self.temperature = cfg.llm.max_tokens, cfg.llm.temperature

    def propose(self, ctx: ReasoningContext) -> str:  # pragma: no cover - needs network
        payload = {
            "model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": build_user_prompt(ctx)}],
        }
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
        return body["choices"][0]["message"]["content"]


def make_backend(cfg, seed: int = 0) -> Backend:
    kind = cfg.llm.backend
    if kind == "offline":
        return OfflineReasoner()
    if kind == "chaos":
        return ChaosBackend(OfflineReasoner(), cfg.llm.chaos_fault_rate, seed)
    if kind == "anthropic":
        return AnthropicBackend(cfg)
    if kind == "openai_compatible":
        return OpenAICompatibleBackend(cfg)
    raise ValueError(f"unknown llm backend '{kind}'")
