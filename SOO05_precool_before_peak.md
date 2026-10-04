---
id: SOO05
title: Pre cooling ahead of the peak tariff window
category: sequence_of_operation
tags: [pre cool, peak tariff, load shift, thermal mass, afternoon]
directives:
  - id: SOO05_D1
    priority: 40
    label: precool
    when: "mode == 'cooling' and tariff not in ('peak', 'critical') and h_to_peak > 0 and h_to_peak <= 2 and occupied and t_out_max_6h >= 27"
    set: {cool: "max(22.0, cool - precool_depth)", heat: "min(heat, 20.0)"}
---
## Purpose
Electricity costs roughly three times more in the peak window than off peak. This sequence stores cooling in the building mass before the window opens.

## When it applies
Cooling season, the zone is occupied, the peak tariff window starts within two hours, and the forecast for the next six hours reaches at least 27 C.

## Procedure
Lower the cooling setpoint by the pre cooling depth, which is zero, one or two degrees, but never below 22 C. Lower the heating setpoint to 20 C at the same time so the dead band stays open. Release the pre cool when the peak window opens.

## Rationale
A cooler slab and cooler furniture absorb heat through the peak window, so the compressors run less when energy is most expensive. On mild days the stored cooling is not needed and pre cooling only wastes energy.
