---
doc: fable_round_response
responds_to: claude/fable_guidance_v18.md (14:45 EDT Oct 2); v17a and decision CATEGORIES-ARE-SITUATIONS
date: 2026-10-02 (14:45 EDT)
from: cloud Claude (supervisor)
---

# Round 18 response

## 1. Decisions

| item | verdict | status |
|---|---|---|
| A.1 T80 withdrawn | accepted | The formal T80 was already run before v18 arrived: 4 of 60 flips, 0 new wrong, all gains on tasks the build already solves (round 17 §0b). It stands as a record only. |
| A.3 / C.3 aligner v2 (lcs over pairs in the role lattice) | done | §2 |
| A.4 deadline guard (v21) | done | v21 staged in batch-0083. Driver equivalence and plumbing were checked on 12 eval tasks. A full local parity run over all 120 eval tasks (v21's probe payload and guarded driver) gives **b6c6bfd8**, equal to the expected digest (verified 15:03 EDT). |
| A.5 runner-up in slot 2 | not included | Filling slot 2 changes predictions on any eval task with an empty slot 2, so the parity digest would change. A.5's condition (digest unchanged) cannot hold, so it stays out. |
| B.1 two situation generators (stamping, projection) | accepted | Waiting for Len's definitions (B.2). Nothing is written before them. |
| B.2 definitions from Len | the page is ready | The Categories tab now carries the six-slot template, with a "Declare a situation" form (§3). Len can write stamping and projection there or in claude/situations_len_v1.md. |
| B.3 T86 go/no-go | accepted | Population and current status in §4 |
| G83 | adopted | |

## 2. Aligner v2 (C.3, the one permitted change)

- **The change.** Across pairs the slot value is now the least common subsumer of the per-pair values in a declared,
  task-free parent lattice (`PARENTS` in tools/dream/o0/template_align.py), instead of a value holding identically
  on every pair. Some of the parent links:
  - marker ⊑ smallest_object ⊑ odd_object ⊑ all_objects ⊑ whole_grid
  - frame_or_container ⊑ region
  - mirror_complete / fill / copy_stamp ⊑ complete_shape
  - draw_line ⊑ decorate
  - aligned / between / toward ⊑ on_line_of_sight
  - contact ⊑ obstacle
- The 2:1 relational weight is kept, and nothing else was tuned.
- **T83, diagnostic:**

| | v1 | v2 |
|---|---|---|
| OPEN slots: WHO | 15 / 38 | **10** / 38 |
| OPEN slots: WHAT | 15 / 38 | 15 / 38 |
| OPEN slots: WHERE | 7 / 38 | 7 / 38 |
| OPEN slots: UNTIL | 4 / 38 | 4 / 38 |
| all four slots agree, lenient | 0 / 38 | 0 / 38 |
| all four slots agree, parsed value subsumes or equals the aligned one | 3 / 38 | 3 / 38 |

Per slot (subsumed scoring) under v2: WHO 18 / 37, WHAT 14, WHERE 22, UNTIL 26.

- **WHO benefits from the lcs** (5 fewer OPEN).
- **WHAT does not.** On its 15 OPEN lines at least one training pair has *no* WHAT value at all. Each per-pair
  definition (e.g. "every added component is straight") fails on that pair, so there is nothing to generalise.
- Loosening the per-pair definitions is outside C.3, so I left it.
- Results: results/o0/t83_v2_result.json.

## 3. Review page: categories are situations (decision items 1–3; v17a)

Published to the review page (version 88), Categories tab:

- **Situations come first.** Each category page shows:
  - the six-slot template, with the open role marked;
  - WHY, which is required (a missing WHY is shown in red);
  - the membership table = P2 status per design task ("aligned: roles bound k of 5", "invariant failed"), from
    aligner v1 on training pairs only;
  - the mechanism groups with aligned members;
  - Len's ✓ in / ✗ out per task.
- **Labels** are stored in `decisions` as `{kind: situation_label, task, situation, label, reviewer, ts, test_seen: false}`.
  They go into the next review batch, are never an aligner input, and are used for T85.
- **Seeds.**
  - The four v17 situations are seeded, marked as Claude's placeholders that Len's definitions replace.
  - The two candidate drafts are "recolour by key" (from palette mapping) and "extract the distinguished region" (from
    crop). They are shown dashed, not used (G82), and have no WHY yet.
- **"Declare a situation"** replaces "add a new category".
  - The form has five closed-vocabulary selects, the open role, and WHY (mandatory).
  - It saves `{kind: situation_declaration, …, g82: draft}`.
  - A note asks Len for stamping and projection by Oct 4.
- **Grid checks are evidence.** The old category section is retitled "Evidence: grid checks (no longer
  categories)", with the reassignments listed:
  - scale → evidence for tiling;
  - crop → evidence for the extract candidate;
  - palette → evidence for the recolour-by-key candidate;
  - sparse and partition → evidence only.
  Len's earlier corrections are kept.
- **Situation count: 4 seeded + 2 drafts** (v17a caution: about 10 at most).
- **R(S) on the 997 design tasks** (aligned / invariant failed):

| situation | aligned | invariant failed |
|---|---|---|
| tiling | 16 | 46 |
| stamping | 12 | 34 |
| projection | 24 | 0 |
| symmetry | 19 | 0 |

## 4. T86 population and OQ-18.2

- **Population.** The 16 situation instances are 14 distinct tasks (dd2401ed and e7b06bea instantiate both).
  - stamping: 1efba499, 252143c9, 758abdf0, 97c75046, c4d067a0 (ARC-2), dd2401ed, e4941b18, e7b06bea, ecaa0ec1,
    fc10701f
  - projection: 696d4842, a78176bb, cf133acc, dd2401ed, df978a02, e7b06bea
- **OQ-18.2: why they fail today.**
  - None of the 38 prior families fits any of the 14.
  - In the V34 full run (c42, read only for these tasks), 12 of the 13 present have **no answer at all**: both slots
    empty, placeholder.
  - Only dd2401ed has an answer occupying a slot, wrong, from Len's line family, so its second slot is free.
  - c4d067a0 is not in c42's population.
- So all 14 fail because nothing fits, which is where a generator can act. A generator stratum that fills empty
  slots only would reach every one of them, and cannot displace anything elsewhere (b = 0 by construction).

## 5. Next

1. LATEST → v21 after tonight's v20 submission (parity verified).
2. Len's two definitions (OQ-18.1). As soon as they exist I write the two generators from them alone, admit them via
   T43, and run T86 on the 14 tasks, then T87 at the N2 gate.
3. T85 when Len has labelled some tasks.
