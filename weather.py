"""Weather series on the simulation grid, with forecasts and a perturbed variant."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from .calendar import Calendar
from .epw import read_epw


@dataclass
class Weather:
    name: str
    label: str
    lat: float
    lon: float
    tz: float
    t_out: np.ndarray       # per step, C
    dew: np.ndarray         # per step, C
    ghi: np.ndarray         # per step, W/m2
    dni: np.ndarray
    dhi: np.ndarray
    hourly_t: np.ndarray    # per hour, C
    hourly_ghi: np.ndarray
    fc_error: np.ndarray    # per hour, unit variance forecast error process
    fc_sd: float
    fc_horizon: float

    def forecast(self, hour_idx: int, horizon: int) -> np.ndarray:
        """Outdoor temperature forecast for the next ``horizon`` hours, issued at ``hour_idx``.

        The error grows linearly with lead time up to ``fc_horizon`` hours, so the first
        hours are close to truth and the day ahead view is honestly uncertain.
        """
        idx = (hour_idx + np.arange(horizon)) % len(self.hourly_t)
        lead = np.minimum(np.arange(horizon) / self.fc_horizon, 1.0)
        return self.hourly_t[idx] + self.fc_sd * lead * self.fc_error[idx]


def _to_steps(hourly: np.ndarray, cal: Calendar) -> np.ndarray:
    centres = np.arange(len(hourly)) + 0.5
    t = (np.arange(cal.n_steps) + 0.5) * cal.dt / 3600.0
    return np.interp(t, centres, hourly, period=len(hourly))


def _ar1(n: int, rho: float, rng: np.random.Generator) -> np.ndarray:
    noise = rng.standard_normal(n) * np.sqrt(1.0 - rho**2)
    out = np.empty(n)
    out[0] = rng.standard_normal()
    for i in range(1, n):
        out[i] = rho * out[i - 1] + noise[i]
    return out


def load_weather(path: str | Path, name: str, label: str, cal: Calendar, cfg, seed: int) -> Weather:
    epw = read_epw(path)
    f = epw.frame
    rng = np.random.default_rng(seed)
    return Weather(
        name=name, label=label, lat=epw.latitude, lon=epw.longitude, tz=epw.timezone,
        t_out=_to_steps(f["dry_bulb"].to_numpy(), cal), dew=_to_steps(f["dew_point"].to_numpy(), cal),
        ghi=_to_steps(f["ghi"].to_numpy(), cal), dni=_to_steps(f["dni"].to_numpy(), cal),
        dhi=_to_steps(f["dhi"].to_numpy(), cal),
        hourly_t=f["dry_bulb"].to_numpy(), hourly_ghi=f["ghi"].to_numpy(),
        fc_error=_ar1(8760, 0.9, rng), fc_sd=cfg.forecast.weather_error_sd_c,
        fc_horizon=cfg.forecast.weather_error_horizon_h,
    )


def perturb(weather: Weather, cal: Calendar, seed: int, temp_sd: float = 2.0) -> Weather:
    """Create a statistically similar but different year from the same climate.

    Used for the commissioning year so the agent's memory is never trained on the exact
    weather it is later evaluated on. Each day receives a persistent temperature offset
    and a cloudiness factor.
    """
    rng = np.random.default_rng(seed)
    offset_daily = temp_sd * _ar1(cal.n_days, 0.7, rng)
    sun_daily = np.clip(1.0 + 0.2 * _ar1(cal.n_days, 0.5, rng), 0.5, 1.2)
    off_h, sun_h = np.repeat(offset_daily, 24), np.repeat(sun_daily, 24)
    off_s, sun_s = _to_steps(off_h, cal), _to_steps(sun_h, cal)
    return replace(
        weather, name=weather.name + "_commissioning",
        t_out=weather.t_out + off_s, dew=weather.dew + off_s,
        ghi=weather.ghi * sun_s, dni=weather.dni * sun_s, dhi=weather.dhi * sun_s,
        hourly_t=weather.hourly_t + off_h, hourly_ghi=weather.hourly_ghi * sun_h,
        fc_error=_ar1(8760, 0.9, rng),
    )
