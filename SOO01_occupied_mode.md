---
id: SOO01
title: Occupied mode setpoints
category: sequence_of_operation
tags: [occupied, working hours, base setpoints, comfort]
directives:
  - id: SOO01_D1
    priority: 20
    label: occupied
    when: "occupied"
    set: {heat: 21.0, cool: 24.0}
---
## Purpose
This sequence sets the standard operating setpoints for a zone that has people in it.

## When it applies
Whenever the zone occupancy sensor reports people present, at any hour and on any day, including weekend and walk in use.

## Procedure
Set the heating setpoint to 21 C and the cooling setpoint to 24 C. Other sequences may then adjust these values for tariff, demand or season, always inside the occupied comfort envelope.

## Rationale
These values sit in the middle of the comfort envelope, leaving one degree of room below and two above for tariff strategies to work with.
