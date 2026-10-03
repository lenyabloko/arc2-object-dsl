---
doc: proposal
date: 2026-10-02 (23:05 EDT)
from: cloud Claude (supervisor), on Len's idea
for: Fable (next guidance round)
---

# Proposal: a scale-free situation schema (Len, 23:00 EDT Oct 2)

## Len's words

- "If the schema is not sufficiently rich, it needs to be enhanced (as inductive prior)."
- "I suspect it is a scale free schema that repeats for each sub-node."

## What happened tonight (the case behind it)

1. **The first check failed.** Len defined the cell markers × stamp for dfadab01: "one copy of the unit at every
   anchor depending only on the color of the marker mapped to the stamp by the legend". As written, it did not
   reproduce the training pairs.
2. **His correction:** "some markers got no stamp because they are used by exemplar to map the mark color to the
   stamp. Only the marks at left top corner of the exemplar indicate place for stamp".
3. **The one-off reading worked.** Implemented as a separate check program, it reproduced the training pairs, and the
   one harness check was **exact**.
4. **Len objected** that a correction living only in a check program is not part of the profile matrix, so it can
   never transfer.
5. **It went into the schema, as engine v3** (tools/dream/o0/situation_engine.py, sha 2c8f226e1fe3; v2 stays frozen):
   - a row `marks`: single-cell marks without the legend's marks; a mark touching a shape counts only at that shape's
     top-left corner;
   - two new stamp arguments: `place` (nearest anchor, or the unit's top-left corner on the mark) and `rest` (the rest
     of the input kept, or cleared).
6. **The review page (v148)** shows the same slots in every stamp cell, and his cell definition carries them.
7. **Measured on design** (training pairs only, held-out excluded): results/o0/c2_column_fit_v3.json.
   - The first run let `place := topleft` combine with grid-corner anchors. That added 13 fits that only pin a fixed
     pattern to a fixed place (the memorising pattern of round 20 §5). Top-left placement is now limited to
     markers / marks / fg / objects.
   - After that: v2 fits 158 / 983 and v3 fits 160 / 983. The two new tasks are dfadab01 and 1c02dbbe. Nothing that
     v2 fitted was lost. On the build-failing design tasks the count goes from 13 to 14.
   - 1c02dbbe (ARC-1, build-failing) is the only non-source task the prior newly fits. Its fitted situations give no
     prediction on the test input, so the result is **empty**: no transfer yet, and no harness comparison was made.

## Why "scale-free" fits the evidence

- **The correction is itself a situation one level down.**
  - "marks" = pick out (single cells) except (those touching a shape) unless (at the shape's top-left corner). That is
    WHO with a WHERE condition, the same form as a cell.
  - The legend is another one: exemplar + mark gives a colour → stamp map, which is the unit argument of the parent
    stamp.
- **The residuals of the hard tasks point the same way.** T89, round 20 §3/§5: after the best single situation, the
  residual fits one more column on 2 / 13 tasks (v1) and 6 / 13 (v2). The hard tasks need a second situation, applied
  either to the result or inside an argument.
- **Today's columns take rows and constants as arguments, never situations.** Every row is a hand-written detector,
  so each new reviewer refinement ("marks without the legend's marks") needs a new row in code.

## The proposal

- **S-schema, recursive.** A slot of a situation (WHO, WHERE, unit, PLACE, REST, …) may be filled by:
  - a row,
  - a constant ("the same in all examples"), or
  - **another situation of the same form, evaluated one scale down**: on an object, a part, or a panel instead of the
    grid. A situation used as a WHO returns cells / objects; one used as a unit returns a pattern map.
- **Scale levels.** The same columns and rows at every level: grid → panel → object → part → cell. A sub-node is any
  object or part, and the same schema is tried there. "Scale-free" means one schema, applied at every level.
- **Induction stays as now.** Fit = column × assignment × (depth ≤ 2), exact on the training pairs, with each column's
  WHY checked at every level. The test-blind and held-out rules are unchanged.
- **Budget.** Depth 2 with the present 8 columns and about 25 rows multiplies the search by roughly 25–60. That is
  affordable for design fits (c2_column_fit ran 983 tasks in under 3 minutes with 2 processes) but needs pruning:
  - only slots that take cells or patterns may recurse;
  - the inner situation must fit a sub-problem that its WHY admits.

## Questions for Fable

- **OQ-21.a.** Composition was ruled out of scope (C, v19/v20). Does this proposal, with the T89 numbers and tonight's
  case, reopen it as a bounded step (depth 2, one recursion per situation)?
- **OQ-21.b.** If yes, what is the test? I suggest:
  - placement first: does depth 2 fit any of the T86 13 on training pairs (they stay hidden from Len, with the 12
    exposed on the phone page excluded as round 20 §8 proposes);
  - then a T86-style check under the same rules, frozen before placement.
- **OQ-21.c.** Len's refinements arrive as words in a cell. Should each refinement become:
  - a recursive sub-situation filled by the reviewer (scale-free, as proposed), or
  - a new row in code (as tonight's `marks`)?
  The first is what Len asks for.
