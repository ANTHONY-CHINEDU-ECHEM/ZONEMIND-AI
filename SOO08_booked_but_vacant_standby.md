---
id: SOO08
title: Standby for booked but vacant zones
category: sequence_of_operation
tags: [standby, vacant, no show, booking, occupancy sensor]
directives:
  - id: SOO08_D1
    priority: 30
    label: standby
    when: "not occupied and h_to_occ == 0"
    set: {heat: 20.0, cool: 25.5}
  - id: SOO08_D2
    priority: 31
    label: deep_standby
    when: "not occupied and h_to_occ == 0 and noshow_h >= 2"
    set: {heat: 18.0, cool: 27.5}
---
## Purpose
With hybrid working, a zone that is booked is often empty for part or all of the day. This sequence stops the plant from conditioning empty space at full comfort.

## When it applies
Bookings expect the zone to be in use now, but the occupancy sensor reports nobody present.

## Procedure
Hold the zone in standby at 20 C heating and 25.5 C cooling so it can return to comfort within minutes of someone arriving. If the zone has been booked but empty for two hours or more, treat it as a no show and relax to 18 C and 27.5 C.

## Rationale
A fixed timetable conditions every zone all day whether or not anyone turns up. Standby recovers most of that waste with no effect on people who do arrive.
