---
doc: fable_guidance
version: 2
date: 2026-09-29
based_on: fable_guidance_v1, fable_round_1_response, supervisor_evidence_r1
---

# Fable guidance, round 2

Advisory. Sources read in full: `claude/fable_guidance_v1.md`, `docs/fable_round_1_response.md`,
`docs/supervisor_evidence_r1.md`, `latent/prior_abduced.py`, `widen/probe_v28/occupancy2.py` (`_mdl_class_lattice`,
`_mdl_class_g`, the MDL block in `solve`), `widen/probe_v28/gdsl.py` (`search`, `nearmiss_fallback`, `fit_cmap`,
`fam_recolour_by_property`), `widen/probe_v28/prior_topology.py` (`_mdl_entries`), `fam_recolour_objects.py`,
`fam_recolour_by_colour_map.py`, `compose_objmap2.py` (`fmt_rules`), `tools/wake/{wake_eval,full_eval,parity_eval}.py`.
Convention from here on: **`|P| = n_rules`, root/default included** (response §0). Code lengths in bits unless a
"unit" is named; 1 gdsl cost unit = 4 bits (calibrated so that a parameter-free one-concept family, cost 3, is the
12-bit one-concept program of v1 Q2.4). Pipes inside code spans of tables are escaped.

## A. Convention correction and corrected numbers

**Verdict: accepted.** With the root counted, the calibration table and the v1 cost model agree without residual:
one concept + default = `|P| = 2` ≈ 12 bits; each further node ≈ 10–19 bits; typical evidence 20–60 bits; the
model puts the precision cliff at `|P| = 5` (≈ 58 bits) and the data show 15/42 at `|P| = 5`. The v1 Q2.4
discrepancy is closed. Corrected guards:

```
G6′   slot 1:  |P| ≤ 2  (34/34, CP-lower 0.916)              — one concept + default only
      slot 2:  |P| ≤ 3  (20/25, Wilson [0.61, 0.91]; ≥ 0.60 threshold met)
      empty-slot filling only (never displacing an exact fit): |P| = 4 (14/17, lower 0.59 < 0.60), |P| ≥ 5 (15/42),
                                                               then near-miss (see A.3)
      Dream trigger: ω ≠ SOLVED, i.e. no exact program with |P| ≤ 2 and margin' ≥ 4
R7′(i) P ⊨ D_t, |P| ≤ 2 (h = 1);  (ii) margin'(P) ≥ μ₁ = 4 per segmentation;  (iii)(iv) unchanged
G7′   displaceable B0 attempt classes: lattice |P| ≥ 3, compose (objmap/lift/ctx), near-miss.
      Non-displaceable: library exact fit with L ≤ 20 bits (A.2), lattice |P| ≤ 2.
```

Consequence to state plainly: an exception program `root → C → exception` has `|P| = 3` and is **slot-2 material**
until T7 measures W1's own `|P| = 3` class at ≥ 0.90; "one concept per task" is the only slot-1 form.

### A.1 V23's class rule against G5–G7′ (code read)

`_mdl_class_lattice`: `n = nrules(rules)`; class `0 if n ≤ 2, 1 if n == 3, else 2`. Correct under the convention.

`_mdl_class_g(prog)`: `nearmiss:` → 3; else if the name has `->` entries: `n = count("->")`, `0 if n ≤ 2, 1 if n == 3,
else 2`; else `parts = 1 + count("+") + count(" ; ")`, `0 if parts ≤ 2 else 1`. Four defects:

