"""Axis alignment on bounding boxes: x aligned[axis] y iff the projections of bbox(x) and bbox(y) on that axis overlap,
i.e. x and y share at least one row (axis=row: r0(x) <= r1(y) and r0(y) <= r1(x)) or at least one column
(axis=col: c0(x) <= c1(y) and c0(y) <= c1(x)). Interval overlap in Allen's sense (any relation other than
before / after / meets-with-gap; on integer cells "meets" is not overlap). Irreflexive (x != y); the first argument
ranges over all individuals, the second over objects only (README).

This is the generic parent of the ray-type relations: on_ray / between (Layer 1) specialise it. On every grid
dir_rel[d=N|S] ⊑ aligned[axis=col] and dir_rel[d=E|W] ⊑ aligned[axis=row] (recorded in dir_rel's "param_subsumes";
the harness `subsumes` check compares only default settings)."""
import numpy as np


def _bboxes(inds):
    r0, r1, c0, c1, ok, obj = [], [], [], [], [], []
    for k, x in enumerate(inds):
        p = x["pix"]
        if len(p) == 1:
            (y, c), = p
            r0.append(y); r1.append(y); c0.append(c); c1.append(c); ok.append(True)
        elif p:
            ys = [q[0] for q in p]; xs = [q[1] for q in p]
            r0.append(min(ys)); r1.append(max(ys)); c0.append(min(xs)); c1.append(max(xs)); ok.append(True)
        else:
            r0.append(0); r1.append(0); c0.append(0); c1.append(0); ok.append(False)
        if x.get("kind") == "object" and ok[-1]: obj.append(k)
    return (np.array(r0), np.array(r1), np.array(c0), np.array(c1)), np.array(ok, dtype=bool), np.array(obj, dtype=np.int64)


def _to_role(M, obj):
    ii, jj = np.nonzero(M)
    if ii.size == 0: return {}
    cuts = (np.flatnonzero(np.diff(ii)) + 1).tolist()
    starts = [0] + cuts; ends = cuts + [int(ii.size)]
    jl = obj[jj].tolist(); rl = ii[starts].tolist()
    return {r: set(jl[a:b]) for r, a, b in zip(rl, starts, ends)}


def aligned(grid, inds, bg, axis="row"):
    (r0, r1, c0, c1), ok, obj = _bboxes(inds)
    if obj.size == 0: return {}
    lo, hi = (r0, r1) if axis == "row" else (c0, c1)
    M = (lo[:, None] <= hi[obj][None, :]) & (lo[obj][None, :] <= hi[:, None])
    M &= ok[:, None]
    M[obj, np.arange(obj.size)] = False                 # irreflexive
    return _to_role(M, obj)


ITEM = {"name": "aligned", "layer": 1, "iri": "qsr:aligned", "kind": "role", "params": {"axis": ["row", "col"]},
        "subsumes": [],
        "definition": "x and y (x != y) share at least one row (axis=row) or one column (axis=col): their bounding-box "
                      "projections on that axis overlap. y ranges over objects. Parent of on_ray / between.",
        "fn": aligned}
