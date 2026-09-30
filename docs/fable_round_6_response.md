---
doc: fable_round_response
round: 6
date: 2026-09-30
from: cloud Claude (supervisor)
responds_to: claude/fable_guidance_v6.md, claude/fable_guidance_v7.md, claude/fable_guidance_v7a_triage.md, claude/plan_oct12_path.md
---

# Supervisor response to Fable guidance v6 (and v7 / v7a, plan to Oct 12)

v6 is adopted (G45, G5 low-evidence branch, G34 fallback at 80 %, D19, D20); v7 / v7a are adopted as the Dream D2
pipeline and triage rule; Len's plan to Oct 12 is adopted with the source-task correction in §4.
Tool: `tools/dream/routeA_v6.py` (design training tasks, V29 vocabulary; lattice pass cached).

## 1. Q1: the concept programs, E_obj, E_cell, L and test agreement

19 lattice programs with `|P| ≤ 2` are correct at attempt 1 on design training tasks: 3 default-only, 13 with a
single attribute, 3 with a two-attribute conjunction. Route A (with G45) recovers all 19: the 13, one conjunction as a
single role chain (63613498), and two conjunctions as nested tests.

| task | lattice rule | Route A pick | P | E_obj | E_cell | L | margin' | test agrees |
|---|---|---|---|---|---|---|---|---|
| 00d62c1b | color_least_common → recolour 4 | color_least_common | 2 | 74.9 | 395.8 | 12 | 62.9 | yes |
| 2a5f8217 | color=1 → recolour same shape | color=1 | 2 | 36.8 | 222.5 | 12 | 24.8 | yes |
| 3906de3d | color_least_common → slide up | bottommost | 2 | 28.3 | 267.2 | 12 | 16.3 | yes |
| 42a50994 | isolated ⊓ square_bbox → remove | smallest_of_its_color ⊓ isolated (G45) | 3 | 145.9 | 354.7 | 23 | 122.9 | yes |
| 63613498 | n_touch=0 ⊓ shape_shared → recolour largest | ∃same_shape.leftmost | 2 | 18.1 | 103.4 | 16 | 2.1 | yes |
| 67385a82 | smallest → keep | smallest_of_its_color | 2 | 22.8 | 124.1 | 12 | 10.8 | yes |
| 7ee1c6ea | inside_other → recolour same holes | ∃inside.largest_of_its_color (k fell back to 1) | 2 | 154.1 | 413.3 | 16 | 138.1 | yes |
| 810b9b61 | hollow_rect → recolour 3 | has_hole | 2 | 28.7 | 441.9 | 12 | 16.7 | yes |
| a5313dff | contextColor=2 → recolour 1 | contextColor=2 | 2 | 25.2 | 269.9 | 12 | 13.2 | yes |
| aabf363d | touches_border → remove | square_bbox | 2 | 5.2 | 158.3 | 12 | −6.8 | **no** |
| aedd82e4 | smallest → recolour 1 | smallest_of_its_color | 2 | 24.8 | 38.6 | 12 | 12.8 | yes |
| b1948b0a | color_most_common → recolour 2 | color_most_common | 2 | 53.5 | 125.8 | 12 | 41.5 | yes |
| b230c067 | shape_shared → recolour 1 | ∃aligned.shape_unique | 2 | 23.8 | 432.1 | 16 | 7.8 | **no** |
| c8f0f002 | color=7 → recolour 5 | color=7 | 2 | 40.2 | 89.1 | 12 | 28.2 | yes |
| d5d6de2d | color=2 → remove | color=2 | 2 | 13.1 | 476.2 | 12 | 1.1 | yes |
| e0fb7511 | smallest_of_its_color ⊓ n_touch=0 → keep | same (G45) | 3 | 157.2 | 401.9 | 23 | 134.2 | yes |

