"""Deterministic grounded reasoner.

This backend needs no network and no API key. It reads the machine readable directives
carried by the retrieved documents, evaluates each guard against the current situation
and applies the matching instructions in priority order. It can only act on documents
that retrieval returned: if a relevant sequence is not retrieved, its directive is not
applied, exactly as a language model cannot follow guidance it was never shown. That
property makes it both a fallback for the language model path and a clean instrument
for measuring how retrieval quality drives control outcomes.
"""
from __future__ import annotations

import json

from ..safe_eval import safe_eval
from .base import ReasoningContext


class OfflineReasoner:
    name = "offline"

    def propose(self, ctx: ReasoningContext) -> str:
        directives = sorted(
            (d for doc_id in dict.fromkeys(h.doc_id for h in ctx.hits) for d in ctx.kb.docs[doc_id].directives),
            key=lambda d: (d.priority, d.id),
        )
        zones, cited, labels = {}, [], []
        for zone in ctx.situation.zones:
            env = ctx.situation.zone_context(zone, ctx.knob_vars)
            env["heat"], env["cool"] = float(ctx.safe_default["heat"]), float(ctx.safe_default["cool"])
            lockout, label = False, "safe_default"
            for d in directives:
                if not safe_eval(d.when, env):
                    continue
                for target, expr in d.set.items():
                    env[target] = float(safe_eval(expr, env))
                lockout = lockout or d.lockout
                label = d.label
                if d.doc_id not in cited:
                    cited.append(d.doc_id)
            zones[zone.name] = {"heat": round(env["heat"], 2), "cool": round(env["cool"], 2), "lockout": lockout}
            labels.append(label)
        strategy = "+".join(dict.fromkeys(labels))
        rationale = "; ".join(f"{z.name}: {lab}" for z, lab in zip(ctx.situation.zones, labels))
        return json.dumps({"zones": zones, "strategy": strategy, "rationale": rationale, "citations": cited})
