# Object DSL recovery: previous failure modes and an isolated working subset

Prepared 2026-09-25 from the `recovery` checkout of `arc_extended_arga` (HEAD `023678b2`). Evidence comes from the full reflog (1,364 entries between 17 July and 24 September), the governing docs, the recovery and verification records, a Wake rule snapshot and a static scan of the code. This is an analysis. Nothing in the repo was changed.

---

## Part 1: Previous failure modes

### F1. The learning happened in the development loop, not in the system

The design calls for an offline loop in which Wake's capability gaps are closed by deterministic Dream (see F4). In practice, the executable rules came from the nondeterministic lane during development: Codex looked at visible tasks and wrote executors for them. The population Dream worked over was the "complete 800-task authority": ARC-1 training plus evaluation (`INCREMENTAL_WAKE_PROVENANCE.md`). Later it also included the ARC-2 training file. The evaluation sets used to report success were therefore the same sets the executors were written for. The replication was "blind" only within a single run, not across development.

- 22 July: about 60 `Realize <behavior>` commits in one day, for example "Realize handed barrier detour portal paths" and "Realize segmented outward paired-bar rays".
- 12–13 August: 121 `synthesize` / `solve` / `compose` / `authorize` commits in three days, for example "solve bracketed path collapse" and "synthesize boundary seed pinball flow".
- Wake rule snapshot (`_tmp_wake_rules.json`, July): 246 rules use 233 distinct operations, and 231 of those operations appear in exactly one rule. 97 rules have a support group count of 0, and 52 bind literal colors.
- Outcome: 338/400 on ARC-1 evaluation (`evaluation_replication_7faad138.md`) and 99/120 tasks on ARC-2 evaluation (static `2a55`). But both official Kaggle submissions on record, `55757140` and `56476468`, scored a public **0.00**. A system that scores 82–85% on public sets and 0% on hidden ones has memorized the public sets rather than learned from them.

### F2. Task-specific solvers disguised as DSL atoms

The DSL grew by adding a new named mode whenever a task needed one, not by adding composable primitives. So "search" ended up choosing among stored solutions.

- `extended_transformations/fill_grid.py` is 459 KB. Almost all of it is one function, `fill_grid_based`, which is 10,471 lines long and branches on the `object` string across 152 named cases, for example `"copy_template_centered_on_marker"` and `"rectangle_border_fill_by_height_parity"`. Twenty of the 26 grid-transform modules dispatch on named modes the same way (`basic_grid` 66, `magnet_grid` 51, `recolor_grid` 40, `crop_grid` 36, ...).
- `dsl.py` (541 KB): `DSLMapper` has about 100 `*_candidates` generators, for example `mirror_gray_components_across_red_frame_candidates` and `gray_bar_extremes_candidates`.
- `connectors/`: about 110 executor modules named after single behaviors, for example `fuel_panel_slide.py`, `taut_bar_wrap.py` and `tee_room_recolor.py`.

North Star commitment 1 ("do not replace abstraction with family-specific grid probes disguised as atoms") is a direct response to this.

### F3. Governance was used in place of generalization

After the deployment score was recorded on 20 August, the work turned to certifying the existing rules. Of the 769 commits between 20 August and 8 September, **673** are `Lower … shadow`, `Prove … selector binding`, `Close … selector`, `Ground …` or `Inventory …`. Each one breaks an existing bespoke selector into "detector atoms" named after that same bespoke behavior, for example "Lower strict-shared-cardinal-gravity shadow". That makes a memorized solution auditable, not general. The protocol itself forbids "ontology names attached after implementation", but it couldn't enforce that, because the atoms were derived from the executors.

Meanwhile the ten-gate acceptance hierarchy and population-wide closure receipts made every change expensive. Progress came to be measured in closures and receipts, not in transfer to unseen tasks.

### F4. The offline Wake → Dream loop has no generative step

