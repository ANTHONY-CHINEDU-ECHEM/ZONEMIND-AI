"""Simulation calendar: maps integration steps to hours, weekdays, months and holidays."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Calendar:
    dt: int                    # seconds per step
    steps_per_hour: int
    n_steps: int
    n_hours: int
    n_days: int
    hour_of_day: np.ndarray    # per step, fractional hour at the step midpoint
    day: np.ndarray            # per step, day index from zero
    weekday_daily: np.ndarray  # per day, Monday is zero
    month_daily: np.ndarray    # per day, January is one
    workday_daily: np.ndarray  # per day, True on working days
    dates: pd.DatetimeIndex    # per day

    @property
    def month(self) -> np.ndarray:
        return self.month_daily[self.day]

    def hour_index(self, step: int) -> int:
        return step // self.steps_per_hour

    def stamp(self, step: int) -> pd.Timestamp:
        return self.dates[0] + pd.Timedelta(seconds=int(step) * self.dt)


def build_calendar(year: int, dt: int, holidays: list[str]) -> Calendar:
    dates = pd.date_range(f"{year}-01-01", periods=365, freq="D")
    steps_per_hour = 3600 // dt
    n_hours = 365 * 24
    n_steps = n_hours * steps_per_hour
    t_hours = (np.arange(n_steps) + 0.5) * dt / 3600.0
    holiday_set = set(holidays)
    is_holiday = np.array([d.strftime("%m-%d") in holiday_set for d in dates])
    weekday = dates.weekday.to_numpy()
    return Calendar(
        dt=dt, steps_per_hour=steps_per_hour, n_steps=n_steps, n_hours=n_hours, n_days=365,
        hour_of_day=t_hours % 24.0, day=(t_hours // 24).astype(int),
        weekday_daily=weekday, month_daily=dates.month.to_numpy(),
        workday_daily=(weekday < 5) & ~is_holiday, dates=dates,
    )
