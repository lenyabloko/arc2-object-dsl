"""Line family for card 7d419a02 -- reviewer (Len): damaged flat stick ends.

Reading (test-blind, induced only from the training pairs):
  Sticks are the parallel bars of one colour that lie between full-background separator lines (rows for horizontal
  sticks, columns for vertical ones).  Along a stick, a position is "damaged" when its cross-section holds a
  background cell (a hole).  An end of the stick is "flat" when its end cross-section is entirely stick colour.
  For each stick that has a damaged flat end (an intact flat end with a hole near it), recolour a stretch that starts
  at that end and covers the damage with equally many cells on both sides of it (the intact cells between the end
  and the damage, the damage run, and as many cells again beyond it), and recolour an equally long stretch at the
  opposite end of the stick.  The recolouring stops so that the recoloured stretch does not touch another coloured
  stretch: the two stretches of a stick keep at least one cell between them, and a stick whose stretch would touch a
  stretch of a foreign colour (neither background nor stick colour) is left alone.
  Holes stay background; only stick-colour cells are repainted, with the one new colour induced from the train pairs.

Variants (small finite domain, ordered by cost; the literal reading is first):
  ends   in {flat, any}       which ends may be the damaged end (flat cross-section required or not)
  extent in {sym, past1}      the stretch reaches past the damage by as many cells as precede it, or by one cell
  stop   in {clip, skip}      a stretch touching the opposite stretch is shortened, or the stick is left alone
  alien  in {skip, clip}      a stretch touching a foreign-colour stretch: the stick is left alone, or it is shortened
"""
from collections import Counter

CARD = "7d419a02"
LINE = ("recolor a damaged flat end of each stick on both sides of the damage and equally long stretch on the "
        "opposite end of the stick as long as recolored stretch does not touch another colored stretch")
READING = {
    "generator": "For each stick with a damaged flat end, recolour the stretch from that end across the damage, "
                 "reaching as far beyond the damage as the end lies before it, and recolour an equally long "
                 "stretch at the stick's opposite end (holes stay background).",
    "stop": "The stretch ends symmetric about the nearest damage run; it is shortened until the two stretches of "
            "the stick keep a gap of at least one cell, and a stick whose stretch would touch a foreign-colour "
            "stretch (e.g. a block of another colour inside the stick) is not recoloured.",
    "params": "ends ∈ {flat, any} · extent ∈ {sym, past1} · stop ∈ {clip, skip} · alien ∈ {skip, clip} · "
              "orientation ∈ {rows, cols} (per grid: the axis with more separator-bounded bands) · "
              "new colour ∈ {the single colour stick cells turn into in training}",
    "participants": "Sticks: maximal bands of consecutive non-separator lines between full-background lines, "
                    "extent = first..last non-background position along the band; stick colour = most frequent "
                    "non-background colour of the grid; damage = positions whose cross-section has a background "
                    "cell; foreign stretches = cells of any other colour inside a stick; background = most "
                    "frequent border colour.",
    "preconditions": "Same-shape pairs; the input splits into >= 2 parallel sticks by full-background separator "
                     "lines; every changed cell is a stick-colour cell turned into one common new colour; at least "
                     "one stick has a damaged end.",
}

VARIANTS = [  # (ends, extent, stop, alien)
    (e, x, s, a)
    for e in ("flat", "any") for x in ("sym", "past1") for s in ("clip", "skip") for a in ("skip", "clip")
]


def _bg(g):
    H, W = len(g), len(g[0])
    border = [g[0][c] for c in range(W)] + [g[H - 1][c] for c in range(W)] + \
             [g[r][0] for r in range(H)] + [g[r][W - 1] for r in range(H)]
    return Counter(border).most_common(1)[0][0]


def _T(g):
    return [list(r) for r in zip(*g)]


def _bands(g, bg):
    """Maximal runs of rows that are not entirely background."""
    out, cur = [], []
    for r, row in enumerate(g):
        if all(v == bg for v in row):
            if cur:
                out.append(cur)
                cur = []
        else:
            cur.append(r)
    if cur:
        out.append(cur)
    return out


def _orient(g, bg):
    """Return (transposed?, bands) choosing the axis with more separator-bounded bands (>= 2)."""
    br = _bands(g, bg)
    bc = _bands(_T(g), bg)
    if len(br) >= len(bc) and len(br) >= 2:
        return False, br
    if len(bc) >= 2:
        return True, bc
    return None, None


def _stick_colour(g, bg):
    cnt = Counter(v for row in g for v in row if v != bg)
    return cnt.most_common(1)[0][0] if cnt else None


