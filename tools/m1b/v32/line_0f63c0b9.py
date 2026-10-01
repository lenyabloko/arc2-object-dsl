"""Line family for card 0f63c0b9 -- reviewer (Len): "complete full length rail profile shapes across from middle to edge".

Reading: every seed (non-background cell) lies in the "middle" of its own rail profile.  Through each seed a rail
is drawn the full length of the grid (a whole row, or a whole column for the vertical orientation).  The grid is
cut into bands, one per seed: each line across the grid belongs to its nearest seed line (the cut lies at the
middle between consecutive seeds).  Each band's profile is completed out to the grid edge in its seed's colour:
the two side rails on the grid border running the band's length, and the outer bands are capped by a full rail
on the grid edge they touch.  The seed colour is the only colour a band uses; background stays inside.

Parameters (small finite domains, induced by fitting the training pairs; nothing is hard-coded):
  axis  ∈ {rows, cols}           rails run along rows (horizontal) or along columns (vertical)
  split ∈ {mid-lo, mid-hi, next, prev}
        mid-* : each line goes to the nearest seed line, a tie at the middle goes to the earlier (lo) / later (hi)
        next  : a seed owns the lines from itself up to the next seed;  prev : from the previous seed up to itself
  cap   ∈ {outer, none, all}    full rail on the grid edges of the outer bands / none / at both ends of every band
  sides ∈ {both, none}          side rails along the two grid borders parallel to the cut
"""
from collections import Counter

CARD = "0f63c0b9"
LINE = "complete full length rail profile shapes across from middle to edge"
READING = {
    "generator": "Through every seed a full-length rail (whole row or column) is drawn in the seed's colour, and the "
                 "band of the grid nearest to that seed is completed into a rail profile out to the grid edge: side "
                 "rails along the two grid borders for the band's length and, for the outermost bands, a full rail "
                 "on the grid edge they touch.",
    "stop": "Every rail runs the full length of the grid, border to border; a band stops at the middle between its "
            "seed and the neighbouring seed (tie at the exact middle per induced side) or at the grid edge, where "
            "the outer band is capped.",
    "params": "axis ∈ {rows, cols} · split ∈ {mid-lo, mid-hi, next, prev} · cap ∈ {outer, none, all} · "
              "sides ∈ {both, none}",
    "participants": "Seeds: the non-background cells of the input (background = most frequent colour), grouped by "
                    "the row (or column) they lie on; each seed line owns one band and gives it its colour. The grid "
                    "border supplies the side rails and the caps.",
    "preconditions": "Output has the input's shape; the input has at least one seed and no row (column) holds seeds "
                     "of two colours; seeds are kept; every changed cell takes the colour of a seed; one setting "
                     "reproduces every training pair.",
}

AXES = ("rows", "cols")
SPLITS = (("mid-lo", 0), ("mid-hi", 0), ("next", 1), ("prev", 1))
CAPS = (("outer", 1), ("none", 0), ("all", 2))
SIDES = (("both", 1), ("none", 0))


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _t(g):
    return [list(r) for r in zip(*g)]


def _seed_lines(g, bg, strict):
    """[(row index, colour)] for every row holding non-background cells; None on a two-colour row when strict."""
    out = []
    for i, row in enumerate(g):
        cnt = Counter(v for v in row if v != bg)
        if not cnt:
            continue
        if len(cnt) > 1 and strict:
            return None
        c = sorted(cnt.items(), key=lambda t: (-t[1], t[0]))[0][0]
        out.append((i, c))
    return out


def _owner(n, seeds, split):
    """owner[i] = index into seeds of the band that line i belongs to."""
    pos = [s[0] for s in seeds]
    own = []
    for i in range(n):
        if split in ("mid-lo", "mid-hi"):
            best = None
            for k, p in enumerate(pos):
                d = abs(i - p)
                if best is None or d < best[0] or (d == best[0] and split == "mid-hi"):
                    best = (d, k)
            own.append(best[1])
        elif split == "next":
            k = 0
            for j, p in enumerate(pos):
                if p <= i:
                    k = j
            own.append(k)
        else:  # prev
            k = len(pos) - 1
            for j in range(len(pos) - 1, -1, -1):
                if pos[j] >= i:
                    k = j
            own.append(k)
    return own


def _draw(g, split, cap, sides, strict=False):
    bg = _bg(g)
    seeds = _seed_lines(g, bg, strict)
    if not seeds:
        return None
    H, W = len(g), len(g[0])
    own = _owner(H, seeds, split)
    col = [seeds[k][1] for k in own]
    out = [[bg] * W for _ in range(H)]
    if sides == "both":
        for i in range(H):
            out[i][0] = col[i]
            out[i][W - 1] = col[i]
    caps = set()
    if cap == "outer":
        caps = {0, H - 1}
    elif cap == "all":
        for i in range(H):
            if i == 0 or own[i - 1] != own[i]:
                caps.add(i)
            if i == H - 1 or own[i + 1] != own[i]:
                caps.add(i)
    for i in sorted(caps):
        out[i] = [col[i]] * W
    for p, c in seeds:  # the rail through each seed, full length
        out[p] = [c] * W
    for i in range(H):  # seeds themselves are kept
        for j in range(W):
            if g[i][j] != bg:
                out[i][j] = g[i][j]
    return out


def _apply(g, axis, split, cap, sides, strict=False):
    if axis == "cols":
        r = _draw(_t(g), split, cap, sides, strict)
        return None if r is None else _t(r)
    return _draw([list(r) for r in g], split, cap, sides, strict)


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if not gi or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        bg = _bg(gi)
        seedc = {v for r in gi for v in r if v != bg}
        if not seedc:
            return
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != bg and a != b:
                    return  # seeds are kept
                if b != bg and b not in seedc:
                    return  # only seed colours are painted
    if all(pr["input"] == pr["output"] for pr in train):
        return
    found = []
    for ai, axis in enumerate(AXES):
        if any(_seed_lines(pr["input"] if axis == "rows" else _t(pr["input"]), _bg(pr["input"]), True) is None
               for pr in train):
            continue
        for split, sc in SPLITS:
            for cap, cc in CAPS:
                for sd, dc in SIDES:
                    if all(_apply(pr["input"], axis, split, cap, sd, True) == pr["output"] for pr in train):
                        cost = 10 + sc + cc + dc
                        name = "rail_profile[%s,%s,cap=%s,sides=%s]" % (axis, split, cap, sd)
                        found.append((cost, len(found), name, (axis, split, cap, sd)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


def _make(axis, split, cap, sides):
    def fn(grid):
        r = _apply(grid, axis, split, cap, sides, False)
        return [list(x) for x in grid] if r is None else r
    return fn


FAMILIES = [fam]
