"""Performance metrics for a simulated period: energy, bill, demand and comfort."""
from __future__ import annotations

import numpy as np

from ..data.calendar import Calendar
from ..data.tariff import Tariff
from ..sim.comfort import classify_mode, pmv_ppd
from ..sim.env import BuildingEnv


def day_modes(hourly_t: np.ndarray, cfg) -> list[str]:
    daily = hourly_t.reshape(-1, 24)
    return [classify_mode(d.mean(), d.max(), cfg.comfort.mode_thresholds) for d in daily]


def compute_metrics(env: BuildingEnv, tariff: Tariff, cal: Calendar, cfg, s0: int, s1: int) -> dict:
    dt_h = cal.dt / 3600.0
    c = cfg.comfort
    power = env.rec_power[s0:s1]
    total_kw = env.total_kw(s0, s1)
    bill = tariff.bill(total_kw, cal, s0, hvac_kw=power.sum(axis=1))

    ta = env.rec_ta[s0:s1].astype(float)
    tm = env.rec_tm[s0:s1].astype(float)
    present = env.occ.actual[s0:s1] >= env.occ.threshold
    lo, hi = c.band_c
    dev = np.maximum(np.maximum(lo - ta, ta - hi), 0.0) * present
    occupied_zone_hours = present.sum() * dt_h

    modes = day_modes(env.weather.hourly_t, cfg)
    clo_daily = np.array([c.clo[m] for m in modes])
    clo = clo_daily[cal.day[s0:s1]][:, None] * np.ones_like(ta)
    people = env.occ.actual[s0:s1] * env.model.design_people
    if present.any():
        _, ppd = pmv_ppd(ta[present], 0.5 * (ta[present] + tm[present]), c.air_speed,
                         c.relative_humidity, c.met, clo[present])
        ppd_mean = float(np.average(ppd, weights=people[present]))
    else:
        ppd_mean = float("nan")

    return {
        "cooling_kwh": float(power[:, 0].sum() * dt_h),
        "heating_kwh": float(power[:, 1].sum() * dt_h),
        "fan_kwh": float(power[:, 2].sum() * dt_h),
        "hvac_kwh": float(power.sum() * dt_h),
        "base_kwh": float(env.base_kw[s0:s1].sum() * dt_h),
        "total_kwh": float(total_kw.sum() * dt_h),
        "energy_cost": bill["energy_cost"], "hvac_energy_cost": bill["hvac_energy_cost"],
        "demand_cost": bill["demand_cost"], "total_cost": bill["total_cost"],
        "peak_kw": bill["peak_kw"], "on_peak_kw": bill["on_peak_kw"],
        "monthly_peak_kw": bill["monthly_peak_kw"], "monthly_on_peak_kw": bill["monthly_on_peak_kw"],
        "monthly_energy_cost": bill["monthly_energy_cost"],
        "comfort_kh": float(dev.sum() * dt_h),
        "unmet_hours": float((dev > c.unmet_threshold_k).sum() * dt_h),
        "occupied_zone_hours": float(occupied_zone_hours),
        "in_band_pct": float(100.0 * (1.0 - (dev > 0.0).sum() * dt_h / max(occupied_zone_hours, 1e-9))),
        "ppd_mean": ppd_mean,
    }
