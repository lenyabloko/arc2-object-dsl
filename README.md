# arc2-object-dsl

A **symbolic** solver for [ARC-AGI-2](https://arcprize.org/): for each task, it infers a short
program over **ARCGraph abstract objects** from the task's own training pairs only, then runs that
program on the test inputs. It uses no neural network, no LLM at inference, no task-ID dispatch,
and no stored answers.

Goal of this repository: to put a symbolic, ontology-grounded solver on the ARC-AGI-2 map with a
non-zero hidden-set score on Kaggle.

## Status

| Candidate | Public eval (120 tasks / 172 slots) | ARC-2 training (1000 / 1076) | Kaggle hidden (public LB) |
|---|---|---|---|
| `9d446873` (single abstraction, 5 primitives) | 2/172 | 14/1076 | 0.00 (submission 56568989) |
| widened search (`search2.py`) | in progress | in progress | — |

Every Kaggle submission first replicates the frozen local result on the public evaluation set
inside the notebook, and stops if the predictions differ (`submission/v1`).

## Layout

- `candidate/`: the frozen solver bundle. `ARCGraph.py` and `image.py` provide ARGA-derived
  object abstractions and operations. `experiments/object_dsl_recovery/search.py` and
  `object_queries.py` hold the original bounded search and the typed relational queries.
  `search2.py` is the widened search.
- `submission/v1/`: the Kaggle competition notebook with the parity gate, plus `predict.py`.
- `tools/`: `predict2.py` (the widened driver), scoring and probes. `tools/wsl/` holds the sync tooling.
- `docs/`: north star, failure-mode analysis, convergence and ETA assessment, code review.

`candidate/extended_transformations/` is kept only because `ARCGraph.py` imports it. Its
named-mode grid transforms are legacy code, and the searches here do not use them (see
`docs/recovery_isolation_manifest.md`, Part 3).

## Reproduce

Put the ARC Prize 2026 competition files (`arc-agi_*_challenges.json`, solutions) in a folder `D`, then:

```bash
pip install numpy scipy networkx rdflib tqdm colorama
python submission/v1/predict.py --candidate candidate --challenges $D/arc-agi_evaluation_challenges.json \
  --out sub.json --log log.json
python tools/score.py sub.json $D/arc-agi_evaluation_solutions.json   # expects 2/172
```

## Provenance

This code was derived from a larger private repository (`arc_extended_arga`). Development is
assisted by Claude (cloud session) and published through `tools/wsl/sync_outbox.sh`: complete,
hash-verified batches only, secret-scanned, and never touching the sync tooling itself.
Kaggle submissions are made by hand.
