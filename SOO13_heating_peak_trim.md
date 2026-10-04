---
id: SOO13
title: Heating trim inside the winter peak tariff window
category: sequence_of_operation
tags: [winter peak, heating, trim, evening, tariff]
directives:
  - id: SOO13_D1
    priority: 50
    label: peak_trim
    when: "mode == 'heating' and tariff == 'peak' and occupied"
    set: {heat: "max(20.0, heat - 0.5 * shed_depth)"}
---
## Purpose
In winter the peak tariff window falls in the early evening, when heat pump efficiency is dropping with the outdoor temperature. This sequence trims heating during that window.

## When it applies
Heating season, the peak tariff window is active now, and the zone is occupied.

## Procedure
Lower the heating setpoint by half the shed depth, so by zero, half a degree or one degree, but never below 20 C.

## Rationale
Late in the day internal gains and stored heat carry the zone. Most people have left or are about to leave, so a small trim has little comfort impact.
