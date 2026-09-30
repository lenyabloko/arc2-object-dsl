# Bounds and guards for abductive meta-learning (answers to Q1–Q6)

Companion to `meta_learning_problem_statement.md` (2026-09-29). Every guard below is stated as an inequality
the Wake or Dream code can check with integers and counters; no wall-clock quantity enters any Wake decision.

Conventions used throughout (they fix ambiguities in the statement; see Contradictions C8, C10):

- `|P|` counts **all** nodes of the RDR tree, root included. "Rules" = `|P| − 1`. The lattice data
  "1–2 rules" therefore means `|P| ≤ 3`; "3 rules" means `|P| = 4`; "5 rules" means `|P| = 6`.
- `n_t` = training pairs, `q_t = |Q_t|` = test inputs, `N_i` = number of individuals of grid `x_i` under the
  segmentation the program uses, `Δ_i ⊆ I(x_i)` = individuals whose cells differ between `x_i` and `y_i`
  (for generation tasks, the individuals of `y_i` absent from `x_i`), `d_i = |Δ_i|`.
- All code lengths are integers in **millibits** (`⌈1000·ℓ⌉`), so `argmin L` is platform-independent.
- `s_max` = seed cap, `m` = out-degree cap, `k_max` = radius cap, `p_max` = node cap (root included),
  `h_max` = depth cap, `a_eff` = admissible (concept, action) pairs per concept after the residual determines
  the action, `w` = beam width, `V_max` = grounded candidates per radius.

---

## Summary of guards

| # | Guard | Inequality / parameter | Recommended value (assumption) | Monitored metric | Threshold | Action when crossed |
|---|---|---|---|---|---|---|
| G1 | Ring code for concepts (Q1) | `ℓ_t(C) = (k_C+1) + log₂ s_max + k_C·log₂ m`, `k_C ≤ k_max`; Kraft sum ≤ 1 | `s_max = 4`, `m = 8` → `ℓ = 3, 7, 11` bits at `k = 0, 1, 2` (A-Wake) | none needed (fixed code) | — | — |
| G2 | Program code is prefix-free (Q1, Q2) | `L(P) = 2(\|P\|−1) + ℓ(a_root) + Σ_ν [ℓ_t(C_ν) + ℓ(a_ν) + L(θ_ν)]`; ordered-tree shape 2 bits/node; every parameter charged `log₂\|domain\|` | as stated | unit test: two distinct programs never share a code word | 0 collisions | fix encoder before any MDL comparison |
| G3 | Pre-existence of a concept (Q1) — **changed by Q7:** the firing-count clause is Option A only; under Option B (recommended, Q7.5) it is a monitor and the gate is G30 | `C ∈ 𝒦` with snapshot stats **and** `r_C` fires on ≥ `g_min` design tasks other than its source **and** fires on ≤ 50 % of design grids | `g_min = 3` (A-design) | tasks-fired-other-than-source `g(C)` | `g(C) < 3` | Option A: do not admit to `G⁺`; Option B: report only |
| G4 | Grounding pays for itself (Q1, C2) — **changed by Q7:** Option A gate; under Option B a monitor (no charge on the ontology) | `Σ_t [L_old(P_t) − L_new(P_t)] > L(def r_C) + 1`, with savings on ≥ 2 tasks incl. one not the source | `L(def) = 8·bytes(source)` bits (A-code) | corpus saving `ΔL_corpus(C)` | `≤ 0` | Option A: reject grounding; Option B: report, and raise the Q7 alarm if `ζ` (G26) also fails |
| G5 | Chance-fit margin (Q2) | accept `P` iff `E_P(D_t) − log₂\|H_≤(P)\| ≥ μ`, where `E_P = Σ_i [log₂ C(N_i, d_i) + d_i·log₂ a_i]` and `H_≤(P)` = enumerated programs with `L ≤ L(P)` (`\|H_≤\| ≤ 2^{L(P)}` by Kraft) | `μ₁ = 3` bits for slot 1 (`P(chance) ≤ 1/8`), `μ₂ = 0` for slot 2 (A-null, A-ind) | precision on design vs margin bucket | precision(`μ ≥ 3`) `< 0.85` | raise `μ₁` by 1 bit; re-calibrate |
| G6 | Node / depth caps (Q2) | slot 1: `\|P\| ≤ 3`, `h ≤ 2`; slot 2 or no B0 fit: `\|P\| ≤ 4`, `h ≤ 3`; never `\|P\| ≥ 6` | from lattice data: `\|P\| ≤ 3`: 34/34 (CP-lower 0.916); `\|P\| = 4`: 0.80 [0.61, 0.91]; `\|P\| = 6`: 0.36 [0.23, 0.51] | precision by `\|P\|` on design (Wilson 95 %) | lower bound `< 0.90` for slot-1 class | demote that class to slot 2 |
| G7 | Slot ordering / no regression (Q2, R6) | slot 1 = candidate with highest Wilson-lower precision class; B0 fit ≈ 0.90 on N2 (37/41) | classes: prior `\|P\| ≤ 3, μ ≥ 3` (0.92) > B0 fit (0.90 held-out, 0.69 design) > prior `\|P\| = 4` (0.80) | design tasks solved only by B0 slot 2 (`s₂`) | `s₂ > 2` | keep B0 slot 2 fixed, prior program gets slot 1 only |
| G8 | Wake work budget (Q4) | `W_eval ≤ 2·10⁵` evaluations, `W_rec ≤ 1000` recogniser calls, `W_gen ≤ 2000` generator calls per task; each call has a static step cap | worst case ≈ 45 s local (typ. 15 s), budget 100 s local, `κ = 1.5` Kaggle/local (A-κ), B0 ≤ 60.5 s → ≤ 241 s < 300 s | measured max wall time per task on parity run | `> 100 s` local | halve `V_max`; never raise the alarm |
| G9 | Neighbourhood caps (Q4) | `\|N_k\| ≤ s_max·Σ_{j≤k} m^j`; `V_k = \|N_k ∩ G⁺\| ≤ V_max` | `s_max = 4, m = 8, k_max = 2, V_max = 96` → `\|N_2\| ≤ 288` | nodes visited per task | `> 288` | bug: Wake touched `O` outside the neighbourhood |
| G10 | Independence of `\|O\|` (Q4) | Wake accesses only stored capped adjacency lists of visited nodes + root recogniser set `ρ₀` | `ρ₀ ≤ 64` roots, subsumption-pruned descent (needs monotone recognisers) | count of `O` accesses per task | `> ρ₀ + \|N_{k_max}\|` | bug; fail the parity gate |
| G11 | Mining budget per abduction (Q3) | `\|N_d(C*)\| ≤ Σ_{i≤d} (f·\|Rel\|)^i =: M` | `d = 2, f = 5, \|Rel\| = 6` → `M ≤ 930` | nodes added per abduction | `> 930` | bug in miner |
| G12 | Hub exclusion (Q3) | never expand through `v` with `indeg_Rel(v) > δ_hub` or subclass-depth ≤ 3 below `entity` | `δ_hub = 500` (A-𝒦; measure the degree quantile, target top 0.5 %) | fraction of mined nodes reached only via hubs | `> 5 %` | lower `δ_hub` |
| G13 | Merge policy (Q3) | node identity = canonical Wikidata QID; DBpedia/ConceptNet only via mapping; strings never identify | — | audited duplicate rate (label sim ≥ 0.9, no link) | `> 2 %` | run merge pass; block admission until `< 2 %` |
| G14 | Frozen ontology = `k_max`-closure of `G⁺` (Q3) | `\|O_frozen\| ≤ \|G⁺\|·Σ_{j≤k_max} m^j` | `= 73·\|G⁺\|`; with `\|G⁺\| ≤ 300`: ≤ 21 900 nodes; ≈ 17 KB per grounded concept (73 × 200 B graph + 2 KB code) → ≈ 5 MB ≪ `B = 64` MB | `\|O_frozen\|` per cycle | growth `> 73·(new groundings)` | pruning is not applied; fix before freezing |
| G15 | Saturation / stopping (Q3) | new-node fraction `r_w = (\|S_n\| − \|S_{n−w}\|)/(w·M) < ε` and Chao2 completeness `S_obs/Ŝ ≥ 0.9` | `w = 10, ε = 0.10` | `r_w`, `Ŝ = S_obs + ((n−1)/n)·Q₁²/(2Q₂)` | both hold in 2 consecutive cycles | freeze graph mining; ground on demand only |
| G16 | Per-cycle Dream cap (Q3) | ≤ `a_max` abductions, ≤ `g_max` new groundings per cycle | `a_max = 10, g_max = 10` | counts | exceeded | defer to next cycle |
| G17 | Transfer decision (Q5) | exact McNemar on discordant counts `(b, c)`: reject H0 iff `P[Bin(b+c, ½) ≥ c] ≤ α` | `α = 0.05`, `b = 0 → c ≥ 5`; `b = 1 → c ≥ 7`; `b = 2 → c ≥ 9`; `b = 3 → c ≥ 10` | `(b, c)` on the decision set, one look on Oct 12 | as left | if not met: "directional evidence only", no transfer claim |
| G18 | Look budget (Q5) | decision sets looked at ≤ 1 time before Oct 12 and ≤ 1 before Nov 1; gating on N2-gate half only; per-cycle release = `(b, c, n_changed)` | split N2 by `hash(task_id) mod 2` | `L_looks` per split; winner's-curse allowance `0.8·Σ_c √(n_changed(c)·p̂(1−p̂))` | allowance `≥ 2` tasks | raise threshold `c ≥ 5 + allowance` |
| G19 | RBox regularity (Q6) | every chain axiom has one of the OWL 2 shapes (R∘R⊑R; S∘R₁…Rₙ⊑S; R₁…Rₙ∘S⊑S; R₁…Rₙ⊑S with all Rᵢ ≺ S); `≺` acyclic; RHS roles non-simple | `\|ℛ_chains\| ≤ 10`, hand-curated; mined "mechanisms" stored as `C ⊑ ∃R.D` (T-box, OWL 2 EL) | regularity check per admission (`O(\|ℛ\|)`) | any violation | reject axiom |
| G20 | Recogniser/T-box conformance (Q6) | for admitted `C ⊑ D` with both grounded: `r_C(g) ⊆ r_D(g)` on every design grid | violation rate 0 | violations per axiom | `> 0` | mark axiom defeasible (graph-only edge, no pruning through it) |
| G21 | Determinism discipline (R1) | integer costs; canonical iteration order `(L, k, IRI)`; no hash-order iteration; no wall-clock reads; deterministic abort on counters | `PYTHONHASHSEED=0` plus explicit sorts | cross-machine prediction-hash equality | any mismatch | fail parity gate |
| G22 | Front-running trigger (Q7.2) | Dream step for `t` only if `ω(t) ∈ {FAIL, WRONG}` (FIT only with spare budget); Wake always runs first on frozen `O_n` | trigger priority WRONG > NO_FIT > NO_SEED > GEN > FIT; `a_c = min(a_max, #distinct signatures)` | Dream steps without a Wake failure record | `> 0` | reject the step (no signal, no Dream) |
| G23 | Signal-bounded mining (Q7.2) | mine `N_d(C*) ∩ N_{d+d_link}(S_0 ∪ F)`; proposal `C*` within `d_link` hops of `S_0 ∪ F` unless `φ = NO_SEED` | `d_link = 2`; nodes per step `≤ min(M, \|N_4(S_0 ∪ F)\|)` | nodes mined outside the ball | `> 0` | bug in miner |
| G24 | Residual-directed grounding contract (Q7.2) | admitted `r_{C*}` must make `P' = NM ⊕ (C*, a)` or a new `\|P'\| ≤ 3` program exact on train **and** pass the test-blind test check; else discarded | `β = 3` near-misses in the signal | contract failures per cycle | `> 50 %` of steps | halve `a_c` (G25) |
| G25 | Retry cap, quarantine, streak cap (Q7.3) | `retries(s) ≤ ρ_max` per failure signature `s`; consecutive unproductive steps per cycle `≤ u_max` | `ρ_max = 2`, `u_max = 5` | quarantine size `\|Q_c\|`, unproductive fraction `1 − p_c` | `1 − p_c > 0.8` | Dream halts for the cycle; only regrouping continues |
| G26 | Convergence potential (Q7.3) | `Φ_n = \|G⁺_n\| + (g_step/ε)·F_n` non-increasing; design failure rate `f_c` non-increasing | `g_step ≤ 2`; alarm when solves-per-grounding `ζ < 1.2` over 20 groundings | `f_c`, `ζ_c` (design), `ζ^{N2}_c` (N2-gate) | `f_c` flat over 3 cycles with ≥ 10 steps, or `ζ < 1.2` | freeze mining; tighten G30 (b); review last 20 groundings for task constants |
| G27 | Offline round schedule (Q7.4) | rounds with static work budgets, commit per round, wall-clock read only at round boundaries; `Σ_r U_r ≤ U_K = T_K(1−s)/(κ·c_unit)` | `s = 0.25`, `κ = 1.5`, `c_unit = 100 µs` → `U_K = 2.16·10⁸` units (12 h) | planned vs actual units per round (logged) | actual `> 1.25×` planned at a boundary | skip all later rounds; emit last committed round; log round count |
| G28 | Per-task total work cap (Q7.4) | `B0 + Σ_r W_r(t) ≤ 150 s` local-equivalent | `60.5 + 10 + 45 + 35 = 150.5 s ≤ 300/κ_max`, `κ_max = 2` | max per-task local time on parity | `> 150 s` | cut `W_3` first, then `W_2` |
| G29 | Work-unit calibration (Q7.4) | `c_unit` per counter type from the parity run; `κ` from the Kaggle log of the same notebook | recalibrate when `c_unit` drifts `> 20 %`; `κ = max(1.5, measured)` | ratio Kaggle/local on the public 120 | `> 1.5` | raise `κ`, rebuild the round plan (units unchanged, rounds fewer) |
| G30 | Option B grounding gate (Q7.5; replaces G3/G4 as gates) | (a) IRI in 𝒦 + source-domain definition cited; (b) recogniser parameters from a declared finite domain, no task constants; (c) test-blind grounding + within-task test check exact; (d) no design losses; (e) front-running (G22) | chance pass of (c) `≤ 2^{−E(test)}` ≈ 0.4 % at `E = 8` bits | false-admission estimate `Σ 2^{−E(test)}` per cycle; `b` on N2-gate | `b > 0` or estimate `> 1` | retire the offending concept; raise required `E(test)` to 10 bits |

