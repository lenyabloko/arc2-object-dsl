# Formal problem statement: abductive meta-learning with a convergent ontology of priors

Prepared 2026-09-29 for a formal attack (bounds and guards). Author of the approach: Len Yabloko. Scribe: Claude.
Companion design doc: "Abductive Meta-Learning: Dream and Wake" (Claude Doc).

## 0. Setting

- **Benchmark.** ARC-AGI-2 (Kaggle ARC Prize 2026). A task t = (D_t, Q_t): D_t = {(x_i, y_i)}, i = 1..n_t, training
  pairs of grids (n_t is typically 2 to 5); Q_t = test inputs. A grid is an H × W array, H, W ≤ 30, over 10 colours.
  Score = fraction of test outputs reproduced exactly within 2 attempts.
- **Two regimes.** Dream runs online (internet and the Semantic Web reachable, no hard time limit per step).
  Wake runs offline on Kaggle: no network, deterministic, total time budget T_K for the hidden task set, and a
  per-task alarm of 300 s in the current notebook.
- **Splits.** Design set 𝒟 = ARC-1 training tasks, N1 (130 ARC-AGI-2 training tasks), dev-eval half A. Held-out
  𝒱 = N2 (101 tasks), dev-eval half B (49 tasks), sealed (public-eval outputs never used for design). Held-out
  results may be observed as counts only, once per cycle. Public-eval parity: 120 tasks, 172 test outputs.
- **Baseline B0** = solver V21: public eval 49/172 (digest c93d287b), N2 exact 37 (fit 41), half B 1/49,
  sealed 1, training G-stratum exact 617 of 1000; single-process public-eval run 1667 s, max 60.5 s per task.

## 1. Objects

1. **A-box.** For a grid g, a deterministic procedure A(g) yields a finite set of individuals I(g) (cells;
   connected components under a fixed set of segmentations S; background regions) and assertions: unary
   (colour, size, shape class, …) and binary (adjacent, inside, same shape, aligned, …). |A(g)| is polynomial in |g|.
2. **T-box 𝒯.** A finite set of concept names. Each concept C has:
   - an intension def(C) in its source domain (optics, mechanics, topology, chemistry, …);
   - a recogniser r_C : A(g) → 2^{I(g)}, total, deterministic, with time bound τ_r;
   - optionally a generator γ_C : (A(g), θ) → partial grid, deterministic, with time bound τ_γ;
   - links ext(C) to external entities (Wikidata, DBpedia, ConceptNet IRIs).
   C is **grounded** if r_C (and γ_C where needed) is implemented; otherwise it is graph-only.
3. **RBox ℛ.** Role names and axioms: role inclusions and OWL 2 property chains R_1 ∘ … ∘ R_k ⊑ S (regular, as
   OWL 2 DL requires). A role is grounded if it is computable on A-boxes, else graph-only. Mechanisms of priors
   (e.g. rainbow: caused by dispersion; dispersion: light splits into an ordered spectrum; many drops: bow shape)
   are stated as chains; chain steps point to recognisers or generators where these exist.
4. **Ontology graph** G(𝒯, ℛ): nodes = concepts; typed edges from {subClassOf, partOf, hasCause, hasEffect,
   hasShape, chain link}; G⁺ ⊆ nodes = grounded concepts.
5. **Actions.** A finite set Act = {keep, paint(ρ), remove, move(δ), draw(γ_C, θ)}, ρ a colour role, δ a displacement.
6. **Programs.** P is a ripple-down-rule (RDR) tree: a root default action; each node ν = (C_ν, a_ν, ordered
   children). An individual receives the action of the deepest node on its path whose concept covers it, with
   first match among siblings. |P| = number of nodes; h(P) = depth. P(x) = the grid after applying the actions.
   P ⊨ D_t iff P(x_i) = y_i for every training pair.

## 2. Description length (MDL on used atoms and chains only)

```
L(P | 𝒯, ℛ) = Σ_{ν ∈ P} ℓ(C_ν) + Σ_{ν ∈ P} ℓ(a_ν) + L(θ_P),      ℓ(C) = −log₂ π(C)
P*_t = argmin_{P ⊨ D_t} L(P | 𝒯, ℛ)
```

π is a prior over concepts derived from outside knowledge. **The ontology is not charged**: it is a side effect
of Dream and is meant to grow far beyond what the training tasks use, because that surplus is what transfers.
Conjunctions are not a program form; context in the RDR tree replaces them, and every node is charged.

## 3. Processes

**Dream (online).** State O_n = (𝒯_n, ℛ_n, G⁺_n) after n abductions. One step, for a task that needs a prior
(unsolved, solved only by a program with ≥ 3 nodes, or answered wrongly):
1. propose a concept C* that covers the change in one or two words (from the reviewer, a model, or search),
   lifting into a richer world when the 2D description needs conditions (3D, motion, optics, gravity, chemistry);
