"""Baseline controllers the agent is measured against.

``fixed`` holds comfort setpoints at all times. ``scheduled`` is the timetable most
building management systems run: comfort during fixed working hours, set back
otherwise. ``scheduled_tou`` adds hand written tariff rules on top, which is what a
diligent energy manager would configure without any adaptive layer.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..llm.schema import ZoneCommand
from .situation import Situation


@dataclass
class Decision:
    commands: dict[str, ZoneCommand]
    trace: dict | None = None


class BaselineController:
    def __init__(self, name: str, cfg):
        if name not in ("fixed", "scheduled", "scheduled_tou"):
            raise ValueError(f"unknown baseline '{name}'")
        self.name, self.b = name, cfg.baselines
        self.stats: dict = {}

    def _setpoints(self, s: Situation) -> tuple[float, float]:
        b = self.b
        if self.name == "fixed":
            return b.fixed.heat, b.fixed.cool
        sched = b.scheduled
        if not (s.is_workday and sched.start_hour <= s.hour < sched.end_hour):
            return sched.setback_heat, sched.setback_cool
        heat, cool = sched.heat, sched.cool
        if self.name == "scheduled_tou" and s.mode == "cooling":
            t = b.scheduled_tou
            if s.tariff == "critical":
                cool = t.critical_cool
            elif s.tariff == "peak":
                cool = t.peak_cool
            elif 0 < s.h_to_peak <= t.precool_hours:
                cool = t.precool_cool
        return heat, cool

    def decide(self, s: Situation) -> Decision:
        heat, cool = self._setpoints(s)
        return Decision({z.name: ZoneCommand(heat=heat, cool=cool) for z in s.zones})

    def end_of_day(self, day: int, summary: dict) -> None:
        return None
