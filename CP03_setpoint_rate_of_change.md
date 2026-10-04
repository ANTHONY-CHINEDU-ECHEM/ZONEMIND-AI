---
id: CP03
title: Setpoint rate of change while occupied
category: comfort_policy
tags: [drift, ramp, occupied, rate]
constraints:
  - {id: C_RATE, kind: rate, max_delta: 3.0, when: "occupied", reason: "Occupants notice and complain about abrupt setpoint swings"}
---
## Purpose
People tolerate slow temperature drift far better than sudden change. This policy limits how quickly a setpoint may move while a zone is occupied.

## Limits
While a zone is occupied, neither the heating nor the cooling setpoint may change by more than 3 C between consecutive supervisory decisions. Where this limit conflicts with the occupied comfort envelope, the envelope takes precedence.

## Rationale
Step changes larger than this produce draughts from the terminal units and a noticeable change in supply air noise. A ramp also protects the compressors from a sudden full load call.
