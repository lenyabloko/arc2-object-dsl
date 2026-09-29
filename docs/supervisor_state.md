# Supervisor state (read this first when taking over)

_Last updated: 2026-09-29 15:55 UTC (11:55 EDT). Updated with every outbox batch._

## Goal and rules (unchanged)
- Non-zero Kaggle score in ARC Prize 2026 (ARC-AGI-2). Deadline Nov 2; decision point Oct 12.
- Symbolic solver only.
- **Kaggle:** submit only via `submission/daily_submit.sh` after the Kaggle parity check passes (digest match plus `correct_of_172`). One submission per UTC day.
- **Data discipline:**
  - Design uses training, dev-eval half A (burned as a design set) and N1, the design half of the 233 ARC-AGI-2-new training tasks (`tools/m1b/novel_N1.txt`).
  - N2 (`novel_N2.txt`), half B and sealed: counts only; task ids are never inspected.
- No task-specific code; no Codex solutions.
- Never touch Kaggle credentials; no deletions on the user's machine.

## Current builds

| Build | Probe | Training (lattice + G) | Half A | Half B | Sealed | Public eval | Status |
|---|---|---|---|---|---|---|---|
| V17 | `tools/m1b/v17` | 504 | 35 | 1/49 | 0/21 | 46/172 | **Submitted** 2026-09-29 01:05 UTC as notebook v11 (kernel v3). Kaggle parity passed; score pending. |
| V18 | `tools/m1b/v18` | 590 | 36 | 1/49 | — | 47/172 | Admitted (cycle 15). Has 2 wall-clock budgets, so it is not Kaggle-safe. |
| V18d | `tools/m1b/v18d` | — | — | — | — | digest 087dfbc6 | V18 with those budgets removed. Last parity run was under heavy load: 1 task timed out at 300 s, and 5 took >150 s. **Re-time on an idle machine before building notebook v12.** |

- ADMIT for c13–c15 is done (`results/m1b/perturbations.txt`, cycles 13–15): no regressions, all admitted.
- **Finding:** held-out half B stays at 1/49 and sealed at 0/21 across V13→V18. Monolithic families and priors are at a fixed point for transfer.

## Lanes
- **Group primitives** (`latent/fam_*.py`, 29 modules): done through pass 5.
- **Priors** (`latent/prior_*.py`, 8 domains): done through round 2.
- **Composition engines** (`latent/compose_*.py`), the current lane.
  - N2 exact counts: objmap 4, lift 5, residual 0.
  - Kaggle parity needs deterministic work budgets:

  | Engine | Deterministic conversion |
  |---|---|
  | compose_objmap | Done and verified: byte-identical under load and with a different hash seed; N2 4 exact / 5 fit / 1 wrong. |
  | compose_lift | Converted by an agent that was interrupted; not verified. Orphan eval (`out_compose_lift_det.jsonl`) was still running at 02:30 UTC. The first det-eval log showed ARC1 160, N1 11, half A 1, N2 5 exact / 0 wrong. |
  | compose_residual | Converted by an interrupted agent; not verified. Orphan eval was still running at 02:30 UTC. |

  - The originals are kept as `compose_*_timed.py`.
- **Ontology:**
  - `results/ontology/mechanism_ontology.json`
  - `latent/ontology_links.ttl` (635 verified external links)
  - The review page shows mechanism groups (M001–M170) and 8 prior categories.

## Infrastructure
- **Cloud workspace:**
  - `/home/claude/work/widen`: gdsl.py plus probes and parity runs.
  - `/home/claude/work/latent`: engines, briefs and eval harnesses (`eval_fam.py`, `eval_fam2.py` = transfer-aware).
  - `/home/claude/work/s0`: review page (`mview/build_mview.py` → `mview/arc_group_review.html`).
- **WSL wake loop** (`~/arc/wsl_work/wake/wake_loop.sh`) runs `wake_jobs/*.json` via `tools/wake/wake_eval.py`.
  - Results go to `cloud_outbox/wsl_results/wake/<job>/`.
  - From batch-0026 on, `summary.json` includes N2 counts.
- **Outbox:** batches carry `files.tar.gz` and `MANIFEST.json`, with `READY` written last. Allowed extensions only (no `.jsonl`; use `.txt`). Always read `RESULT.json` before claiming a batch was pushed.
- **Review page:** claude.ai artifact `Ty8UPeb21xRCRamtphdZj2` (db capability; decisions keyed by group id; the v1 spectral groups are still reachable through the toggle).