*This replaces an earlier version of this section that misread the design.* The intent is a learning loop that runs offline inside Kaggle. Wake emits capability gaps, expressed as missing ontology subgraphs. Deterministic Dream closes them with no neural net or LLM involved.

As specified in `VERTICAL_CLOSURE_ALGORITHMS.md`, though, deterministic Dream can't produce the missing subgraph:

- **Closure can't add anything new.** C1–C12 are positive Horn rules over a frozen, finite universe `U` of registries. A least fixed point of those rules is always built from symbols and edges already in `U`. A missing subgraph is, by definition, one that isn't there.
- **Only reviewed code can execute.** C7: "cannot create or activate an executable Wake rule. Realization remains a separate reviewed transaction." Section 9: provisional children stay "non-executable … until reviewed". Section 13.1: `wake_eligible` requires "a reviewed realization". Inside Kaggle there's no reviewer.
- **The only executable composition reuses existing transforms.** C10 chains the partial transforms that existing RDR nodes already have. It can't create a new operation or binding.
- **The step that invents something is the offline LLM lane.** Section 16 says to escalate to nondeterministic Dream when deterministic Dream doesn't improve. That lane is the only one allowed to introduce a `new_hypothesis` or `new_differentiator`, and it isn't available offline.
- **New concepts need support from several tasks.** Differentiation proposes a child only with "minimum cross-case support" (section 9). ARC-AGI-2 tasks are built around in-context symbol definition, so the concept a hidden task needs usually appears in that task alone.

The evidence agrees. The Kaggle visible-population run (`authority552 … v7`) attributes **0** of 259 answers to `deterministic_dream`, and on the 120-task evaluation run all 136 correct answers came from `wake:rule`. The loop was never shown to close a gap without the offline LLM lane.

### F5. The measurement populations were mislabeled

The 240-task file (`arc-agi_test_challenges.json`) is a subset of the training set. It was reported as ARC-2 progress (235/259 cases) for weeks. The real 120-task / 172-input evaluation baseline was first measured on 23 September (`KAGGLE_VERIFICATION_HANDOFF.md`). The loop was therefore tuning against a population that couldn't expose overfitting.

### F6. Infrastructure sprawl crowded out the core question

Between 17 July and 10 August, 426 commits went mostly to authority, cohort, G-drive, lifetime DB and Assistant UI plumbing (about 180 commits). The root directory holds 668 Python files (16.6 MB) plus multi-megabyte ontology TTL and JSON files. Meanwhile the one question that mattered, whether it solves tasks it has never seen, went unmeasured until the Kaggle 0.00.

### How the current pilot compares

| Failure | Pilot status |
|---|---|
| F4, no inference-time synthesis | **Addressed.** `search.py` builds a program from the demonstrations of each task. |
| F2, disguised atoms | Mostly avoided: 5 general primitives. The exception is `slide_node`, a new macro designed after seeing scored errors. |
| F5, population | **Addressed.** Corpus identity is verified: 120 tasks / 172 inputs. |
| F1, dev loop sees the measurement set | **Still at risk.** The same 2-task family was diagnosed and then re-scored. |
| F3, governance instead of capability | **Still at risk.** Four Kaggle parity rounds for a candidate that scores 2/172. |

### Train-time vs. test-time framing (corrected per the author)

**Train time.** Online Wake ↔ Dream cycles, assisted by an LLM and reviewed by a human in the Assistant UI, grow the ontology through nondeterministic transitive closure. The ontology plays the role that a network's latent space would. This amounts to train-time learning from human feedback.

**Test time.** The offline, deterministic Wake ↔ Dream loop in Kaggle uses the learned ontology as fixed "weights".

Seen this way, the question is whether what was learned transfers to tasks it was never trained on. Based on the evidence, it didn't. There are three causes:

