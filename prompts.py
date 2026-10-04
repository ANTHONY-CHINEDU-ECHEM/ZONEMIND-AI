"""Prompt construction for language model backends."""
from __future__ import annotations

import json

from ..variables import SITUATION_VARIABLES
from .base import ReasoningContext

SYSTEM_PROMPT = """You are ZoneMind, the supervisory setpoint controller for a multi zone office building.
Each hour you choose a heating setpoint and a cooling setpoint (in degrees C) for every zone.

Rules you must follow:
1. Ground every decision in the retrieved operating documents. Do not invent strategies that the documents
   do not describe. If no document covers a zone's situation, use the safe default setpoints.
2. Documents are applied in order of their stated priority; a more specific sequence refines a general one.
3. Use the strategy knobs exactly as given (recovery lead time, pre conditioning depth, shed depth, set back
   values). They were selected from the outcomes of similar past days.
4. Never trade occupant comfort limits for savings. A separate verifier enforces hard limits and will
   repair any command that breaks one, so a non compliant answer gains nothing.
5. Cite the id of every document you relied on. Only cite documents that appear in the retrieved set.

Respond with one JSON object and nothing else, in exactly this shape:
{"zones": {"<zone name>": {"heat": <number>, "cool": <number>, "lockout": <true|false>}, ...},
 "strategy": "<short label>", "rationale": "<one or two sentences>", "citations": ["<doc id>", ...]}
"lockout" disables mechanical cooling so only outdoor air is used; set it only where a document says so."""


def build_user_prompt(ctx: ReasoningContext) -> str:
    view = ctx.situation.to_prompt()
    glossary = {k: SITUATION_VARIABLES[k] for k in sorted(set(view["building"]) | {"h_to_occ", "h_to_vacant", "noshow_h"})
                if k in SITUATION_VARIABLES}
    docs = []
    for h in ctx.hits:
        doc = ctx.kb.docs[h.doc_id]
        docs.append(f"[{doc.id}] {doc.title} (category: {doc.category})\n{doc.body}")
    parts = [
        "## Situation", json.dumps(view, indent=1),
        "## Meaning of the situation fields", json.dumps(glossary, indent=1),
        "## Strategy knobs for today", json.dumps({"selected": ctx.knobs, "values": ctx.knob_vars}, indent=1),
        "## Safe default setpoints", json.dumps(dict(ctx.safe_default)),
        "## Outcomes of similar past days", json.dumps(ctx.episodes, indent=1) if ctx.episodes else "No history yet.",
        "## Retrieved operating documents", "\n\n".join(docs) if docs else "None retrieved.",
        "## Task", "Give the setpoints for every zone for the next hour as the JSON object described.",
    ]
    return "\n".join(parts)
