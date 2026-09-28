# Wake/Dream cycle (from 2026-09-28)

Open-ended, LLM-assisted and nondeterministic on the Dream side; deterministic and parallel on the Wake side.
It runs until model capability is exhausted or a fixed point is reached: a Dream pass that proposes nothing admissible.

## DREAM (cloud Claude session, nondeterministic)
1. Read the current mechanism ontology (`results/ontology/mechanism_ontology.json`): the groups, each with a definition, parameters, detector, members, and which members are still uncovered.
2. For the largest groups not yet covered, write or extend ONE parametrised primitive per group. The contract is that it covers the whole group. Members it cannot cover are proposed as a split or reassignment, never special-cased.
3. Revise the groups: apply the splits, assign residual tasks through the feature spectrum, and merge groups when one primitive covers both.
4. Freeze a candidate probe (`tools/m1b/vNN`) and emit WAKE jobs (`wake_jobs/*.json`).

## WAKE (WSL, deterministic, all cores): `tools/wake/WAKE.md`
- Run the full G-DSL stratum over training and dev-eval half A, count half B, and report exact solves, wrong-first counts and timeouts.

## ADMIT (cloud)
- Compose the lattice and G-DSL results. Admit if there are no regressions and there is a gain on training or half A.
- Half B is counted once per cycle and reported as a count only.
- Admitted primitives become spectrum features: "primitive P fits all training pairs" is an exact detector for its group. The group spectra and the spectral clustering are recomputed from them (vertical closure, upward).
- Public-eval parity runs in the cloud, and one notebook per day goes to Kaggle.

## Fixed-point criteria
- Two consecutive Dream passes with no admitted primitive and no accepted regrouping.
- Or every remaining group is residual, meaning no generic mechanism is known.
