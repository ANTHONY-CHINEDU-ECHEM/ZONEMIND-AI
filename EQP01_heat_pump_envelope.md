---
id: EQP01
title: Heat pump setpoint operating envelope
category: equipment
tags: [heat pump, setpoint range, manufacturer limits]
constraints:
  - {id: C_EQP_HEAT, kind: bound, var: heat, min: 12.0, max: 24.0, reason: "Terminal unit heating setpoint range"}
  - {id: C_EQP_COOL, kind: bound, var: cool, min: 20.0, max: 32.0, reason: "Terminal unit cooling setpoint range"}
---
## Purpose
The zone terminal units only accept setpoints inside a fixed range. Commands outside the range are rejected by the controller and raise an alarm.

## Limits
Heating setpoints must lie between 12 C and 24 C. Cooling setpoints must lie between 20 C and 32 C.

## Rationale
These are the manufacturer limits for stable refrigerant circuit operation. A cooling setpoint below 20 C risks coil icing at low load and a heating setpoint above 24 C risks high head pressure trips.