Readings:
- **T35 passes**: both conjunctions come back as `|P| = 3` nested tests (slot 2) and agree with the test. The first
  implementation spent the whole `W_sub` budget on them because it paired role-chain candidates; G45 now pairs
  depth-0 names with precomputed extensions (set intersections), 10.8k and 18.6k checks.
- **μ₁**: margin' < 4 on three picks (63613498 2.1 and d5d6de2d 1.1, both right; aabf363d −6.8, wrong). Only
  aabf363d is in the low-evidence branch (`E_obj < 8`), and its generality pick is wrong: the branch's precision on
  this sample is 0 / 1. T36 needs more low-evidence tasks than design training offers at `|P| ≤ 2` before the branch
  can reach slot 1; until then the branch stays slot 2. The two margin-failing right answers go to slot 2 by G5 —
  still scored on Kaggle.
- **Generality pick errors**: 2 of 16 (aabf363d, b230c067). Both are choices among many exact candidates (12 and 49)
  where the test-input extension and `φ_design` do not separate the lattice's concept from a coincidental one. With
  flat names there is no T-box order to break the tie; this is where the role vocabulary (and a real subsumption
  order) has to do the work.
- `E_cell` is 3–40 × `E_obj`; agreed with v6 not to use it (it would make every recolour task pass the margin).

## 2. Q2: do lattice `|P| = 3` programs become shorter or nested under Route A?

No. 8 lattice programs with `|P| = 3` are correct at attempt 1: 7 use two different actions (two concept nodes plus
the default; they stay `|P| = 3`), 1 (12eac192) uses one action for a disjunction (`smallest` or `size=2`); Route A
fails on it, as EL has no ∨ (C_t = `n_holes=0 ⊓ sym_lr ⊓ sym_ud`). None collapses to `|P| = 2`.

## 3. Q3 (T34 on the 33): not yet — the roles are grounded Oct 1–3 per the plan.

## 4. Cycle 21 closed; plan to Oct 12

- Gate release #0: compare_gate B0 (c24) vs V29 (c32) on N2-gate = `{b: 0, c: 0, n_changed: 1}` → V29 admitted, P2 = 0.
  V29 parity: digest 277d8cef, 52/172 (B0 49), max 60.7 s per task, 0 timeouts; notebook v16 takes the Oct 1 slot.
- **Plan correction (P1 accounting, G31).** The plan's "~20 clean solves from the 44 tasks" counts the tasks the
  roles are grounded on. Rule adopted: each role names ≤ 3 source tasks whose training pairs are read during
  grounding; the rest of its class is scored by the harness once per role version (like the test check). My
  first-training-pair reading of the 68 is logged as a design look (`results/cycle21/design_looks.txt`).
- **Grounding = parameterising what exists.** The lattice already has `ray` (8 directions, from every pixel, stop at
  obstacle or border) and `connect` (orthogonal, same colour) effect generators. The 33 ray/between tasks fail on
  parameters: bending or bouncing rays, colour sequences, stops at a template length, rays from bar ends only,
  endpoints of different colours, bridge width equal to the object extent, midpoints. `on_ray` and `between` are
  therefore one parameterised role each (D19), charged per parameter.
- **v7 open questions.** Harness model: this session proposes; G48's five samples run as subagents on a smaller
  model (bounded by G50). RAG corpus: Wikipedia first sentences fetched at proposal time, URL and date stored in the
  repo as the versioned snapshot (T40). Role pass once per cycle over all open groups: yes. V21's code was written
  by Codex and Claude; the "source domain" citations are external text, so the contamination risk is in proposal,
  not in provenance.

## 5. Protocol issue (G18)

Parity's `correct_of_172` counts all 120 public tasks, sealed included; together with the design counts on the 99
it would reveal the sealed count by subtraction. I have not done that subtraction. Proposed fix: parity summaries
report correct slots on the 99 and the digest; the Kaggle parity gate compares the digest and a hash of the correct
vector, and the sealed-inclusive count moves into `decide_sealed.json`.
