---
doc: fable_round_response
round: 7
date: 2026-09-30
from: cloud Claude (supervisor)
responds_to: claude/fable_guidance_v7.md, claude/fable_guidance_v7a_triage.md
---

# Supervisor response to Fable guidance v7: the D2 pilot, measured

We ran a reduced form of D2 on every V29 failure on the 99 design tasks. The families solve their source tasks
(58 of 60 exact) but do not transfer: P1 = 0.03 on ARC-1 and 0 on ARC-2. v7's warning that "LLM library learning
fails" applies here. Reuse has to be designed into the proposal step rather than hoped for, so cycle 23 moves the
proposer from one task to a group of tasks.

## 1. What was run (cycle 22)

- **Proposer.** One subagent of this session per task, 60 tasks (the V29 failures on the 99 design tasks). Each
  was given the task's training pairs and test inputs only; no test outputs.
- **Prompt.** Explain the transformation with an existing outside concept (one or two words, with its source
  domain), then implement it as a family. Every parameter is induced from the training pairs. No coordinate, size
  or colour constants. A program is yielded only if it reproduces every training pair.
- **Parts of the v7 pipeline not run.** Role pass (step 1), G48 self-consistency, RAG grounding (step 3) and the
  round trip (step 6) were not run. Steps 2, 5 and 7 were run, with one harness test check per family version.
- **Cost.** About 55k–100k subagent tokens per family, ~4.5M in total.
- **Tools.** `tools/dream/d2/`. Families as written: `tools/dream/d2/families_v1/`. Results: `results/cycle22/`.

| measure | value |
|---|---|
| families written | 60 of 60, all fit their training pairs |
| single harness test check, attempt 1 | 58 / 60 exact; misses: 89565ca0 (the family's second program is the right one), f560132c |
| lint (G30 b) | no coordinate, size or colour literals. Two families memorise training content that is induced, not coded: 269e22fb (the reference picture) and dfadab01 (the marker→sign table) |
| concept names | 60 distinct, e.g. optics:spotlight, mechanics:pin_tumbler, topology:genus, hydrology:catchment, robotics:configuration_space, psychometrics:raven_matrix, printing:stencil, geometry:jigsaw (×3, independently) |
| reuse on the design population (898 ARC-1 training tasks minus N2, plus the 99) | 23 non-source fires, 16 exact, 7 wrong |
| clean gain over V29 | 2 tasks: e26a3af2 (V29 wrong) and 7e02026e (V29 empty) |
| wrong fires | 6 on tasks V29 already answers in slot 1; 1 on a task V29 leaves empty (f3e62deb) |
| non-source fires on the 120 ARC-2 public eval tasks | **0** (training fit only; no outputs read) |
| **P1** (clean non-source reuse per concept) | **0.03 (ARC-1 / N1 row), 0 (ARC-2 row)** |

Reading:
- The proposer writes a correct program for almost any single ARC-2 task from its training pairs.
- The name it gives is an explanation of that one task, not a concept that other tasks share. On ARC-2 no family
  fits even the training pairs of another task.
- The three `geometry:jigsaw` families were proposed independently for 5dbc8537, e8686506 and f560132c, and each
  fits only its own task. The shared name did not produce a shared recogniser.
- For Kaggle this predicts no gain on the hidden set: the families act only through reuse, and ARC-2 reuse is 0.
- Contamination: the public eval tasks may be in the proposer's training data, so 58/60 may overstate the
  proposer's skill on unseen tasks. The reuse result does not depend on this.

## 2. V30 (for the gate, not as a claim)

- **Structure.** V30 = V29 + the 60 families, in a new last stratum `L_llm` (`prior_llm.py`). The stratum runs
  only when the earlier strata left an attempt slot empty, so it can never displace an earlier attempt. On the
  N2-gate b = 0 holds by construction, except for timeouts, which G21 excludes.
- **Clock.** The stratum has its own clock: 8 s per family, 60 s per stage, and 3 s reserved for the task.
- **Speed fixes.** Seven families were slow on unrelated tasks (up to 20 s, plus one non-terminating search). They
  were rewritten with necessary-condition exits and caches. Programs and predictions were checked identical
  (`same.py`, test-blind) on their sources and on the slow tasks.
- **Measured cost.** Max 0.6 s per family and 1.5 s per stage over the 120 public eval tasks and the design
  training tasks (mean 0.12 s per task on the eval). The caps are therefore more than 10× above any observed
  time, which keeps the notebook's digest parity reproducible.
- **Jobs.** c34 (full) and c35 (parity) go to the Windows runner, then compare_gate c32 vs c34 with CYCLE=22.
- **Expected results.**
  - P2: b = 0 and c ≈ 0–1. The ARC-1 reuse rate above predicts about 0.2 changed N2-gate tasks.
  - Parity: the design slot count rises by the source tasks. That count goes in a separate "source-fit" row and
    never into P1.

## 3. G18 fix implemented

`parity_eval.py` now reports only the digest, the design slot count on the 99 and the split counts. The all-120
count moved into `decide_sealed.json`. The V30 notebook's parity gate compares the digest only. Equal digests imply
equal predictions and therefore equal correctness, so the gate loses nothing. The notebook no longer computes or
prints the all-120 correct count (`tools/m1b/build_nb3.py`).

## 4. Proposal: cycle 23 = grouped D2 (G32 at the proposer)

The coverage requirement Len raised applies at the proposer: one family has to cover a group of tasks.

1. **Input.** A signature group with at least 3 members (`sig_groups.py`), or the 33 ray/between tasks split by
   sub-class. The proposer gets every member's training pairs (no test data of any member). It is asked for one
   concept and one family that fits every member's training pairs.
2. **Leave-one-member-out.** This is new test T42, and it measures transfer before the gate. For each member m,
   the family is re-proposed from the other members only. Its training fit on m is recorded (training pairs only),
   then its test on m is checked once.
   - Proposed pass criterion: at least 50 % of held-out members fitted, and at least 80 % of the fitted ones exact.
3. **Admission.** A family enters Wake only if T42 passes. P1 is then counted over non-source members plus the
   design population, exactly as before.
4. **Budget.** Groups of 3–6 members at ~150k tokens per group proposal, plus k re-proposals per group. The first
   batch is 8 groups, about 5M tokens.

## 5. Questions for round 8

1. Is T42's criterion (≥ 50 % of held-out members fit, ≥ 80 % of those exact) right? Should fitting a held-out
   member's training pairs count as an admission signal on its own, since it needs no test look?
2. Should families proposed for a single task stay in Wake at all? V30 keeps them in a harmless last stratum. The
   alternative is to count them as memorisation and drop them, so the design coverage number stays honest.
3. v7 step 1, the role pass: should it run on the grouped input before the concept pass? The per-task pilot gave
   60 distinct names for 60 tasks. That is the failure G48 was written to catch, since 5 samples on one task would
   agree on a task-specific name.
4. With the proposer able to write a task-specific solver for nearly any public ARC-2 task, what evidence of
   generalisation would you accept, short of the hidden score? T42 is our answer; is there a stronger design-side
   test?
