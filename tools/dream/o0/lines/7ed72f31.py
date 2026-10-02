"""Line family for card 7ed72f31 (test-blind; written from the reviewer's line and train pairs only).

Reading: every multicolour shape on the background carries a short segment of one shared "axis"
colour. That segment is a mirror: the rest of the shape is reflected across it and the reflected
copy is drawn, so the shape becomes symmetric about the segment. A horizontal segment mirrors
across its row, a vertical one across its column, a diagonal one across its diagonal, and a
single axis cell acts as a point mirror (180-degree turn about that cell).
"""

CARD = "7ed72f31"
LINE = "use colored segment as a mirror symmetry axis for completing each multicolor shape"
READING = {
    "generator": "For each multicolour shape, reflect its non-axis cells across the shape's axis-coloured segment "
                 "(across the row / column / diagonal it lies on, or through the cell when the segment is a single "
                 "cell) and paint the reflected copy in the same colours.",
    "stop": "One reflection per shape; reflected cells falling outside the grid are dropped; the original shape and "
            "the segment are kept as they are.",
    "params": "axis colour in {non-background colours present in every train input} · connectivity in {8, 4} · "
              "single-cell segment in {point mirror, ignore} · paint in {background cells only, overwrite}",
    "participants": "Background = most frequent colour of the grid. Shapes = connected components of non-background "
                    "cells (all colours together). Segment = the axis-coloured cells of a shape (one connected piece "
                    "lying on a row, column or diagonal); the mirrored part = the shape's other cells. If a shape "
                    "holds several segments, each non-axis piece is mirrored across the one segment it touches.",
    "preconditions": "Same input/output size; every train input has at least one shape made of a straight "
                     "axis-coloured segment plus cells of another colour; outputs only add cells.",
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _nbrs(conn):
    if conn == 8:
        return [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
    return [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _components(cells, conn):
    """Connected components of a set of (r, c) cells, deterministic order."""
    cells = set(cells)
    seen, out = set(), []
    D = _nbrs(conn)
    for p in sorted(cells):
        if p in seen:
            continue
        comp, stack = [], [p]
        seen.add(p)
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for dr, dc in D:
                q = (r + dr, c + dc)
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        out.append(sorted(comp))
    return out


def _mirror(seg, single):
    """Return a reflection function for a straight segment, or None if the segment is not straight."""
    if len(seg) == 1:
        if single != "point":
            return None
        r0, c0 = seg[0]
        return lambda r, c: (2 * r0 - r, 2 * c0 - c)
    rs = {r for r, _ in seg}
    cs = {c for _, c in seg}
    n = len(seg)
    if len(rs) == 1 and max(cs) - min(cs) + 1 == n:
        r0 = seg[0][0]
        return lambda r, c: (2 * r0 - r, c)
    if len(cs) == 1 and max(rs) - min(rs) + 1 == n:
        c0 = seg[0][1]
        return lambda r, c: (r, 2 * c0 - c)
    d = {r - c for r, c in seg}
    if len(d) == 1 and max(rs) - min(rs) + 1 == n:
        k = seg[0][0] - seg[0][1]
        return lambda r, c: (c + k, r - k)
    s = {r + c for r, c in seg}
    if len(s) == 1 and max(rs) - min(rs) + 1 == n:
        t = seg[0][0] + seg[0][1]
        return lambda r, c: (t - c, t - r)
    return None


def _jobs(g, axis, conn, single):
    """List of (mirror_fn, cells) pairs: the cells to reflect and how."""
    H, W = len(g), len(g[0])
    bg = _bg(g)
    if axis == bg:
        return bg, []
    fg = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    jobs = []
    D = _nbrs(conn)
    for comp in _components(fg, conn):
        ax = [p for p in comp if g[p[0]][p[1]] == axis]
        rest = [p for p in comp if g[p[0]][p[1]] != axis]
        if not ax or not rest:
            continue
        segs = _components(ax, conn)
        if len(segs) == 1:
            f = _mirror(segs[0], single)
            if f is not None:
                jobs.append((f, rest))
            continue
        seg_of = {}
        for i, sgm in enumerate(segs):
            for p in sgm:
                seg_of[p] = i
        for piece in _components(rest, conn):
            touch = set()
            for r, c in piece:
                for dr, dc in D:
                    q = (r + dr, c + dc)
                    if q in seg_of:
                        touch.add(seg_of[q])
            if len(touch) == 1:
                f = _mirror(segs[touch.pop()], single)
                if f is not None:
                    jobs.append((f, piece))
    return bg, jobs


def _make(axis, conn, single, paint):
    def fn(g):
        H, W = len(g), len(g[0])
        bg, jobs = _jobs(g, axis, conn, single)
        out = [row[:] for row in g]
        for f, cells in jobs:
            for r, c in cells:
                rr, cc = f(r, c)
                if 0 <= rr < H and 0 <= cc < W:
                    if paint == "overwrite" or g[rr][cc] == bg:
                        out[rr][cc] = g[r][c]
        return out
    return fn


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    # axis colour candidates: non-background colours present in every train input
    cands = None
    for p in train:
        g = p["input"]
        bg = _bg(g)
        cols = {v for row in g for v in row if v != bg}
        cands = cols if cands is None else cands & cols
    if not cands:
        return

    # rank candidates by how many multicolour shapes (8-conn) they take part in across train inputs
    def score(a):
        s = 0
        for p in train:
            g = p["input"]
            bg = _bg(g)
            fg = [(r, c) for r in range(len(g)) for c in range(len(g[0])) if g[r][c] != bg]
            for comp in _components(fg, 8):
                colset = {g[r][c] for r, c in comp}
                if a in colset and len(colset) > 1:
                    s += 1
        return s

    axes = sorted(cands, key=lambda a: (-score(a), a))
    # precondition: under some axis colour, every train input has at least one mirror job
    progs = []
    for ai, a in enumerate(axes):
        for ci, conn in enumerate((8, 4)):
            for si, single in enumerate(("point", "ignore")):
                if not all(_jobs(p["input"], a, conn, single)[1] for p in train):
                    continue
                for pi, paint in enumerate(("bg_only", "overwrite")):
                    name = "mirror_shape_across_segment[axis=%d,conn=%d,single=%s,paint=%s]" % (a, conn, single, paint)
                    progs.append((name, 1 + ai + ci + si + pi, _make(a, conn, single, paint)))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
