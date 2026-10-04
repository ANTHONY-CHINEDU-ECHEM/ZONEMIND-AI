# ZoneMind AI

**Retrieval Grounded Adaptive Setpoint Control for Multi Zone Smart Buildings, with Episodic Memory and Constraint Verified Reasoning**

<img width="1438" height="748" alt="architecture" src="https://github.com/user-attachments/assets/b8cef896-2159-472b-a4d9-350449a76924" />


## Project brief

Heating, ventilation and air conditioning is the largest controllable load in most commercial buildings, yet the logic that runs it has barely changed in thirty years. A typical building management system follows a timetable: comfort setpoints from early morning to early evening on working days, set back otherwise. That timetable was written for a world in which every desk was occupied every day and electricity cost the same at every hour. Neither is true any more. Hybrid working means a zone that is booked is often empty, and a zone that is empty on Friday is full on Tuesday. Tariffs now charge three times more in the late afternoon than overnight, add a separate charge for the single highest quarter hour of the month, and on the hottest days of summer raise the price again for a few critical hours. A timetable cannot see any of this, so it conditions empty rooms, buys energy at the worst possible time, and still leaves people uncomfortable when they arrive early or stay late.

The knowledge needed to do better already exists in every well run building. It sits in sequences of operation written by the commissioning engineer, in the comfort policy agreed with tenants, in the supply contract, in equipment manuals, and in the playbooks the facilities team writes after each heat wave and cold snap. The problem is that none of it is connected to the control system. Operators cannot read forty documents every hour, and a building management system cannot read them at all. Large language models can, but nobody responsible for a building will let a language model write setpoints to live plant on the strength of its own judgement. A model that invents a strategy, misreads a limit or returns malformed output is a comfort complaint at best and a frozen pipe at worst.

ZoneMind AI is a complete, runnable answer to that problem. Every hour it describes the state of the building in plain language, retrieves the operating documents that apply to that state, and proposes heating and cooling setpoints for each zone that are grounded in, and cite, those documents. An independent verifier then checks the proposal against every hard limit in the governed knowledge base and repairs anything that breaks one before it reaches the plant. An episodic memory records what each day cost and how comfortable it was, so that strategy can be tuned from the outcomes of similar past days. The reasoning step is pluggable: a language model through the Anthropic API or any OpenAI compatible server, or a deterministic reasoner that executes the same documents without a model and serves as the fallback whenever a model's output cannot be used.

The project is evaluated in closed loop rather than on question answering scores, because the only test that matters for a controller is what happens to the building. A five zone, 800 square metre office is simulated with a two node thermal network per zone, a heat pump plant with weather dependent efficiency, an economizer, heat recovery ventilation, stochastic hybrid occupancy with an imperfect booking forecast, and a time of use tariff with two demand charges and critical peak events. The same building is run for a full year in four climates using measured typical year weather for Chicago, Tampa, San Francisco and Golden: 35,040 hourly decisions and 420,480 five minute physics steps per controller. The knowledge base holds 43 original operating documents with 24 machine readable directives and 11 hard constraints.

One point of transparency before the findings. Every number reported below was produced with the deterministic reasoner, so the results are exactly reproducible on any machine with no API key and no model download. The language model backends are implemented behind the same interface, the same parser and the same verifier, but they were not exercised in the reported experiments and have not been tested against a live endpoint. The results therefore measure the retrieval, grounding, verification and memory architecture, and they are a floor for what a capable model in the reasoning seat should achieve, not a claim about any particular model.

## Headline results

Four buildings, one per climate, one evaluation year each. Every controller sees identical weather, occupancy and tariff.

| Controller | Total bill | HVAC energy cost | HVAC kWh | Comfort violations K·h | Unmet zone hours |
|---|---:|---:|---:|---:|---:|
| Fixed setpoints, never set back | 51,694 | 13,500 | 88,432 | 0.0 | 0.0 |
| Timetable | 51,660 | 12,234 | 71,354 | 487.4 | 229.4 |
| Timetable with hand written tariff rules | 50,107 | 10,969 | 70,750 | 496.3 | 230.5 |
| **ZoneMind AI** | **47,970** | **9,964** | **68,978** | **54.6** | **21.7** |