Assumption labels (A-Wake, A-design, A-code, A-null, A-ind, A-κ, A-𝒦, A-T_K, A-N_K) are defined in the last section.

---

## Q1. The prior π

### Q1.1 Statement

Concept space 𝒞 = all IRIs of 𝒦 (unbounded in principle: Wikidata alone > 10⁸ items) plus invented concepts.
Required: a code `ℓ` on 𝒞 with Kraft sum `Σ_C 2^{−ℓ(C)} ≤ 1` (so `π(C) = 2^{−ℓ(C)}` is a sub-prior), computable in
Wake from the frozen `O` only, deterministic, invariant under growth of `O` (no MDL drift), and such that
"invent a concept for this task" is never cheaper than writing the conjunction it names.

### Q1.2 Construction

Two codes, used in two places.

**(a) Wake ring code (task-conditional, used in `L(P)`).** Let `S_0(t)` be the seed set (capped at `s_max` by
the seed ranking of Q4) and let `k_C ∈ {0, …, k_max}` be the capped-BFS distance of `C` from `S_0(t)` in the
frozen graph. Define

```
ℓ_t(C) = (k_C + 1) + log₂ s_max + k_C · log₂ m          (C ∈ N_{k_max}(t))
ℓ_t(C) = ∞                                              (otherwise: not usable by Wake)
```

With `s_max = 4`, `m = 8`: `ℓ_t = 3, 7, 11` bits at `k = 0, 1, 2` (all integers since `s_max`, `m` are powers of 2).

*Kraft.* Ring `k` has at most `s_max·m^k` members (BFS with out-degree cap `m`); the unary prefix `(k+1)` bits is a
prefix code on `k`. Hence `Σ_C 2^{−ℓ_t(C)} ≤ Σ_{k=0}^{k_max} 2^{−(k+1)} · (s_max m^k)·2^{−log₂(s_max m^k)} = Σ_k 2^{−(k+1)} < 1`.
It is a proper sub-prior for every task, over an unbounded 𝒞 (everything outside the neighbourhood has `π = 0`,
and the leftover mass `2^{−(k_max+1)}` is the escape code for "not in the neighbourhood").

*Invariance.* `ℓ_t(C)` depends only on `k_C`, `s_max`, `m`, never on `|O|` or on the actual ring size, so
`L(P)` of an existing program does not change when `O` grows unless `C`'s distance to the seeds changes (which is
a genuine change of evidence). Using the cap rather than the true ring size costs at most `log₂(s_max m^k / |R_k|)`
bits of slack per node and buys drift-freedom and integer arithmetic.

*Determinism and cost.* Rings are produced by BFS over the stored, pre-ranked adjacency lists (top-`m` by the
Dream statistic, ties by IRI). Cost `O(|N_{k_max}|)` per task, independent of `|O|` (G9, G10).

**(b) Dream base code (global, used for ranking adjacency and for the corpus-level MDL of groundings).**
Let `s(C)` be a snapshot statistic taken at admission (recommended: number of design tasks on which `r_C` fires,
then in-degree of `C` in 𝒦 over `Rel`, then IRI, lexicographic). Let `rank(C)` be the position of `C` in the
snapshot order (unique). Elias-γ:

```
ℓ_0(C) = 2·⌊log₂ rank(C)⌋ + 1        Σ_{r≥1} 2^{−ℓ_0(r)} = Σ_j 2^j · 2^{−2j−1} = 1
```

Proper over an unbounded rank space (universal code for the integers). Values: rank 1 → 1 bit, 10 → 7, 100 → 13,
1000 → 19, 10⁴ → 27. Snapshot `rank(C)` is stored in the node and never recomputed, so Dream's corpus MDL is stable.

**(c) Invented concepts.** A concept `C_new ∉ 𝒦` has no rank and no place in the ring; the only code for it is
its definition in the program code itself: `ℓ(C_new) = 1 + L(def C_new)` (1 escape bit). Hence for any program,

```
L(P with node C_new)  =  L(P with def C_new inlined) + 1  >  L(P with def inlined),
```

so within a task inventing a concept never lowers `L`. Across tasks (two-part corpus code
`L_corpus = Σ_{C ∈ G⁺} L(def r_C) + Σ_t L(P_t)`), an invented concept pays once and helps only if
`Σ_t [L_old(P_t) − L_new(P_t)] > L(def) + 1` (guard G4). A pre-existing concept pays `ℓ_0(C)` (a few bits)
because its definition is external knowledge; that asymmetry is the whole value of priors and is also the attack
surface: a recogniser with task-specific constants smuggles `L(def)` in for free. Guard G3 (IRI in 𝒦 + generality
`g_min = 3` other design tasks + fires on ≤ 50 % of grids) and a code-review rule (no task ids, no literal colours,
no grid-size constants in `r_C`) close it. The V22 loss of 5 tasks is this attack in the wild ("can move up" is a
low-level predicate that fires almost everywhere: it passes generality but fails the ≤ 50 % ceiling).

### Q1.3 Monitoring

- `g(C)` = other design tasks where `r_C` fires; threshold `< 3` → graph-only (G3).
- Fire ratio `φ(C)` = fraction of design grids where `r_C ≠ ∅`; threshold `> 0.5` → graph-only (G3).
- `ΔL_corpus(C)` from G4; threshold `≤ 0` → reject grounding.