| # | defect | evidence in code | fix (exact) |
|---|---|---|---|
| 1 | `->` count is `\|P\|` only when an explicit `else ->` entry exists (`fmt_pred` prints `'else'` for the `true` predicate); without it the implicit `keep` default is uncounted, so `A -> x ; B -> y` (`\|P\| = 3`) gets class 0 | `compose_objmap2.fmt_rules`, `fmt_pred` | `n = prog.count("->") + (0 if "else ->" in prog else 1)`; class by `n` as for the lattice |
| 2 | `+colour-map` (post-step substitution table, `fit_cmap`) and `colour=table[k:n]` inside objmap actions are free (`parts` counts `+` as one concept) | `search` line 1017: `cost + 1`; `fmt_desc` prints `table[...:n]` | charge tables per entry (B.1); a program is class 0 only if `L ≤ 20` bits |
| 3 | class ignores the margin; two class-0 candidates tie by *original index* (lattice before G) | `sorted(cands, key=(class, index))` | key `= (class, −margin'_bucket, L_bits, index)`; until `margin'` exists, `(class, L_bits, index)` |
| 4 | G is consulted only if **all** lattice programs have `\|P\| ≥ 3` (`all(nrules(a) >= 3 …)`); with one short and one long lattice program the long one keeps slot 2 while a class-0 G program is never seen | `solve` line 919–920 | consult G whenever **any** of the two lattice attempts is displaceable (`any(nrules ≥ 3)` or `len < 2`); rank all candidates; keep the non-displaceable lattice attempt in place |

Should compose programs with 1–2 decision entries be class 0? Only if `|P| ≤ 2` after fix 1 **and** no table term
pushes `L` past 20 bits: `objmap[c4]: colour=3 -> keep ; else -> delete` is `|P| = 2`, ≈ 14 bits → class 0;
`objmap: size=1 -> paint 2 ; size=2 -> paint 4` with implicit keep is `|P| = 3` → class 1.

### A.2 Class from bits, not from a count

Replace the class number by `L_bits` (B.1) with class boundaries `0: L ≤ 20`, `1: 20 < L ≤ 34`, `2: 34 < L ≤ 60`,
`3: near-miss`. These reproduce the current classes for parameter-free programs (`|P| = 2` ≈ 12, `|P| = 3` ≈ 23,
`|P| = 4` ≈ 38) and demote table programs automatically. Keep the integer `cost` field for compatibility:
`L_bits = 4·cost + table_bits`.

### A.3 Near-miss guesses in slot 1 (Q-E)

On Kaggle a wrong attempt costs nothing, so filling an otherwise-empty slot with a near-miss guess is weakly
dominant. Rule: a near-miss may occupy a slot **iff no exact-fit program is available for that slot**; it never
displaces an exact fit; it is labelled `source = nearmiss` and excluded from every precision table and from
`wrong_first`; for the Dream trigger the task counts as `FAIL` (the guess goes into the signal as `NM`). V23 already
orders near-miss last (class 3); the missing parts are the label and the exclusion from calibration. Measure its
precision once on design (`k ≥ 3` pairs, `NEARMISS_MAX_CELLS = 2400` restricts it); if `< 0.05` it is still free
on Kaggle but should not be reported as coverage.

## B. Answers to Q-A … Q-E

### B.1 Q-A: one code length for table-bearing families

A lookup table is an RDR sub-tree: one node per entry (`concept = "f = key_j"`, `action = a_j`) under the default.
Under G1/G2 (every parameter charged `log₂|domain|`, 2 bits per node for the ordered-tree shape):

```
L(P) = 4·cost_base + Σ_{j > 2} e_j ,    e_j = log₂ K_f + ℓ(a_j) + 2            (bits; entries beyond the first two,
                                                                                which the base cost already covers)
K_f   = number of distinct values of the key feature f over the training grids (the induced key domain)
ℓ(a)  = log₂ 9 = 3.17 (literal colour) | log₂ 3 = 1.58 (own / bg / keep / delete role) | log₂ 24 (displacement)
```

Values: literal-colour entry `e = 6.75` (`K_f = 3`), `8.5` (`K_f = 10`, colour map); role entry `5.2` (`K_f = 3`).
In gdsl units (`÷ 4`): **1.5–2.1 units per literal entry, 1.2–1.7 per role entry**. The current `0.5` per entry
beyond two (topology only) undercharges by 3–4×, and `colour-map` at cost 1 regardless of size undercharges a
4-entry map (36 bits) by 32 bits. Kraft argument: at a fixed cost there are `(K_f·9)^{|T|}` distinct tables; with
2 bits per entry that is more than `4^{|T|}` code words, so the ranking is not a code length and the G5 theorem does
not apply to it. Compatibility with G5: `E_P` is fixed by the task while `L` grows with `|T|`, so memorised tables
are exactly what the margin removes; with G1 the entries are `θ` of one node, not new concepts.

