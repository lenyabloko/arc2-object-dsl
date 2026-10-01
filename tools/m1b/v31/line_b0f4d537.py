"""Line family for card b0f4d537 -- reviewer (Len): homeomorphic stretch of the multicolour area.

Reading: a wall colour cuts the grid into full rectangles.  One of them (the most multicoloured) holds a small
pattern: a background with single rows / columns of line colour ("line rows / line columns" = rows / columns that
differ from the pattern's most frequent row / column).  A neighbouring rectangle with the same background holds tick
marks.  The pattern is stretched without tearing or reordering (a monotone surjection of output rows onto pattern
rows, and the same for columns): each line row / column lands on its tick, and every plain run of pattern rows /
columns is repeated to fill the gap between ticks, until the pattern has that area's shape.

Ticks (per grid, no constants):
  edge     : a non-background cell on the area's left/right border ticks its row, on the top/bottom border its column
  interior : non-background cells strictly inside the area tick their row and column
  any      : every non-background cell ticks its row and its column
An axis without ticks (and only then) spreads the pattern evenly: lines stay one cell, plain runs share the growth.
"""
from collections import Counter

CARD = "b0f4d537"
LINE = ("extract multicolor area and stretch homeomorphically untill it acquires the neighboring area shape "
        "of the same background")
READING = {
    "generator": "The multicoloured rectangle is cut out and stretched without tearing or reordering: its line "
                 "rows/columns are carried onto the rows/columns ticked in the neighbouring area of the same "
                 "background, and its plain background rows/columns are repeated to fill the gaps between them; "
                 "the output is the stretched pattern, the size of that area.",
    "stop": "Stretching stops when the pattern exactly covers the neighbouring area (its height and width) with "
            "every line on its tick; the area's bounds (the wall colour or the grid edge) fix the size.",
    "params": "ticks ∈ {edge, interior, any} · orient ∈ {as-is, auto (first of the 8 rotations/reflections whose "
              "line counts match the ticks)} · output ∈ {area, in-place}",
    "participants": "Wall: the colour whose removal leaves only full rectangles (4-connected); background: the most "
                    "frequent non-wall colour; pattern: the rectangle with strictly the most colours; target: the "
                    "largest other rectangle whose majority colour is the background (first that admits the "
                    "stretch); line rows/columns: pattern rows/columns differing from its most frequent row/column; "
                    "ticks: non-background cells of the target (edge: left/right border cells tick rows, top/bottom "
                    "border cells tick columns).",
    "preconditions": "Some colour splits the grid into full rectangles; one is uniquely most multicoloured and "
                     "contains the background; another, background-majority, has as many ticked rows (columns) as "
                     "the pattern has line rows (columns), or none on that axis; ticks keep the lines' order and "
                     "every plain run of the pattern maps to a non-empty gap at least as long (and line-adjacent "
                     "lines to adjacent ticks).",
}

TICKS = ("edge", "interior", "any")
ORIENTS = ("as-is", "auto")
OUTPUTS = ("area", "in-place")


def _mode(vals):
    c = Counter(vals)
    best = max(c.values())
    return min(k for k, v in c.items() if v == best)


def _components(g, wall):
    h, w = len(g), len(g[0])
    seen = [[False] * w for _ in range(h)]
    comps = []
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == wall:
                continue
            seen[r][c] = True
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = y + dy, x + dx
                    if 0 <= a < h and 0 <= b < w and not seen[a][b] and g[a][b] != wall:
                        seen[a][b] = True
                        stack.append((a, b))
            comps.append(cells)
    return comps


def _regions(g):
    """(bg, pattern rect, [target rects]) for the first wall colour that splits g into full rectangles."""
    cnt = Counter(v for row in g for v in row)
    for wall in sorted(cnt, key=lambda k: (-cnt[k], k)):
        comps = _components(g, wall)
        if len(comps) < 2:
            continue
        rects = []
        for cells in comps:
            ys = [y for y, _ in cells]
            xs = [x for _, x in cells]
            r0, r1, c0, c1 = min(ys), max(ys) + 1, min(xs), max(xs) + 1
            if (r1 - r0) * (c1 - c0) != len(cells):
                rects = None
                break
            rects.append((r0, r1, c0, c1))
        if not rects:
            continue
        bg = _mode([v for row in g for v in row if v != wall])
        ncol = [len({g[r][c] for r in range(a, b) for c in range(x, y)}) for a, b, x, y in rects]
        top = max(ncol)
        if ncol.count(top) != 1 or top < 2:
            continue
        pi = ncol.index(top)
        pr = rects[pi]
        if not any(g[r][c] == bg for r in range(pr[0], pr[1]) for c in range(pr[2], pr[3])):
            continue
        targets = []
        for i, (a, b, x, y) in enumerate(rects):
            if i != pi and _mode([g[r][c] for r in range(a, b) for c in range(x, y)]) == bg:
                targets.append((a, b, x, y))
        if not targets:
            continue
        targets.sort(key=lambda t: (-(t[1] - t[0]) * (t[3] - t[2]), t[0], t[2]))
        return bg, pr, targets
    return None