---

## Q2. Occam guard for Wake

### Q2.1 Why the distribution-free bound is vacuous at ARC sample sizes (state it, then replace it)

Occam bound with a prefix code (Blumer–Ehrenfeucht–Haussler–Warmuth 1987; Blum–Langford 2003 PAC-MDL): for pairs
i.i.d. from the task distribution, for any `ℓ`,

```
P[ ∃P : L(P) ≤ ℓ, P ⊨ D_t, err(P) > ε ]  ≤  2^ℓ (1 − ε)^{n_t}.
```

With `n_t = 3` and even a one-concept program (`L ≈ 12` bits, see Q2.4) the right-hand side is `4096·(1−ε)³ > 1`
for every `ε < 0.94`. **No pair-level bound supports any node cap at `n_t ≤ 5`.** R7 as stated ("right on the
test with high probability", distribution-free) cannot be met; the guarantee has to come from (i) a within-pair
evidence count under an explicit null and (ii) empirical calibration.

### Q2.2 Chance-fit theorem (the implementable guard)

*Definitions.* For program `P` with segmentation `σ_P`, `N_i = |I_{σ_P}(x_i)|`, `d_i = |Δ_i|`, and `a_i` = number of
admissible actions for a changed individual of pair `i` (colours: 9; move: `|δ-set|`; draw: `10` per drawn cell
divided by dependence factor `ρ`, see A-ind). Evidence:

```
E_P(D_t) = Σ_{i=1}^{n_t} [ log₂ C(N_i, d_i) + d_i · log₂ a_i ]        (bits)
```

*A-null.* If `P` is unrelated to the task, its change set on `x_i` is a uniformly random `d_i`-subset of the
`N_i` individuals with uniformly random admissible actions, independently across pairs. Then
`P_null[P ⊨ D_t] = Π_i 1/(C(N_i,d_i) a_i^{d_i}) = 2^{−E_P(D_t)}`.

*Theorem.* For any prefix code `L` (Kraft) and any `μ ≥ 0`,

```
P_null[ ∃P : P ⊨ D_t  and  L(P) ≤ E_P(D_t) − μ ]  ≤  Σ_P 2^{−E_P} · 1[E_P ≥ L(P)+μ]  ≤  Σ_P 2^{−L(P)−μ}  ≤  2^{−μ}.
```

The bound is independent of `|H_k|`; only the margin matters. `μ = 3` → chance-fit probability ≤ 1/8;
`μ = 4.32` → ≤ 5 %. It does **not** bound the error of a program that is related-but-wrong (misspecified DSL);
that residual is what the calibration in Q2.3 measures.

*Counted variant (tighter, same proof).* Let `H_≤(P) = {P' enumerated : L(P') ≤ L(P)}` and
`E_min = min_{P' ∈ H_≤(P)} E_{P'}(D_t)`. A plain union bound gives
`P_null[∃P' ∈ H_≤(P) : P' ⊨ D_t] ≤ |H_≤(P)| · 2^{−E_min}`, and `|H_≤(P)| ≤ 2^{L(P)}` by Kraft, so
`margin' := E_min − log₂|H_≤(P)| ≥ E_P − L(P)`. The enumeration is deterministic, so `|H_≤(P)|` is an exact
integer available for free. The code of G1–G2 is deliberately slack (unary prefixes, capped ring sizes), so
`margin'` is often several bits larger than `margin`; use `margin'` in the guard and `margin` for design-time
reasoning.

*Guard G5.* Slot 1 requires `margin' ≥ μ₁ = 3`; slot 2 requires `margin' ≥ μ₂ = 0`. Programs failing `μ₂` are not
proposed at all (they are, by the theorem, indistinguishable from chance).

*Worked evidence values* (objects as individuals, colour actions): 3 pairs, 10 objects, 1 changed: `E = 19.5`;
3 pairs, 10 objects, 3 changed: `49.2`; 2 pairs, 6 objects, 1 changed: `11.5`; 3 pairs, 20 objects, 6 changed:
`102.8`; 5 pairs, 12 objects, 2 changed: `61.9`.

### Q2.3 Caps from the empirical table (Wilson / Clopper–Pearson, 95 %)

| `\|P\|` (rules) | correct / fitted | precision | 95 % interval |
|---|---|---|---|
| ≤ 3 (1–2) | 34 / 34 | 1.00 | lower bound 0.916 (Clopper–Pearson one-sided); rule of three: error ≤ 0.088 |
| 4 (3) | 20 / 25 | 0.80 | [0.61, 0.91] |
| 5 (4) | 14 / 17 | 0.82 | [0.59, 0.94] |
| 6 (5) | 15 / 42 | 0.36 | [0.23, 0.51] |

B0 reference precision among fits: design 70/101 = 0.69 [0.60, 0.78]; held-out N2 37/41 = 0.90 [0.78, 0.96].

Decision rule (G6, G7): a candidate may take slot 1 only if the lower confidence bound of its class is ≥ the class
it would displace. `|P| ≤ 3` (lower 0.916) beats B0 on held-out (0.90 point, 0.78 lower) → prior programs with
`|P| ≤ 3` and margin ≥ 3 take slot 1. `|P| = 4, 5` (lower 0.59–0.61) do not beat B0 → slot 2, or slot 1 only when B0
has no fit. `|P| = 6` (upper 0.51) is below B0's lower bound → never proposed. So **depth 2 / 3 nodes is right for
slot 1; 4 nodes for slot 2; ≥ 6 never.** `h_max = 2` for `|P| ≤ 3` is automatic; `h_max = 3` for `|P| = 4`
(chain of two exceptions) is allowed because the cost is charged per node.

### Q2.4 `p_max`, `h_max`, `k_max` as functions of `n_t`, grid size, π

Per-node cost under G1–G2 (concept at ring `k`, simple action, 2 shape bits):
`b(k) ≈ 2 + ℓ_t(k) + ℓ(a) ≈ 2 + (4k+3) + 2.3…5.6`, i.e. `b ≈ 8–11` bits at `k = 0`, `12–15` at `k = 1`,
`16–19` at `k = 2`. Typical programs: 1 concept ≈ 12 bits, +1 exception ≈ 23, 3 rules ≈ 38, 4 rules ≈ 58, 5 rules ≈ 76.

Task-adaptive node cap from G5 (the only cap that depends on `n_t` and grid size):

```
p_max(t) = 1 + ⌊ (E(D_t) − μ₁ − ℓ(a_root)) / b_min ⌋,     b_min = 8 bits,
```

with `E(D_t)` growing linearly in `n_t` and in `Σ_i log₂ C(N_i, d_i)` (grid size enters only through the
individual count `N_i`, not through `H·W`, because cells inside an object are not independent evidence).
Examples (`ℓ(a_root) = 1`): `E = 19.5` → `p_max = 2` (root + one concept); `E = 49` → `6`, capped at 4 by G6;
`E = 11.5` (two sparse pairs) → `p_max = 1` under the code bound, i.e. only the counted variant of G5 can admit
a one-concept program there (`log₂|H_≤| = log₂(4 seeds × 10 colours) = 5.3 ≤ 11.5 − 3`). This is the honest
consequence of two pairs with one changed object each: the guarantee rests on the enumerated set being small.
Consistency check against the table: 4-rule programs (≈ 58 bits) exceed the evidence of most
tasks (20–60 bits) so their precision should collapse toward chance, and 5 rules (≈ 76) certainly do; observed
0.82 → 0.36 across `|P| = 5 → 6` is the predicted cliff. 3 rules (≈ 38 bits) sit inside the evidence range for
tasks with several changed objects and outside it for sparse tasks: observed 0.80, a mixture, as predicted.

`k_max`: each hop costs 4 bits under G1, so radius is self-limiting through G5 (`k ≤ (E − L_rest − μ)/4`), but the
compute bound of Q4, not the code, fixes `k_max = 2`. Exact `argmin_k`: continue to `k+1` only if
`L_best > L_lower(k+1) = ℓ(a_root) + 2 + ℓ_t(k+1) + min_a ℓ(a)`; otherwise stop (branch-and-bound makes the staged
search return the true minimum over `k ≤ k_max`).

### Q2.5 Monitoring

- Precision by (`|P|`, margin bucket `{<0, 0–3, 3–6, >6}`, source) on design, Wilson lower bound; recompute per
  cycle; threshold: any slot-1 class lower bound `< 0.90` → demote to slot 2 (G6/G7).
- Chance-fit audit: fraction of design programs with `E − L < 0` that are exact on test; expect ≈ chance; if
  `> 0.5`, `E` is under-counted (probably wrong `a_i` or segmentation) — fix `E`, do not lower `μ`.
- `s₂` = design tasks solved only by B0's second attempt; threshold `> 2` → keep B0's slot 2 (G7).

---

## Q3. Convergence of Dream

### Q3.1 Model

Store after `n` abductions: `S_n = ∪_{j≤n} N_d(C*_j)`, `N_d` = nodes within `d` hops via relations in `Rel`, fan-out
`≤ f` per relation per node, hubs not expanded. Per-abduction bound (G11):

```
|N_d(C*)| ≤ M := Σ_{i=1}^{d} (f·|Rel|)^i ;    d=2, f=5, |Rel|=6 → M ≤ 930 ;    d=3 → 27 930 ;    d=1, f=10 → 60.
```

Hence `|S_n| ≤ n·M` (linear, never bounded by itself). Boundedness needs one of:

- **(B1) finite reachable universe.** `𝒦_reach := ∪_{C ∈ 𝒫} N_d(C)` for the proposal universe 𝒫 (concepts a Dream
  step can name). With hub exclusion and `Rel` fixed, `|S_n| ≤ |𝒦_reach| < ∞` for all `n`. Without hub exclusion,
  `𝒦_reach` ≈ the whole class hierarchy (every class is ≤ 2 hops from a hub) — this is Codex's failure.
- **(B2) recurrence.** If proposals are exchangeable draws with `q_v := P(v ∈ N_d(C*))`, then
  `E[|S_{n+1}| − |S_n|] = Σ_v q_v (1−q_v)^n → 0` (species accumulation / coupon collector), and
  `|S_n| → Σ_v 1[q_v > 0] ≤ |𝒦_reach|`.

Under (B1)+(B2) the growth rate tends to 0 (R4) **for the store**. The frozen ontology has a stronger, unconditional
bound:

*Lemma (prune-invariance).* Let `O_frozen` be the subgraph induced by `V' = {v : dist(G⁺, v) ≤ k_max}` in the capped
graph (adjacency lists ranked and cut to `m` in the store, then restricted to `V'`, frontier lists truncated). Then
`Wake(t, O_frozen) = Wake(t, O_store)` for every task `t`.
*Proof.* Wake's BFS starts in `S_0(t) ⊆ G⁺`, expands at most `k_max` hops over the stored capped lists, and uses
only `G⁺ ∩ visited` in programs; every visited node is in `V'` and its list is byte-identical. Costs use the same
integer codes. ∎

Consequently `|O_frozen| ≤ |G⁺|·Σ_{j≤k_max} m^j = 73·|G⁺|` (`m = 8, k_max = 2`) (G14), so R4 for the frozen
ontology reduces to boundedness of `|G⁺|`, which is effort-bounded (`g_max = 10` groundings per cycle, G16) and
gated by G3/G4. Everything the store holds beyond `V'` is invisible to Wake; it can be kept for Dream (proposals,
ranking) without any R2/R3 consequence.

### Q3.2 Saturation estimator and stopping rule (G15)

Treat each abduction as a sampling unit and each node as a species; `Y_v` = number of abductions whose
neighbourhood contains `v`; `Q₁ = #{v: Y_v = 1}`, `Q₂ = #{v: Y_v = 2}`, `S_obs = |S_n|`.

```
Chao2 (incidence capture–recapture, lower bound under heterogeneity):
    Ŝ = S_obs + ((n−1)/n) · Q₁² / (2 Q₂)         (Q₂ > 0; else S_obs + ((n−1)/n)·Q₁(Q₁−1)/2)
Good–Turing unseen mass:  U ≈ Q₁ / Σ_v Y_v
Empirical new-node fraction over the last w abductions:  r_w = (|S_n| − |S_{n−w}|) / (w·M)
```

Stop graph mining (freeze the graph part, keep grounding) when `r_w < 0.10` with `w = 10` **and** `S_obs/Ŝ ≥ 0.9`
in two consecutive cycles. Because reviewer proposals sweep the largest uncovered groups first (not exchangeable),
Chao2 is a lower bound on the eventual size; the rule is therefore conservative in the right direction (it never
declares saturation early on account of heterogeneity). After freezing, mining is on-demand: a proposed `C*` absent
from the store triggers a single `N_d(C*)` mine; monitor the miss rate `r_miss` (proposals absent from the store);
`r_miss > 0.2` over a cycle means the freeze was premature → resume for one cycle.

### Q3.3 Codex's non-convergence mechanisms and the guard for each

| Mechanism | Why it diverges | Guard |
|---|---|---|
| Unbounded depth / transitive closure over `subClassOf`, `partOf` | closure of any class reaches `entity` and, downward, everything under it: `\|N_∞\| = \|𝒦\|` | `d ≤ 2` (G11); no closure at mine time; closures only through the ≤ 10 curated RBox chains, and only inside `V'` when materialising for Wake |
| Generic hubs (`entity`, `object`, `physical object`, `phenomenon`, `process`, `artificial entity`, `concept`) | one hop up then one hop down covers ~10⁵ classes | G12: never expand through `indeg > δ_hub = 500` or subclass-depth ≤ 3 from `entity`; hubs may be terminal nodes |
| Synonym duplicates (same thing, different string / source) | each restatement adds a node and a fresh neighbourhood | G13: canonical QID; DBpedia/ConceptNet only through explicit mappings; ConceptNet edges never mined into `O` (its `IsA` is not subsumption-consistent) |
| Ungrounded growth (graph-only nodes with no grounded node within `k_max`) | store grows, Wake cannot use it, R2/R3 pressure without any transfer | Lemma + G14: frozen `O = k_max`-closure of `G⁺`; store may be larger but is not shipped |
| Per-task groundings (renamed conjunctions) | `G⁺` grows with the number of tasks, so `O_frozen` grows without bound and precision does not | G3 (pre-existence + generality), G4 (corpus saving), G16 (`g_max`) |

### Q3.4 Monitoring

`r_w`, `S_obs/Ŝ`, `r_miss`, hub-reached fraction, duplicate rate, `|O_frozen|/|G⁺|` (must stay ≤ 73), `|G⁺|` growth
per cycle (≤ 10). Thresholds and actions in the summary table (G11–G16).

---

## Q4. Wake complexity

### Q4.1 Cost bound

Let `g_t = n_t + q_t ≤ 7` grids per task; `τ_r`, `τ_γ` the enforced step caps of recognisers and generators
(converted to time by A-τ); `c_eval(|I|)` the cost of scoring one candidate node against the residual on one grid
(set intersection over cached extensions, `≈ 100 µs` at `|I| ≤ 900`).

```
cost_W(t) ≤ seeds + Σ_{k=0}^{k_max} [ V_k · g_t · τ_r  +  E_k · n_t · c_eval  +  E_k^{draw} · n_t · τ_γ ] + render
seeds    ≤ ρ₀ · g_t · τ_r  +  (fired · m_sub) · g_t · τ_r          (hierarchical seeding, G10)
V_k      ≤ min(V_max, s_max · Σ_{j≤k} m^j)
E_k      ≤ V_k a_eff + 2 (V_k a_eff)²           (exhaustive, |P| ≤ 3)
         + w · (p_max − 3) · V_k a_eff            (beam, |P| = 4)
```

No term contains `|O|`, `|𝒯|` or `|ℛ|`: Wake reads `ρ₀` root recognisers, the capped adjacency lists of at most
`|N_{k_max}|` nodes, and the recogniser code of at most `V_max` concepts per radius. That is the formal content of
"independent of `|O|`" (G9, G10). The one hidden dependence in the statement — "seeds = {C ∈ G⁺ : …}" evaluated
over all of `G⁺` — is removed by hierarchical seeding: roots `ρ₀ ≤ 64`, and a child recogniser is evaluated only
where its parent fired. This needs recogniser monotonicity `C ⊑ D ⇒ r_C(g) ⊆ r_D(g)` (G20); where an axiom is
only defeasible, the child is attached to the root set instead.

### Q4.2 Numbers (A-Wake, A-τ)

`s_max = 4, m = 8, k_max = 2, V_max = 96, a_eff = 3, w = 4, p_max = 4, g_t = 7, τ_r = 10 ms, c_eval = 100 µs`:

| stage | count | time |
|---|---|---|
| root seeds | `64 × 7 × 10 ms` | 4.5 s |
| recognisers, `k ≤ 2` | `≤ 96 × 7 × 10 ms` per radius, ≤ 3 radii | ≤ 20 s (typ. 7 s) |
| exhaustive `\|P\| ≤ 3` at `k = 1` (`V_1 ≤ 32`) | `96 + 2·96² = 18 528` | 1.9 s |
| exhaustive `\|P\| ≤ 3` at `k = 2` (`V_2 ≤ 96`) | `288 + 2·288² = 166 176` | 16.6 s |
| beam `\|P\| = 4` | `4 × 1 × 288 = 1 152` | 0.1 s |
| total worst case | `W_eval ≈ 1.9·10⁵` | ≈ 45 s local (typ. ≈ 15 s) |

Budget: 100 s local for Wake; with `κ = 1.5` (A-κ) and B0 ≤ 60.5 s: `1.5·100 + 1.5·60.5 = 241 s < 300 s`. The alarm
must never fire (it is wall-clock and would break R1); the work counters `W_eval ≤ 2·10⁵`, `W_rec ≤ 1000`,
`W_gen ≤ 2000` are the real limits and abort deterministically to the B0 stack (G8). Total (A-T_K, A-N_K):
`240 × (15 + 14) s × 1.5 ≈ 2.9 h` typical, `240 × 241 s = 16 h` worst case, so `T_K = 12 h` is met only in
expectation; if the measured mean on parity exceeds `T_K/(κ·N_K) = 120 s` local, halve `V_max` (each halving
divides the dominant term by 4). With 4 worker processes (deterministic per task) the wall-clock sum divides by ≈ 3.5.

Why these values: `m = 8` because `|N_2| = 288` is the largest neighbourhood whose exhaustive 3-node search fits
the budget with a factor ≥ 2 to spare; `m = 10` gives `|N_2| = 440` and `2·440² ≈ 3.9·10⁵` evaluations (39 s,
too close); `k_max = 3` gives `|N_3| = 2336` (impossible exhaustively). `p_max = 4` because `|P| = 4` is the
last class with precision above chance (Q2.3) and its beam cost is negligible.

Full enumeration of `|P| = 4` at `k = 2` would be `5·(288·3)³ ≈ 3·10⁹` (impossible); therefore the `argmin_P L`
of Section 2 is exact only for `|P| ≤ 3` and beam-approximate for `|P| = 4`. Since `|P| = 4` programs never take
slot 1 (G6), the exactness of slot 1 is preserved.

### Q4.3 Monitoring

Per-task counters `(W_eval, W_rec, W_gen, nodes_visited, O_accesses)` written to the parity log; thresholds in G8–G10;
max local wall time on the public-eval parity run `> 100 s` → halve `V_max`; any cross-machine prediction-hash
mismatch → fail parity (G21).

---

## Q5. Transfer test

### Q5.1 Definitions

For a split `V` and cycle `c`, with `Sol_c(t)` = Wake's exact solve of `t` within 2 attempts and
`Prior_c(t)` = "the solving program's nodes are all in `G⁺` and none was grounded in a Dream step triggered by `t`":

```
exact_c(V)  = |{t ∈ V : Sol_c(t)}|
reuse_c(V)  = |{t ∈ V : Sol_c(t) ∧ Prior_c(t)}| / |V|           (reuse rate; R5 demands it rises in c)
```

On held-out splits `Prior_c(t)` holds by construction (no design ever touched `t`), so `reuse_c(V) = exact_c(V)/|V|`
restricted to prior programs (B0-stack solves excluded). On the design set `Prior_c(t)` is the leave-one-source-out
condition and is observable at full resolution with no leakage; it is the proxy to optimise between looks.

### Q5.2 Decision rule for Oct 12 (G17)

Paired comparison against B0 with discordant counts `b` (B0 right, new wrong) and `c` (new right, B0 wrong): under
H0 (no transfer) `c ~ Bin(b+c, ½)`; exact McNemar = sign test, one-sided. Minimal `c` at given `b`:

| `b` | α = 0.05 | α = 0.025 | α = 0.01 | α = 0.005 |
|---|---|---|---|---|
| 0 | 5 | 6 | 7 | 8 |
| 1 | 7 | 8 | 10 | 11 |
| 2 | 9 | 10 | 12 | 13 |
| 3 | 10 | 12 | 14 | 15 |

The threshold does not depend on `|V|`; power does: for `c ≥ 5, b = 0` at 80 % power the true per-task gain rate must
be ≈ 7 % on 101 tasks (≈ 7 tasks), ≈ 15 % on 49–51 tasks, and the 21 sealed tasks alone cannot reach it below 25 %.
So: **the minimal detectable improvement at α = 0.05 is +5 net exact solves with zero held-out regressions**
(N2: 37 → 42; half B: 1 → 6; pooled decision set 121 tasks: +5). With `b > 0` the requirement rises as tabulated.

Counts-only compatibility: `(b, c)` are two counts per split, not task identities; the notebook can emit them
without violating the protocol. `Δ = c − b` alone is insufficient (the same `Δ = 5` is significant at `b = 0` and
not at `b = 2`).

### Q5.3 Look budget (G18)

Every per-cycle look at a split used for admission ("no lower held-out count") is a selection step on that split;
under H0 the accepted count sequence is a random walk with rejected downward steps, giving an upward bias per cycle
≈ `E[Z | Z ≥ 0] ≈ 0.8·σ_c`, `σ_c = √(n_changed(c)·p̂(1−p̂))`, `n_changed(c)` = held-out tasks whose prediction
changed in cycle `c` (observable as a count). With `p̂ = 0.4` (N2) and `n_changed = 4`: `0.78` tasks per gated cycle;
10 gated cycles ≈ 8 tasks — larger than the +5 threshold. Half B has been gated ≈ 20 cycles and N2 ≈ 5; both are
partially spent.

Protocol from now on:

1. Split N2 by `hash(task_id) mod 2` into N2-gate (≈ 50) and N2-decide (≈ 51). Gate admissions on design + N2-gate
   only; per-cycle release `(b, c, n_changed)` on N2-gate.
2. Decision set = N2-decide ∪ half B ∪ sealed (121 tasks, B0 ≈ 20 exact). Looks: one on Oct 12, one on Nov 1.
   Oct 12 rule: transfer demonstrated iff `c ≥ c_min(b, 0.05)` from the table on the pooled decision set (with Bonferroni
   `α/2 = 0.025` if the Nov 1 look is also to count as a test).
3. If gating continues on a split later used for decision, add the allowance `A = 0.8·Σ_c σ_c` to the threshold:
   require `c ≥ c_min(b, α) + ⌈A⌉`. Report `A` with every decision.
4. Leakage accounting: each `(b, c, n_changed)` release ≤ `3·log₂(|V|+1) ≈ 17` bits; treat the design process as
   having ≤ `17·L_looks` bits of held-out information; do not exceed `L_looks = 12` on N2-gate before Oct 12.

Hidden Kaggle score: one look per day is fixed by the platform; it is the only look on the hidden set and is the
final arbiter; do not tune on the public leaderboard portion.

### Q5.4 Monitoring

`(b, c)` per gated cycle on N2-gate; `b > 0` blocks admission (R6 on held-out); `reuse_c(design, leave-one-source-out)`
must rise monotonically across admitted cycles, else the admitted concepts are not transferring even in-sample →
raise `g_min` to 4.

---

## Q6. Consistency

### Q6.1 T-box / RBox / A-box assignment

| Item in the statement | Correct layer | Note |
|---|---|---|
| concept name, `def(C)`, `ext(C)` | T-box | intensional; `ext` are annotations, not axioms |
| `r_C`, `γ_C` | procedural attachment to T-box concept | closed-world, total, bounded; **not** DL realisation |
| cells, components, regions, colour/size/adjacent/inside | A-box (per grid) | finite; realisation = evaluation, trivially decidable |
| "rainbow hasCause dispersion", "dispersion hasEffect spectrum", "drops hasShape bow" | **T-box GCIs `C ⊑ ∃R.D`**, not RBox | class-to-class links are existential axioms (OWL 2 EL); as written they are paths in `G`, not property-chain axioms |
| `R₁ ∘ … ∘ R_k ⊑ S` | RBox | Wikidata supplies only transitivity flags (P279, P361, …), i.e. `R∘R ⊑ R`; everything else is curated |
| RDR tree, first-match, exceptions | program layer | non-monotonic; outside OWL by design; the ontology proposes nodes, it does not define program semantics |
| `owl:sameAs` merge | individuals only | for classes use `owl:equivalentClass`; Wikidata items used as classes are punned — do the merge on QIDs (G13) |

### Q6.2 OWL 2 DL regularity and decidability

Regularity (OWL 2 Structural Specification §11, global restrictions): there is a strict partial order `≺` on roles
such that every chain axiom has one of the shapes `R∘R ⊑ R`, `R⁻ ⊑ R`, `S∘R₁…Rₙ ⊑ S`, `R₁…Rₙ∘S ⊑ S`,
`R₁…Rₙ ⊑ S` with each `Rᵢ ≺ S`; roles on the right of a chain are non-simple and may not appear in cardinality,
`Self`, or disjointness axioms. Check per admitted axiom in `O(|ℛ|)` by extending `≺` and testing acyclicity (G19).
With that, SROIQ realisation is decidable (N2ExpTime-complete) — irrelevant in Wake, which never runs a reasoner.
Recommendation: keep all mined axioms in **OWL 2 EL** (`C ⊑ D`, `C ⊑ ∃R.D`, `R∘S ⊑ T`, no inverses, no negation):
classification is polynomial (ELK) and can run in Dream on the whole store; materialise the subsumption closure
inside `V'` so Wake needs no inference. `hasCause`/`hasEffect` are stored as two roles, not as inverses.

Soundness of procedural realisation relative to the T-box (G20): for grounded `C ⊑ D`, `r_C(g) ⊆ r_D(g)` on every
design grid, else the axiom is a defeasible edge (kept for neighbourhood ranking, not used for pruning or
hierarchical seeding). This is where "outside knowledge" and "grid reading" can disagree, and the test is cheap.

### Q6.3 Requirements check

R1 holds iff G21 and the snapshot rule of Q1(b); R2 iff G8–G10 (Q4); R3 iff G14 (`B = 64 MB` is ≈ 13× the bound at `|G⁺| = 300`);
R4 iff G11–G16 (Q3); R5 measurable only under G18 (Q5); R6 iff G7 (slot ordering) plus `b = 0` gating; R7 is
unattainable as stated and is replaced by G5 + G6 (Q2). The contradictions below are the places where the
statement, taken literally, violates one of these.

---

## Contradictions and resolutions

**C1. R4 (bounded, saturating `O`) vs "grow far beyond what training uses" vs "ontology not charged".**
Unbounded, uncharged growth is exactly the Codex failure. Resolution: two stores. The Dream store may grow to
`|𝒦_reach|` (bounded by G11–G13); the frozen `O` is the `k_max`-closure of `G⁺` (Lemma, G14), which Wake cannot
distinguish from the full store. R4 is stated for the frozen `O` and follows from bounded `|G⁺|`. The "surplus that
transfers" is precisely `N_{k_max}(G⁺) \ Used(design)` plus grounded-but-unused concepts; anything further from
`G⁺` cannot transfer through Wake at all (Lemma), so keeping it in the notebook is provably useless.

**C2. "Ontology not charged" vs MDL soundness.** If groundings are free, `G⁺` grows one concept per task, every
task becomes a one-node program, and precision does not improve (V22: "can move up" replaced other coincidences;
420 Codex atoms: training +2, held-out 0). Smallest change: **charge groundings, never the graph.** Corpus two-part
code `L_corpus = Σ_{C ∈ G⁺} L(def r_C) + Σ_t L(P_t)`; admit a grounding only if G3 (pre-existence, generality) and
G4 (corpus saving over ≥ 2 tasks) hold. This is the reviewer's own gate ("compresses beyond its source task") made
formal; it does not reject graph-only surplus, which costs nothing.

**C3. R2 "cost independent of `|O|`" vs seeds computed over all of `G⁺`.** Seeding as written is `Θ(|G⁺|·g_t·τ_r)`.
Resolution: hierarchical seeding (roots `ρ₀ ≤ 64`, subsumption-pruned descent, G10), which requires recogniser
monotonicity (G20); plus adjacency-only access to `G` with the visited-node counter (G9).

**C4. "Conjunctions are not a program form" vs exception RDR.** An exception path `C₁ → C₂` acts on `C₁ ∩ C₂`, and
a sibling list acts on `C₁ ∧ ¬C₂ ∧ …`: RDR trees are decision lists, i.e. conjunctions with negation. The principle
is only true syntactically. Restate as: **no uncharged conjunction** — every context node pays `ℓ_t(C) + ℓ(a) + 2`
bits, and sibling order is charged by the ordered-tree code (G2). Without charging order, two programs with different
semantics would share a code length and Kraft (hence Q2's theorem) would fail.

**C5. R7 vs `n_t = 2–5`.** No distribution-free guarantee exists (Q2.1). Replace R7 by: slot-1 programs pass G5
with `μ₁ = 3` and belong to a class whose design precision has Wilson lower bound ≥ 0.90 (G6). R7 as a probability
statement over the test distribution is dropped.

**C6. R5 on held-out vs available sample sizes and counts-only observation.** With B0 = 1/49 on half B, a rise in
reuse rate is undetectable below +5 (Q5.2), and half B has already absorbed ≈ 20 gated looks. Resolution: measure
reuse at full resolution on design (leave-one-source-out, Q5.1); use N2-gate for gating; reserve a pooled 121-task
decision set for one look on Oct 12 (G18).

**C7. R6 (no regression) vs "prior program first, B0 fallback".** V22 lost 5 design tasks this way. Resolution:
slot ordering by calibrated precision class (G7); prior programs displace B0 from slot 1 only when `|P| ≤ 3` and
margin ≥ 3; otherwise they take slot 2. Regressions are then possible only through B0's slot-2 solves (`s₂`,
measure; expected ≤ 2).

**C8. Dream trigger "≥ 3 nodes" vs cap "depth 2 / 3 nodes".** Consistent only under the root-inclusive count
(fixed above): a program `root + C + exception` has `|P| = 3`, triggers Dream (an exception was needed) and is still
slot-1 eligible. Write the convention into the code (`len(P.nodes)` includes root).

**C9. Dream admission "no lower held-out counts" per abduction vs "held-out counted once per cycle".** Several
abductions per cycle each gated on held-out = several looks. Resolution: batch admission — all abductions of a cycle
are admitted or rejected together on one `(b, c)` release from N2-gate (G16, G18).

**C10. "Mechanisms stated as OWL 2 property chains" vs what mechanisms are.** `rainbow → dispersion → spectrum` is
a path of class-level assertions, not a chain axiom; forcing it into the RBox either violates regularity or says
nothing. Resolution: store mechanisms as T-box existential axioms (`Rainbow ⊑ ∃hasCause.Dispersion`,
`Dispersion ⊑ ∃hasEffect.Spectrum`), keep the RBox to ≤ 10 curated chains (transitivity of `partOf`,
`partOf ∘ locatedIn ⊑ locatedIn`, …), and check regularity at admission (G19). Wake treats both as typed edges of `G`.

**C11. R1 vs a prior derived from live 𝒦 statistics.** Instance counts and centrality change between Dream
cycles; if `ℓ_0` were recomputed, the same program would get different `L` on different days. Resolution: snapshot
`rank(C)` at admission (Q1(b)); Wake uses only the ring code (Q1(a)), which reads no statistics.

**C12. "Most general consistent concept" (G-boundary) vs `argmin L`.** They agree only if generality is what π
encodes. Resolution: make generality the Dream statistic `s(C)` (design tasks where `r_C` fires) so that "more
general" = "smaller rank" = "shorter"; where they still conflict, `L` wins (it has the theorem; generality does not).

**C13. Recogniser time bound `τ_r` vs determinism.** A wall-clock bound is non-deterministic. Resolution: `τ_r` is a
static step cap (`≤ c·|I|²` operations, counted), abort is deterministic and yields `r_C(g) = ∅` for that grid.

**C14. Seed definition "covers individuals that change in every pair".** "Covers" is ambiguous (⊇ vs ∩ ≠ ∅) and
empty for generation tasks. Resolution: seed score = `(recall_i ≥ 1 ∀i, then precision, then ℓ_0)` where
`recall_i = |r_C(x_i) ∩ Δ_i|/|Δ_i|`; for generation tasks seeds come from `γ_C` preconditions on `x_i` as stated;
take the top `s_max = 4` by this order.

**C15. Parameters `θ` and displacements `δ` uncharged.** `L(θ_P)` appears in the formula but `move(δ)`, `paint(ρ)`
domains are unspecified; an uncharged parameter is a free conjunction. Resolution (G2): `ℓ(a) = log₂|Act| + log₂|domain(θ)|`
(paint: `log₂ 5 + log₂ 10 ≈ 5.6`; move over 24 displacements: `≈ 6.9`; draw: `log₂ 5 + ℓ_t(C) + L(θ)`).

---

## Assumptions to measure

| Label | Assumption used | Value assumed | How the implementer measures it |
|---|---|---|---|
| A-T_K | Kaggle total budget | `T_K = 12 h = 43 200 s` | competition rules page; notebook log of total run time on the hidden set |
| A-N_K | hidden task count | `N_K = 240` | competition rules; `len(test_challenges)` printed in the notebook log |
| A-κ | Kaggle / local speed ratio | `κ = 1.5` | ratio of the parity notebook's per-task max on Kaggle to the same run locally (V19: 60 s cloud vs 57 s WSL suggests ≈ 1.1; keep 1.5 until measured on Kaggle) |
| A-τ | recogniser / generator cost | `τ_r ≤ 10 ms`, `τ_γ ≤ 20 ms` per grid | histogram of per-call times over all design grids; enforce with step caps, not timers |
| A-Wake | search parameters | `s_max = 4, m = 8, k_max = 2, V_max = 96, a_eff = 3, w = 4, p_max = 4, c_eval = 100 µs` | counters in the parity log; `a_eff` = mean admissible actions per candidate concept after the residual determines the action |
| A-design | generality threshold | `g_min = 3` other tasks, fire ratio ≤ 0.5 | `g(C)`, `φ(C)` over the 603 design tasks per concept |
| A-code | definition length of a grounding | `8 × bytes(source of r_C)` bits (after stripping comments) | tokeniser on the recogniser source |
| A-null | chance-fit null (Q2.2) | uniform `d_i`-subset and uniform actions per pair | audit: precision of design programs with `E − L < 0` should be ≈ chance; if ≫ chance, `E` is under-counted |
| A-ind | evidence independence | individuals = objects under the program's segmentation (`ρ = 1`); cells only with `ρ = mean object size` | compute `E` both ways on the 118 lattice programs and check that precision is monotone in `E − L` |
| A-𝒦 | relevant region of 𝒦 and hub threshold | `\|𝒦_reach\| ~ 10⁴–10⁵` classes; `δ_hub = 500` | Chao2 `Ŝ` after 30 abductions; in-degree quantiles of the mined store (set `δ_hub` at the 99.5th percentile) |
| A-B0 | B0 precision classes | design 0.69, held-out 0.90; `s₂ ≤ 2` | `(fit, exact)` counts per split; count of design tasks solved only by B0's attempt 2 |
| A-gate | gating noise | `n_changed(c)` ≈ 4 per cycle on N2 | count of held-out tasks whose prediction hash changed, per cycle |

---

## Q7. Wake front-runs Dream

Added after Len's statement that (1) Dream is invoked only when Wake fails, in both regimes; (2) offline, the same
rule keeps the run inside `T_K` and "Dream" can only deepen the search over the frozen `O`; (3) Wake must hand Dream
a signal that keeps Dream focused and bounded. Guards G22–G30; changes to earlier guards are listed in Q7.7.

### Q7.1 The controlled process

*State.* `O_n = (𝒯_n, ℛ_n, G⁺_n)` after `n` Dream steps; `Q_n` = quarantined failure signatures;
`retries(s)` per signature; `U_n ⊆ 𝒟` = design tasks not SOLVED under `O_n`.

*Wake outcome* for task `t` under frozen `O_n` (deterministic, work-budgeted, Q4):

```
ω(t) = SOLVED   iff ∃ exact P with |P| ≤ 3 and margin'(P) ≥ μ₁            (slot-1 eligible)
ω(t) = FIT      iff an exact P exists but only with |P| ≥ 4 or margin' < μ₁
ω(t) = WRONG    iff ω would be SOLVED/FIT and the design test output is known and P(x*) ≠ y*
ω(t) = FAIL     otherwise, with class φ(t) ∈ {NO_SEED, NO_FIT, GEN, BUDGET}
   NO_SEED: S_0(t) = ∅ (no grounded concept covers the change);  NO_FIT: seeds exist, no exact P within caps;
   GEN: output has individuals absent from the input and no generator precondition holds;
   BUDGET: a work counter aborted the search before the radius/tree caps were reached.
```

*Signal* `σ(t)` (the only thing Dream receives about `t`, besides the training pairs):

```
σ(t) = ( ω, φ, S_0 with (recall_i, precision_i) per pair, F, k*, W_spent, NM_β, U )
F      = {C ∈ N_{k*} ∩ G⁺ : r_C(x_i) ≠ ∅ for some i}                    (concepts that fired)
U_i    = Δ_i \ ∪_{C ∈ F} r_C(x_i),   U = (U_1, …, U_{n_t})              (unexplained change, cells)
NM_β   = top-β programs by (|R(P)|, L(P)) with residual R_i(P) = individuals of x_i whose action under P is wrong,
         their cells, and margin'(P);  β = 3
sig(t) = hash(φ, sorted IRIs of S_0, sorted IRIs of top-8 of F by π)      (failure signature)
```

`|σ(t)| ≤ s_max + V_max + β·(p_max + Σ_i |R_i|) + Σ_i |U_i| = O(V_max + n_t·H·W)`: bounded by Wake's own caps,
never by `|O|`. `sig(t)` is what makes "the same missing concept" recognisable across tasks.

### Q7.2 How the signal bounds Dream (G22–G24)

A Dream step is admissible only for `t` with `ω(t) ∈ {FAIL, WRONG}` (FIT triggers are served only from spare
budget; they raise precision, not coverage). Per cycle: `a_c = min(a_max, |{sig(t) : t ∈ T_c} \ Q_c|)`, i.e. the
budget is the number of **distinct** open failure signatures, not tasks (G22). Within a step:

1. **Proposal ball.** `C*` must lie within `d_link = 2` hops (over `Rel`, in `𝒦 ∪ O_n`) of `S_0(t) ∪ F(t)`;
   for `φ = NO_SEED` the proposal is free (this is the only door through which new knowledge enters). The proposer
   sees `σ(t)` and the training pairs only — never the design test output (test-blind, Q7.5).
2. **Mining ball.** Mine `N_d(C*) ∩ N_{d+d_link}(S_0 ∪ F)`; hence nodes per step
   `≤ min(M, |N_4(S_0 ∪ F)|) ≤ min(930, (s_max + |F|)·Σ_{i≤4}(f|Rel|)^i)` — the second term is the bound for
   NO_SEED steps, the first for all others (G23). Hubs, merge and depth guards G11–G13 still apply.
3. **Grounding contract.** The new recogniser must explain the residual: either `P' = NM_1 ⊕ (C*, a)` (one node added
   to the best near-miss) or a fresh `|P'| ≤ 3` program with a node `C*` is exact on all training pairs, and the
   harness's within-task test check passes. Otherwise the grounding is discarded and the step is *unproductive*
   (G24). This is what "one concept covers the change" means operationally: the residual is the abduction target.
4. **Budget per step.** One proposal plus one re-proposal; mining as in 2; grounding effort `e_max` (LLM tokens or
   reviewer minutes, measured). Budget is proportional to the signal, through `|S_0 ∪ F|` in the mining ball and
   through the number of distinct signatures in `a_c`; nothing is proportional to `|O_n|` or to `|𝒦|`.

A step is **productive** iff its outcome is admitted: ≥ 1 design task moves to SOLVED, no design task leaves SOLVED
(monotone admission), `b = 0` on N2-gate at the cycle's batch admission (C9). Otherwise it is unproductive and
`retries(sig(t)) += 1`; at `ρ_max` the signature enters `Q` (G25).

### Q7.3 Convergence from the front-running rule

**Proposition 1 (finite design stream; deterministic).** Assume (H1) monotone admission, (H2) retry cap `ρ_max`
with quarantine by signature, (H3) per step ≤ `M` mined nodes and ≤ `g_step` groundings. Define the potential

```
V_n = Σ_{s ∈ Sig(U_n) \ Q_n} (ρ_max − retries_n(s))  ≥ 0     (integer)
```

Every Dream step lowers `V_n` by ≥ 1: an unproductive step raises one `retries(s)` by 1 (or moves `s` into `Q`,
removing a term equal to 1); a productive step removes ≥ 1 signature with `ρ_max − retries ≥ 1` and, by (H1),
never re-adds a signature (no task returns to `U`). Re-opening a quarantined signature (allowed only after a productive step changed its `S_0`, one signature per
productive step, one extra retry) raises `V` by 1 at most once per productive step, so it adds at most `|𝒟|` steps.
Hence

```
#Dream steps ≤ V_0 + #productive ≤ (ρ_max + 1)·|Sig(𝒟)| ≤ (ρ_max + 1)·|𝒟|,
|Store_∞| ≤ |O_0| + (ρ_max+1)·|𝒟|·M,       |G⁺_∞| ≤ |G⁺_0| + g_step·(ρ_max+1)·|𝒟|,       |O_frozen| ≤ 73·|G⁺_∞|.
```

Numbers: `|𝒟| ≈ 1180`, `ρ_max = 2`, `M = 930`, `g_step = 2`: store ≤ 3.3·10⁶ nodes, `|G⁺| ≤ 7080`
(worst case, every design task failing three times); with B0's 617/1000 already solved the realistic ceiling is
`≈ 500 open signatures → ≤ 1500 steps, |G⁺| ≤ 2000` (productive steps ≤ 500), frozen `O ≤ 146 000` nodes ≈ 35 MB < `B = 64` MB. R4 holds
by construction, with no assumption on `𝒦`, because Dream is driven by a finite set of failures with bounded
retries — this is the formal content of "Wake front-runs Dream is the key to convergence".

**Proposition 2 (unbounded i.i.d. task stream; supermartingale).** Tasks `t ~ 𝒯`; `F_n = P_𝒯[ω(t) ≠ SOLVED | O_n]`.
Assume (H1), and (H4) *transfer granularity*: a productive step lowers `F` by at least `ε > 0` in expectation
(the grounded concept solves a task-mass ≥ `ε`, not just its source). Let

```
Φ_n = |G⁺_n| + (g_step/ε) · F_n .
```

Productive step: `|G⁺|` rises ≤ `g_step`, `E[F]` falls ≥ `ε` → `E[ΔΦ] ≤ 0`. Unproductive step: nothing is admitted,
so `|G⁺|` and `F` are unchanged → `ΔΦ = 0`. Thus `Φ_n` is a non-negative supermartingale and
`E|G⁺_n| ≤ Φ_0 = |G⁺_0| + g_step/ε` for all `n`; the frozen `O` is bounded by `73·Φ_0`. The **store** is not
bounded by this argument (unproductive steps still mine); it is bounded by (H2) per signature and by the streak cap
`u_max` per cycle (G25): unproductive steps over `C` cycles `≤ u_max·(#productive + C) ≤ u_max·(1/ε + C)`.

**Failure modes and their guards.**

| Condition violated | What happens | Guard |
|---|---|---|
| (H1) admission not monotone (a new concept displaces a correct program) | signatures re-enter `U`, `V_n` can rise, steps unbounded | batch admission with "no design losses" (existing) — Wake's slot rule G7 makes displacement require a *better* precision class |
| (H2) no retry cap: unsolvable tasks (no prior in 𝒦 explains them, or the DSL cannot express the action) trigger Dream every cycle | linear growth of the store, `f_c` flat | `ρ_max = 2` per signature; quarantine; `Q` reported per cycle; a quarantined signature is re-opened (one extra retry) only when a *productive* step changes its `S_0`, at most one signature per productive step |
| (H4) fails: `ε → 0` (groundings solve only their source: renamed conjunctions) | `\|G⁺\|` grows like the number of failures; `f_c` falls one task per grounding, held-out unchanged | `ζ_c` = design tasks newly SOLVED per grounding ≥ 1.2 over any 20 consecutive groundings and `ζ^{N2}_c > 0` over a cycle (G26); on violation freeze mining and tighten G30(b) |
| persistent low productivity in a cycle | wasted mining, store growth | streak cap `u_max = 5`; `a_c` tied to distinct signatures (G22) |

Monitoring for Q7.3: `f_c = |U_c|/|𝒟|` (must be non-increasing; flat over 3 cycles with ≥ 10 steps → freeze mining),
`p_c` = productive fraction (`< 0.2` → halve `a_c`), `|Q_c|`, `ζ_c`, `ζ^{N2}_c`, `|G⁺_c|`, store size.

### Q7.4 Offline Kaggle schedule

*Facts and assumptions.* `T_K = 12 h = 43 200 s` (A-T_K). `N_K ≈ 120` tasks / ≈ 170 test outputs per Len; the 2025
hidden set had 240 tasks, so the plan is also checked at `N_K = 240`. The notebook prints `len(challenges)` and the
number of test outputs to its log at start; `N_K` is read from the input, so any allocation that depends on it is
still a deterministic function of the hidden set. Kaggle/local speed `κ = 1.5` (A-κ; V19: 60 s cloud vs 57 s WSL
suggests ≈ 1.1). Offline "Dream" = deeper deterministic search over the frozen `O` only.

*Work units.* One unit = one candidate evaluation on one grid, `c_unit ≈ 100 µs` local; recogniser calls, generator
calls and B0 steps are converted with their own measured per-call costs from the parity run
(B0: 1667 s single-process / 120 tasks = 13.9 s mean, 60.5 s max → `1.39·10⁵` units mean, `6.05·10⁵` max).
Every budget below is in units; wall-clock is read only at round boundaries (G27).

*Rounds* (each round processes its task set in `hash(task_id)` order and **commits** its outputs only when the whole
round finishes; per-task budgets in units, local-time equivalents in brackets):

| round | task set | search | budget per task | class-specific deepening |
|---|---|---|---|---|
| R1 | all | B0 stack + Wake `k ≤ 1`, `\|P\| ≤ 3` exhaustive | `W_1 = 2·10⁴` [≤ 10 s] + B0 [≤ 60.5 s] | — (produces `ω`, `φ`, `σ` for every task) |
| R2 | `ω ≠ SOLVED` | Wake `k = 2`, `\|P\| ≤ 4`, `w = 4` | `W_2 = 2·10⁵` [≤ 45 s] | BUDGET: same search, budget ×4 |
| R3 | `ω ≠ SOLVED` after R2 | offline Dream by class | `W_3 = 3·10⁵` [≤ 35 s] | NO_SEED: seeds from concepts firing on `≥ n_t − 1` pairs; `k = 3` through graph-only bridges with `V_max = 96`. NO_FIT: `\|P\| ≤ 5` (slot 2 only), `w = 8`. GEN: generator composition `draw ∘ paint`, `θ` on a declared grid. WRONG-class calibration is not available offline. |
| R4 | tasks with one attempt filled | second-attempt filling: next distinct prediction by `L` | `W_4 = 2·10⁴` [≤ 2 s] | — |

Per-task total `≤ 60.5 + 10 + 45 + 35 + 2 ≈ 152 s` local ≤ `300 s / κ_max` with `κ_max = 2` (G28): the 300 s alarm
cannot fire unless Kaggle is more than 2× slower than local, and then G27 degrades by rounds, not by tasks.

*Optimisation.* With `x_{t,r} ∈ {0,1}` = "task `t` receives round `r`", class gains `g(φ, r)` = fraction of class-`φ`
tasks that become correct in round `r` (estimated on the design set for R2/R3 and checked on N2-gate as counts),
and unit costs `w_r`:

```
maximise  Σ_{t,r} x_{t,r} · g(φ_r(t), r)
subject to  Σ_{t,r} x_{t,r} · w_r  ≤  U_rem := U_K − U_1(actual counters),   x_{t,r} ≤ x_{t,r−1}·1[ω_{r−1}(t) ≠ SOLVED]
U_K = T_K·(1 − s)/(κ·c_unit) = 43 200·0.75/(1.5·10⁻⁴) = 2.16·10⁸ units  (s = 0.25 safety)
```

The LP relaxation is a fractional knapsack: fund items in decreasing `η = g(φ, r)/w_r` (Dantzig); the integral
greedy is within one item (≤ 1 expected correct output) of optimal because all items of a round have equal size.
Expected ordering of `η` from the design experience (to be measured, G29 table): R2 on NO_FIT > R2 on BUDGET >
R3 on NO_SEED (bridging) > R3 on GEN > R3 on NO_FIT (`|P| = 5`, slot 2 only) > R4. All inputs to the greedy
(`φ`, counters, the `η` table frozen into the notebook, `N_K`) are deterministic, so the allocation is a function
of (hidden set, `O`) — R1 is preserved.

Feasibility at the recommended values: `N_K = 120`: R1 worst `120·(6.05+0.2)·10⁵ = 7.5·10⁷` units, typical
`1.9·10⁷`; R2+R3 worst `100·5·10⁵ = 5·10⁷`; total worst `1.3·10⁸ < 2.16·10⁸` ✓ — the per-task cap binds, not `T_K`.
`N_K = 240`: R1 worst `1.5·10⁸`, R2+R3 worst `1.0·10⁸`, total `2.5·10⁸ > U_K` → the greedy rations R3 (and part of R2)
by `η`; typical case (`R1 ≈ 3.8·10⁷`) is comfortably feasible. With 4 worker processes the wall-clock divides by
≈ 3.5 and `U_K` may be multiplied accordingly, but keep `s = 0.25` on the parallel figure.

*Safety margin.* `s = 0.25` of `T_K` plus `κ = 1.5` against a measured ≈ 1.1 gives an effective 2.7× margin on the
sum; the per-task alarm has 2× (G28).

*Calibration and deterministic degradation (G27, G29).* `c_unit` and per-counter costs come from the local parity run;
`κ` from the Kaggle log of the same notebook on the 120 public tasks (`κ = max(1.5, measured)`). Recalibrate when the
parity run's `c_unit` drifts by > 20 %. On Kaggle the notebook compares elapsed time to the planned time only at
round boundaries: if `elapsed > 1.25 × planned_so_far`, all later rounds are skipped and the last committed round's
outputs are emitted. The number of completed rounds is the only wall-clock-dependent quantity; it is logged, and the
local run pre-computes a parity digest `digest_r` for every `r = 1..4`, so parity is checkable whichever round count
Kaggle reached. Because rounds commit atomically, no task ever depends on a timeout: if the 300 s alarm nevertheless
fires inside round `r`, the handler aborts round `r` for all tasks (no partial commit), which is the same outcome as
"round `r` skipped".

### Q7.5 MDL: Len's rule versus G3/G4, and the smallest guard that does not charge the ontology

*Precise conflict.* Len: `L(P)` charges only the atoms and chains a program uses; the ontology is excluded. G3 (fires
on ≥ 3 other design tasks) and G4 (corpus saving ≥ `L(def)`) are admission gates on `G⁺`; G4 is literally a
charge in bits on the ontology and G3 is a generality tax. They reject Rainbow (fires on one design task) although it
is a verified common outside concept — exactly the kind of prior the surplus is meant to carry. The reason G3/G4
exist is to block *renamed conjunctions*: a "concept" whose recogniser is a task-specific predicate. On the design
set alone a rare genuine prior and a renamed conjunction have the **same** firing statistics (one task each), so any
firing-count gate has a type-I error against rare priors. Firing counts are the wrong discriminator; provenance and
prediction are the right ones.

**Option A (statistical/corpus charge; current G3/G4).** Strong against renamed conjunctions; contradicts the
transfer thesis by rejecting rare genuine priors; risk = under-grounding, and it re-introduces exactly the corpus-MDL
gate the reviewer excluded.

**Option B (recommended: provenance + prediction + front-running; no charge on the ontology; G30).** Admit a
grounding iff

- (a) pre-existence: `C*` has an IRI in 𝒦 with snapshot statistics, and its definition text cites the source-domain
  description (Wikidata/Wikipedia first sentence) — checked by the harness as a citation, not a similarity score;
- (b) bounded parameters: every parameter of `r_{C*}`/`γ_{C*}` is drawn from a finite domain declared in the
  definition (spectrum order, bow geometry, motion directions); no task ids, no literal colours, no grid-size or
  coordinate constants (a code-review rule enforced by a linter);
- (c) test-blind grounding with a within-task test check: the proposer never receives the design task's test output;
  the harness runs the check once; a chance pass by a renamed conjunction has probability
  `≤ 2^{−E(test)}`, `E(test) = log₂ C(N*, d*) + d*·log₂ a` (≈ 8–20 bits on typical tasks, i.e. ≤ 0.4 % at 8 bits);
- (d) no design losses at batch admission (monotone admission (H1));
- (e) front-running (G22): the grounding was triggered by a Wake failure and explains its residual (G24).

Under Option B the ontology is not charged anywhere: `L(P)` stays exactly Len's rule (used atoms and chains, ring code
G1), and convergence comes from Q7.3, not from a corpus code. G3's firing count and G4's `ΔL_corpus` remain as
**monitors** (reported per concept, never gating), and `ζ` (G26) is the alarm that Option B's residual risk has
materialised.

