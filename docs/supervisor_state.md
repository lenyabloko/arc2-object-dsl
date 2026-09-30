# Supervisor state (read this first when taking over)

_Last updated: 2026-09-30 02:05 UTC (22:05 EDT Sep 29). Updated with every outbox batch._

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

## Update 14:50 EDT Sep 29: cycle 19 — near-miss fallback (hidden-score lever)
- Unsolved tasks got a 1×1 placeholder on Kaggle (always wrong). Experiment `latent/nearmiss_exp.py` (design splits only): leave-one-pair-out library programs (fit all training pairs but one, k ≥ 3) as best-effort attempts. ARC1 unsolved 249 → 20 guesses, **10 exact**; N1 80 → 4 guesses, **1 exact**; half A 14 → 0. Results `results/cycle19/nearmiss_design.txt`.
- V21 = V20 + fam_fill_bg_windows v2 + `gdsl.nearmiss_fallback` (last stage after compose; deterministic, size cap 2400 input cells; names prefixed `nearmiss:`). Probe `tools/m1b/v21`; WSL jobs c22-v21 (N2/half-B counts) and c23-v21-parity (timing vs the 300 s alarm).
- Review page v43: palette category lists every candidate group ('minority' ranked last), shape-palette-transfer grid check (23 tasks); closure-notes card removed. Slip: the 23 shape-palette ids were printed without filtering N2 — treat that concept's N2 count as possibly contaminated; design any primitive from ARC1/N1/half A members only.
- Pending design fixes from Len's review: regroup should ADD a task to a second group (overlap) instead of moving a mechanism-group medoid; priors should act as ranking/pruning bias in search, not as more whole-task families; stop adding monolithic families (North Star).

## Update 15:00 EDT Sep 29: ontology roles clarified (Len)
- **Conceptual lattice** = orthogonal axes with meets and joins (FCA attributes). **Categories** = meta-classes of mechanisms (classes of groups/primitives), not lattice axes; any current overlap between them is accidental. Implemented: a group is in a category when most of its members show evidence (review v44); task-level evidence inside other groups is a regrouping signal, not category membership.
- Agreed (Len): stop adding monolithic families; effort goes to composition over existing object operations and to hidden-score levers.
- Near-miss for k = 2 pairs (single-pair induction, other pair ≥ 0.95 cell accuracy): design splits 50 tasks → 3 guesses, 2 exact (17829a00, 9356391f); goes into V22 after V21 is measured.

## Update 16:10 EDT Sep 29: V21 admitted (cycle 19)
- c22-v21: G train 606 → 617 (+11: 3eda0437, e88171ec by fill v2; 444801d8, 44f52bb0, 4ff4c9da, a3f84088, a8d7556c, ac0c5833, e1d2900e, ef135b50, f18ec8cc by near-miss); LOST none; half A 36 (=); N2 exact 37 (=), fit 39 → 41 (2 wrong near-miss guesses); half B 1 (=, no near-miss guess).
- c23-v21-parity: digest **c93d287b… again identical** (near-miss fires on no public-eval task), 49/172, max 60.5 s, 0 timeouts; total 1667 s (+300 s).
- Finding: near-miss helps ARC-1-style tasks only (ARC1 9 of 17 guesses right) — on ARC-AGI-2-style tasks it almost never finds a leave-one-out program (N1 1, N2 0 right, half A/public eval none; the 2400-cell cap is not the reason: `latent/nearmiss_big.py` found 0 candidates on the large N1/half-A tasks). Expected hidden-score gain ≈ 0.
- Notebook **v14 = V21** staged in `submission/v14` (EXPECTED c93d287b / 49) as the Sep 30 candidate (supersedes v13; identical public-eval output). LATEST stays v12 tonight.
- Review v45: search matches category/evidence/rule text with spelling tolerance ('pallet'); palette category page lists all 39 grid-evidence tasks by group; stamp groups renamed (stamp = fixed image; decorate/draw/reflect/complete/copy otherwise; `tools/review/group_labels.json`, `apply_group_labels.py`).

## Next steps
1. Tonight after 20:00 EDT: WSL runs `bash submission/daily_submit.sh` (v12 = V19, expected c93d287b / 49). Read `submissions/2026-09-30.json` and `scores.txt` at the 22:30 EDT check-in.
2. Read c20-v20 / c21-v20-parity. If admitted, build notebook v13 = V20 (EXPECTED from c21) and stage it for the Sep 30 evening slot (v12 goes tonight).
2b. Dream cycle 19: target the largest remaining design gaps (CA/progression creations, different-size outputs, multi-step object changes).
3. Keep review ingestion going: category and group decisions from the page db (`decisions` collection).
4. Check-ins run 12-hourly at 10:30 and 22:30 EDT (next: 2026-09-30 02:30 UTC).

