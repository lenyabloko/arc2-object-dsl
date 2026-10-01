"""Line family for card d017b73f (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds several components laid out one after another along an axis, each separated from
the next by empty background. Every component is a path with two ends: a start end (the side facing the
previous component) and a finish end (the side facing the next one). The components are attached into one
chain: the first stays where it is, and each following one is shifted so that its start cell sits directly
next to (edge to edge, never only corner to corner) the finish cell of the previous one, one step further
along the axis. The empty gaps disappear, so the output is as long as the chain.

Ends of a component: if it is a simple path, its two degree-1 cells (start = the one nearer the previous
component, finish = the one nearer the next). Otherwise the unique cell in its first / last line along the
axis, or the unique degree <= 1 cell there.
"""

CARD = "d017b73f"
LINE = "attach components from both ends without touching corners"
READING = {
    "generator": "Shift every component after the first so that its start end sits edge to edge (never only "
                 "corner to corner) right after the finish end of the previous component, chaining all of them "
                 "into one path; the empty gaps between them disappear.",
    "stop": "One pass over the components in order along the axis; the output ends at the last cell of the last "
            "component (perpendicular size kept, or the chain's bounding box, as induced from train).",
    "params": "axis/anchor in {left-to-right first fixed, right-to-left last fixed, top-to-bottom, bottom-to-top} "
              "· connectivity in {4, 8} · size in {keep cross size and compact length, chain bounding box, "
              "keep input size} · bg = most frequent colour of the grid",
    "participants": "Components: connected groups of non-background cells (any colours), ordered along the axis; "
                    "their extents along the axis must not overlap. Ends: the two degree-1 cells of a path "
                    "component (else the unique cell, or unique degree<=1 cell, in its first/last line).",
    "preconditions": "Every train input has at least two components whose extents along the axis are disjoint, "
                     "each with identifiable start/finish ends; the chained result fits without overlapping "
                     "cells and the output size is consistent with one size mode.",
}


# ---------------------------------------------------------------- transforms (chain runs left to right)

def _transpose(g):
    return [list(r) for r in zip(*g)]


def _fliplr(g):
    return [list(r[::-1]) for r in g]


_TF = [
    ("lr", lambda g: [list(r) for r in g], lambda g: g),
    ("rl", _fliplr, _fliplr),
    ("tb", _transpose, _transpose),
    ("bt", lambda g: _fliplr(_transpose(g)), lambda g: _transpose(_fliplr(g))),
]


# ---------------------------------------------------------------- helpers

def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _nbrs(conn):
    if conn == 4:
        return ((-1, 0), (1, 0), (0, -1), (0, 1))
    return tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)


def _pieces(g, bg, conn):
    """Connected non-bg components, ordered by first column; None unless column extents are disjoint."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    N = _nbrs(conn)
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            seen[r][c] = True
            st, cells = [(r, c)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for dr, dc in N:
                    x, y = a + dr, b + dc
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            out.append(sorted(cells))
    out.sort(key=lambda cs: (min(c for _, c in cs), min(r for r, _ in cs)))
    for i in range(len(out) - 1):
        if max(c for _, c in out[i]) >= min(c for _, c in out[i + 1]):
            return None
    return out


def _ends(cells, conn):
    """List of (start, finish) options in preference order, or [] when the ends cannot be identified."""
    S = set(cells)
    if len(S) == 1:
        return [(cells[0], cells[0])]
    N = _nbrs(conn)
    deg = {p: sum((p[0] + dr, p[1] + dc) in S for dr, dc in N) for p in S}
    ep = sorted(p for p in S if deg[p] == 1)
    if len(ep) == 2 and all(deg[p] == 2 for p in S if p not in ep):       # simple path
        a, b = ep
        if a[1] < b[1]:
            return [(a, b)]
        if b[1] < a[1]:
            return [(b, a)]
        return [(a, b), (b, a)]                                           # path across the axis: both orders

    def pick(col):
        L = sorted(p for p in S if p[1] == col)
        if len(L) == 1:
            return L[0]
        L1 = [p for p in L if deg[p] <= 1]
        return L1[0] if len(L1) == 1 else None

    s = pick(min(c for _, c in S))
    f = pick(max(c for _, c in S))
    if s is None or f is None:
        return []
    return [(s, f)]


def _chain(g, conn, size):
    bg = _bg(g)
    P = _pieces(g, bg, conn)
    if P is None or len(P) < 2:
        raise ValueError("no chainable components")
    H, W = len(g), len(g[0])
    placed = {}                                                           # (r, c) -> colour
    fin = None
    for i, cells in enumerate(P):
        opts = _ends(cells, conn)
        if not opts:
            raise ValueError("ends not identifiable")
        if i == 0:
            s, f = opts[0]
            dr, dc = 0, 0
        else:
            best = None
            for s, f in opts:                                             # prefer the smallest displacement
                d = (abs(fin[0] - s[0]), s[0])
                if best is None or d < best[0]:
                    best = (d, s, f)
            _, s, f = best
            dr, dc = fin[0] - s[0], fin[1] + 1 - s[1]
        for r, c in cells:
            q = (r + dr, c + dc)
            if q in placed:
                raise ValueError("overlap")
            placed[q] = g[r][c]
        fin = (f[0] + dr, f[1] + dc)
    rows = [r for r, _ in placed]
    cols = [c for _, c in placed]
    c0 = min(cols)
    if size == "bbox":
        r0, oh, ow = min(rows), max(rows) - min(rows) + 1, max(cols) - c0 + 1
    else:
        oh = H
        r0 = 0
        if min(rows) < 0 or max(rows) >= H:                               # keep the chain inside the rows
            if max(rows) - min(rows) + 1 > H:
                raise ValueError("chain too tall")
            r0 = min(rows) if min(rows) < 0 else max(rows) - H + 1
        if size == "keep":
            ow = W
            c0 = 0                                                        # first component keeps its column
            if max(cols) >= W:
                c0 = max(cols) - W + 1
            if min(cols) - c0 < 0:
                raise ValueError("chain too long")
        else:
            ow = max(cols) - c0 + 1
    out = [[bg] * ow for _ in range(oh)]
    for (r, c), v in placed.items():
        out[r - r0][c - c0] = v
    return out


def _make(tf, inv, conn, size):
    def fn(grid):
        return inv(_chain(tf(grid), conn, size))
    return fn


_SIZES = ("compact", "bbox", "keep")


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs:
        return
    k = 0
    for tname, tf, inv in _TF:
        for conn in (4, 8):
            ok_pre = True
            for i, _ in pairs:
                g = tf(i)
                P = _pieces(g, _bg(g), conn)
                if P is None or len(P) < 2 or any(not _ends(cs, conn) for cs in P):
                    ok_pre = False
                    break
            if not ok_pre:
                continue
            for size in _SIZES:
                fn = _make(tf, inv, conn, size)
                try:
                    fits = all(fn(i) == o for i, o in pairs)
                except Exception:
                    fits = False
                if fits:
                    yield ("attach_ends_%s_c%d_%s" % (tname, conn, size), 10 + k, fn)
                k += 1


FAMILIES = [fam]
