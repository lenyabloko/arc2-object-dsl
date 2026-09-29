# Priors enrichment lane (Dream, prior-driven rather than group-driven)

Group-driven primitives only cover mechanisms seen in training groups. The hidden ARC-AGI-2 test needs PRIORS we don't have yet.
Your job: use your own knowledge of mathematics to add a missing prior as a GENERAL SEARCH ALGORITHM — not mined from one task — then measure what it solves.

Domains (you are assigned one):
- TOPOLOGY: invariants under continuous deformation — connectivity, holes/genus, containment (inside/outside trees), adjacency graphs of regions, boundary/interior, path-connectedness, homeomorphism classes of shapes (e.g. match/recolour/select objects by topological class, fill by winding/containment, graph isomorphism between region-adjacency graphs of input and output).
- GEOMETRY: symmetry groups and transformations — full/partial/local symmetry detection with arbitrary centres and axes (incl. half-integer), glide reflections, translational lattices, rotation orbits of objects, affine maps (scale+shear), projective alignment, distances/convexity/hulls.
- COMBINATORICS: permutations and orderings — output as a permutation of input parts (objects, rows, columns, panels, colours), permutations inferred from sort keys or from a legend, cyclic shifts, permutation composition across pairs, counting/matching (bipartite matchings between objects), set operations on parts.

## How
- Implement in /home/claude/work/latent/prior_<domain>.py with FAMILIES = (...) in the G-DSL interface (see /home/claude/work/latent/BRIEF.md: fam(train) yields (name, cost, fn)). All parameters induced from training pairs; no task-specific constants.
- Design the prior first (write the concept + search space at the top of the file), then search for ARC tasks it explains, using the unsolved lists: /home/claude/work/s0/taskan/mechanism_ontology.json (residual groups especially: ids ending in '.residual', and uncovered members) and half-A (/home/claude/work/s0/taskan/halfA_placement.json). Half-A is the priority because it resembles the hidden test.
- Evaluate: cd /home/claude/work/latent && python3 eval_fam.py prior_<domain>.py out_prior_<domain>.jsonl  [comma-list of ids for quick runs]. WRONG (fit train, wrong test) must be 0 at the end.
- Rules: training + half-A only (never read deval_b.txt), never look at test outputs, no Codex code.
Report: the prior(s) implemented (concept, search space), full-eval exact/new/WRONG, NEW ids (half-A ones highlighted), and which residual tasks it explains.
