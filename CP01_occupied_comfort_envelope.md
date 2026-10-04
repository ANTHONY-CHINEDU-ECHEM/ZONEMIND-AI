---
id: CP01
title: Occupied comfort envelope
category: comfort_policy
tags: [comfort, occupied, limits, policy]
constraints:
  - {id: C_OCC_HEAT, kind: bound, var: heat, min: 20.0, when: "occupied", reason: "Occupied zones may not be allowed to fall below 20 C"}
  - {id: C_OCC_COOL, kind: bound, var: cool, max: 26.0, when: "occupied", reason: "Occupied zones may not be allowed to rise above 26 C"}
---
## Purpose
This policy defines the temperature envelope that must be respected whenever people are present in a zone. It is the single most important limit in the building and no energy or tariff strategy may override it.

## Limits
While the occupancy sensor reports people present, the heating setpoint must be at least 20 C and the cooling setpoint must be at most 26 C. Any strategy that floats, sheds or trims a setpoint must stop at these values.

## Rationale
The envelope reflects the lease commitment to tenants and the comfort range that keeps predicted dissatisfaction low for office clothing and activity. Savings achieved by leaving the envelope are not counted as savings; they are counted as service failures.
