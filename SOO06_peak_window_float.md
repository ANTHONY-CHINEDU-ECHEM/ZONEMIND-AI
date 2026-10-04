---
id: SOO06
title: Setpoint float inside the peak tariff window
category: sequence_of_operation
tags: [peak tariff, load shed, float, cooling, afternoon]
directives:
  - id: SOO06_D1
    priority: 50
    label: peak_float
    when: "mode == 'cooling' and tariff == 'peak' and occupied"
    set: {cool: "min(26.0, cool + shed_depth)"}
---
## Purpose
During the peak tariff window every kilowatt hour is expensive. This sequence lets occupied zones float upward within the comfort envelope to reduce compressor run time.

## When it applies
Cooling season, the peak tariff window is active now, and the zone is occupied.

## Procedure
Raise the cooling setpoint by the shed depth, which is zero, one or two degrees, but never above 26 C. Return to the normal setpoint when the window closes.

## Rationale
Combined with pre cooling, the zone starts the window cool and drifts slowly toward the upper limit. Occupants experience a gentle rise rather than a step.
