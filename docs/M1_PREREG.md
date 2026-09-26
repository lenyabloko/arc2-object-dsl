# M1 — Occupancy milestone (pre-registered 2026-09-26, before any results)

Purpose: decide within days whether option 3 (prior-concept layer + per-task
conceptual lattice + RDR) can plausibly produce a non-zero ARC-AGI-2 score.

## Setup (frozen before measurement)
- Segmentation: existing ARCGraph abstractions (nbccg, ccgbr, nbvcg, nbhcg, mcccg).
- Case = one input node in one training pair; label = its change
  (keep / recolor(c | chain-valued) / remove / translate(dx,dy) / slide-to-contact(dir)).
- Attributes = fixed prior layer only (topology, geometry, number/extremes,
  property chains). No task ids, no per-task code, no output data at test time.
- Rule induction = FCA closure of each label's positive set; if not a concept,
  one RDR exception level from the closure of the counterexamples; ranking by
  minimal generator size (MDL proxy). Attempt 2 = second-ranked generator set.

## Metrics
- R: share of tasks whose training outputs are exactly reconstructible from node labels.
- O (occupancy): share of tasks where every label class is a lattice concept (<=1 exception level).
- LOO: share of tasks where every held-out training pair is predicted exactly.
- T: exact test solves (2 attempts) on the 1000 ARC-AGI-2 training tasks.
- E: exact test solves on the 99 non-sealed public-eval dev tasks (counts only).
- Sealed 21 tasks: not touched in M1.

## Decision thresholds on T (training test-exact)
- GO (build full option 3 toward Kaggle): T >= 50/1000 (5%) and E >= 1.
- MARGINAL (continue only with enrichment round from gap report): 20 <= T < 50, or T >= 50 with E = 0.
- NO-GO as primary path: T < 20 (search2 baseline level ~1.4%).
Baselines for comparison: v1 = 14/1076 slots on training; search2 = 2/158 on dev150.
