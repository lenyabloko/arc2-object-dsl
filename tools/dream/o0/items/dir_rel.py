"""Cardinal direction relation on bounding boxes (projection-based cardinal directions, Frank 1991; cardinal direction
calculus on minimum bounding rectangles, Goyal & Egenhofer). x d y reads "x lies to the d of y".

Grid reading: rows grow downward, so N = smaller row index, S = larger row index, E = larger column index,
W = smaller column index. With bbox(x) = [r0, r1] x [c0, c1]:
  above(x, y) = r1(x) < r0(y)     below(x, y) = r0(x) > r1(y)
  left(x, y)  = c1(x) < c0(y)     right(x, y) = c0(x) > c1(y)
  rows_ov = not above and not below (x and y share a row);  cols_ov = not left and not right (share a column)
  N = above & cols_ov   S = below & cols_ov   E = right & rows_ov   W = left & rows_ov
  NE = above & right    NW = above & left     SE = below & right    SW = below & left
The eight settings are pairwise disjoint; their union is exactly the pairs whose bounding boxes do not intersect.
The first argument ranges over all individuals, the second over objects only (README).

Subsumptions holding on every grid (per matched parameter setting; the harness `subsumes` check compares only the
two default settings, so they are recorded under "param_subsumes" and not in "subsumes"):
  dir_rel[d=N], dir_rel[d=S] ⊑ aligned[axis=col];  dir_rel[d=E], dir_rel[d=W] ⊑ aligned[axis=row]."""
import numpy as np

D = ("N", "S", "E", "W", "NE", "NW", "SE", "SW")


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


def dir_rel(grid, inds, bg, d="N"):
    (r0, r1, c0, c1), ok, obj = _bboxes(inds)
    if obj.size == 0: return {}
    R0, R1, C0, C1 = r0[obj][None, :], r1[obj][None, :], c0[obj][None, :], c1[obj][None, :]
    r0, r1, c0, c1 = r0[:, None], r1[:, None], c0[:, None], c1[:, None]
    v = d[0] if d[0] in "NS" else ""; h = d[-1] if d[-1] in "EW" else ""
    if v: V = (r1 < R0) if v == "N" else (r0 > R1)   # x entirely above / below y
    if h: H = (c0 > C1) if h == "E" else (c1 < C0)   # x entirely right / left of y
    if v and h:
        M = V & H
    elif v:
        M = V & (c0 <= C1) & (C0 <= c1)              # column projections overlap
    else:
        M = H & (r0 <= R1) & (R0 <= r1)              # row projections overlap
    M &= ok[:, None]
    return _to_role(M, obj)


ITEM = {"name": "dir_rel", "layer": 1, "iri": "qsr:cardinal_direction", "kind": "role", "params": {"d": list(D)},
        "subsumes": [],
        "param_subsumes": [["dir_rel", {"d": "N"}, "aligned", {"axis": "col"}], ["dir_rel", {"d": "S"}, "aligned", {"axis": "col"}],
                           ["dir_rel", {"d": "E"}, "aligned", {"axis": "row"}], ["dir_rel", {"d": "W"}, "aligned", {"axis": "row"}]],
        "definition": "x lies strictly in direction d of y on bounding boxes (rows grow downward): N/S = x's bbox entirely "
                      "above/below y's and their column projections overlap; E/W = entirely right/left and row projections "
                      "overlap; NE/NW/SE/SW = entirely above/below and entirely right/left. y ranges over objects.",
        "fn": dir_rel}
