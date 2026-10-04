---
id: TAR04
title: Pre conditioning before a critical peak event
category: tariff
tags: [critical peak, demand response, pre cool, event day, preparation]
directives:
  - id: TAR04_D1
    priority: 42
    label: event_precool
    when: "dr_today and h_to_dr > 0 and h_to_dr <= 3 and occupied"
    set: {heat: 20.0, cool: 22.5}
---
## Purpose
A critical peak event is far easier to ride through if the building enters it cold.

## When it applies
A critical peak event has been announced for today, it starts within three hours, and the zone is occupied.

## Procedure
Lower the cooling setpoint to 22.5 C and the heating setpoint to 20 C in the three hours before the event. This replaces the normal pre cooling depth for the day.

## Rationale
Three hours at the mid rate charges the slab and furniture with enough cooling to carry much of the event. The building then drifts from 22.5 C toward 26 C over four hours with the compressors lightly loaded.
