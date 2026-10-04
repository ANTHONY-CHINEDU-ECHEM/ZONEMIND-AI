"""Thermal comfort: the Fanger PMV and PPD indices and the seasonal operating mode."""
from __future__ import annotations

import numpy as np


def pmv_ppd(ta, tr, vel: float, rh: float, met: float, clo) -> tuple[np.ndarray, np.ndarray]:
    """Predicted Mean Vote and Predicted Percentage Dissatisfied (ISO 7730 method).

    Vectorised over air temperature ``ta``, mean radiant temperature ``tr`` and clothing
    insulation ``clo``. Returns arrays of PMV (roughly minus three to plus three) and
    PPD (percent of occupants expected to be dissatisfied, minimum five).
    """
    ta = np.asarray(ta, dtype=float)
    tr = np.asarray(tr, dtype=float)
    clo = np.broadcast_to(np.asarray(clo, dtype=float), ta.shape)
    pa = rh * 10.0 * np.exp(16.6536 - 4030.183 / (ta + 235.0))
    icl = 0.155 * clo
    m = met * 58.15
    fcl = np.where(icl <= 0.078, 1.0 + 1.29 * icl, 1.05 + 0.645 * icl)
    hcf = 12.1 * np.sqrt(vel)
    taa, tra = ta + 273.0, tr + 273.0
    tcla = taa + (35.5 - ta) / (3.5 * icl + 0.1)
    p1 = icl * fcl
    p2, p3, p4 = p1 * 3.96, p1 * 100.0, p1 * taa
    p5 = 308.7 - 0.028 * m + p2 * (tra / 100.0) ** 4
    xn, xf = tcla / 100.0, tcla / 50.0
    hc = np.full(ta.shape, hcf)
    for _ in range(60):  # fixed point iteration for clothing surface temperature
        xf = (xf + xn) / 2.0
        hcn = 2.38 * np.abs(100.0 * xf - taa) ** 0.25
        hc = np.maximum(hcf, hcn)
        xn = (p5 + p4 * hc - p2 * xf**4) / (100.0 + p3 * hc)
    tcl = 100.0 * xn - 273.0
    hl1 = 3.05e-3 * (5733.0 - 6.99 * m - pa)
    hl2 = 0.42 * (m - 58.15) if m > 58.15 else 0.0
    hl3 = 1.7e-5 * m * (5867.0 - pa)
    hl4 = 0.0014 * m * (34.0 - ta)
    hl5 = 3.96 * fcl * (xn**4 - (tra / 100.0) ** 4)
    hl6 = fcl * hc * (tcl - ta)
    ts = 0.303 * np.exp(-0.036 * m) + 0.028
    pmv = ts * (m - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)
    ppd = 100.0 - 95.0 * np.exp(-0.03353 * pmv**4 - 0.2179 * pmv**2)
    return pmv, ppd


def classify_mode(mean_c: float, max_c: float, thresholds) -> str:
    """Seasonal operating mode for a day, from its outdoor temperature outlook."""
    if mean_c >= thresholds.cooling_mean_c or max_c >= thresholds.cooling_max_c:
        return "cooling"
    if mean_c <= thresholds.heating_mean_c:
        return "heating"
    return "shoulder"