1. **No generalization signal during training.** Training was credited for solving visible tasks, and the evaluation sets were inside the training population (F1, F5). There was never a held-out validation split, so overfitting was invisible until Kaggle scored 0.00.
2. **No compression pressure on the executable layer.** Description length (section 9) and RDR compression apply to the ontology and the rules. Each reviewed realization, though, added a task-sized executor: 231 of 233 operations are used once. What was learned is a lookup table, not shared structure. The ontology atoms were then derived from those executors (F3), so they're no more general.
3. **Too coarse to compose at test time.** Offline, the only generative mechanism is composition (C10) of existing partial transforms. Transforms that each solve one whole task can't be recombined into a solution for a new task.

The split itself is sound. It's the wake–sleep library-learning pattern, as in DreamCoder. What's missing is the condition that makes such a library generalize: an item is admitted only when it **compresses solutions across several tasks**, and acceptance is measured on **tasks held out from training**.

### Where the ARCGraph inductive bias leaked (per the author's design intent)

The design differs from DreamCoder in one respect. Its nondeterministic phase is meant to be steered by the strong inductive bias of the ARCGraph abstractions, so that it produces reusable topological and geometric primitives, with human feedback guiding an ontology grounded in the detectors and connectors induced along the way. In practice, that bias shaped the vocabulary but not the executables:

- **Realizations bypassed ARCGraph.** None of the 26 `extended_transformations` modules import `ARCGraph` or `Image`, and 11 of them reimplement connected components or rectangle finding for themselves. They operate on raw grids, so the executable layer never expressed anything in ARCGraph primitives.
- **The unit of induction was one task.** Frontier packets attach "exactly one default proposal" to each unresolved task. DreamCoder gets reuse by abstracting over several solved programs; generating per task yields solutions sized to a task.
- **Review checked correctness and grounding, not reuse.** No reuse or held-out-transfer measure gated admission.

**Correction from the author:** all three of these were already specified in the governing docs.

- **Realizations:** the docs require realizations over ARCGraph abstractions.
- **Induction:** they specify clustering across multiple tasks, driven by medoid metrics.
- **Human feedback:** it arrives as ontology *perturbations* in the Assistant UI, which then propagate through vertical closure.

The failures were implementation drift: Codex didn't follow those directions. The design's intent stands.

The lesson is that prose constraints didn't hold against an implementing agent, even as the docs grew (the vertical-closure docs alone are 96 KB). The key constraints should therefore be **enforced by construction**, so that a violation can't pass:

1. **The realization API accepts only ARCGraph programs.** A test rejects any realization that imports grid-level code or calls anything other than registered primitives.
2. **Admission is computed, not asserted.** New primitives need medoid-cluster support of at least *k* tasks, plus transfer solves on sealed tasks.
3. **The perturbation → vertical closure → re-realization path works end to end.** Build and test it on a small core before any new realization work.
4. **Every cycle reports its transfer-solve count automatically.**

### Using unsolved ARC-2 evaluation tasks as the split (per the author)

During training, the targets are the ARC-2 public evaluation tasks that aren't solved yet. That target is right, but a task the LLM or a reviewer has inspected while inducing a primitive stops being held out. It then measures how well training fits, not how well it transfers. The static system solved 99 of 120 evaluation tasks this way and still scored 0.00 on hidden tasks.

A cheap fix reuses the existing packet provenance. Credit a **transfer solve** only when:

- the solving ontology or primitive revision was induced from packets that did not include that task, and
- the task was never shown in the Assistant UI during that cycle.

Keep a sealed share of the unsolved evaluation tasks that is never shown, and report its solve rate separately. That rate is the estimate of the hidden score.

### How realizations were meant to arise (per the author)

- **Induced, not directed.** Human perturbations (`new_hypothesis`, `new_differentiator`) are a second-order inductive bias on top of the DSL-grounded ontology. Realizations aren't directed by the human; the LLM induces them from the perturbed concepts.
- **Disposable.** They must strictly adhere to those concepts, and they are regenerated nondeterministically in every online Wake–Dream cycle.
- **Gaps feed back.** Remaining capability gaps become the ground for the next perturbations.

