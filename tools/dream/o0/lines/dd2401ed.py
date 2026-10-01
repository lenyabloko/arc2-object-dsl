"""Line family for card dd2401ed -- reviewer (Len): "move solid line/wall to next available slot  towards middle of  area".

Reading: the input holds one solid wall -- a full row or full column (or a band of consecutive identical full
lines) of a single non-background colour.  The wall sits nearer one edge; the strip between that edge and the wall,
together with the wall itself, is one "slot".  The wall jumps towards the middle of the grid by whole slots: it is
redrawn at the first slot boundary (offset k * slot width, k = 1, 2, ...) whose lines are empty (background only),
and its old place is cleared.  Objects that the jump brings onto the wall's near side may take the near side's
colour; whether they do is an induced condition from a small finite domain:
  never              nothing is recoloured
  always             every captured cell takes the near-side colour
  past_middle        recolour only when the wall lands strictly past the grid's middle line
  captured_majority  recolour only when more far-side cells are captured than are left on the far side
No coordinates, sizes, colours or counts are constants: the background is the most common colour, the wall is
found per grid, the slot width is the wall's own distance to the near edge plus its thickness, and the near-side
colour is the most common non-background colour on the near side of the input (falling back to the far->near
colour map read off the training diffs when the near side is empty).
"""
from collections import Counter

CARD = "dd2401ed"
LINE = "move solid line/wall to next available slot  towards middle of  area"
READING = {
    "generator": "The solid wall (a full row or column of one colour) is erased and redrawn one slot further towards "
                 "the middle of the grid, where a slot is the strip between the near edge and the wall plus the "
                 "wall itself (so its distance to the near edge doubles plus one); objects it passes over now lie "
                 "on the near side and, when the induced condition holds, take the near-side objects' colour.",
    "stop": "At the first slot boundary (offset k x slot width from the old wall, k = 1, 2, ...) towards the middle "
            "whose lines are all background; past the grid edge nothing is moved.",
    "params": "recolour ∈ {never, always, past_middle, captured_majority} · axis ∈ {rows, cols} found per grid · "
              "direction = towards the grid middle (from the nearer edge)",
    "participants": "Background: most common colour. Wall: the unique maximal band of consecutive full rows or full "
                    "columns of one non-background colour. Near side: cells between the wall and its nearer edge; "
                    "their most common colour is the target colour. Captured cells: non-background, non-target cells "
                    "between the old wall and the new slot boundary.",
    "preconditions": "Output has the input's shape; every training input has exactly one solid wall band, not "
                     "centred (one edge strictly nearer), and an empty slot boundary exists towards the middle.",
}

RECOLOUR = ("never", "always", "past_middle", "captured_majority")
COST = {"never": 1, "always": 1, "past_middle": 2, "captured_majority": 3}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _walls_rows(g, bg):
    """Maximal bands of consecutive full rows, each a single non-background colour (same colour across the band)."""
    full = [(r[0] if r and r[0] != bg and all(v == r[0] for v in r) else None) for r in g]
    bands, i = [], 0
    while i < len(full):
        if full[i] is None:
            i += 1
            continue
        j = i
        while j + 1 < len(full) and full[j + 1] == full[i]:
            j += 1
        bands.append((i, j - i + 1, full[i]))
        i = j + 1
    return bands


def _find_wall(g, bg):
    """(transposed?, start, thickness, colour) of the unique wall band, or None."""
    rows = _walls_rows(g, bg)
    cols = _walls_rows(_transpose(g), bg)
    cands = [(False,) + b for b in rows] + [(True,) + b for b in cols]
    if len(cands) != 1:
        return None
    return cands[0]


def _move_rows(g, bg, s, t, wc, mode, cmap):
    """Wall occupies rows s..s+t-1 of g (rows axis).  Returns the moved grid or None."""
    L = len(g)
    d_lo, d_hi = s, L - (s + t)
    if d_lo == d_hi:
        return None
    flip = d_lo > d_hi                       # normalise so that the near edge is row 0
    if flip:
        g = g[::-1]
        s = L - (s + t)
    d = s
    slot = d + t
    k, ns = 1, None
    while s + k * slot + t <= L:
        cand = s + k * slot
        if all(v == bg for r in g[cand:cand + t] for v in r):
            ns = cand
            break
        k += 1
    if ns is None:
        return None
    out = [list(r) for r in g]
    near = Counter(v for r in g[:s] for v in r if v != bg and v != wc)
    target = near.most_common(1)[0][0] if near else None
    for r in range(s, s + t):
        out[r] = [bg] * len(out[r])
    for r in range(ns, ns + t):
        out[r] = [wc] * len(out[r])

    def tgt(v):
        if target is not None:
            return target if v != target else None
        return cmap.get(v)

    captured = [(r, c) for r in range(s + t, ns) for c, v in enumerate(g[r])
                if v != bg and v != wc and tgt(v) is not None]
    if mode == "never":
        do = False
    elif mode == "always":
        do = True
    elif mode == "past_middle":
        do = 2 * ns + (t - 1) > (L - 1)        # wall centre strictly past the axis centre (doubled units)
    else:                                       # captured_majority
        far_cols = {g[r][c] for r, c in captured}
        left = sum(1 for r in range(ns + t, L) for v in g[r] if v in far_cols)
        do = len(captured) > left
    if do:
        for r, c in captured:
            out[r][c] = tgt(g[r][c])
    if flip:
        out = out[::-1]
    return out


def wall_jump(grid, mode, cmap=None):
    g = [list(r) for r in grid]
    if not g or not g[0]:
        return g
    bg = _bg(g)
    w = _find_wall(g, bg)
    if w is None:
        return g
    tr, s, t, wc = w
    h = _transpose(g) if tr else g
    out = _move_rows(h, bg, s, t, wc, mode, cmap or {})
    if out is None:
        return g
    return _transpose(out) if tr else out


def _diff_map(train):
    """Colour map old->new over changed cells where both colours are non-background and neither is the wall."""
    m = {}
    for p in train:
        a, b = p["input"], p["output"]
        bg = _bg(a)
        w = _find_wall(a, bg)
        wc = w[3] if w else None
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y and x != bg and y != bg and x != wc and y != wc:
                    if m.get(x, y) != y:
                        return None
                    m[x] = y
    return m


def _shape(g):
    return (len(g), len(g[0]) if g else 0)


def fam(train):
    if not train or any(not p["input"] or not p["input"][0] or _shape(p["input"]) != _shape(p["output"])
                        for p in train):
        return
    for p in train:
        if _find_wall(p["input"], _bg(p["input"])) is None:
            return
    cmap = _diff_map(train) or {}
    for mode in sorted(RECOLOUR, key=lambda m: (COST[m], RECOLOUR.index(m))):
        fn = (lambda M: (lambda grid: wall_jump(grid, M, cmap)))(mode)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("wall_jump_to_next_slot[recolour=%s]" % mode, COST[mode], fn)


FAMILIES = [fam]
