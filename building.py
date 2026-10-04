"""Thermal model of the building: a resistance and capacitance network.

Each zone has two temperature states. The air node responds within minutes and is what
occupants and thermostats sense. The mass node represents slabs, walls and furniture,
responds over hours, and is what makes pre cooling and night flushing worthwhile. The
linear network is integrated with an implicit (backward Euler) step, which is
unconditionally stable, so the transition matrix is inverted once and reused.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

AIR_RHO_CP = 1206.0  # J/m3K, volumetric heat capacity of air


@dataclass
class BuildingModel:
    names: list[str]
    orientations: list[str]
    kinds: list[str]
    area: np.ndarray
    window: np.ndarray
    design_people: np.ndarray
    c_air: np.ndarray
    c_mass: np.ndarray
    ua_env: np.ndarray        # air node to outdoors (glazing and infiltration)
    ua_mass_out: np.ndarray   # mass node to outdoors (walls and roof)
    ua_am: np.ndarray         # air node to mass node
    cool_cap: np.ndarray      # W thermal
    heat_cap: np.ndarray
    fan_rated: np.ndarray     # W electric
    g_econ: np.ndarray        # W/K of outdoor air at full flow
    M: np.ndarray             # (2n, 2n) implicit transition matrix
    Mq: np.ndarray            # (2n, n) response of all states to heat injected at air nodes
    sens: np.ndarray          # (n,) K of air temperature per W over one step
    bout_dt: np.ndarray       # (2n,) outdoor coupling times dt
    dt_c_air: np.ndarray
    dt_c_mass: np.ndarray

    @property
    def n(self) -> int:
        return len(self.names)


def build_model(cfg, dt: int) -> BuildingModel:
    b, env, plant = cfg.building, cfg.building.envelope, cfg.plant
    zones = b.zones
    n = len(zones)
    area = np.array([z.area_m2 for z in zones], dtype=float)
    window = np.array([z.window_m2 for z in zones], dtype=float)
    kinds = [z.kind for z in zones]
    volume = area * b.ceiling_height_m
    infil = AIR_RHO_CP * env.infiltration_ach * volume / 3600.0
    is_core = np.array([k == "core" for k in kinds])

    c_air = AIR_RHO_CP * volume * env.air_capacity_multiplier
    c_mass = env.mass_capacity_kj_m2k * 1000.0 * area
    ua_am = env.air_mass_coupling_w_m2k * area
    ua_env = env.window_u * window + np.where(is_core, 0.3 * infil, infil)
    ua_mass_out = env.wall_u * env.wall_to_window_ratio * window + env.roof_u * area

    # Perimeter zones exchange heat with the core through internal partitions.
    ua_zone = np.zeros((n, n))
    if is_core.any():
        core = int(np.flatnonzero(is_core)[0])
        for i in range(n):
            if i != core:
                ua_zone[i, core] = ua_zone[core, i] = env.partition_ua_w_k

    a = np.zeros((2 * n, 2 * n))
    bout = np.zeros(2 * n)
    for i in range(n):
        a[i, i] = -(ua_env[i] + ua_am[i] + ua_zone[i].sum()) / c_air[i]
        a[i, n + i] = ua_am[i] / c_air[i]
        for j in range(n):
            if ua_zone[i, j]:
                a[i, j] = ua_zone[i, j] / c_air[i]
        a[n + i, n + i] = -(ua_am[i] + ua_mass_out[i]) / c_mass[i]
        a[n + i, i] = ua_am[i] / c_mass[i]
        bout[i] = ua_env[i] / c_air[i]
        bout[n + i] = ua_mass_out[i] / c_mass[i]

    m = np.linalg.inv(np.eye(2 * n) - dt * a)
    cool_cap = plant.cool_cap_w_m2 * area
    return BuildingModel(
        names=[z.name for z in zones], orientations=[z.orientation for z in zones], kinds=kinds,
        area=area, window=window, design_people=area / b.gains.area_per_person_m2,
        c_air=c_air, c_mass=c_mass, ua_env=ua_env, ua_mass_out=ua_mass_out, ua_am=ua_am,
        cool_cap=cool_cap, heat_cap=plant.heat_cap_w_m2 * area, fan_rated=plant.fan_w_m2 * area,
        g_econ=cool_cap / plant.design_supply_delta_k,
        M=m, Mq=np.ascontiguousarray(m[:, :n]), sens=np.diag(m)[:n] * dt / c_air,
        bout_dt=bout * dt, dt_c_air=dt / c_air, dt_c_mass=dt / c_mass,
    )
