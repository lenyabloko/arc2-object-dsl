"""Reviewer line family for ARC card 7d419a02 (two diagonal cones along striped bands).

The grid is cut into parallel bands by empty (all-background) lines.  One
marker block (cells that are neither background nor the body colour) sits in
one band.  For a body cell in another band, let d = how many bands away it is
from the marker's band, and e = how many cells it lies beyond the marker's
extent measured along the band.  With s = the marker's size along the band,
the cell is recoloured when ceil(e / s) >= d, i.e. its distance along the
band in marker-sized steps is at least its band distance.  The kept cells form
a cone widening by one marker size per band, so the recoloured cells form two
diagonal cones running along the bands, one on each side of the marker.
"""

CARD = "7d419a02"
LINE = ("The grid is striped into bands by empty lines and holds one marker block; every body cell outside "
        "the marker's band whose distance along the band (in marker-sized steps) is at least its band "
        "distance from the marker is recoloured, giving two diagonal cones running along the bands.")

READING = {
    "generator": "Every body-coloured cell in a band other than the marker's is recoloured to the induced "
                 "colour when its distance beyond the marker's extent along the band, counted in marker-sized "
                 "steps (rounded up), is at least the number of bands between it and the marker's band.",
    "stop": "Nothing is drawn in the marker's own band or on non-body cells; recolouring runs to the grid "
            "border along each band (two cones, one on each side of the marker along the band axis).",
    "params": "orientation ∈ {rows, columns} (per grid: the axis whose empty lines yield more bands) · "
              "rounding ∈ {ceil, floor} · offset ∈ {0, 1} (recolour iff steps >= band_distance + offset) · "
              "new colour ∈ {0..9} (induced from the train diffs)",
    "participants": "Background = colour filling the most complete rows/columns; bands = maximal runs of "
                    "non-empty lines along the chosen axis; body = most frequent non-background colour; "
                    "marker = all remaining non-background, non-body cells (must lie in one band); marker size "
                    "s = its bounding-box extent along the band direction.",
    "preconditions": "Same grid size in and out; at least two bands on some axis; a non-empty marker inside a "
                     "single band; every changed training cell goes body colour -> one common new colour.",
}


def _bg(g):
    h, w = len(g), len(g[0])
    score = {}
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    for r in range(h):
        if len(set(g[r])) == 1:
            score[g[r][0]] = score.get(g[r][0], 0) + 1
    for c in range(w):
        col = {g[r][c] for r in range(h)}
        if len(col) == 1:
            v = next(iter(col))
            score[v] = score.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: (score.get(k, 0), cnt[k]))


def _bands(empty):
    """Maximal runs of non-empty line indices -> list of (start, end) inclusive."""
    out, start = [], None
    for i, e in enumerate(empty):
        if not e and start is None:
            start = i
        elif e and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(empty) - 1))
    return out


def _analyse(g):
    """-> dict with bg, body, axis, bands, marker band index, marker extent along band; or None."""
    h, w = len(g), len(g[0])
    bg = _bg(g)
    cnt = {}
    for row in g:
        for v in row:
            if v != bg:
                cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 2:
        return None
    body = max(sorted(cnt), key=lambda k: cnt[k])
    marker = [(r, c) for r in range(h) for c in range(w) if g[r][c] != bg and g[r][c] != body]
    if not marker:
        return None
    row_empty = [all(v == bg for v in g[r]) for r in range(h)]
    col_empty = [all(g[r][c] == bg for r in range(h)) for c in range(w)]
    cands = []
    for axis, empty in (("rows", row_empty), ("cols", col_empty)):
        bands = _bands(empty)
        if len(bands) < 2:
            continue
        # across-band coordinate and along-band coordinate of each marker cell
        acr = [r if axis == "rows" else c for r, c in marker]
        alo = [c if axis == "rows" else r for r, c in marker]
        idx = None
        for i, (a, b) in enumerate(bands):
            if all(a <= x <= b for x in acr):
                idx = i
                break
        if idx is None:
            continue
        cands.append((len(bands), axis, bands, idx, min(alo), max(alo)))
    if not cands:
        return None
    # more bands wins; tie -> rows (stable order above)
    best = max(cands, key=lambda x: x[0])
    _, axis, bands, idx, m0, m1 = best
    return {"bg": bg, "body": body, "axis": axis, "bands": bands, "mi": idx, "m0": m0, "m1": m1}


def _make(new_col, rounding, offset):
    def fn(grid):
        g = [list(r) for r in grid]
        info = _analyse(grid)
        if info is None:
            return g
        h, w = len(g), len(g[0])
        body, axis, bands, mi = info["body"], info["axis"], info["bands"], info["mi"]
        m0, m1 = info["m0"], info["m1"]
        s = m1 - m0 + 1
        along_len = w if axis == "rows" else h
        for bi, (a, b) in enumerate(bands):
            d = abs(bi - mi)
            if d == 0:
                continue
            for x in range(a, b + 1):
                for p in range(along_len):
                    r, c = (x, p) if axis == "rows" else (p, x)
                    if g[r][c] != body:
                        continue
                    if p < m0:
                        e = m0 - p
                    elif p > m1:
                        e = p - m1
                    else:
                        e = 0
                    steps = -(-e // s) if rounding == "ceil" else e // s
                    if steps >= d + offset:
                        g[r][c] = new_col
        return g
    return fn


def _new_colour(train):
    """Every changed cell must go body -> one common colour; returns that colour or None."""
    tgt = set()
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or any(len(a) != len(b) for a, b in zip(gi, go)):
            return None
        info = _analyse(gi)
        if info is None:
            return None
        for a, b in zip(gi, go):
            for x, y in zip(a, b):
                if x != y:
                    if x != info["body"]:
                        return None
                    tgt.add(y)
    if len(tgt) != 1:
        return None
    return next(iter(tgt))


def fam(train):
    new_col = _new_colour(train)
    if new_col is None:
        return
    cost = 0
    for rounding in ("ceil", "floor"):
        for offset in (0, 1):
            fn = _make(new_col, rounding, offset)
            ok = True
            for p in train:
                if fn(p["input"]) != [list(r) for r in p["output"]]:
                    ok = False
                    break
            if ok:
                yield ("band_cones[%s,off=%d,col=%d]" % (rounding, offset, new_col), 10 + cost, fn)
            cost += 1


FAMILIES = [fam]
