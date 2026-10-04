"""Solar geometry: irradiance on vertical facades from horizontal measurements."""
from __future__ import annotations

import numpy as np

# Facade azimuth measured from south, positive toward west (degrees).
FACADE_AZIMUTH = {"south": 0.0, "west": 90.0, "north": 180.0, "east": -90.0}


def sun_position(t_hours: np.ndarray, lat: float, lon: float, tz: float) -> tuple[np.ndarray, np.ndarray]:
    """Return solar altitude and azimuth (radians, azimuth from south, west positive).

    ``t_hours`` is local standard time in hours since the start of the year.
    """
    day = np.floor(t_hours / 24.0) + 1.0
    clock = t_hours % 24.0
    b = np.radians(360.0 * (day - 81.0) / 364.0)
    eot = 9.87 * np.sin(2 * b) - 7.53 * np.cos(b) - 1.5 * np.sin(b)           # minutes
    solar_time = clock + (4.0 * (lon - 15.0 * tz) + eot) / 60.0
    decl = np.radians(23.45) * np.sin(np.radians(360.0 * (284.0 + day) / 365.0))
    omega = np.radians(15.0 * (solar_time - 12.0))
    phi = np.radians(lat)
    sin_alt = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(omega)
    alt = np.arcsin(np.clip(sin_alt, -1.0, 1.0))
    cos_az = (np.sin(alt) * np.sin(phi) - np.sin(decl)) / np.maximum(np.cos(alt) * np.cos(phi), 1e-6)
    az = np.sign(omega) * np.arccos(np.clip(cos_az, -1.0, 1.0))
    return alt, az


def vertical_irradiance(t_hours, lat, lon, tz, dni, dhi, ghi, orientation: str, rho: float = 0.2):
    """Total irradiance (W/m2) on a vertical facade: beam, sky diffuse and ground reflected."""
    if orientation not in FACADE_AZIMUTH:
        return np.zeros_like(np.asarray(dni, dtype=float))
    alt, az = sun_position(np.asarray(t_hours, dtype=float), lat, lon, tz)
    gamma = np.radians(FACADE_AZIMUTH[orientation])
    cos_inc = np.cos(alt) * np.cos(az - gamma)
    beam = np.where((alt > 0) & (cos_inc > 0), dni * cos_inc, 0.0)
    return beam + 0.5 * dhi + 0.5 * rho * ghi