## 2026-09-29 ~19:30 EDT — Cavity concept (reviewer abduction, e73095fd)
- Reviewer principle: abduction to an existing concept does not violate MDL — the concept's definition absorbs the conjunctions; program length is counted in concepts. The "and/or flag" applies to clauses of an induced rule, not to a concept definition.
- Cavity (3D reading): the grid is a cut through a scene; a cavity is empty space inside ONE shape; the frame is a cut, not a wall (a box cut by the frame keeps its cavity); space enclosed only by several shapes together is outside each and is not a cavity. Implemented as selector `cavity` in fam_fill_bg_windows (box wall turns at its corners).
- e73095fd: "fill every cavity with 4" exact on 3/3 training pairs + test. Alone over ARC training+eval: fires on 1 task, 0 wrong. The lattice still ranks its 4-clause RDR list first (wrong); cavity is attempt 2 → MDL ranking perturbation (one-concept program outranks a multi-clause list; gdsl consulted even when the lattice has 2 predictions) planned for V22.
- V22 candidate dir: widen/probe_v22 (= V21 + cavity selector), mirrored tools/m1b/v22. Parity not yet run.
- CAVEAT: locally, probe dirs import fam_* from /home/claude/work/latent first (compose_ctx inserts latent/widen into sys.path), so local runs of a frozen probe pick up edited latent files. WSL/Kaggle unaffected (paths absent). Local frozen-probe evals must run with a clean sys.path.
- Reviewer (19:05 EDT): the abduction works by assuming 3D space and possible movements of shapes. Design consequence: concepts like inside / cavity / supported / falls-off are invariants of a 3D world with independently movable rigid shapes; a cavity = empty space that stays enclosed under every independent rigid motion of the shapes. Planned experiment (V22+): (1) decompose connected walls into movable parts (straight segments, closed boxes; joints where parts meet) so "one shape" is computed by separability, not the corner proxy; (2) abductive re-description: for multi-clause (3+) programs, search for one motion-invariant concept whose extension equals the changed cells; count how many of those 21 programs collapse to one concept and whether the wrong ones become right.
- DESIGN PRINCIPLE (reviewer, 19:15 EDT): adding an extra space dimension and considering movement of parts lets the solver discover an EXISTING concept (prior) and transfer the description burden to it. Abduction = lift the observation into a richer world model (3D, rigid parts, motion; also depth/occlusion, gravity) where one existing concept matches; the concept's definition is paid once in the prior library, so the program is one term. Guard: the concept must pre-exist (defined independently of the task) and must predict the test; inventing a concept per task only renames the conjunction.
- Reviewer (19:20 EDT): the prior concept is MORE GENERAL than the conjunctive clauses it replaces — it subsumes them. In pixel terms cavity = "enclosed hole OR room cut by the frame"; after the lift both disjuncts are one invariant (enclosed under motion). Ranking consequence: among programs that fit the training pairs exactly, prefer the MOST GENERAL consistent concept (version-space G boundary), not the most specific decision list (S boundary, where the RDR lattice sits). Generality can be measured by how many scenes the concept applies to across the design splits.
- DIRECTIVE (Len, 19:25 EDT): apply the inductive-prior principle to EVERY task — instead of enumerating conditions, fit the case into an outside prior; that is the purpose of priors as inductive bias for MDL. Plan: (1) priors expose concepts (task-independent named predicates, incl. lifted 3D/motion concepts) as lattice attributes / cell selectors, not whole-task programs; (2) one-concept rule first for every task, enumeration (conjunctions) only as fallback, fallback fits flagged "needs a prior"; (3) ranking exact fit → most general concept → shortest. Measure on design splits, then held-out via WSL.
- Reviewer (19:30–19:40 EDT): ARC wants an existing one- or two-word concept that already covers the situation; conjunctive forms are almost never needed. Instead of conjunctions use EXCEPTION RDR over existing abducted concepts — every node one concept, context replaces conjunction — so every abducted concept is reused.
- Baseline evidence (lattice, a_atoms training run): programs with 1–2 rules 34/34 exact; 3 rules 20/25; 4 rules 14/17; 5 rules 15/42 — every wrong lattice answer is a 3+-rule enumeration.
- Cycle 20 implementation (widen/probe_v22): `prior_concepts.py` (P:cavity, P:free_<dir>/P:supported, P:mirror_pair, P:between, P:key/P:lock, P:occluded/P:occluder) added as lattice attributes; learners prefer prior concepts at equal coverage/length; `M1B_SINGLE=1` removes conjunctive generators and adds `learn_rdr` (exception RDR, one concept per node, depth ≤ 3, ≤ MAX_RULES nodes). e73095fd: lattice attempt 1 is now "P:cavity → paint 4, else keep" (exact). Cloud A/B running (scratchpad c20: v21_design, v22_design, v22s_design; 603 same-shape design tasks, N2 excluded).
- Reviewer (19:40 EDT): ontology enrichment must be INTENSIONAL (definitions that compress description), not extensional (membership lists). Ontology = T-box (intensional concept definitions from priors); A-box = per-task individuals (cells, objects, regions) and asserted relations computed from the grid, connected by induced primitive operations. Abduction = realization of A-box individuals under T-box concepts; rule stated in T-box terms (one concept + exceptions). Note sent: OWL 2 property-chain axioms are RBox (terminological); the chains of assertions they walk are A-box; our per-task induced chains (e.g. container colour) are A-box operations and become T-box roles only if naming them compresses many tasks. Review-page categories are extensional (A-box-like).
- Reviewer (19:50 EDT): 3979b1a8 = Rainbow (optics): a drop splits colours; many drops form a bow. Verified reading (exact on 2 train + test): drop = the input with concentric colours; spectrum = colours on the ray from its centre to its corner; the ray continues periodically to the corner of the 2n canvas; each ray colour draws a bow (arms one step further out, rounded corner) around the drop through its ray point. 2D description needs a conjunction (L bands with shifted corner); optics needs two concepts.
- Reviewer: enhance the ontology with physical, chemical and optical priors; repeating abductive steps is the key to transferring priors and RDR to held-out tasks; in many cases it can be a deterministic offline search over the enhanced ontology. Design: each T-box concept = intensional definition (outside domain) + recogniser (A-box classification) + generator (what it produces). Ontology built offline, frozen into the notebook; per-task search deterministic. Admission gate per concept: compresses beyond its source task and does not hurt held-out counts.
- Reviewer (20:00 EDT): RDR forest is fast for offline search guided by ontology-graph neighbourhood (guidance originally given to Codex; never realized in Wake). Correction: the ontology is built ONLINE (Dream, Semantic Web reachable) and used OFFLINE (Wake/Kaggle); priors must carry their mechanisms as OWL 2 property chains mined from the Semantic Web during Dream, with chain steps bound to existing grid mechanisms (recogniser/generator). Wake plan: seeds = concepts whose recognisers fire; RDR forest with nodes drawn from the seeds' 1–2-hop graph neighbourhood; widen only if nothing fits; deterministic. Existing: codex/ontology/concept_hierarchy.ttl (property chains only for internal feature entailment) and codex/ontology/dream_proposals/*/03_ontology_grounding.ttl — reuse formats; no mined mechanisms, no neighbourhood search yet.
- CENTREPIECE DOC (20:10 EDT): "Abductive Meta-Learning: Dream and Wake" — Claude Doc https://claude.ai/code/artifact/c86f732e-3055-4f52-ad82-9f26fd52973a (purpose, principles, formal model, Algorithm W, Algorithm D, growth and convergence, worked examples, evidence, contradictions, plan to Oct 12 / Nov 2). Len: this algorithm is the centre of further effort.
- Reviewer (20:05 EDT): T-box/RBox should grow roughly exponentially at first, then slow and converge to a large all-encompassing ontology of priors far exceeding the rules training uses — that surplus is how learning transfers; convergence in time and space must be ensured. Consequence recorded in the doc: no corpus-MDL gate on ontology admission (it would reject the surplus); growth bounded by budgets (mining depth d, fan-out f, Wake out-degree cap m so |N_k| <= m^k, notebook size B); saturation test = new-node rate r(n) < eps over a window while reuse rises.
- Reviewer (20:15–20:50 EDT): MDL applies only to the atoms and chains a program uses; the ontology is a side effect, excluded. Codex failed to converge on a finite ontology — avoid. Online learning = Dream + Wake with WAKE FRONT-RUNNING DREAM (Dream only when Wake fails) — the key to convergence; the same offline on Kaggle (fast Wake first so the 12-hour limit is never exceeded; offline Dream only deepens search over the frozen ontology); in both, Wake supplies a signal that keeps Dream focused and bounded.
- Formal review by Fable (subagent, 21:00 EDT): `docs/meta_learning_problem_statement.md` → `docs/meta_learning_bounds_guards.md` (Q1–Q7, guards G1–G30, 15 contradictions). Key: attempt-1 programs ≤ 3 nodes (root incl.), chance-fit margin ≥ 3 bits; ring code 3/7/11 bits; Wake caps s_max 4, m 8, k_max 2, V_max 96, ≤ 2e5 evals/task; mining d 2, f 5, hub in-degree > 500 excluded; frozen O = radius-2 closure of grounded concepts (≤ 73 nodes each); front-running: Dream only on FAIL/WRONG, ≤ 2 retries per failure signature then quarantine (≤ 3 Dream steps per design task ⇒ finite ontology without KB assumptions); Kaggle rounds R1–R4 with work units, budget 12 h × 0.75 / 1.5; McNemar: 0 lost ⇒ need ≥ 5 gained. Decisions for Len: grounding gate Option A vs B (B recommended), mechanisms as C ⊑ ∃R.D (EL) vs chains, R7 unattainable as stated, N2 gate/decide split.
- Cycle 20 result: V22 flat-concept lattice REJECTED (603 design tasks: V21 71/31; V22 69/34 +3/−5; V22 single 70/34 +5/−6). Ledger updated.
- batch-0045 (baseline B0 = frozen V21: tools/wake/BASELINE_B0.md, wake jobs b0-v21-design / b0-v21-parity, v21 checksums, LATEST=v14, problem statement, cavity, V22 probe) written to outputs; RESULT.json to be checked.
- Fable hand-back protocol (21:25 EDT): Fable writes ONE file fable_guidance_v<N>.md (header doc/version/date/based_on; sections A verdicts on G1–G30, B decisions, C implementation spec W1/D1/scheduler, D convergence, E open questions for the supervisor, F machine-readable JSON of guards/decisions/tests) to the project as claude/fable_guidance_v<N>.md, or Len saves it to C:\Users\lenya\arc_extended_arga\fable_inbox\. Supervisor (cloud Claude) checks both at every check-in, verifies, adopts or rejects each item, and replies in the project as claude/fable_round_<N>_response.md with measurements vs B0 and answers. Fable never instructs WSL/Kaggle/repo.