*Residual risks of Option B, quantified.* (i) False admission by a chance test pass: expected number over the run
`≤ Σ_steps 2^{−E(test)} ≤ 1000 × 0.004 ≈ 4` concepts — each bounded in cost (one entry in `G⁺`, evaluated only when
reached through the graph) and detected if it over-fires (`b > 0` on N2-gate). Raising the required `E(test)` to
10 bits (skip the test check as insufficient evidence when `E(test) < 10`, and require a second design task instead)
brings the expectation below 1. (ii) Over-firing on hidden tasks unlike the design set — unmeasurable before
submission; bounded by the slot rule G7 (a prior program takes slot 1 only in the `|P| ≤ 3, margin ≥ 3` class).
(iii) Process risk: (c) is enforced by the harness withholding `y*`, not by mathematics; if the proposer is a human
who has seen the test output (as with e73095fd and 3979b1a8), record the concept as "test-seen" and require one
further design or N2-gate solve before it may take slot 1.

*Optional held-out-free generality check (soft).* "`r_{C*}` fires on ≥ 1 design grid outside its source task, or has
a generator, or is a step of an admitted mechanism chain." Rainbow passes through its generator and chain; a renamed
conjunction typically fails. Recommended as a *monitor with a warning*, not a gate, so that a rare prior with neither
is still admitted on (a)–(e).

