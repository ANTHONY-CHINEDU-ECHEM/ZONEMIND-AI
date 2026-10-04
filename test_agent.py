"""Tests for the verifier, the reasoner, episodic memory and the closed loop."""
import numpy as np
import pytest

from zonemind.control.verifier import Verifier
from zonemind.eval.runner import make_controller, make_scenario, run
from zonemind.knowledge.retriever import Hit
from zonemind.llm.base import ReasoningContext
from zonemind.llm.offline import OfflineReasoner
from zonemind.llm.parser import parse_proposal
from zonemind.llm.schema import Proposal, ZoneCommand
from zonemind.memory.episodic import Episode, EpisodicMemory, KnobTuner

ZONES = ("north", "east", "south", "west", "core")


def proposal(heat=21.0, cool=24.0, lockout=False, skip=(), citations=()):
    return Proposal(zones={z: ZoneCommand(heat=heat, cool=cool, lockout=lockout) for z in ZONES if z not in skip},
                    citations=list(citations))


# ---------------------------------------------------------------- verifier
def test_compliant_proposal_passes_untouched(kb, cfg, situation, knob_vars):
    commands, report = Verifier(kb, cfg).verify(proposal(), situation(), knob_vars, {"SOO01"})
    assert report.ok and all(c.heat == 21.0 and c.cool == 24.0 for c in commands.values())


def test_occupied_comfort_limit_is_enforced(kb, cfg, situation, knob_vars):
    s = situation(zone={"prev_cool": 26.0})
    commands, report = Verifier(kb, cfg).verify(proposal(cool=29.5), s, knob_vars)
    assert all(c.cool == 26.0 for c in commands.values())
    assert "C_OCC_COOL" in {v.constraint for v in report.violations}


def test_rate_limit_applies_before_bounds(kb, cfg, situation, knob_vars):
    commands, report = Verifier(kb, cfg).verify(proposal(heat=20.0, cool=22.0), situation(zone={"prev_cool": 26.0}), knob_vars)
    assert all(c.cool == 23.0 for c in commands.values())
    assert {v.constraint for v in report.violations} == {"C_RATE"}


def test_inverted_dead_band_is_repaired(kb, cfg, situation, knob_vars):
    commands, report = Verifier(kb, cfg).verify(proposal(heat=24.0, cool=22.0), situation(), knob_vars)
    assert all(c.cool - c.heat >= 2.0 - 1e-9 and c.cool <= 26.0 and c.heat >= 20.0 for c in commands.values())
    assert "C_DEADBAND" in {v.constraint for v in report.violations}


def test_lockout_is_released_when_occupied_but_allowed_when_empty(kb, cfg, situation, knob_vars):
    v = Verifier(kb, cfg)
    occupied, _ = v.verify(proposal(lockout=True), situation(), knob_vars)
    empty, report = v.verify(proposal(heat=15.5, cool=21.0, lockout=True),
                             situation(zone={"occupied": False, "h_to_occ": 8}), knob_vars)
    assert not any(c.lockout for c in occupied.values())
    assert all(c.lockout for c in empty.values()) and not report.violations


def test_missing_zone_gets_the_safe_default(kb, cfg, situation, knob_vars):
    commands, report = Verifier(kb, cfg).verify(proposal(skip=("west",)), situation(), knob_vars)
    assert commands["west"].heat == cfg.agent.safe_default.heat
    assert "C_MISSING" in {v.constraint for v in report.violations}


def test_equipment_range_core_ceiling_and_citations(kb, cfg, situation, knob_vars):
    s = situation(zone={"occupied": False, "h_to_occ": 9, "prev_heat": 15.5, "prev_cool": 30.0})
    commands, report = Verifier(kb, cfg).verify(proposal(heat=9.0, cool=35.0, citations=("SOO02", "SOO99")), s, knob_vars, {"SOO02"})
    assert commands["north"].heat == 13.0 and commands["north"].cool == 31.0 and commands["core"].cool == 27.0
    assert report.ungrounded_citations == ["SOO99"]


def test_verified_commands_always_pass_a_second_check(kb, cfg, situation, knob_vars):
    v = Verifier(kb, cfg)
    rng = np.random.default_rng(0)
    for _ in range(200):
        s = situation(zone={"occupied": bool(rng.integers(2)), "prev_heat": float(rng.uniform(13, 23)),
                            "prev_cool": float(rng.uniform(25, 31))}, t_out_min_12h=float(rng.uniform(-25, 20)))
        commands, _ = v.verify(proposal(heat=float(rng.uniform(0, 40)), cool=float(rng.uniform(0, 40)),
                                        lockout=bool(rng.integers(2))), s, knob_vars)
        again = Proposal(zones=commands)
        for z in s.zones:   # the repaired command is now the command in force
            z.prev_heat, z.prev_cool = commands[z.name].heat, commands[z.name].cool
        assert not v.audit(again, s, knob_vars).violations


