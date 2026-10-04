---
id: SOO02
title: Unoccupied set back
category: sequence_of_operation
tags: [unoccupied, set back, night, weekend, holiday]
directives:
  - id: SOO02_D1
    priority: 10
    label: setback
    when: "not occupied and h_to_occ > start_lead"
    set: {heat: "setback_heat", cool: "setback_cool"}
---
## Purpose
An empty zone does not need conditioning. This sequence widens the setpoints overnight, at weekends, on holidays and in any zone that is not expected to be used.

## When it applies
The zone is unoccupied and bookings do not expect anyone within the recovery lead time.

## Procedure
Set the heating and cooling setpoints to the current set back values. Three depths are available. The deep set back is 15.5 C heating and 30 C cooling. The standard set back is 17.5 C and 28.5 C. The shallow set back is 19 C and 27 C and is preferred when the recovery load would otherwise set a demand peak.

## Rationale
Set back is the largest single source of savings in an intermittently used office. A deeper set back saves more overnight but costs more to recover from.