Against the timetable that most buildings run today, ZoneMind AI cut the total electricity bill by 7.1 percent, the HVAC energy cost by 18.6 percent, and occupied comfort violations by 89 percent. Against a timetable that an energy manager has already tuned by hand for the tariff, the bill fell by 4.3 percent and HVAC energy cost by 9.2 percent, again with 89 percent fewer comfort violations. The total bill includes lighting and equipment, which no HVAC controller can influence and which make up roughly two thirds of consumption in this building, so the HVAC energy cost column is the fairer measure of what the controller itself achieved.

<img width="1839" height="635" alt="benchmark" src="https://github.com/user-attachments/assets/f2c91fc6-c154-4cf3-a4fd-608775453f4e" />


Three further results matter as much as the savings:

1. **Every decision was grounded.** All 35,040 decisions cited at least one retrieved document, with 2.3 citations per decision on average, and no citation pointed outside the retrieved set.
2. **The verifier held under attack.** With faults injected into 15 percent of reasoning outputs, 3,871 commands that broke a hard limit reached the plant when the verifier was switched off. With it switched on, none did.
3. **Episodic memory did not earn its place in this building.** Strategy tuning from past days left the bill within 0.3 percent of the same agent with no memory. The reason is measured and explained below; it is reported as a finding, not hidden.

## How it works

Each hourly decision passes through six stages.

1. **Situation.** Sensor readings, the weather forecast, room bookings, the tariff calendar and metered demand are assembled into a numeric state. The agent sees only what a real supervisory controller could know: forecasts carry error that grows with lead time, bookings differ from actual attendance, and the simulator's internal state is never exposed.
2. **Verbalisation.** The state is described as short plain language facets, such as "The peak tariff window starts within two hours in cooling season" or "A zone is booked for use now but is vacant with nobody present". Facets describe what is happening, never what to do.
3. **Retrieval.** Each facet is ranked separately against the knowledge base by BM25 and by a latent semantic embedding, the two rankings are combined by reciprocal rank fusion, and the facets are merged so that every facet receives its best document before any facet receives its second. Results are cached by situation, and an uncached query takes about 0.6 milliseconds.
4. **Reasoning.** The retrieved documents, the situation, the strategy knobs for the day and the outcomes of similar past days go to the reasoning backend, which returns one JSON proposal: setpoints per zone, a rationale and the documents it relied on.
5. **Verification.** The verifier loads every hard constraint from the knowledge base at start up and applies all of them to every proposal, whether or not the relevant document was retrieved. It limits rate of change, clamps to occupied and unoccupied bounds, reopens a closed dead band, releases a mechanical cooling lockout in an occupied zone, fills in any zone the proposal left out, and flags citations that were never retrieved. Each repair is logged with the constraint and source document.
6. **Learning.** At midnight the finished day is stored as an episode: the outlook the agent saw, the knobs it used, and what the day cost in energy, demand and comfort.

Documents are the single source of truth. Each is a Markdown file whose prose is retrieved and read, and whose front matter carries the same guidance as directives for the deterministic reasoner and constraints for the verifier. An operations team changes policy by editing one file. Conditions inside documents are evaluated by a whitelisting expression interpreter, so a document is data and can never execute code.

## One day in detail: a critical peak event in Tampa

Thursday 17 July reaches 34 C and the supplier has called a critical peak event from 15:00 to 19:00, when energy costs 0.85 per kilowatt hour against 0.11 overnight.

<img width="1274" height="1001" alt="event_day_tampa" src="https://github.com/user-attachments/assets/c811bc8a-c527-40d5-b7f3-176dd0fe8db3" />


The timetable holds 24 C all day and carries about 25 kW through the event. ZoneMind AI cools the west zone slightly ahead of the afternoon sun, brings the building down to about 22.5 C in the three hours before the event while energy is at the mid rate, then floats to the 26 C comfort limit when the event begins. Its demand inside the event falls to roughly 15 kW. The cost is a higher load between noon and 15:00, which is visible in the lower panel and is exactly the trade the tariff rewards.

The decision trace for 15:00, abridged from the audit record, shows grounding and verification working together:

