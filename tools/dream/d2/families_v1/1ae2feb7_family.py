"""Family for ARC task 1ae2feb7 -- concept: WAVELENGTH (physics).

A straight wall (the longest single-colour line in the grid) separates a "source" side from an empty side.
Each coloured band on the source side of a row is an emitter whose band width is its wavelength: beyond the
wall it transmits a pulse train of its colour with period = band width. Where pulse trains of several bands
coincide, one band dominates (nearest-to-wall or farthest -- induced from training).
Orientation (vertical/horizontal wall, sources on either side) is detected per input, so it works on any
rotation/reflection and grid size. Parameters (finite domains, induced from train):
    priority in {"near", "far"}   which band wins where pulses coincide
    phase    in {"start", "end"}  pulse at distance k from wall when k % L == 0 ("start") or k % L == L-1 ("end")
"""
from collections import Counter


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _fliplr(g):
    return [list(reversed(r)) for r in g]


def _longest_run(seq, bg):
    best, col, cur, prev = 0, None, 0, None
    for v in seq:
        cur = cur + 1 if (v == prev and v != bg) else (1 if v != bg else 0)
        prev = v
        if cur > best:
            best, col = cur, v
    return best, col


def _find_wall(g, bg):
    """Return (transposed?, index) of the line holding the longest single-colour straight run."""
    best = None
    for tr in (False, True):
        h = _transpose(g) if tr else g
        W = len(h[0])
        for c in range(W):
            n, _ = _longest_run([h[r][c] for r in range(len(h))], bg)
            if best is None or n > best[0]:
                best = (n, tr, c)
    return best[1], best[2]


def _emit_rows(g, bg, wall, priority, phase):
    """g normalised: vertical wall at column `wall`, sources to its left, empty side to its right."""
    out = [list(r) for r in g]
    W = len(g[0])
    for r, row in enumerate(g):
        # maximal single-colour bands on the source side, ordered nearest-to-wall first
        bands, c = [], wall - 1
        while c >= 0:
            v = row[c]
            if v == bg:
                c -= 1
                continue
            s = c
            while s - 1 >= 0 and row[s - 1] == v:
                s -= 1
            bands.append((v, c - s + 1))
            c = s - 1
        if not bands:
            continue
        order = bands if priority == "near" else bands[::-1]
        for k in range(W - wall - 1):
            x = wall + 1 + k
            if g[r][x] != bg:
                continue
            for v, L in order:
                if (k % L) == (0 if phase == "start" else L - 1):
                    out[r][x] = v
                    break
    return out


def _make(priority, phase):
    def fn(grid):
        bg = _bg(grid)
        tr, wall = _find_wall(grid, bg)
        g = _transpose(grid) if tr else [list(r) for r in grid]
        W = len(g[0])
        left = sum(1 for row in g for c in range(wall) if row[c] != bg)
        right = sum(1 for row in g for c in range(wall + 1, W) if row[c] != bg)
        flip = right > left
        if flip:
            g, wall = _fliplr(g), W - 1 - wall
        out = _emit_rows(g, bg, wall, priority, phase)
        if flip:
            out = _fliplr(out)
        return _transpose(out) if tr else out
    return fn


def fam_wavelength(train):
    for priority in ("near", "far"):
        for phase in ("start", "end"):
            fn = _make(priority, phase)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("physics:wavelength[priority=%s,phase=%s]" % (priority, phase), 3, fn)


FAMILIES = (fam_wavelength,)
