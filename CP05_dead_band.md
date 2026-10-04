---
id: CP05
title: Minimum dead band between heating and cooling
category: comfort_policy
tags: [dead band, simultaneous heating and cooling]
constraints:
  - {id: C_DEADBAND, kind: gap, min_gap: 2.0, reason: "Prevents the plant from heating and cooling the same zone in turn"}
---
## Purpose
A zone with heating and cooling setpoints too close together will hunt between the two modes and waste energy.

## Limits
The cooling setpoint must always be at least 2 C above the heating setpoint in every zone. If a strategy would close the gap, raise the cooling setpoint first; lower the heating setpoint only if the cooling setpoint is already at its ceiling.

## Rationale
The terminal units have a control tolerance of roughly half a degree either way. A 2 C gap guarantees the two loops never overlap.