## Liveness (heartbeat)
- `cloud_outbox/status/heartbeat.json` + `STATUS.txt` on Len's machine: rewritten at every step (what I'm doing, what's next). Stale after 90 min (or the `stale_after_minutes` I set before a known long step).
- Review page → Cycle tab → "In flight" first row shows the same heartbeat.
- Optional WSL watchdog: `nohup bash tools/watch/heartbeat_watch.sh >/dev/null 2>&1 &` — one Windows notification per stale episode, log `~/arc/heartbeat_watch.log`.

## Operating rules (learned the hard way)
- Run long jobs detached (`nohup … &`) and poll. Never block a tool call on a job longer than a few minutes; that includes multi-agent batches, so keep agent batches small.
- Check every outbox `RESULT.json`. batch-0018 was rejected over a `.jsonl` file and went unnoticed.
- Kill processes only with exact patterns such as `pgrep -f "^python3 eval_gdsl2"`; broad patterns kill the shell.
- Wall-clock budgets anywhere in the probe break Kaggle parity.

## Update 22:45 EDT Sep 28
- The cloud machine rebooted at 22:42 EDT. Files survived; detached processes did not (the orphan lift/residual evals were lost).
- Engine verification moved to WSL: wake jobs `c16-objmap-det`, `c16-lift-det`, `c16-residual-det` (batch-0030; `wake_eval.py` now has engine mode and per-task prediction hashes `ph`).
- Cloud cross-check: the same engines on the first 120 training tasks (`/tmp/claude-0/xcheck/<engine>/results.jsonl`). Matching `ph` between WSL and cloud = cross-machine determinism.

## Update 00:35 EDT Sep 29
- All three composition engines are verified deterministic across machines. WSL c16 vs cloud: 111/111 identical prediction hashes each.
  - objmap: N2 4 exact / 5 fit.
  - lift: N2 5 / 6.
  - residual: N2 0 / 1 (left out of V19).
- V19 = V18d + composition fallback (objmap, then lift) in `gdsl.search` (`compose_fallback`, reentrancy-guarded). Probe `tools/m1b/v19`.
- WSL queue:
  - c17-v19 (train/half A, N2, half-B count).
  - c18-v18d-parity and c19-v19-parity: new `mode: parity`, full probe on the 120 public-eval tasks, single process, PYTHONHASHSEED=0, per-task timing. Held-out tasks: counts and anonymous times only.
- The cloud machine reboots on every session restart. Long cloud jobs are unreliable; use WSL wake jobs.

## Update 01:45 EDT Sep 29: V19 admitted (cycle 17)
- c17-v19 (WSL):
  - visible training 552 → 570 (+18), half A 36 (unchanged), no regressions.
  - N2 G-exact 37 (unchanged: the engines' N2 solves overlap the library's).
  - half B 1/49.
- Parity/timing runs (WSL, single process, same file as Kaggle):
  - V18d: digest 4c487dd1… (identical to the V18 cloud parity), 47/172, max task 56 s, 0 timeouts.
  - V19: digest c93d287b…, **49/172** (half A 35, half B 1, **sealed 1**, the first sealed solve), max task 57 s, 0 timeouts, total 21 min.
- Notebook v12 = V19 (`submission/v12`, EXPECTED c93d287b / 49).
- **The cloud parity re-run confirmed the digest** c93d287b (max 60 s, 0 timeouts).
- **LATEST=v12 is staged (batch-0035).** Tonight's submission after 20:00 EDT: WSL runs `bash submission/daily_submit.sh`.

## Update 11:55 EDT Sep 29 (12-hour check-in)
- No new WSL jobs since c19. The review page has one new decision: *Layout & lattice* approved with M141 excluded (ingested: `results/review/decisions_ingested.json`).
- v11 score not recorded yet. New `submission/record_scores.sh` (read-only kaggle CLI) writes `cloud_outbox/submissions/scores.txt`; `daily_submit.sh` calls it.
- The local shell on Len's machine (device_bash) failed to start this morning; file listing, staging and commits still work. The WSL loop is unaffected.
- Report appended to `docs/convergence_and_eta_assessment.md` (estimate about 50%).

## Next steps
1. Tonight after 20:00 EDT: WSL runs `bash submission/daily_submit.sh` (v12 = V19, expected c93d287b / 49). Read `submissions/2026-09-30.json` and `scores.txt` at the 22:30 EDT check-in.
2. Dream cycle 18 (composition lane): context-aware lifting, richer objmap relations, priors as composable operators. Measure on N2 and half-B counts via WSL wake jobs; admit on held-out gain with no regressions; then parity-mode job before any notebook v13.
3. Keep review ingestion going: category and group decisions from the page db (`decisions` collection).
4. Check-ins run 12-hourly at 10:30 and 22:30 EDT (next: 2026-09-30 02:30 UTC).
