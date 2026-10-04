"""Closed loop building environment.

The environment owns the physics and the plant. Controllers never see inside it; they
only supply heating and cooling setpoints (and an optional mechanical cooling lockout)
for each zone, exactly as a supervisory layer writes to a building management system.
"""
from __future__ import annotations

import numpy as np

from ..data.calendar import Calendar
from ..data.occupancy import Occupancy
from ..data.solar import vertical_irradiance
from ..data.weather import Weather
from .building import AIR_RHO_CP, BuildingModel, build_model


class BuildingEnv:
    def __init__(self, cfg, cal: Calendar, weather: Weather, occupancy: Occupancy):
        self.cfg, self.cal, self.weather, self.occ = cfg, cal, weather, occupancy
        self.model: BuildingModel = build_model(cfg, cal.dt)
        m, g, plant = self.model, cfg.building.gains, cfg.plant
        n, ns = m.n, cal.n_steps
        occ = occupancy.actual
        present = occ >= occupancy.threshold
        t_hours = (np.arange(ns) + 0.5) * cal.dt / 3600.0

        # Internal heat gains and the electricity that causes them (W).
        people = occ * m.design_people * g.people_sensible_w
        equipment = m.area * (g.equipment_base_w_m2 + g.equipment_occupied_w_m2 * occ)
        lighting = m.area * g.lighting_w_m2 * present
        internal = people + equipment + lighting
        self.base_kw = (equipment + lighting).sum(axis=1) / 1000.0

        # Solar gains through glazing, split between the air node and the thermal mass.
        solar = np.zeros((ns, n))
        for i, orient in enumerate(m.orientations):
            if m.window[i] > 0:
                irr = vertical_irradiance(t_hours, weather.lat, weather.lon, weather.tz, weather.dni,
                                          weather.dhi, weather.ghi, orient,
                                          cfg.building.envelope.ground_reflectance)
                solar[:, i] = irr * m.window[i] * cfg.building.envelope.shgc
        fa = g.solar_to_air_fraction
        self.q_air = internal * (1.0 - g.radiant_fraction) + solar * fa
        self.q_mass = internal * g.radiant_fraction + solar * (1.0 - fa)

        # Ventilation: outdoor air while occupied, with heat recovery when it helps.
        flow = present * (occ * m.design_people * plant.vent_l_s_person + m.area * plant.vent_l_s_m2) / 1000.0
        recover = (weather.t_out < 16.0) | (weather.t_out > 26.0)
        self.g_vent = AIR_RHO_CP * flow * np.where(recover, 1.0 - plant.heat_recovery_eff, 1.0)[:, None]
        self.vent_frac = present * plant.vent_min_flow_fraction

        # Plant performance depends on outdoor conditions only, so it is precomputed.
        t = weather.t_out
        self.cop_c = np.clip(plant.cop_cool_rated * (1.0 + plant.cop_cool_slope * (35.0 - t)),
                             plant.cop_cool_min, plant.cop_cool_max)
        self.cop_h = np.clip(plant.cop_heat_rated + plant.cop_heat_slope * (t - 7.0),
                             plant.cop_heat_min, plant.cop_heat_max)
        self.econ_ok = (t <= plant.economizer_max_drybulb_c) & (weather.dew <= plant.economizer_max_dewpoint_c)

        self.rec_ta = np.zeros((ns, n), dtype=np.float32)
        self.rec_tm = np.zeros((ns, n), dtype=np.float32)
        self.rec_heat_sp = np.zeros((ns, n), dtype=np.float32)
        self.rec_cool_sp = np.zeros((ns, n), dtype=np.float32)
        self.rec_power = np.zeros((ns, 3))      # cooling, heating, fans (kW electric)
        self.rec_thermal = np.zeros((ns, 2))    # mechanical cooling, heating (kW thermal)
        self.reset()

    def reset(self) -> None:
        self.x = np.full(2 * self.model.n, float(self.cfg.sim.initial_temp_c))
        self.eff_heat = self.eff_cool = None   # setpoints the local loops are currently tracking

    @property
    def air_temp(self) -> np.ndarray:
        return self.x[: self.model.n]

    def total_kw(self, s0: int, s1: int) -> np.ndarray:
        return self.rec_power[s0:s1].sum(axis=1) + self.base_kw[s0:s1]

    def run_block(self, s0: int, s1: int, heat_sp, cool_sp, lockout) -> None:
        """Advance the building from step ``s0`` to ``s1`` holding the given zone commands."""
        m = self.model
        n = m.n
        heat_sp = np.asarray(heat_sp, dtype=float)
        cool_sp = np.asarray(cool_sp, dtype=float)
        mech_allowed = ~np.asarray(lockout, dtype=bool)
        x = self.x
        src = np.empty(2 * n)
        # Local control loops ramp toward a tighter setpoint rather than stepping to it, as a
        # real building management system does. A relaxed setpoint takes effect immediately.
        ramp = self.cfg.plant.setpoint_ramp_k_per_h * self.cal.dt / 3600.0
        if self.eff_heat is None:
            self.eff_heat, self.eff_cool = heat_sp.copy(), cool_sp.copy()
        eff_heat, eff_cool = self.eff_heat, self.eff_cool
        t_out, q_air, q_mass, g_vent = self.weather.t_out, self.q_air, self.q_mass, self.g_vent

        for s in range(s0, s1):
            tout = t_out[s]
            ta = x[:n]
            eff_cool = np.maximum(cool_sp, np.minimum(eff_cool, ta) - ramp)
            eff_heat = np.minimum(heat_sp, np.maximum(eff_heat, ta) + ramp)
            # Free response of the building over this step with the plant off.
            src[:n] = (q_air[s] + g_vent[s] * (tout - ta)) * m.dt_c_air
            src[n:] = q_mass[s] * m.dt_c_mass
            x_free = m.M @ (x + src + m.bout_dt * tout)
            ta_free = x_free[:n]

            # Ideal thermostat: the thermal power needed to land on the active setpoint.
            cool_need = np.maximum(ta_free - eff_cool, 0.0) / m.sens
            heat = np.minimum(np.maximum(eff_heat - ta_free, 0.0) / m.sens, m.heat_cap)
            heat[cool_need > 0.0] = 0.0

            # Economizer first, then mechanical cooling for whatever is left.
            if self.econ_ok[s]:
                avail = m.g_econ * np.maximum(ta - tout, 0.0)
                free = np.minimum(cool_need, avail)
                econ_frac = np.divide(free, avail, out=np.zeros(n), where=avail > 0.0)
            else:
                free = np.zeros(n)
                econ_frac = free
            mech = np.minimum(cool_need - free, m.cool_cap) * mech_allowed

            x = x_free + m.Mq @ ((heat - free - mech) * m.dt_c_air)

            frac = np.maximum.reduce([self.vent_frac[s], mech / m.cool_cap, heat / m.heat_cap, econ_frac])
            fan = (m.fan_rated * (0.05 * (frac > 0.0) + 0.95 * frac**2.5)).sum()
            mech_sum, heat_sum = mech.sum(), heat.sum()
            self.rec_power[s, 0] = mech_sum / self.cop_c[s] / 1000.0
            self.rec_power[s, 1] = heat_sum / self.cop_h[s] / 1000.0
            self.rec_power[s, 2] = fan / 1000.0
            self.rec_thermal[s, 0] = mech_sum / 1000.0
            self.rec_thermal[s, 1] = heat_sum / 1000.0
            self.rec_ta[s] = x[:n]
            self.rec_tm[s] = x[n:]
        self.rec_heat_sp[s0:s1] = heat_sp
        self.rec_cool_sp[s0:s1] = cool_sp
        self.x = x
        self.eff_heat, self.eff_cool = eff_heat, eff_cool
