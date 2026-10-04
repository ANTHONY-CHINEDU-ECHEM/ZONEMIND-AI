"""Turn a numeric situation into short natural language facets for retrieval.

Each facet describes one aspect of what is happening in the building, in the words an
operator would use. The facets say nothing about what to do; connecting a described
state to the right operating guidance is the retriever's job. A language model query
rewriter could replace this module without changing anything downstream.
"""
from __future__ import annotations

from .situation import Situation

_SEASON = {
    "cooling": "cooling season with warm weather",
    "heating": "heating season with cold weather",
    "shoulder": "shoulder season with mild weather",
}


def verbalise(s: Situation, start_lead: int) -> list[str]:
    season = _SEASON[s.mode]
    zones = s.zones
    facets: list[str] = []

    if any(z.occupied for z in zones):
        facets.append(f"Zones are occupied with people present in {season}.")
    if any(not z.occupied and z.h_to_occ > start_lead for z in zones):
        facets.append("Zones are unoccupied and empty with nobody expected soon, at night, a weekend or a holiday.")
    if any(not z.occupied and 0 < z.h_to_occ <= start_lead + 1 for z in zones):
        facets.append(f"Zones are unoccupied but bookings expect people to arrive soon, morning recovery in {season}.")
    if any(not z.occupied and z.h_to_occ == 0 for z in zones):
        facets.append("A zone is booked for use now but is vacant with nobody present.")
    if any(z.occupied and z.h_to_vacant == 1 for z in zones):
        facets.append("A zone is occupied and bookings expect it to empty within the hour at the end of the day.")
    if any(z.kind == "core" and not z.occupied for z in zones):
        facets.append("The core zone is unoccupied.")

    if s.tariff == "critical":
        facets.append("A critical peak event is active now.")
    elif s.tariff == "peak":
        facets.append(f"The peak tariff window is active now in {s.mode} season.")
    elif 0 < s.h_to_peak <= 2:
        facets.append(f"The peak tariff window starts within two hours in {s.mode} season.")
    if s.dr_today and 0 < s.h_to_dr <= 3:
        facets.append("A critical peak event has been announced for today and starts within three hours.")

    if s.t_out_max_24h >= 35.0:
        facets.append("Extreme heat is forecast, a heat wave.")
    if s.t_out_min_12h <= -12.0:
        facets.append("Severe cold is forecast overnight, a cold snap.")
    if s.mode == "cooling" and s.econ_ok and any(not z.occupied and s.t_out <= z.t_zone - 3.0 for z in zones):
        facets.append("At night the outdoor air is cool and dry and well below the zone temperature.")
    if s.mode == "cooling" and 11 <= s.hour <= 13 and s.t_out_max_6h >= 30.0:
        facets.append("A hot afternoon is forecast with sun on the west facade.")
    if s.demand_ratio >= 0.92:
        facets.append("Building demand is close to the highest demand recorded this month.")
    if s.is_monday and s.mode == "heating" and s.hour <= 9:
        facets.append("It is Monday morning after a weekend of set back in heating season.")
    return facets
