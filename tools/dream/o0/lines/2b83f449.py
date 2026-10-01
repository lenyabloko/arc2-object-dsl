"""Reviewer line for 2b83f449 (Len): "reorient free colored segments in orthogonal direction and recolor all of them into another fixed color".
Implemented literally, test-blind (train pairs only):
  generator      every free straight segment of the segment colour (odd length L) is turned 90 degrees about its middle
                 cell: the new segment (same length, centred on the old middle cell) is painted in the induced new colour,
                 the vacated cells of the old segment take the induced fill colour.  Side effect (from the training
                 pairs): marker cells (induced colour, e.g. the row-end caps) slide through the maze of fill/marker cells
                 to the lowest run of their connected region and stack there from the run's wall-side end.
  stop           each segment is redrawn once; each marker moves once
  params         orient ∈ {id, flip_v, transpose, transpose_flip} (fixes segment axis and slide direction)
                 · markers ∈ {slide, keep}
  participants   segment colour = colour present in every train input and absent from every train output; new colour =
                 the colour of the reoriented middle cells in the train outputs; fill colour = train-output colour of the
                 vacated cells; marker colour = the other colour whose cells move between input and output
  preconditions  every segment-colour component is a straight 1xL line along the canonical axis with L odd >= 3 and the
                 induced colours are unique and consistent over all training pairs"""
from collections import Counter

CARD = "2b83f449"
LINE = "reorient free colored segments in orthogonal direction and recolor all of them into another fixed color"
READING = {
    "generator": "Each free straight segment is turned 90 degrees about its middle cell: a segment of the same length, "
                 "centred on the old middle cell, is painted in a fixed new colour, and the vacated cells take the fill "
                 "colour of the surrounding strips; marker cells (the row-end caps) then slide down through the "
                 "connected strip region to its lowest run and stack at that run's wall-side end.",
    "stop": "Every segment is redrawn exactly once; every marker moves once, to the lowest run of its region.",
    "params": "orient ∈ {id, flip_v, transpose, transpose_flip} · markers ∈ {slide, keep}",
    "participants": "Segment colour = colour present in every train input and absent from every train output; segments = "
                    "its 4-connected components; new colour = train-output colour at the segments' middle cells; fill "
                    "colour = train-output colour at the vacated segment cells; marker colour = the remaining colour "
                    "whose cell positions change; regions = 4-connected components of fill/marker cells after redrawing.",
    "preconditions": "Every segment is a straight 1xL line (L odd, >= 3) along one axis, the segment/new/fill colours are "
                     "unique and consistent over all training pairs.",
}


# ---------------------------------------------------------------- grid transforms
def _T(g):
    return [list(r) for r in zip(*g)]


def _V(g):
    return [list(r) for r in g[::-1]]


_ORIENTS = [
    ("id", lambda g: [list(r) for r in g], lambda g: [list(r) for r in g]),
    ("flip_v", _V, _V),
    ("transpose", _T, _T),
    ("transpose_flip", lambda g: _V(_T(g)), lambda g: _T(_V(g))),
]


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not pred(g[y][x]):
                continue
            seen[y][x] = True
            st, cells = [(y, x)], []
            while st:
                cy, cx = st.pop()
                cells.append((cy, cx))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and pred(g[ny][nx]):
                        seen[ny][nx] = True
                        st.append((ny, nx))
            out.append(sorted(cells))
    return out


def _segments(g, seg):
    """Horizontal odd segments of colour seg in canonical orientation, or None if precondition fails."""
    segs = []
    for cells in _comps(g, lambda v: v == seg):
        rows = {y for y, _ in cells}
        xs = sorted(x for _, x in cells)
        if len(rows) != 1 or len(xs) < 3 or len(xs) % 2 == 0:
            return None
        segs.append((cells[0][0], xs))
    return segs


