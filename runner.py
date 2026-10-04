"""Scenario construction and the closed loop simulation runner."""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from ..config import repo_root
from ..control.agent import ZoneMindAgent
from ..control.baselines import BaselineController
from ..control.situation import SituationBuilder
from ..control.verifier import Verifier
from ..data.calendar import Calendar, build_calendar
from ..data.occupancy import Occupancy, generate_occupancy
from ..data.tariff import Tariff, build_tariff
from ..data.weather import Weather, load_weather, perturb
from ..knowledge.loader import KnowledgeBase, load_knowledge_base
from ..knowledge.retriever import Retriever
from ..llm.backends import make_backend
from ..memory.episodic import EpisodicMemory
from ..sim.env import BuildingEnv
from .metrics import compute_metrics


@dataclass
class Scenario:
    cfg: object
    climate: str
    label: str
    cal: Calendar
    weather: Weather
    occ: Occupancy
    tariff: Tariff


def make_scenario(cfg, climate: str, commissioning: bool = False) -> Scenario:
    """Build weather, occupancy and tariff for one climate.

    The evaluation year uses the measured typical year weather file. The commissioning
    year uses a perturbed copy of the same climate and a different occupancy draw, so
    nothing the agent learns there is a memory of the exact days it is later tested on.
    """
    seed = int(cfg.project.seed)
    cal = build_calendar(cfg.sim.year, cfg.sim.dt_seconds, list(cfg.occupancy.holidays))
    spec = cfg.climates[climate]
    weather = load_weather(repo_root() / spec.file, climate, spec.label, cal, cfg, seed)
    if commissioning:
        weather = perturb(weather, cal, seed + 101)
    kinds = [z.kind for z in cfg.building.zones]
    occ = generate_occupancy(cal, kinds, cfg, seed + (202 if commissioning else 1))
    return Scenario(cfg, climate, weather.label, cal, weather, occ, build_tariff(cal, weather, cfg))


_KB_CACHE: dict[str, KnowledgeBase] = {}


def get_kb() -> KnowledgeBase:
    path = str(repo_root() / "data" / "knowledge_base")
    if path not in _KB_CACHE:
        _KB_CACHE[path] = load_knowledge_base(path)
    return _KB_CACHE[path]


def make_controller(name: str, cfg, memory: EpisodicMemory | None = None, overrides: dict | None = None,
                    audit_path=None, seed: int | None = None):
    """Create a baseline or a ZoneMind agent variant by name."""
    if name in ("fixed", "scheduled", "scheduled_tou"):
        return BaselineController(name, cfg)
    cfg = copy.deepcopy(cfg)
    for dotted, value in (overrides or {}).items():
        node = cfg
        *parents, leaf = dotted.split(".")
        for p in parents:
            node = node[p]
        node[leaf] = value
    kb = get_kb()
    seed = int(cfg.project.seed) if seed is None else seed
    return ZoneMindAgent(cfg, kb, Retriever(kb, cfg), make_backend(cfg, seed), Verifier(kb, cfg),
                         memory=memory, name=name, seed=seed, audit_path=audit_path)


def run(scenario: Scenario, controller, start_day: int = 0, days: int | None = None, keep_env: bool = False,
        trace_days: set[int] | None = None) -> dict:
    """Simulate ``days`` days of closed loop operation and return metrics and daily series."""
    cfg, cal = scenario.cfg, scenario.cal
    env = BuildingEnv(cfg, cal, scenario.weather, scenario.occ)
    builder = SituationBuilder(cfg, cal, scenario.weather, scenario.occ, scenario.tariff, env)
    names = env.model.names
    sph = cal.steps_per_hour
    days = cal.n_days - start_day if days is None else min(days, cal.n_days - start_day)
    h0, h1 = start_day * 24, (start_day + days) * 24
    dt_h = cal.dt / 3600.0
    price = scenario.tariff.price_steps()
    lo, hi = cfg.comfort.band_c
    lam = cfg.memory.comfort_penalty_per_kh
    daily, traces = [], []

    for h in range(h0, h1):
        step = h * sph
        situation = builder.build(step)
        decision = controller.decide(situation)
        if trace_days and situation.day in trace_days and decision.trace:
            traces.append(decision.trace)
        heat = [decision.commands[n].heat for n in names]
        cool = [decision.commands[n].cool for n in names]
        lock = [decision.commands[n].lockout for n in names]
        env.run_block(step, step + sph, heat, cool, lock)
        builder.observe(step, step + sph, heat, cool)

        if (h + 1) % 24 == 0:
            day = h // 24
            s0, s1 = day * 24 * sph, (day + 1) * 24 * sph
            kw = env.total_kw(s0, s1)
            ta = env.rec_ta[s0:s1]
            present = scenario.occ.actual[s0:s1] >= scenario.occ.threshold
            comfort = float((np.maximum(np.maximum(lo - ta, ta - hi), 0.0) * present).sum() * dt_h)
            energy_cost = float((kw * dt_h * price[s0:s1]).sum())
            demand_cost, peak, peak_on = scenario.tariff.day_demand_cost(kw, cal, s0)
            score = energy_cost + demand_cost + lam * comfort
            summary = {"day": day, "energy_cost": energy_cost, "peak_kw": peak, "on_peak_kw": peak_on,
                       "comfort_kh": comfort, "score": score, "label": scenario.climate}
            controller.end_of_day(day, summary)
            daily.append(summary)

    s0, s1 = h0 * sph, h1 * sph
    result = compute_metrics(env, scenario.tariff, cal, cfg, s0, s1)
    result.update(controller=controller.name, climate=scenario.climate, days=days, daily=daily,
                  stats=copy.deepcopy(getattr(controller, "stats", {})))
    if isinstance(controller, ZoneMindAgent):
        result["knob_log"] = list(controller.knob_log)
        r = controller.retriever
        result["retrieval"] = {"calls": r.calls, "cache_hits": r.cache_hits,
                               "ms_per_uncached_query": 1000.0 * r.seconds / max(r.calls - r.cache_hits, 1)}
        if hasattr(controller.backend, "injected"):
            result["injected_faults"] = dict(controller.backend.injected)
    if traces:
        result["traces"] = traces
    if keep_env:
        result["env"] = env
    return result
