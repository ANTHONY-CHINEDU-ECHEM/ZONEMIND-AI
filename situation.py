"""The agent's view of the building at a decision point.

A ``Situation`` contains only what a real supervisory controller could know: sensor
readings, the weather forecast, the booking forecast, the tariff calendar and the
metered demand so far. It never exposes the simulator's internal state or the true
future.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..data.calendar import Calendar
from ..data.occupancy import Occupancy
from ..data.tariff import CRITICAL, PEAK, PERIOD_NAMES, Tariff
from ..data.weather import Weather
from ..sim.comfort import classify_mode
from ..sim.env import BuildingEnv


@dataclass
class ZoneState:
    name: str
    orientation: str
    kind: str
    t_zone: float
    occupied: bool
    h_to_occ: int
    h_to_vacant: int
    noshow_h: int
    prev_heat: float
    prev_cool: float


@dataclass
class Situation:
    step: int
    hour_idx: int
    day: int
    stamp: str
    hour: int
    weekday: int
    is_monday: bool
    is_workday: bool
    mode: str
    tariff: str
    h_to_peak: int
    dr_today: bool
    h_to_dr: int
    t_out: float
    t_out_max_6h: float
    t_out_max_24h: float
    t_out_min_12h: float
    econ_ok: bool
    demand_ratio: float
    demand_kw: float
    month_peak_kw: float
    outlook: dict
    zones: list[ZoneState] = field(default_factory=list)

    def building_vars(self) -> dict:
        return {
            "mode": self.mode, "tariff": self.tariff, "h_to_peak": self.h_to_peak, "dr_today": self.dr_today,
            "h_to_dr": self.h_to_dr, "t_out": self.t_out, "t_out_max_6h": self.t_out_max_6h,
            "t_out_max_24h": self.t_out_max_24h, "t_out_min_12h": self.t_out_min_12h, "econ_ok": self.econ_ok,
            "demand_ratio": self.demand_ratio, "hour": self.hour, "weekday": self.weekday,
            "is_monday": self.is_monday, "is_workday": self.is_workday,
        }

    def zone_context(self, zone: ZoneState, knob_vars: dict) -> dict:
        """All variables a directive or constraint may reference for one zone."""
        ctx = self.building_vars()
        ctx.update(knob_vars)
        ctx.update(occupied=zone.occupied, h_to_occ=zone.h_to_occ, h_to_vacant=zone.h_to_vacant,
                   noshow_h=zone.noshow_h, t_zone=zone.t_zone, orientation=zone.orientation,
                   kind=zone.kind, prev_heat=zone.prev_heat, prev_cool=zone.prev_cool,
                   heat=zone.prev_heat, cool=zone.prev_cool)
        return ctx

    def to_prompt(self) -> dict:
        """Compact, rounded view for a language model prompt or an audit record."""
        b = self.building_vars()
        b = {k: (round(v, 1) if isinstance(v, float) else v) for k, v in b.items()}
        b.update(time=self.stamp, demand_kw=round(self.demand_kw, 1), month_peak_kw=round(self.month_peak_kw, 1))
        zones = {z.name: {"t_zone": round(z.t_zone, 1), "occupied": z.occupied, "h_to_occ": z.h_to_occ,
                          "h_to_vacant": z.h_to_vacant, "noshow_h": z.noshow_h, "orientation": z.orientation,
                          "kind": z.kind, "prev_heat": z.prev_heat, "prev_cool": z.prev_cool}
                 for z in self.zones}
        return {"building": b, "zones": zones}


def knob_variables(knobs: dict, cfg) -> dict:
    """Translate the named strategy knobs into the numeric variables directives use."""
    m = cfg.memory
    out = {"start_lead": int(knobs["start_lead"])}
    out.update(m.peak_strategy_map[knobs["peak_strategy"]])
    out.update(m.setback_map[knobs["setback"]])
    return out


def default_knobs(cfg) -> dict:
    return {name: spec.default for name, spec in cfg.memory.knobs.items()}


class SituationBuilder:
    def __init__(self, cfg, cal: Calendar, weather: Weather, occ: Occupancy, tariff: Tariff, env: BuildingEnv):
        self.cfg, self.cal, self.weather, self.occ, self.tariff, self.env = cfg, cal, weather, occ, tariff, env
        n = env.model.n
        self.noshow = np.zeros(n, dtype=int)
        self.prev_heat = np.full(n, float(cfg.agent.safe_default.heat))
        self.prev_cool = np.full(n, float(cfg.agent.safe_default.cool))
        self.month, self.month_peak, self.last_month_peak, self.demand_kw = 0, 0.0, 0.0, 0.0
        self._day_cache: dict[int, tuple[str, dict]] = {}

    def _day_outlook(self, day: int) -> tuple[str, dict]:
        if day not in self._day_cache:
            fc = self.weather.forecast(day * 24, 24)
            mode = classify_mode(float(fc.mean()), float(fc.max()), self.cfg.comfort.mode_thresholds)
            outlook = {
                "t_max": float(fc.max()), "t_min": float(fc.min()), "t_mean": float(fc.mean()),
                "ghi_mean": float(self.weather.hourly_ghi[day * 24: day * 24 + 24].mean()),
                "attendance": float(self.occ.attendance_daily[day]),
                "is_monday": bool(self.cal.weekday_daily[day] == 0),
                "dr_today": bool(self.tariff.critical_days[day]), "mode": mode,
            }
            self._day_cache[day] = (mode, outlook)
        return self._day_cache[day]

    def observe(self, s0: int, s1: int, heat, cool) -> None:
        """Update metered demand and remembered setpoints after a block has been simulated."""
        per_quarter = max(1, 900 // self.cal.dt)
        kw = self.env.total_kw(s0, s1)
        quarters = kw[: len(kw) // per_quarter * per_quarter].reshape(-1, per_quarter).mean(axis=1)
        month = int(self.cal.month[s0])
        if month != self.month:
            self.last_month_peak, self.month_peak, self.month = self.month_peak, 0.0, month
        self.demand_kw = float(quarters.max())
        self.month_peak = max(self.month_peak, self.demand_kw)
        self.prev_heat, self.prev_cool = np.asarray(heat, float).copy(), np.asarray(cool, float).copy()

    def build(self, step: int) -> Situation:
        cal, m = self.cal, self.env.model
        h = cal.hour_index(step)
        day, hour = h // 24, h % 24
        mode, outlook = self._day_outlook(day)
        fc = self.weather.forecast(h, 24)
        period = int(self.tariff.period_hourly[h])
        thr = self.occ.threshold
        present = self.occ.present(step)
        booked = self.occ.forecast_hourly[h: h + 24] >= thr          # (<=24, n_zones)
        reference_peak = max(self.month_peak, 0.8 * self.last_month_peak, 10.0)

        zones = []
        for i, name in enumerate(m.names):
            col = booked[:, i]
            hits = np.flatnonzero(col)
            h_to_occ = int(hits[0]) if hits.size else 99
            if col.size and col[0]:
                gaps = np.flatnonzero(~col)
                h_to_vacant = int(gaps[0]) if gaps.size else int(col.size)
            else:
                h_to_vacant = 0
            if not present[i] and h_to_occ == 0:
                self.noshow[i] += 1
            else:
                self.noshow[i] = 0
            zones.append(ZoneState(
                name=name, orientation=m.orientations[i], kind=m.kinds[i], t_zone=float(self.env.air_temp[i]),
                occupied=bool(present[i]), h_to_occ=h_to_occ, h_to_vacant=h_to_vacant,
                noshow_h=int(self.noshow[i]) - 1 if self.noshow[i] else 0,
                prev_heat=float(self.prev_heat[i]), prev_cool=float(self.prev_cool[i]),
            ))
        return Situation(
            step=step, hour_idx=h, day=day, stamp=cal.stamp(step).strftime("%a %d %b %H:%M"), hour=hour,
            weekday=int(cal.weekday_daily[day]), is_monday=bool(cal.weekday_daily[day] == 0),
            is_workday=bool(cal.workday_daily[day]), mode=mode, tariff=PERIOD_NAMES[period],
            h_to_peak=self.tariff.hours_until(h, (PEAK, CRITICAL)),
            dr_today=bool(self.tariff.critical_days[day]), h_to_dr=self.tariff.hours_until(h, (CRITICAL,)),
            t_out=float(self.weather.t_out[step]), t_out_max_6h=float(fc[:6].max()),
            t_out_max_24h=float(fc.max()), t_out_min_12h=float(fc[:12].min()),
            econ_ok=bool(self.env.econ_ok[step]), demand_ratio=self.demand_kw / reference_peak,
            demand_kw=self.demand_kw, month_peak_kw=self.month_peak, outlook=outlook, zones=zones,
        )
