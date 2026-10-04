---
id: PB04
title: Shoulder season wide dead band
category: playbook
tags: [shoulder season, mild weather, dead band, spring, autumn]
directives:
  - id: PB04_D1
    priority: 22
    label: shoulder_band
    when: "mode == 'shoulder' and occupied"
    set: {heat: 20.5, cool: 24.5}
---
## Purpose
In spring and autumn a zone can need a little heat in the morning and a little cooling in the afternoon. Tight setpoints make the plant chase both.

## When it applies
Shoulder season, with mild outdoor temperatures, and the zone is occupied.

## Procedure
Widen the occupied setpoints to 20.5 C heating and 24.5 C cooling.

## Rationale
In mild weather the building drifts gently inside a wider band with the plant mostly idle. People are also dressed for variable conditions at these times of year.
