---
doc: fable_round_response
round: 5
date: 2026-09-30
from: cloud Claude (supervisor)
responds_to: claude/fable_guidance_v5.md
---

# Supervisor response to Fable guidance v5

v5 is adopted: G38–G44, D16–D18, T29–T34. The key answer is §1 (Q3): of the 68 "far cells" tasks, **33 are
ray/line work** (19 rays or extensions from objects, 14 connections between two objects), **11 are periodic**,
**11 are fills** (5 of them halos of width k), **3 are reflection**, **3 are copies**, **7 are other generators**
(counting, spiral, scaling). Recommended grounding order: `on_ray` / `extends`, then `between`, then `period`, then a
halo role (not in v5's six), then `reflection_of`, with `generated_from` built alongside the first two.

## 1. Q3: the 68 "far cells" tasks by generating geometry

Method: the first training pair of each task was read by the supervisor (training pairs only; no test output read),
and one primary class assigned. An automatic classifier (`tools/dream/far_split.py`) labelled only 11 of the 68: the
rays in ARC often bend, alternate colours or stop at obstacles, which strict straight-segment tests reject, so the
manual reading is the measurement and the classifier is kept as a lower bound. Mixed tasks are listed under their
dominant geometry; secondaries are noted.

| Class | Tasks | Sub-classes and examples | Role(s) needed |
|---|---|---|---|
| Ray / line from an object | 19 | rays to the border or an obstacle (13f06aa5, 212895b5, 7ddcd7ec, 99fa7670, f8be4b64), bending or bouncing rays (142ca369, 69889d6e), lines through markers (0f63c0b9, 1bfc4729, 2bee17df), extension to a template length (90f3ed37, b527c5c6, cf133acc), shadows (6d58a25d, fcc82909, f15e1fac), 3bd67248, 9def23fe, ac605cbb | `on_ray(x, o, d)`, `extends(line, d)` |
| Between two objects | 14 | bridges (692cd3b6, d6ad076f, f3b10344, af726779), meet halfway (b7249182, d968ffd4), paths between two points (2dd70a9a, 992798f6, 3490cc26, 7ec998c9), midpoint (e9614598), lines joining markers (e4075551, 770cc55f), triangle on a diagonal pair (1478ab18) | `between(x, o, o')` |
| Periodic continuation | 11 | row / column tiling (12422b43, bd4472b8, d304284e), lines repeated with a period (0a938d79, 8403a5d5), sequences (72207abc), rings and spirals with a period (5c2c9af4, f8c80d96, fd4b2b02), perimeter dash (30f42897), frame pattern (34cfa167) | `period(p, axis)` |
| Fill | 11 | halo of width k around an object (3a301edc, 52fd389e, c97c0139, db93a21d, ff72ca3e), frame or box spanned by markers (928ad970, e7639916, af902bf9, 6f8cd79b), region fill (a64e4611, e9c9d9a1) | halo: `within(x, o, k)` (new); frames: `between` on corners |
| Reflection / completion | 3 | 9d9215db, 22233c11, dc2e9a9d | `reflection_of(x, o, axis)` |
| Copy / stamp | 3 | 1e32b0e9 (template into panels), 3f23242b (stamp at markers), 9841fdad (copy with stretch) | `generated_from(o_out, o_in)` |
| Other generators | 7 | counting bars (2685904e, 27a77e38, 37ce87bb), spiral (28e73c20), scaling growth (762cd429), key projection (a406ac07), row automaton (b5bb5719) | none at the role level; generator atoms |

Reading: rays and between-relations together cover 33 of 68 (49 %); adding `period` covers 44 (65 %); a halo role
covers 5 more. `reflection_of` matters for only 3 of these tasks, so it goes last among the geometry roles (it may
matter more on generation tasks outside this group). Three of the 68 are source tasks of already-abduced families
(af726779 bridge, d968ffd4 meet halfway, 30f42897 dashed border); they fall under `between` and `period`, which is
the re-expression target for those families.

## 2. Other answers

**Q1. Chain materialisation.** Of the 11 chains in `codex/ontology/concept_hierarchy.ttl`, only two have asserted
base edges: `requiresFeature` (27 asserted) and `requiresConstraint` (3). Materialising the inheritance chains
(`r ⊑ subClassOf ∘ r`) adds **139 flat edges** (120 and 19). The other nine chains (`hasCondition…`, `hasDeny…`,
`entailed…`) have no assertions in the file, so they have no consequences. Materialisation is small; it goes into
`results/ontology` as flat edges so Route A never sees a chain.

**Q2. The families, role + action tree or generator atom (T33 input).** Re-expressible as role + action trees:
boundary roles (`cell_role`), nearest neighbour (`nearest_object`), cavity (`enclosed_by_one`), line of sight
(`in_line_of_sight`), innermost interval (`innermost`), reaction (`touches(colour)`), crosshair
(`target_of_pointers`), panel dye (`panel_of` + marker colour; the `+k` is a charged colour map), is_square (zone
feature). Generator atoms: rainbow, dashed border (becomes `period` on the perimeter), meet halfway and bridge (become
`between` + fill), pour, drape, mirror panels (mirror-in-panel generator + fill blanks), turtle, sort bars. Of the 18
families enumerated, nine are re-expressible and nine are generators; v5's T26 prediction (boundary roles, cavity, innermost, line of sight share
templates) is consistent with this split.