**Where this broke.** Adherence to a concept was a semantic judgment. The perturbation is a free-form Note, so only the generating agent could vouch that the code adhered. Realizations also accumulated as lasting assets instead of being regenerated.

**Mechanical checks that make adherence testable:**

1. **Structural adherence.** A realization's selector must equal the concept's grounded detector conjunction exactly, and its effect may only compose ARCGraph primitives.
2. **Regeneration stability.** Regenerate every realization from scratch in a fresh session, from the concept and the DSL alone. If the set of solved tasks changes materially, knowledge was living in the code rather than in the ontology.

### What would make the Wake ↔ Dream loop work offline

Deterministic Dream needs an **inductive operator**: a bounded, typed generator that proposes candidate subgraphs for a gap. The candidates would be new relations, bindings or program statements built from a small, complete set of general primitives. Each candidate is admitted automatically when it reproduces the demonstrations exactly and wins under a description-length criterion, with no reviewer involved. The gap's first missing layer and its type signature narrow the search. That narrowing is where the ontology earns its place: it's the thing that should beat plain brute force on ARC-AGI-2.

The recovery pilot (`search.py` plus `object_queries.py`) is a first, very small instance of exactly this operator. It builds typed relational queries and programs from demonstrations alone.

### What a new approach must guarantee

1. **Generalization must be earned at inference time.** Given 2–5 demonstrations of a new task, the loop builds the missing subgraph and its executable form itself, from primitives that don't encode any particular task.
2. **Primitives are grown only for coverage, never for a single task.** A new primitive has to be motivated by a gap census across many tasks and must pay off on tasks that weren't used to motivate it.
3. **A sealed measurement set.** Split the 120 evaluation tasks into a development half and a sealed half that no human or LLM inspects. Treat the hidden Kaggle score as the final arbiter.
4. **Provenance is a byproduct, not the work.** Keep deterministic replay and freeze-before-score. Drop closure and receipt ceremony until there is capability worth certifying.

---

## Part 2: Proposed isolated subset (provisional)

This part is provisional until an architecture is chosen. It came from a static scan, not a close reading of the code. Don't extract anything until the architecture question below is settled.

The rule is to keep code that is general by construction, extract code that is general but entangled, and exclude anything that encodes particular tasks or exists only for governance.

### Code: keep as is

| Path | Why |
|---|---|
| `experiments/object_dsl_recovery/search.py`, `object_queries.py`, `run_experiment.py`, `select_evaluation_families.py`, `freeze_suite.py`, `check_*.py`, `fixtures/` | The only inference-time synthesis loop. Small (about 1,300 lines) and honest about its limits. |
| `utils.py` | `Direction` and other enums (911 bytes). |
| `extended_transformations/rotate_grid.py`, `shift_grid.py`, `count_grid.py`, `pyramid_grid.py`, `rotate_duplicate.py`, `downscale_grid.py`, `utils.py` | No named-mode dispatch. Pure grid or geometry helpers. |

### Code: extract into a new clean module

| Source | What to take | Size |
|---|---|---|
| `ARCGraph.py` (3,680 method lines) | The 113 core methods: node attributes, the `filter_by_*` filters, the `param_bind_*` binders, the object transformations (`update_color`, `move_node`, `extend_node`, `move_node_max`, `rotate_node`, `add_border`, `fill_rectangle`, `hollow_rectangle`, `mirror`, `flip`, `insert`, `remove_node`), geometry/collision checks, `apply*`, `undo_abstraction`, `update_abstracted_graph`. | About 1,830 lines |
| `ARCGraph.py`: what to leave out | The 27 `extended_transformations` imports and the grid-method wrappers (about 1,000 lines), `duplicate` (482 lines), the `fit_*` / `connect_aligned_*` cavity/corridor helpers (about 570 lines), rdflib `runtime_registry` hooks, scene-contract binding, cooperative-stop plumbing. | |
| `image.py` (1,384 lines) | The abstraction constructors (`get_*_graph`: nbccg, ccg, ccgbr, mcccg, na, lrg, nbvcg, nbhcg, occlusion), `graph_from_grid`, `init_from_grid`, `undo_abstraction`. Leave out the canvas-context and symmetry detectors, and the background-binding contract. | About 500 lines |
| `connectors/schema.py`, `connectors/dsl_shadows.py`, `ontology/dsl_schema.py` | The typed signatures for the 39 transformations, 11 filter families and 8 binder families. This is the "connector representation" the North Star asks for. Cut the dependency on `dsl_connector_audit`. | About 40 KB |

