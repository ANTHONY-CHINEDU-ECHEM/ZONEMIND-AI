"""Reader for EnergyPlus Weather (EPW) files.

EPW is the standard exchange format for typical meteorological year data. Each file has
eight header lines followed by 8,760 hourly records. Only the fields the simulator needs
are extracted; any EPW file from any location can be dropped into ``data/weather``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Zero based column positions defined by the EPW specification.
_COLS = {"month": 1, "day": 2, "hour": 3, "dry_bulb": 6, "dew_point": 7, "rel_hum": 8,
         "ghi": 13, "dni": 14, "dhi": 15, "wind_speed": 21}


@dataclass
class EpwData:
    city: str
    latitude: float
    longitude: float
    timezone: float
    elevation: float
    frame: pd.DataFrame  # 8,760 hourly rows


def read_epw(path: str | Path) -> EpwData:
    path = Path(path)
    with open(path, encoding="latin-1") as fh:
        header = fh.readline().strip().split(",")
    if header[0] != "LOCATION":
        raise ValueError(f"{path} does not look like an EPW file")
    raw = pd.read_csv(path, skiprows=8, header=None, encoding="latin-1")
    frame = pd.DataFrame({name: raw.iloc[:, idx].astype(float) for name, idx in _COLS.items()})
    # Drop a leap day if present so every file is exactly one 365 day year.
    frame = frame[~((frame["month"] == 2) & (frame["day"] == 29))].reset_index(drop=True)
    if len(frame) != 8760:
        raise ValueError(f"{path} has {len(frame)} hourly rows, expected 8760")
    for col in ("ghi", "dni", "dhi"):
        frame[col] = np.where(frame[col] >= 9999, 0.0, frame[col]).clip(min=0.0)
    return EpwData(
        city=header[1], latitude=float(header[6]), longitude=float(header[7]),
        timezone=float(header[8]), elevation=float(header[9]), frame=frame,
    )
