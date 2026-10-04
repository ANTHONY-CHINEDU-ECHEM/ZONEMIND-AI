"""Figures for the README, rendered from saved experiment results."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from ..config import repo_root

COLORS = {"fixed": "#9aa0a6", "scheduled": "#4c78a8", "scheduled_tou": "#f58518", "zonemind": "#1b9e77"}
LABELS = {"fixed": "Fixed setpoints", "scheduled": "Timetable", "scheduled_tou": "Timetable with tariff rules",
          "zonemind": "ZoneMind AI"}
ABLATION_LABELS = {
    "zonemind_no_memory": "No episodic memory", "zonemind_cold_memory": "Memory without commissioning",
    "zonemind_bm25_only": "BM25 retrieval only", "zonemind_dense_only": "Dense retrieval only",
    "zonemind_single_query": "No query decomposition", "zonemind_no_retrieval": "No retrieval",
}
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 140, "savefig.bbox": "tight"})


def _load(name: str):
    path = repo_root() / "results" / name
    return json.loads(path.read_text()) if path.exists() else None


def _out(name: str) -> Path:
    folder = repo_root() / "docs" / "figures"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


def _short(cfg, climate: str) -> str:
    return cfg.climates[climate].label.split(" (")[0]


def fig_architecture() -> None:
    fig, ax = plt.subplots(figsize=(13, 6.4))
    ax.set_xlim(0, 12.8), ax.set_ylim(0.2, 6.6), ax.axis("off")

    def box(x, y, w, h, title, body, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=color, ec="#333333", lw=1.1))
        ax.text(x + w / 2, y + h - 0.2, title, ha="center", va="top", weight="bold", fontsize=10)
        ax.text(x + w / 2, y + h - 0.55, body, ha="center", va="top", fontsize=8.2, color="#222222")

    def path(points, label="", at=None, ha="center"):
        xs, ys = zip(*points[:-1]) if len(points) > 2 else ((), ())
        if len(points) > 2:
            ax.plot(list(xs), list(ys), color="#333333", lw=1.2, solid_capstyle="round")
        ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>", mutation_scale=13, lw=1.2,
                                     color="#333333", shrinkA=0, shrinkB=1))
        if label:
            ax.text(*at, label, ha=ha, va="center", fontsize=8, color="#444444")

    blue, cream, green, purple, red = "#e8eef7", "#fdf1dc", "#e3f4ec", "#f3e8f7", "#fbe3e1"
    box(0.1, 2.9, 2.0, 1.4, "Signals, forecasts", "zone sensors, demand\nweather, bookings\ntariff calendar", blue)
    box(2.5, 2.9, 1.7, 1.4, "Situation", "numeric state and\nplain language\nfacets", cream)
    box(4.6, 2.9, 1.8, 1.4, "Hybrid retriever", "BM25 and dense\nfacet coverage\nfusion", green)
    box(6.8, 2.9, 1.7, 1.4, "Reasoner", "language model or\ndeterministic\nfallback", cream)
    box(8.9, 2.9, 1.5, 1.4, "Verifier", "check, repair\nand audit", red)
    box(10.8, 2.9, 1.8, 1.4, "Building plant", "zone setpoints\nfor the next hour", blue)
    box(6.7, 5.0, 1.9, 1.2, "Episodic memory", "similar past days\nstrategy knob tuner", green)
    box(4.6, 0.6, 1.8, 1.4, "Knowledge base", "sequences, policies\ntariffs, playbooks\nprose and rules", purple)

    path([(2.1, 3.6), (2.5, 3.6)])
    path([(4.2, 3.6), (4.6, 3.6)], "facets", (4.4, 4.5))
    path([(6.4, 3.6), (6.8, 3.6)], "documents", (6.6, 4.5))
    path([(8.5, 3.6), (8.9, 3.6)], "proposal", (8.7, 4.5))
    path([(10.4, 3.6), (10.8, 3.6)], "verified\ncommands", (10.6, 4.6))
    path([(3.35, 4.3), (3.35, 5.6), (6.8, 5.6)], "day outlook", (5.0, 5.78))
    path([(7.65, 5.0), (7.65, 4.3)], "strategy knobs", (7.75, 4.74), ha="left")
    path([(11.7, 4.3), (11.7, 5.6), (8.5, 5.6)], "daily cost, demand and comfort", (10.1, 5.78))
    path([(5.5, 2.0), (5.5, 2.9)], "indexed chunks", (5.6, 2.45), ha="left")
    path([(6.4, 1.3), (9.65, 1.3), (9.65, 2.9)], "every hard constraint, on every decision", (8.0, 1.08))
    ax.set_title("ZoneMind AI decision loop", fontsize=13, weight="bold")
    fig.savefig(_out("architecture.png")), plt.close(fig)


def fig_benchmark(cfg) -> None:
    rows = _load("benchmark.json")
    if not rows:
        return
    climates = list(dict.fromkeys(r["climate"] for r in rows))
    panels = (("total_cost", "Annual electricity bill"), ("hvac_energy_cost", "HVAC energy cost"),
              ("comfort_kh", "Comfort violations (K·h)"), ("on_peak_kw", "Highest on peak demand (kW)"))
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2))
    width = 0.2
    for ax, (key, title) in zip(axes, panels):
        for j, name in enumerate(LABELS):
            vals = [next(r[key] for r in rows if r["climate"] == c and r["controller"] == name) for c in climates]
            ax.bar(np.arange(len(climates)) + (j - 1.5) * width, vals, width, color=COLORS[name],
                   label=LABELS[name] if key == "total_cost" else None)
        ax.set_xticks(np.arange(len(climates)), [_short(cfg, c).replace(" ", "\n") for c in climates], fontsize=9)
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    fig.legend(loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.07))
    fig.suptitle("One evaluation year per climate, identical weather, occupancy and tariff for every controller",
                 fontsize=11)
    fig.savefig(_out("benchmark.png")), plt.close(fig)


def fig_event_day(cfg, climate: str) -> None:
    path = repo_root() / "results" / f"event_day_{climate}.npz"
    if not path.exists():
        return
    d = np.load(path)
    n = len(d["zonemind__kw"])
    t = np.arange(n) * 24.0 / n
    period = d["zonemind__period"]
    names = [z.name for z in cfg.building.zones]
    zone = names.index("west")
    fig, axes = plt.subplots(3, 1, figsize=(10, 8.2), sharex=True)

    def shade(ax):
        for code, color, label in ((2, "#f58518", "Peak window"), (3, "#d62728", "Critical peak event")):
            mask = period == code
            if mask.any():
                ax.axvspan(t[mask][0], t[mask][-1] + 24.0 / n, color=color, alpha=0.13, label=label)

    ax = axes[0]
    shade(ax)
    ax.plot(t, d["zonemind__t_out"], color="#b23b3b", lw=1.6, label="Outdoor temperature")
    ax.set_ylabel("Outdoor (°C)")
    ax2 = ax.twinx()
    ax2.fill_between(t, d["zonemind__occ"].mean(axis=1) * 100, color="#888888", alpha=0.25, step="mid")
    ax2.set_ylabel("Occupancy (% of design)"), ax2.grid(False), ax2.set_ylim(0, 100)
    ax2.spines["right"].set_visible(True)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.set_title(f"A critical peak event day in {_short(cfg, climate)}: conditions")

    ax = axes[1]
    shade(ax)
    for name in ("scheduled", "zonemind"):
        ax.plot(t, d[f"{name}__ta"][:, zone], color=COLORS[name], lw=1.8, label=f"{LABELS[name]}: zone temperature")
        ax.plot(t, d[f"{name}__cool_sp"][:, zone], color=COLORS[name], lw=1.0, ls="--",
                label=f"{LABELS[name]}: cooling setpoint")
    ax.axhline(26.0, color="#444444", lw=0.8, ls=":")
    ax.text(0.2, 26.15, "occupied comfort limit", fontsize=7.5, color="#444444")
    ax.set_ylabel("West zone (°C)"), ax.set_ylim(21, 35.5)
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=7.5)
    ax.set_title("West zone temperature and cooling setpoint")

    ax = axes[2]
    shade(ax)
    for name in ("scheduled", "zonemind"):
        q = d[f"{name}__kw"].reshape(-1, 3).mean(axis=1)
        ax.step(np.arange(len(q)) / 4.0, q, where="post", color=COLORS[name], lw=1.6, label=LABELS[name])
    ax.set_ylabel("Building demand (kW)"), ax.set_xlabel("Hour of day")
    ax.set_xticks(range(0, 25, 3)), ax.set_xlim(0, 24)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.set_title("Metered building demand, quarter hour average")
    fig.savefig(_out(f"event_day_{climate}.png")), plt.close(fig)


def fig_ablation(cfg) -> None:
    abl, bench = _load("ablations.json"), _load("benchmark.json")
    if not abl or not bench:
        return
    full = {r["climate"]: r for r in bench if r["controller"] == "zonemind"}
    names = list(ABLATION_LABELS)
    bill = [np.mean([100.0 * (r["total_cost"] / full[r["climate"]]["total_cost"] - 1.0)
                     for r in abl if r["controller"] == n]) for n in names]
    comfort = [np.mean([r["comfort_kh"] - full[r["climate"]]["comfort_kh"] for r in abl if r["controller"] == n])
               for n in names]
    recall = [np.mean([r["stats"]["recall_sum"] / max(r["stats"]["recall_n"], 1) for r in abl if r["controller"] == n])
              if n != "zonemind_no_retrieval" else 0.0 for n in names]
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), sharey=True)
    y = np.arange(len(names))
    for ax, vals, title, fmt in ((axes[0], bill, "Change in annual bill vs full agent (%)", "{:+.1f}"),
                                 (axes[1], comfort, "Change in comfort violations vs full agent (K·h)", "{:+.1f}"),
                                 (axes[2], recall, "Recall of applicable documents", "{:.3f}")):
        colors = ["#c44e52" if v > 0 else "#1b9e77" for v in vals] if ax is not axes[2] else "#4c78a8"
        ax.barh(y, vals, color=colors)
        for yi, v in zip(y, vals):
            ax.text(v, yi, " " + fmt.format(v), va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
        ax.set_title(title, fontsize=10), ax.grid(axis="y", visible=False), ax.margins(x=0.18)
    axes[0].set_yticks(y, [ABLATION_LABELS[n] for n in names]), axes[0].invert_yaxis()
    fig.suptitle("Ablations, mean of four climates", fontsize=11, y=1.03)
    fig.savefig(_out("ablations.png")), plt.close(fig)


def fig_retrieval() -> None:
    rows = _load("retrieval_eval.json")
    if not rows:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9))
    styles = {"BM25": ("#4c78a8", "o"), "LSA dense": ("#f58518", "s"), "Hybrid, single query": ("#9aa0a6", "^"),
              "Hybrid, decomposed": ("#1b9e77", "D")}
    for ax, key, title in ((axes[0], "recall", "Recall of applicable documents"),
                           (axes[1], "full_coverage", "Share of decisions with every applicable document retrieved")):
        for label, (color, marker) in styles.items():
            ks = sorted({r["k"] for r in rows})
            vals = [np.mean([r[key] for r in rows if r["retriever"] == label and r["k"] == k]) for k in ks]
            ax.plot(ks, vals, color=color, marker=marker, lw=1.8, label=label)
        ax.set_xlabel("Documents retrieved per decision (k)"), ax.set_title(title, fontsize=10), ax.set_ylim(0.5, 1.02)
    axes[0].legend(frameon=False, fontsize=8.5)
    fig.savefig(_out("retrieval.png")), plt.close(fig)


def fig_robustness() -> None:
    rows = _load("robustness.json")
    if not rows:
        return
    labels = {"clean_with_verifier": "No faults\nverifier on", "faults_with_verifier": "Faults\ninjected\nverifier on",
              "faults_without_verifier": "Faults\ninjected\nverifier off"}
    colors = ["#1b9e77", "#4c78a8", "#c44e52"]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.2), gridspec_kw={"wspace": 0.42})
    by = {r["controller"]: r for r in rows}
    series = (("Commands breaking a hard limit\nthat reached the plant", [by[k]["stats"]["unsafe_commands"] for k in labels]),
              ("Comfort violations (K·h)", [by[k]["comfort_kh"] for k in labels]),
              ("Annual bill", [by[k]["total_cost"] for k in labels]))
    for ax, (title, vals) in zip(axes, series):
        ax.bar(range(3), vals, color=colors)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:,.0f}" if v >= 100 else f"{v:.1f}", ha="center", va="bottom", fontsize=9)
        ax.set_xticks(range(3), labels.values(), fontsize=8), ax.set_title(title, fontsize=10)
        ax.grid(axis="x", visible=False), ax.margins(y=0.15)
    faults = by["faults_with_verifier"].get("injected_faults", {})
    axes[3].barh([f.replace("_", " ") for f in faults], list(faults.values()), color="#9aa0a6")
    axes[3].set_title(f"Faults injected over the year ({sum(faults.values())} total)", fontsize=10)
    axes[3].grid(axis="y", visible=False), axes[3].tick_params(axis="y", labelsize=8)
    fig.savefig(_out("robustness.png")), plt.close(fig)


def fig_memory(cfg) -> None:
    sens, bench = _load("knob_sensitivity.json"), _load("benchmark.json")
    if not sens or not bench:
        return
    climates = list(dict.fromkeys(r["climate"] for r in sens))
    knobs = list(cfg.memory.knobs)
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    palette = ["#4c78a8", "#f58518", "#1b9e77", "#b279a2"]
    for ax, knob in zip(axes[0], knobs):
        values = list(cfg.memory.knobs[knob]["values"])
        for j, climate in enumerate(climates):
            base = next(r["score"] for r in sens if r["climate"] == climate and r["knob"] == knob and r["is_default"])
            delta = [100.0 * (next(r["score"] for r in sens if r["climate"] == climate and r["knob"] == knob
                                   and r["value"] == v) / base - 1.0) for v in values]
            ax.bar(np.arange(len(values)) + (j - 1.5) * 0.2, delta, 0.2, color=palette[j],
                   label=_short(cfg, climate) if knob == knobs[0] else None)
        ax.set_xticks(range(len(values)), [str(v) for v in values])
        ax.set_title(f"Knob '{knob}' held fixed all year:\nchange in annual score vs default (%)", fontsize=10)
        ax.axhline(0, color="#333333", lw=0.8), ax.grid(axis="x", visible=False)
    axes[0][0].legend(frameon=False, fontsize=8)
    for ax, knob in zip(axes[1], knobs):
        values = list(cfg.memory.knobs[knob]["values"])
        modes = ("heating", "shoulder", "cooling")
        log = [e for r in bench if r["controller"] == "zonemind" for e in r["knob_log"]]
        counts = Counter((e["mode"], e[knob]) for e in log)
        bottom = np.zeros(len(modes))
        for i, v in enumerate(values):
            share = np.array([counts[(m, v)] / max(sum(counts[(m, u)] for u in values), 1) for m in modes]) * 100
            ax.bar(modes, share, bottom=bottom, color=palette[i], label=str(v))
            bottom += share
        ax.set_title(f"What the tuner chose for '{knob}'\n(share of days, four climates pooled)", fontsize=10)
        ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08))
        ax.grid(axis="x", visible=False)
        ax.set_ylim(0, 100)
    fig.tight_layout()
    fig.savefig(_out("memory.png")), plt.close(fig)


def fig_monthly(cfg, climate: str) -> None:
    rows = _load("benchmark.json")
    if not rows:
        return
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
    x = np.arange(12)
    for j, name in enumerate(("scheduled", "scheduled_tou", "zonemind")):
        r = next(r for r in rows if r["climate"] == climate and r["controller"] == name)
        for ax, key in zip(axes, ("monthly_energy_cost", "monthly_peak_kw", "monthly_on_peak_kw")):
            ax.bar(x + (j - 1) * 0.27, [r[key][str(m)] for m in range(1, 13)], 0.27, color=COLORS[name],
                   label=LABELS[name] if key == "monthly_energy_cost" else None)
    for ax, title in zip(axes, ("Energy charge by month", "Highest demand at any time (kW)",
                                "Highest demand inside peak windows (kW)")):
        ax.set_xticks(x, months, fontsize=8), ax.set_title(title, fontsize=10), ax.grid(axis="x", visible=False)
    fig.legend(loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle(f"{_short(cfg, climate)}: where the bill comes from", fontsize=11, y=1.02)
    fig.savefig(_out(f"monthly_{climate}.png")), plt.close(fig)


def make_all_figures(cfg) -> None:
    fig_architecture()
    fig_benchmark(cfg)
    for climate in cfg.climates:
        fig_event_day(cfg, climate)
    fig_ablation(cfg)
    fig_retrieval()
    fig_robustness()
    fig_memory(cfg)
    for climate in ("chicago", "tampa"):
        fig_monthly(cfg, climate)
    print("figures written to", repo_root() / "docs" / "figures")