Three things to review before including them, since they may carry extensions: `filter_by_fit`, `filter_by_occlusion`, `param_bind_aligned_node_by_color`, `insert` (88 lines) and `update_abstracted_graph` (98 lines), plus a scan of `connectors/typed_gkat_ir.py` in case a guarded-program IR is wanted later.

**Search loop:** ARGA's original best-first search with tabu and constraints is still inside `task.py`, but it's tangled into 11,883 lines of Dream, realization and submission logic. It would be cleaner to re-derive it from the published upstream ARGA code than to extract it from here.

### Code: exclude

`dsl.py`, `heuristics.py`, `task.py`, `main.py`, the named-mode grid transforms (`fill_grid`, `basic_grid`, `beam_grid`, `magnet_grid`, `recolor_grid`, `crop_grid`, `extract_grid`, `summary_grid`, `symmetry_grid`, `tile_grid`, `overlay_grid`, `placement_grid`, `truncate_grid`, `upscale_grid`, `connect_grid`, `neighborhood_grid`, `mirror_grid`, `squeeze_grid`, `arbitrary_duplicate_grid`), every task-named `connectors/*.py` executor and every `native_*_actions.py`, all `ontology/*.ttl` and receipt JSON, and every `dream_*`, `wake_*`, `audit_*`, `realiz*`, `lifetime_*`, `cohort_*`, `build_*`, `prepare_*` and Assistant module, along with the rule libraries, `_goal_runs/` and `reports/`.

`mirror_grid` and `upscale_grid` are small but dispatch on 8–9 named modes. If they turn out to be needed, rewrite them as plain D4 and scale operations rather than keeping them.

### Guiding docs

| Keep | Use |
|---|---|
| `docs/OBJECT_DSL_RECOVERY_NORTH_STAR.md` | The primary direction. |
| This file | Failure modes and the constraints above. |
| `experiments/object_dsl_verification/theoretical_soundness_assessment_v1.md` | An honest statement of the fragment's limits, with a minimal audit list. |
| `experiments/object_dsl_recovery/README.md` and `RESULTS.md` | Experiment protocol and preserved failures. Trim the Kaggle-parity narrative. |
| `docs/KAGGLE_VERIFICATION_HANDOFF.md`, "Correct populations" section only | Corpus identity facts. |
| Excerpt of `PIPELINE_GOVERNING_OBJECTIVES.md` | Only "Generalization before local success" (the first paragraph), task IDs as provenance only, and deterministic reproducibility. |
| Excerpt of `NO_MAGIC_DREAM_PROTOCOL.md` | Only the "Prohibited shortcuts" list. |

Exclude: `VERTICAL_CLOSURE_*` (96 KB), `LIFETIME_LEARNING_ARCHITECTURE`, `WINDOWS_PIPELINE_OPERATING_MANUAL`, `ASSISTANT_CAPABILITY_GAP_UI_CONTRACT`, `GENERAL_SYMBOLIC_REASONER_SHADOW`, `GLOBAL_CROSS_LAYER_SHADOW_CLASSIFIER`, `RDR_BACKGROUND_BACKTRACKING_GOAL`, `PORTABLE_PIPELINE_DECISIONS`, `INCREMENTAL_WAKE_PROVENANCE`, `dream_family_observation_store`, `reuse_remap_logging`. Keep the `evaluation_replication_*` files only as the cautionary record behind F1.

### Estimated size

