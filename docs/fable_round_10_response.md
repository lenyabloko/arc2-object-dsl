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
