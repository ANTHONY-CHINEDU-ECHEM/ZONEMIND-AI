---
id: EQP05
title: Freeze protection in severe cold
category: equipment
tags: [freeze protection, severe cold, pipework, winter]
constraints:
  - {id: C_FREEZE, kind: bound, var: heat, min: 16.0, when: "t_out_min_12h <= -15", reason: "Protects perimeter pipework and limits recovery load in severe cold"}
---
## Purpose
In severe cold a deeply set back perimeter zone can approach freezing at the glazing line even when the room sensor reads well above zero.

## Limits
Whenever the forecast minimum for the next twelve hours is minus 15 C or colder, no zone heating setpoint may be below 16 C.

## Rationale
Burst sprinkler and condensate lines are far more costly than the energy saved by a deep set back on a handful of nights each year.
