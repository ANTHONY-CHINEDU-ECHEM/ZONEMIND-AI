"""Unit tests for the building blocks: expressions, knowledge, retrieval, parsing, physics."""
import json

import numpy as np
import pytest

from zonemind.data.calendar import build_calendar
from zonemind.data.occupancy import generate_occupancy
from zonemind.data.tariff import CRITICAL, PEAK, build_tariff
from zonemind.data.weather import load_weather
from zonemind.config import repo_root
from zonemind.knowledge.loader import parse_document
from zonemind.knowledge.retriever import Retriever
from zonemind.llm.parser import ParseError, parse_proposal
from zonemind.safe_eval import UnsafeExpression, safe_eval, validate
from zonemind.sim.building import build_model
from zonemind.sim.comfort import classify_mode, pmv_ppd


# ---------------------------------------------------------------- safe expressions
def test_safe_eval_supports_conditions_and_arithmetic():
    ctx = {"occupied": True, "h_to_peak": 2, "cool": 24.0, "tariff": "mid"}
    assert safe_eval("occupied and 0 < h_to_peak <= 2 and tariff not in ('peak', 'critical')", ctx)
    assert safe_eval("max(22.0, cool - 3)", ctx) == 22.0
    assert safe_eval(21.5, ctx) == 21.5


@pytest.mark.parametrize("expr", [
    "__import__('os').system('echo hi')", "occupied.__class__", "open('x')", "(lambda: 1)()",
    "[x for x in (1, 2)]", "cool ** 9", "ctx['a']", "_private > 1",
])
def test_safe_eval_rejects_anything_outside_the_whitelist(expr):
    with pytest.raises(UnsafeExpression):
        safe_eval(expr, {"occupied": True, "cool": 24.0, "ctx": {}, "_private": 1})


def test_validate_rejects_unknown_variables():
    with pytest.raises(UnsafeExpression):
        validate("occupied and typo_variable > 1", {"occupied"})


# ---------------------------------------------------------------- knowledge base
def test_knowledge_base_loads_and_is_consistent(kb):
    stats = kb.stats()
    assert stats["documents"] >= 40 and stats["directives"] >= 20 and stats["constraints"] >= 10
    assert all(d.doc_id in kb.docs for d in kb.directives)
    assert {c.kind for c in kb.constraints} <= {"bound", "gap", "rate", "flag"}
    assert all(chunk.text.startswith(kb.docs[chunk.doc_id].title) for chunk in kb.chunks)


def test_loader_rejects_a_document_with_a_bad_directive():
    text = "---\nid: X1\ntitle: Bad\ncategory: test\ndirectives:\n  - {priority: 1, when: \"nonsense > 1\", set: {cool: 24}}\n---\n## A\nbody\n"
    with pytest.raises(UnsafeExpression):
        parse_document(text)


# ---------------------------------------------------------------- retrieval
@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
def test_retrieval_finds_the_peak_window_sequence(kb, cfg, mode):
    hits = Retriever(kb, cfg).search(["The peak tariff window is active now in cooling season."], top_k=3, mode=mode)
    assert "SOO06" in [h.doc_id for h in hits]


def test_retrieval_decomposition_covers_every_facet(kb, cfg):
    facets = ["Zones are unoccupied and empty with nobody expected soon, at night, a weekend or a holiday.",
              "Severe cold is forecast overnight, a cold snap."]
    got = [h.doc_id for h in Retriever(kb, cfg).search(facets, top_k=2, mode="hybrid", decompose=True)]
    assert got == ["SOO02", "PB02"] or set(got) == {"SOO02", "PB02"}


def test_retrieval_mode_none_returns_nothing(kb, cfg):
    assert Retriever(kb, cfg).search(["anything"], mode="none") == []


