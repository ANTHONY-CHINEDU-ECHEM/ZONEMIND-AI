### Chicago (cold continental)

| Controller | HVAC kWh | HVAC energy cost | Demand charges | Total bill | Peak kW | On peak kW | Comfort violations K·h | Unmet zone hours | Mean PPD % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed setpoints | 33,019 | 4,802 | 4,140 | 14,726 | 31.9 | 26.3 | 0.0 | 0.0 | 5.8 |
| Timetable | 27,265 | 4,414 | 4,605 | 14,802 | 45.8 | 27.6 | 246.9 | 128.2 | 6.1 |
| Timetable with tariff rules | 27,044 | 4,054 | 4,535 | 14,372 | 45.8 | 27.6 | 250.5 | 128.8 | 6.3 |
| ZoneMind AI | 27,232 | 3,736 | 4,083 | 13,602 | 40.9 | 20.3 | 18.8 | 5.8 | 6.3 |

### Tampa (hot humid)

| Controller | HVAC kWh | HVAC energy cost | Demand charges | Total bill | Peak kW | On peak kW | Comfort violations K·h | Unmet zone hours | Mean PPD % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed setpoints | 19,942 | 3,598 | 4,098 | 13,464 | 25.9 | 25.7 | 0.0 | 0.0 | 5.9 |
| Timetable | 16,727 | 3,248 | 4,175 | 13,190 | 27.3 | 26.0 | 52.5 | 19.5 | 6.0 |
| Timetable with tariff rules | 16,546 | 2,713 | 3,916 | 12,396 | 36.0 | 18.7 | 57.4 | 20.0 | 6.4 |
| ZoneMind AI | 15,637 | 2,549 | 3,920 | 12,237 | 35.7 | 20.8 | 5.5 | 2.3 | 6.4 |

### San Francisco (mild marine)

| Controller | HVAC kWh | HVAC energy cost | Demand charges | Total bill | Peak kW | On peak kW | Comfort violations K·h | Unmet zone hours | Mean PPD % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed setpoints | 7,095 | 1,036 | 2,896 | 9,704 | 19.6 | 19.4 | 0.0 | 0.0 | 6.3 |
| Timetable | 4,933 | 909 | 3,136 | 9,817 | 26.6 | 19.4 | 36.7 | 16.9 | 6.7 |
| Timetable with tariff rules | 4,928 | 857 | 3,247 | 9,876 | 27.4 | 17.0 | 36.7 | 16.9 | 6.7 |
| ZoneMind AI | 4,438 | 678 | 3,022 | 9,472 | 24.0 | 16.6 | 5.9 | 2.9 | 7.4 |

### Golden (cool dry, high altitude)

| Controller | HVAC kWh | HVAC energy cost | Demand charges | Total bill | Peak kW | On peak kW | Comfort violations K·h | Unmet zone hours | Mean PPD % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed setpoints | 28,376 | 4,064 | 3,961 | 13,800 | 32.9 | 26.7 | 0.0 | 0.0 | 5.9 |
| Timetable | 22,429 | 3,664 | 4,412 | 13,851 | 42.2 | 28.6 | 151.3 | 64.8 | 6.1 |
| Timetable with tariff rules | 22,232 | 3,346 | 4,342 | 13,464 | 42.2 | 28.6 | 151.7 | 64.8 | 6.3 |
| ZoneMind AI | 21,671 | 3,000 | 3,883 | 12,658 | 42.9 | 20.8 | 24.4 | 10.7 | 6.5 |

### ZoneMind AI reduction relative to each baseline

