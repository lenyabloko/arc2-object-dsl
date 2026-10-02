---
doc: fable_round_response
responds_to: claude/fable_guidance_v12.md (00:10 EDT Oct 2)
date: 2026-10-02 (03:00 EDT)
from: cloud Claude (supervisor)
---

# Round 12 response

## 1. Decisions

| item | verdict | status |
|---|---|---|
| G68 restated (extended colour-role set; learned constant last, charged) | adopted | colour_roles.py extended; V35 puts the roles-only families before the literal passes (§3) |
| G70 Δ on test inputs | adopted, with a finding against its first branch (§2, T70) | implemented and measured |
| G71 lattice parents + sibling rule | adopted | mapping written; T71 measured with the asserted hierarchy |
| D39 roles-only family wins slot 1 | adopted as stratum order (L_priors4 before L_priors2 / L_priors3) | V35 at the gate (cycle 29) |
| D40 stop far-68 index variants; T67 names the generators | adopted | T67 below |

## 2. Results

**T66 blind A/B.**
- Len wrote 10 lines. 4 were on his hash-assigned tasks (7ed72f31, 4c7dc4dd, e2092e0c, a644e277). The other 6 were
  tasks of his choice from the 18 Claude cannot solve alone.
- The LLM side is Claude's existing one-off readings: the 10 hash-assigned LLM tasks, plus the same 4 tasks for a
  paired comparison.
- Every description was implemented by the same prompt (one subagent each, training pairs only) and measured by
  line_check on the 997 design tasks.

| comparison | Len | LLM | difference (95 % bootstrap) |
|---|---|---|---|
| same 4 tasks, paired: own exact / other exact | 3 / 1 | 3 / 1 | identical on all 4 tasks |
| hash-assigned halves: other exact per description | 0.25 (4 lines) | 0.20 (10 readings) | 0.05 [−0.55, 0.55] |
| all 10 of Len's lines vs the LLM half | 1.3 | 0.2 | 1.1 [0.0, 2.4], confounded by task choice |
| new over V32 on other tasks | 0 | 0 | — |

- **Reading.** On the clean comparisons there is no difference between Len's descriptions and Claude's.
- The higher reuse of Len's other 6 lines comes from the tasks he chose:
  - f3b10344 (rectangular channels between same-coloured shapes) solves 6 other tasks.
  - 0d87d2a6 (beams), 17829a00 (attraction) and d6542281 (exemplar completion) solve 2 each.
  - Every one of those other tasks is already solved by the build.
- **Own tasks.** Len's line solves 2dd70a9a, which Claude could not solve alone. The other five hard tasks did not
  solve:
  - f3b10344, 0d87d2a6 and f560132c fit the training pairs but miss the test.
  - 17829a00 and d6542281: the implementers report one training output that disagrees with the rest.
- Files: results/o0/t66_selection.json, results/o0/t66_result.json, tools/dream/o0/lines/, tools/dream/o0/lines_llm/,
  results/o0/lines_llm_ledger.jsonl.txt.

**T67 action-gap table.**
- 33 of the 45 nameable-but-failing tasks are now exact in the O0 ledgers. 7 of the 33 are solved only by the
  literal-colour passes, so they depend on D39.
- The 12 left, by missing generator:

| missing generator | tasks |
|---|---|
| on-stop clause for ray/slide (the ray exists; it has no action at its stop) | 13f06aa5, 758abdf0, fc10701f |
| virtual-anchor construction (targets no action can compute) | 1478ab18, e4941b18, c4d067a0 |
| legend as an ordered sequence or a shape table | 3e6067c3, b20f7c8b |
| split-and-explode | 4a21e3da |
| cellular automaton | b5bb5719 |
| docking acceptance rule | a25697e4 |
| colour-only gap | 14754a24 (fixed by the train_background role) |

- Of 98 family modules, 2 fit any of the 12 and both miss the test.
- docs/t67_action_gap.md, results/o0/t67_action_gap.json.

**T70 (G70 Δ on test inputs).**
- Branches: role pattern on 182 tasks; bbox ∪ border on 770 (size change 314, no exact pattern 352, budget 84,
  other 20).
- T59 parity still 4,153 / 4,153. W_mat max 141,332, mean 12,518. No grid over a cap.
- **Finding.** The Δ-restricted relations change Route A's slot-1 program on 35 of 621 tasks, not ≈ 0, all through
  allen / dir_rel. The training Δ is the target set, so relations restricted to it name the targets for free: a leak.
  With bbox ∪ border on every input (training included) the count drops to 3 / 621.
- **Proposal:** G70 uses bbox ∪ border on training and test inputs alike. The role-pattern branch stays for
  logging only.

**T71 (G71 parents + sibling rule, asserted hierarchy).**
- The mapping covers 117 emitted lattice names: Shape 10, Position 15, Colour 14, Scale 47, Relation 31. Not placed:
  pixel / object names, 420 detector atoms, selector keys, D11.
- The T-box re-export stays EL and regular (554 classes). Route A parity and T24 are unchanged.
- aabf363d: Shape (3 co-fitting siblings) beats Position (2), and φ_design picks sym_lr. The test agrees.
- b230c067: three Scale names outvote the lone shape name, and the pick (D10:largest_of_its_color) is wrong. Its
  training pairs do not separate size from shape.
- Result: 17 / 19 recovered (the two conjunctions, as before). One tie is resolved correctly; the other miss is
  explained. A taxonomy predicted from the exported axioms gives the same picks, so the ELK run should confirm
  rather than change this.

## 3. Build

- **V35 = V34 + L_priors4** (the 19 roles-only families plus colour_roles.py) placed before L_priors2 / L_priors3.
- It also removes the five held-out ids from three docstrings (D1; code identical, checked on the AST).
- Wake jobs: c44 (full) and c45 (parity); compare_gate CYCLE=29 against c42 (batch-0080, ORDERS seq 16).
- v20 (V34) goes to Kaggle tonight. v19's public score is pending.

## 4. Still blocked

- **T58 (ELK).** The Windows session's safety check needs Len's approval inside that session, or Len can use the
  Protégé GUI route. The re-exported T-box (with G71 parents) ships in batch-0080.
