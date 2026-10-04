"""Stochastic occupancy with an imperfect booking forecast.

Real offices do not follow the timetable programmed into the building management
system. Hybrid working means attendance swings by weekday, whole teams are sometimes
away, and booked spaces are sometimes never used. The generator reproduces those
patterns and, separately, the booking view an agent could see in advance.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calendar import Calendar


@dataclass
class Occupancy:
    actual: np.ndarray            # (n_steps, n_zones) fraction of design occupancy
    forecast_hourly: np.ndarray   # (n_hours, n_zones) booked fraction, peak within the hour
    attendance_daily: np.ndarray  # (n_days,) booked building attendance
    threshold: float

    def present(self, step: int) -> np.ndarray:
        return self.actual[step] >= self.threshold


def _profile(t: np.ndarray, arrive: float, depart: float, lunch: float) -> np.ndarray:
    """Trapezoid presence profile over the hours of one day."""
    up = np.clip(t - arrive, 0.0, 1.0)
    down = np.clip(depart - t, 0.0, 1.0)
    shape = np.minimum(up, down)
    return np.where((t >= 12.0) & (t < 13.0), shape * lunch, shape)


def generate_occupancy(cal: Calendar, zone_kinds: list[str], cfg, seed: int) -> Occupancy:
    o = cfg.occupancy
    rng = np.random.default_rng(seed)
    nz, sph = len(zone_kinds), cal.steps_per_hour
    spd = 24 * sph
    t_day = (np.arange(spd) + 0.5) / sph
    actual = np.zeros((cal.n_steps, nz))
    booked = np.zeros((cal.n_steps, nz))
    attendance = np.zeros(cal.n_days)

    for d in range(cal.n_days):
        rows = slice(d * spd, (d + 1) * spd)
        if cal.workday_daily[d]:
            base = np.clip(rng.normal(o.weekday_attendance[cal.weekday_daily[d]], o.attendance_sd), 0.1, 1.0)
            for z in range(nz):
                level = float(np.clip(base * rng.normal(1.0, o.zone_factor_sd), 0.05, 1.0))
                arrive = float(np.clip(rng.normal(o.arrival_mean_h, o.arrival_sd_h), 6.5, 10.0))
                depart = float(np.clip(rng.normal(o.departure_mean_h, o.departure_sd_h), 15.5, 20.0))
                draw = rng.random()
                known_absence = zone_kinds[z] != "core" and draw < o.zone_vacant_prob
                noshow = (not known_absence) and zone_kinds[z] != "core" and draw > 1.0 - o.noshow_prob
                level_fc = float(np.clip(level * rng.normal(1.0, o.forecast_noise), 0.05, 1.0))
                arrive_fc = arrive + rng.normal(0.0, o.forecast_time_sd_h)
                depart_fc = depart + rng.normal(0.0, o.forecast_time_sd_h)
                if not (known_absence or noshow):
                    actual[rows, z] = level * _profile(t_day, arrive, depart, o.lunch_factor)
                if not known_absence:
                    booked[rows, z] = level_fc * _profile(t_day, arrive_fc, depart_fc, o.lunch_factor)
        elif rng.random() < o.weekend_use_prob:
            z = int(rng.integers(nz))
            level = rng.uniform(0.15, 0.3)
            shape = level * _profile(t_day, 10.0, 15.0, 1.0)
            actual[rows, z] = shape
            if rng.random() < 0.5:   # half of weekend use is booked, the rest is walk in
                booked[rows, z] = shape
        attendance[d] = booked[rows].max(axis=0).mean()

    forecast_hourly = booked.reshape(cal.n_hours, sph, nz).max(axis=1)
    return Occupancy(actual=actual, forecast_hourly=forecast_hourly,
                     attendance_daily=attendance, threshold=o.presence_threshold)
