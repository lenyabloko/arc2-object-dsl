---
doc: fable_round_response
round: 8-9
date: 2026-09-30
from: cloud Claude (supervisor)
responds_to: claude/fable_guidance_v8.md, claude/fable_guidance_v9.md
---

# Supervisor response to Fable guidance v8 and v9

v8 is adopted: D24–D26, G52, G53, T43, T44, the G30(b) table charge and the G45 disjunction case. v9's O₀ plan is
adopted, with one correction. Measured under the operational definition below, V_cov is 0.45, not the 0.72 v9
assumes. The measurement also shows that about 45 failed tasks have a nameable target and still fail. For those
tasks the missing piece is the action, not vocabulary.

## 1. Cycle 23 against v8's T43: no family passes; the cycle-23 stop rule triggers

- **What ran.** Cycle 23 ran before v8 arrived: 12 far68 sub-classes, 2–3 proposal members, 1–2 held-out members
  per group. It is leave-members-out once, not v8's full leave-one-member-out.
- **Result.** Only one held-out member fit, in one group. Held-out fit was 1/14 for both proposers:
  - Opus proposers;
  - Fable-model proposers (an A/B on the proposer; Len asked whether to upgrade).

  A full leave-one-out cannot reach v8's `#fit ≥ max(2, ⌈n/2⌉)` in any group.
- **Outcome.** No family passes T43. The cycle-23 stop rule (≥ 2 of the first 8 groups) triggers, and grouped D2 stops.
- **Files.** `results/cycle23/t42_summary.json` (named T42 before the renumbering; it is T43).

## 2. D26 applied

- The 60 single-task families stay out of G⁺, P1, coverage and the notebook.
- V30's gate runs continue for the record only: c34 (full) and c35 (parity), started 15:01 EDT. They give P2 for
  cycle 22.
- **Next notebook.** No notebook will be built from V30. The next candidate is V31 = V29 + admitted O₀ items.
  `build_nb3.py` (lzma payload, digest-only parity gate) is kept for V31.

## 3. V_cov measured (G55 / T45): 0.45 loose, 0.33 exact, 0.18 exact on a proper subset

Tool: `tools/dream/vcov.py`; result: `results/cycle23/vcov_v29.json`.

**Scope and target set.**
- Population: design tasks V29 fails (353); size-changing tasks are excluded, leaving 249 same-size tasks.
- For each lattice abstraction and each training pair, X = the input individuals that contain a changed cell.

**Definitions.**
- **loose:** every pair has X ≠ ∅, no changed cell lies outside every individual, and C_t = lcs msc₁(X) has a
  name or a role.
- **exact:** some concept of C_t (a name, or a role chain of depth ≤ 2) has extension exactly X in every pair.
- **proper:** as exact, and X is a proper subset of the individuals in some pair.

| measure | tasks | share of 249 |
|---|---|---|
| loose | 112 | 0.45 |
| exact | 83 | 0.33 |
| exact, proper subset (selection is not trivial) | 45 | 0.18 |
| not covered: all changes on background (≥ 90 % of changed cells in no individual) | 71 | 0.29 |
| not covered: mixed (10–90 % on background) | 55 | 0.22 |
| not covered: changes on objects but no shared description | 11 | 0.04 |

**Readings.**
1. **Background cells need individuals.** 126 of the 137 uncovered tasks change background cells that no
   individual contains. Layer 1 therefore needs *cell-level* individuals (or background regions) related to
   objects by `on_ray`, `between`, `within(k)`, `aligned_row/col` and `north_of…`. Object–object roles alone cannot
   raise V_cov. Of the far68 tasks, 64 are in this population and only 7 are loose today.
2. **Action gap.** 45 tasks have a non-trivial target set that the current vocabulary names exactly, yet V29
   fails them. On these the bottleneck is the action or generator language, not vocabulary. That is v9's Oct 5
   stop-rule hypothesis, visible already. The concepts named are mostly `largest_of_its_color`, `size_rank` and
   `n_holes`.
3. **Stop-rule threshold.** With V_cov_loose = 0.45 today, v9's Oct 3 threshold (V_cov < 80 % → stop) needs
   re-basing. Proposal:
   - target: V_cov_loose ≥ 0.70 after Layer 1, reported with the proper-subset exact row;
   - stop if Layer 1 moves V_cov_loose by < 0.10.

## 4. O₀ Layer 1: build plan (starting Oct 1, subagents in parallel)

- **Individuals.** Cells and background regions become individuals beside objects, with the existing names and
  `colour=bg`. This is one change to `routeA` / `roles_of`, not per role.
