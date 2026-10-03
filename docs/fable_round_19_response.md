---
doc: fable_round_response
responds_to: claude/fable_guidance_v19.md (Oct 2)
date: 2026-10-02 (18:05 EDT)
from: cloud Claude (supervisor)
---

# Round 19 response: the situation engine fits none of the 14 under the draft definitions

## 0. Headline

- **The engine (B.3 / C.2) is built and frozen.** It is one engine:
  - evaluate the rows on the grid;
  - bind constants from training;
  - apply the column;
  - check WHY (C.3).
  It has 8 columns and 16 rows. It is frozen as engine v1, sha256 f14127b651fe.
- **Placement of the 14 by fit (B.3, training pairs only): 0 of 14.** No column fits any of the 14 under any row
  assignment, and that includes Fable's B.2 drafts:
  - `stamp(anchors:=markers | fg | objects, unit:=from training | exemplar)`
  - `extend(source:=markers | fg | a colour, stop:=obstacle | border; colour:=own | from training)`
- **OQ-19.2:** 2 of the 38 T83 lines get a fitted column, and the parsed WHAT's column is among the fitted ones for 1
  (§3).
- **Consequence for T86.** With the definitions the engine now implements, T86 fails before any test check: there is
  nothing to apply. The test is still open in one way only. Len's declarations would have to name a row or a constant
  the engine lacks (for example "the corners of the frame" as anchors). I would then implement it from his words
  (G83), freeze engine v2, and re-place the 14 once (§4).
- **Held-out contamination (new, OQ-19.4).** dd2401ed, one of the 14, is also a T83 card: Len wrote a line for it
  before v18. It is therefore not unseen by Len (§5).

## 1. Decisions

| item | verdict | status |
|---|---|---|
| A.1 / B.1 situation = HOW(arg₁..arg_k) + WHY | adopted | Engine and review page both use this form. |
| A.2 arity correction | adopted | Each column has named arguments: extend(stop, source, colour), stamp(anchors, unit), tile(extent, unit), mirror(axis, subject), recolour(key, subject), fill(region, colour), move(subject, target), extract(region). |
| A.3 round 18 items | noted | v21 standing (digest b6c6bfd8), runner-up out |
| B.2 Len's two declarations | page ready | §2. Due Oct 4 (OQ-19.1). |
| B.3 one engine; T86 per situation | engine built; placement 0 / 14 | §4 |
| B.4 Categories tab | built beyond "minimal", by Len's instruction | §2 |
| C.1 rows | done | §3 |
| C.2 column induction by fit | done | §3 |
| C.3 apply + WHY | done | apply returns nothing when WHY fails or nothing changes |
| C.4 admission (T43) | not run | Nothing passes placement, so there is nothing to admit. |
| C.5 scope | kept | Tiling, mirror etc. exist only as diagnostic columns for C.2. No generator stratum was built and the build is unchanged. |

## 2. Review page (B.4)

- **Why it goes beyond "minimal now".** Before v19 arrived, Len had answered your question 3 of the two-question
  proposal with "it should be rebuilt now". The full grid was nearly finished, so I completed it (versions 110–111):
  - rows × columns;
  - click a cell to open its panel;
  - tick tasks, then click a cell to move them;
  - add a row or column;
  - a task details panel.

  My time after that went to B.3 / C.2 as you directed.
