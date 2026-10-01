---
doc: fable_round_response
responds_to: claude/fable_guidance_v10.md, claude/fable_guidance_v10a.md
date: 2026-10-01 (14:55 EDT)
from: cloud Claude (supervisor)
---

# Round 10 response: the description lattice, measured

## 1. Decisions

| item | verdict | note |
|---|---|---|
| D29 one pipeline for all descriptions | adopted | 514 descriptions parsed: Len's lines, Claude's one-off readings, the 150 group specs, the 60 cycle-22 families, the 20 cycle-27 concepts |
| D30 the pile proposes, the design set admits | adopted | — |
| G58–G61 | adopted | G60: one parse per description, batched 86 per subagent call |
| D31 OWL 2 definitions + standard engines | adopted in principle; **engine blocked** | ELK / HermiT / owlready2 cannot be installed here: the egress policy blocks Maven Central and PyPI. Java 21 and rdflib 7.6 are present. Options are in §4. |
| D32 hierarchy active offline | adopted; waits on T58/T59 | — |
| D33 lcs / refinement replace menus | adopted for the next step | T54 below still uses declared menus (written before v10a arrived) |

## 2. Tests

| test | result |
|---|---|
| T53 parse + generalise (60 cycle-22 + 150 group specs) | **pass**: 189/210 = 90 % parse to a record with a schema; 14 distinct schema tops (≤ 20). The 21 returned under G61 are the residual groups and "to be defined" placeholders. Over all 514: one-offs 256/260, Len 23/24 (returned: "the first example does inverse"), concepts 20/20. |
| T62 cycle-22 by fragment | 22 single-definition, 38 two-definition (composition), 0 outside the fragment |
| T54 expand + ground 5 schemas to depth 2 | **pass on its own terms**: PATH 358, LINK 331, CYCLE 268, CENTER-PERIPHERY 293, SYMMETRY 271 = 1,521 nodes, all grounded (drawn on seeds 0–3; family fitted on 0–2 predicts 3). Caveat: one author wrote each schema's drawer and recogniser, so the round trip is close to a tautology. It shows the code is consistent, not that the shapes are ARC-like. |
| T55 index retrieval on the 68 far-cells tasks | **fail**: a fitting node exists for only 4 of 68 tasks (oracle; top-3 also 4/68: 0a938d79, 72207abc periodic; 2bee17df, 6f8cd79b). Your §9 limit is what happened: the synthetic inputs look like the vocabulary, not like ARC. |
| T56 redundancy | not run (moot after T55) |

**Contrast with cycle 27.** Cycle 27 built 19 prior families by anti-unifying Claude's one-off programs on real tasks, grouped by WordNet/VerbNet-style frames. They fit 34 of the far-68 tasks, but 33 of those are their own member (source) tasks and only 1 is not (7ddcd7ec). On the full design set they reach 112 non-member tasks, and 5 of those are new over V32. Neither route has shown transfer to unseen real tasks yet. The cycle-27 families are at the N2 gate now (c40/c41, compare_gate CYCLE=27).

## 3. Proposal (v10b)

1. **Ground on real grids, not synthetic ones.** A node enters the pile when its family fits a real design task that is not its source (training pairs only). Synthetic draws stay as a lint (G59), not as grounding.
2. **Menus from fitted values.** Take specialisation values from the parameters that real fits actually bind (the cycle-27 families record them) instead of declared menus. This is D33's refinement operator restricted to the observed A-box.
3. **Seed the top nodes with the cycle-27 families** (20 frames ≈ 14 schemas), since they are the real-grounded version of the schema nodes.

## 4. Engines (v10a)

- **Kaggle side.** The pure-Python stratified semi-naive Datalog evaluator is needed in any case. It is next (T59 parity on all design grids, then T63 notebook size).
- **Dream side.** ELK cannot be fetched here. Choices for Len:
  - (a) The WSL session downloads ELK (needs Java) and runs T58 there.
  - (b) EL classification in pure Python with the standard completion rules (CEL/ELK calculus), cross-checked by ELK once (a) is possible. This is a home-written implementation of a standard algorithm, which conflicts with "no bespoke inference".
- **Recommendation:** (a) for T58, with T59 in the cloud meanwhile.

## 5. Status

- V32 = notebook v18 goes to Kaggle tonight.
- V33 (cycle 27) is at the gate.
- Len's list is the 18 tasks Claude cannot solve alone. 314 tasks are marked one-off, and 150 of those are now covered by a prior family.
- Files: results/o0/v10_records.json, results/o0/v10_ground.json, results/o0/v10_index_far68.json, tools/dream/v10/.

## 6. Addendum (15:50 EDT): cycle-27 gate, T64, next steps

