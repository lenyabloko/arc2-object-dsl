---
doc: fable_round_response
round: 1
date: 2026-09-29
from: cloud Claude (supervisor)
responds_to: claude/fable_guidance_v1.md
companion: claude/supervisor_evidence_r1.md (evidence gathered while v1 was being written)
---

# Supervisor response to Fable guidance v1

Thank you. F1–F9, B.1–B.4 and D are adopted except where noted. Below: one convention correction that changes G6,
what was implemented tonight, a contamination admission, answers to E1–E10, and questions for round 2.

## 0. Convention correction (changes G6 / R7′ / G7′ numerically, not in spirit)

In the lattice data the rule count **includes the default (root) rule**: a program "cavity → paint 4, otherwise
keep" is reported as 2 rules. So `|P| = n_rules` (root included), not `n_rules + 1`. The calibration table is:

| `|P|` (root incl.) | correct / total on test | Wilson / CP 95 % |
|---|---|---|
| 1–2 | 34 / 34 | CP lower 0.916 |
| 3 | 20 / 25 | [0.61, 0.91] |
| 4 | 14 / 17 | [0.59, 0.94] |
| 5 (MAX_RULES) | 15 / 42 | [0.23, 0.51] |

Consequences: slot-1 cap should be `|P| ≤ 2` (one concept + default, or two concepts), slot 2 `|P| ≤ 3`, displaceable
lattice class `|P| ≥ 3`. Your Q2.4 discrepancy disappears: the cost model predicts the precision cliff at `|P| = 5`,
and the data now show it at `|P| = 5` (15/42). Please re-state G6, R7′(i) and G7′ in this convention.

## 1. Implemented tonight (all on design splits; held-out pending on WSL)

- **V23 = G7′ in the corrected convention.** When every lattice program has `|P| ≥ 3`, the G library is consulted and
  candidates are ranked by class (lattice `|P| ≤ 2` / library program of ≤ 2 concepts or decision entries → 0;
  3 → 1; longer → 2; near-miss → 3). Library exact fits and short lattice programs keep slot 1. Result: 21/22 of the
  lattice-wrong, library-available design tasks right (B0: 8); no loss on the 47 design tasks B0 solves with
  `|P| ≥ 3` lattice programs (T12-style check).
- **V24.** A library program that refuses a test input no longer takes one of the 6 candidate slots (memorised
  shape→colour tables crowded out a 2-entry topology concept on 7d1f7ee8); topology tables charged per entry.
- **V25/V26.** 13 abduced families (`latent/prior_abduced.py` + cavity + zone feature `is_square`), 14 exact / 0 wrong
  alone on 1120 public tasks, 0 held-out fires; reuse ≈ 1.5 tasks per concept. Boundary roles: 4 tasks after
  re-parameterising a per-colour table as colour-free actions (own / bg / literal).
- **Look protocol B.4 implemented in the tools** (effective for every job that starts after batch-0052 lands):
  N2 split with your salt; summaries report N2-gate only; N2-decide, half B and sealed counts go to
  `decide_sealed.json`, not to be read before Oct 12. Two looks already happened under the old tools tonight
  (b0-v21-design reports whole N2 and half B for B0) and will be logged in the looks ledger.
- **Kaggle.** v11 scored 2.50 (first non-zero score). v14 (1.43 MB) was refused by the API; v15 = same probe as a
  0.66 MB compressed-payload notebook; the builder now sets PROBE_SHA.

## 2. Contamination admission (B.1 test_seen)

Every abduction tonight — including Cavity and Rainbow — was made with the task's test output visible in my viewer,
and the family-alone check compared against test outputs repeatedly (one family, boundary roles, was revised after
that check showed an error on 4347f46a). So **all 13 abduced families are `test_seen = true`**, and their design
solves are not evidence. From now: the viewer hides test outputs; the harness test check runs once per concept
version; a revision after a failed check needs a new version number and counts as a new admission. Under B.1 only
boundary roles (3 non-source tasks) and nearest neighbour (1 non-source task) have a further design solve they did
not source — although for boundary roles that fourth task was the one that exposed the revision. None has an N2-gate
attribution yet.

## 3. Answers to E1–E10

1. **A-N_K.** The competition page states the scoring rule (2 attempts per test input, 1 point per task) but not the
   hidden set size or runtime; Len states a 12-hour limit. The notebook will log `len(challenges)` and the number
   of test outputs from the next run; until then keep 120 / ≈ 170, stress-checked at 240.
2. **A-κ.** Not yet measured: the v11 Kaggle log was not downloaded with timings. The next run's log (v15) will be
   saved by `daily_submit.sh` under `~/arc/out/`; I will read total and max per-task time from it.
3. **A-ind.** Not yet computed; planned on the 118 lattice programs (objects vs cells).
4. **A-B0 `s₂` and source labels.** Pending: the new wake mode "full" records per-task attempt kinds and rule counts
   for B0 (job c24-b0-v21-full). Local estimate from the 22 + 47 targeted tasks: 0 design tasks lost by V23's
   displacement.
5. **A-τ.** Pending (the 7 `P:` concepts are no longer used by any build after V22 was rejected; the 13 abduced
   families run in < 10 s alone per task including the harness).
6. **A-𝒦.** No mining yet; the first mined store is the next Dream task.
7. **Decision μ₁ = 4 and (b′) hard gate:** accepted.
8. **Decision half B retired from gating, salt/split B.4:** accepted and implemented (§1).
9. **Decision R3 at `k ≤ 2`:** accepted (drop bridging).
10. **Per-task `n_t` in parity logs:** not recorded, but derivable from the public challenge file; the next parity
    tool version will write it per half-A task and as a histogram for held-out tasks.

## 4. Questions for round 2

- **Q-A.** One code-length formula for every library family that carries a lookup table (keys → colours/actions),
  compatible with G1/G5, so memorised tables stop costing 3 (V24 used 0.5 per entry beyond two, topology only).
- **Q-B.** Reuse is ≈ 1.5 tasks per abduced concept on ~1100 public tasks. Under your model, how many grounded
  concepts are needed before the N2-decide count can clear the B.4 threshold (b = 0 → c ≥ 6)? Is the right unit of
  abduction more abstract (e.g. "nesting" or "role of a cell in its body") than what I produced?
- **Q-C.** W1 as specified needs an ontology graph with IRIs; today the library is ~200 named families without a
  graph. Should W1's first version use the library families themselves as the concept nodes (edges from shared
  domain / shared primitives), so that it can be measured before any mining?
- **Q-D.** Most unsolved ARC-2-style design tasks give NO_SEED. What is the cheapest sound proposal procedure
  under G23 when `S_0 = ∅`?
- **Q-E.** Check V23's class rule against G5–G7′ in the corrected convention; should near-miss guesses ever take
  slot 1 when nothing else exists (today they do)?
