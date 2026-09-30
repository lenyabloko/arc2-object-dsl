---
doc: fable_sub_guidance
version: 3
date: 2026-09-29
based_on: fable_guidance_v2, V29 code (widen/probe_v29), tools/wake (compare_gate.py, full_eval.py, wake_eval.py)
---

# Fable guidance, round 3 (closing)

Read: `diff probe_v28 probe_v29` for `occupancy2.py`, `gdsl.py`, `prior_topology.py`; `prior_topology._choose`;
`fam_recolour_objects.induce_table/apply_table`; `compose_objmap2` lines 820, 1444, 1500; `tools/wake/compare_gate.py`,
`full_eval.py` 63–83, `wake_eval.py` 5, 60–79. Convention: `|P| = n_rules` (root included); 1 unit = 4 bits.

## A. Code verification

### A.1 V29 (`widen/probe_v29`)

| item | status | finding | exact fix |
|---|---|---|---|
| fix 1: implicit default counted | ✓ | `n += 0 if "else ->" in prog else 1` | — |
| composite count class | **bug** | `parts = 1 + count("+") + count(" ; ")`, class 0 if `parts ≤ 2`: `A ; B` (`\|P\| = 3`) and `X+colour-map` (`\|P\| = 3`) get count class 0; only the bits class rescues them (`cost ≥ 6`) | `n_nodes = 1 + (1 + prog.count(" ; ")) + prog.count("+")`; `c_count = 0 if n_nodes <= 2 else (1 if n_nodes == 3 else 2)` |
| bits class `L = 4·cost`, boundaries 20/34/60, `max(c_count, c_bits)` | ✓ | consistent with v2 A.2; near-miss returns 3 before `cost` is read | — |
| sort key `((class, short-lattice flag, bits), index)` | ✓ | lattice `\|P\| ≤ 2` never displaced (G7′); G programs ordered by bits, then original order | — |
| fix 4: G consulted when `any(nrules ≥ 3)` or `< 2` attempts | ✓ | — | — |
| `_lattice_bits = 12 + 11·max(0, n−2)` | ✓ (approx.) | rule literals and lattice tables are not charged; acceptable for this build | later: `+ 1.7` per table entry beyond two inside lattice rules |
| `_cmap_units(m) = 2.125·max(0, n_nonid − 1)` on `colour-map` and `+colour-map` | ✓ | `= 4 + 8.5·(n−1)` bits, as v2 B.1 | — |
| `_mdl_entries`: `vals = sorted(table, key=repr)[2:]`, 1.7 literal / 1.3 role | ✓ deterministic, **allowance arbitrary** | which two entries are free depends on `repr` order, so the same table can cost 0.4 units more or less depending on key names | `e = [1.7 if literal(a) else 1.3 for a in table.values()]; return max(0.0, sum(e) - 2.6)` (two-role allowance) |
| `fam_recolour_by_property` (gdsl, 13 features) | **not done** | table `m` (value → literal colour) still cost 3 | `yield (…, 3 + 1.7*max(0, len(m) - 2), fn)` |
| `fam_recolour_objects.fam_recolour_object_feature` | **not done** | table `t` (value → `("lit",c)`/`("keep",)`/`("own",)`/`("bg",)`) still `4 + nearest` | `4 + nearest + max(0, sum(1.7 if r[0]=="lit" else 1.3 for r in t.values()) - 2.6)` |
| objmap `colour=table[F:n]` | **not done** | `compose_objmap2` line 820: `1.5 + 0.4*len(cx[2])` in objmap's own cost scale | `1.5 + 1.7*max(0, len(cx[2]) - 2)`; and in `_mdl_class_g` add `1.7*max(0, n-2)` units for every `table[…:n]` in the name (`re.findall(r"table\[[^:\]]*:(\d+)\]")`) so the bits class sees it |
| near-miss labelling (D5) | **not done** | `nearmiss:` programs still count in `occupied` and enter precision tables | `source = "nearmiss"` on the attempt; `occupied` and every precision table exclude it; ω = FAIL for Dream |

### A.2 Protocol tools (`tools/wake`)