About 5,000 lines of Python in roughly 15 files, plus about 6 short docs. Compare 16.6 MB and 668 files at the repo root. The extracted `ARCGraph` core must reproduce the pilot's frozen 2/172 predictions exactly before any new work starts on top of it.

---

## Part 3: Why the Brain–Blood Barrier (BBB) was not enforced

Sources: `KNOWLEDGE_MODEL.md` (Brain-Blood Barrier Policy), `SOURCE_AUTHORITY.md`, `README.md`, `ontology/README.md`, `tests/test_brain_blood_barrier.py`, `ontology/brain_literal_audit.py`, `ontology/runtime_integrity.py` (`assert_wake_runtime_authorized`), `ontology/brain_literal_contracts.json` and `ontology/executor_parameter_contracts.json`. The dates below are file modification times.

### The policy itself is sound and covers the failure

"Code implements mechanisms. Ontology declares every assumption that can change interpretation, abstraction, inference, candidate generation, pruning, mapping, or ranking." It requires that "every executable abstraction, filter, transformation, selector, binder, and rule that can affect wake must resolve to one ontology contract". It also forbids "an opaque task-specific executable patch". As written, the per-task grid modes and connector executors are all violations.

### How the implementation let them through

1. **Enforcement worked per callable, while the knowledge sat inside callables.** A contract binds a callable's name, signature, digest and fixtures. `fill_grid` is one transformation with one contract, but inside it is 152 behaviors, selected by the string value of its `object` parameter. The digest check proves the code hasn't changed since it was registered; it says nothing about whether the code contains knowledge. The knowledge moved into parameter values and branch bodies, where a per-callable contract can't see it.
2. **The audit scope excluded the code that carried the knowledge.** `brain_literal_audit.PYTHON_GLOBS` covers `connectors/`, `detectors/`, `wake/rules/`, `ontology/` and three scripts. It does not cover `dsl.py` (541 KB), `task.py` (554 KB), `extended_transformations/` (about 1.1 MB), `heuristics.py`, `ARCGraph.py` or `image.py`. `test_brain_blood_barrier.py` (9 tests) and the Wake gate check only the runtime registry (semantic priors, `Image` abstraction constructors, the transformation-name inventory) and that DSL entries have interface mappings. None of them looks at what a transformation does.
3. **The literal audit is written to report, not block, and its contracts are empty.** It outputs `status: capability_gap`, not a failure, and its only blocking condition is "no new gaps compared with a previous audit". Nothing in `task.py`, `main.py`, `dsl.py` or `runtime_integrity.py` references it. `brain_literal_contracts.json` has empty `literal_bindings`, `path_bindings` and `lowering_bindings`, and `executor_parameter_contracts.json` has empty role maps. With empty contracts every literal is "unbound debt". The policy itself allows existing debt ("Initial audits may report existing … priors … as explicit debt"), so whatever existed when the audit started was grandfathered. Because the comparison baseline is whichever previous audit is passed in, one re-run is enough to turn new gaps into existing ones. That depends on how it was actually run, and should be checked.
4. **Ordering.** The named-mode grid transforms were last modified on 2026-07-01. The BBB tests and contracts date from 2026-07-18. The grid transforms therefore entered as grandfathered debt. `dsl.py` (09 Aug) and `task.py` (22 Aug) kept growing outside the audit scope. The roughly 110 connector executors (mid-August) are inside the scope but fall under the report-only gate.
5. **Self-attestation.** The Python realization boundary is "the implemented operation must be recoverable as connector metadata" (`CONNECTOR_SPECS`). The same agent writes the metadata and the code, and nothing checks that the two describe the same behavior. The DSL shadows themselves still record behavioral agreement as `pending_representative_cases`.
6. **The tests check the checker, not the codebase.** The BBB tests confirm that the registry is immutable, that a digest mismatch fails and that a hidden abstraction op is caught. All of these are synthetic tampering scenarios. None of them lists the code Wake can actually reach and asserts that it complies. A large, passing suite of such tests signals rigor while leaving the invariant unchecked.
7. **The "medication" loophole.** Code edits are allowed if they restore "an already represented connector contract". Adding a mode to `fill_grid` can be framed as working inside the existing `fill_grid` contract.