```json
{
  "time": "Thu 17 Jul 15:00",
  "facets": [
    "Zones are occupied with people present in cooling season with warm weather.",
    "A critical peak event is active now.",
    "Building demand is close to the highest demand recorded this month."
  ],
  "retrieved": ["SOO01", "TAR03", "SOO09", "CP01", "TAR04", "TAR02", "SOO11", "SOO03"],
  "applicable": ["SOO01", "SOO09", "TAR03"],
  "citations": ["SOO01", "TAR03", "SOO09"],
  "proposed": {"north": {"heat": 20.5, "cool": 26.0}},
  "verification": {
    "violations": [{
      "zone": "north", "constraint": "C_RATE", "source": "CP03", "field": "cool",
      "proposed": 26.0, "repaired": 25.5,
      "reason": "Occupants notice and complain about abrupt setpoint swings"
    }]
  },
  "commands": {"north": {"heat": 20.5, "cool": 25.5}}
}
```

The critical event document says to float to 26 C. The zone was at 22.5 C a moment earlier, and the comfort policy forbids moving an occupied zone's setpoint by more than 3 C in one decision. That policy document (CP03) was not even retrieved for this decision, but the verifier enforces it regardless, trims the command to 25.5 C, and records why. The next hour completes the move to 26 C.

## Detailed findings

### 1. Cost, demand and comfort by climate

| Climate | Controller | HVAC energy cost | Demand charges | Total bill | On peak demand kW | Comfort violations K·h | Mean PPD % |
|---|---|---:|---:|---:|---:|---:|---:|
| Chicago | Fixed setpoints | 4,802 | 4,140 | 14,726 | 26.3 | 0.0 | 5.8 |
| Chicago | Timetable | 4,414 | 4,605 | 14,802 | 27.6 | 246.9 | 6.1 |
| Chicago | Timetable with tariff rules | 4,054 | 4,535 | 14,372 | 27.6 | 250.5 | 6.3 |
| Chicago | ZoneMind AI | 3,736 | 4,083 | 13,602 | 20.3 | 18.8 | 6.3 |
| Tampa | Fixed setpoints | 3,598 | 4,098 | 13,464 | 25.7 | 0.0 | 5.9 |
| Tampa | Timetable | 3,248 | 4,175 | 13,190 | 26.0 | 52.5 | 6.0 |
| Tampa | Timetable with tariff rules | 2,713 | 3,916 | 12,396 | 18.7 | 57.4 | 6.4 |
| Tampa | ZoneMind AI | 2,549 | 3,920 | 12,237 | 20.8 | 5.5 | 6.4 |
| San Francisco | Fixed setpoints | 1,036 | 2,896 | 9,704 | 19.4 | 0.0 | 6.3 |
| San Francisco | Timetable | 909 | 3,136 | 9,817 | 19.4 | 36.7 | 6.7 |
| San Francisco | Timetable with tariff rules | 857 | 3,247 | 9,876 | 17.0 | 36.7 | 6.7 |
| San Francisco | ZoneMind AI | 678 | 3,022 | 9,472 | 16.6 | 5.9 | 7.4 |
| Golden | Fixed setpoints | 4,064 | 3,961 | 13,800 | 26.7 | 0.0 | 5.9 |
| Golden | Timetable | 3,664 | 4,412 | 13,851 | 28.6 | 151.3 | 6.1 |
| Golden | Timetable with tariff rules | 3,346 | 4,342 | 13,464 | 28.6 | 151.7 | 6.3 |
| Golden | ZoneMind AI | 3,000 | 3,883 | 12,658 | 20.8 | 24.4 | 6.5 |

ZoneMind AI has the lowest bill in all four climates. Relative to the plain timetable the bill reduction is 8.1 percent in Chicago, 7.2 percent in Tampa, 3.5 percent in San Francisco and 8.6 percent in Golden. Relative to the hand tuned tariff timetable it is 5.4, 1.3, 4.1 and 6.0 percent.

The Tampa result deserves a direct reading. Hand written tariff rules capture most of what is available in a climate that cools every afternoon of the year, and they hold on peak demand slightly lower than ZoneMind AI does (18.7 kW against 20.8 kW). The agent's advantage there is comfort and occupancy awareness, not tariff response. In the heating climates the hand written rules do nothing for half the year, and the gap is wider.

