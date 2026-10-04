---
id: CP02
title: Unoccupied temperature limits
category: comfort_policy
tags: [unoccupied, limits, fabric protection]
constraints:
  - {id: C_UNOCC_HEAT, kind: bound, var: heat, min: 13.0, reason: "Fabric and pipework protection floor"}
  - {id: C_UNOCC_COOL, kind: bound, var: cool, max: 31.0, reason: "Furnishings and equipment ceiling"}
---
## Purpose
Empty zones can drift well outside the comfort envelope, but not without limit. This policy sets the widest range any zone may reach at any time, occupied or not.

## Limits
The heating setpoint must never be below 13 C and the cooling setpoint must never be above 31 C. These limits apply at night, at weekends and on holidays.

## Rationale
Below 13 C the risk of condensation on cold surfaces and of slow morning recovery rises sharply. Above 31 C adhesives, electronics and stored materials begin to suffer, and the recovery load on the next working morning can exceed plant capacity.