# ---------------------------------------------------------------- parser
def test_parser_handles_fences_and_prose():
    payload = {"zones": {"north": {"heat": 21, "cool": 24}}, "citations": ["SOO01"]}
    text = "Sure, here you go:\n```json\n" + json.dumps(payload) + "\n```\nHope that helps."
    proposal = parse_proposal(text)
    assert proposal.zones["north"].cool == 24 and proposal.zones["north"].lockout is False


@pytest.mark.parametrize("text", ["no json here", '{"zones": {"north": {"heat": 21, "cool": 2',
                                  '{"zones": {"north": {"heat": "warm"}}}'])
def test_parser_raises_on_unusable_output(text):
    with pytest.raises(ParseError):
        parse_proposal(text)


# ---------------------------------------------------------------- physics and comfort
def test_pmv_matches_the_iso_7730_reference_case():
    pmv, ppd = pmv_ppd(np.array([22.0]), np.array([22.0]), 0.1, 60.0, 1.2, 0.5)
    assert pmv[0] == pytest.approx(-0.75, abs=0.02) and ppd[0] == pytest.approx(17.0, abs=0.5)


def test_mode_classification(cfg):
    th = cfg.comfort.mode_thresholds
    assert classify_mode(25, 31, th) == "cooling"
    assert classify_mode(2, 6, th) == "heating"
    assert classify_mode(13, 19, th) == "shoulder"


def test_thermal_model_is_stable_and_relaxes_to_outdoor_temperature(cfg):
    m = build_model(cfg, 300)
    assert np.all(np.abs(np.linalg.eigvals(m.M)) < 1.0)
    x = np.full(2 * m.n, 21.0)
    for _ in range(12 * 24 * 30):       # thirty days with no gains and no plant
        x = m.M @ (x + m.bout_dt * 5.0)
    assert np.allclose(x, 5.0, atol=0.05)


@pytest.fixture(scope="module")
def world(cfg):
    cal = build_calendar(cfg.sim.year, cfg.sim.dt_seconds, list(cfg.occupancy.holidays))
    weather = load_weather(repo_root() / cfg.climates.chicago.file, "chicago", "Chicago", cal, cfg, 1)
    return cal, weather


def test_weather_file_is_a_full_year(world):
    cal, weather = world
    assert len(weather.hourly_t) == 8760 and len(weather.t_out) == cal.n_steps
    assert -35 < weather.t_out.min() < weather.t_out.max() < 45
    assert weather.forecast(100, 24).shape == (24,)


def test_tariff_structure_and_bill_arithmetic(cfg, world):
    cal, weather = world
    tariff = build_tariff(cal, weather, cfg)
    assert 0 < tariff.critical_days.sum() <= cfg.tariff.critical.max_events
    saturday = int(np.flatnonzero(cal.weekday_daily == 5)[0])
    assert (tariff.period_hourly[saturday * 24: saturday * 24 + 24] == 0).all()
    july_workday = int(np.flatnonzero((cal.month_daily == 7) & cal.workday_daily & ~tariff.critical_days)[0])
    assert tariff.period_hourly[july_workday * 24 + 16] == PEAK
    event = int(np.flatnonzero(tariff.critical_days)[0])
    assert tariff.period_hourly[event * 24 + 16] == CRITICAL
    bill = tariff.bill(np.full(cal.n_steps, 10.0), cal)
    assert bill["energy_cost"] == pytest.approx(10.0 * tariff.price_hourly.sum())
    assert bill["demand_cost"] == pytest.approx(12 * 10.0 * (tariff.demand_anytime + tariff.demand_peak))


def test_occupancy_is_plausible(cfg, world):
    cal, _ = world
    occ = generate_occupancy(cal, [z.kind for z in cfg.building.zones], cfg, 3)
    assert occ.actual.min() >= 0 and occ.actual.max() <= 1
    daily = occ.actual.reshape(cal.n_days, -1).max(axis=1)
    assert (daily[cal.workday_daily] > 0).mean() > 0.95
    assert (daily[~cal.workday_daily] > 0).mean() < 0.2
    assert occ.forecast_hourly.shape == (cal.n_hours, len(cfg.building.zones))
