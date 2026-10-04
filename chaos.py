"""Fault injection backend for robustness testing.

Language models occasionally return malformed JSON, cite documents that do not exist,
or propose values outside any sensible range. This backend wraps a well behaved
reasoner and corrupts a configurable share of its outputs with those failure types, so
the parser, the fallback path and the verifier can be exercised and measured without
waiting for a real model to misbehave. It is a test instrument, not a model.
"""
from __future__ import annotations

import json

import numpy as np

from .base import Backend, ReasoningContext

FAULTS = ("out_of_range", "inverted_dead_band", "comfort_breach", "freeze_risk", "lockout_occupied",
          "missing_zone", "hallucinated_citation", "malformed_json", "wild_swing")


class ChaosBackend:
    name = "chaos"

    def __init__(self, inner: Backend, fault_rate: float, seed: int = 0):
        self.inner, self.fault_rate = inner, fault_rate
        self.rng = np.random.default_rng(seed)
        self.injected: dict[str, int] = {f: 0 for f in FAULTS}

    def propose(self, ctx: ReasoningContext) -> str:
        text = self.inner.propose(ctx)
        if self.rng.random() >= self.fault_rate:
            return text
        fault = FAULTS[int(self.rng.integers(len(FAULTS)))]
        self.injected[fault] += 1
        data = json.loads(text)
        names = list(data["zones"])
        zone = names[int(self.rng.integers(len(names)))]
        z = data["zones"][zone]
        if fault == "out_of_range":
            z["cool"], z["heat"] = 14.0, 9.0
        elif fault == "inverted_dead_band":
            z["heat"], z["cool"] = 24.0, 21.0
        elif fault == "comfort_breach":
            for name in names:
                data["zones"][name]["cool"] = 29.5
        elif fault == "freeze_risk":
            for name in names:
                data["zones"][name]["heat"] = 12.0
        elif fault == "lockout_occupied":
            for name in names:
                data["zones"][name]["lockout"] = True
        elif fault == "missing_zone":
            del data["zones"][zone]
        elif fault == "hallucinated_citation":
            data["citations"] = list(data["citations"]) + ["SOO99"]
        elif fault == "wild_swing":
            z["heat"], z["cool"] = z["heat"] - 6.0, z["cool"] + 6.0
        out = json.dumps(data)
        if fault == "malformed_json":
            out = "Here is my answer:\n" + out[: int(len(out) * 0.6)]
        return out