| Climate | Baseline | Total bill | HVAC energy cost | HVAC kWh | On peak demand | Comfort violations K·h |
|---|---:|---:|---:|---:|---:|---:|
| Chicago (cold continental) | Fixed setpoints | 7.6% | 22.2% | 17.5% | 22.8% | 0.0 to 18.8 |
| Chicago (cold continental) | Timetable | 8.1% | 15.3% | 0.1% | 26.5% | 246.9 to 18.8 |
| Chicago (cold continental) | Timetable with tariff rules | 5.4% | 7.8% | -0.7% | 26.5% | 250.5 to 18.8 |
| Tampa (hot humid) | Fixed setpoints | 9.1% | 29.1% | 21.6% | 19.1% | 0.0 to 5.5 |
| Tampa (hot humid) | Timetable | 7.2% | 21.5% | 6.5% | 19.9% | 52.5 to 5.5 |
| Tampa (hot humid) | Timetable with tariff rules | 1.3% | 6.0% | 5.5% | -11.2% | 57.4 to 5.5 |
| San Francisco (mild marine) | Fixed setpoints | 2.4% | 34.5% | 37.5% | 14.1% | 0.0 to 5.9 |
| San Francisco (mild marine) | Timetable | 3.5% | 25.4% | 10.0% | 14.1% | 36.7 to 5.9 |
| San Francisco (mild marine) | Timetable with tariff rules | 4.1% | 20.8% | 9.9% | 2.2% | 36.7 to 5.9 |
| Golden (cool dry, high altitude) | Fixed setpoints | 8.3% | 26.2% | 23.6% | 22.2% | 0.0 to 24.4 |
| Golden (cool dry, high altitude) | Timetable | 8.6% | 18.1% | 3.4% | 27.4% | 151.3 to 24.4 |
| Golden (cool dry, high altitude) | Timetable with tariff rules | 6.0% | 10.3% | 2.5% | 27.4% | 151.7 to 24.4 |

### Portfolio view, four buildings combined

| Controller | Total bill | HVAC energy cost | HVAC kWh | Comfort violations K·h | ZoneMind bill reduction | ZoneMind HVAC cost reduction |
|---|---:|---:|---:|---:|---:|---:|
| Fixed setpoints | 51,694 | 13,500 | 88,432 | 0.0 | 7.2% | 26.2% |
| Timetable | 51,660 | 12,234 | 71,354 | 487.4 | 7.1% | 18.6% |
| Timetable with tariff rules | 50,107 | 10,969 | 70,750 | 496.3 | 4.3% | 9.2% |
| ZoneMind AI | 47,970 | 9,964 | 68,978 | 54.6 |  |  |

### Grounding and verification in the main runs

| Climate | Decisions | Grounded decisions | Citations per decision | Document recall | Decisions repaired | Repairs by constraint |
|---|---:|---:|---:|---:|---:|---:|
| Chicago (cold continental) | 8760 | 100.0% | 2.34 | 0.995 | 32 | C_RATE 72, C_CORE_COOL 13, C_OCC_HEAT 4, C_OCC_COOL 3 |
| Tampa (hot humid) | 8760 | 100.0% | 2.31 | 0.996 | 37 | C_RATE 70, C_CORE_COOL 18, C_OCC_HEAT 4, C_OCC_COOL 3 |
| San Francisco (mild marine) | 8760 | 100.0% | 2.35 | 0.981 | 20 | C_RATE 51, C_CORE_COOL 7, C_OCC_HEAT 3, C_OCC_COOL 3 |
| Golden (cool dry, high altitude) | 8760 | 100.0% | 2.34 | 0.994 | 33 | C_RATE 65, C_CORE_COOL 16, C_OCC_HEAT 3, C_OCC_COOL 2 |

### Ablations, mean of four climates

| Variant | Mean annual bill | Bill vs full agent | Comfort violations K·h | Document recall | Decisions repaired by verifier |
|---|---:|---:|---:|---:|---:|
| Full agent | 11,992 |  | 13.7 | 0.991 | 30 |
| No episodic memory | 11,959 | -0.2% | 14.2 | 0.991 | 29 |
| Memory without commissioning | 12,011 | +0.2% | 11.7 | 0.991 | 28 |
| BM25 retrieval only | 11,992 | +0.0% | 13.7 | 0.994 | 30 |
| Dense retrieval only | 11,992 | +0.0% | 13.7 | 0.990 | 30 |
| No query decomposition | 12,005 | +0.1% | 13.5 | 0.943 | 277 |
| No retrieval | 12,923 | +7.4% | 0.0 | 0.000 | 0 |

### Episodic memory by climate (annual bill / comfort violations K·h)

