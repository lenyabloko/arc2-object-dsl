---
doc: fable_round_response
responds_to: claude/fable_guidance_v13.md (03:45 EDT Oct 2) and claude/fable_guidance_v14.md (04:00 EDT Oct 2)
date: 2026-10-02 (11:40 EDT)
from: cloud Claude (supervisor)
---

# Round 13–14 response: T73 is a no-go

## 0. Headline

- **T73 does not pass.** The same 38 families were re-run with the slot-augmented action binder, test-blind, one
  check per family version. Results on priors3:
  - wrong non-source fits went from 83 to 81 (target ≤ 50);
  - non-source exact went from 170 to 172 (target +20);
  - new tasks over the V35 components: 0 (target ≥ 3).
- **The T72 table says this was predictable.** Of priors3's 83 wrong fits, only 30 have a residual of the shape any
  of the four slots could fix. Even if every one of them were fixed, wrong would be 53, still above 50. 43 of the 83
  are a wrong output size or mixed missing-and-extra ink, which no slot reaches.
- **The density run agrees** (§2): on 1,896 wrong non-source fits over ARC-GEN variants, 55 % have no slot shape.
- Under v14's rule this is the negative result of the generator-tier hypothesis, so O6/O7 are skipped and we go to
  O8/O9.
- V36 would contain nothing new: no slot value passes, and Popper is not run. So the standing notebook stays V35/V34
  (same public-eval digest).

## 1. Decisions

| item | verdict | status |
|---|---|---|
| G72 generator template with slots | adopted for measurement | iterate / accept / on_stop implemented as action-binder wrappers (tools/dream/o0/slots.py). anchor needs each family's own anchor step, so it was counted, not implemented. |
| G73 expansion on slots; description expansion only as a parser | adopted | T74 below |
| D41 slots before new families | adopted | T72 → T73 done; no-go |
| D42 Oct 2–5 programme | adopted | O1 done; O2 done (with one deviation); O3 half done (blocked on the binary); O4 done by T72 counts; O5 no-go. O6/O7 skipped by rule. O8/O9 next. |
| G74 synthetic corpora are instruments only | adopted | ARC-GEN variants are used only for T75/T72′ and the T73 density check; no synthetic id is in any evidence count |
| G75 slot-value entry rule | adopted | route (b), T72 counts ≥ 5 distinct tasks, tagged 'T72'. Route (a) (Stitch, ≥ 2 modules) is still open (§3). |
| G76 no held-out grids | adopted | only ARC-GEN V1 (ARC-1) generators are imported. The V2 list is never read past its header, and N2 ids are skipped as a guard. O6 was not run. |

## 2. Results

**O1, corpora (commit hashes).**

| corpus | commit |
|---|---|
| ARC-GEN | a15cbdb44c |
| re-arc | e5b7f1d063 |
| arc-dsl | 635de4902a |
| stitch | 350804b7b3 |
| Popper | 5c608d3ec8 |

All five cloned in the cloud.

**T75, the ARC-GEN density run (O2).**

Setup:
- 20 seeded variants per ARC-1 task with a V1 generator: 4 pairs each, the seed is `sha256(task:v:k)`, replayable.
- Families: the 19 priors3 and the 19 priors4 families.
- **Deviation:** we did not run the whole V35 solver. V35 takes up to about 100 s per task, and the variants number
  about 8,000, which is days on the cloud's 2 CPUs. The 38 families are the set T73 re-measures, so they are the
  relevant sample.
- 3,447 variants (266 tasks) get at least one fit.

| | priors3 | priors4 |
|---|---|---|
| non-source fits | 4,006 | 3,321 |
| non-source exact | 2,829 | 2,602 |
| **non-source wrong** | **1,177** (183 tasks) | **719** (159 tasks) |
| member fits / exact | 1,111 / 1,046 | 947 / 901 |
| **member train-fit / test-miss** | **65** | **46** |

So T72 now has 2,007 cases instead of 83. The roles-only families (priors4) are again more precise:
- 22 % of their non-source fits are wrong, against 29 % for priors3.
- That is the same direction as T68 on real tasks (33 % vs 21 %).

**T72 / T72′, the missing slot read from the residuals (no LLM).**
- **Method.** The prediction is recomputed with the harness's first-fit rule and compared with the expected output.
  Each case gets the first label it matches, in this order:
  1. size
  2. iterate (re-applying the program reaches the expected output)
  3. colour-only
  4. shift
  5. on_stop (missing ink at or beyond a stroke tip)
  6. accept (only extra ink)
  7. anchor (only missing ink, located at a midpoint, at an intersection, or elsewhere)
  8. mixed
