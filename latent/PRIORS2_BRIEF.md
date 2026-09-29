# Priors enrichment lane, round 2: common-sense physics, analogies and foundational mathematics

Read /home/claude/work/latent/PRIORS_BRIEF.md and /home/claude/work/latent/BRIEF.md first (interface, evaluation, rules).
Existing priors already implemented (do NOT duplicate; import their helpers if useful): prior_topology.py, prior_geometry.py, prior_combinatorics.py and the group modules fam_*.py in /home/claude/work/latent.

## Lesson from the last cycle (important)
Primitives written for single tasks solved those tasks but transferred to ZERO held-out tasks (held-out half B stayed at 1/49).
So in this round a family is kept ONLY if it solves >= 3 distinct tasks (training + half A) in the full eval, with WRONG = 0.
Design from the prior (the physics / mathematics), not from a task: state the prior's laws and search space at the top of the file, then look for tasks it explains.

## Domains (you get one)
- OPTICS: optical occlusion and layering — depth order inferred from overlaps (which colour/object is in front), re-layering (bring to front/back), amodal completion of partly hidden shapes (continue edges, rectangles, lines behind occluders), transparency, shadows/projections of objects onto walls or along a light direction.
- MECHANICS: mechanical equilibrium — gravity with support (rigid objects fall until supported, collisions, piling), stacks (LIFO order, towers, sorted stacking against a wall), balance; common-sense machines: "key and keyhole" (lock/key complementarity: a shape fits a cavity, possibly rotated), "slot machine" (rows/columns/reels shift cyclically until a target line aligns), levers/pushing (an object pushes others along its motion).
- FLUIDS: fluid flow — sources pour, liquid falls under gravity, spreads along surfaces, fills containers up to the spill level, flows around obstacles and leaks through gaps; diffusion/infection spreading from sources with barriers; flood fill with sources and sinks.
- ACTION: principle of least action and conservation laws — shortest/least-cost paths on the grid with obstacles; minimal-displacement matching of input objects to output positions (assignment); conservation of cell counts / colours / object counts / "mass" used as a constraint that turns a transformation into a rearrangement search; equilibrium (balanced) configurations.
- ARITHMETIC: foundational arithmetic and set theory — parity (odd/even positions, sizes, counts), modular patterns ((x+y) mod k, periodicity), counting arithmetic (sum/difference/product of counts setting output size or number of marks), comparisons (more/less/equal), divisibility, set operations on objects/panels/colour sets (union, intersection, difference, symmetric difference, complement).

Write /home/claude/work/latent/prior_<domain lowercase>.py. Scratch: /tmp/claude-0/prior_<domain>/. Two shared cores: iterate on subsets, one full eval at the end.
Report: laws/search space, families kept (each with its >= 3 solved tasks), full-eval exact/new/WRONG, NEW ids (half A marked), families dropped for solving < 3 tasks.