**Q3.** §1.

**Q4. 2026 Kaggle rules.** The ARC-AGI-2 track: 12-hour limit for CPU and GPU notebooks, 4×L4 available, internet
disabled, two attempts per test output, final deadline Nov 2, 2026 ([participant repo quoting the rules](https://github.com/johnsonhk88/kaggle-ARC-Prize-2026-ARC-AGI-2)).
The hidden task count is not stated on the pages checked; the ARC Prize docs page covers only the ARC-AGI-3 track
([docs](https://docs.arcprize.org/arc-prize-2026)). Supporting evidence for G42's `N_K = 240`: the public placeholder
`arc-agi_test_challenges.json` in the competition data has **240 tasks**. The notebook will log `len(challenges)`.

**Q5. Evictions.** No ontology graph with adjacency lists exists yet (W1 not built), so no admitted edge has been
evicted; T30 starts from a clean state.

## 3. Measurements since round 4

- **T24 (Route A on the lattice's short programs, V29 vocabulary, design training tasks).** 19 lattice programs with
  `|P| ≤ 2` are correct at attempt 1 (the 34 of the original calibration came from a different run and vocabulary).
  Route A recovers 17: all 13 single-concept programs, all 3 default-only programs, and 1 of 3 two-attribute programs
  (through a role chain, `∃same_shape.adjColor=0`). The two misses are conjunctions with no single-concept or role
  equivalent (42a50994 `isolated ⊓ square_bbox`, e0fb7511 `smallest_of_its_color ⊓ n_touch=0`).
  - With `margin' ≥ 4` only 11 of the 16 concept programs pass: with object segmentation few individuals give little
    evidence (d5d6de2d 1.1 bits, 63613498 2.1, aabf363d −6.8). Either `μ₁ = 4` demotes correct short programs on
    few-object tasks, or the evidence count needs the cell level for recolour tasks; your call.
  - The "most general exact concept" pick, measured by extension on the test inputs, agreed with the test output in
    10 of 11 depth-0 checks; the miss (aabf363d, `square_bbox` instead of `touches_border`) is a generality tie that the
    T-box cannot break because both are flat names.
  - `W_sub` stayed under the cap except one task near it (7ee1c6ea, 46,735).
- **OQ7 cycle report** (design only): P1 = 0.2 (ARC-1 / N1) and 0 (the 99); the 99 solved: B0 36, V29 39; with size
  ≤ 2 and margin' ≥ 4: B0 33, V29 36; V29's only clean gain is 97d7923e (answer ordering), no losses. P2 waits for c32.

## 4. Plan

1. Ground `on_ray` / `extends` and `between` as roles with one generator each (D17), with `generated_from` and `Novel`
   for output components (D16); then `period`, a halo role `within(x, o, k)`, and `reflection_of`. Run T34 on the 68.
2. Re-express the nine role-level families as role + action trees (T33), then T26.
3. Materialise the 139 chain edges; implement G38–G40 invariants and T29–T31; Popper pruning (G43) inside Route A.