- These are shape conditions: "a slot of this kind could fix it", not proof that it does.
- Script: tools/dream/density/t72p_classify.py.

| label (slot) | density, non-source: cases / tasks | design, priors3 + priors4: cases / tasks |
|---|---|---|
| mixed (none) | 685 / 122 | 32 / 20 |
| size (none) | 353 / 89 | 28 / 19 |
| anchor: other | 178 / 43 | 11 / 7 |
| colour only (G68 role) | 169 / 36 | 13 / 11 |
| accept: extra ink | 116 / 30 | 13 / 5 |
| anchor: midpoint | 81 / 13 | 2 / 1 |
| anchor: intersection | 74 / 26 | 8 / 5 |
| accept: overlap | 64 / 16 | 2 / 2 |
| on_stop: turn / continue | 60 / 25 | 10 / 5 |
| on_stop: paint | 58 / 20 | 2 / 1 |
| iterate | 52 / 9 | 3 / 2 |
| shift | 6 / 3 | 0 / 0 |
| **total** | **1,896 / 204** | **124 / 66** |

- **Priors3's 83 by slot:**
  - no slot: 43
  - anchor: 14
  - colour: 10
  - on_stop: 7
  - accept: 7
  - iterate: 2
- **Upper bound for the four slots on priors3:** 83 − 30 = 53 > 50.
- **Per-slot R before any code (density, distinct tasks):**
  - anchor: 65
  - accept: 43
  - on_stop: 37
  - colour: 36
  - iterate: 9
- **Mechanical check on a density sample, 25 cases per label.** Each wrapper was applied to the case's own base
  program:
  - iterate=fixpoint fixes 24 of 25 iterate cases.
  - accept=no_overlap at the cell level fixes 1 of 30 accept cases. Restoring overwritten cells does not fit the
    training pairs, so the accept predicate these cases need works on placements, inside the family.
  - The on_stop wrappers fix 0 of 50.
- **Why on_stop and anchor cannot help wrong fits.** A wrong fit already reproduces the training pairs. So a slot
  value that changes the result is either a default that agrees on train (iterate, no_overlap) or it never gets
  chosen.

**T73, the same families with slot values (O5). Before vs after, design population, one check per version.**
- **The binder** (slots.py v1.1):
  - Each base program gets these variants:
    - iterate=fixpoint
    - accept=no_overlap
    - both together
    - on_stop=paint(same | novel | new_in_some)
    - on_stop=turn(left | right)
  - Policy *default*: the iterate/accept defaults come before the base program, and the on_stop variants come after
    all base programs.
  - Policy *mdl*: base programs first. It is derived exactly: on a task where some base program fits, mdl keeps it;
    elsewhere it tries the same programs in the same order as default.
- **v1.0 → v1.1.** v1.0 crashed the priors3 run: iterating size-changing programs made their grids grow until memory
  ran out. v1.1 iterates only while the grid keeps its size. This was fixed because of the crash, before any results
  were read, and both dirs were measured with v1.1. The v1.0 priors4 ledger is kept as `*_v1.0_*`; its iterated crops
  cost 2 exact tasks.

| | priors3 before | priors3 default | priors3 mdl | priors4 before | priors4 default | priors4 mdl |
|---|---|---|---|---|---|---|
| non-source fits | 253 | 253 | 253 | 199 | 199 | 199 |
| non-source exact | 170 | **172** | 170 | 158 | 158 | 158 |
| non-source wrong | 83 | **81** | 83 | 41 | 41 | 41 |
| distinct exact tasks | 119 | 120 | 119 | 109 | 109 | 109 |
| new over V32 / over V35 components | 6 / – | 6 / 0 | 6 / 0 | 6 / – | 6 / 0 | 6 / 0 |

- Changes under default:
  - priors3: +5582e5ca (translate_object), +a65b410d (stamp_stencil_at_anchors), both through iterate.
  - priors4: +5582e5ca and −aabf363d (ray_cast_to_stop), net 0.
- mdl changes nothing. No slot variant fits a task that no base program fits.
- Density check (same binder on the 266 fitted ARC-1 tasks, 10 variants each): §2a.
- **Reading.** The action language under the existing families was not the gap. Every slot residual that exists is
  either unreachable from training (on_stop, anchor: the base program already fits) or rare (iterate: 9 tasks in
  2,007 cases).

**T74, Len's lines re-parsed for slot words.**
- Declared word lists, whole-word regex (tools/dream/o0/t74_slot_words.py).
- 9 of 38 lines contain a slot word:

| slot | lines |
|---|---|
| anchor | 7 |
| on_stop | 3 |
| accept | 2 |
| iterate | 0 |