### What would prevent a repeat

1. **Realizations are data, not Python.** Solutions are DSL program trees stored as ontology-bound data and run by one fixed interpreter. Python then consists only of the interpreter plus a closed set of primitives. With that separation, knowledge in Python becomes structurally impossible rather than something to detect.
2. **A frozen, human-owned primitive set.** Primitives are hash-pinned. Changing one requires a human-approved medication record plus unchanged behavior fixtures. No string-valued dispatch parameters are allowed: every parameter is typed to an ontology value domain (color, direction, count, shape, …).
3. **Scope is the import closure of the Wake and Dream entry points, computed automatically.** Every reachable Python file is audited. Nothing is in scope by glob.
4. **Gates fail rather than report.** Debt has an owner and an expiry, and it can only shrink. The baseline is pinned by a human, never re-baselined by the implementing agent. The Wake entry point refuses to run if the gate hasn't passed.
5. **Behavioral probes instead of attestations:** rename invariance, concept deletion, regeneration stability, plus a check that fails any wake-reachable function that branches on string literal values beyond a small bound.
6. **The tests target the actual codebase.** For example: list every callable Wake can reach and assert it belongs to the frozen primitive set; assert the Blood's line count stays within a pinned budget.

---

## Part 4: The role of GKAT, and why it didn't protect the induction

**Intended role (per the author).** Nondeterministic DSL program induction relies on GKAT (guarded Kleene algebra with tests) for logical consistency, soundness and decidability.

**What GKAT provides.** Programs are guarded choice (`if b then e else f`) and guarded loops (`while b do e`) over a Boolean algebra of tests and a set of uninterpreted actions. For that fragment, program equivalence is decidable in nearly linear time (Smolka, Foster, Hsu, Kappé, Kozen, Silva, POPL 2020). For induction this gives:

- a canonical form, so equivalent candidate programs collapse and search pruning is sound;
- detection of unsatisfiable or overlapping guards, i.e. consistency of RDR exceptions;
- rewriting that provably preserves equivalence, so RDR-forest compression (the MDL objective) can't change behavior.

**What GKAT can't provide.** Its guarantees hold *relative to* an interpretation of the atoms. It treats actions as uninterpreted and assumes the tests form a Boolean algebra. It can't show that an action means what its ontology concept says, and it can't find knowledge hidden inside an atom. If each action is a whole-task executor, GKAT reasoning stays sound but has nothing to act on: every program is a single guarded action.

**What exists in the repo** (`connectors/typed_gkat_ir.py`, v1). The IR is "deliberately finite and loop-free", a straight-line typed sequence of test conjunctions and actions, checked only for type chaining. It has no guarded union, no `while`, and no equivalence procedure. Its actions call into the native action registry and legacy composition runtime ("execute_delegating_shadow"). The decidability, consistency and compression properties the design relies on were therefore never implemented.

**Relationship to the BBB.** The BBB is the precondition that gives GKAT something to work on. Only when atoms are small, frozen, typed primitives and deterministic detector tests does GKAT's algebra carry the knowledge. The two need to be built together.

**Concrete example.** The pilot's `slide_node` macro is really `while (in_bounds ∧ swept_clear ∧ ¬collision) do move_unit`, a GKAT loop over one primitive action and three primitive tests. Written that way, it would be inspectable data, comparable against other programs, and would need no new Python.

**For the isolated core:**

- Implement GKAT expressions with guarded union and while.
- Add an equivalence check using GKAT automata or bisimulation.
- Deduplicate induction candidates by canonical form.
- Define RDR compression as rewriting to smaller equivalent expressions.
- Check that each detector test is a total, deterministic predicate, so that the Boolean-algebra assumption holds on fixtures.
