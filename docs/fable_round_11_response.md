---
doc: fable_round_response
responds_to: claude/fable_guidance_v11.md (21:30 / 21:50 EDT Oct 1)
date: 2026-10-01 (22:50 EDT; B2, T60, T69 added 22:57 EDT)
from: cloud Claude (supervisor)
---

# Round 11 response

## 1. Decisions

| item | verdict | status |
|---|---|---|
| G62 restated (≤ 4 individual variables in description definitions; base O₀ rules unbounded, admitted by W_mat + T59) | adopted | the 147 base rules are in bound |
| G63 changed (lazy DC, change-set cell relations, per-relation cap) | adopted | implemented and re-measured (B1, §2) |
| G68 changed (declared colour-role set; no literal colours) | adopted for measurement | T68 below; one amendment proposed |
| G69 composition parse | adopted | T69 running |
| D36 T58 via Protégé's ELK | adopted; **blocked** | Len approved; the Windows session found Protégé 5.6.1, `elk-protege-0.5.0.jar`, the OWL API bundle and javac (Java 11.0.19), but its local safety check refuses to compile code that arrived through the outbox. It runs once Len approves inside that session. |
| D37 no seventh concept cycle; Oct 5 report pre-written; V33/V34 standing notebook | adopted | v19 (V33) submitted Oct 2 01:48 UTC, Kaggle parity match (de2bd55e), score pending; v20 (V34) is LATEST for the Oct 3 UTC slot (V34 max 103.9 s against the 300 s task cap) |
| D38 colour roles before any new generator | adopted | T68 below |

## 2. Results

**B1, T59 under the new G63: pass.** 4,153 / 4,153 design grids hash-equal; DC is a lazy view `!connected(I, J)`,
never stored, checked against the item code. W_mat max 215,801 → 128,207, mean 15,079 → 12,020; grids over the
per-grid cap 2 → 0; no relation reaches the per-relation cap (largest now rbn 34.7 k); rdflib SPARQL agrees on
140 / 140 grids including the DC view. Datalog 0.044 s mean, 0.82 s max per grid.
**Open point (Δ).** The change set exists only where a training output of the same size exists: 2,007 inputs. On
the 1,046 test inputs and on 1,100 size-changing training inputs Δ = ∅, so cell–object `dir_rel` / `allen` are not
materialised there. Which Δ should Wake use on a test input: the cells at the training pairs' Δ positions
(same-size tasks only), the cells inside the objects' bounding boxes, or none?

**T68, priors3 re-parameterised over the declared colour roles (no literal colours), measured with prior_check:**

| | priors3 | priors4 (roles only) |
|---|---|---|
| member fits | 194 | 160 |
| non-source fits | 253 | 199 (−21 %) |
| non-source exact | 170 | 158 |
| non-source wrong | 83 | 41 (−51 %) |
| distinct non-source exact tasks | 119 | 109 (9 gained, 19 lost) |
| new over V32 | 6 | 6 (95a58926 in, c92b942c out) |

- The biggest loss is learned_key_table (members 15 → 2). Its fits are colour-to-colour tables learned from the
  training pairs, and no role names those colours.
- The implementers had to define six roles inside families to keep fits: vanishing colour (in every input, absent from
  every output), inert colour (in every input, never changes), common colour (in every input), panel marker (the
  one colour in exactly one panel), training background, and "new in some output".
- **Reading.** Roles only make the families more precise: half the wrong answers go, and 79 % of non-source fits are
  exact (was 67 %). They also cost a fifth of the fits, because fixed palettes are a real property of some tasks.
- **Proposal (G68 amendment):**
  - Extend the declared set with vanishing, inert and common colour.
  - Keep a learned constant as the last resort, charged its literal cost in the MDL order, instead of forbidding it.
  - Order: role first, then role-bound value, then learned constant.
  - In the build, the roles-only pass can go in as a stratum before the second pass, so its higher precision gets the
    first slot and the literal fits still fill empty ones.

**B2, Route A over the materialised A-box: pass.**
- The five Route A roles and the inherited memberships come from one Datalog run per grid
  (tools/datalog/routeA_rules.dl.txt, tools/dream/routeA_dl.py).
- Role and membership sets are hash-equal to the Python roles on all 69 Route A grids, and on 18,360 of 18,360
  design input grids across the 5 segmentations (1,095 grids could not be segmented on either side).
- The engine is called 69 times (once per grid) and never inside the search (G64). It takes 1.3 ms mean, 6.6 ms max
  per grid.
- T24 is unchanged: 19 programs, 17 recovered, 11 with margin ≥ 4. Two lines differ only in W_sub (+9, +1),
  because of set insertion order.
- The asserted lattice T-box adds no inherited names on these grids.

**T60 with the asserted hierarchy: the ties are not resolved.**
- On both tie cases the competing names are unrelated depth-0 roots, so subsumption cannot order them.
- The IRI tie-break picks D1:size_rank_asc=0 on aabf363d (right, by IRI luck) and D10:largest_of_its_color on
  b230c067 (wrong).
- A taxonomy predicted from the exported axioms gives the same picks, so ELK is not expected to change T60 unless
  the hierarchy over lattice names is enriched.
- **Question:** should the lattice names get parents (e.g. square_bbox ⊑ shape-property, touches_border ⊑
  position-property)? They would come from the schema tops, not authored per pair.

**T69, composition parse (G69):**
- 291 records lift to two schemas: 236 split into shared-variable pairs, 55 unsplit (50 have no text for the second
  schema, 5 were returned under G61). All 11 composed frames split.
- T53: parse rate unchanged (189/210). The same 14 tops, all reachable in pairs (82 ordered pairs; most common
  MATCHING > PART-WHOLE, 15).
- T55′ with composed nodes (index3): only CENTER-PERIPHERY + CYCLE qualifies among the schema pairs that have modules
  (3,136 node pairs). The far-68 result is still 5/68, the same 5 tasks; composed nodes add none. This meets the
  ≥ 5 floor and nothing more.

## 3. In progress (Oct 2–5)

- **T58 / T60:** ELK runs once Len approves it on Windows; T60 re-runs on the real taxonomy.
- **A2:** Oct 5 report drafted with blanks (claude/oct5_stop_rule_report_draft.md).
- **A3 / T66:** proposed to Len (10 tasks get his lines, 10 get the LLM's readings, chosen by hash among V32
  failures). Waiting for his yes, since it needs his time.
- **C3(b) / T67:** the action-gap table for the 45 nameable-but-failing tasks follows T68.
- **D1:** the N2-id comments go out in the next rebuilt probe.

Files: tools/dream/o0/colour_roles.py, tools/dream/o0/priors4/, results/o0/priors4_ledger.jsonl.txt, tools/datalog/
(engine.py, o0_rules.dl.txt, t59_parity.py, sparql_check.py), results/o0/t59_parity.json, results/o0/t59_sparql_check.json,
submission/v20, docs/oct5_stop_rule_report_draft.md.
