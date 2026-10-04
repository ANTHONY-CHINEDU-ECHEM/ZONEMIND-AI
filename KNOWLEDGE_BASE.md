# Writing knowledge base documents

Every file in `data/knowledge_base` is a Markdown document with YAML front matter. The prose is what the retriever indexes and what a language model reads. The front matter carries the same guidance in machine readable form.

## Front matter fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Short unique identifier, cited in every decision trace |
| `title` | yes | Repeated at the start of every chunk so chunks stand alone |
| `category` | yes | One of comfort_policy, sequence_of_operation, tariff, equipment, playbook, operations |
| `tags` | no | Keywords appended to the first chunk |
| `directives` | no | Operating instructions for the deterministic reasoner |
| `constraints` | no | Hard limits enforced by the verifier on every decision |

## Directives

```yaml
directives:
  - id: SOO05_D1
    priority: 40            # applied in ascending order, later refines earlier
    label: precool          # appears in the decision rationale
    when: "mode == 'cooling' and h_to_peak > 0 and h_to_peak <= 2 and occupied"
    set: {cool: "max(22.0, cool - precool_depth)", heat: "min(heat, 20.0)"}
    lockout: false          # true disables mechanical cooling (outdoor air only)
```

`when` and the values under `set` are expressions over the variables listed in `src/zonemind/variables.py`. They are checked against a syntax whitelist when the knowledge base loads, so a typo or an unsafe construct fails at index time, never during control.

## Constraints

```yaml
constraints:
  - {id: C_OCC_COOL, kind: bound, var: cool, max: 26.0, when: "occupied", reason: "..."}
  - {id: C_RATE, kind: rate, max_delta: 3.0, when: "occupied", reason: "..."}
  - {id: C_DEADBAND, kind: gap, min_gap: 2.0, reason: "..."}
  - {id: C_LOCKOUT, kind: flag, when: "occupied", reason: "..."}
```

The verifier loads every constraint from every document at start up. It does not depend on retrieval, so a limit applies whether or not its document was retrieved for a given decision.

## Keeping prose and rules aligned

The prose and the front matter must say the same thing. A language model backend acts on the prose; the deterministic reasoner acts on the directives; the verifier acts on the constraints. Write the prose section headed "When it applies" in plain operational language, because that is the text retrieval matches against the described situation.