### Q7.6 Monitoring summary for Q7

| metric | where | threshold | action |
|---|---|---|---|
| Dream steps without a failure record | Dream log | `> 0` | reject step (G22) |
| `f_c`, `p_c`, `\|Q_c\|` | per cycle | `f_c` flat 3 cycles with ≥ 10 steps; `p_c < 0.2` | freeze mining / halve `a_c` (G25, G26) |
| `ζ_c`, `ζ^{N2}_c` | per 20 groundings / per cycle | `ζ < 1.2` or `ζ^{N2} = 0` for 3 cycles | freeze mining; review groundings for task constants (G26) |
| contract failures (G24) | per cycle | `> 50 %` | halve `a_c` |
| planned vs actual units per round; round count reached | Kaggle log | actual `> 1.25×` planned | skip later rounds (G27) |
| max per-task local time | parity run | `> 150 s` | cut `W_3`, then `W_2` (G28) |
| `κ` | Kaggle log vs local | `> 1.5` | raise `κ`, rebuild round plan (G29) |
| false-admission estimate `Σ 2^{−E(test)}`; `b` on N2-gate | per cycle | `> 1`; `b > 0` | retire concept; require `E(test) ≥ 10` (G30) |

### Q7.7 Changes to Q1–Q6 implied by Q7