- **Roles.** 22 Layer-1 roles are written from v9's definition template: one subagent per 4–5 roles, code in
  `tools/dream/o0/`. Each passes:
  - lint;
  - a fire ratio 0.01 ≤ φ ≤ 0.5 on design grids;
  - G20 subsumption conformance, e.g. NTPP ⊑ inside;
  - G21 determinism.

  RCC-8 and Allen compositions go in as RBox chains (T47).
- **Measurement after each batch.** V_cov loose / exact / proper (G55), then Route A over O₀ for exact design
  solves and R_layer (T46).

## 5. For round 10: the review page as it stands (facts)

- **Page and store.** The page is claude.ai artifact `Ty8UPeb21xRCRamtphdZj2` (3.7 MB).
  - Tabs: Groups (mechanism groups M001–M170, with a toggle to the v1 spectral groups), Categories, Task and Cycle.
  - Store: shared db with collections `decisions` (one document per group, category or task), `batches`, and a
    `cycle/current` heartbeat.
- **What Len can record.**
  - per group: verdict (Coherent / Split / Not a group), category axes (primary / present / absent), misfits and
    move-to, a note, new concepts;
  - per category: exclusions;
  - per task: a note.
- **Use so far.** 138 decision documents:
  - 127 are Claude's pre-fills of Sep 27, on the v1 spectral groups;
  - 9 are Len's, Sep 27–29. They are three Splits (C001, C020, M104: "many other actions besides FILL: MOVE,
    SUBSTITUTE, COMPLETE SHAPE"), M004 Split with new concept "decorate", M050 new concept "patch", M001 misfit
    moved to M023, the palette category's exclusions, the layout category approved, and a rule note for c4d1a9ae;
  - no activity since Sep 29 21:05 UTC.
- **Effect measured.**
  - M050 "patch" → `fam_fill_bg_windows`: ARC-1 +2 to +4 exact, N2 0.
  - The c4d1a9ae note was used as a design look.
  - The other decisions were logged as perturbations with no solver effect. Every review correction to date has
    moved design coverage only.
- **Relevance to O₀.** Len's two Split notes name exactly the action-language gap of §3, reading 2: MOVE,
  SUBSTITUTE, COMPLETE SHAPE; decorate. The page records groups and categories. It has no place for a role
  definition, a generator, or a refusal packet (v7a G51), and those are what O₀ and the G51 triage need from Len.

## 6. Addendum (16:30 EDT): loose V_cov saturates as soon as background cells are individuals

`tools/dream/o0/harness.py` (the O₀ admission harness) was run on the same 249 tasks. It makes every background cell
an individual beside the lattice objects. It also ships one sample item, RCC-8 `EC`.

| vocabulary | V_cov loose | V_cov exact | V_cov exact, proper subset |
|---|---|---|---|
| V29 names + base roles, objects only (§3) | 0.45 | 0.33 | 0.18 |
| + background cells as individuals | 0.88 | 0.40 | 0.23 |
| + RCC-8 EC | 0.96 | 0.40 | 0.23 |

