"""Line family for card 2dd70a9a (test-blind; induced only from train pairs).

Reading: the grid holds many shapes of one majority colour (the obstacles) and two straight segments of
minority colour(s).  From one minority segment a path is drawn in the source's colour: it extends straight out
of one end of the segment along the segment's axis, and makes a 90-degree corner whenever the next cell is a
majority-colour shape (or the grid edge), so every corner rests against a majority shape ("connects" them).  It
stops when it runs into the other minority segment end-on, i.e. moving along that segment's own straight line.
"""
import heapq
from collections import Counter

CARD = "2dd70a9a"
LINE = ("connect as many majority color shapes by extending or making corners from one minority-colored segment "
        "until it meets the other minority-colored segment in streight line")
READING = {
    "generator": "From one end of the source minority segment, draw a straight line of the source's colour along "
                 "the segment's axis and turn a 90-degree corner (left or right) each time the next cell is a "
                 "majority-colour shape or the grid edge, so the corners bounce off majority shapes.",
    "stop": "The line stops when its next cell is the other minority segment and it is travelling along that "
            "segment's own axis (it meets it end-on in a straight line); of all such paths the one with the fewest "
            "corners (ties: shortest) is drawn, or with choice=shapes the one touching the most majority shapes; "
            "if no path exists the grid is unchanged.",
    "params": "source ∈ {the minority colour the training outputs paint with, either segment} · "
              "corner ∈ {only when blocked, when blocked or aligned with the target's axis} · "
              "choice ∈ {fewest corners then shortest, most majority shapes touched then fewest corners} · "
              "connectivity = 4",
    "participants": "Background = most frequent colour; majority colour = most frequent other colour, its "
                    "4-connected shapes are the walls; the two minority segments are the straight solid "
                    "4-connected components of the remaining colours (source and target); the path cells are "
                    "background cells.",
    "preconditions": "Same-size input/output; outputs only add cells of one colour on background; every input "
                     "has exactly two minority components, each a straight solid segment, and the painted colour "
                     "is the colour of one of them.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
MAX_CORNERS = 12          # search bound (structural), far above anything a straight-with-corners path needs
MAX_PATHS = 2000
MAX_STEPS = 40000      # search budget per source segment (keeps a 30x30 task well under the time limit)


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _comps(g, keep):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not keep(g[y][x]):
                continue
            c = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in D4:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c:
                        seen[p][q] = True
                        st.append((p, q))
            out.append((c, sorted(pix)))
    out.sort(key=lambda o: (o[1][0], o[0]))
    return out


def _segment(pix):
    """(cells, axis dirs, ends) for a straight solid segment, else None. axis None means a single cell."""
    ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
    r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if min(h, w) != 1 or len(pix) != h * w:
        return None
    if h == 1 and w == 1:
        return {"cells": set(pix), "axis": None, "ends": [((r0, c0), d) for d in D4]}
    if h == 1:
        return {"cells": set(pix), "axis": "h", "ends": [((r0, c0), (0, -1)), ((r0, c1), (0, 1))]}
    return {"cells": set(pix), "axis": "v", "ends": [((r0, c0), (-1, 0)), ((r1, c0), (1, 0))]}


def _parse(g):
    """bg, majority colour, list of minority segments (colour, seg) -- or None if the scene does not fit."""
    bg = _bg(g)
    cnt = Counter(v for r in g for v in r if v != bg)
    if len(cnt) < 2:
        return None
    maj = sorted(cnt.items(), key=lambda t: (-t[1], t[0]))[0][0]
    mins = _comps(g, lambda v: v != bg and v != maj)
    if len(mins) != 2:
        return None
    segs = []
    for c, pix in mins:
        s = _segment(pix)
        if s is None:
            return None
        segs.append((c, s))
    return bg, maj, segs


def _along(d, tgt):
    if tgt["axis"] is None:
        return True
    return (d[0] == 0) == (tgt["axis"] == "h")


def _on_axis(p, tgt):
    tcells = tgt["cells"]
    if tgt["axis"] is None:
        return any(p[0] == a or p[1] == b for a, b in tcells)
    if tgt["axis"] == "h":
        return p[0] == next(iter(tcells))[0]
    return p[1] == next(iter(tcells))[1]


def _best_path(g, bg, src, tgt, corner):
    """Exact fewest-corners-then-shortest corner-at-wall path (Dijkstra over (cell, heading)); (key, cells) or None."""
    H, W = len(g), len(g[0])
    tcells = tgt["cells"]
    heap, tick, done, parent = [], 0, set(), {}
    for end, d in src["ends"]:
        heapq.heappush(heap, (0, 0, tick, end, d, None)); tick += 1
    while heap:
        cn, ln, _, pos, d, par = heapq.heappop(heap)
        st = (pos, d, ln == 0)
        if st in done:
            continue
        done.add(st)
        parent[st] = par
        n = (pos[0] + d[0], pos[1] + d[1])
        if n in tcells and _along(d, tgt) and ln > 0:
            cells, s = [], st
            while s is not None:
                if s[2] is False and (not cells or cells[-1] != s[0]):
                    cells.append(s[0])
                s = parent[s]
            return (cn, ln), cells[::-1]
        free = 0 <= n[0] < H and 0 <= n[1] < W and g[n[0]][n[1]] == bg
        if free:
            heapq.heappush(heap, (cn, ln + 1, tick, n, d, st)); tick += 1
        if ln > 0 and (not free or (corner == "aligned" and _on_axis(pos, tgt) and not _along(d, tgt))):
            for nd in ((d[1], d[0]), (-d[1], -d[0])):
                heapq.heappush(heap, (cn + 1, ln, tick, pos, nd, st)); tick += 1
    return None


def _paths(g, bg, src, tgt, corner):
    """Simple corner-at-wall paths from src to tgt meeting it end-on (bounded DFS). Each: (cells list, corners)."""
    H, W = len(g), len(g[0])
    tcells = tgt["cells"]
    found = []
    steps = [0]

    def on_axis(p):
        return _on_axis(p, tgt)

    def run(pos, d, path, used, corners):
        k = len(path)
        _walk(pos, d, path, used, corners)
        for p in path[k:]:
            used.discard(p)
        del path[k:]

    def _walk(pos, d, path, used, corners):
        while True:
            steps[0] += 1
            if len(found) >= MAX_PATHS or steps[0] > MAX_STEPS:
                return
            n = (pos[0] + d[0], pos[1] + d[1])
            if n in tcells and _along(d, tgt) and path:
                found.append((list(path), corners))
                return
            inside = 0 <= n[0] < H and 0 <= n[1] < W
            free = inside and g[n[0]][n[1]] == bg and n not in used
            may_turn = bool(path) and corners < MAX_CORNERS and (
                not free or (corner == "aligned" and on_axis(pos) and not _along(d, tgt)))
            if may_turn:
                for nd in ((d[1], d[0]), (-d[1], -d[0])):
                    run(pos, nd, path, used, corners + 1)
            if not free:
                return
            pos = n
            path.append(n)
            used.add(n)

    for end, d in src["ends"]:
        run(end, d, [], set(), 0)
    return found


def _touch(g, maj_ids, cells):
    H, W = len(g), len(g[0])
    s = set()
    for a, b in cells:
        for dy, dx in D4:
            p, q = a + dy, b + dx
            if 0 <= p < H and 0 <= q < W and (p, q) in maj_ids:
                s.add(maj_ids[(p, q)])
    return len(s)


def _solve(g, source, corner, choice, paint_col):
    P = _parse(g)
    if P is None:
        return None
    bg, maj, segs = P
    if source == "colour":
        order = [i for i in (0, 1) if segs[i][0] == paint_col]
        if len(order) != 1:
            return None
    else:
        order = [0, 1]
    maj_ids = None
    if choice == "shapes":
        maj_ids = {}
        for k, (c, pix) in enumerate(_comps(g, lambda v: v == maj)):
            for p in pix:
                maj_ids[p] = k
    best = None
    for i in order:
        col, src = segs[i]
        tgt = segs[1 - i][1]
        if choice == "corners":
            r = _best_path(g, bg, src, tgt, corner)
            if r is not None and (best is None or r[0] < best[0]):
                best = (r[0], col, r[1])
            continue
        for cells, corners in _paths(g, bg, src, tgt, corner):
            key = (-_touch(g, maj_ids, cells), corners, len(cells))
            if best is None or key < best[0]:
                best = (key, col, cells)
    if best is None:
        return None
    out = [r[:] for r in g]
    for a, b in best[2]:
        out[a][b] = best[1]
    return out


def _make(source, corner, choice, paint_col):
    def fn(grid):
        r = _solve(grid, source, corner, choice, paint_col)
        return r if r is not None else [row[:] for row in grid]
    return fn


def fam(train):
    if not train:
        return
    paint = set()
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        P = _parse(gi)
        if P is None:
            return
        bg = P[0]
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    if a != bg:
                        return
                    paint.add(b)
    if len(paint) != 1:
        return
    pc = next(iter(paint))
    if not all(any(c == pc for c, _ in _parse(p["input"])[2]) for p in train):
        return
    found = []
    for si, source in enumerate(("colour", "either")):
        for ci, corner in enumerate(("blocked", "aligned")):
            for hi, choice in enumerate(("corners", "shapes")):
                fn = _make(source, corner, choice, pc)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except RecursionError:
                    ok = False
                if ok:
                    name = "corner_path[src=%s,corner=%s,choice=%s]" % (source, corner, choice)
                    found.append((10 + si + ci + hi, len(found), name, fn))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found:
        yield name, cost, fn


FAMILIES = [fam]