def _line_idx(vecs, bg):
    """Indices of line rows: rows differing from the most frequent row (ties: fewer non-bg cells, then first)."""
    cnt = Counter(vecs)
    best = max(cnt.values())
    cands = [v for v in vecs if cnt[v] == best]
    neutral = min(cands, key=lambda v: sum(1 for x in v if x != bg))
    return [i for i, v in enumerate(vecs) if v != neutral]


def _ticks(T, bg, mode):
    H, W = len(T), len(T[0])
    rows, cols = set(), set()
    for r in range(H):
        for c in range(W):
            if T[r][c] == bg:
                continue
            if mode == "edge":
                if c == 0 or c == W - 1:
                    rows.add(r)
                if r == 0 or r == H - 1:
                    cols.add(c)
            elif mode == "interior":
                if 0 < r < H - 1 and 0 < c < W - 1:
                    rows.add(r)
                    cols.add(c)
            else:
                rows.add(r)
                cols.add(c)
    return sorted(rows), sorted(cols)


def _spread(src, q):
    """q output cells onto the pattern indices src (each >= 1), earlier ones take the remainder."""
    p = len(src)
    if (p == 0) != (q == 0) or q < p:
        return None
    out = []
    if p:
        base, rem = divmod(q, p)
        for i, s in enumerate(src):
            out += [s] * (base + (1 if i < rem else 0))
    return out


def _axis_map(n, lines, size, ticks):
    """Monotone surjection output index -> pattern index carrying lines[i] onto ticks[i]; None if impossible."""
    if not ticks:
        if size < n:
            return None
        plain = [i for i in range(n) if i not in set(lines)]
        if not plain:
            return list(range(n)) if size == n else None
        base, rem = divmod(size - len(lines), len(plain))
        grow = {s: base + (1 if j < rem else 0) for j, s in enumerate(plain)}
        out = []
        for i in range(n):
            out += [i] * (grow[i] if i in grow else 1)
        return out
    if len(ticks) != len(lines):
        return None
    out = []
    pl, pt = -1, -1
    for l, t in list(zip(lines, ticks)) + [(n, size)]:
        seg = _spread(list(range(pl + 1, l)), t - pt - 1)
        if seg is None:
            return None
        out += seg
        if l < n:
            out.append(l)
        pl, pt = l, t
    return out if len(out) == size else None


def _dihedral(P):
    t = [list(r) for r in zip(*P)]
    yield P
    yield [list(r) for r in zip(*P[::-1])]                     # rot90 cw
    yield [r[::-1] for r in P[::-1]]                           # rot180
    yield [list(r) for r in zip(*P)][::-1]                     # rot270 cw
    yield [r[::-1] for r in P]                                 # mirror left-right
    yield P[::-1]                                              # mirror top-bottom
    yield t                                                    # transpose
    yield [r[::-1] for r in t[::-1]]                           # anti-transpose


def _stretch(P, T, bg, ticks, orient):
    H, W = len(T), len(T[0])
    trows, tcols = _ticks(T, bg, ticks)
    for Q in (_dihedral(P) if orient == "auto" else [P]):
        h, w = len(Q), len(Q[0])
        rmap = _axis_map(h, _line_idx([tuple(r) for r in Q], bg), H, trows)
        cmap = _axis_map(w, _line_idx([tuple(c) for c in zip(*Q)], bg), W, tcols)
        if rmap is not None and cmap is not None:
            return [[Q[rmap[r]][cmap[c]] for c in range(W)] for r in range(H)]
    return None


def stretch_area(g, ticks, orient, output):
    reg = _regions(g)
    if reg is None:
        return None
    bg, (a, b, x, y), targets = reg
    P = [list(g[r][x:y]) for r in range(a, b)]
    for (r0, r1, c0, c1) in targets:
        T = [list(g[r][c0:c1]) for r in range(r0, r1)]
        S = _stretch(P, T, bg, ticks, orient)
        if S is None:
            continue
        if output == "area":
            return S
        out = [list(row) for row in g]
        for r in range(r0, r1):
            out[r][c0:c1] = S[r - r0]
        return out
    return None


def fam(train):
    if not train or any(not p["input"] or not p["input"][0] for p in train):
        return
    if any(_regions(p["input"]) is None for p in train):
        return
    for i, ticks in enumerate(TICKS):
        for j, orient in enumerate(ORIENTS):
            for k, output in enumerate(OUTPUTS):
                fn = (lambda t, o, u: (lambda grid: stretch_area(grid, t, o, u)))(ticks, orient, output)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("stretch_area[ticks=%s,orient=%s,output=%s]" % (ticks, orient, output),
                           1 + i + j + k, fn)


FAMILIES = [fam]