| Climate | Commissioned memory | No memory | Memory without commissioning |
|---|---:|---:|---:|
| Chicago (cold continental) | 13,602 / 18.8 | 13,498 / 21.9 | 13,521 / 18.2 |
| Tampa (hot humid) | 12,237 / 5.5 | 12,212 / 5.5 | 12,277 / 5.2 |
| San Francisco (mild marine) | 9,472 / 5.9 | 9,477 / 6.0 | 9,461 / 3.9 |
| Golden (cool dry, high altitude) | 12,658 / 24.4 | 12,650 / 23.4 | 12,783 / 19.4 |

### Fault injection (chicago)

| Variant | Faults injected | Parse failures recovered | Verifier repairs | Invented citations flagged | Limit breaking commands at plant | Decisions affected | Comfort violations K·h | Unmet zone hours | Annual bill |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| clean with verifier | 0 | 0 | 80 | 0 | 0 | 0 | 21.9 | 7.5 | 13,498 |
| faults with verifier | 1325 | 150 | 2902 | 138 | 0 | 0 | 85.2 | 38.2 | 13,676 |
| faults without verifier | 1325 | 150 | 0 | 138 | 3871 | 1156 | 273.2 | 139.2 | 13,842 |

### Retrieval recall of applicable documents (35,040 decisions with at least one applicable document)

| Retriever | k=2 | k=4 | k=6 | k=8 | k=10 | k=12 |
|---|---:|---:|---:|---:|---:|---:|
| BM25 | 0.827 | 0.965 | 0.989 | 0.994 | 0.997 | 0.999 |
| LSA dense | 0.855 | 0.966 | 0.987 | 0.990 | 0.995 | 0.998 |
| Hybrid, single query | 0.775 | 0.879 | 0.916 | 0.943 | 0.982 | 0.995 |
| Hybrid, decomposed | 0.829 | 0.968 | 0.989 | 0.991 | 0.996 | 0.999 |

### Tight retrieval budget (k=4), mean of 4 climates, no memory

| Retriever | Document recall | Mean annual bill | HVAC kWh | Comfort violations K·h | Decisions repaired by verifier |
|---|---:|---:|---:|---:|---:|
| hybrid decomposed | 0.968 | 11,974 | 16,971 | 14.3 | 161 |
| hybrid single query | 0.879 | 12,163 | 17,234 | 13.9 | 557 |
| bm25 decomposed | 0.965 | 12,006 | 16,991 | 14.3 | 63 |
| dense decomposed | 0.966 | 12,005 | 16,991 | 14.3 | 63 |

### Knob sensitivity: change in annual score when one knob is held at each value

| Climate | Knob | Score change vs default |
|---|---:|---:|
| Chicago (cold continental) | start_lead | 1: +3.31%, 2: +0.00%, 3: -0.87% |
| Chicago (cold continental) | peak_strategy | none: +2.24%, light: +0.00%, deep: -0.57% |
| Chicago (cold continental) | setback | deep: +0.00%, standard: -0.70%, shallow: -0.24% |
| Tampa (hot humid) | start_lead | 1: +0.38%, 2: +0.00%, 3: -0.33% |
| Tampa (hot humid) | peak_strategy | none: +2.83%, light: +0.00%, deep: -0.32% |
| Tampa (hot humid) | setback | deep: +0.00%, standard: +0.39%, shallow: +1.04% |
| San Francisco (mild marine) | start_lead | 1: +0.11%, 2: +0.00%, 3: -0.12% |
| San Francisco (mild marine) | peak_strategy | none: +0.11%, light: +0.00%, deep: +0.00% |
| San Francisco (mild marine) | setback | deep: +0.00%, standard: -0.05%, shallow: -0.01% |
| Golden (cool dry, high altitude) | start_lead | 1: +2.54%, 2: +0.00%, 3: -0.58% |
| Golden (cool dry, high altitude) | peak_strategy | none: +1.75%, light: +0.00%, deep: -0.14% |
| Golden (cool dry, high altitude) | setback | deep: +0.00%, standard: -0.61%, shallow: -0.31% |
