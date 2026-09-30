# WAKE runner — standing task for WSL Claude (deterministic, parallel part of each Wake/Dream cycle)

The cloud session does DREAM (reads tasks, proposes primitives and regroupings, writes probes). You do WAKE:
run every pending job with all local cores and hand back the results. Nothing here needs judgement.

## Loop (repeat until Len stops you; check every ~5 minutes)
1. `cd ~/arc/arc2-object-dsl && git pull -q`
2. For each `wake_jobs/<job_id>.json` that has no result folder
   `/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/wsl_results/wake/<job_id>/summary.json`:
   `python3 tools/wake/wake_eval.py wake_jobs/<job_id>.json /mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/wsl_results/wake/<job_id>`
   (set `CODEX_DSL_ROOT` to a folder containing Codex's `extended_transformations/` — e.g. `/mnt/c/Users/lenya/arc_extended_arga` — so `summary.json` shows `codex_ops_loaded: true`; set `ARC_DATA` if the ARC-AGI-2 json files are not under /kaggle/input/arc-prize-2026-arc-agi-2; `WAKE_WORKERS` defaults to all cores).
   Run jobs one at a time, oldest first. A job normally takes a few minutes.
3. If a job crashes, write `<result folder>/ERROR.txt` with the last 30 lines of output and move on. Never edit job files or probes.

## Rules
- Half B (tools/m1b/deval_b.txt) is DESIGN since decision OQ7 (Len, 2026-09-30): the 99 Codex-fitted public eval tasks
  (half A + half B) are design; add `"halfB"` to a job's `sets` to evaluate it. N2 stays counts only.
- The 21 never-attempted public eval tasks are SEALED until Nov 1: never print or inspect their ids or results. Do not touch ~/.kaggle or credentials. No deletions.
- This loop is separate from the daily Kaggle submission (submission/WSL_CLAUDE.md), which keeps priority once a day after 00:00 UTC.

## Decision set (from 2026-09-30, Fable guidance v1 B.4)
- N2 is split once by `sha256("arc2-c21-2026-09-29" + task_id)`: gate half (counts reported in summary.json) and
  decide half. Half B and sealed are retired from gating.
- Full and parity jobs write the decision-set counts to `decide_sealed.json`: N2-decide (full/default modes) and the
  21 sealed tasks (parity mode). Half B counts go to summary.json (design, OQ7). Do not print, quote or summarise
  `decide_sealed.json`; it is read once, at the Nov 1 look. Oct 12 uses the per-cycle proxy P1/P2 (OQ7).
- (Fable v2 E1–E3) Full and default jobs also write `n2_gate_private.jsonl.txt` (salted hashed ids, exact, prediction
  hash). `python3 tools/wake/compare_gate.py <baseline_dir> <candidate_dir>` prints only `(b, c, n_changed)` and
  appends the release to `results/looks_ledger.txt`. Do not open the private file; report only the comparer output.
  (`halfB_count: true` in old job files now means "evaluate half B as design".)
- (Fable v3 A.2) The private gate record needs a SECRET salt that is not in the repo. Create it once, never print it:
  `python3 -c "import secrets;print(secrets.token_hex(16))" > ~/arc/.hid_salt && chmod 600 ~/arc/.hid_salt`
  Jobs refuse to write the record without it. summary.json no longer contains N2-gate counts; the only release is
  `CYCLE=<n> python3 tools/wake/compare_gate.py <baseline_dir> <candidate_dir>` once per cycle.
