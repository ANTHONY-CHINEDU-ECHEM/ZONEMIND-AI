"""Constraint verification and repair.

The verifier is the safety boundary of the system. It is deliberately independent of
both retrieval and the reasoning backend: it loads every hard constraint from the
governed knowledge base at start up and checks every proposal against all of them,
whether or not the relevant document was retrieved for this decision. A proposal that
breaks a limit is repaired to the nearest compliant command and the intervention is
recorded with the constraint and source document that triggered it.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

from ..knowledge.loader import KnowledgeBase
from ..llm.schema import Proposal, ZoneCommand
from ..safe_eval import safe_eval
from .situation import Situation

_EPS = 1e-6


@dataclass
class Violation:
    zone: str
    constraint: str
    source: str
    field: str
    proposed: float | bool | None
    repaired: float | bool
    reason: str


@dataclass
class VerificationReport:
    violations: list[Violation] = field(default_factory=list)
    ungrounded_citations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations and not self.ungrounded_citations

    def to_dict(self) -> dict:
        return {"violations": [asdict(v) for v in self.violations],
                "ungrounded_citations": self.ungrounded_citations}


class Verifier:
    def __init__(self, kb: KnowledgeBase, cfg):
        self.kb = kb
        self.safe = cfg.agent.safe_default
        by_kind: dict[str, list] = {"bound": [], "gap": [], "rate": [], "flag": []}
        for c in kb.constraints:
            by_kind[c.kind].append(c)
        self.bounds, self.gaps, self.rates, self.flags = (by_kind[k] for k in ("bound", "gap", "rate", "flag"))

    def verify(self, proposal: Proposal, situation: Situation, knob_vars: dict,
               retrieved_ids: set[str] | None = None) -> tuple[dict[str, ZoneCommand], VerificationReport]:
        report = VerificationReport()
        commands: dict[str, ZoneCommand] = {}
        for zone in situation.zones:
            ctx = situation.zone_context(zone, knob_vars)
            cmd = proposal.zones.get(zone.name)
            if cmd is None:
                report.violations.append(Violation(zone.name, "C_MISSING", "verifier", "zone", None, True,
                                                   "Proposal omitted this zone; safe default applied"))
                heat, cool, lockout = float(self.safe.heat), float(self.safe.cool), False
            else:
                heat, cool, lockout = cmd.heat, cmd.cool, cmd.lockout
            for name, value in (("heat", heat), ("cool", cool)):
                if not math.isfinite(value):
                    fixed = float(self.safe[name])
                    report.violations.append(Violation(zone.name, "C_FINITE", "verifier", name, None, fixed,
                                                       "Setpoint was not a finite number"))
                    heat, cool = (fixed, cool) if name == "heat" else (heat, fixed)
            values = {"heat": float(heat), "cool": float(cool)}

            # 1. Rate of change limits, relative to the setpoints currently in force.
            for c in self.rates:
                if c.when is None or safe_eval(c.when, ctx):
                    for name, prev in (("heat", zone.prev_heat), ("cool", zone.prev_cool)):
                        delta = values[name] - prev
                        if abs(delta) > c.max_delta + _EPS:
                            fixed = prev + math.copysign(c.max_delta, delta)
                            report.violations.append(Violation(zone.name, c.id, c.doc_id, name, values[name], fixed, c.reason))
                            values[name] = fixed

            # 2. Absolute and conditional bounds. These outrank the rate limit.
            upper = {"heat": math.inf, "cool": math.inf}
            for c in self.bounds:
                if c.when is None or safe_eval(c.when, ctx):
                    v = values[c.var]
                    fixed = v
                    if c.min is not None and v < c.min - _EPS:
                        fixed = c.min
                    if c.max is not None:
                        upper[c.var] = min(upper[c.var], c.max)
                        if v > c.max + _EPS:
                            fixed = c.max
                    if fixed != v:
                        report.violations.append(Violation(zone.name, c.id, c.doc_id, c.var, v, fixed, c.reason))
                        values[c.var] = fixed

            # 3. Dead band. Open the gap upward first, downward only if cooling is at its ceiling.
            for c in self.gaps:
                if values["cool"] - values["heat"] < c.min_gap - _EPS:
                    target = values["heat"] + c.min_gap
                    if target <= upper["cool"] + _EPS:
                        report.violations.append(Violation(zone.name, c.id, c.doc_id, "cool", values["cool"], target, c.reason))
                        values["cool"] = target
                    else:
                        new_cool = upper["cool"]
                        new_heat = new_cool - c.min_gap
                        report.violations.append(Violation(zone.name, c.id, c.doc_id, "heat", values["heat"], new_heat, c.reason))
                        values["heat"], values["cool"] = new_heat, new_cool

            # 4. Flags.
            if lockout:
                for c in self.flags:
                    if c.when is None or safe_eval(c.when, ctx):
                        report.violations.append(Violation(zone.name, c.id, c.doc_id, "lockout", True, False, c.reason))
                        lockout = False
                        break
            commands[zone.name] = ZoneCommand(heat=round(values["heat"], 2), cool=round(values["cool"], 2), lockout=lockout)

        if retrieved_ids is not None:
            report.ungrounded_citations = [c for c in proposal.citations if c not in retrieved_ids]
        return commands, report

    def audit(self, proposal: Proposal, situation: Situation, knob_vars: dict) -> VerificationReport:
        """Check without repairing. Used to count what would reach the plant unverified."""
        _, report = self.verify(proposal, situation, knob_vars, None)
        return report