def _reorient(g, seg, new, fill):
    segs = _segments(g, seg)
    if segs is None:
        return None, None
    H, W = len(g), len(g[0])
    out = [list(r) for r in g]
    for r, xs in segs:
        for x in xs:
            out[r][x] = fill
    for r, xs in segs:
        c = xs[len(xs) // 2]
        h = len(xs) // 2
        for y in range(r - h, r + h + 1):
            if 0 <= y < H:
                out[y][c] = new
    return out, segs


def _slide(g, marker, fill, new):
    """Markers slide down through the fill/marker region to its lowest run, stacking from the wall-side end."""
    H, W = len(g), len(g[0])
    out = [list(r) for r in g]
    for cells in _comps(g, lambda v: v == fill or v == marker):
        marks = [(y, x) for y, x in cells if g[y][x] == marker]
        if not marks:
            continue
        cset = set(cells)
        bot = max(y for y, _ in cells)
        xs = sorted(x for y, x in cells if y == bot)
        runs, cur = [], [xs[0]]
        for x in xs[1:]:
            if x == cur[-1] + 1:
                cur.append(x)
            else:
                runs.append(cur); cur = [x]
        runs.append(cur)
        for y, x in marks:
            out[y][x] = fill
        # origin side of each marker: left/right half relative to the region's horizontal extent
        groups = {}
        for y, x in marks:
            # choose target run: nearest by column (deterministic tie -> leftmost)
            run = min(runs, key=lambda rn: (min(abs(x - rn[0]), abs(x - rn[-1])) if not (rn[0] <= x <= rn[-1]) else 0, rn[0]))
            side = 0 if x <= (run[0] + run[-1]) / 2 else 1
            groups.setdefault(tuple(run), [0, 0])[side] += 1
        for run, (nl, nr) in groups.items():
            a, b = run[0], run[-1]
            wall_l = a - 1 < 0 or g[bot][a - 1] != new
            wall_r = b + 1 >= W or g[bot][b + 1] != new
            if wall_l and not wall_r:
                nl, nr = nl + nr, 0
            elif wall_r and not wall_l:
                nl, nr = 0, nl + nr
            for i in range(min(nl, len(run))):
                out[bot][a + i] = marker
            for i in range(min(nr, len(run))):
                out[bot][b - i] = marker
    return out


# ---------------------------------------------------------------- induction
def _colours(g):
    return {v for r in g for v in r}


def _induce(train, fwd):
    ins = [fwd(p["input"]) for p in train]
    outs = [fwd(p["output"]) for p in train]
    if any(len(i) != len(o) or len(i[0]) != len(o[0]) for i, o in zip(ins, outs)):
        return None
    segc = set.intersection(*[_colours(i) for i in ins]) - set.union(*[_colours(o) for o in outs])
    if len(segc) != 1:
        return None
    seg = segc.pop()
    newc, fillc = Counter(), Counter()
    for i, o in zip(ins, outs):
        segs = _segments(i, seg)
        if not segs:
            return None
        for r, xs in segs:
            m = len(xs) // 2
            newc[o[r][xs[m]]] += 1
            for k, x in enumerate(xs):
                if k != m:
                    fillc[o[r][x]] += 1
    if len(newc) != 1 or len(fillc) != 1:
        return None
    new, fill = next(iter(newc)), next(iter(fillc))
    if new == fill:
        return None
    moved = Counter()
    for i, o in zip(ins, outs):
        for y in range(len(i)):
            for x in range(len(i[0])):
                for v in (i[y][x], o[y][x]):
                    if i[y][x] != o[y][x] and v not in (seg, new, fill):
                        moved[v] += 1
    markers = sorted(moved, key=lambda c: (-moved[c], c))
    marker = markers[0] if markers else None
    return seg, new, fill, marker


def _make(fwd, inv, seg, new, fill, marker):
    def fn(grid):
        g = fwd(grid)
        out, segs = _reorient(g, seg, new, fill)
        if out is None:
            return [list(r) for r in grid]
        if marker is not None:
            out = _slide(out, marker, fill, new)
        return inv(out)
    return fn


def fam(train):
    if not train:
        return
    for k, (oname, fwd, inv) in enumerate(_ORIENTS):
        ind = _induce(train, fwd)
        if ind is None:
            continue
        seg, new, fill, marker = ind
        variants = [("slide", marker)] if marker is not None else []
        variants.append(("keep", None))
        for j, (mname, mk) in enumerate(variants):
            fn = _make(fwd, inv, seg, new, fill, mk)
            try:
                ok = all(fn(p["input"]) == [list(r) for r in p["output"]] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("reorient_segments[%s,markers=%s]" % (oname, mname), 3 + k + 2 * j, fn)


FAMILIES = [fam]
