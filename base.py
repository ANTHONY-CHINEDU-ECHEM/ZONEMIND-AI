"""Common interface for reasoning backends."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..control.situation import Situation
from ..knowledge.loader import KnowledgeBase
from ..knowledge.retriever import Hit


@dataclass
class ReasoningContext:
    situation: Situation
    hits: list[Hit]
    kb: KnowledgeBase
    knobs: dict
    knob_vars: dict
    safe_default: dict
    episodes: list[dict] = field(default_factory=list)


class Backend(Protocol):
    name: str

    def propose(self, ctx: ReasoningContext) -> str:
        """Return raw text that should contain one JSON proposal."""
