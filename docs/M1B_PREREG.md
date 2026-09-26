# M1b — LLM-in-the-loop enrichment cycles (pre-registered 2026-09-26, before any perturbation)

The LLM (Claude) plays the human reviewer of the train-time loop: it reads gap tasks and proposes
**conceptual perturbations**; the deterministic probe (occupancy.py) realizes and measures them.

## Perturbation lanes (the only admissible edits)
- `new_differentiator`: a new prior attribute, defined only from ARCGraph node geometry/topology/number
  and property chains over other nodes. No task ids, no task-specific constants, no output data.
- `new_hypothesis`: a new change label (action). Amended 2026-09-26 on the user's correction: the DSL
  is meant to evolve, so a hypothesis may introduce a **new DSL primitive**, not only reuse one that
  ARCGraph already registers. Conditions: it is a typed, parameterized operation over ARCGraph nodes;
  its parameters come only from the concept vocabulary (prior layer, chains, lattice concepts); it is
  registered by name in the vocabulary (never inlined per task); it is admitted by the same MDL/no-regression
  rule. Existing ARCGraph operations are preferred when they already express the concept.
Every proposal, whether admitted or not, is appended to `perturbations.jsonl` with rationale,
source gap tasks, and measured deltas.

## Data discipline
- Proposals may be motivated only by: the 1000 training tasks and dev-eval half A (50 tasks, deval_a.txt).
- Dev-eval half B (49 tasks, deval_b.txt) is **held out**: counts only, measured once per cycle.
- The 21 sealed tasks are not touched.

## Admission rule (per perturbation)
Admit iff, versus the current frozen vocabulary:
1. zero regressions on training test-exact and on half A; and
2. training test-exact +1 or more, or half-A test-exact +1 or more, or training occupancy +3 or more;
3. the rule list of every previously solved task does not grow (MDL non-increase on solved cases).
Rejected perturbations stay in the ledger.

## Cycle exit
A cycle ends after at most 6 proposals. Report: training T, half-A E_A, held-out E_B.
Success signal for the Kaggle goal: E_B >= 1 (a solve on unseen ARC-AGI-2 eval tasks).
Stop enrichment after 3 cycles with E_B = 0 and reassess.
