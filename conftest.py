import pytest

from zonemind.config import load_config
from zonemind.control.situation import Situation, ZoneState, default_knobs, knob_variables
from zonemind.eval.runner import get_kb


@pytest.fixture(scope="session")
def cfg():
    return load_config()


@pytest.fixture(scope="session")
def kb():
    return get_kb()


@pytest.fixture()
def knob_vars(cfg):
    return knob_variables(default_knobs(cfg), cfg)


def make_situation(**overrides) -> Situation:
    """A hot working afternoon with all five zones occupied, unless overridden."""
    zone_overrides = overrides.pop("zone", {})
    zones = []
    for name, orientation, kind in (("north", "north", "perimeter"), ("east", "east", "perimeter"),
                                    ("south", "south", "perimeter"), ("west", "west", "perimeter"),
                                    ("core", "core", "core")):
        state = dict(name=name, orientation=orientation, kind=kind, t_zone=24.0, occupied=True, h_to_occ=0,
                     h_to_vacant=3, noshow_h=0, prev_heat=21.0, prev_cool=24.0)
        state.update(zone_overrides)
        zones.append(ZoneState(**state))
    base = dict(step=0, hour_idx=0, day=196, stamp="Tue 15 Jul 14:00", hour=14, weekday=1, is_monday=False,
                is_workday=True, mode="cooling", tariff="mid", h_to_peak=1, dr_today=False, h_to_dr=99,
                t_out=32.0, t_out_max_6h=34.0, t_out_max_24h=34.0, t_out_min_12h=24.0, econ_ok=False,
                demand_ratio=0.7, demand_kw=20.0, month_peak_kw=28.0, outlook={}, zones=zones)
    base.update(overrides)
    return Situation(**base)


@pytest.fixture()
def situation():
    return make_situation
