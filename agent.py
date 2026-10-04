"""The ZoneMind agent: retrieve, remember, reason, verify, act, learn."""
from __future__ import annotations

import json
from pathlib import Path

from ..knowledge.loader import KnowledgeBase
from ..knowledge.retriever import Retriever
from ..llm.base import Backend, ReasoningContext
from ..llm.offline import OfflineReasoner
from ..llm.parser import ParseError, parse_proposal
from ..llm.schema import ZoneCommand
from ..memory.episodic import Episode, EpisodicMemory, KnobTuner
from ..safe_eval import safe_eval
from .baselines import Decision
from .situation import Situation, default_knobs, knob_variables
from .verbalizer import verbalise
from .verifier import Verifier


class ZoneMindAgent:
    def __init__(self, cfg, kb: KnowledgeBase, retriever: Retriever, backend: Backend, verifier: Verifier,
                 memory: EpisodicMemory | None = None, name: str = "zonemind", seed: int = 0,
                 audit_path: str | Path | None = None):
        self.cfg, self.kb, self.retriever, self.backend, self.verifier = cfg, kb, retriever, backend, verifier
        self.name = name
        self.use_verifier = bool(cfg.agent.verifier)
        self.memory = memory if memory is not None else EpisodicMemory()
        self.tuner = KnobTuner(cfg, self.memory, seed) if cfg.memory.enabled else None
        self.fallback = OfflineReasoner()
        self.safe = dict(cfg.agent.safe_default)
        self.knobs = default_knobs(cfg)
        self.plan_info: dict = {"how": "defaults", "explored": False}
        self._plan_day = -1
        self._outlook: dict = {}
        self._episodes: list[dict] = []
        self.audit = open(audit_path, "w", encoding="utf-8") if audit_path else None
        self.gold_log: list[tuple[tuple[str, ...], frozenset[str]]] = []
        self.knob_log: list[dict] = []
        self.stats = {
            "decisions": 0, "parse_failures": 0, "decisions_repaired": 0, "repairs": 0,
            "repairs_by_constraint": {}, "ungrounded_citations": 0, "citations": 0, "grounded_decisions": 0,
            "unsafe_decisions": 0, "unsafe_commands": 0, "recall_sum": 0.0, "recall_n": 0,
            "retrieved_docs": 0,
        }

    # ------------------------------------------------------------------ planning
    def _plan(self, s: Situation) -> None:
        """At the first decision of each day, choose the strategy knobs for that day."""
        self._plan_day, self._outlook = s.day, s.outlook
        if self.tuner is not None:
            self.knobs, self.plan_info = self.tuner.choose(s.outlook)
            self._episodes = self.memory.summaries(s.outlook, 3)
        self.knob_log.append({"day": s.day, **self.knobs, "explored": self.plan_info.get("explored", False),
                              "t_max": s.outlook["t_max"], "t_min": s.outlook["t_min"], "mode": s.outlook["mode"]})

    def _applicable_docs(self, s: Situation, knob_vars: dict) -> frozenset[str]:
        """Documents whose directives genuinely apply now. Used only to score retrieval."""
        gold = set()
        contexts = [s.zone_context(z, knob_vars) for z in s.zones]
        for d in self.kb.directives:
            if d.doc_id not in gold and any(safe_eval(d.when, ctx) for ctx in contexts):
                gold.add(d.doc_id)
        return frozenset(gold)

    # ------------------------------------------------------------------ decision
    def decide(self, s: Situation) -> Decision:
        if s.day != self._plan_day:
            self._plan(s)
        knob_vars = knob_variables(self.knobs, self.cfg)
        st = self.stats
        st["decisions"] += 1

        facets = verbalise(s, knob_vars["start_lead"])
        hits = self.retriever.search(facets)
        retrieved = {h.doc_id for h in hits}
        st["retrieved_docs"] += len(retrieved)
        gold = self._applicable_docs(s, knob_vars)
        self.gold_log.append((tuple(facets), gold))
        if gold:
            st["recall_sum"] += len(gold & retrieved) / len(gold)
            st["recall_n"] += 1

        ctx = ReasoningContext(situation=s, hits=hits, kb=self.kb, knobs=self.knobs, knob_vars=knob_vars,
                               safe_default=self.safe, episodes=self._episodes)
        raw = self.backend.propose(ctx)
        fell_back = False
        try:
            proposal = parse_proposal(raw)
        except ParseError:
            st["parse_failures"] += 1
            fell_back = True
            proposal = parse_proposal(self.fallback.propose(ctx))

        if self.use_verifier:
            commands, report = self.verifier.verify(proposal, s, knob_vars, retrieved)
            if report.violations:
                st["decisions_repaired"] += 1
                st["repairs"] += len(report.violations)
                for v in report.violations:
                    st["repairs_by_constraint"][v.constraint] = st["repairs_by_constraint"].get(v.constraint, 0) + 1
        else:
            # Ablation: commands go to the plant unchecked. A missing zone holds its last command.
            report = self.verifier.audit(proposal, s, knob_vars)
            report.ungrounded_citations = [c for c in proposal.citations if c not in retrieved]
            commands = {z.name: proposal.zones.get(z.name, ZoneCommand(heat=z.prev_heat, cool=z.prev_cool))
                        for z in s.zones}
            if report.violations:
                st["unsafe_decisions"] += 1
                st["unsafe_commands"] += len(report.violations)
        st["ungrounded_citations"] += len(report.ungrounded_citations)
        valid = [c for c in proposal.citations if c in retrieved]
        st["citations"] += len(valid)
        st["grounded_decisions"] += bool(valid)

        trace = {
            "time": s.stamp, "backend": self.backend.name, "fallback_used": fell_back,
            "knobs": self.knobs, "knob_selection": self.plan_info, "facets": facets,
            "retrieved": [h.doc_id for h in hits], "applicable": sorted(gold),
            "strategy": proposal.strategy, "rationale": proposal.rationale, "citations": proposal.citations,
            "proposed": {k: v.model_dump() for k, v in proposal.zones.items()},
            "commands": {k: v.model_dump() for k, v in commands.items()},
            "verification": report.to_dict(), "situation": s.to_prompt(),
        }
        if self.audit:
            self.audit.write(json.dumps(trace) + "\n")
        return Decision(commands, trace)

    # ------------------------------------------------------------------ learning
    def end_of_day(self, day: int, summary: dict) -> None:
        """Store the finished day as an episode so future days can learn from it."""
        if self.tuner is None or day != self._plan_day:
            return
        self.memory.add(Episode(
            day=day, label=summary.get("label", ""), outlook=self._outlook, knobs=dict(self.knobs),
            energy_cost=summary["energy_cost"], peak_kw=summary["peak_kw"], comfort_kh=summary["comfort_kh"],
            score=summary["score"], explored=bool(self.plan_info.get("explored", False)),
        ))

    def close(self) -> None:
        if self.audit:
            self.audit.close()
            self.audit = None