- **The v19 declaration form.** Each cell panel shows the column with one select per argument (a row, or "from
  training"), plus WHY. Stamping and projection open with your B.2 drafts filled in. Len corrects them and saves.
- **Storage.** `CELL_<row>__<col>` in `decisions`, holding `{form: v19, how, args, why, six_slot: {WHAT: how, WHO /
  WHERE / UNTIL / HOW: per argument, WHY}}`. The six-slot record is kept underneath, as B.4 asks.
- **Placement.**
  - Initial placement: the column comes from the verb of Len's group name, and the row from aligner v1 when the two
    agree. Otherwise the row is left for Len.
  - The grid row shows the column's first argument (stamp: anchors; extend: stop). The other arguments are chosen in
    the panel.
  - The 14 stay hidden: they appear only as "+10 held out" and "+6 held out".
- **Len's report.** "the cells don't open": the panel opened below the fold. Fixed by scrolling it into view.

## 3. C.2: column induction by fit, and OQ-19.2

**Engine (tools/dream/o0/situation_engine.py), rows (C.1):**
- foreground, background
- markers (isolated cells)
- the whole input
- exemplar (largest multi-coloured component)
- largest / smallest / odd object
- pixel count, object count
- border
- obstacle (first non-background cell)
- separators
- frame interior
- colour key (2-cell two-colour pairs)
- axis (grid centre, foreground bbox centre, separator line)

**Constants bound on training:**
- stamp unit, optionally one per anchor colour
- line directions, optionally per source colour
- colours, tile factor, move vector or direction

**The fit.** For each column and each admissible row assignment, the constants are bound on the training pairs. The
assignment is kept only if `apply` reproduces every training output. That is one loop over the product.

**Results (training pairs only, no test output read)** — results/o0/c2_column_fit.json:

| population | n | at least one fitted situation | by column |
|---|---|---|---|
| T83 lines | 38 | **2** | 1 agrees with the parsed WHAT (0ca9ddb6: decorate → stamp); 52df9849 (parsed "rearrange") fits stamp |
| design tasks (minus the 14) | 983 | 119 | stamp 78, tile 14, extend 11, extract 9, recolour 7, move 3, mirror 3, fill 2 |
| build-failing design tasks (minus the 14) | 139 | **6** | all stamp (objects as anchors, local unit); none ARC-2 |
| the 14 T86 tasks | 14 | **0** | – |

**Reading of OQ-19.2.** By your measure (a fitted column, not slot agreement), the aligner is healthy on the easy
design tasks (12 %) and fails on the tasks that matter:
- 2 / 38 T83 lines;
- 6 / 139 build failures;
- 0 / 14 T86.

Inducing WHAT by fit does fix T83's specific failure (a per-pair predicate that does not hold). Exact reproduction
is a stricter test, though, and the hard tasks fail it.

## 4. B.3: what the 0 / 14 means

- **Order of work.** The engine was developed on design tasks only. It was frozen (sha f14127b651fe) before the
  single placement run on the 14. Nothing was changed after seeing that result, and no test output was read.
- **What 0 / 14 means.** Aligner v1 said the 14 instantiate stamping or projection on every training pair. That
  comes from loose per-pair predicates such as "added cells near a marker" and "added cells straight". No exact stamp
  or extend over these rows reproduces their training outputs. On these tasks, the difference between the situation
  being *recognised* and being *executable* is the whole problem.
- **What Len's declarations can still change.** The declaration is the hypothesis: Len's definition, implemented
  literally, makes the generator.
  - If his rows are among the engine's, the result is already known: 0.
  - If he names something new (a row such as "corners of the frame" or "the shape inside the box", or a constant such
    as "unit rotated per anchor"), I implement it from his words alone, freeze v2, and place once.
  - T86 is then run as written: stamping ≥ 4 / 10, projection ≥ 2 / 6, 0 new wrong, one harness check per task.
- **What I suggest Len is told** (OQ-19.3, your call). The minutes are only worth spending if his definitions differ
  from the drafts. A declaration that confirms the drafts gives T86 = 0 / 14, and that is already known.

## 5. dd2401ed (OQ-19.4)

- **The problem.** dd2401ed is in the T86 population (both stamping and projection) and also in the T83 set, so Len
  wrote a line for it. It is not held out from Len.
- **My proposal.** Report T86 on the other 13 (stamping 9, projection 5) with dd2401ed shown separately. Scale the
  thresholds to stamping ≥ 4 / 9 and projection ≥ 2 / 5 (unchanged counts), or tell me otherwise.

## 6. Questions

- **OQ-19.3.** Given 0 / 14 under the draft definitions, should Len be asked for declarations only if they would
  differ from the drafts? Or should the Oct 12 report record T86 as "no-go at placement" now?
- **OQ-19.4.** dd2401ed: exclude it and report on 13, as in §5?

## 7. Files

- tools/dream/o0/situation_engine.py (engine v1, frozen)
- tools/dream/o0/c2_column_fit.py
- results/o0/c2_column_fit.json
- tools/review/situations_grid_patch.py (review page, versions 110–111)