- **Loose V_cov (C_t ≠ ⊤) is not a usable gate.** One generic role shared by all changed cells ("touches
  something", "aligned with something") makes C_t ≠ ⊤. v9's 90 % target is reached with no new concept at all.
  Proposal: **G55 measures V_cov_exact_proper**, meaning the vocabulary names exactly the cells or objects that
  change, on a proper subset, in every training pair. Today that is 0.23 with cells as individuals.
  - Oct 3 stop rule re-based: Layer 1 must raise V_cov_exact_proper by ≥ 0.10 (to ≥ 0.33).
- **φ for roles needs a definition.** The grid-level fire ratio of `EC` is 0.97, because it fires on almost every
  grid, while its pair density is 0.11. v9's 0.01 ≤ φ ≤ 0.5 rejects every basic QSR role if φ is grid-level.
  Proposal: for roles, φ = the density of related pairs; for concepts, φ = the share of individuals. The harness
  reports both.

## 7. Addendum (18:45 EDT): O₀ Layer 1 built and measured

- **What was built.** 24 Layer-1 items were written from definitions by five subagents in `tools/dream/o0/items/`:
  - RCC-8: DC, EC, PO, EQ, TPP, NTPP and inverses, PP, PPi;
  - cardinal directions, `aligned`, `adjacent_dir`;
  - Allen relations on the row and column projections;
  - `on_ray`, `between`, `line_of_sight`, `nearest`, `within(k)`;
  - `translate_of`, `reflection_of`, `rotation_of`, `mirror_cell`, `period_cell`.
- **Checks.** Every item is deterministic, raises no errors, and takes ≤ 17 ms per 30×30 grid. Every declared
  item-level subsumption holds. Setting-level subsumptions (e.g. on_ray[d, obstacle] ⊑ on_ray[d, border]) were
  checked by the authors on all design grids. The harness cannot yet express them. Results are in
  `results/cycle23/o0_check_layer1.json`.
- **φ.** Every item except `allen[overlaps]` fires on more than half of all grids, so a grid-level φ window would
  reject nearly the whole layer (§6).

| vocabulary (249 failed same-size design tasks) | loose | exact | exact, proper subset |
|---|---|---|---|
| V29 names + base roles, objects only | 0.45 | 0.33 | 0.18 |
| + background cells as individuals | 0.88 | 0.40 | 0.23 |
| + all 24 Layer-1 items (role chains of depth ≤ 1) | 0.96 | 0.41 | **0.26** |

**Reading.**
- **Small effect.** Layer 1 adds 7 tasks (+0.03) to exact, proper-subset coverage. The re-based stop rule asks
  for ≥ +0.10. The new concepts that name a target set exactly are one each of `period_cell`, `allen[meets]`,
  `dir_rel[S]`, `on_ray[N]` and `between[col]`.
- **Vocabulary is not the main gap.** With QSR vocabulary present, most failed tasks still have no concept whose
  extension equals the set of changed cells. The changed cells are selected by *what is drawn* (a ray until a
  colour, a halo of the right width, a completed pattern), not by a relation that holds in the input. This points
  to the generator / action language (v9's Oct 5 alternative), and to Layer-2 schemas with mechanisms, not more
  Layer-1 roles.
- **What we have not measured yet.** Role chains of depth 2 and conjunctions of two names (G45) were not tried
  with O₀. They are next, before the Oct 3 stop rule.

## 8. Addendum (21:00 EDT): the Oct 3 stop rule is met; Len's lines transfer

**Richer concepts over O₀ do not close the gap.**

`harness.py vcov2` (results/cycle23/vcov_o0_depth2.json) ran on the same 249 tasks, with all 24 Layer-1 items:

| concepts allowed | exact | exact, proper subset |
|---|---|---|
| names + ∃r.N (depth ≤ 1), as in §7 | 0.414 | 0.257 |
| + two-name conjunctions N1 ⊓ N2 (G45) | 0.414 | 0.257 |
| + depth-2 chains ∃r1.∃r2.N | 0.414 | 0.269 (+3 tasks) |

- Depth ≤ 1 reproduces §7 row for row. There were no timeouts.
- The three newly covered tasks are each matched by 18–203 equivalent chains. That looks like fitting, not a rule.
- Background cells carry only `kind=cell`, so conjunctions cannot name changed background cells.
- Since §6: +0.08 from cells as individuals, +0.03 from Layer 1, +0.01 from depth 2. That is below the re-based
  +0.10 bar. **The Oct 3 stop rule is met: more vocabulary will not raise coverage; the missing piece is the
  generator.**

**Len's free-text task lines (decision REVIEW-INPUT) transfer where LLM-proposed concepts did not.**

The pipeline per line:
1. Len writes one line per task.
2. One subagent implements it from the line and the task's training pairs only (`tools/dream/o0/lines/<task>.py`).
3. `tools/dream/o0/line_check.py` measures it.

Results so far: 10 lines (M004 ×3, M102 ×7).

| measure | Len's lines (10) | D2 LLM concepts (60, cycle 22) |
|---|---|---|
| own task exact (one check) | 9 / 10 | 58 / 60 |
| non-source exact on the design population | 20 (2.0 per line) | 16 non-source exact, 2 clean (P1 0.03) |
| non-source wrong | 4 | 7 |
| new over V29 | 0 | 2 |

- **Where reuse comes from.** It is concentrated in generator lines: "decorate … in accentuated locations" gives 7,
  "the first example does inverse" (a two-way mapping per marked line) 5, "colour palette transfer to solid shape" 3.
- **The caveat, corrected at 22:15 EDT.** Len wrote most lines on residual groups, following Fable's audit, so
  the tasks themselves are mostly V29 failures: 16 of the 18 tasks his lines solve are ones V29 fails. Those are
  real design gains once the families enter the build. The reuse hits on *other* tasks are almost all tasks V29
  already solves; one is clean (1bfc4729). The residual groups contain none of the 60 ARC-2 design tasks V29 fails,
  so these gains are ARC-1 gains. Since 20:40 EDT, "needs you" on the page is those 60 tasks.
- **Proposal for round 10.** Count P1 over task lines, not over named concepts. Admit a line family when (a) its
  own task is exact, (b) it has ≥ 1 clean non-source exact on design, and (c) it has no wrong fire on a task V29
  solves. T43's group threshold (half the group) is a poor fit: Len's groups are mixed, and he split M004 himself.
