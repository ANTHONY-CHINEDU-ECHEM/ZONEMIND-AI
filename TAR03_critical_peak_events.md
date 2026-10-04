---
id: TAR03
title: Critical peak event programme
category: tariff
tags: [critical peak, demand response, event, grid, shed]
directives:
  - id: TAR03_D1
    priority: 55
    label: critical_shed
    when: "tariff == 'critical' and occupied"
    set: {cool: 26.0}
  - id: TAR03_D2
    priority: 55
    label: critical_shed
    when: "tariff == 'critical' and not occupied"
    set: {cool: "max(cool, 28.0)"}
---
## Purpose
On up to twelve of the hottest summer working days the supplier calls a critical peak event. Energy used between 15:00 and 19:00 on those days costs 0.85 per kilowatt hour.

## When it applies
A critical peak event is active now. Events are announced the day before.

## Procedure
In occupied zones, float the cooling setpoint to the top of the comfort envelope at 26 C for the duration of the event. In booked but vacant zones, raise the cooling setpoint to at least 28 C.

## Rationale
At the critical rate, one event afternoon can cost as much as a normal week. Operating at the top of the envelope for four hours is within policy.
