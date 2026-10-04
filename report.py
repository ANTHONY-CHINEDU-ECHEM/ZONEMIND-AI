"""Turn saved experiment results into Markdown tables (``results/summary.md``)."""
from __future__ import annotations

import json

import numpy as np

from ..config import repo_root
from .plots import ABLATION_LABELS, LABELS


def _load(name: str):
    path = repo_root() / "results" / name
    return json.loads(path.read_text()) if path.exists() else None


def _table(header: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def _pct(new: float, old: float) -> str:
    return f"{100.0 * (1.0 - new / old):.1f}%"


def summarise(cfg) -> str:
    out = []
    bench = _load("benchmark.json")
    if bench:
        get = lambda c, n: next(r for r in bench if r["climate"] == c and r["controller"] == n)
        climates = list(dict.fromkeys(r["climate"] for r in bench))
        for c in climates:
            rows = []
            for n in LABELS:
                r = get(c, n)
                rows.append([LABELS[n], f"{r['hvac_kwh']:,.0f}", f"{r['hvac_energy_cost']:,.0f}", f"{r['demand_cost']:,.0f}",
                             f"{r['total_cost']:,.0f}", f"{r['peak_kw']:.1f}", f"{r['on_peak_kw']:.1f}",
                             f"{r['comfort_kh']:.1f}", f"{r['unmet_hours']:.1f}", f"{r['ppd_mean']:.1f}"])
            out += [f"### {cfg.climates[c].label}", "", _table(
                ["Controller", "HVAC kWh", "HVAC energy cost", "Demand charges", "Total bill", "Peak kW",
                 "On peak kW", "Comfort violations K·h", "Unmet zone hours", "Mean PPD %"], rows), ""]
        rows = []
        for c in climates:
            z = get(c, "zonemind")
            for ref in ("fixed", "scheduled", "scheduled_tou"):
                b = get(c, ref)
                rows.append([cfg.climates[c].label, LABELS[ref], _pct(z["total_cost"], b["total_cost"]),
                             _pct(z["hvac_energy_cost"], b["hvac_energy_cost"]), _pct(z["hvac_kwh"], b["hvac_kwh"]),
                             _pct(z["on_peak_kw"], b["on_peak_kw"]),
                             f"{b['comfort_kh']:.1f} to {z['comfort_kh']:.1f}"])
        out += ["### ZoneMind AI reduction relative to each baseline", "", _table(
            ["Climate", "Baseline", "Total bill", "HVAC energy cost", "HVAC kWh", "On peak demand",
             "Comfort violations K·h"], rows), ""]
        tot = {n: sum(get(c, n)["total_cost"] for c in climates) for n in LABELS}
        hv = {n: sum(get(c, n)["hvac_energy_cost"] for c in climates) for n in LABELS}
        kwh = {n: sum(get(c, n)["hvac_kwh"] for c in climates) for n in LABELS}
        cm = {n: sum(get(c, n)["comfort_kh"] for c in climates) for n in LABELS}
        rows = [[LABELS[n], f"{tot[n]:,.0f}", f"{hv[n]:,.0f}", f"{kwh[n]:,.0f}", f"{cm[n]:.1f}",
                 _pct(tot["zonemind"], tot[n]) if n != "zonemind" else "", _pct(hv["zonemind"], hv[n]) if n != "zonemind" else ""]
                for n in LABELS]
        out += ["### Portfolio view, four buildings combined", "", _table(
            ["Controller", "Total bill", "HVAC energy cost", "HVAC kWh", "Comfort violations K·h",
             "ZoneMind bill reduction", "ZoneMind HVAC cost reduction"], rows), ""]
        rows = []
        for c in climates:
            s = get(c, "zonemind")["stats"]
            rep = ", ".join(f"{k} {v}" for k, v in sorted(s["repairs_by_constraint"].items(), key=lambda kv: -kv[1]))
            rows.append([cfg.climates[c].label, s["decisions"], f"{100 * s['grounded_decisions'] / s['decisions']:.1f}%",
                         f"{s['citations'] / s['decisions']:.2f}", f"{s['recall_sum'] / max(s['recall_n'], 1):.3f}",
                         s["decisions_repaired"], rep or "none"])
        out += ["### Grounding and verification in the main runs", "", _table(
            ["Climate", "Decisions", "Grounded decisions", "Citations per decision", "Document recall",
             "Decisions repaired", "Repairs by constraint"], rows), ""]

    abl = _load("ablations.json")
    if abl and bench:
        full = {r["climate"]: r for r in bench if r["controller"] == "zonemind"}
        rows = [["Full agent", f"{np.mean([r['total_cost'] for r in full.values()]):,.0f}", "",
                 f"{np.mean([r['comfort_kh'] for r in full.values()]):.1f}",
                 f"{np.mean([r['stats']['recall_sum'] / r['stats']['recall_n'] for r in full.values()]):.3f}",
                 f"{np.mean([r['stats']['decisions_repaired'] for r in full.values()]):.0f}"]]
        for n, label in ABLATION_LABELS.items():
            rs = [r for r in abl if r["controller"] == n]
            delta = np.mean([100.0 * (r["total_cost"] / full[r["climate"]]["total_cost"] - 1.0) for r in rs])
            rec = np.mean([r["stats"]["recall_sum"] / max(r["stats"]["recall_n"], 1) for r in rs])
            rows.append([label, f"{np.mean([r['total_cost'] for r in rs]):,.0f}", f"{delta:+.1f}%",
                         f"{np.mean([r['comfort_kh'] for r in rs]):.1f}", f"{rec:.3f}",
                         f"{np.mean([r['stats']['decisions_repaired'] for r in rs]):.0f}"])
        out += ["### Ablations, mean of four climates", "", _table(
            ["Variant", "Mean annual bill", "Bill vs full agent", "Comfort violations K·h", "Document recall",
             "Decisions repaired by verifier"], rows), ""]
        rows = []
        for c in full:
            row = [cfg.climates[c].label, f"{full[c]['total_cost']:,.0f} / {full[c]['comfort_kh']:.1f}"]
            for n in ("zonemind_no_memory", "zonemind_cold_memory"):
                r = next(r for r in abl if r["controller"] == n and r["climate"] == c)
                row.append(f"{r['total_cost']:,.0f} / {r['comfort_kh']:.1f}")
            rows.append(row)
        out += ["### Episodic memory by climate (annual bill / comfort violations K·h)", "", _table(
            ["Climate", "Commissioned memory", "No memory", "Memory without commissioning"], rows), ""]

    rob = _load("robustness.json")
    if rob:
        rows = []
        for r in rob:
            s = r["stats"]
            rows.append([r["controller"].replace("_", " "), sum(r.get("injected_faults", {}).values()), s["parse_failures"],
                         s["repairs"], s["ungrounded_citations"], s["unsafe_commands"], s["unsafe_decisions"],
                         f"{r['comfort_kh']:.1f}", f"{r['unmet_hours']:.1f}", f"{r['total_cost']:,.0f}"])
        out += [f"### Fault injection ({rob[0]['climate']})", "", _table(
            ["Variant", "Faults injected", "Parse failures recovered", "Verifier repairs", "Invented citations flagged",
             "Limit breaking commands at plant", "Decisions affected", "Comfort violations K·h", "Unmet zone hours",
             "Annual bill"], rows), ""]

    ret = _load("retrieval_eval.json")
    if ret:
        ks = sorted({r["k"] for r in ret})
        rows = []
        for label in dict.fromkeys(r["retriever"] for r in ret):
            rows.append([label] + [f"{np.mean([r['recall'] for r in ret if r['retriever'] == label and r['k'] == k]):.3f}"
                                   for k in ks])
        n = sum(r["decisions"] for r in ret if r["retriever"] == "BM25" and r["k"] == ks[0])
        out += [f"### Retrieval recall of applicable documents ({n:,} decisions with at least one applicable document)", "",
                _table(["Retriever"] + [f"k={k}" for k in ks], rows), ""]

    bud = _load("retrieval_budget.json")
    if bud:
        rows = []
        for n in dict.fromkeys(r["controller"] for r in bud):
            rs = [r for r in bud if r["controller"] == n]
            rows.append([n.replace("_", " "), f"{np.mean([r['stats']['recall_sum'] / max(r['stats']['recall_n'], 1) for r in rs]):.3f}",
                         f"{np.mean([r['total_cost'] for r in rs]):,.0f}", f"{np.mean([r['hvac_kwh'] for r in rs]):,.0f}",
                         f"{np.mean([r['comfort_kh'] for r in rs]):.1f}",
                         f"{np.mean([r['stats']['decisions_repaired'] for r in rs]):.0f}"])
        out += [f"### Tight retrieval budget (k={bud[0]['k']}), mean of {len({r['climate'] for r in bud})} climates, no memory", "",
                _table(["Retriever", "Document recall", "Mean annual bill", "HVAC kWh", "Comfort violations K·h",
                        "Decisions repaired by verifier"], rows), ""]

    sens = _load("knob_sensitivity.json")
    if sens:
        rows = []
        for c in dict.fromkeys(r["climate"] for r in sens):
            for knob in dict.fromkeys(r["knob"] for r in sens):
                rs = [r for r in sens if r["climate"] == c and r["knob"] == knob]
                base = next(r for r in rs if r["is_default"])
                cells = ", ".join(f"{r['value']}: {100.0 * (r['score'] / base['score'] - 1.0):+.2f}%" for r in rs)
                rows.append([cfg.climates[c].label, knob, cells])
        out += ["### Knob sensitivity: change in annual score when one knob is held at each value", "",
                _table(["Climate", "Knob", "Score change vs default"], rows), ""]

    text = "\n".join(out)
    (repo_root() / "results" / "summary.md").write_text(text, encoding="utf-8")
    return text
