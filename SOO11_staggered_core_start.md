---
id: SOO11
title: Staggered morning start for the core zone
category: sequence_of_operation
tags: [staggered start, morning peak, core, recovery, demand]
directives:
  - id: SOO11_D1
    priority: 26
    label: stagger
    when: "kind == 'core' and mode == 'heating' and not occupied and h_to_occ > start_lead and h_to_occ <= start_lead + 1"
    set: {heat: 19.0}
---
## Purpose
When every zone begins warm up in the same hour the heat pumps draw their highest load of the day and can set the monthly demand peak before anyone has arrived.

## When it applies
Heating season. The core zone is unoccupied and is one hour away from the start of its normal recovery lead time.

## Procedure
Begin warming the core zone one hour before the perimeter zones, to an intermediate setpoint of 19 C. The normal optimal start then completes the recovery.

## Rationale
The core is the largest zone and has no solar gain to help it. Spreading its recovery over an extra hour flattens the morning demand spike.
