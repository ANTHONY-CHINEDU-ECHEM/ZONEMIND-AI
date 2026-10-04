---
id: SOO10
title: Anticipating afternoon sun on the west facade
category: sequence_of_operation
tags: [west facade, solar gain, afternoon sun, anticipation]
directives:
  - id: SOO10_D1
    priority: 38
    label: west_solar
    when: "orientation == 'west' and mode == 'cooling' and occupied and hour >= 11 and hour <= 13 and t_out_max_6h >= 30 and tariff not in ('peak', 'critical')"
    set: {cool: "max(22.5, cool - 0.5)"}
---
## Purpose
The west zone receives low angle sun from mid afternoon, exactly when the peak tariff window opens. This sequence gets ahead of that gain.

## When it applies
The west zone is occupied in cooling season between 11:00 and 14:00, the forecast for the next six hours reaches 30 C, and the peak window has not yet started.

## Procedure
Lower the west zone cooling setpoint by half a degree, but not below 22.5 C, in addition to any general pre cooling.

## Rationale
Solar gain through west glazing is the largest single cooling load in the building on a hot afternoon. A small head start costs little at mid day rates.
