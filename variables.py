"""The vocabulary shared by knowledge documents, the reasoner and the verifier.

Directive conditions and constraint guards written inside knowledge base documents may
only reference the variables listed here. The loader rejects any document that uses an
unknown name, which catches typos at index time rather than in the middle of a run.
"""

SITUATION_VARIABLES = {
    # Building level
    "mode": "seasonal operating mode for the day: 'heating', 'cooling' or 'shoulder'",
    "tariff": "current tariff period: 'off', 'mid', 'peak' or 'critical'",
    "h_to_peak": "hours until the next peak or critical window starts (0 inside one, 99 if none)",
    "dr_today": "True when a critical peak event has been announced for today",
    "h_to_dr": "hours until the critical window starts (0 inside it, 99 if none)",
    "t_out": "outdoor dry bulb temperature now (C)",
    "t_out_max_6h": "forecast maximum outdoor temperature over the next 6 hours (C)",
    "t_out_max_24h": "forecast maximum outdoor temperature over the next 24 hours (C)",
    "t_out_min_12h": "forecast minimum outdoor temperature over the next 12 hours (C)",
    "econ_ok": "True when outdoor air is cool and dry enough for free cooling",
    "demand_ratio": "recent building demand divided by the monthly peak so far",
    "hour": "hour of day, 0 to 23",
    "weekday": "day of week, Monday is 0",
    "is_monday": "True on Mondays",
    "is_workday": "True on working days",
    # Zone level
    "occupied": "True when the zone occupancy sensor reports people present",
    "h_to_occ": "hours until bookings expect the zone to be occupied (0 if expected now, 99 if none)",
    "h_to_vacant": "hours until bookings expect the zone to empty (0 if not expected now)",
    "noshow_h": "consecutive hours the zone has been booked but empty",
    "t_zone": "zone air temperature now (C)",
    "orientation": "facade orientation: 'north', 'east', 'south', 'west' or 'core'",
    "kind": "'perimeter' or 'core'",
    "prev_heat": "heating setpoint in force during the previous decision interval (C)",
    "prev_cool": "cooling setpoint in force during the previous decision interval (C)",
    # Tunable knobs selected by episodic memory
    "start_lead": "hours of recovery allowed before expected occupancy",
    "precool_depth": "degrees of pre cooling ahead of a peak window",
    "shed_depth": "degrees of setpoint float inside a peak window",
    "setback_heat": "unoccupied heating setpoint (C)",
    "setback_cool": "unoccupied cooling setpoint (C)",
    # Working values, updated as directives are applied in priority order
    "heat": "heating setpoint being built for this zone (C)",
    "cool": "cooling setpoint being built for this zone (C)",
}

VARIABLE_NAMES = set(SITUATION_VARIABLES)
