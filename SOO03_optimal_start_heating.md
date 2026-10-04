---
id: SOO03
title: Optimal start for heating and mild seasons
category: sequence_of_operation
tags: [optimal start, morning warm up, recovery, heating, pre heat]
directives:
  - id: SOO03_D1
    priority: 25
    label: optimal_start
    when: "not occupied and h_to_occ > 0 and h_to_occ <= start_lead and mode != 'cooling'"
    set: {heat: 21.0, cool: 26.0}
---
## Purpose
Zones must be comfortable when people arrive, not an hour later. This sequence begins morning warm up ahead of expected occupancy.

## When it applies
Heating or shoulder season. The zone is unoccupied and bookings expect people within the recovery lead time.

## Procedure
Raise the heating setpoint to 21 C. Hold the cooling setpoint at 26 C so the plant does not cool during warm up. The recovery lead time is one, two or three hours and should be longer on cold mornings and after long set back periods.

## Rationale
Starting too late leaves people cold. Starting too early heats an empty building. The right lead time depends on the weather and on how long the zone has been set back.