Comfort violations are measured as degree hours outside the 20 C to 26 C envelope while a zone is actually occupied. The timetable accumulates them on cold mornings when a fixed two hour start is too short, and whenever people arrive before or stay after the programmed hours. The agent follows bookings and sensors, so it recovers each zone for its own arrival time and stays with late occupants. Mean predicted percentage dissatisfied, computed with the ISO 7730 method, rises by between 0.2 and 0.7 points under ZoneMind AI because it deliberately uses more of the permitted envelope during peak windows. That is the price of the saving and it stays well inside the range normally regarded as comfortable.

### 2. Where the saving comes from

<img width="1718" height="615" alt="monthly_chicago" src="https://github.com/user-attachments/assets/567c6d15-96d6-45c8-ac8a-7f06d06afe1f" />


In Chicago the agent uses almost exactly as many HVAC kilowatt hours as the timetable (27,232 against 27,265) yet spends 15.3 percent less on HVAC energy and cuts on peak demand by 26.5 percent. The saving is not from using less; it is from using it at better times and in fewer rooms, then spending part of the gain on proper recovery before people arrive. Across the portfolio HVAC consumption falls by a modest 3.3 percent while HVAC energy cost falls by 18.6 percent. Anyone evaluating a controller of this kind on kilowatt hours alone would conclude it does very little, and would be wrong.

The fixed setpoint baseline is a useful warning. Never setting back uses 24 percent more HVAC energy than the timetable, but its total bill is almost identical (51,694 against 51,660) because steady operation avoids the morning recovery spike that sets the facilities demand charge. With heat pumps and demand charges, a naive set back can cost as much as it saves.

### 3. Retrieval: decomposition matters more than the ranker

<img width="1291" height="534" alt="retrieval" src="https://github.com/user-attachments/assets/9ab1c6f1-9e02-46c6-9cd3-8121b56fbf1d" />


Ground truth for retrieval needs no hand labelling. A document is relevant to a decision exactly when one of its directives applies to the situation, so every one of the 35,040 decisions is a labelled test case.

| Retriever | k=2 | k=4 | k=6 | k=8 | k=10 | k=12 |
|---|---:|---:|---:|---:|---:|---:|
| BM25, decomposed | 0.827 | 0.965 | 0.989 | 0.994 | 0.997 | 0.999 |
| LSA dense, decomposed | 0.855 | 0.966 | 0.987 | 0.990 | 0.995 | 0.998 |
| Hybrid, decomposed | 0.829 | 0.968 | 0.989 | 0.991 | 0.996 | 0.999 |
| Hybrid, single query | 0.775 | 0.879 | 0.916 | 0.943 | 0.982 | 0.995 |

On this corpus the choice between lexical, dense and hybrid ranking is immaterial. What matters is whether the situation is sent as one query or as one query per facet. At four documents per decision, decomposition lifts recall from 0.879 to 0.968. A control situation is several things at once, and a single long query lets the dominant topic crowd out the rest. Hybrid fusion is kept as the default because it costs nothing here and is the safer choice once a corpus grows and vocabulary diverges, but this project provides no evidence that it beats BM25 alone, and the README does not claim it.

Because the reasoner can only act on what it was shown, retrieval misses appear directly in the building. Rerunning the year with a budget of four documents:

| Retriever at k=4 | Document recall | Mean annual bill | Decisions repaired by verifier |
|---|---:|---:|---:|
| Hybrid, decomposed | 0.968 | 11,974 | 161 |
| Hybrid, single query | 0.879 | 12,163 | 557 |

Nine points of recall cost 1.6 percent on the bill and more than triple the verifier's workload, as it catches limits that the missing documents would have told the reasoner about. With retrieval removed entirely the agent holds safe default setpoints at all times, which reproduces the fixed setpoint baseline and raises the bill by 7.4 percent. Comfort does not suffer in any of these cases, because the fail safe is comfort first.

<img width="1871" height="550" alt="ablations" src="https://github.com/user-attachments/assets/8263f0c7-cd8f-4631-976e-5884bf750541" />


### 4. Verification under fault injection

Language models occasionally return truncated JSON, cite documents that do not exist, or propose values outside any sensible range. A fault injection backend corrupts a chosen share of otherwise correct outputs with nine such failure types so the defences can be measured without waiting for a real model to misbehave. Over a Chicago year, 1,325 of 8,760 outputs were corrupted.

