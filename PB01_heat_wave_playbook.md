---
id: PB01
title: Heat wave playbook
category: playbook
tags: [heat wave, extreme heat, overnight, recovery load]
directives:
  - id: PB01_D1
    priority: 15
    label: heatwave_setback
    when: "t_out_max_24h >= 35 and not occupied and h_to_occ > start_lead and h_to_occ <= 10"
    set: {cool: 27.0}
---
## Purpose
During a heat wave the building never fully cools overnight. A deep set back leaves the morning cool down too much to do.

## When it applies
The forecast for the next 24 hours reaches 35 C or more, the zone is unoccupied, and occupancy is expected within ten hours.

## Procedure
Hold the unoccupied cooling setpoint at 27 C instead of the normal set back value through the night before occupancy.

## Rationale
In extreme heat the slab soaks up heat all evening. Limiting the overnight rise costs some off peak energy but prevents a morning recovery that would run every compressor at full load and still leave zones warm at arrival.