**What is a table.** Charge only tables **induced from training outputs** (memorised). A table **read from the test
input** (legend, key row, exemplar pool) is data and costs only its reading concept:

| family (file) | table origin | per-entry charge |
|---|---|---|
| `colour-map`, `+colour-map` (`gdsl.fit_cmap/apply_cmap`) | memorised, `K_f = 10` | 8.5 bits per non-identity entry beyond the first; base 4 |
| `recolour-by-{pn}` (`gdsl.fam_recolour_by_property`, 13 features) | memorised over `pval` | `log₂ K_f + 3.17 + 2`; base 12 covers `f` + 2 entries |
| `recolour-objects:{mode}[{fname}]` (`fam_recolour_objects.induce_table`) | memorised | same; role actions (own/bg/keep) at 1.58 |
| `topo:recolour`, `topo:fill`, `topo:cellmap` (`prior_topology._mdl_entries`) | memorised | replace `0.5·max(0,\|T\|−2)` by `Σ_{j>2} e_j / 4` units |
| objmap `colour=table[k:n]` (`compose_objmap2.fmt_desc`) | memorised | `n` entries at `e_j`, added to the rule's node cost |
| `recolour-solid-blocks[T]` | one parameter | `log₂ 30` |
| `key-position`, `legend-map`, `key-recolour`, `recolour-shape-match` (exemplar pool) | read from input | 0 per entry |
| `program:turtle-glyph-strokes` (`prior_abduced.fam_turtle`, `strokes` dict) | memorised: 3×3 mask → (dir, n) | `9 + 1.58 + log₂ n_max + 2 ≈ 15.6` per glyph; 4 glyphs ≈ 62 bits (class 2, not cost 4) |

### B.2 Q-B: what the observed reuse implies

Data: 20 families, 22 exact alone on 1120 public tasks, 4 fires outside source tasks (all `test_seen`). Per
(concept, task) non-source rate `q_abd = 4/(20·1100) = 1.8·10⁻⁴`. For the whole G library, `37` N2 exact over
`≈ 200` families gives `q_lib = 37/(200·101) = 1.8·10⁻³`: **the abduced families are 10× more task-specific than
the average library family.** Expected held-out gain per abduced concept: `51·q_abd = 0.009` on N2-decide,
`0.022` on the pooled 121 decision set, `0.022` on a 120-task hidden set. Concepts needed for `c ≥ 6` with `b = 0`:
**≈ 650 on N2-decide, ≈ 275 pooled.** At 5 test-blind abductions per day, Oct 12 brings ≈ 60 → expected +1.3
pooled, `P(c ≥ 6) ≈ 0.2 %` (Poisson). Even at the library's rate, 60 concepts give ≈ +13 pooled expected only if
they were as general as the average library family, which the data say they are not.

Model reading (v1 D.3): `ε ≈ q·(1 + reuse)` is tiny, so the loop converges trivially (few productive steps) and
transfers nothing; `ζ^{N2}` would read 0. The unit of abduction is wrong: the families with any reuse are the
**role/relation** recognisers (boundary role, nearest object, cavity, `is_square`, inside→outermost); the ones with
zero reuse are **whole-grid programs with a rigid parse** (turtle, drape, rainbow, dashed border, mirror panels,
crosshair). Operational criterion, added as a warning (not a gate): fire ratio `φ(C) ≥ 0.01` on design grids; every
abduced whole-grid family has `φ ≤ 0.004`, every role recogniser `φ ≥ 0.05`.