def _sticks(g, bg, sc):
    """Horizontal-canonical sticks: list of dict(rows, lo, hi, dmg:set(pos), alien:set(pos))."""
    W = len(g[0])
    res = []
    for rows in _bands(g, bg):
        cols = [c for c in range(W) if any(g[r][c] != bg for r in rows)]
        if not cols:
            continue
        lo, hi = min(cols), max(cols)
        dmg = {c for c in range(lo, hi + 1) if any(g[r][c] == bg for r in rows)}
        alien = {c for c in range(lo, hi + 1) if any(g[r][c] not in (bg, sc) for r in rows)}
        res.append({"rows": rows, "lo": lo, "hi": hi, "dmg": dmg, "alien": alien})
    return res


def _end_len(st, side, ends, extent):
    """Length of the stretch anchored at the damaged end `side` (+1 = lo end, -1 = hi end), or None."""
    lo, hi, dmg = st["lo"], st["hi"], st["dmg"]
    n = hi - lo + 1
    seq = list(range(lo, hi + 1)) if side > 0 else list(range(hi, lo - 1, -1))
    if ends == "flat" and seq[0] in dmg:
        return None
    k = 0
    while k < n and seq[k] not in dmg:
        k += 1
    if k == n:
        return None                                   # no damage seen from this end
    w = 0
    while k + w < n and seq[k + w] in dmg:
        w += 1
    beyond = k if extent == "sym" else 1
    return k + w + beyond


def _plan(st, ends, extent, stop, alien):
    """Return the set of positions to recolour in this stick."""
    lo, hi = st["lo"], st["hi"]
    n = hi - lo + 1
    cands = []
    for side in (1, -1):
        L = _end_len(st, side, ends, extent)
        if L is not None:
            cands.append((L, side))
    if not cands:
        return set()
    L = min(cands)[0]                                  # the damaged end whose damage lies nearest to the end
    L = min(L, n)
    maxL = (n - 1) // 2                                # two stretches keeping a gap >= 1 between them
    if L > maxL:
        if stop == "skip":
            return set()
        L = maxL
    if L <= 0:
        return set()

    def stretches(m):
        return set(range(lo, lo + m)) | set(range(hi - m + 1, hi + 1))

    def touches_alien(m):
        s = stretches(m)
        return any((p in st["alien"]) or (p - 1 in st["alien"]) or (p + 1 in st["alien"]) for p in s)

    if st["alien"] and touches_alien(L):
        if alien == "skip":
            return set()
        while L > 0 and touches_alien(L):
            L -= 1
        if L <= 0:
            return set()
    return stretches(L)


def _apply(g, bg, sc, nc, var):
    tr, _ = _orient(g, bg)
    if tr is None:
        return [row[:] for row in g]
    h = _T(g) if tr else [row[:] for row in g]
    out = [row[:] for row in h]
    for st in _sticks(h, bg, sc):
        for c in _plan(st, *var):
            for r in st["rows"]:
                if h[r][c] == sc:
                    out[r][c] = nc
    return _T(out) if tr else out


def _induce(train):
    """Common background, stick colour, new colour; None when the preconditions fail."""
    bg = sc = nc = None
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        b = _bg(gi)
        s = _stick_colour(gi, b)
        if s is None:
            return None
        if bg is None:
            bg, sc = b, s
        elif (b, s) != (bg, sc):
            return None
        tr, bands = _orient(gi, b)
        if tr is None:
            return None
        for r in range(len(gi)):
            for c in range(len(gi[0])):
                if gi[r][c] != go[r][c]:
                    if gi[r][c] != sc:
                        return None
                    if nc is None:
                        nc = go[r][c]
                    elif go[r][c] != nc:
                        return None
    if nc is None or nc in (bg, sc):
        return None
    # at least one stick somewhere has damage
    if not any(st["dmg"] for p in train
               for st in _sticks(_T(p["input"]) if _orient(p["input"], bg)[0] else p["input"], bg, sc)):
        return None
    return bg, sc, nc


def _make(bg, sc, nc, var):
    def fn(grid):
        return _apply(grid, bg, sc, nc, var)
    return fn


def fam(train):
    ind = _induce(train)
    if ind is None:
        return
    bg, sc, nc = ind
    progs = []
    for var in VARIANTS:
        cost = 1 + (var[0] != "flat") + (var[1] != "sym") + (var[2] != "clip") + (var[3] != "skip")
        fn = _make(bg, sc, nc, var)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        progs.append((0 if ok else 1, cost, "damaged_end[%s|%s|%s|%s]->%d" % (var + (nc,)), fn))
    progs.sort(key=lambda t: (t[0], t[1], t[2]))
    for _, cost, name, fn in progs:
        yield name, cost, fn


FAMILIES = [fam]
