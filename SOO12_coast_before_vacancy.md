---
id: SOO12
title: Coasting before the end of occupancy
category: sequence_of_operation
tags: [coast, end of day, departure, early shutdown]
directives:
  - id: SOO12_D1
    priority: 45
    label: coast
    when: "occupied and h_to_vacant == 1"
    set: {cool: "min(26.0, cool + 0.5)", heat: "max(20.0, heat - 0.5)"}
---
## Purpose
The building mass holds a zone close to comfort for some time after the plant backs off. This sequence uses that inertia at the end of the working day.

## When it applies
The zone is occupied and bookings expect it to empty within the hour.

## Procedure
Relax the cooling setpoint by half a degree and the heating setpoint by half a degree, staying inside the comfort envelope.

## Rationale
The last hour of conditioning mostly benefits an empty room. A small relaxation is not perceptible to the few people still present.