- **N2 gate, cycle 27:** compare_gate c38 (V32) vs c40 (V33) = {b 0, c 0, n_changed 1}, so P2 = 0. Every concept cycle so far (21, 22, 24, 25, 27) has P2 = 0.
- **Design set:** training 620 → 754, half A 42 → 44, half B 1 → 13, 0 lost. All 136 gains on training plus half A are member (source) tasks; the full solver gains no non-member task. Parity c41: digest de2bd55e, max 66 s, 0 timeouts.
- **Notebook:** v19 (V33) replaces v18 for tonight's slot, since V33 contains V32.
- **T64 (frames → schemas):** the 20 frames map to 12 of the 14 schemas. 11 frames are compositions of two schemas (e.g. kronecker_tiling = SCALE ∘ CYCLE, rectangle_from_delimiters = CONTAINMENT ∘ PART-WHOLE). Mapping in results/o0/t64_frame_schema.json.
- **Next:** T65, the second pass over fitted bindings with role-bound menus (G68), is starting for the 19 families. After that comes T55′ over the real-grounded pile. ELK on WSL (D35) is waiting for Len's OK to install Java.

## 7. Addendum (18:35 EDT): v10b tests T65 and T55′, cycle-28 gate, T59, T63

| test | result |
|---|---|
| T65 second pass (19 families specialised over fitted bindings, G68 role-bound values, widened test-blind) | **fail**: non-source fits 229 → 253 (+10 %, needed +50 %); non-source exact 150 → 170; distinct non-source tasks fitted 154 → 160 (exact 112 → 119); 1 new over V32 (a79310a0). Member fits 166 → 194, member exact 160 → 184. Most bindings that mattered were colour roles: "the colour new in every output", "most / least frequent", "background". Measured alone, the role-first order changed the first program on 3 tasks (one non-source exact lost); in the build the second pass runs after the first, so nothing is displaced. |
| T55′ index over the real-grounded pile on the 68 | **fail**: 5/68 have a fitting node, top-3 also 5/68 (0a938d79, 72207abc periodic; 2bee17df; 6f8cd79b; 7ddcd7ec by ray_cast_to_stop). Pile: 921 of the 1,521 lattice nodes fit at least one real design task (604 fit two or more; together they cover 81 design tasks), plus the 19 second-pass families, each indexed only for non-member tasks. The lattice fits are the same 4 tasks as in T55; the families add 1. |
| N2 gate, cycle 28 (V34 = V33 + second pass as stratum L_priors3 after L_priors2) | compare_gate c40 vs c42 = {b 0, c 0, n_changed 0}: **P2 = 0**. Parity c43: digest b6c6bfd8, design slots 74 → 85, half A 44 → 44, half B 13 → 19, 0 timeouts; max per task 103.9 s (V33: 66.5 s). |
| T59 engine parity (pure-Python stratified semi-naive Datalog vs the O0 item code) | **pass**: 4,153 / 4,153 design input grids hash-equal (166 skipped on both sides: more than 64 objects). 24 items, 147 rules, 81 strata (4 recursive). Standard-engine cross-check: rdflib SPARQL CONSTRUCT to fixpoint agrees on 140 / 140 grids, all 147 rules translated. W_mat mean 15,079, max 215,801; **2 grids exceed the G63 cap** (dominant: allen 47.8 k, dir_rel 40.0 k, rcc8_DC 39.8 k facts). **G62:** every rule has ≤ 4 body atoms, but 64 / 147 have more than 4 variables (max 10), mostly cell coordinates. 6 rules never fire on a design grid. Time per grid: Datalog mean 0.06 s, max 0.85 s (Python items 0.02 / 0.39 s). |
| T63 notebook with the evaluator | partial: engine + rules = 35 KB raw, **9.7 KB lzma** (≤ 100 KB). Materialisation per task (all input grids) on the 99 design eval tasks: mean 0.64 s, **max 2.33 s** (3 of 997 design tasks above 2 s, measured on a loaded machine). Not added to the notebook: nothing in Wake consumes the facts yet (G64), so "digest reproduces" is trivially true and was not run. |

**Reading.** Every concept cycle (21, 22, 24, 25, 27, 28) has P2 = 0. The second pass grew member coverage (+28) and
non-source fits only a little (+24). Real grounding keeps 61 % of the lattice, but it fits ARC-1 training tasks,
not the far-68 group. Both v10b routes now stand at 5/68 on the hard group.

**Questions for Fable.**
1. G62: should the ≤ 4-variable bound apply to description definitions only, not to the base O0 role rules?
   Coordinate rules need Y, X, Y2, X2 plus individuals.
2. G63: the cap is exceeded through the negative and all-pairs relations (rcc8_DC, allen, dir_rel over every
   cell–object pair). Options: do not materialise DC (it is the complement of connected) and dir_rel/allen over
   cells; or cap per relation.
3. ELK (D35): Len's home folder contains Protégé 5.6.1 and a Maven repository (folder names only, not opened).
   Protégé distributions usually bundle a Java runtime and the ELK reasoner, so T58 may need no download. It is
   waiting for Len's OK.

Files: tools/dream/o0/priors3/, results/o0/priors3_ledger.jsonl.txt, results/o0/v10_ground_real_*.json,
results/o0/v10_index2_far68.json, tools/datalog/ (engine.py, o0_rules.dl, t59_parity.py, sparql_check.py),
results/o0/t59_parity.json, results/o0/t59_sparql_check.json, tools/m1b/v34 (V34.txt).
