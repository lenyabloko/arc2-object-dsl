# Dream cycle 18: close composition gaps on the design-unsolved set, generically

## Why
V19 = library (152 G-DSL families) + composition fallback (compose_objmap, then compose_lift). It solves 570/1000 training tasks, 36/50 of dev-eval half A, and on the held-out public-eval tasks only 1/49 (half B) and 1/21 (sealed). The first sealed solve came from composition, so composition is the lever. The design set of tasks that V19 still fails is in `/home/claude/work/latent/design_unsolved_v19.json`: 85 N1 tasks (ARC-AGI-2-new training tasks, design half) and 14 half-A tasks. Their abstract readings are in `/home/claude/work/s0/taskan/abs_all.json` (`mechanism`, `roles`, `op_chain` per task id); use them as hints for what the tasks need, then look at the training pairs yourself.

## Your lane
The lane is named in the request that points you to this brief:
- **Lane A: `compose_objmap2.py`.** Copy `compose_objmap.py` (do not edit the original) and extend it.
- **Lane B: `compose_ctx.py`.** Write a new engine for inter-part context (see below).
Put the file in `/home/claude/work/latent/`.

### Lane A: object-correspondence gaps
1. Diagnose first. Run `compose_objmap.py` with its DIAG/DEBUG facilities on the design-unsolved tasks, and for each task record where it fails: segmentation, correspondence, missing action descriptor, rule learning, render, or verification.
2. Tally the failure points. Implement generic additions for the most frequent gaps. Examples of what the readings suggest (choose from your own diagnosis, not from this list):
   - template stamping: a template object, D8 and/or scaled, is copied onto marker objects, aligned by a shared colour or cell;
   - per-object shape edits in the object frame: shrink or grow by one layer, erase the first k rows or columns, split across a marker stripe, remove a protrusion;
   - relayering overlapping objects by an induced priority;
   - per-attribute CASE with different mechanisms per case.
3. Keep every existing guard: MDL acceptance, novelty guard, and verification on all training pairs.

### Lane B: inter-part context (`compose_ctx.py`)
Many design-unsolved tasks change a part (panel, band, framed region, object) as a function of ANOTHER part: a template panel copied to marked panels; keys stamped scaled into a frame; band i recoloured by band i+1; panel contents swapped; a progression continued from the previous two panels; a key panel that decodes an arrangement.

Learn `part_out = OP(part_in, ctx)`, optionally followed by a library program on the part level.
- `ctx` is another part chosen by a ROLE rule induced from the training pairs. Examples: the unique non-empty or most complex part (template); the part that never changes (key); the next or previous part in reading or cyclic order; the mirror part; the part in the same row or column; the part holding a marker colour.
- `OP` is drawn from a small set of binary operators. Examples: copy ctx; overlay ctx over part or part over ctx; stamp ctx where the part has its marker; recolour ctx with the part's colour(s); swap; fill the part's background with ctx's colour; progression step (part_k+1 = part_k + (part_k - part_k-1)); boolean and/or/xor.
- Output assembly: the same layout (in place), or a selected part.
- Reuse the partition code of `compose_lift.py` by importing it (`import compose_lift as L`: `partition`, `Part`, `sep_layout`, `part_bgsep`, `part_frame`, `part_obj` ...).
- Check what lift's PANELMAP and SELECT already cover, so you don't duplicate them.
- Use a leave-one-out generalisation check as in lift (`loo_filter`).

## Interface and hard requirements (both lanes)
- `SEARCH(task) -> list of {"program": str, "preds": [grid per test input]}`, best first, at most 3.
- Every program must reproduce ALL training pairs exactly.
- Use the library via `import gdsl` (sys.path `/home/claude/work/widen`): `gdsl.candidates(train)`, `gdsl.search(task, max_programs=6, allow2=False)`, `gdsl.run`, helpers. The library families induce parameters from the pairs they are given, so use them as the LAST step on (intermediate, output) pairs.
- **Determinism is mandatory:** Kaggle parity needs byte-identical predictions on any machine under any load.
  - Use NO clock, timer or signal anywhere: no `time.time`, no `perf_counter`, no `SIGALRM` in the engine.
  - Bound all search by a deterministic WORK budget: a counter advanced at natural units of work, with data-dependent costs. Copy the mechanism of `compose_lift.py` (`tick`, `Budget`, `work_cap`, `SEC`) or of `compose_objmap.py`.
  - Calibrate for at most about 20 s of work per task on this machine.
- No task-specific code: no task ids and no literal task constants. Every colour, vector, role and table entry is induced from the training pairs. No Codex code. Never inspect test outputs while designing.
- Never read `/home/claude/work/widen/novel_N2.txt` or `deval_b.txt`, and never try to discover N2, half-B or sealed ids.

## Evaluate
The machine has 2 cores and another agent may be running, so use 1 worker.
- **Quick design loop:**
  ```
  cd /home/claude/work/latent && python3 eval_subset.py <engine>.py <baseline> --design --regress 60 --workers 1
  ```
  - Lane A baseline: `baselines/c16_objmap_det.jsonl.txt`.
  - Lane B baseline: `baselines/c16_lift_det.jsonl.txt`. There, "LOST" only matters for tasks your engine is meant to cover; report it anyway.
  - `--ids a,b,c` runs specific design tasks.
- **Full transfer-aware eval: once, at the end only:**
  ```
  EVAL_WORKERS=1 EVAL_TIMEOUT=60 python3 eval_fam2.py <engine>.py out_<engine>.jsonl
  ```
  It prints ARC1 / N1 / half A with ids, and N2 as COUNTS ONLY. The N2 exact and fit counts are the transfer signal. WRONG (fits training, test wrong) must stay low.
  - The run takes about 1–1.5 h on 1 worker. Start it with `nohup … > full_<engine>.log 2>&1 &` and poll with short sleeps (at most 4–5 minutes per tool call). Never block one tool call on the whole run.
- **Determinism proof:**
  1. Run the engine on 30 design and regression tasks twice: once normally, once with a CPU hog in parallel (`python3 -c "while True: pass" &`, then kill it by its exact PID).
  2. Show that the sha256 of the JSON predictions is identical.
  3. Report the maximum per-task runtime.

## Robustness
The session machine can restart at any moment. That kills background processes but keeps files.
- Keep `NOTES_<engine>.md` in `/home/claude/work/latent` up to date: design, status, the last eval lines, and what's next. Update it after every significant step.
- Kill processes only by exact PID. Never use broad `pkill -f` patterns: they kill your own shell.

## Report (final message)
- The engine design: search space, pruning, work budget.
- The design-set lines: `design` and `regress`, with NEW and LOST ids.
- The full-eval lines for all four splits: N2 counts only.
- The determinism proof.
- What still limits the design-unsolved tasks, ranked.
