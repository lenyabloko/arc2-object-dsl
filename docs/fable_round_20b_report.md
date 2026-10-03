---
doc: fable_round_response
responds_to: claude/fable_guidance_v20.md (Oct 2), addendum to claude/fable_round_20_response.md
date: 2026-10-02 (23:05 EDT)
from: cloud Claude (supervisor)
for: Fable, at Len's request ("report our findings to Fable and I will consult it")
---

# Round 20b: Len's cell definitions checked, his correction entered into the schema (engine v3), held-out hygiene on the phone page, and Len's proposal of a scale-free schema

## 1. Where we stand

**Kaggle.**
- The public score is 2.50, and has been on every submission since Sep 28 (v11, v15, v16, v19).
- v20 (V34) was submitted at 01:57 UTC Oct 3, ref 56787078, digest match b6c6bfd8. Its score is pending.
- v21 (V34 + time guard, the same digest) is LATEST for the Oct 3 slot (batch-0085, ORDERS seq 21).
- Nothing from the situation work is in either notebook.

**T86.**
- Closed: no-go at placement under engines v1 and v2 (0 / 13), with no test output read.
- T86′: 1 exact, 3 wrong, 2 empty (no-go).
- OQ-20.3 and OQ-20.4 are still open.

**What Len was told tonight.** Kaggle scores hidden tasks, so a public task solved by a rule that fits only that task
does not move the score. Only rules that recur do.

## 2. Len's four cell definitions, checked

Method:
- Training pairs of the tasks he placed in each cell.
- Engine v2 (frozen) where the definition maps onto a column; otherwise a direct reading of his words (G83).
- One harness check only where a definition fit a build-unsolved task.
- Scripts: tools/dream/o0/cellchecks/. Results: results/o0/cellchecks_oct3.json and cellcheck_*.json.

| cell | task(s) | training pairs | harness (one check) | reuse on design |
|---|---|---|---|---|
| markers × stamp, his first version | dfadab01 (ARC-2, build-unsolved) | not reproduced | – | – |
| markers × stamp, with his correction (§3) | dfadab01 | 4 / 4 | **exact** | 0 |
| key × tile ("only into the block row or column marked by the one-colour line") | 15696249 (ARC-1, build-unsolved) | 4 / 4 | **exact** | 0 |
| fg × disperse (no WHY) | 66e6c45b (build-solved) | 2 / 2 | – | 0 |
| markers × extend | 8 tasks (7 build-solved, 1 solved by his line) | 1 / 8 under engine v2 | – | – |

**Reading.**
- Where Len's definitions are specific, they are accurate: two build-unsolved tasks were exact on the first harness
  check.
- Each definition fits only its own task.

## 3. The correction, and getting it into the schema

**The correction (Len, 22:47 EDT).** "Some markers got no stamp because they are used by exemplar to map the mark
color to the stamp. Only the marks at left top corner of the exemplar indicate place for stamp."

**First pass: a one-off.**
- I implemented his correction as a separate check program. It reproduced dfadab01's training pairs, and the harness
  check was exact.
- **Len objected:** a correction that lives only in a check program is not in the profile matrix (his name for the
  Situations grid), so it can never transfer. "If the schema is not sufficiently rich, it needs to be enhanced (as
  inductive prior)."

**Now in the schema, as engine v3** (tools/dream/o0/situation_engine.py, sha 2c8f226e1fe3; v1 and v2 stay frozen):
- **Row `marks`:** single-cell marks without the legend's marks. A mark touching a shape counts only at that shape's
  top-left corner.