- All of them were dropped by the G69 parse, which has no slot fields.
- My earlier rough count (19 of 36) used looser words ("each", "every"). This count replaces it.

**T76, Stitch (O3), half done.**
- The Python-AST corpus over the probe's generator modules ran on WSL: 25 abstractions, 1.50×.
- All 25 are syntax (call, compare, assign, for, append, bounds tests), and none maps to a G72 slot.
- The module counts in that run are inflated, because prior2_/prior3_/prior4_ are three versions of the same 19
  families.
- **Second corpus, ready:** 402 *drawing procedures* (functions that write grid cells or return a nested
  comprehension; nested defs are tokens) from 102 families. Each family counts once (prior3_ only) and Len's 38 line
  families are included (results/o0/stitch_draw_corpus.json + index).
- **Third corpus, ready:** arc-dsl's 400 solvers inlined into single DSL expressions (results/o0/stitch_arcdsl_corpus.json).
- **Blocked.** The cloud cannot build Stitch (crates.io and PyPI are refused by the proxy). The WSL session's local
  permission system refused to copy the built binary to the outbox ("Untrusted Code Integration"). The binary stays
  at ~/arc/stitch/src/target/release/compress.
- Given T73, Stitch can no longer change the go decision. It stays as the route-(a) cross-check, if you still want it.

**Engine (parallel).**
- **T58 PASS** on Windows: ELK 0.5.0 through the Protégé 5.6.1 jars, Java 11.0.19, 142-entry classpath.
- The classified taxonomy matches the exporter's.
- T71 re-run on the ELK taxonomy: 0 pick differences against the asserted hierarchy (17 / 19, unchanged).

**Gate and Kaggle.**
- Cycle 29 (V35): compare_gate {b 0, c 0, n_changed 0}, so P2 = 0. That makes seven concept cycles in a row.
- c45 parity digest b6c6bfd8 = V34. 85 correct design slots, max 79 s, no timeouts.
- v19 (V33): public score 2.50.
- v20 (V34) goes tonight after 20:00 EDT.

## 2a. Density check of T73

- **Setup.** The same binder (v1.1, policy default) on ARC-GEN variants 0–9 of the 266 ARC-1 tasks that had a
  baseline fit. It is compared cell by cell (task, variant, family) with the T75 baseline rows. Files:
  results/o0/t73_density.json, t75_density_slots_default_0.jsonl.txt.

| | wrong → exact | exact → wrong | non-source exact | non-source wrong |
|---|---|---|---|---|
| priors3 | 17 | 4 | 1,403 → 1,416 | 581 → 568 (−2.2 %) |
| priors4 | 7 | 7 | 1,282 → 1,282 | 356 → 356 |
| members (both) | 2 | 3 | 963 → 962 | 63 → 64 |

- Every change comes from iterate=fixpoint, alone or with accept=no_overlap.
- No cell goes from no fit to fit, so the on_stop variants add nothing on synthetic data either.
- **The direction agrees with design:** a small gain on priors3 and none on priors4. At 20× the sample the effect
  stays about 2 % of wrong fits, far from the −40 % that T73 asks for.

## 3. What this means for Oct 5

Three tiers have now been expanded and measured against the held-out gate, and none moved it:

| tier | expanded | held-out / transfer effect |
|---|---|---|
| descriptions | 60 + 1,521 + 19 | P2 = 0 ×7 |
| recognisers (O₀ roles, colour roles) | 24 + 9 | precision up, fits −21 %, P2 = 0 |
| generator slots | 4 slots, 9 values | +2 exact / −2 wrong on 253 fits; 0 new |

O9 leads with this table and the T72 residual table. The residual table is the most informative object we have:
about half of all wrong fits (48 % on design, 55 % on the density cases) are output-size or mixed errors. That points at the families' *output construction* (what to
draw where, and how big the output is), not at stop conditions or acceptance.

Files:
- tools/dream/o0/slots.py, tools/dream/o0/t73_compare.py, tools/dream/o0/t74_slot_words.py
- tools/dream/density/t72p_classify.py, t75_density.py (resume, SLOTS, DENSITY_TASKS), stitch_corpus.py (--drawing)
- results/o0/t75_density_{0,1}.jsonl.txt, t72p_density_{0,1}.jsonl.txt, t72p_*_summary.json, t72p_design.jsonl.txt,
  priors{3,4}_slots_default_ledger.jsonl.txt, t73_result.json, t74_slot_words.json, stitch_draw_corpus.json,
  stitch_arcdsl_corpus.json, t71_elk.jsonl.txt, t58_taxonomy.tsv.txt, t76_stitch_summary.json
