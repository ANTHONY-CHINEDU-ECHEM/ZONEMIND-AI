---
id: SOO09
title: Demand limiting near the monthly peak
category: sequence_of_operation
tags: [demand limiting, demand charge, monthly peak, kilowatt]
directives:
  - id: SOO09_D1
    priority: 60
    label: demand_limit
    when: "demand_ratio >= 0.92 and occupied"
    set: {cool: "min(26.0, cool + 0.5)", heat: "max(20.0, heat - 0.5)"}
---
## Purpose
The demand charge is set by the single highest quarter hour of the month. This sequence trims load when the building is about to set a new monthly peak.

## When it applies
Recent building demand is at or above 92 percent of the highest demand recorded so far this month, and the zone is occupied.

## Procedure
Raise the cooling setpoint by half a degree and lower the heating setpoint by half a degree, staying inside the comfort envelope. Hold until demand falls back.

## Rationale
One new peak costs the same as many hours of energy. A half degree trim is rarely noticed and is usually enough to stay under the existing peak.
