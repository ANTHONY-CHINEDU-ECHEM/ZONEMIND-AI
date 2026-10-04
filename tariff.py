"""Electricity tariff: time of use energy rates, a demand charge and critical peak events."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .calendar import Calendar
from .weather import Weather

OFF, MID, PEAK, CRITICAL = 0, 1, 2, 3
PERIOD_NAMES = {OFF: "off", MID: "mid", PEAK: "peak", CRITICAL: "critical"}


@dataclass
class Tariff:
    period_hourly: np.ndarray   # (n_hours,) period code
    price_hourly: np.ndarray    # (n_hours,) currency per kWh
    critical_days: np.ndarray   # (n_days,) bool
    demand_anytime: float       # per kW of the monthly maximum demand
    demand_peak: float          # per kW of the monthly maximum demand inside peak windows
    steps_per_hour: int

    def price_steps(self) -> np.ndarray:
        return np.repeat(self.price_hourly, self.steps_per_hour)

    def hours_until(self, hour_idx: int, codes: tuple[int, ...], horizon: int = 24) -> int:
        """Hours until the next period in ``codes`` begins; zero while inside one, 99 if none."""
        window = self.period_hourly[hour_idx: hour_idx + horizon]
        hits = np.flatnonzero(np.isin(window, codes))
        return int(hits[0]) if hits.size else 99

    def quarter_demand(self, total_kw: np.ndarray, cal: Calendar, s0: int = 0):
        """Quarter hour average demand with the month and peak flag of each quarter."""
        per_quarter = max(1, 900 // cal.dt)
        n = len(total_kw) // per_quarter * per_quarter
        kw = total_kw[:n].reshape(-1, per_quarter).mean(axis=1)
        month = cal.month[s0: s0 + n: per_quarter]
        on_peak = np.repeat(self.period_hourly, self.steps_per_hour)[s0: s0 + n: per_quarter] >= PEAK
        return kw, month, on_peak

    def day_demand_cost(self, total_kw: np.ndarray, cal: Calendar, s0: int) -> tuple[float, float, float]:
        """One day's demand charges amortised over a month of 21 working days.

        Returns the amortised cost, the day's maximum demand and its maximum on peak demand.
        """
        kw, _, on_peak = self.quarter_demand(total_kw, cal, s0)
        peak_any = float(kw.max())
        peak_on = float(kw[on_peak].max()) if on_peak.any() else 0.0
        return (self.demand_anytime * peak_any + self.demand_peak * peak_on) / 21.0, peak_any, peak_on

    def bill(self, total_kw: np.ndarray, cal: Calendar, s0: int = 0, hvac_kw: np.ndarray | None = None) -> dict:
        """Compute the bill for the metered load starting at step ``s0``.

        Demand charges for a partly simulated month are prorated by the share simulated.
        """
        dt_h = cal.dt / 3600.0
        price = self.price_steps()[s0: s0 + len(total_kw)]
        energy_steps = total_kw * dt_h * price
        kw, month, on_peak = self.quarter_demand(total_kw, cal, s0)
        per_quarter = max(1, 900 // cal.dt)
        step_month = cal.month[s0: s0 + len(total_kw)]
        monthly_any, monthly_on, monthly_energy = {}, {}, {}
        demand_cost = 0.0
        for m in np.unique(month):
            sel = month == m
            share = sel.sum() * per_quarter / (cal.month == m).sum()
            monthly_any[int(m)] = float(kw[sel].max())
            monthly_on[int(m)] = float(kw[sel & on_peak].max()) if (sel & on_peak).any() else 0.0
            monthly_energy[int(m)] = float(energy_steps[step_month == m].sum())
            demand_cost += share * (self.demand_anytime * monthly_any[int(m)] + self.demand_peak * monthly_on[int(m)])
        out = {
            "energy_cost": float(energy_steps.sum()), "demand_cost": float(demand_cost),
            "total_cost": float(energy_steps.sum() + demand_cost),
            "peak_kw": float(kw.max()), "on_peak_kw": float(kw[on_peak].max()) if on_peak.any() else 0.0,
            "monthly_peak_kw": monthly_any, "monthly_on_peak_kw": monthly_on,
            "monthly_energy_cost": monthly_energy,
        }
        if hvac_kw is not None:
            out["hvac_energy_cost"] = float((hvac_kw * dt_h * price).sum())
        return out


def build_tariff(cal: Calendar, weather: Weather, cfg) -> Tariff:
    t = cfg.tariff
    period = np.zeros(cal.n_hours, dtype=int)
    price = np.zeros(cal.n_hours)
    hours = np.arange(24)
    daily_max = weather.hourly_t.reshape(cal.n_days, 24).max(axis=1)
    summer = np.isin(cal.month_daily, t.summer_months)

    for d in range(cal.n_days):
        season = t.summer if summer[d] else t.winter
        codes = np.full(24, OFF)
        if cal.workday_daily[d]:
            for lo, hi in season.mid_hours:
                codes[(hours >= lo) & (hours < hi)] = MID
            codes[(hours >= season.peak_hours[0]) & (hours < season.peak_hours[1])] = PEAK
        rates = np.array([season.rate_off, season.rate_mid, season.rate_peak])[codes]
        period[d * 24:(d + 1) * 24], price[d * 24:(d + 1) * 24] = codes, rates

    # Critical peak events: the hottest summer working days, announced a day ahead.
    critical_days = np.zeros(cal.n_days, dtype=bool)
    eligible = np.flatnonzero(summer & cal.workday_daily)
    if eligible.size:
        threshold = np.percentile(daily_max[eligible], t.critical.percentile)
        hot = eligible[daily_max[eligible] >= threshold]
        hot = hot[np.argsort(daily_max[hot])[::-1][: t.critical.max_events]]
        critical_days[hot] = True
        for d in hot:
            rows = d * 24 + np.arange(t.critical.hours[0], t.critical.hours[1])
            period[rows], price[rows] = CRITICAL, t.critical.price
    return Tariff(period_hourly=period, price_hourly=price, critical_days=critical_days,
                  demand_anytime=t.demand_anytime_per_kw, demand_peak=t.demand_peak_per_kw,
                  steps_per_hour=cal.steps_per_hour)
