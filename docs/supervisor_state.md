# Supervisor state (read this first when taking over)

_Last updated: 2026-09-29 18:30 UTC (14:30 EDT). Updated with every outbox batch._

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
- Never rebuild a batch in the same directory: the outputs folder syncs asynchronously, so a re-run can ship a tar and a MANIFEST from different runs (batch-0039 was rejected for a sha256 mismatch). Rebuild under a new batch number.
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

## Update 12:55 EDT Sep 29: Dream cycle 18 (composition gaps), V20 candidate
- Design set = the 99 tasks V19 fails in N1 (85) and half A (14): `latent/design_unsolved_v19.json`. Quick harness `latent/eval_subset.py` (design + regression sample vs a baseline; no held-out ids).
- Lane A `latent/compose_objmap2.py` (copy of objmap + shape edits in the object frame, inbb predicates, complete-template creation, template stamping incl. scaled/inner, separator-colour background). Full eval: ARC1 116 exact (+13 vs objmap 103), N1 10 (+3: 52364a65, 9720b24f, e734a0e8), half A 2 (=), **N2 4 exact / 5 fit / 1 wrong (unchanged)**, no LOST. Deterministic (sha256 identical under load), max 6 s/task.
- Lane B `latent/compose_ctx.py` (new: part_out = OP(part_in, ctx), ctx by role rule: global selector / next / previous / lattice neighbour / mirror; OP = cell tables, recolour, copy/overlay + lift library, progression). Full eval: ARC1 47 exact, N1 3 (5a719d11, c4d1a9ae, e734a0e8), half A 0, **N2 0**, wrong 0. Deterministic, max 1 s/task.
- Reviewer rule for M050 ("cover the largest square background patch with colour") → `latent/fam_fill_bg_windows.py` (greedy largest all-r squares / windows / square components). Alone: ARC1 6 exact, 0 wrong (new: 31adaf00, 6cf79266), N2 0. The rule fits 2 of M050's 6 tasks exactly; a8d7556c nearly (one pair), the other three are template/plus patterns.
- **V20** = V19 + fam_fill_bg_windows + COMPOSE_ENGINES (objmap2, lift, ctx). Probe `tools/m1b/v20`. WSL jobs: `c20-v20` (train/half A, N2 + half-B counts) and `c21-v20-parity` (public eval, sealed count, timing). Admit only with no regressions and public eval ≥ 49/172, max task well under 300 s.
- Finding: design-set gains (+6 N1, +15 ARC1) did not move N2. Held-out transfer remains the bottleneck; the remaining design failures are dominated by creations nobody explains (CA, paths, progressions: 31), different-size outputs (25) and multi-step per-object changes (19).
- **Review principle (Len, 14:30 EDT): the review page is for corrections/perturbations only and stays subordinate to the main pipeline; it is not the classification or inference engine.** Keep: group Primary/Present/Absent, verdict/split, misfit, notes/new concepts, ✗ group/task out of a category. Removed: category approval flow (Approve/Split/Merge/Drop + submit). Every correction is ingested as a perturbation and kept only if it does not hurt the solver.
- Prior-domain categories (8) hidden from the review page (v41; data kept as `cats_prior` / `categories_prior`): they were a suggestion to strengthen inductive bias and have not shown held-out gains (half B / sealed / N2 unchanged by the prior families). `apply_op_domains.py` is dropped from the pipeline.
- Review page v40 (13:50 EDT): **categories are evidence-based** (`tools/review/category_evidence.py`; Codex detector strengths dropped for non-prior categories). A task carries a category by exact grid check (palette = every output a colour relabelling of its input; crop = sub-grid; scale = size multiple; sparse ≤ 20% cells change; partition = full-length line), solver module, or reading (operators / roles / wording); a group carries it when ≥ half its members do. Palette mapping now = M024, M027, M135, M148, M078, M130, M089, M085 (+12 stray tasks listed on the category page). Pipeline order: regroup → patch_review_json → apply_op_domains → apply_solved_names → category_evidence → render.
- Project doc `claude/supervisor_state.md`: write at most once per 30 min (Len). The repo copy is updated with every batch.
- Review page v39 (13:35 EDT): **group membership is algorithmic** (Len: not a review task). `tools/review/regroup_algorithmic.py`: a task solved by a group primitive (module fam_<key>, or BIND e.g. fill_bg_windows → fill.largest_empty) joins that group; solved-family/residual groups dissolve into mechanism groups; multi-group modules never move tasks between mechanism groups; mechanism-group medoids never move. 91 moves, 18 solved-family groups dissolved (ids retired, e.g. M141, M145), 152 groups. Pipeline: regroup → patch_review_json.py → apply_op_domains.py → apply_solved_names.py → render. No membership dropdown (removed); misfit flags stay as evidence. Default tab = Categories.
- Review page v36 (13:15 EDT): search box (name/rule/id/task id); per-task membership dropdown in mechanism groups (✓ in / ✗ exclude / → move to Mxxx; stored as `misfits` + `move_to` in the group's decision — ingest both); solved groups renamed to plain mechanism names (`tools/review/solved_names.json`, family in brackets, `same_as` links); operator → prior-domain links (`tools/review/op_domains.json`, e.g. RAY ⊑ optics, geometry) shown on operator rows/readings and added 151 group→prior-category links ('via operator').
- fam_fill_bg_windows v2 (after V20 was queued): + unique largest rectangle / square (optionally interior) and largest rectangle with sides >= 2 — the M067 'fill.largest empty' concept = reviewer's 'patch'. Alone: ARC1 8 exact, 0 wrong (new 31adaf00, 3eda0437, 6cf79266, e88171ec); N2 0. Goes into the next candidate (V21).
- Review page v34 (13:00 EDT): mechanism-ontology rows first (operators from abstract readings, roles, prior domains; `mech:` labels, ✓/✗ per task), Codex detector labels collapsed as legacy with alias variants merged (one decision applies to all variants), fully accepted/rejected rows highlighted. Data patch: `tools/review/patch_review_json.py` (idempotent; reproduces the published JSON from v32). Parent-concept proposals: New concepts field, syntax `patch > region, template match, …` → add as superclass in the mechanism ontology at ingestion.
- Review page v33: "N need you" pill lists the tasks and reasons; label counts fixed (task labels now carry every class/rule the task has). Do NOT rebuild the review JSON with `build_mview.py` (it renumbers the M groups after status changes); patch it in place.

## Update 14:05 EDT Sep 29: V20 wake results (c20-v20)
- G-stratum training exact 594 → 606 (+12: 31adaf00, 44d8ac46, 52364a65, 5a719d11, 6cf79266, 9720b24f, aabf363d, bda2d7a6, c444b776, c4d1a9ae, e734a0e8, e76a88a6); LOST none; half A 36 (=); **N2 37 exact / 39 fit (=)**; half B 1/49 (=); fit-but-wrong 13 → 14; max task 164 s under 4 workers (training). c21-v20-parity pending.
- batch-0039 rejected (sha mismatch, see rule above); contents resent in batch-0041.

## Update 14:30 EDT Sep 29: V20 admitted (cycle 18)
- c21-v20-parity: digest **c93d287b… identical to V19** (the new engines change no public-eval prediction), 49/172, half A 35, half B 1, sealed 1, max task 57 s, 0 timeouts.
- Admitted for training coverage (+12, no losses). Notebook **v13 = V20** built with `tools/m1b/build_nb.py` and staged in `submission/v13` (EXPECTED c93d287b / 49); **LATEST stays v12** for tonight. v13 is a fallback for the Sep 30 slot (same public-eval output; may differ only on hidden tasks where the new engines fire).
- Lesson: cycle-18 composition gains are all on the design set; held-out transfer (N2, half B, sealed, public-eval predictions) did not move. Next cycle must target held-out failure modes, not design coverage.

## Next steps
1. Tonight after 20:00 EDT: WSL runs `bash submission/daily_submit.sh` (v12 = V19, expected c93d287b / 49). Read `submissions/2026-09-30.json` and `scores.txt` at the 22:30 EDT check-in.
2. Read c20-v20 / c21-v20-parity. If admitted, build notebook v13 = V20 (EXPECTED from c21) and stage it for the Sep 30 evening slot (v12 goes tonight).
2b. Dream cycle 19: target the largest remaining design gaps (CA/progression creations, different-size outputs, multi-step object changes).
3. Keep review ingestion going: category and group decisions from the page db (`decisions` collection).
4. Check-ins run 12-hourly at 10:30 and 22:30 EDT (next: 2026-09-30 02:30 UTC).
