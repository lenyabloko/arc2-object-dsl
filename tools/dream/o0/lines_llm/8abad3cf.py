"""Line expansion for 8abad3cf: colour counts redrawn as solid squares, smallest to largest (test-blind; train pairs only)."""
from collections import Counter
from math import isqrt

CARD = "8abad3cf"
LINE = "Count the cells of each non-background colour and redraw each colour as a solid square of that area, the squares lined up from smallest to largest, aligned along one edge and separated by background columns."
READING = {
    "generator": "For every non-background colour, count its cells (anywhere in the grid, connected or not) and draw a solid square of that colour "
                 "whose area equals the count; place the squares side by side on a fresh background canvas, sorted by size, flush against one "
                 "shared edge, with background strips between neighbours.",
    "stop": "One square per colour; the canvas is exactly as tall as the largest square and exactly as wide as the squares plus the gaps (no margin).",
    "params": "orient ∈ {h: row of squares split by background columns, v: column of squares split by background rows} · "
              "align ∈ {far: bottom/right edge, near: top/left edge} · order ∈ {asc, desc} along the reading direction · "
              "gap ∈ {1, 0, 2} · tie ∈ {colour value, first appearance} · bg ∈ {most frequent colour, most frequent border colour}",
    "participants": "background = the chosen bg colour (also the output canvas colour); colours = every other colour present in the input, "
                    "each counted by total cell number.",
    "preconditions": "At least one non-background colour, and every non-background colour's cell count is a perfect square.",
}


def _bg_mode(g):
    c = Counter(v for row in g for v in row)
    return max(sorted(c), key=lambda k: c[k])


def _bg_border(g):
    H, W = len(g), len(g[0])
    c = Counter()
    for r in range(H):
        for cc in range(W):
            if r in (0, H - 1) or cc in (0, W - 1):
                c[g[r][cc]] += 1
    return max(sorted(c), key=lambda k: c[k])


BG = [("mode", _bg_mode, 0), ("border", _bg_border, 1)]


def _squares(g, bgf, tie):
    """-> (bg, [(side, colour), ...] sorted ascending) or None if preconditions fail."""
    if not g or not g[0]:
        return None
    bg = bgf(g)
    cnt = Counter()
    first = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v == bg:
                continue
            cnt[v] += 1
            first.setdefault(v, (r, c))
    if not cnt:
        return None
    sq = []
    for col, n in cnt.items():
        s = isqrt(n)
        if s * s != n:
            return None
        sq.append((s, col))
    if tie == "colour":
        sq.sort(key=lambda t: (t[0], t[1]))
    else:
        sq.sort(key=lambda t: (t[0], first[t[1]]))
    return bg, sq


def _make(bgf, orient, align, order, gap, tie):
    def fn(g):
        res = _squares(g, bgf, tie)
        if res is None:
            raise ValueError("preconditions fail")
        bg, sq = res
        if order == "desc":
            sq = sq[::-1]
        S = max(s for s, _ in sq)
        L = sum(s for s, _ in sq) + gap * (len(sq) - 1)
        # build in h orientation: S rows x L cols
        out = [[bg] * L for _ in range(S)]
        x = 0
        for s, col in sq:
            r0 = S - s if align == "far" else 0
            for r in range(r0, r0 + s):
                for c in range(x, x + s):
                    out[r][c] = col
            x += s + gap
        if orient == "v":
            out = [list(r) for r in zip(*out)]
        return out
    return fn


def fam(train):
    if not train:
        return
    variants = []
    for bname, bgf, bc in BG:
        for orient, oc in (("h", 0), ("v", 1)):
            for align, ac in (("far", 0), ("near", 1)):
                for order, rc in (("asc", 0), ("desc", 1)):
                    for gap, gc in ((1, 0), (0, 1), (2, 2)):
                        for tie, tc in (("colour", 0), ("first", 1)):
                            name = f"count_squares[orient={orient},align={align},order={order},gap={gap},tie={tie},bg={bname}]"
                            variants.append((name, 10 + bc + oc + ac + rc + gc + tc,
                                             _make(bgf, orient, align, order, gap, tie)))
    variants.sort(key=lambda t: t[1])
    for name, cost, fn in variants:
        ok = True
        for p in train:
            try:
                pred = fn(p["input"])
            except Exception:
                ok = False
                break
            if pred != [list(r) for r in p["output"]]:
                ok = False
                break
        if ok:
            yield name, cost, fn


FAMILIES = [fam]
