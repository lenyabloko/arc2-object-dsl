"""Directed bounding-box adjacency: x adjacent_dir[d] y iff x lies immediately in direction d of y, i.e. the facing
sides of bbox(x) and bbox(y) touch with a gap of 0 cells and their projections on the other axis overlap.
Rows grow downward. With bbox = [r0, r1] x [c0, c1]:
  N: r1(x) + 1 == r0(y) and columns overlap      S: r0(x) - 1 == r1(y) and columns overlap
  E: c0(x) - 1 == c1(y) and rows overlap         W: c1(x) + 1 == c0(y) and rows overlap
The first argument ranges over all individuals, the second over objects only (README).

Grounding: contact is between bounding boxes, not pixels, so adjacent_dir does NOT imply rcc8_EC (two objects whose
bboxes touch face-to-face may have no 4-adjacent pixel pair, e.g. staggered shapes).

Subsumptions holding on every grid, per matched setting: adjacent_dir[d] ⊑ dir_rel[d] (same d) and hence
adjacent_dir[d=N|S] ⊑ aligned[axis=col], adjacent_dir[d=E|W] ⊑ aligned[axis=row]. The harness `subsumes` check
compares only the two default settings (it cannot bind d to d), so these are recorded under "param_subsumes"."""
import numpy as np

D = ("N", "S", "E", "W")


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


def adjacent_dir(grid, inds, bg, d="N"):
    (r0, r1, c0, c1), ok, obj = _bboxes(inds)
    if obj.size == 0: return {}
    R0, R1, C0, C1 = r0[obj][None, :], r1[obj][None, :], c0[obj][None, :], c1[obj][None, :]
    r0, r1, c0, c1 = r0[:, None], r1[:, None], c0[:, None], c1[:, None]
    if d == "N":   M = (r1 + 1 == R0) & (c0 <= C1) & (C0 <= c1)
    elif d == "S": M = (r0 - 1 == R1) & (c0 <= C1) & (C0 <= c1)
    elif d == "E": M = (c0 - 1 == C1) & (r0 <= R1) & (R0 <= r1)
    else:          M = (c1 + 1 == C0) & (r0 <= R1) & (R0 <= r1)
    M &= ok[:, None]
    return _to_role(M, obj)


ITEM = {"name": "adjacent_dir", "layer": 1, "iri": "qsr:adjacent_dir", "kind": "role", "params": {"d": list(D)},
        "subsumes": [],
        "param_subsumes": [["adjacent_dir", {"d": d}, "dir_rel", {"d": d}] for d in D]
                          + [["adjacent_dir", {"d": d}, "aligned", {"axis": "col" if d in "NS" else "row"}] for d in D],
        "definition": "x lies immediately in direction d of y (rows grow downward): the facing sides of their bounding "
                      "boxes touch with a gap of 0 cells and their projections on the other axis overlap. y ranges over "
                      "objects. Specialises dir_rel for the same d (bbox contact, not pixel contact).",
        "fn": adjacent_dir}
