# Composition engines (Dream lane 3): make the library fire on held-out tasks

## Why
The library (150+ G-DSL families in /home/claude/work/widen/gdsl.py, which imports fam_*.py and prior_*.py) now solves ~500/1000 training tasks and 34/50 half-A tasks, but fits (on training pairs) only 1 of 49 held-out half-B tasks and 0 of 21 sealed ones. Every family is a monolithic input->output mechanism; ARC-AGI-2 held-out tasks compose 2-4 concepts. Your engine must COMPOSE existing operators, not add another monolithic family.

## Interface
Write /home/claude/work/latent/compose_<name>.py defining `SEARCH(task) -> list of {"program": str, "preds": [grid per test input]}` (best first; at most 3), using `import gdsl` (sys.path /home/claude/work/widen) and its library:
- `gdsl.candidates(train)` -> list of (name, cost, fn) for every family program on these pairs (can take ~1-5 s; cache per task);
- `gdsl.search(task, max_programs=6, allow2=False)` -> verified single-step programs for a task dict {"train":[{input,output}], "test":[{input}]}; `gdsl.run(fn, grid)` safe apply; helpers objects(), bg_of(), split_panels(), bbox(), crop(), D8 transforms etc.
Every returned program MUST reproduce all training pairs exactly. Budget: <= 25 s per task wall-clock on one core (check time and stop early); the whole harness uses a 30 s alarm.

## Evaluate (transfer-aware)
`cd /home/claude/work/latent && python3 eval_fam2.py compose_<name>.py out_compose_<name>.jsonl`
It reports ARC-1-origin training, N1 (design half of the 233 ARC-AGI-2-new training tasks, ids in novel_N1.txt), half A, and N2 (validation half, COUNTS ONLY). N2 "fit" and "exact" counts are the transfer signal you should try to raise; never try to discover N2 ids and never read /home/claude/work/widen/novel_N2.txt or deval_b.txt. WRONG (fit train but wrong test) must be low; report it per split.
Iterate on subsets (pass a comma list of ids as a quick test by writing a small driver, or temporarily restrict keys), full eval at most 3 times (2 shared cores; other agents are running).

## Rules
No task-specific code; parameters induced from training pairs; no Codex code; never look at test outputs.
Report: engine design (search space, pruning, budget), full-eval lines for all four splits, NEW ids in ARC1/N1/half A, and what limits N2.

## Important property of the library
Many newer families (fam_*.py, prior_*.py) induce their parameters FROM the given pairs and only yield programs that reproduce those pairs' outputs. They therefore work as a LAST step (call gdsl.candidates / gdsl.search on (intermediate, output) pairs), but not as a free first step. The older gdsl families (geometric, tile, scale, crop, panels, symmetry, gravity, fill_enclosed, object_filter, rays, connect, outline, colour-map ...) yield output-independent transforms and can serve as first steps. Design around this: e.g. residual search = cheap first steps (or segment/select) + library search on the residual pairs; lifting = run the full library on part-level pairs; object mapping = learn per-object actions directly.
