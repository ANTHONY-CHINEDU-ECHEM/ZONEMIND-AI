---
id: SOO14
title: Pre heating ahead of the winter peak tariff window
category: sequence_of_operation
tags: [pre heat, winter peak, load shift, heating]
directives:
  - id: SOO14_D1
    priority: 40
    label: preheat
    when: "mode == 'heating' and tariff != 'peak' and h_to_peak > 0 and h_to_peak <= 1 and occupied and precool_depth > 0"
    set: {heat: "min(22.5, heat + 0.5 * precool_depth)"}
---
## Purpose
The winter equivalent of pre cooling. A little extra heat stored before the evening peak window allows a trim inside it.

## When it applies
Heating season, the zone is occupied, and the peak tariff window starts within the hour.

## Procedure
Raise the heating setpoint by half the pre conditioning depth, so by half a degree or one degree, but never above 22.5 C.

## Rationale
Heat stored at the mid rate displaces heat that would be bought at the peak rate. The effect is smaller than summer pre cooling because the window is short and the building is emptying.
