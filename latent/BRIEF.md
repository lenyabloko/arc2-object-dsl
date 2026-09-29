# Brief: build robust, generic G-DSL primitives (ARC-AGI-2)

Goal: raise solves on the 1000 training tasks + dev-eval half A with GENERIC primitives, written from scratch in our own code (do NOT import or copy Codex code under /home/claude/work/codex or cand2; you may read it for ideas only, but prefer your own clean design).

## Interface
Write ONE module /home/claude/work/latent/fam_<AREA>.py that defines `FAMILIES = (fam_a, fam_b, ...)`.
Each `fam_x(train)` receives the task's training pairs (list of {"input","output"} grids, lists of lists of ints) and yields `(name, cost, fn)` where `fn(grid) -> grid` (or None). Names like "project:intersect[rows=left,cols=top]". cost: 3-6 (higher = more parameters).
You may `import gdsl` (sys.path /home/claude/work/widen) for helpers: bg_of, objects(g,bg,diag,by_colour), bbox, crop, colours, H, W, dihedral fns, split_panels, static_colours, etc. Read /home/claude/work/widen/gdsl.py first to avoid duplicating existing families.
The search harness verifies every program on ALL training pairs (optionally followed by a global colour map), so a program only counts when exact.

## Hard rules (BBB: no task-specific code)
- Every parameter must be INDUCED from the training pairs (colours seen, roles such as background / marker / most-frequent / new-in-output colour, sizes, directions from a small enumerated set). No literal task colours, sizes or positions chosen because one task needs them. Enumerate small generic domains instead (4 edges, 4/8 directions, colour roles).
- A primitive is only worth keeping if it is a real concept that plausibly recurs: it must solve >= 2 training tasks, OR be the obvious general form of a rule (e.g. "markers on any edge project lines; combine by intersection/union") rather than a special case.
- Keep yield counts bounded (<= ~60 programs per family per task) and fast (a task's whole family run < 2 s). Return None quickly when preconditions fail (check shapes on train[0] first).
- Over-firing matters: a program that fits training but is wrong on test counts against you. Prefer precise preconditions.
- Use ONLY training tasks and dev-eval half A (ids in /home/claude/work/widen/deval_a.txt) for motivation. Never read /home/claude/work/widen/deval_b.txt or tasks outside those sets. Never look at test outputs while designing; the harness scores them.

## Data
- Tasks: /kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json (train/test inputs); evaluation file for half A.
- Claude's per-task readings of unsolved tasks, by capability: /home/claude/work/latent/unsolved_by_capability.json  ({capability: [{task, rule, conf, feasible, halfA}]}). Use them to find recurring mechanisms; verify against real grids.
- Visual sheets exist in /home/claude/work/s0/sheetsU/uNNN.png (index in sheetsU/index.json) if you want to look.

## Evaluate
`cd /home/claude/work/latent && python3 eval_fam.py fam_<AREA>.py out_<AREA>.jsonl`  (≈1-3 min; the machine has 2 cores shared with other agents — never run more than one eval at a time, and use the optional 3rd arg, a comma list of task ids, for quick iteration).
Output: exact count, NEW solves (not solved by the current system), WRONG (fit training but wrong test).

## Report (final reply, compact)
Families implemented (one line each: concept, parameters induced), exact / new / wrong counts from the full eval, the list of NEW task ids, and any family you dropped because it only fit one task or over-fired.

## Group contract (supersedes the "capabilities" framing above)
You are assigned ONE mechanism group from /home/claude/work/s0/taskan/mechanism_ontology.json (subclasses[<id>]: definition, parameters, detector, primitive_sketch, coverage_risk, tasks). The reviewer's requirement: the primitive must cover the ENTIRE group — one parametrised primitive (parameters induced per task from training pairs) that solves every member. Work toward full coverage; iterate with
`python3 eval_fam.py fam_<id>.py out_<id>.jsonl <comma-separated member ids>`
and run the full evaluation (no 3rd arg) ONCE at the end to measure over-firing on all tasks.
If some members genuinely need a different mechanism, do not special-case them: report them as "split out" with a one-line reason (that becomes a regrouping decision). File name: fam_<id with dots replaced by _>.py. Scratch files: /tmp/claude-0/<id>/ only.
Final report: coverage k/n on the group (list uncovered + reason), full-eval exact/new/WRONG counts, any extra tasks solved outside the group.

## Pass 3 addendum: half A comes first
Groups now also contain dev-eval half-A tasks (held-out style, the ones that matter for the hidden test). They are listed per group in /home/claude/work/s0/taskan/halfA_placement.json ("readings": [{task, subclass, mechanism, fit_note, ...}]). Their grids are in arc-agi_evaluation_challenges.json (training pairs + test inputs only; NEVER open the solutions file). eval_fam.py already scores half A. Covering the half-A members is the priority; training members are the second priority. Report half-A coverage separately.