## Update 21:45 EDT Sep 29: cycle 21 — MDL attempt ordering (V23) and slot-crowding fix (V24)
- Finding: in 13 design tasks V21's lattice produced two wrong 3+-rule decision lists that took both attempts while the G library had a correct one-concept program (lock-and-key, projection, colour map, size rank, key position, periodic fill…) that never got a slot (G is consulted only when the lattice has < 2 predictions).
- V23 = V21 + MDL attempt ordering in occupancy2.solve: if every lattice program has 3+ rules, consult G; rank candidates by description class (lattice ≤ 2 rules / G ≤ 2 concepts or decision entries = 0; 3 = 1; longer = 2; near-miss = 3), ties in the old order. Local: 21/22 lattice-wrong tasks right (V21 8/22), 0 losses on the 47 long-correct tasks.
- V24 = V23 + gdsl.search fix: programs that refuse a test input no longer use up one of the 6 candidate slots (memorised shape→colour tables crowded out topo:recolour on 7d1f7ee8, now solved: "inside → colour of the outermost container") + topology lookup tables cost 0.5 per entry beyond two.
- Probe copies V23/V24 use sys.path.append (not insert) for latent/widen so local runs are no longer contaminated by edited latent files.
- New wake mode "full" (tools/wake/full_eval.py): full probe with the Kaggle attempt ordering on training + half A, N2/half B counts. Jobs: c24-b0-v21-full, c25-v23-full, c26-v24-full, c27-v24-parity (batch-0047).
- V25 (22:00 EDT) = V24 + `prior_abduced.py` (line of sight 4f537728, nearest neighbour 6df30ad6/aabf363d, innermost interval 5ad8a7c0 [N1], dashed border 30f42897 [N1], fronts meet halfway d968ffd4 [N1], rainbow 3979b1a8) + cavity selector (e73095fd). Alone on all 1120 public tasks: 7 exact, 0 wrong, 0 held-out fires (reuse ≈ 1.2 tasks per concept). Full solve: all 9 tasks right at attempt 1. Jobs c28-v25-full, c29-v25-parity (batch-0048). Evidence for Fable: project doc claude/supervisor_evidence_r1.md (repo docs/supervisor_evidence_r1.md).
- **Kaggle (22:00 EDT): v11 (V17) public score 2.50 — the first non-zero score (project goal met).** Tonight's slot: v14 push_failed (Kaggle API "400 Bad Request" on SaveKernel). v14 = 1.43 MB vs v11 0.82 MB (pushed fine) → likely a notebook size limit near 1 MB. New `tools/m1b/build_nb2.py` ships the probe as one zlib+base64 payload cell (byte-identical files, verified) and also sets PROBE_SHA (build_nb.py never did — V23+ change occupancy2.py, so the old builder would have failed the gate). v15 = V21 compact (0.66 MB), LATEST = v15. daily_submit.sh refuses notebooks > 1,000,000 bytes; WSL_CLAUDE.md step 7: a failed push is not a submission — a newer LATEST may be pushed the same UTC day (batch-0049).
- V26 (22:20 EDT) = V25 + topology zone feature is_square (44d8ac46, refactor of a 3-rule lattice program) + prior_abduced v2 (black background when present; boundary roles with colour-free actions: 4/0 alone; chemistry reaction A+B→C: d90796e8; panel dye +k: 54d9e175). Abduced families alone on 1120 public tasks: 13 exact, 0 wrong, 0 held-out fires. Refactoring of the 47 long-correct lattice programs under V23: 36 now answered first by a correct one-concept G program; 6 had no G program (319f2597, 44d8ac46✓, 54d9e175✓, 7ddcd7ec, b6afb2da✓, d90796e8✓). Jobs c30-v26-full, c31-v26-parity (batch-0050).
- WSL queue trimmed (22:05 EDT): intermediate jobs c25–c29 (V23/V24/V25) moved to wake_jobs/deferred/ so the night goes to b0-v21-design, b0-v21-parity, c24-b0-v21-full, c30-v26-full, c31-v26-parity (V26 contains V23–V25). Attribution runs can be restored later.
- **Fable guidance v1 received (21:29 EDT; project doc claude/fable_guidance_v1.md).** Adopted: F1–F9, Option B grounding gate hardened (b′ fire ratio ≤ 0.5, f E(test) ≥ 10 bits or a second task, test_seen flags), mechanisms as EL existentials + ≤ 10 curated chains, R7′/G7′ slot rule, B.4 look protocol (N2 split with salt arc2-c21-2026-09-29; half B and sealed retired from gating; decision set sealed in decide_sealed.json, looks on Oct 12 and Nov 1), convergence via per-task retry cap + quarantine + monotone admission, early-failure monitor M1–M9. Convention correction sent: lattice n_rules includes the root, so |P| = n_rules (slot-1 cap |P| ≤ 2). Contamination admitted: all 13 abduced families test_seen; viewer now test-blind. Response: claude/fable_round_1_response.md.
- Tools (batch-0052): wake_eval default + full + parity modes now report N2-gate counts only; N2-decide, half B, sealed → decide_sealed.json (not to be read before Oct 12). WAKE.md updated.
- V27 (22:05 EDT) = V26 + first TEST-BLIND abductions (viewer hides test outputs; one harness test check per family version, ledger results/cycle21/harness_ledger.jsonl): pour (fluids) db7260a4 ✓, bridge the gaps (masonry) af726779 ✓, crosshair (geometry) 9f5f939b ✓ — all exact on their single test check; drape over a pole bae5c565 (test_seen). Abduced families alone: 17 exact, 0 wrong, 0 held-out fires. WSL: c30/c31 now point to V27 (V26 jobs deferred) — batch-0053.
- V28 (22:15 EDT) = V27 + test-blind abductions: mirror panels (optics reflection + blank fill, N1 4e7e0eb9 ✓), turtle glyph strokes (program interpretation, half A 136b0064 ✓), sort bars by height (combinatorics, half A 31f7f899 ✓). Harness ledger: 7 test-blind single checks, 7 exact (db7260a4, af726779, 9f5f939b, 4e7e0eb9, 136b0064, 31f7f899 + pour/bridge/crosshair/mirror/turtle/sort). Two half-A (public eval) tasks newly solved → V28 parity digest will differ from B0; expected correct_of_172 ≥ 51. WSL c30/c31 retargeted to V28 (V27 jobs deferred) — batch-0055.
- Kaggle: v15 pushed as kernel version 4 (01:50 UTC), run in progress (WSL report 22:10 EDT) — the push size was the v14 problem.
