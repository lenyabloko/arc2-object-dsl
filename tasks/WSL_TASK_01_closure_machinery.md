# WSL Task 01 — compute and plumbing for the two-way vertical closure

Owner: WSL Claude (runs while waiting for the daily Kaggle slot). Designer/reviewer: the cloud session.
The cloud session decides what is admitted; you build and run well-specified machinery and report numbers.

## Hard rules
1. **Work only in `~/arc/wsl_work/`** (create it; copy files there). Never edit, commit or run git in
   `~/arc/arc2-object-dsl` except `git pull` — the outbox sync resets that clone and would destroy your work.
2. Kaggle duty first: if a UTC day has no submission yet, run `bash submission/daily_submit.sh` (see
   `submission/WSL_CLAUDE.md`) before or between these tasks.
3. **Never evaluate on the sealed tasks.** Their ids are in
   `/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/private/sealed_ids_EXCLUDE.txt`; skip them everywhere,
   do not print or copy that file.
4. No task-specific code: no task ids, hard-coded colours, or per-task branches in anything you write.
   Do not change the semantics of `occupancy2*.py`; do not add concepts yourself.
5. Deliverables go to `/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/wsl_results/<task>/`
   (code + results + a short `REPORT.md`). Do not push to GitHub.
6. Codex sources are read-only at `/mnt/c/Users/lenya/arc_extended_arga` (detectors/, wake/, ontology/, root *.py).

## T1 — S0 atom extent sweep (full scale)
- Load every public `*_evidence` function in `detectors/*.py` (Codex repo root on `sys.path`; `tools/wsl_tasks/atoms_eval_reference.py`
  shows the loader). One-argument functions take an input grid; two-argument functions take (input, output).
- Population: every training pair of all 1000 ARC-AGI-2 training tasks, and every training pair of the 99 non-sealed
  evaluation tasks (inputs for 1-arg atoms; input/output pairs for 2-arg atoms). Grid ids = order of
  (split, sorted task id, pair index). Data: the competition files (`kaggle competitions download -c arc-prize-2026-arc-agi-2`).
- Per call: 0.3 s timeout; exceptions count as not fired. Use 4 worker processes.
- For each atom write one JSONL row: `atom`, `arity`, `fired` (grid ids), `evidence_digest` per fired grid
  (sha1 of `json.dumps(ev, sort_keys=True, default=str)`, first 10 hex), `cells` per fired grid = the union of all
  (row, col) integer pairs found anywhere in the evidence payload that lie inside the grid (lists/tuples/sets of pairs,
  or dicts with `row`/`col` keys), `ms` mean time, `errors`.
- **Acceptance:** on the 1,265-grid reference population (`results/reference/population_meta.json`), the fired sets
  of the 1,032 one-argument atoms must equal `results/reference/atoms_fired_reference.json` (report any mismatches).
- Deliver `wsl_results/T1/atoms_full.jsonl.gz`, the script, `REPORT.md` (counts, timing, mismatches).

## T2 — digest-keyed stratum cache (library + tests)
- `strata_cache.py`: content-address each stratum result by sha256 over (sorted input digests, code digest of the
  producing function's module file, vocabulary string). API: `get_or_compute(stratum, inputs, fn, code_path, vocab)`,
  `dependents(digest)`, `invalidate(digest)` (returns the transitive dependents it dropped). Storage: one SQLite file.
- Tests: recompute only along the dependency path when one input changes; identical results when nothing changes;
  deterministic across runs (`PYTHONHASHSEED=0`).
- Deliver `wsl_results/T2/` (code, tests, `REPORT.md`).

## T3 — parallel admission runner
- Port `tools/m1b/cycle.sh` + `compare.py` so that several proposals (each = a vocabulary string) run concurrently,
  sharded over 4 processes, using `tools/m1b/occupancy2_current.py` with `ARC_CANDIDATE` pointing at the repo's
  `candidate/` directory and `ARC_STUBS` unset (real tqdm is fine).
- **Acceptance:** with vocabulary `$(cat tools/m1b/V5.txt)` it must reproduce training test-exact = 81 and
  dev-eval half A = 2, half B = 0 (the cloud baseline `y_d10`). Report wall time per proposal on 4 cores.
- Deliver `wsl_results/T3/` (runner, the reproduced jsonl, `REPORT.md`).

Report back to Len in one paragraph per task when done (numbers + where the files are).
