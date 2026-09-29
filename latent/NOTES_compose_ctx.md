# NOTES compose_ctx (cycle 18, lane B)

## Design (compose_ctx.py, sha256 4f8623cf... at full-eval launch)
part_out = OP(part_in, ctx), ctx chosen by a ROLE rule; reuses compose_lift by import (partition, Part, _attrs,
select, _selectors, _block_specs, lib_search, loo_filter, deterministic work budget tick/Budget/work_cap/SEC).
- partitions: sepx (own: separator lines of any colour incl. majority colour), lift sep, bgsep rc/r/c, frame, blocks,
  object bboxes (8-multi, 4-single, 8-single; disjoint only)
- ROLE: sel (lift selectors: template/key/marker/index), next/prev (cyc or not), right/left/down/up (cyc or not),
  mirror mh/mv/mp
- OP: cell table (key: none / ctx cell / part cell / both, as role or literal colour; value: P, C, role colour of
  part or ctx, literal) with ctx D8; recol (part colour -> ctx/part role colour or literal); two role systems
  (scene-bg first / count first); simplest consistent key mode wins; per-key expression = first in prior order
- PREDICATE (which parts get OP): all, notctx, has c, lacks c, ncol n, ncol>=2
- modes: INPLACE-CTX (same size), INPLACE-LIB (OP in {copy ctx, ctx over part, part over ctx} then lift lib_search
  on pooled part pairs, <= 4 library calls, lift loo_filter), PROG (next panel of the sequence: per-colour shift
  or growth extrapolation; output panel or panel+separator ring), SELCTX (output = table(selected part, its ctx)).
- LOO: re-fit on all pairs but the last changed (and first when >= 3 changed), must predict held-out grid exactly.
- budget: lift's work counter, 19 s; CELL_UNIT 6 wu/cell (work >= CPU on design set).

## Results
- quick loop (design): n=99 exact=3 fit=3 wrong=0 NEW=[5a719d11, c4d1a9ae, e734a0e8] LOST=[52df9849]
- quick loop (regress 60, lift's solved set): exact=6 fit=6 wrong=0 (LOST 54: expected, other mechanisms)
- determinism: 30 tasks, sha256 449e7c6e... identical with / without CPU hog; max CPU/task 0.96 s (wall 2.97 s under hog);
  max CPU on the design set 3.2 s (9aaea919).
- full eval (DONE, full_compose_ctx.log, out_compose_ctx.jsonl, engine sha 4f8623cf...):
  ARC1-train: n=767 exact=47 fit=47 wrong=0 (21 new vs V19 solved list)
  N1: n=131 exact=3 fit=3 wrong=0 new=[5a719d11, c4d1a9ae, e734a0e8]
  halfA: n=50 exact=0 fit=0 wrong=0
  N2 (counts only): n=102 exact=0 fit=0 wrong=0
  timeouts 0 errors 0
- tried after the full eval, NOT kept: XCTX (ctx = object outside the parts, nearest-neighbour stretched into
  frame interiors, ctx erased) for 465b7d93 - that task needs line-preserving stretch; saved unevaluated as
  scratchpad ctxB/compose_ctx_v2_xctx_unevaluated.py.  Final engine = the evaluated version.

## Next
- DONE: report sent. Ideas: line-preserving stretch of a ctx object into frames; ctx from another partition
  level (loose object / legend -> panel); non-constant progressions; group-level roles; part permutation.
- not solved context tasks: 2ccd9fef (tile layout differs train/test), ba1aa698 (step not constant), db615bd4/9841fdad
  (scaled/stretched stamping), a416fc5b, b74ca5d1, 20fb2937, 15660dd6, 5ecac7f7, f18ec8cc, 4e7e0eb9 (grouped swap).