| Variant | Malformed outputs recovered | Invented citations flagged | Commands breaking a hard limit at the plant | Comfort violations K·h | Annual bill |
|---|---:|---:|---:|---:|---:|
| No faults, verifier on | 0 | 0 | 0 | 21.9 | 13,498 |
| Faults injected, verifier on | 150 | 138 | 0 | 85.2 | 13,676 |
| Faults injected, verifier off | 150 | 138 | 3,871 | 273.2 | 13,842 |

<img width="1862" height="592" alt="robustness" src="https://github.com/user-attachments/assets/c2df93e0-15e2-4313-a527-841ecae8be54" />


With the verifier in the loop no command that breaks a hard limit reaches the plant, all 150 malformed outputs are replaced by the deterministic fallback, and all 138 invented citations are flagged. Comfort violations still rise from 21.9 to 85.2 K·h. The verifier guarantees that every command is permitted; it cannot make a bad command good. A corrupted proposal that deepens a set back during morning recovery is inside every limit, and the zone is cold when people arrive. This is the honest boundary of rule based verification, and it is why the fallback reasoner and grounding checks exist alongside it.

In normal operation the verifier is quiet. It repaired 122 of 35,040 decisions, about one in 290. Most were rate of change limits, such as the first hour of a critical event in the trace above. The rest were unexpected walk in occupancy and the core zone ceiling on occasions when its policy document was not retrieved.

### 5. Episodic memory: a measured null result

The agent tunes three daily strategy knobs from memory: recovery lead time, peak strategy depth and set back depth. It was given a full commissioning year of randomised exploration on perturbed weather with a different occupancy draw, then evaluated on the measured year.

| Climate | Commissioned memory | No memory | Memory without commissioning |
|---|---:|---:|---:|
| Chicago | 13,602 / 18.8 | 13,498 / 21.9 | 13,521 / 18.2 |
| Tampa | 12,237 / 5.5 | 12,212 / 5.5 | 12,277 / 5.2 |
| San Francisco | 9,472 / 5.9 | 9,477 / 6.0 | 9,461 / 3.9 |
| Golden | 12,658 / 24.4 | 12,650 / 23.4 | 12,783 / 19.4 |

Each cell is annual bill / comfort violations in K·h. On average the commissioned memory raised the bill by 0.3 percent and lowered comfort violations from 14.2 to 13.7 K·h. That is no effect.

<img width="1945" height="967" alt="memory" src="https://github.com/user-attachments/assets/0a92233e-9042-4395-9fe1-c0a55e26539f" />


The sensitivity study explains why. Holding each knob at each value for an entire year shows that the best alternative to the defaults improves the daily score by less than one percent in every climate (the largest gain is 0.87 percent, from a three hour lead in Chicago), while the worst choice costs up to 3.3 percent. A one percent effect is a few tenths of a currency unit per day, against day to day variation from weather and attendance that is many times larger. One year of daily episodes cannot resolve that reliably. An earlier version of the tuner that always acted on its best estimate made the bill between one and two percent worse in the two climates tested; the shipped version leaves a default only when the estimated gain exceeds one standard error, which removes the harm but leaves little to gain.

The broader lesson is that the knowledge base had already absorbed the adaptation. The sequences condition on weather, bookings, sensors and tariff every hour, so there was little left for a daily tuner to find. Memory of this kind should pay off where documents are silent or wrong, for example a building whose real recovery time differs from what its sequences assume. Learning zone level recovery rates from past mornings, a physical quantity with far less noise than a daily bill, is the first item on the roadmap.

### 6. What the tariff structure does to strategy

During development the tariff had a single demand charge on the highest quarter hour at any time. Under that structure pre cooling raised bills: it moves load into the early afternoon, when lighting and equipment are also at their highest, and creates a new peak that costs more than the energy it saves. In a development run for Tampa the hand written tariff rules cost about 4 percent more than the plain timetable. The reported experiments use a facilities charge plus a separate on peak charge, which is how many commercial tariffs reward load shifting. `configs/flat_demand_tariff.yaml` restores the single charge so the effect can be reproduced. A strategy library that is right for one contract can be wrong for another, which is an argument for keeping tariff knowledge in documents that can be replaced when the contract changes.

## What this means for a building owner