| item | status | finding | exact fix |
|---|---|---|---|
| private record `n2_gate_private.jsonl.txt` (`hid = sha256(SALT‖id)[:16]`, `exact`, `ph`, sorted by hash) | ✓ | written by `full_eval.py` 80–83 and `wake_eval.py` 76–79 | — |
| `compare_gate.py` → `(b, c, n_changed)` only, ledger append | ✓ | asserts equal gate sets; prints three integers | add `"salt": SALT` and a `cycle` field to the ledger row; assert both records carry the same salt |
| `hid` reversible | **gap** | the hid salt **is** the public split salt, and `novel_N2.txt` is in the repo: anyone (or any tool) can map `hid → task id`; reading the file is a per-task look | second salt from outside the repo (`N2_HID_SALT` env var or `~/arc/.hid_salt`), never printed; fall back to refusing to write the record if unset |
| per-job counts in `summary.json` (`N2_gate_exact_count`, `N2_gate_fit_count`) | **gap** (E1 half-done) | every job's summary is a look (two counts), and it is not ledgered; several jobs per cycle = several looks | remove both from `summary.json` (keep `N2_gate_n`, `N2_salt`); the only release is `compare_gate` for the cycle's candidate, once |
| ledger auto-append on summary write (E3) | not done, moot after the fix above | — | — |
| `wake_eval.py` line 5 default `"halfB_count": true` | **bug** (E2) | the two queued jobs override it, the default still computes half B for every new job | `"halfB_count": false` in the default; `true` only in the two decision-day jobs |
| `"timeout": 25` wall-clock per task (E4) | **open** | local exact counts are machine-dependent; T1 cannot pass; a slow machine reports fewer solves | engines' work counters; alarm only marks `timeout=true` and the task is excluded from exact/occupied on both sides of a comparison |

## B. Item 3: 60b61512, the V24 rule and `search2`

**The V24 rule is right** (a program that refuses a test input cannot fill an attempt; letting it occupy one of
`max_programs = 6` slots was a bug). The regression is **stage ordering** in `gdsl.search`: `if not res: res =
search2(task)`; `if not res: res = compose_fallback(task)`. Before V24 the inner `search(sub, max_programs=2)` inside
`search2` filled its two slots with refusing programs, so `search2` returned nothing and `compose_fallback` (right)
ran; after V24 the refusers are skipped, a wrong but fitting `stencil` step is found, `search2` returns
`geom-sym-complete ; stencil` (cost 9 = 36 bits) and `compose_fallback` never runs. V29 then ranks correctly among
what it sees (lattice `|P| = 4` = 34 bits < 36) but the right objmap program is not a candidate.

Exact rule (replace the three `if not res` lines):

```
single = verified single-step programs, refusers excluded                     # V24 rule kept
if single: return rank(single)
cands = search2(task) + compose_fallback(task)          # both, whenever no single-step program exists
if cands: return rank(cands)                            # key = (bits, n_nodes, stage) with stage: compose < search2
return nearmiss_fallback(task)                          # empty slots only, source = nearmiss
bits: search2      = 4·cost (table steps charged, A.1)
      objmap/lift  = 12 + 11·(|P| − 2) + 6.8·max(0, n_table − 2), |P| from the "->" count with the implicit default
```

Ties go to `compose` (object-level RDR is the calibrated class; grid-level two-step composites are the class that
carries 14 of 20 wrong G programs, evidence §4). Cost: `compose_fallback` now runs on every task with no single-step
program, which is the pre-V24 profile plus `search2`; re-check the parity maximum (60.5 s). With this rule 60b61512
returns the objmap program at ≈ 23 bits ahead of the lattice `|P| = 4` (34) and the composite (36). Neither
composite may take slot 1 over an exact `|P| ≤ 2` program (G6′), which the sort key already enforces.

## C. Final consolidated guidance (paste-ready)

### C.i Guards that matter for the next build

