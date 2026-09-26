# Recovery north star — 23 September 2026

Saved at the user's explicit request: “Save last few turns of this chat as a
guiding ‘north star’ light.” The conversation below is the basis for this work.
This document guides implementation choices; it does not declare that the
intended architecture or any acceptance milestone has already been achieved.

## Intended purpose

Recover compositional generalization by combining the domain's abstract-object
DSL with the connector representation of **the same executable semantics**.
The DSL supplies useful objects, properties, relations and operations for
abduction. The connector representation supports their composition and checking.
Neither is an independent substitute for the other.

The unit of progress is an end-to-end capability: infer a reusable program from
demonstrations, execute it over abstract objects, and transfer it to unseen
configurations. Refactoring a fixed Python recipe, creating a shadow declaration,
increasing an audit counter, or replaying a known answer does not establish this.

## Working commitments

1. Reuse the surviving object abstractions and DSL operations. Do not replace
   abstraction with family-specific grid probes disguised as atoms.
2. Keep executable programs, connector representations and actual intermediate
   object states connected. State honestly which semantics remain unchecked.
3. Let demonstrations drive bounded abductive search. Do not hand the solver a
   complete solution recipe, task-ID dispatch or held-out answers.
4. Define the evaluation population, resource limits and success conditions
   before the experiment. Preserve failures and unresolved cases. Do not replace
   failed tests with easier ones or expand the architecture to postpone a decision.
5. Demonstrate a small complete capability before scaling migration. A small
   supported DSL fragment is acceptable; sacrificing the end goal is not.
6. Measure transfer across object shapes, positions, counts and applicable
   relational bindings. Distinguish synthetic evidence, real ARC results,
   regression preservation, deployment readiness and hidden-score improvement.
7. Keep full-library coverage and eventual removal of the old-library fallback
   as goals. A pilot must execute without that fallback, while remaining isolated
   from the deployed baseline until integration is supported.
8. Use checks to expose actual defects. Do not make completion of the entire
   future pipeline a circular prerequisite for an honest, limited experiment.
9. Advance toward an executable result. Documentation and local mechanism repair
   are supporting work, not replacements for the result.

## Conversation preserved

### User

> Is there any feasible path to recover some of Indended purpose from the current repo?

### Assistant

**Yes. The repository still contains enough of the intended architecture for a credible recovery experiment. Full recovery is not yet demonstrated.**

I found three useful foundations:

- **Object-level DSL operations remain.** `ARCGraph.py` selects graph nodes by attributes; `update_color` changes a node’s color.
- **Graph-program execution remains.** `dsl.py` constructs an abstraction, applies a sequence of operations, and reconstructs the grid.
- **Shadows already reference those operations.** However, their own metadata says signature agreement is verified while behavioral agreement remains pending.

The crucial gap is connecting these foundations into **search over meaningful abstract programs**. The connector search inspected combines declared logical facts. That alone does not establish that it can discover object transformations from demonstrations.

I recommend this bounded recovery path:

1. **Reconnect a small object DSL to its shadows.** Use existing component abstractions, filters, relational bindings, and two or three transformations. Both execution paths must represent the same program and agree on intermediate object states.
2. **Restore abductive program discovery within that fragment.** Infer candidate programs from demonstrations, with explicit limits on program length and search work. A complete family-specific Python solution must not masquerade as one primitive.
3. **Test previously unseen compositions.** Freeze test cases before development; vary object shapes, positions, and counts. Require the system to discover and execute combinations that were not supplied as complete recipes, without the old-library fallback.

**The first meaningful recovery result would be an automatically discovered abstract program that transfers to withheld configurations and has a matching shadow execution.** Reproducing an existing answer through another fixed recipe would not meet that criterion.

I would make this a capped feasibility experiment before expanding migration across the 552 rules. Existing regression evidence and Kaggle packaging remain useful afterward. A positive Kaggle score remains unproved.

This assessment comes from source inspection; I have not run or claimed that recovery experiment.

### User

> Can you continue the intended effort without architectural theatre and micro-targeting low level behavior at expense of implementation convergence? Can you demonstrate limited success without sacrificing the end goal?

### Assistant — commitment before implementation

> I’ll build a bounded demonstration of the intended path: discover a short program over abstract objects, execute that same program through its connector representation, and test it on withheld configurations. I’ll use the result to decide whether this approach warrants further work.

### User

> Save  last few turns of this chat as a guiding "north star" light.

The assistant answer above retains its wording; repository links were shortened
to filenames for this saved transcript. Subsequent results must be recorded as
results, not edited into these historical statements.

## Concrete experiment

### User clarification — real ARC2 families are required

> You must select the families from ARC2 evaluation dataset for your experiments in order to avoid trivial cases. The tasks you used to demonstrate earlier progress was trivial color map excersize.

This clarification governs the experiment. Synthetic fixtures are implementation
controls only. Families must be selected from the actual ARC2 evaluation dataset
using training evidence, before looking at held-out results. Simple color-map
exercises do not qualify as recovery progress. A qualifying result must address
nontrivial object relationships or dependent transformations. Confirm the corpus
identity rather than treating any 240-task file as ARC2 evaluation.

See `experiments/object_dsl_recovery/README.md`. Its first result must report
learned programs, withheld predictions, intermediate-state execution agreement,
actual work consumed, and remaining limitations. Full authority acceptance and
Kaggle success must never be inferred from this pilot alone.
