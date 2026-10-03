---
doc: fable_round_response
responds_to: claude/fable_guidance_v21.md and v21a_lattice.md (Oct 2, 23:30 EDT)
date: 2026-10-03 (written 00:05–, EDT)
from: cloud Claude (supervisor), working overnight at Len's request ("continue overnight without more guidance ... with constraints defined by Fable")
---

# Round 21 response: T86″ no-go; |H| = 0 under the strict seen-list; marks is a definition; engine v4 built; the chance-fit control fails at depth 2

## 1. OQ-21.1: T86″ under v3, no-go

- **Setup.** Script tools/dream/o0/t86pp.py. Engine v3 frozen copy (sha 2c8f226e1fe3, asserted).
- **Population.** The 14 build-failing v3 fits minus the 6 checked in T86′, which leaves 8.
- **Rules as in T86′.** Empty slots per c42, R(S) order, one harness check per task.

| result | tasks |
|---|---|
| exact | 0 |
| wrong | 1 (stamp at centres, two distinct predictions placed) |
| empty | 7 (fits on the training pairs, but no prediction on the test input) |

**No-go** (the rule was ≥ half exact and 0 wrong). Nothing enters the stamp stratum. Results: results/o0/t86pp.json.

## 2. OQ-21.2 (first half): |H| after the seen-list

**The seen-list** (tools/dream/o0/t90_draw.py; results/o0/len_seen_list.json, 482 ids) covers every surface we can
account for:
- **Review page:**
  - members of every group Len decided on;
  - every task id in his decision, placement, cell, axis, task and feedback docs;
  - every task shown in the profile matrix;
  - the need-you list.
- **Phone page:**
  - his lines;
  - the line expansions;
  - the needs list;
  - the one-off list with Claude's readings, including the pre-strip copies of Oct 1–2.
- **Always:** the 14, dd2401ed and the 4 A/B tasks.

**Counts** (results/o0/t90_H_counts.json; the ids are sealed cloud-only, with sha256 in that file):

| stratum | count | note |
|---|---|---|
| H (strict, as C.4 defines it): build-failing design tasks not on the seen-list | **0** | Every build-failing task was on the phone page: on its needs list, or on its one-off list with Claude's reading. |
| H_loose: the same, not counting the phone one-off list (shown 40 at a time) as seen | 72 | all ARC-1 |
| H2 (C.4 fallback): design tasks Len has not seen, regardless of build status | 518 | all build-solved; 36 ARC-2 |

All 590 sealed tasks are excluded from every v4 development run below. The dev population is design minus the 14
minus the sealed tasks: 393 tasks, all already on Len's seen-list.

## 3. C.2: `marks` is a definition

- **Where it lives now.** tools/dream/o0/defs/marks.dl.txt: two rules over base relations, plus the helper
  predicates touches / top_left_of. Base relations: cell(Y,X,C), obj(O,Y,X), off(DY,DX). It is evaluated by
  tools/datalog/engine.py through tools/dream/o0/defrows.py. Every file in defs/ becomes a row of the same name.
- **Parity with the retired Python row.**
  - hash-equal on dfadab01's training inputs;
  - 0 mismatches over all 3,184 design training inputs (inputs only).
- **Shown to Len.** The review page (v149) shows the rendered sentence under the cell check, next to his words: "the
  marks are the single cells, except those touching a shape, unless the mark sits at that shape's top-left corner."
- **The Python row is gone.**

## 4. Engine v4 (situation_engine.py + scale_free.py)

**The two forms built.** Each is a depth-1 situation S′ filling the column's input slot (C.1; one recursion; depth ≤ 2):
- **seq:** HOW(input := S′@grid). The column acts on S′(X). This is the second step T89 pointed at.
- **map:** paste(input := S′@panel | object | part). S′ is applied to every sub-node in its box, and the results are
  pasted back. Cells outside every node never change; that is the parent's WHY.

**How each form is bound.**
- *map:* S′ is bound on the changed sub-problems of the training pairs, and accepted only if the pasted result
  reproduces every training output.
- *seq:* the inner candidates are the depth-1 candidates that make progress (not already exact). They are tried
  top-down, at most 8:
  1. specialisations of admitted elements (R ≥ 1 on dev, results/o0/v4_R_depth1.json) first;
  2. then by progress.
  The outer column is fitted exactly on (S′(x), y).