For this 800 square metre office the saving against today's timetable is about 920 currency units per building per year, a little over one unit per square metre, with nine in ten comfort violations removed. That is a modest sum for one small building and a meaningful one across a portfolio, and it requires no new plant: the agent only writes setpoints that the existing system already accepts. The larger commercial argument is risk. Every command is traceable to a governed document, every limit is enforced by a component that does not depend on the model, and the full reasoning for any hour of the year can be printed on demand. That is what a facilities director or an insurer needs before any learning system is allowed near live plant.

## Limitations

1. **No live language model in the results.** All reported numbers use the deterministic reasoner. The Anthropic and OpenAI compatible backends are untested against live endpoints.
2. **Simulation, not a real building.** The thermal network is a reduced order model. Latent cooling load is not modelled, which understates cooling energy in Tampa. Plant part load behaviour is simplified.
3. **The retrieval test is kind.** Facets are produced by templates that share vocabulary with the documents, and the corpus has 43 documents. The finding that rankers do not matter should not be generalised to large, heterogeneous corpora.
4. **Prose and directives are maintained by hand.** Nothing checks that the two say the same thing. A language model backend acts on the prose and the deterministic reasoner on the directives.
5. **One building and one tariff family.** The tariff is illustrative, with values typical of North American commercial contracts. Savings will differ under other contracts, as section 6 shows.
6. **One random seed.** Occupancy and forecast errors come from a single seed per scenario. Differences of a few tenths of a percent between variants are within noise.

## Repository layout

```
configs/                  default.yaml and example overrides
data/weather/             four TMY3 weather files (8,760 hours each)
data/knowledge_base/      43 operating documents with directives and constraints
src/zonemind/
    data/                 calendar, EPW reader, solar geometry, weather, occupancy, tariff
    sim/                  thermal network, plant and environment, comfort indices
    knowledge/            loader, chunker, BM25, LSA embeddings, hybrid retriever
    control/              situation builder, verbaliser, verifier, baselines, agent
    llm/                  schema, parser, prompts, backends, offline reasoner, fault injection
    memory/               episodic store and knob tuner
    eval/                 runner, metrics, experiment suites, figures, report
    safe_eval.py          whitelisting expression interpreter
    cli.py                command line interface
tests/                    42 tests
docs/                     figures and the knowledge base authoring guide
results/                  saved results of every experiment reported above
```

## Quick start

Python 3.10 or later. Run commands from the repository root.

```
pip install .
zonemind info
pytest
```

Reproduce every table and figure in this document (about twenty minutes on one core):

```
zonemind all
```

Individual suites are `benchmark`, `ablations`, `robustness`, `retrieval`, `sensitivity`, `budget`, `figures` and `report`. The report command writes every table to `results/summary.md`.

Print the full decision trace for one hour, by default 14:00 on a July afternoon in Chicago:

```
zonemind explain
```

Simulate a single controller as described by the `run` section of the configuration:

```
zonemind run
```

## Using a language model

A run is fully described by a configuration file layered over `configs/default.yaml`. Two examples are provided, each covering three July days (72 model calls).

```
pip install anthropic
export ANTHROPIC_API_KEY=your_key
export ZONEMIND_CONFIG=configs/anthropic_three_days.yaml
zonemind run
```

For a local model served through an OpenAI compatible endpoint, edit the URL and model name in `configs/local_model_three_days.yaml` and point `ZONEMIND_CONFIG` at it. Every decision trace is written to the audit file named in the configuration. If a model's output cannot be parsed, the agent falls back to the deterministic reasoner for that hour and counts the event.

## Extending the project

1. **Add or change operating knowledge.** Edit or add a file in `data/knowledge_base`. The format is described in `docs/KNOWLEDGE_BASE.md`. Unknown variables and unsafe expressions are rejected when the knowledge base loads.
2. **Add a location.** Place any EPW weather file in `data/weather` and register it under `climates` in the configuration.
3. **Change the building, plant or tariff.** Every physical and commercial parameter is in `configs/default.yaml`.
4. **Use neural embeddings.** Install `sentence_transformers` and set `retrieval.dense_backend` accordingly.

## Data sources

Weather: TMY3 typical meteorological year files for four stations, from the weather folder of the EnergyPlus project maintained by the National Renewable Energy Laboratory. Occupancy, tariff and building parameters are synthetic and fully specified in the configuration. Knowledge base documents were written for this project; they describe common industry practice in original wording and do not reproduce any published standard.

## Licence

MIT. See `LICENSE`.
