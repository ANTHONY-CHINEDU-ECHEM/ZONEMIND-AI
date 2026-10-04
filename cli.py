"""Command line interface for ZoneMind AI."""
from __future__ import annotations

import argparse
import json

from .config import load_config
from .eval import experiments
from .eval.runner import get_kb, make_controller, make_scenario, run


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", default=None, help="optional YAML file layered over configs/default.yaml")
    p.add_argument("--climates", nargs="*", default=None, help="subset of climates (default: all)")


def _climates(cfg, args) -> list[str]:
    return args.climates or list(cfg.climates)


def cmd_info(cfg, args) -> None:
    stats = get_kb().stats()
    print(json.dumps({"knowledge_base": stats, "climates": {k: v.label for k, v in cfg.climates.items()},
                      "zones": [z.name for z in cfg.building.zones], "backend": cfg.llm.backend}, indent=2))


def cmd_run(cfg, args) -> None:
    r = cfg.run
    climate = args.climate or r.climate
    name = args.controller or r.controller
    start_day = r.start_day if args.start_day is None else args.start_day
    days = r.days if args.days is None else args.days
    audit = args.audit or r.audit
    overrides = {"llm.backend": args.backend} if args.backend else {}
    scenario = make_scenario(cfg, climate)
    use_memory = (args.memory or r.memory) and name == "zonemind"
    memory = experiments.load_memory(cfg, climate) if use_memory else None
    controller = make_controller(name, cfg, memory=memory, overrides=overrides, audit_path=audit)
    result = run(scenario, controller, start_day=start_day, days=days)
    if hasattr(controller, "close"):
        controller.close()
    keep = ("controller", "climate", "days", "hvac_kwh", "total_kwh", "energy_cost", "hvac_energy_cost",
            "demand_cost", "total_cost", "peak_kw", "on_peak_kw", "comfort_kh", "unmet_hours", "in_band_pct",
            "ppd_mean", "stats")
    print(json.dumps({k: result[k] for k in keep if k in result}, indent=2, default=float))


def cmd_explain(cfg, args) -> None:
    """Print the full decision trace for one hour: what was retrieved, proposed and verified."""
    scenario = make_scenario(cfg, args.climate)
    overrides = {"llm.backend": args.backend} if args.backend else {}
    agent = make_controller("zonemind", cfg, memory=experiments.load_memory(cfg, args.climate), overrides=overrides)
    start = max(args.day - 3, 0)   # a short run in so the building state is realistic
    result = run(scenario, agent, start_day=start, days=args.day - start + 1, trace_days={args.day})
    print(json.dumps(result["traces"][args.hour], indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="zonemind", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    _add_common(sub.add_parser("info", help="describe the knowledge base and configuration"))
    p = sub.add_parser("run", help="simulate one controller in one climate")
    _add_common(p)
    p.add_argument("--climate", default=None)
    p.add_argument("--controller", default=None, help="fixed, scheduled, scheduled_tou or zonemind")
    p.add_argument("--backend", default=None, help="offline, anthropic, openai_compatible or chaos")
    p.add_argument("--start-day", type=int, default=None)
    p.add_argument("--days", type=int, default=None)
    p.add_argument("--memory", action="store_true", help="attach the commissioned episodic memory")
    p.add_argument("--audit", default=None, help="write every decision trace to this JSONL file")
    p = sub.add_parser("explain", help="show the decision trace for one hour")
    _add_common(p)
    p.add_argument("--climate", default="chicago")
    p.add_argument("--day", type=int, default=196, help="day of year, from zero")
    p.add_argument("--hour", type=int, default=14)
    p.add_argument("--backend", default=None)
    for name, text in (("benchmark", "baselines against the agent in every climate"),
                       ("ablations", "remove one component at a time"),
                       ("robustness", "fault injection with and without the verifier"),
                       ("retrieval", "recall of applicable documents per retriever"),
                       ("sensitivity", "hold each strategy knob fixed for a year"),
                       ("budget", "rerun with a tight retrieval budget of four documents"),
                       ("figures", "render every figure from saved results"),
                       ("report", "write results/summary.md from saved results"),
                       ("all", "run every experiment, then render figures")):
        _add_common(sub.add_parser(name, help=text))

    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    if args.command == "info":
        cmd_info(cfg, args)
    elif args.command == "run":
        cmd_run(cfg, args)
    elif args.command == "explain":
        cmd_explain(cfg, args)
    else:
        climates = _climates(cfg, args)
        if args.command in ("benchmark", "all"):
            experiments.benchmark(cfg, climates)
        if args.command in ("ablations", "all"):
            experiments.ablations(cfg, climates)
        if args.command in ("robustness", "all"):
            experiments.robustness(cfg, climates[0])
        if args.command in ("retrieval", "all"):
            experiments.retrieval_eval(cfg, climates)
        if args.command in ("sensitivity", "all"):
            experiments.knob_sensitivity(cfg, climates)
        if args.command in ("budget", "all"):
            experiments.retrieval_budget(cfg, climates)
        if args.command in ("figures", "all"):
            from .eval.plots import make_all_figures
            make_all_figures(cfg)
        if args.command in ("report", "all"):
            from .eval.report import summarise
            summarise(cfg)
            print("summary written to results/summary.md")


if __name__ == "__main__":
    main()