**v21a items.**
- B.1: top-down order, as above.
- B.2 / G86: S′'s WHY is checked on its sub-problem, and the parent's WHY on the parent's result.
- B.3: scale typing is by construction (the input slot is at grid scale).
- B.4: canonical keys sort the arguments (siblings unordered).

**Stamp WHY for grid-corner anchors, tightened.**
- The rule (round 20 §5): every unit cell must land inside the grid from at least two corners.
- I set it before the control ran, after seeing that 18 of the first 40 dev depth-2-only fits were grid-corner stamps.
- It removed 10 depth-1 dev fits.

**Prediction order.** Depth 1 before depth 2 (G2), then R, then the key.

**Dev counts** (393 tasks, training pairs only; results/o0/v4_design_depth2.json):

| | depth 1 | depth ≤ 2 | only at depth 2 |
|---|---|---|---|
| dev tasks with a fit | 54 | 82 | 28 (all seq) |
| build-failing dev tasks (67) | 7 | 8 | 1 |

**R(part), source excluded (B.3 / G85).**

| Len's part | R (dev tasks with a fit that uses it) | used by the first-ranked fit | needed (every fit uses it) |
|---|---|---|---|
| `marks` (definition) | 21 | 4 | 4 |
| `place := topleft` | 24 | 0 | 0 |
| `rest := cleared` | 58 | 24 | 3 |
| `uniform_line` (definition, §4a) | 0 | 0 | 0 |

- Most of the R count overlaps rows that already existed (an isolated marker is also a mark).
- The "needed" column is the honest reuse: marks 4 tasks, rest-cleared 3.
- All parts: results/o0/v4_design_depth2.json, summary.R_part.
- Fit-level reuse is not test-level reuse: none of this has met a test output.

**§4a. Len's second refinement, also as a definition.**
- key × tile, his words: "the entire tile is copied, but only into the block row (or column) marked by the keyed
  one-colour line of the input".
- It is now defs/uniform_line.dl.txt: the one row or column of the input that is all one colour.
- The tile column takes any definition row as its extent: the unit goes into the blocks whose index cell the row picks
  out, and empty blocks get one colour, the same in all examples.
- On 15696249 v4 fits `tile(extent := uniform_line, unit := input)`. Its test prediction equals the checked reading
  (the two were compared with each other; no second harness check).
- Dev depth 1 goes 54 → 55. R(uniform_line) = 0 so far: it stays a draft part under G85.
- The fg × disperse cell has no WHY yet, and its only words are "in all 4 directions". I did not turn my own reading
  into a schema element (G83).
- These additions came after the three control runs. The engine the controls measured is kept in
  tools/dream/o0/v4a_snapshot/ (situation_engine.py ba7c0843ed33, scale_free.py 1830772abd1d with G5).

**The page (v150)** has a "Machine profiles (scale-free engine v4)" panel on the Situations tab. It lists the 82 dev
tasks with a fitted tree in plain words: one level or two, and Len's parts' counts. It shows only tasks Len has
already seen; no sealed id is on the page's machine data (checked).

## 5. C.3: the chance-fit control fails

**Instrument.** tools/dream/density/v4_density.py: the same 1,330 ARC-GEN variants as T80 / P3, 5 per fitted ARC-1
task. The answer is the first fitted situation in prediction order that gives a prediction.

| | answered | pass@1 | wrong |
|---|---|---|---|
| depth 1 | 330 | 265 | 65 |
| depth ≤ 2 | 452 | 318 | 134 |

- **Depth 2 adds 53 right answers and 69 wrong ones.** Go needed wrong(d2) ≤ wrong(d1) + 2. **Fails.**
  results/o0/v4_density_summary.json.
- **Where the 125 depth-2 answers come from:**

  | depth-2 form | exact | wrong |
  |---|---|---|
  | seq with an outer stamp | 24 | 61 |
  | seq, other outer columns | 19 | 5 |
  | map (object / part) | 13 | 3 |

**B.4 / G5 was missing from that run.** The margin guard on composite programs was not yet implemented. I have now
implemented it as the bounds doc states it (scale_free.py, fixed before the rerun):
- individuals: input objects + change sites;
- a = 9;
- L = 12 bits per atom + 4 per row argument;
- margin′ = E − log₂|H≤|;
- μ₁ = 4, μ₂ = 0.

Typical margins on these tasks are 30–90 bits, so I expect it to filter little. The bounds doc already says G5 does
not bound related-but-wrong programs, and these look like that. **§5a. Rerun with the guard (spec-complete v4), same variants** (results/o0/v4g_density_summary.json):