- **G3, G4 → monitors under Option B** (marked in the summary table). Q1.2(c)'s statement that an invented concept
  never lowers `L` within a task is unchanged; the corpus two-part code is no longer a gate.
- **G16 (`a_max`)** is now `a_c = min(a_max, #distinct open signatures)` (G22); `g_max` stays as a hard cap.
- **G15 (saturation stopping rule)** becomes a *secondary* check: convergence is guaranteed by Proposition 1
  regardless of Chao2; keep `r_w` and `Ŝ` as diagnostics of how much of `𝒦_reach` the failures have pulled in.
- **G8 (Wake budget)** is split into round budgets `W_1..W_4` (G27, G28); the total per task is unchanged (≤ 150 s local).
- **Q5 protocol:** the trigger set `T_c` and all signals are computed on design tasks only; held-out tasks never
  trigger Dream (their failures would leak identities). On Kaggle the signal drives only the deterministic rounds.
- **C1 resolution** is strengthened: the surplus ontology now grows only through failure-driven, signal-bounded
  steps, so "grow far beyond training" is bounded by `ρ_max·|Sig(𝒟)|·M` without any saturation assumption.
- **Assumptions added:** A-N_K becomes "120 tasks / ≈ 170 outputs (Len), stress-checked at 240; measured from the
  notebook's start-of-run log"; A-ε (transfer granularity, estimated as `1/ζ` from design and N2-gate counts);
  A-s (`s = 0.25` safety fraction).