2. mine N_d(C*) from an external knowledge base 𝒦: depth ≤ d, fan-out ≤ f per relation, relations from a fixed
   list Rel; merge equivalent nodes (same IRI, owl:sameAs);
3. ground some nodes (write r_C, γ_C);
4. admit if the guards hold (no design losses, no new wrong answers, no lower held-out counts, budgets respected).
O_{n+1} = O_n ∪ mined nodes and axioms ∪ new groundings.

**Wake (offline).** For task t:
1. seeds S_0(t) = {C ∈ G⁺ : r_C covers individuals that change, in every training pair} ∪ {C : γ_C's preconditions hold};
2. neighbourhoods N_k(t) in G, with each node's out-degree capped at m (ranked by π);
3. enumerate RDR trees with nodes from N_k ∩ G⁺, |P| ≤ p_max, h(P) ≤ h_max; keep exact fits; choose by L;
4. if none, k ← k + 1 up to k_max; then fall back to the B0 stack, tagging the answer "needs a prior".

## 4. Requirements

- **R1 Determinism.** Wake output is a function of (task, frozen O) only.
- **R2 Time.** Σ_t cost_W(t) ≤ T_K, and cost_W(t) ≤ 300 s, independent of |O|.
- **R3 Space.** size(frozen O) ≤ B.
- **R4 Convergence.** |O_n| stays bounded and its growth rate tends to 0 (saturation). The previous system
  (Codex) failed exactly here: its ontology never converged to a finite size.
- **R5 Transfer.** The reuse rate (tasks explained by concepts already in O with no new code) rises on held-out splits.
- **R6 No regression** against B0.
- **R7 Generalisation.** A program chosen on n_t pairs must be right on the test with high probability.

## 5. Empirical facts available

- Lattice solver, training run (118 programs): 1–2 rules 34/34 correct; 3 rules 20/25; 4 rules 14/17; 5 rules 15/42.
- V22 experiment (concepts added as flat attributes with a tie-break preference, 575 of 603 design tasks):
  V21 70 correct / 31 wrong; V22 68 / 34 (gained 3, lost 5); V22 with exception-RDR only 69 / 34 (gained 5, lost 6).
  Coincidental low-level concepts ("can move up") replaced other coincidences.
- Reviewer abductions verified exactly: e73095fd = Cavity (3D reading; exact on 3 train + test);
  3979b1a8 = Rainbow (drop spectrum + bows; exact on 2 train + test).

## 6. Questions to attack (deliverables)

For each: a formal statement, the bound or guard as explicit inequalities with recommended parameter values,
a short justification, and a monitoring metric with a threshold.

- **Q1 Prior π.** Construct π from statistics of 𝒦 (e.g. instance counts, hierarchy depth, centrality) and graph
  distance to the task's seeds. Show it is a proper (sub-)prior over a potentially unbounded concept space
  (Kraft), that "invent a concept per task" is expensive under it, and that it is computable offline and deterministically.
- **Q2 Occam guard for Wake.** With H_k = the candidate programs at radius k, bound the probability that a program
  consistent with D_t is wrong on the test. Derive p_max, h_max, k_max (and the exception cap: is depth 2 / 3 nodes
  right?) as functions of n_t, grid sizes and π. Relate to the empirical accuracy-by-rule-count data.
- **Q3 Convergence of Dream.** Model |O_n| = |∪_{j ≤ n} N_d(C*_j)| over a knowledge base 𝒦. Give conditions for
  boundedness and a saturation estimator (e.g. Good–Turing or capture–recapture on new-node rates); the guards
  (d, f, Rel, merge policy, hub exclusion, per-cycle cap) and a stopping rule. Name the likely mechanisms of
  Codex's non-convergence (unbounded depth, closure through generic hubs such as "physical object", synonym
  duplicates, ungrounded growth) and the guard for each.
- **Q4 Wake complexity.** Bound cost_W(t) in terms of |S_0|, m, k, |Act|, p_max, τ_r, τ_γ; choose m, k_max, p_max
  to meet R2 with margin; show the cost is independent of |O|.
- **Q5 Transfer test.** Define the reuse rate formally. Give a decision rule for Oct 12 with N2 = 101 (B0: 37 exact)
  and half B = 49 (B0: 1): the minimal detectable improvement at α = 0.05 for a paired comparison, and a budget of
  looks so that repeated per-cycle counts do not leak held-out information into design.
- **Q6 Consistency.** Check the T-box / RBox / A-box assignment, OWL 2 DL regularity of mined chains, decidability of
  realisation; list any contradictions among R1–R7 and the principles (e.g. R4 versus "grow far beyond training",
  R2 versus a rich ontology, MDL versus exceptions) with a resolution for each.