What to abduce instead (the right level is an **A-box predicate or relation**, entering the lattice/RDR as a node
under the seed rule, not a whole-grid family): `cell_role ∈ {corner, edge, interior}`, `nesting_depth(o)`,
`innermost(o)`, `nearest_object(o)`, `in_line_of_sight(o, src)`, `touches(o, colour)`, `panel_of(cell)`,
`target_of_pointers(cell)`, `supported(o)`, `enclosed_by_one(o)` (cavity). V22's loss of 5 came from **low-level
motion attributes with a tie-break**, not from role attributes; the fix is the seed rule inside the lattice (a prior
attribute is admitted to task `t`'s attribute list only if its extension covers the changed cells in every pair),
which is the front-running rule applied to attributes (D, lever L4).

### B.3 Q-C: W1 v0 over library families as nodes

Worth building **as a measurement, not as a solver**: the 200-family scan costs < 10 s per task, so locality buys no
time; it buys the test of the locality hypothesis and the W1 infrastructure (seeds, signal, counters, failure
classes). Specification:

```
nodes  : families F (≈ 220, grounded: recogniser = "fn(x_i) ≠ None on every training input" (precondition fires),
         generator = fn); primitives Π (objects c4/c8, bbox, panels, rays, symmetry, colour counts, …: the helpers a
         family calls); domains Δ (name prefix before ':' or the docstring "Groups:" line)
edges  : F —uses→ π (static call graph of the family's module), F —inDomain→ δ, F —sharesPrimitives→ F' (≥ 2 shared π),
         F —refines→ F' (F' name is a suffix-variant of F, e.g. recolour-by-size / -by-size_rank)
π rank : number of design tasks the family fits (snapshot), ties by name; adjacency cut to m = 8 by rank
seeds  : families whose precondition fires on all training inputs AND whose output changes ≥ 1 changed cell correctly
         in every pair (recall ≥ 1 relaxed to "touches Δ"); top s_max = 4
search : k ≤ 2 neighbourhood; programs = single family, family + colour-map, family ; family (search2 shape)
```

Decisive experiment (`T13`): for every design task solved by family `F*` under the full scan, record whether
`F* ∈ N_2(seeds)` and its rank. Pass if `≥ 70 %` of solved tasks have `F* ∈ N_2` with `|N_2| ≤ 292`; if `< 50 %`
the neighbourhood hypothesis fails at this granularity and mining 𝒦 is premature (mined edges would be added to a
graph whose own edges do not predict solutions). The graph also yields the NO_SEED statistics for B.4 for free.
Cost: 1–2 days; expected held-out gain by Oct 12: 0.

### B.4 Q-D: NO_SEED proposals

Cheapest sound procedure, in a fixed order (steps 1–2 are deterministic and need no Dream):

1. **Relax the seed rule** (no new code beyond ordering): (a) cover `Δ` in `≥ n_t − 1` pairs; (b) recall ≥ 0.5 of
   changed cells in every pair; (c) **target seeds**: concepts firing on the *output* grids' new individuals. Any hit
   reclassifies the task `NO_FIT` with the usual ball. Most generation tasks are NO_SEED only because seeds are
   computed on inputs.
2. **Analogy proposal**: compute a change signature `Σ(t)` = multiset of tokens over `Δ` (object counts in/out,
   colour roles in/out, size ratio bucket, position relation to the nearest unchanged object, shape-class change,
   grid-size relation); propose the concepts that solved the `k = 3` nearest **solved design tasks** by Jaccard on
   `Σ`. Sound under G30(a) (pre-existing grounded concepts only), ball = `N_2` of those concepts, cost `O(|𝒟|)`.
3. **Free proposal** (LLM/reviewer) from `σ(t)` with `Σ(t)` in the prompt, test-blind; mining bounded by `M = 930`;
   one proposal per **signature group** (dedup on `Σ`), priority by group size.
4. Budget: NO_SEED groups get at most `⌈a_c/2⌉` of the cycle's steps; the rest goes to NO_FIT/WRONG where the ball is
   small. With role-level recognisers (B.2) NO_SEED becomes rare, which is the real fix.

### B.5 Q-E

Answered in A.1–A.3: fix the four defects, rank by `L_bits` with class boundaries, near-miss only into empty slots
with the label, and consult G whenever any attempt is displaceable.

## C. The 20 abduced families as T-box concepts

Legend: **G** = genuinely general (outside-domain concept, few parameters from declared domains); **S** = over-specific
(layout or parse encodes the source task); **(b)** = G30(b) violation (task constant in code); **(b′)** = fire-ratio
ceiling; **φ↓** = below the 0.01 abstraction floor (all 16 whole-grid families; listed once here).

| family (`prior_abduced.py` unless noted) | verdict | what encodes the source task | smallest generalisation |
|---|---|---|---|
| `optics:line-of-sight[axis]` | G | `len(objs) < 3` scene constant (minor) | expose relation `in_line_of_sight(o, src)`; source = role "unique colour" |
| `geometry:nearest-neighbour[rest]` | G (reuse 2) | body = unique largest object | expose attribute `nearest_object_colour(o)` for every object |
| `optics:rainbow[k,corner]` | S | odd square only; spectrum read on the centre→corner diagonal; L-shaped bands | decompose: `spectrum(drop)` (ordered colours along any ray) ∘ `period-extend` (library) ∘ `concentric-rings` (library `fam_summarise_concentric_rings`); keep as a program, not a concept |
| `topology:innermost-interval[axis]` | G idea, S parse | every non-empty line must have exactly 2 same-colour cells (`len(cells) != 2 → None`) | intervals = same-colour endpoint pairs on a line with any other content; relation `strictly_inside(I, J)`; role `innermost` |
| `graphics:dashed-border` | S | interior must be empty; exactly one dash; `n % 2L == 0` | periodic completion along a closed path = `period-extend` on the perimeter walk |
| `physics:fronts-meet-halfway` | duplicate | exactly 2 objects; fills the whole grid corridor (`range(h)`) | it is Voronoi with axis distance: merge into `fam_recolour_by_distance_layers` (`vor`) |
| `topology:boundary-roles[…]` | **G** (reuse 4) | solid rectangles ≥ 3×3 | expose `cell_role` as a lattice attribute; actions own/bg/literal already colour-free — the model to copy |
| `chemistry:reaction[a+b->c]` | G | only `at = 'a'` variant survives; reactants = "the two colours that change" | relation `touches(o, colour)`; reactant colours as roles ("the two changing colours") |
| `arithmetic:panel-dye[+k]` | S, dubious domain | colour `+k mod 10` is an ARC artefact; one marker per panel | concept = "panel takes its unique marker's colour" (`k = 0`); `+k` is a colour map (charged) |
| `physics:drape-over-pole[rot]` | S (test_seen) | sheet must be the top row; pole a single column; 45° | keep as program; no cheap concept |
| `fluids:pour` | **G** | none (a simulator) | generator `γ_liquid`; fine |
| `masonry:bridge-gaps[c2,rot]` | S, **(b)** | `y += 2` layer spacing hard-coded; `c2` from output ✓ | spacing = induced parameter in `{1,2,3}` or derived from stone height |
| `geometry:crosshair[c2,gap]` | G | bars ≥ 2 cells (minor) | relation `target_of_pointers(cell)`; fine |
| `optics:mirror-panels[m,blank]` | composite | two concepts in one family (mirror in panel; fill blanks in plain panel); separator parse | split into `mirror-in-panel` and `fill-panel-blanks`; RDR combines them (`\|P\| = 3`) |
| `program:turtle-glyph-strokes` | S, **(b)**, table | `seps[0] != 7 → None` (separator column 7 hard-coded); glyph slots at cols 0–2 / 4–6; block stride 4; `strokes` memorised | separator = any full column; glyphs = 3×3 components left of it; stroke **derived** from glyph geometry (arm direction, cell count) — else charge the table (≈ 62 bits, B.1) |
| `combinatorics:sort-bars-by-height[order]` | G | exactly one full axis row | "sort objects along an axis by size"; compare `fam_summarise_ranked_bars` |
| `cavity` (selector, `fam_fill_bg_windows`) | **G** (right level) | corner proxy for "one shape" | separability by rigid motion (planned) |
| `is_square` zone feature | **G** (right level) | — | — |
| `topo:recolour` inside→outermost | **G** (right level) | — | — |
| `drape`/`turtle`/`rainbow` as a group | φ↓ | fire on ≤ 4/1120 | these are **programs**; count them in G, not as T-box concepts |

G30(b) violations: `turtle` (column 7, slot columns), `bridge` (stride 2). (b′) violations: none (all fire rarely; the
problem is the opposite floor). Six of six test-blind checks exact is evidence that the **procedure produces correct
source-task programs** (`P(6/6 | p = 0.5) = 1.6 %`), not evidence of transfer.

## D. Twelve days to Oct 12

Constraints: one Kaggle slot per day (v15 = B0 running; V28 parity pending), WSL ≈ 1.5 h per full job and 30 min per
parity, cloud 2 cores, decision set sealed until Oct 12. Levers ranked by expected held-out gain per day; each has
the measurement that decides it. Gains are on the hidden set (≈ 120 tasks), assuming the N2-gate rate transfers.

| rank | lever | expected hidden gain | days | deciding measurement (all on N2-gate as `(b, c)`) |
|---|---|---|---|---|
| L1 | **Ship the MDL slot fixes** (V23/V24, or V28 if parity passes) | +2–4 (design flip rate 22/603 = 3.6 %; N2 fit rate is lower, so ≈ 2 %) | 1 | c25/c26 full jobs: `b = 0` and `c ≥ 1` on N2-gate → submit next slot |
| L2 | **Charge tables + fix the four class defects** (A.1, B.1) → V29 | +0–2 (7d1f7ee8-type crowd-outs) | 1 | design: no task lost, list of flips; N2-gate `b = 0` |
| L3 | **Slot-2 policy**: next distinct prediction from the next class; near-miss only into empty slots, labelled | +0–1 (free) | 0.5 | `s₂`, fraction of design tasks with an empty slot 2 |
| L4 | **Seed-gated role attributes in the lattice** (`cell_role`, `nearest_object_colour`, `nesting_depth`, `touches`, `panel_of`, `enclosed_by_one`) with `M1B_SINGLE` and the seed rule | +0–3 by Oct 12, the only lever that scales past it | 3–4 | design exact/wrong vs V21 (must beat V22's −5); N2-gate `(b, c)` |
| L5 | **Test-blind abductions** at the role level (B.2), 4–6 per day | +0–1 (0.02 per concept at the current level) | continuous, cloud | per concept: `φ ∈ [0.01, 0.5]`, harness check, `E(test) ≥ 10` |
| L6 | **W1 v0 locality test** (B.3, T13) | 0 | 1–2 | `≥ 70 %` of solving families in `N_2(seeds)` → mining justified for Nov 2 |
| L7 | **Read the v15 Kaggle log**: `κ`, `N_K`, outputs | 0, unblocks G27–G29 | 0.2 | `κ = max(1.5, measured)` |
| L8 | **Protocol repairs** (E1–E3): private per-task N2-gate record, `(b, c, n_changed)` comparer, auto-ledger, `halfB_count` default off | 0, makes L1–L5 measurable | 0.5 | `(b, c, n_changed)` appears in every summary |

Schedule: **D1** L7, L8, L1 (parity V24/V28 → slot). **D2** L2 → V29 full job (WSL) + parity. **D3** L3; start L4 on
cloud. **D4–D7** L4 (design run each night); L5 in parallel (cloud). **D8–D9** L6 while L4's job runs. **D10–D11**
freeze the Oct 12 candidate = the last build with `b = 0` on N2-gate and the highest `c`; run its parity; submit.
**D12 (Oct 12)** one decision look: `(b, c)` on the pooled 121-task set; transfer claimed iff `c ≥ c_min(b, 0.025)`
(`b = 0 → 6`) — which, by B.2, will almost certainly not be met by abduction; the honest expected outcome is
"directional evidence from L1/L2 (`c` of 1–3), no significant transfer". The Kaggle daily score remains the only
hidden look; do not chase the public leaderboard.

## E. Contradictions and risks in V23–V28 + protocol

| # | risk | evidence | fix |
|---|---|---|---|
| E1 | The gate condition `b = 0` cannot be checked: tools emit only `N2_gate_exact_count` / `fit_count`, and N2 rows are never written (`if r["task"] not in N2: f.write`) | `wake_eval.py` 63–70, `full_eval.py` 66–73 | write `n2_gate_private.jsonl` with `(sha256(salt‖id), exact, ph)`; a comparer emits `(b, c, n_changed)` vs B0's record and nothing else |
| E2 | `halfB_count: true` is the default job config; every job computes half B into `decide_sealed.json` | `wake_eval.py` line 5 | default `false`; compute only on the two decision days |
| E3 | No looks ledger in the tools (the response says looks "will be logged") | grep: no `ledger` | auto-append `looks_ledger.jsonl` whenever `N2_gate_*` is written |
| E4 | Local evaluation uses a **wall-clock** per-task timeout (`"timeout": 25`), so local exact counts are machine-dependent while Kaggle uses work budgets; T1 cannot pass across machines | `wake_eval.py` line 5, `timeouts` field | replace by the engines' work counters; keep the alarm only as a crash guard with the task marked, not silently failed |
| E5 | `_mdl_class_g` defects 1–4 (A.1): decision lists with implicit default under-counted; tables and colour maps free; G unseen when one lattice attempt is short | code | A.1, B.1 |
| E6 | The V23 "21/22" and "no loss on 47" are **in-sample**: the rule was designed on those tasks | evidence §1 | report only N2-gate `(b, c)` as evidence; design figures as diagnostics |
| E7 | `nearmiss` cost `+10` is ignored by the class rule (class 3 regardless), and a near-miss can be reported as a "solve" in `occupied` | `nearmiss_fallback`, `wake_eval` `occupied` | A.3 label; `occupied` excludes `source = nearmiss` |
| E8 | 13 families are `test_seen`; V28 ships them with 0 held-out fires — harmless on Kaggle, but any design gain from them must not enter T3 | response §2 | tag rows `test_seen`; T3 counts exclude them |
| E9 | Kaggle notebook size: v14 (1.43 MB) refused, 0.66 MB compressed accepted — `B` for the notebook is ≈ 1 MB, not 64 MB | response §1 | the frozen `O` ships as a compressed payload or an attached dataset; G14's `B` becomes `B_notebook ≈ 1 MB`, `B_dataset` large; test the dataset route once before Nov |
| E10 | The G scan is `Θ(#families)` per task (`candidates(train)` runs every family) — the `\|O\|`-dependence G10 forbids, in disguise; at 220 families it is < 10 s, at 500 it is not | `gdsl.candidates` | measure `candidates()` time per task on parity; cap families per task by the seed/neighbourhood rule (B.3) before the count doubles |
| E11 | Corrected G6′ makes exception RDR slot-2 only, while the design principle says "exception RDR replaces conjunctions" | A | no contradiction in scoring (slot 2 counts); calibrate W1's `\|P\| = 3` class (T7) before promoting |
| E12 | Abduction throughput (10–30 min each, all by the supervisor) is the binding constraint and its yield (B.2) cannot reach the Oct 12 threshold | evidence §3, B.2 | shift to role-level recognisers (L4/L5); stop counting whole-grid families as concepts |

## F. Machine-readable summary

```json
{"guards":[
 {"id":"G6","rule":"G6': slot1 |P|<=2 (root incl.); slot2 |P|<=3; |P|>=4 only into empty slots; Dream trigger = no exact |P|<=2 with margin'>=4","params":{"p_max_slot1":2,"p_max_slot2":3},"metric":"Wilson lower bound by |P| class on design","threshold":"<0.90 slot-1 class; <0.60 slot-2 class","action":"demote class","status":"changed"},
 {"id":"G7","rule":"G7': displaceable B0 classes = lattice |P|>=3, compose, near-miss; non-displaceable = library exact fit L<=20 bits, lattice |P|<=2","params":{"L_class0_max_bits":20},"metric":"design tasks solved only by displaced attempts","threshold":">0","action":"restore attempt","status":"changed"},
 {"id":"G2","rule":"table entries charged: L=4*cost_base+sum_{j>2}(log2 K_f+l(a_j)+2) bits for memorised tables; tables read from the input cost 0 per entry","params":{"unit_bits":4,"literal_colour_bits":3.17,"role_bits":1.58,"colour_map_entry_bits":8.5},"metric":"Kraft check on table programs","threshold":"(K_f*9)^|T| > 2^{L}","action":"fix charge","status":"changed"},
 {"id":"G5","rule":"unchanged (mu1=4 per segmentation); class ordering key = (class, -margin bucket, L_bits, index)","params":{"mu1":4,"mu2":0},"metric":"precision by margin bucket","threshold":"<0.85 at margin>=4","action":"raise mu1","status":"unchanged"},
 {"id":"G30","rule":"add warning (not gate): fire ratio phi(C) >= 0.01 on design grids; whole-grid families with phi<0.01 are programs, not T-box concepts","params":{"phi_min":0.01,"phi_max":0.5},"metric":"phi(C)","threshold":"phi<0.01 warn","action":"decompose into role/relation recognisers","status":"changed"},
 {"id":"G18","rule":"per-cycle release must be (b,c,n_changed) from a private per-task N2-gate record; auto-ledger; halfB_count default off","params":{"L_looks":12},"metric":"ledger rows","threshold":"missing (b,c)","action":"job invalid as evidence","status":"changed"},
 {"id":"G21","rule":"no wall-clock timeouts in local evaluation; work counters only; alarm marks the task","params":{},"metric":"cross-machine exact-count equality","threshold":"any mismatch","action":"fail T1","status":"changed"},
 {"id":"G14","rule":"B_notebook ~1 MB (API refused 1.43 MB); frozen O ships compressed or as attached dataset","params":{"B_notebook_MB":1,"B_dataset":"large"},"metric":"payload size","threshold":">1 MB uncompressed in notebook","action":"use dataset route","status":"changed"},
 {"id":"G10","rule":"G scan time per task measured; families per task capped by seed/neighbourhood before library exceeds 300","params":{"families_max_scan":300},"metric":"candidates() seconds per task","threshold":">10 s","action":"cap by neighbourhood","status":"changed"}
],
"decisions":[
 {"id":"D5","choice":"near-miss guesses fill only otherwise-empty slots, labelled source=nearmiss, excluded from calibration and from 'occupied'; task counts as FAIL for Dream","rationale":"wrong attempts cost nothing on Kaggle; they must not contaminate precision tables"},
 {"id":"D6","choice":"classes derived from L_bits (0: <=20, 1: <=34, 2: <=60, 3: near-miss) with memorised tables charged per entry; G consulted whenever any attempt is displaceable","rationale":"count-based classes violate Kraft and hide table size; V23 misses class-0 G programs when one lattice attempt is short"},
 {"id":"D7","choice":"abduce role/relation recognisers (phi in [0.01,0.5]) that enter the lattice under the seed rule; whole-grid families stay in G as programs","rationale":"abduced families are 10x more specific than the library average (q=1.8e-4 vs 1.8e-3); 275-650 such concepts would be needed for c>=6"},
 {"id":"D8","choice":"W1 v0 built over library families as a locality measurement (T13) before any mining","rationale":"decides whether neighbourhood search predicts solutions at this granularity; costs 1-2 days, gains nothing by Oct 12"},
 {"id":"D9","choice":"Oct 12 candidate = last build with b=0 on N2-gate and highest c; levers ranked L1..L8; expected outcome is directional evidence, not a significant transfer claim","rationale":"B.2 arithmetic"}
],
"tests":[
 {"id":"T13","description":"locality test: solving family in N_2(seeds) with |N_2|<=292","pass_criterion":">=70% of design solves; <50% means mining is premature"},
 {"id":"T14","description":"table charge regression: 7d1f7ee8-type tasks and all design tasks after B.1","pass_criterion":"no design task lost; Kraft check passes on 1e4 sampled table programs"},
 {"id":"T15","description":"class-rule fixes 1-4 on the 22+47 targeted tasks and on all design","pass_criterion":"21/22 kept; 47 kept; every flip listed with L_bits before/after"},
 {"id":"T16","description":"(b,c,n_changed) comparer vs B0 private record on N2-gate","pass_criterion":"emits exactly three integers; b=0 for any build to be admitted"},
 {"id":"T17","description":"seed-gated role attributes vs V22's 5 lost tasks","pass_criterion":"none of the 5 lost; design exact >= V21"},
 {"id":"T18","description":"near-miss labelling","pass_criterion":"occupied and precision tables exclude source=nearmiss; slot 1 never holds a near-miss when an exact fit exists"}
]}
```