| id | guard | current value |
|---|---|---|
| G2 | code length in bits: `L = 4·cost + Σ_{j>2} e_j`, `e_j = log₂K_f + ℓ(a_j) + 2` for memorised tables (1.7 units literal, 1.3 role; colour map 2.125 per non-identity entry beyond the first); tables read from the input cost 0 | V29: colour maps, topology tables done; `recolour-by-*`, `recolour-objects`, objmap tables pending (A.1) |
| G6′ | slot 1: `\|P\| ≤ 2` (34/34, CP-lower 0.916); slot 2: `\|P\| ≤ 3` (20/25); `\|P\| ≥ 4` and near-miss only into empty slots | classes 0 `L ≤ 20`, 1 `≤ 34`, 2 `≤ 60`, 3 near-miss |
| G7′ | non-displaceable B0 attempts: lattice `\|P\| ≤ 2`, library exact fit `L ≤ 20`; displaceable: lattice `\|P\| ≥ 3`, compose, search2, near-miss | V29 sort key |
| G5 | chance-fit margin `margin' ≥ 4` bits for slot 1 (per segmentation) | not implemented; class/bits ordering stands in until W1 |
| D5 | near-miss: empty slots only, `source = nearmiss`, excluded from `occupied` and precision tables, ω = FAIL | pending |
| G18 | one release per cycle: `(b, c, n_changed)` on N2-gate via `compare_gate`; no gate counts in `summary.json`; half B and sealed untouched until Oct 12; `L_looks ≤ 12`; secret hid salt | tools: two gaps (A.2) |
| G21 | determinism: no wall-clock in decisions or in local evaluation counts; `PYTHONHASHSEED=0`; sorted iteration | `timeout: 25` still wall-clock (A.2) |
| G22 | Dream only on a Wake failure record (`FAIL`/`WRONG`; a near-miss fill is `FAIL`) | manual Dream; enforce by listing open tasks from the full job |
| G25 | retries per task `≤ 2`, quarantine, `≤ 10` abductions per cycle, streak cap 5 | manual ledger of retries per task id (design ids only) |
| G30 | grounding gate: (a) IRI/definition cited, (b) parameters from declared finite domains, no layout constants, (b′) `φ ≤ 0.5`, (c) test-blind + one harness check per version, (d) no design loss, (e) failure-triggered, (f) `E(test) ≥ 10` bits or a second task; **warning** `φ < 0.01` = program, not concept | in force since 22:15 EDT; 13 early families `test_seen` |
| G10/E10 | G scan `Θ(#families)`: measure `candidates()` seconds per task; cap at 300 families or gate by seeds | measure on the next parity |
| G14/E9 | notebook payload ≤ 1 MB compressed (1.43 MB refused); larger frozen data ships as an attached dataset | test the dataset route once before Nov 1 |
| G27–G29 | Kaggle: `κ = max(1.5, measured)`, `N_K` and outputs from the v15 log; per-task local ≤ 147.5 s; rounds commit atomically (R1 per-task alarm → placeholder) | `κ`, `N_K` unmeasured |

### C.ii The loop as it will run to Oct 12

- **Wake front-runs.** Every build is a full job on design + N2-gate (WSL, 1.5 h). Open tasks = design tasks with
  ω ∈ {FAIL, WRONG} (near-miss fills count as FAIL); each carries its signal: changed cells, families whose
  precondition fired, near-miss programs, change signature `Σ(t)`.
- **Dream on failures only.** Per cycle ≤ 10 abductions, ordered by signature-group size, WRONG before NO_FIT before
  NO_SEED; one proposal per group; retries ≤ 2 per task, then quarantine (listed, not retried).
- **Test-blind.** Viewer hides test outputs; one harness check per concept version; a revision is a new version and a
  new admission; `E(test) ≥ 10` bits or a second solved task.
- **Admission = batch per cycle.** No design task lost, no new WRONG (staged re-run), then one `compare_gate` release:
  admit iff `b = 0`; `c` and `n_changed` go to the ledger. Half B, N2-decide and sealed are not computed.
- **Ship.** The daily Kaggle slot carries the last admitted build; the public score is the only hidden look and is
  never used to choose between builds.
- **Monitors per cycle:** `f_c` (open fraction), productive steps, `|Q_c|`, `(b, c, n_changed)`, `φ(C)` per new
  concept, parity max seconds, `candidates()` seconds.

### C.iii What abduction should produce

- An **A-box predicate, role or relation** with a recogniser on the object lattice, entering a task only under the
  seed rule (its extension covers the changed cells in every training pair): `cell_role`, `nesting_depth`,
  `innermost`, `nearest_object_colour`, `in_line_of_sight`, `touches(colour)`, `panel_of`, `target_of_pointers`,
  `supported`, `enclosed_by_one` (cavity), `is_square`.
- **Criteria:** definition from the source domain, cited; parameters from a declared finite domain (colour roles,
  directions, `k ∈ 1..3`), never grid positions, separator columns, slot layouts, strides or sizes; fire ratio
  `φ ∈ [0.01, 0.5]` on design grids; actions colour-free where possible (own / bg / literal); no memorised tables
  (or charged as in G2).
- **Whole-grid families with a rigid parse** (turtle, drape, rainbow, dashed border, mirror panels, crosshair) are
  programs: keep them in G, do not count them as concepts, decompose when a decomposition exists (rainbow = spectrum ∘
  period-extend ∘ rings; panel-dye = fill-panel-by-marker ∘ colour-map; fronts-meet-halfway = axis Voronoi).
- **Fix the two G30(b) violations:** turtle (separator column 7, slot columns, memorised strokes → derive strokes
  from glyph geometry), bridge (stride 2 → induced).
- **Yield to expect:** at the current level `≈ 0.02` held-out solves per concept; the level shift (roles into the
  lattice, L4) is the only lever that scales.

### C.iv Oct 12 decision rule and honest expectation