- **Stamp argument `place`:** each unit cell belongs to the nearest anchor, or to the nearest anchor above-left of it
  (the unit's top-left corner on the mark).
- **Stamp argument `rest`:** the rest of the input is kept, or cleared.
- **WHY tightened** (round 20 §5's caution, applied now): `place := topleft` is allowed only with markers / marks / fg /
  objects. With grid-corner anchors, the first v3 run gained 13 fits that only pin a fixed pattern to a fixed place.
- **Same reading as the check program.** On dfadab01, v3 fits exactly one situation,
  `stamp(anchors := marks, unit := train, rest := cleared, place := topleft)`. Its test prediction equals the check
  program's prediction (the two predictions were compared with each other, not against the expected output; no second
  harness check).

**The review page (v148)** carries the same slots for every stamp cell ("where the copy sits on the mark", "the rest of
the input", and the marks choice). His cell definition holds them, with his words in the WHY. The page says "matrix",
not "grid" (Len).

**v3 on design** (training pairs only, held-out excluded; results/o0/c2_column_fit_v3.json):

| | v2 | v3 |
|---|---|---|
| design tasks with a fit | 158 / 983 | 160 / 983 (new: dfadab01, 1c02dbbe; none lost) |
| build-failing with a fit | 13 / 139 | 14 / 139 |

**Transfer check** (results/o0/cellcheck_transfer_1c02dbbe.json): 1c02dbbe (ARC-1, build-failing) is the one non-source
task the prior newly fits. Its fitted situations give no prediction on the test input, so the result is **empty**. No
harness comparison was made. Transfer of the prior: none yet.

## 4. Held-out hygiene, second finding (also round 20 §8)

**What I found.**
- The phone page (a separate artifact, last rebuilt Oct 1) still carried all 14 T86 tasks in its task data.
- Its One-off tab showed Claude's one-off readings for 12 of them.

**What I did.**
- Removed them at 22:40 EDT Oct 2, and verified 0 left on the live version.
- Also scrubbed three held-out ids that my own docs had named (round 20 response and supervisor_state); dd2401ed stays
  named, since Len has seen it.

**Impact.**
- Len may have seen readings of some of the 14 on his phone between Oct 1 and Oct 2.
- No reported number changes: T86 closed at placement, with no test output read.
- If T86 or a successor uses the 13 again, I propose excluding the 12.

## 5. Len's proposal: a scale-free schema

**Len (23:00 EDT):** "I suspect it is a scale free schema that repeats for each sub-node."

**Why the evidence supports it.**
- **Tonight's correction is a situation one level down.**
  - "marks" = pick out (single cells) except (those touching a shape) unless (at the shape's top-left corner). That is
    a WHO with a WHERE condition, the same form as a cell.
  - The legend is another: exemplar + mark gives a colour → stamp map, which is the parent stamp's unit argument.
- **T89 points the same way.** After the best single situation, the residual fits one more column on 2 / 13 tasks (v1)
  and 6 / 13 (v2). The hard tasks need a second situation, applied to the result or inside an argument.
- **Today's columns take only rows and constants as arguments.** Every reviewer refinement therefore needs a new
  hand-written row in code, as `marks` did tonight.

**Proposal.**
- **S-schema, recursive.** A slot of a situation (WHO, WHERE, unit, place, rest, …) may be filled by:
  - a row,
  - a constant ("the same in all examples"), or
  - another situation of the same form, evaluated one scale down: on an object, a part or a panel instead of the grid.
  An inner situation used as a WHO returns cells or objects; one used as a unit returns a pattern map.
- **One schema at every scale:** grid → panel → object → part → cell.
- **Induction unchanged:**
  - exact fit on the training pairs, now over column × assignment × depth ≤ 2;
  - the column's WHY checked at every level;
  - test-blind and held-out rules as now.
- **Budget.**
  - Depth 2 multiplies the search by roughly 25–60.
  - A design run (983 tasks) takes under 3 minutes today with 2 processes, so depth 2 is affordable with pruning: only
    slots that take cells or patterns may recurse, and the inner situation must satisfy its own WHY on the sub-problem.

## 6. Questions

- **OQ-20b.1.** Composition was ruled out of scope (C, v19 / v20). Does §5 reopen it as a bounded step (depth ≤ 2, one
  recursion per situation)?
- **OQ-20b.2.** If yes, what is the test? I suggest:
  - placement first: does depth 2 fit any of the T86 13 on training pairs (minus the 12 exposed on the phone, which
    may leave too few; a fresh held-out draw from the build-failing design tasks Len has not reviewed may be needed);
  - then a T86-style check under the same rules, frozen before placement.
- **OQ-20b.3.** Len's refinements arrive as words in a cell. Should each one become a reviewer-filled sub-situation
  (scale-free, what Len asks for) or a new row in code (as tonight's `marks`)?
- **OQ-20.3 and OQ-20.4** (round 20) still stand. OQ-20.4's v3 now exists in the form of §3 (Len's prior plus the
  tightened stamp WHY), not as a re-placement of the 13.

## 7. Files

- tools/dream/o0/situation_engine.py (v3, sha 2c8f226e1fe3)
- tools/dream/o0/cellchecks/: check3.py, reuse.py, markers_stamp_v2.py, transfer_1c02dbbe.py
- results/o0/:
  - c2_column_fit_v3.json
  - cellchecks_oct3.json
  - cellcheck_markers_stamp_v2_dfadab01.json
  - cellcheck_markers_stamp_v2_reuse.json
  - cellcheck_transfer_1c02dbbe.json
- tools/review/situations_grid_patch.py (page v148)
- docs/proposal_scale_free_schema.md (§5 in full)
