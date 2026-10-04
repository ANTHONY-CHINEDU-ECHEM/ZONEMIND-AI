---
id: SOO04
title: Optimal start for cooling season
category: sequence_of_operation
tags: [optimal start, morning cool down, recovery, cooling]
directives:
  - id: SOO04_D1
    priority: 25
    label: optimal_start
    when: "not occupied and h_to_occ > 0 and h_to_occ <= start_lead and mode == 'cooling'"
    set: {heat: 18.0, cool: 24.0}
---
## Purpose
After a warm night the building mass holds heat. This sequence begins morning cool down ahead of expected occupancy so zones are comfortable on arrival.

## When it applies
Cooling season. The zone is unoccupied and bookings expect people within the recovery lead time.

## Procedure
Lower the cooling setpoint to 24 C. Hold the heating setpoint at 18 C so the plant does not heat during cool down. Morning electricity is off peak, so cool down is cheap compared with catching up later in the day.

## Rationale
Removing stored heat before the tariff rises and before solar gains build is the cheapest cooling of the day.
