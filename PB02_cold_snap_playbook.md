---
id: PB02
title: Cold snap playbook
category: playbook
tags: [cold snap, severe cold, morning recovery, demand peak]
directives:
  - id: PB02_D1
    priority: 15
    label: coldsnap_setback
    when: "t_out_min_12h <= -12 and not occupied and h_to_occ > start_lead"
    set: {heat: 18.0}
  - id: PB02_D2
    priority: 27
    label: coldsnap_early_start
    when: "t_out_min_12h <= -12 and not occupied and h_to_occ > start_lead and h_to_occ <= start_lead + 1"
    set: {heat: 21.0, cool: 26.0}
---
## Purpose
On the coldest nights of the year heat pump capacity and efficiency are both at their lowest. A normal set back followed by a normal start produces the highest demand peak of the winter and cold zones at arrival.

## When it applies
The forecast minimum for the next twelve hours is minus 12 C or colder and the zone is unoccupied.

## Procedure
Hold the unoccupied heating setpoint at 18 C instead of the normal set back value. Begin morning warm up one hour earlier than the normal recovery lead time.

## Rationale
A shallower set back and a longer, gentler recovery keep the heat pumps out of their least efficient full load condition.
