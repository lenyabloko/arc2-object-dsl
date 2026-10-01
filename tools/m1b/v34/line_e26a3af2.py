"""Line family for card e26a3af2 -- reviewer (Len): "denoise color panels".

Reading: the input is tiled by axis-aligned rectangular colour panels (row bands, column bands, or a 2-D grid of
blocks) sprinkled with off-colour noise cells.  Each panel is repainted entirely in its own majority colour.

Panel finding (per grid, no constants):
  rows : row bands   = maximal runs of consecutive rows with the same majority colour
  cols : column bands = the same on columns
  grid : 2-D blocks  = alternate the two: row bands by the tuple of majority colours over the current column
         segments, column bands by the tuple over the current row bands, until a fixed point
         (started from the row side and from the column side; the cheaper result is kept)
  auto : per grid, whichever of rows | cols | grid gives the shortest description
         (#repainted cells + #panels); panels need not be the same orientation in every grid.
Every segmentation is then cleaned by MDL merging: two adjacent bands are merged while that does not lengthen
the description (#repainted cells + #panels), so a noise-dominated line does not survive as a fake panel.
Majority ties break to the smallest colour value (deterministic).
"""
from collections import Counter

CARD = "e26a3af2"
LINE = "denoise color panels"
READING = {
    "generator": "Each rectangular colour panel of the input (a row band, a column band, or a block of a 2-D grid of "
                 "panels) is repainted entirely in its own majority colour, which erases the scattered off-colour "
                 "noise cells.",
    "stop": "A panel ends where the majority colour of the rows (or columns, or row/column segments for a 2-D grid) "
            "changes; adjacent bands are merged while merging does not lengthen the description "
            "(#repainted cells + #panels); the grid edge closes the outer panels.",
    "params": "layout ∈ {auto, rows, cols, grid} (auto = choose per grid by shortest description)",
    "participants": "Panels: maximal runs of consecutive rows/columns sharing a majority colour (for a 2-D grid, "
                    "sharing the tuple of majority colours over the other axis' segments). Noise: every cell whose "
                    "colour differs from its panel's majority colour.",
    "preconditions": "Output has the input's shape; the input is covered by axis-aligned rectangular panels, each "
                     "with a strict-majority-like dominant colour (noise is a minority inside every panel).",
}

LAYOUTS = ("auto", "rows", "cols", "grid")


def _mode(vals):
    c = Counter(vals)
    best = max(c.values())
    return min(k for k, v in c.items() if v == best)


def _runs(labels):
    out, s = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[s]:
            out.append((s, i))
            s = i
    return out


def _row_bands(g, csegs):
    return _runs([tuple(_mode(g[r][a:b]) for a, b in csegs) for r in range(len(g))])


def _col_bands(g, rsegs):
    return _runs([tuple(_mode([g[r][c] for r in range(a, b)]) for a, b in rsegs) for c in range(len(g[0]))])


class _Counts:
    """2-D prefix counts per colour: O(#colours) majority / noise count of any rectangle."""

    def __init__(self, g):
        h, w = len(g), len(g[0])
        self.cols = sorted({v for r in g for v in r})
        self.P = {}
        for k in self.cols:
            P = [[0] * (w + 1) for _ in range(h + 1)]
            for r in range(h):
                run, row, prev = 0, P[r + 1], P[r]
                for c in range(w):
                    run += g[r][c] == k
                    row[c + 1] = prev[c + 1] + run
            self.P[k] = P
        self.memo = {}

    def block(self, r0, r1, c0, c1):
        """(majority colour, number of non-majority cells) of rows r0:r1, columns c0:c1."""
        key = (r0, r1, c0, c1)
        if key not in self.memo:
            best, bk = -1, None
            for k in self.cols:
                P = self.P[k]
                n = P[r1][c1] - P[r0][c1] - P[r1][c0] + P[r0][c0]
                if n > best:
                    best, bk = n, k
            self.memo[key] = (bk, (r1 - r0) * (c1 - c0) - best)
        return self.memo[key]


def _cost(cnt, R, C):
    """Description length: repainted (noise) cells + number of panels."""
    return sum(cnt.block(a, b, c, d)[1] for a, b in R for c, d in C) + len(R) * len(C)


def _merge(cnt, R, C):
    """Greedy MDL merging of adjacent row bands / column bands while the description does not get longer."""
    R, C = list(R), list(C)
    while True:
        base = _cost(cnt, R, C)
        best = None
        for axis, S in ((0, R), (1, C)):
            for i in range(len(S) - 1):
                T = S[:i] + [(S[i][0], S[i + 1][1])] + S[i + 2:]
                c = _cost(cnt, T, C) if axis == 0 else _cost(cnt, R, T)
                if c <= base and (best is None or c < best[0]):
                    best = (c, axis, T)
        if best is None:
            return R, C
        if best[1] == 0:
            R = best[2]
        else:
            C = best[2]


def _grid_fix(g, start_rows):
    h, w = len(g), len(g[0])
    if start_rows:
        C = [(0, w)]
        R = _row_bands(g, C)
    else:
        R = [(0, h)]
        C = _col_bands(g, R)
    seen = set()
    for _ in range(h + w + 2):
        key = (tuple(R), tuple(C))
        if key in seen:
            break
        seen.add(key)
        C = _col_bands(g, R)
        R = _row_bands(g, C)
    return R, C


def _segment(g, layout, cnt):
    h, w = len(g), len(g[0])
    if layout == "rows":
        cands = [(_row_bands(g, [(0, w)]), [(0, w)])]
    elif layout == "cols":
        cands = [([(0, h)], _col_bands(g, [(0, h)]))]
    elif layout == "grid":
        cands = [_grid_fix(g, True), _grid_fix(g, False)]
    else:
        cands = [_segment(g, L, cnt) for L in ("rows", "cols", "grid")]
    best = None
    for R, C in cands:
        R, C = _merge(cnt, R, C)
        c = _cost(cnt, R, C)
        if best is None or c < best[0]:
            best = (c, R, C)
    return best[1], best[2]


def denoise_panels(g, layout):
    cnt = _Counts(g)
    R, C = _segment(g, layout, cnt)
    out = [list(r) for r in g]
    for a, b in R:
        for c, d in C:
            col = cnt.block(a, b, c, d)[0]
            for r in range(a, b):
                for x in range(c, d):
                    out[r][x] = col
    return out


def _shape(g):
    return (len(g), len(g[0]) if g else 0)


def fam(train):
    if not train or any(_shape(p["input"]) != _shape(p["output"]) or not p["input"] or not p["input"][0]
                        for p in train):
        return
    if all(p["input"] == p["output"] for p in train):
        return
    for cost, layout in ((1, "auto"), (2, "rows"), (2, "cols"), (3, "grid")):
        fn = (lambda L: (lambda grid: denoise_panels(grid, L)))(layout)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("denoise_panels[layout=%s]" % layout, cost, fn)


FAMILIES = [fam]