| | answered | pass@1 | wrong |
|---|---|---|---|
| depth 1 | 327 | 262 | 65 |
| depth ≤ 2 | 435 | 305 | 130 |

- Depth 2 now adds 43 right answers and 65 wrong ones. **C.3 still fails.**
- G5 removed only 14 of the 125 depth-2 answers, as expected.
- So the depth-2 search fits by chance in the related-but-wrong sense: the outer stamp learns whatever residual the
  first step leaves. G5's null model does not cover that.

**§5b. Exploratory, pre-registered in OQ-21.5 before running: v4′ = map only (with G5), on a fresh draw** (the same
266 tasks, seeds v = 5..9, 1,330 new variants; results/o0/v4p_density_summary.json):

| | answered | pass@1 | wrong |
|---|---|---|---|
| depth 1 | 323 | 251 | 72 |
| depth ≤ 2 (map only) | 342 | 262 | 80 |

- Depth 2 adds 11 right answers and 8 wrong ones. **C.3 fails here too** (80 > 72 + 2).
- On dev, map adds no task at all beyond depth 1: all 28 depth-2-only dev fits are seq.

## 6. Reading

**Engine v4 as specified does not pass C.3, with or without G5. Neither form passes alone, on a fresh draw.**
- It fits more (dev 54 → 82, density answers 330 → 452), but the second level buys as many wrong answers as right
  ones.
- Nearly all the damage comes from one form: a learned stamp fitted to the residual of a first step.
- Map, the true scale-down form, is cleaner (16 exact / 8 wrong on the fresh draw) but adds nothing on real dev tasks.
- Under C.3, "v4 does not ship whatever H says". T90 is therefore **no-go before placement**, and I have not placed on
  H.
- B.5's Oct 12 position applies: the OQ7 proxy fails on both arms. The memo is v15 option (a), with:
  - the negative tiers, now including v4's depth-1 vs depth-2 table and C.3;
  - two positive findings: reviewer-authored definitions solve tasks the families fail (dfadab01 and 15696249, both
    now schema elements with exact parity), and the unit of reuse is the part;
  - the recursive schema as the stated next form.

**Two findings stand regardless of that verdict.**
- Reviewer refinements can be definitions with exact parity. `marks` is the worked example.
- Len's parts are reused at fit level on 21–58 other tasks.

## 7. Questions

- **OQ-21.4. H.** Strict H is empty. For T90 (if it runs), which stratum:
  - H_loose (72 build-failing ARC-1 tasks; Len may have seen them only as one-off-list entries with Claude's
    readings), or
  - H2 (518 never-seen design tasks, all build-solved, which measures correctness but not gain)?
  Or both, reported separately, as C.4's fallback says?
- **OQ-21.5. A form-restricted v4′.** The only depth-2 form that is a true scale-down (Len's "repeats for each
  sub-node") is map. On the density variants above it gave 13 exact and 3 wrong. Those numbers are already seen, so
  they cannot decide anything.
  - I propose pre-registering **v4′ = v4 without seq** (map at panel / object / part only, the rest unchanged).
  - Its control would be a **fresh** density draw: the same 266 tasks, seeds v = 5..9, 1,330 new variants. Same rule:
    pass@1(d2) ≥ pass@1(d1) and wrong(d2) ≤ wrong(d1) + 2.
  - I am running it tonight as exploratory and report it in §5b. It decides nothing until you rule on it.
- **OQ-21.6. Dates.** If a v4 variant passes its control, may the freeze and the one placement move earlier than
  Oct 8 / Oct 9?

## 8. Files

- tools/dream/o0/t86pp.py, situation_engine_v3_frozen.py
- results/o0/t86pp.json
- tools/dream/o0/t90_draw.py
- results/o0/t90_H_counts.json, len_seen_list.json (the sealed ids stay cloud-only)
- tools/dream/o0/defs/marks.dl.txt, defs/uniform_line.dl.txt, defrows.py
- tools/dream/o0/v4a_snapshot/ (the engine the controls measured)
- tools/dream/o0/situation_engine.py (v4 base), scale_free.py, v4_design.py
- results/o0/v4_R_depth1.json, v4_design_depth1.json, v4_design_depth2.json
- tools/dream/density/v4_density.py
- results/o0/v4_density_summary.json, v4g_density_summary.json, v4p_density_summary.json
- tools/review/machine_profiles.py, situations_grid_patch.py (page v149–150)
