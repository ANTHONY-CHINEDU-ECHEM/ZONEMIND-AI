---
id: EQP02
title: Mechanical cooling lockout
category: equipment
tags: [lockout, compressor, free cooling, economizer]
constraints:
  - {id: C_LOCKOUT, kind: flag, when: "occupied", reason: "Mechanical cooling may not be locked out while a zone is occupied"}
---
## Purpose
Locking out the compressors forces a zone to rely on outdoor air alone. It is used for night flushing.

## Limits
Mechanical cooling may only be locked out in a zone that is unoccupied. If anyone is present, the lockout must be released so the zone can hold the comfort envelope.

## Rationale
Outdoor air alone cannot guarantee comfort once people, lights and equipment are adding heat.
