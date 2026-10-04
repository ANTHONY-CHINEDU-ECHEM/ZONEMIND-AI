---
id: SOO07
title: Night flush with outdoor air
category: sequence_of_operation
tags: [night flush, free cooling, economizer, outdoor air, thermal mass]
directives:
  - id: SOO07_D1
    priority: 35
    label: night_flush
    when: "mode == 'cooling' and not occupied and h_to_occ > 1 and econ_ok and t_out <= t_zone - 3 and t_zone >= 22.5 and t_out_max_24h >= 27"
    set: {heat: 15.5, cool: 21.0}
    lockout: true
---
## Purpose
On clear nights the outdoor air is often much cooler than the building. This sequence uses the fans alone to purge stored heat before a hot day.

## When it applies
Cooling season, the zone is unoccupied with more than one hour before expected occupancy, the outdoor air is cool and dry enough for free cooling and at least 3 C below the zone, the zone is at 22.5 C or warmer, and the next day is forecast to reach 27 C.

## Procedure
Lower the cooling setpoint to 21 C and lock out mechanical cooling so only outdoor air is used.

## Rationale
Fans cost a small fraction of compressor energy. A flushed slab delays the start of mechanical cooling the next day.