- Decision set: N2-decide (51) ∪ half B (49) ∪ sealed (21) = 121 tasks, B0 ≈ 20 exact. **One look**, paired
  against B0: `(b, c)` from the private records. Transfer claimed iff `c ≥ c_min(b, α = 0.025)`:
  `b = 0 → 6`, `1 → 8`, `2 → 10`, `3 → 12` (plus `⌈A⌉` if any gated cycle touched a decision task; `A = 0` under
  C.ii).
- Candidate = last build with `b = 0` on N2-gate and the highest `c`, parity-verified.
- Expectation: MDL slot fixes (V23–V29) `c ≈ 1–3`; abductions `≈ +0.3`; `P(claim) < 5 %`. Report the outcome as
  "directional evidence, no significant transfer" unless the threshold is met; no wording stronger than the count
  allows. The Kaggle daily score (v11: 2.50) remains the hidden-set measurement.

### C.v Open risks

- Local evaluation still uses a 25 s wall-clock timeout: cross-machine counts differ; T1 not passable yet.
- `hid` is reversible with the public salt; per-job gate counts in `summary.json` are unledgered looks.
- V23/V29 gains (21/22, 47) are in-sample; only `(b, c)` on N2-gate is evidence, and it is not yet released.
- `search2` short-circuits `compose_fallback` (B); pending table charges (A.1) leave `recolour-by-*` tables at cost 3.
- 13 shipped families are `test_seen`; harmless on Kaggle (0 held-out fires), excluded from evidence.
- G scan time grows with the library (`Θ(#families)`); unmeasured; W1 locality untested (T13 not run).
- `κ`, `N_K` unmeasured; notebook payload limit ≈ 1 MB; the round scheduler (G27) is not built — the current
  notebook relies on the per-task alarm.
- Abduction throughput and yield (B.2 of v2): the Oct 12 threshold is out of reach by 20–50× at the current level.

## D. JSON summary of changes vs v2

```json
{"guards":[
 {"id":"G2","rule":"bits = 4*cost + table entries; composite count n_nodes = 1 + (1 + count(' ; ')) + count('+')","params":{"literal_units":1.7,"role_units":1.3,"cmap_units":2.125,"allowance_units":2.6},"metric":"tables charged in recolour-by-*, recolour-objects, objmap","threshold":"any flat-cost table family","action":"apply A.1 patches","status":"changed"},
 {"id":"G7","rule":"G7' + search2 composites displaceable; compose_fallback always runs with search2 when no single-step program; ties compose < search2","params":{},"metric":"60b61512 attempt 1 = objmap program","threshold":"lost","action":"apply B rule","status":"changed"},
 {"id":"G18","rule":"no gate counts in summary.json; single release per cycle via compare_gate; secret hid salt; ledger rows carry salt and cycle","params":{"L_looks":12},"metric":"unledgered looks","threshold":">0","action":"strip summary fields","status":"changed"},
 {"id":"G21","rule":"local evaluation timeouts by work counters; timed-out tasks excluded from both sides of a comparison","params":{},"metric":"cross-machine exact-count equality","threshold":"any mismatch","action":"fail T1","status":"changed"},
 {"id":"D5","rule":"near-miss labelled source=nearmiss; excluded from occupied and precision; omega=FAIL","params":{},"metric":"near-miss rows in tables","threshold":">0","action":"fix labels","status":"unchanged (pending)"}
],
"decisions":[
 {"id":"D10","choice":"keep the V24 test-refusal rule; fix stage ordering so search2 and compose_fallback both run and rank by bits","rationale":"the regression on 60b61512 is ordering, not the rule"},
 {"id":"D11","choice":"topology allowance = sum(e_j) - 2.6 rather than the first two entries in repr order","rationale":"deterministic but arbitrary charge otherwise"},
 {"id":"D12","choice":"Oct 12 candidate = last admitted build (b=0, highest c); outcome reported as directional unless c >= c_min(b, 0.025)","rationale":"v2 B.2 arithmetic"}
],
"tests":[
 {"id":"T19","description":"60b61512 under the B rule","pass_criterion":"attempt 1 = objmap program; the 21/22 and 47 checks unchanged"},
 {"id":"T20","description":"table charge on recolour-by-*, recolour-objects, objmap tables","pass_criterion":"no design task lost; flips listed with bits before/after"},
 {"id":"T21","description":"summary.json contains no N2-gate counts; compare_gate is the only release; ledger rows carry salt and cycle","pass_criterion":"grep clean; one ledger row per cycle"},
 {"id":"T22","description":"hid salt secret","pass_criterion":"record cannot be regenerated from repo contents alone"}
]}
```
