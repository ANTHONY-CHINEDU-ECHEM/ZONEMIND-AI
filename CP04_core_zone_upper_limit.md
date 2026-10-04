---
id: CP04
title: Core zone upper temperature limit
category: comfort_policy
tags: [core, comms room, limit, unoccupied]
constraints:
  - {id: C_CORE_COOL, kind: bound, var: cool, max: 27.0, when: "kind == 'core'", reason: "Network cabinets in the core need a cooler ceiling than open offices"}
directives:
  - id: CP04_D1
    priority: 12
    label: core_ceiling
    when: "kind == 'core' and not occupied"
    set: {cool: "min(cool, 27.0)"}
---
## Purpose
The core zone contains the network cabinets, the print hub and the main meeting rooms. Its equipment is less tolerant of heat than the open plan perimeter offices.

## Limits
The cooling setpoint of the core zone must never exceed 27 C, including overnight, at weekends and during set back. When the core is unoccupied, apply the normal unoccupied set back but cap the cooling setpoint at 27 C.

## Rationale
Switch and server intake temperatures follow room temperature closely. Holding the core at or below 27 C keeps the cabinets inside their rated range without dedicated cooling.
