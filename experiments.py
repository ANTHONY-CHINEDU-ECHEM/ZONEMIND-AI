"""Experiment suites: benchmark, ablations, robustness and retrieval quality.

Protocol. For every climate the agent first operates a commissioning year on perturbed
weather with a different occupancy draw, choosing its strategy knobs at random so the
episodic memory fills with unbiased evidence. It is then evaluated on the measured
typical year with that memory attached. Baselines and ablations are evaluated on the
same evaluation year, so every number in a table is directly comparable.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from ..config import repo_root
from ..knowledge.retriever import Retriever
from ..memory.episodic import EpisodicMemory
from .runner import get_kb, make_controller, make_scenario, run

BASELINES = ("fixed", "scheduled", "scheduled_tou")
ABLATIONS = {
    "zonemind_no_memory": {"memory.enabled": False},
    "zonemind_cold_memory": {},                                   # starts the evaluation year with no episodes
    "zonemind_bm25_only": {"retrieval.mode": "bm25"},
    "zonemind_dense_only": {"retrieval.mode": "dense"},
    "zonemind_single_query": {"retrieval.decompose": False},
    "zonemind_no_retrieval": {"retrieval.mode": "none", "memory.enabled": False},
}
_DROP = ("env", "traces")


def results_dir() -> Path:
    path = repo_root() / "results"
    path.mkdir(exist_ok=True)
    return path


def _slim(result: dict) -> dict:
    return {k: v for k, v in result.items() if k not in _DROP}


def _save(name: str, payload) -> Path:
    path = results_dir() / name
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=float)
    return path


def _log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def memory_path(climate: str) -> Path:
    return results_dir() / "memory" / f"{climate}.json"


def commission(cfg, climate: str) -> EpisodicMemory:
    """Run the commissioning year with random knob exploration and save the memory."""
    scenario = make_scenario(cfg, climate, commissioning=True)
    agent = make_controller("zonemind_commissioning", cfg, memory=EpisodicMemory(),
                            overrides={"memory.warmup_days": 10_000})
    result = run(scenario, agent)
    agent.memory.save(memory_path(climate))
    _log(f"commissioned {climate}: {len(agent.memory)} episodes, bill {result['total_cost']:.0f}")
    return agent.memory


def load_memory(cfg, climate: str) -> EpisodicMemory:
    path = memory_path(climate)
    return EpisodicMemory.load(path) if path.exists() else commission(cfg, climate)


def _event_day(scenario) -> int:
    """The critical peak day with the highest attendance, used for the worked example."""
    days = np.flatnonzero(scenario.tariff.critical_days)
    return int(days[np.argmax(scenario.occ.attendance_daily[days])])


def _window(env, scenario, day: int) -> dict:
    sph = scenario.cal.steps_per_hour
    s0, s1 = day * 24 * sph, (day + 1) * 24 * sph
    return {"ta": env.rec_ta[s0:s1], "cool_sp": env.rec_cool_sp[s0:s1], "heat_sp": env.rec_heat_sp[s0:s1],
            "kw": env.total_kw(s0, s1), "hvac_kw": env.rec_power[s0:s1].sum(axis=1),
            "t_out": scenario.weather.t_out[s0:s1], "occ": scenario.occ.actual[s0:s1],
            "period": np.repeat(scenario.tariff.period_hourly[day * 24:(day + 1) * 24], sph)}


def benchmark(cfg, climates: list[str]) -> list[dict]:
    """Baselines against the full agent on the evaluation year of each climate."""
    rows = []
    for climate in climates:
        commission(cfg, climate)
        scenario = make_scenario(cfg, climate)
        day = _event_day(scenario)
        windows = {}
        for name in BASELINES:
            result = run(scenario, make_controller(name, cfg), keep_env=True)
            windows[name] = _window(result["env"], scenario, day)
            rows.append(_slim(result))
            _log(f"{climate} {name}: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f}")
        agent = make_controller("zonemind", cfg, memory=load_memory(cfg, climate))
        result = run(scenario, agent, keep_env=True, trace_days={day})
        windows["zonemind"] = _window(result["env"], scenario, day)
        rows.append(_slim(result))
        _log(f"{climate} zonemind: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f}")
        np.savez_compressed(results_dir() / f"event_day_{climate}.npz", day=day,
                            **{f"{c}__{k}": v for c, w in windows.items() for k, v in w.items()})
        _save(f"traces_{climate}.json", {"day": day, "date": str(scenario.cal.dates[day].date()),
                                         "traces": result["traces"]})
        _save("benchmark.json", rows)
    return rows


def ablations(cfg, climates: list[str]) -> list[dict]:
    """Remove one component at a time and rerun the evaluation year."""
    rows = []
    for climate in climates:
        scenario = make_scenario(cfg, climate)
        for name, overrides in ABLATIONS.items():
            uses_warm_memory = name not in ("zonemind_cold_memory", "zonemind_no_memory", "zonemind_no_retrieval")
            memory = load_memory(cfg, climate) if uses_warm_memory else EpisodicMemory()
            result = run(scenario, make_controller(name, cfg, memory=memory, overrides=overrides))
            rows.append(_slim(result))
            _log(f"{climate} {name}: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f}")
            _save("ablations.json", rows)
    return rows


def robustness(cfg, climate: str) -> list[dict]:
    """Inject faults into the reasoning output with and without the verifier in the loop."""
    rows = []
    scenario = make_scenario(cfg, climate)
    variants = {
        "clean_with_verifier": {"memory.enabled": False},
        "faults_with_verifier": {"memory.enabled": False, "llm.backend": "chaos"},
        "faults_without_verifier": {"memory.enabled": False, "llm.backend": "chaos", "agent.verifier": False},
    }
    for name, overrides in variants.items():
        result = run(scenario, make_controller(name, cfg, overrides=overrides))
        rows.append(_slim(result))
        _log(f"{climate} {name}: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f} "
             f"unsafe {result['stats']['unsafe_commands']}")
    _save("robustness.json", rows)
    return rows


def retrieval_eval(cfg, climates: list[str], ks=(2, 4, 6, 8, 10, 12)) -> list[dict]:
    """Recall of applicable operating documents for each retriever configuration.

    Ground truth needs no hand labelling: a document is relevant to a decision exactly
    when one of its directives applies to the situation. Every hourly decision of the
    evaluation year is scored.
    """
    kb = get_kb()
    rows = []
    for climate in climates:
        scenario = make_scenario(cfg, climate)
        agent = make_controller("probe", cfg, overrides={"memory.enabled": False})
        run(scenario, agent)
        cases = Counter(agent.gold_log)
        retriever = Retriever(kb, cfg)
        for mode, decompose, label in (("bm25", True, "BM25"), ("dense", True, "LSA dense"),
                                       ("hybrid", False, "Hybrid, single query"),
                                       ("hybrid", True, "Hybrid, decomposed")):
            for k in ks:
                recall = full = total = 0.0
                for (facets, gold), count in cases.items():
                    if not gold:
                        continue
                    got = {h.doc_id for h in retriever.search(list(facets), top_k=k, mode=mode, decompose=decompose)}
                    recall += count * len(gold & got) / len(gold)
                    full += count * (gold <= got)
                    total += count
                rows.append({"climate": climate, "retriever": label, "k": k, "recall": recall / total,
                             "full_coverage": full / total, "decisions": int(total),
                             "distinct_situations": len(cases)})
        _log(f"retrieval eval {climate}: {len(cases)} distinct situations")
    _save("retrieval_eval.json", rows)
    return rows


def knob_sensitivity(cfg, climates: list[str]) -> list[dict]:
    """Hold each strategy knob at each of its values for a whole year, one at a time.

    This measures how much there is to gain from tuning at all, which puts the episodic
    memory result in context.
    """
    rows = []
    for climate in climates:
        scenario = make_scenario(cfg, climate)
        for knob, spec in cfg.memory.knobs.items():
            for value in spec["values"]:
                overrides = {"memory.enabled": False, f"memory.knobs.{knob}.default": value}
                result = run(scenario, make_controller(f"{knob}={value}", cfg, overrides=overrides))
                row = _slim(result)
                row.update(knob=knob, value=value, is_default=value == spec.default,
                           score=sum(d["score"] for d in result["daily"]))
                row.pop("daily", None)
                rows.append(row)
                _log(f"{climate} {knob}={value}: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f}")
        _save("knob_sensitivity.json", rows)
    return rows


def retrieval_budget(cfg, climates: list[str], k: int = 4) -> list[dict]:
    """Rerun the year with a tight retrieval budget to expose how retrieval misses change control.

    With a generous budget every retriever finds what it needs. Halving the budget makes
    the retrievers differ, and because the reasoner can only act on what it was shown,
    the difference appears directly in the bill, in comfort and in verifier workload.
    """
    rows = []
    variants = {
        "hybrid_decomposed": {}, "hybrid_single_query": {"retrieval.decompose": False},
        "bm25_decomposed": {"retrieval.mode": "bm25"}, "dense_decomposed": {"retrieval.mode": "dense"},
    }
    for climate in climates:
        scenario = make_scenario(cfg, climate)
        for name, extra in variants.items():
            overrides = {"memory.enabled": False, "retrieval.top_k": k, **extra}
            result = run(scenario, make_controller(name, cfg, overrides=overrides))
            row = _slim(result)
            row.update(k=k)
            row.pop("daily", None)
            rows.append(row)
            _log(f"{climate} k={k} {name}: bill {result['total_cost']:.0f} comfort {result['comfort_kh']:.1f}")
        _save("retrieval_budget.json", rows)
    return rows
