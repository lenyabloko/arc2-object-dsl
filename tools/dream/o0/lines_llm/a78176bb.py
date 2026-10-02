"""Reviewer line family for ARC card a78176bb (shift filler into a parallel line).

The input holds one full monochrome straight line (border to border; a
diagonal in the card, but rows / columns / anti-diagonals are handled the
same way) with filler blobs attached to it.  The filler is erased, and on
every side of the line that carried filler a new full line of the line's
colour is drawn parallel to it, ``gap`` empty parallels beyond the filler's
farthest cell.  ``gap`` is induced from the training pairs.
"""

CARD = "a78176bb"
LINE = ("The filler triangles attached to the full diagonal line are erased, and on each side that had "
        "filler a new full line parallel to the diagonal is drawn just beyond the triangle's farthest "
        "cell (gap induced from training).")

READING = {
    "generator": "Erase the filler cells attached to the full straight line, and on each side of the line "
                 "that had filler draw a new full line of the line's colour parallel to it, placed gap+1 "
                 "parallels beyond the filler's farthest cell on that side; the original line stays.",
    "stop": "Each new line runs border to border (clipped to the grid); exactly one new line per side "
            "that had filler, none on a side without filler.",
    "params": "direction ∈ {row, column, diagonal, anti-diagonal} (read from the input's line) · "
              "gap ∈ {0, 1, …, max(H, W)} (induced: every value reproducing all train pairs, smallest first)",
    "participants": "Background = most frequent colour; the line = the longest straight line (any of the "
                    "4 directions) whose every in-grid cell has one non-background colour; filler = "
                    "8-connected components of the remaining non-background cells that touch the line "
                    "(8-adjacency); side and distance of a filler cell = signed index difference between "
                    "its parallel and the line's.",
    "preconditions": "Same grid size in and out; a unique longest full monochrome line of length >= 2 "
                     "exists; at least one filler cell is attached to it.",
}

_DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# direction name -> index function k(r, c) identifying the parallel a cell lies on
_KEYS = {
    "row": lambda r, c: r,
    "col": lambda r, c: c,
    "diag": lambda r, c: c - r,
    "anti": lambda r, c: c + r,
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _parallels(h, w, dname):
    key = _KEYS[dname]
    lines = {}
    for r in range(h):
        for c in range(w):
            lines.setdefault(key(r, c), []).append((r, c))
    return lines


def _find_line(g, bg):
    """Unique longest full monochrome straight line -> (dname, k, colour, cells) or None."""
    h, w = len(g), len(g[0])
    cands = []
    for dname in ("row", "col", "diag", "anti"):
        for k, cells in _parallels(h, w, dname).items():
            if len(cells) < 2:
                continue
            cols = {g[r][c] for r, c in cells}
            if len(cols) == 1:
                col = next(iter(cols))
                if col != bg:
                    cands.append((len(cells), dname, k, col, cells))
    if not cands:
        return None
    best = max(x[0] for x in cands)
    top = [x for x in cands if x[0] == best]
    if len(top) != 1:
        return None
    _, dname, k, col, cells = top[0]
    return dname, k, col, cells


def _analyse(g):
    h, w = len(g), len(g[0])
    bg = _bg(g)
    found = _find_line(g, bg)
    if found is None:
        return None
    dname, k0, col, cells = found
    on_line = set(cells)
    seen = set()
    filler = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or (r, c) in on_line or g[r][c] == bg:
                continue
            seen.add((r, c))
            stack, comp, touches = [(r, c)], [], False
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in _DIRS8:
                    ny, nx = y + dy, x + dx
                    if not (0 <= ny < h and 0 <= nx < w):
                        continue
                    if (ny, nx) in on_line:
                        touches = True
                    elif g[ny][nx] != bg and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            if touches:
                filler.extend(comp)
    if not filler:
        return None
    key = _KEYS[dname]
    far = {}  # side sign -> farthest distance
    for r, c in filler:
        d = key(r, c) - k0
        if d == 0:
            continue
        s = 1 if d > 0 else -1
        far[s] = max(far.get(s, 0), abs(d))
    if not far:
        return None
    return bg, dname, k0, col, filler, far


def _apply(g, gap):
    info = _analyse(g)
    if info is None:
        return None
    bg, dname, k0, col, filler, far = info
    h, w = len(g), len(g[0])
    out = [row[:] for row in g]
    for r, c in filler:
        out[r][c] = bg
    lines = _parallels(h, w, dname)
    for s, dist in sorted(far.items()):
        k = k0 + s * (dist + gap + 1)
        for r, c in lines.get(k, []):
            out[r][c] = col
    return out


def _make(gap):
    def fn(grid):
        res = _apply(grid, gap)
        return [row[:] for row in grid] if res is None else res
    return fn


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        if _analyse(gi) is None:
            return
    maxdim = max(max(len(p["input"]), len(p["input"][0])) for p in train)
    for gap in range(0, maxdim + 1):
        if all(_apply(p["input"], gap) == p["output"] for p in train):
            yield ("filler_to_parallel_line_gap%d" % gap, 3 + gap, _make(gap))


FAMILIES = [fam]
