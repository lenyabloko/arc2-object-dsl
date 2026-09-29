# NOTES compose_objmap2 (cycle 18, Lane A)

Started 2026-09-29 11:51. compose_objmap2.py = copy of compose_objmap.py, extended (original untouched).

## Diagnosis (99 design tasks, V1 = original objmap logic + DIAG counters)
- diffsize: 26 (outside the same-size object learner; only compose_first could apply)
- every segmentation leaves unexplained objects (missing action descriptor): ~30
  (classes: part-erase / part-change dominate -> per-object shape edits, relayering, stamping)
- all objects explained but no decision list (predicates cannot separate, L=0): ~10
- lists found but all rejected by MDL (single-object rules = coincidental descriptors): ~9
- lists found, render fails on training (created cells no creation kind explains): ~30
- training fits, test render fails: 1 (ecb67b6d)

## Additions (all generic, induced from the pairs)
1. Shape edits in the object frame, descriptor ('edit', kind, param, colour-expr): kept subset of the object's
   cells, rest -> background, kept cells optionally recoloured uniformly.  kinds: trim first k=1..3 rows/cols
   from N/S/W/E; erode 4/8; hollow 4/8; erase minority / majority colour (2-colour objects); core (widest rows x
   tallest cols); thin (remove 1-thick rows/cols).  Unchanged objects take no-op edits (vacuous).
   Solves 52364a65 (trim W 2), 9720b24f (m8 + erase minority).
2. Predicate inbb / inbb* (inside the bounding box of a larger object).
3. Creation 'complete' (id / d8): stamp the unique larger template containing the object's coloured pattern.
4. Re-layering 'front' (small / large priority by bbox area): complete own bbox over lower-priority occluders;
   render paints fronts in priority order; occluded objects may KEEP (cons = recolour only).
5. Template stamping ('stamp', role, (align, D8), 'same'): receiver overwritten by the template (role mostcol /
   large), aligned by bbox (same size) or centre.  Solves e734a0e8 (with 6.).
6. Separator background mode: a colour drawing full rows/cols in every input is tried as the background.

## Fixes after the full regress (112 baseline-exact tasks)
- 917bccba LOST: vacuous / total-erase edits on every unchanged / vanished object enlarged masks and pushed the
  right decision list out of the 20-list cap.  Now: changed objects take real edits (non-empty strict kept
  subset); unchanged objects get no-op edits and vanished ones total-erase edits only in a post-pass, for the
  edits some edited object uses; a vanished 2-D piece whose delete was dropped by least action may still take a
  total-erase edit (keeps 9720b24f exact).
- aa4ec2a5 LOST (compose_first second step): the vacuous 'front' masks perturbed rule search -> re-layering is
  disabled (RELAYER=False; it also predicted 52df9849's test wrong).

## Status / evals
- ev1 (edits+inbb+complete): design 2 exact (52364a65, 9720b24f), regress 60/60.
- ev2 (+front): design 2 exact, fit 3 (52df9849 wrong); regress pending.
- ev3 (+stamp +separator bg): design 3 exact (52364a65, 9720b24f, e734a0e8), fit 4, regress60 60/60.
- reg112 (+rowsame/colsame predicates, slide away from anchor): 110/112, LOST 917bccba, aa4ec2a5 -> fixed (above).
- ARC1-unsolved (256, older version): exact 3 (NEW 44d8ac46 [used front], c444b776 [stamp]), fit 10, wrong 7
  (baseline: fit 5, exact 1, wrong 4).
- ev4 (fixes, relayer off): design 3 exact / fit 3 / wrong 0 (52364a65, 9720b24f, e734a0e8); regress 112/112.
- ARC1-unsolved fits (ev4 version): EXACT 009d5c81 (baseline), 44d8ac46 (NEW, fill-enclosed ; erode), c444b776
  (NEW, stamp); WRONG 8fbca751, a79310a0, f76d97a5 (baseline wrong too), 32e9702f, 782b5218, e73095fd (new; edits
  inside composed programs emulate clipping / total erase).  Baseline: exact 1, wrong 4 (17b80ad2 no longer fits).
- + stamp aligns 'scale' (k x k blocks filling the receiver bbox) and 'inner' (scaled into the hole bbox),
  role 'near'.  ev5: design 3 exact / fit 3 / wrong 0; regress 112/112 (no LOST).
- FROZEN engine sha256 43488d9d34bad336fb6106e68bc3e8c7667c61bf24549b4309a081977b8b8d7b.
- FULL EVAL started 12:23 (PID 1977): EVAL_WORKERS=1 EVAL_TIMEOUT=60 python3 eval_fam2.py compose_objmap2.py
  out_compose_objmap2.jsonl > full_compose_objmap2.log.  If the machine restarted, rerun it with nohup.
- DETERMINISM PROOF done (12:26, frozen engine): 30 tasks (15 design + 15 regression), sha256 of the canonical
  JSON predictions 051550eeeb3f78ef96f1daafe0637ee9e041a88da87508aa38a3acee1185e8db both normally and with a CPU
  hog (python3 -c "while True: pass", killed by PID); files identical (cmp).  Max per-task runtime 6.22 s
  (5a719d11) normally, 12.10 s under the hog (+ the full eval running = 3 processes on 2 cores).
- FULL EVAL DONE 12:42 (18 min, 1 worker; out_compose_objmap2.jsonl, full_compose_objmap2.log):
  ARC1-train n=767 exact=116 fit=130 wrong=14   (c16 objmap baseline 103 / 116 / 13)
  N1         n=131 exact=10  fit=10  wrong=0    (baseline 7 / 7 / 0)
  halfA      n=50  exact=2   fit=2   wrong=0    (baseline 2 / 2 / 0)
  N2 (counts only) n=102 exact=4 fit=5 wrong=1  (baseline 4 / 5 / 1: no held-out change)
  timeouts 0 errors 0.  vs baseline: LOST none in any split.
  NEW ARC1 (13): 22168020 3618c87e 36d67576 4347f46a 44d8ac46 54d9e175 5af49b42 6455b5f5 7e0986d6 7f4411dc 88a10436
  91714a58 c444b776 (edits hollow/thin/erode, complete id/d8, stamp large:centre / mostcol:bbox, separator bg).
  NEW N1 (3): 52364a65 9720b24f e734a0e8.  New ARC1 wrongs: 32e9702f 782b5218 e73095fd (edits inside composed
  programs); 2 baseline wrongs no longer fit.

## Remaining limits on the design set (final DIAG tally, 99 tasks)
  train render fails (creations nobody explains: CA / paths / progressions / band context) 31; different-size 25;
  unexplained objects in every segmentation (multi-step per-object changes) 19; no decision list (missing
  relational predicate) 10; MDL-rejected single-object rules 9; test render fail 1; other 1; solved 3.