# ---------------------------------------------------------------- reasoner
def _ctx(kb, cfg, s, knob_vars, doc_ids):
    hits = [Hit(d, 1.0, d + "#0", "", "") for d in doc_ids]
    return ReasoningContext(situation=s, hits=hits, kb=kb, knobs={}, knob_vars=knob_vars,
                            safe_default=dict(cfg.agent.safe_default))


def test_reasoner_without_documents_holds_the_safe_default(kb, cfg, situation, knob_vars):
    p = parse_proposal(OfflineReasoner().propose(_ctx(kb, cfg, situation(), knob_vars, [])))
    assert all(c.heat == 21.0 and c.cool == 24.0 for c in p.zones.values()) and p.citations == []


def test_reasoner_only_applies_what_was_retrieved(kb, cfg, situation, knob_vars):
    s = situation()   # occupied, cooling season, peak window starts in one hour, hot forecast
    with_precool = parse_proposal(OfflineReasoner().propose(_ctx(kb, cfg, s, knob_vars, ["SOO01", "SOO05"])))
    without = parse_proposal(OfflineReasoner().propose(_ctx(kb, cfg, s, knob_vars, ["SOO01"])))
    assert with_precool.zones["north"].cool == 23.0 and "SOO05" in with_precool.citations
    assert without.zones["north"].cool == 24.0 and "SOO05" not in without.citations


# ---------------------------------------------------------------- memory
def _episode(day, t_max, lead, score):
    outlook = {"t_max": t_max, "t_min": t_max - 8, "t_mean": t_max - 4, "ghi_mean": 150.0, "attendance": 0.6,
               "is_monday": False, "dr_today": False, "mode": "heating"}
    return Episode(day, "test", outlook, {"start_lead": lead, "peak_strategy": "light", "setback": "deep"},
                   score, 20.0, 0.0, score)


def test_tuner_learns_a_clear_effect_and_ignores_noise(cfg, tmp_path):
    rng = np.random.default_rng(1)
    clear, noisy = EpisodicMemory(), EpisodicMemory()
    for day in range(300):
        lead = int(rng.integers(1, 4))
        t_max = float(rng.uniform(-5, 10))
        clear.add(_episode(day, t_max, lead, 50.0 - t_max + (0.0 if lead == 3 else 6.0) + rng.normal(0, 1.0)))
        noisy.add(_episode(day, t_max, lead, 50.0 - t_max + rng.normal(0, 5.0)))
    outlook = clear.episodes[0].outlook
    assert KnobTuner(cfg, clear, 0).choose(outlook)[0]["start_lead"] == 3
    assert KnobTuner(cfg, noisy, 0).choose(outlook)[0] == {"start_lead": 2, "peak_strategy": "light", "setback": "deep"}
    clear.save(tmp_path / "m.json")
    assert len(EpisodicMemory.load(tmp_path / "m.json")) == 300


def test_tuner_explores_during_commissioning(cfg):
    _, info = KnobTuner(cfg, EpisodicMemory(), 0).choose(_episode(0, 5.0, 2, 0.0).outlook)
    assert info["explored"]


# ---------------------------------------------------------------- closed loop
@pytest.fixture(scope="module")
def scenario(cfg):
    return make_scenario(cfg, "chicago")


def test_agent_runs_end_to_end_and_stays_grounded(cfg, scenario):
    result = run(scenario, make_controller("zonemind", cfg), start_day=188, days=5)
    stats = result["stats"]
    assert stats["decisions"] == 120 and stats["grounded_decisions"] == 120 and stats["ungrounded_citations"] == 0
    assert np.isfinite(result["total_cost"]) and result["in_band_pct"] > 95.0


def test_agent_beats_the_timetable_on_comfort_in_a_cold_week(cfg, scenario):
    agent = run(scenario, make_controller("zonemind", cfg, overrides={"memory.enabled": False}), start_day=12, days=7)
    timetable = run(scenario, make_controller("scheduled", cfg), start_day=12, days=7)
    assert agent["comfort_kh"] <= timetable["comfort_kh"]


def test_fault_injection_is_contained_by_the_verifier(cfg, scenario):
    base = {"memory.enabled": False, "llm.backend": "chaos", "llm.chaos_fault_rate": 0.5}
    guarded = run(scenario, make_controller("guarded", cfg, overrides=base), start_day=188, days=5)
    exposed = run(scenario, make_controller("exposed", cfg, overrides={**base, "agent.verifier": False}), start_day=188, days=5)
    assert sum(guarded["injected_faults"].values()) > 20
    assert guarded["stats"]["unsafe_commands"] == 0 and guarded["stats"]["repairs"] > 0
    assert guarded["stats"]["parse_failures"] > 0          # malformed output fell back cleanly
    assert exposed["stats"]["unsafe_commands"] > 0
