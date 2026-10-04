---
id: PB03
title: Monday morning recovery after the weekend
category: playbook
tags: [monday, weekend, long set back, morning warm up]
directives:
  - id: PB03_D1
    priority: 27
    label: monday_early_start
    when: "is_monday and mode == 'heating' and not occupied and h_to_occ > start_lead and h_to_occ <= start_lead + 1"
    set: {heat: 21.0, cool: 26.0}
---
## Purpose
After sixty hours of weekend set back the building mass is much colder than after a single night. The usual warm up time is not enough.

## When it applies
Monday morning in heating season. The zone is unoccupied and is one hour away from the start of its normal recovery lead time.

## Procedure
Begin warm up one hour earlier than the normal recovery lead time.

## Rationale
The air reaches setpoint quickly, but cold walls and furniture keep the room feeling cool and pull the air temperature back down. The extra hour warms the mass.
