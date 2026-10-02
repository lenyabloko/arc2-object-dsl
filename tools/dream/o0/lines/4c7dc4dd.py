"""Line family for card 4c7dc4dd (test-blind; induced only from train pairs).

Reading: the input holds several "common frames" (big single-colour rectangular rings), each enclosing a pair
of equal-size "individually framed" grids.  In a demonstration frame both grids are filled and one is a
transformed version of the other, the transformation painting with the common frame's colour.  In the query
frame one grid is empty (a single colour).  The mechanism is identified per input from a small finite list by
reproducing the demonstration (painting colour = demo frame colour); it is then applied to the query's filled
grid with the query frame's colour, and the result (individual frame stripped) is the output.
"""

CARD = "4c7dc4dd"
LINE = ("inside each of two pairs of framed grid, one is a transformed version of another, and the common frame "
        "provides the color used in that transformation. You need to extract the empty grid from one of the pairs "
        "after applying the exact mechanism used for transforming in the first pair using the color of the common "
        "frame and ignoring the individual frame.")
READING = {
    "generator": "Find the common frames that each hold two equal-size framed grids; in the frame whose two grids "
                 "are both filled, find the mechanism that turns one grid into the other when painting with that "
                 "common frame's colour, and output the empty grid of the other pair filled by applying the same "
                 "mechanism to its partner grid, painting with that pair's common frame colour (individual frames "
                 "stripped).",
    "stop": "One application of the identified mechanism to the query's filled grid; the output is exactly the "
            "interior of the empty grid (same size as its partner's interior).",
    "params": "mechanism ∈ {pointwise role map (empty/frame-colour/other → empty/frame-colour/same), "
              "D4 symmetry + role map, connect aligned cells (orthogonal | orthogonal+diagonal), rays to the edge "
              "(N|S|E|W|orthogonal|diagonal|all 8), halo (4|8), fill enclosed holes, fill bounding box, "
              "fill full rows/cols/both of occupied cells} · direction ∈ {first→second, second→first} per "
              "demonstration pair · paint colour = enclosing common frame colour · empty colour = colour of the "
              "uniform (empty) grid",
    "participants": "Rectangles whose 1-cell border is a single colour (found by run lengths); a common frame is "
                    "such a rectangle enclosing two disjoint inner framed rectangles of identical size and border "
                    "colour (the largest such pair); the inner grids are their interiors; the query pair is the "
                    "one with a uniform (empty) interior, every other pair is a demonstration.",
    "preconditions": "At least two disjoint common frames are found, exactly one of them holds an empty grid next "
                     "to a filled one, every demonstration pair has two filled grids of equal size, and one "
                     "mechanism in the list reproduces all demonstrations (otherwise the closest one is used).",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
RAYDIRS = {"N": ((-1, 0),), "S": ((1, 0),), "W": ((0, -1),), "E": ((0, 1),),
           "orth": D4, "diag": DG, "all8": D4 + DG}


# ----------------------------------------------------------------------------------------------- parsing

def _runs(g):
    H, W = len(g), len(g[0])
    right = [[1] * W for _ in range(H)]
    down = [[1] * W for _ in range(H)]
    for r in range(H):
        for c in range(W - 2, -1, -1):
            if g[r][c] == g[r][c + 1]:
                right[r][c] = right[r][c + 1] + 1
    for r in range(H - 2, -1, -1):
        for c in range(W):
            if g[r][c] == g[r + 1][c]:
                down[r][c] = down[r + 1][c] + 1
    return right, down


def _rects(g, cap=200000):
    """All rectangles (r0, c0, r1, c1, colour) with h, w >= 3 whose 1-cell border is one colour and that are
    distinguished from their surroundings (the ring just outside is not entirely that colour)."""
    H, W = len(g), len(g[0])
    right, down = _runs(g)

    def hrun(r, a, b, k):  # row r, cols a..b all colour k (clipped; off-grid = vacuous)
        if r < 0 or r >= H:
            return True
        a, b = max(a, 0), min(b, W - 1)
        return a > b or (g[r][a] == k and right[r][a] >= b - a + 1)

    def vrun(c, a, b, k):
        if c < 0 or c >= W:
            return True
        a, b = max(a, 0), min(b, H - 1)
        return a > b or (g[a][c] == k and down[a][c] >= b - a + 1)

    out, n = [], 0
    for r0 in range(H):
        for c0 in range(W):
            k = g[r0][c0]
            mw, mh = right[r0][c0], down[r0][c0]
            if mw < 3 or mh < 3:
                continue
            for w in range(3, mw + 1):
                c1 = c0 + w - 1
                dh = down[r0][c1]
                if dh < 3:
                    continue
                for h in range(3, min(mh, dh) + 1):
                    n += 1
                    if n > cap:
                        return None
                    r1 = r0 + h - 1
                    if right[r1][c0] < w:
                        continue
                    if (hrun(r0 - 1, c0 - 1, c1 + 1, k) and hrun(r1 + 1, c0 - 1, c1 + 1, k)
                            and vrun(c0 - 1, r0 - 1, r1 + 1, k) and vrun(c1 + 1, r0 - 1, r1 + 1, k)):
                        continue  # not distinguished from the outside: part of a uniform region
                    out.append((r0, c0, r1, c1, k))
    return out


def _inside(a, b):  # rect a strictly inside the interior of rect b
    return b[0] < a[0] and a[2] < b[2] and b[1] < a[1] and a[3] < b[3]


def _disjoint(a, b):
    return a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]


def _interior(g, r):
    return [row[r[1] + 1:r[3]] for row in g[r[0] + 1:r[2]]]


def _uniform(m):
    return bool(m) and bool(m[0]) and len({v for row in m for v in row}) == 1


def _parse(g):
    """-> candidate structures, each a list of (common frame colour, interior A, interior B) for disjoint
    common frames (outermost level first), or None."""
    if not g or not g[0]:
        return None
    rects = _rects(g)
    if rects is None or len(rects) > 4000:
        return None
    best = {}
    for B in rects:
        if B[2] - B[0] < 4 or B[3] - B[1] < 4:
            continue
        groups = {}
        for a in rects:
            if a[4] != B[4] and _inside(a, B):
                groups.setdefault((a[2] - a[0], a[3] - a[1], a[4]), []).append(a)
        pair, parea = None, 0
        for (dh, dw, _), lst in sorted(groups.items()):
            area = (dh + 1) * (dw + 1)
            if area <= parea or len(lst) < 2:
                continue
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    if _disjoint(lst[i], lst[j]):
                        pair, parea = (lst[i], lst[j]), area
                        break
                if pair is not None and parea == area:
                    break
        if pair is not None:
            best[B] = pair
    # level choice: outermost frames first; then, in case those enclose common frames themselves (a spurious
    # enclosure), the frames whose inner pair is not made of common frames
    levels = [list(best), [B for B, p in best.items() if p[0] not in best and p[1] not in best]]
    outs = []
    for cands in levels:
        cands.sort(key=lambda B: (-(B[2] - B[0] + 1) * (B[3] - B[1] + 1), B))
        chosen = []
        for B in cands:
            if all(_disjoint(B, C) for C in chosen):
                chosen.append(B)
        if len(chosen) < 2:
            continue
        chosen.sort(key=lambda B: (B[0], B[1]))
        out = [(B[4], _interior(g, best[B][0]), _interior(g, best[B][1])) for B in chosen]
        if out not in outs:
            outs.append(out)
    return outs


def _roles(g):
    """-> (demos [(c, A, B)], query (c, src), empty colour z) or None."""
    structs = _parse(g)
    for pairs in structs or ():
        r = _assign(pairs)
        if r is not None:
            return r
    return None


def _assign(pairs):
    query, demos = [], []
    for c, a, b in pairs:
        ua, ub = _uniform(a), _uniform(b)
        if ua and ub:
            return None
        if ua or ub:
            query.append((c, b if ua else a, a if ua else b))
        else:
            if len(a) != len(b) or len(a[0]) != len(b[0]):
                return None
            demos.append((c, a, b))
    if len(query) != 1 or not demos:
        return None
    c, src, empty = query[0]
    if len(src) != len(empty) or len(src[0]) != len(empty[0]):
        return None
    return demos, (c, src), empty[0][0]


# ----------------------------------------------------------------------------------------------- mechanisms

def _copy(m):
    return [row[:] for row in m]


def _sym(m, k):
    if k == 0:
        return _copy(m)
    if k == 1:
        return [row[::-1] for row in m]
    if k == 2:
        return [row[:] for row in m[::-1]]
    if k == 3:
        return [list(r) for r in zip(*m)]
    if k == 4:
        return [list(r) for r in zip(*m[::-1])]          # rot90 cw
    if k == 5:
        return [row[::-1] for row in m[::-1]]           # rot180
    if k == 6:
        return [list(r) for r in zip(*m)][::-1]         # rot90 ccw
    return [list(r)[::-1] for r in zip(*m)][::-1]       # anti-transpose


def _role(v, c, z):
    return "z" if v == z else ("c" if v == c else "o")


def _rolemap_fit(demos):
    allowed = {}
    for s, t, c, z in demos:
        if len(s) != len(t) or len(s[0]) != len(t[0]):
            return None
        for rs, rt in zip(s, t):
            for sv, tv in zip(rs, rt):
                labs = set()
                if tv == sv:
                    labs.add("same")
                if tv == c:
                    labs.add("c")
                if tv == z:
                    labs.add("z")
                r = _role(sv, c, z)
                allowed[r] = allowed.get(r, labs) & labs
                if not allowed[r]:
                    return None
    mp = {r: next(l for l in ("same", "c", "z") if l in labs) for r, labs in allowed.items()}
    if "o" not in mp and "c" in mp:
        mp["o"] = mp["c"]
    if "c" not in mp and "o" in mp:
        mp["c"] = mp["o"]
    return mp


def _rolemap_vote(demos):
    """Majority-vote role map (fallback only)."""
    cnt = {}
    for s, t, c, z in demos:
        if len(s) != len(t) or len(s[0]) != len(t[0]):
            continue
        for rs, rt in zip(s, t):
            for sv, tv in zip(rs, rt):
                r = _role(sv, c, z)
                for l in ("same", "c", "z"):
                    if (l == "same" and tv == sv) or (l == "c" and tv == c) or (l == "z" and tv == z):
                        cnt[(r, l)] = cnt.get((r, l), 0) + 1
    mp = {}
    for r in ("z", "c", "o"):
        sc = [(cnt.get((r, l), 0), -i, l) for i, l in enumerate(("same", "c", "z"))]
        best = max(sc)
        if best[0] > 0:
            mp[r] = best[2]
    if "o" not in mp and "c" in mp:
        mp["o"] = mp["c"]
    if "c" not in mp and "o" in mp:
        mp["c"] = mp["o"]
    return mp


def _rolemap_apply(s, c, z, mp):
    out = []
    for row in s:
        nr = []
        for v in row:
            l = mp.get(_role(v, c, z), "same")
            nr.append(v if l == "same" else (c if l == "c" else z))
        out.append(nr)
    return out


def _connect(s, c, z, dirs):
    H, W = len(s), len(s[0])
    out = _copy(s)
    for y in range(H):
        for x in range(W):
            if s[y][x] == z:
                continue
            for dy, dx in dirs:
                path, p, q = [], y + dy, x + dx
                while 0 <= p < H and 0 <= q < W and s[p][q] == z:
                    path.append((p, q))
                    p, q = p + dy, q + dx
                if 0 <= p < H and 0 <= q < W:          # reached another occupied cell
                    for a, b in path:
                        out[a][b] = c
    return out


def _rays(s, c, z, dirs):
    H, W = len(s), len(s[0])
    out = _copy(s)
    for y in range(H):
        for x in range(W):
            if s[y][x] == z:
                continue
            for dy, dx in dirs:
                p, q = y + dy, x + dx
                while 0 <= p < H and 0 <= q < W and s[p][q] == z:
                    out[p][q] = c
                    p, q = p + dy, q + dx
    return out


def _halo(s, c, z, nb):
    H, W = len(s), len(s[0])
    out = _copy(s)
    for y in range(H):
        for x in range(W):
            if s[y][x] == z and any(0 <= y + dy < H and 0 <= x + dx < W and s[y + dy][x + dx] != z
                                    for dy, dx in nb):
                out[y][x] = c
    return out


def _holes(s, c, z):
    H, W = len(s), len(s[0])
    seen = [[False] * W for _ in range(H)]
    st = [(y, x) for y in range(H) for x in range(W)
          if (y in (0, H - 1) or x in (0, W - 1)) and s[y][x] == z]
    for y, x in st:
        seen[y][x] = True
    while st:
        y, x = st.pop()
        for dy, dx in D4:
            p, q = y + dy, x + dx
            if 0 <= p < H and 0 <= q < W and not seen[p][q] and s[p][q] == z:
                seen[p][q] = True
                st.append((p, q))
    return [[c if (s[y][x] == z and not seen[y][x]) else s[y][x] for x in range(W)] for y in range(H)]


def _bbox(s, c, z):
    cells = [(y, x) for y, row in enumerate(s) for x, v in enumerate(row) if v != z]
    out = _copy(s)
    if not cells:
        return out
    y0, y1 = min(p[0] for p in cells), max(p[0] for p in cells)
    x0, x1 = min(p[1] for p in cells), max(p[1] for p in cells)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if out[y][x] == z:
                out[y][x] = c
    return out


def _lines(s, c, z, rows, cols):
    rs = {y for y, row in enumerate(s) if any(v != z for v in row)} if rows else set()
    cs = {x for x in range(len(s[0])) if any(row[x] != z for row in s)} if cols else set()
    return [[c if (v == z and (y in rs or x in cs)) else v for x, v in enumerate(row)] for y, row in enumerate(s)]


def _fixed(f):
    return (lambda demos: True if all(f(s, c, z) == t for s, t, c, z in demos) else None,
            lambda s, c, z, prm: f(s, c, z),
            lambda demos: True)


def _symrole(k):
    def fit(demos):
        return _rolemap_fit([(_sym(s, k), t, c, z) for s, t, c, z in demos])

    def vote(demos):
        return _rolemap_vote([(_sym(s, k), t, c, z) for s, t, c, z in demos])
    return fit, (lambda s, c, z, mp: _rolemap_apply(_sym(s, k), c, z, mp)), vote


MECHS = [("rolemap", 0) + _symrole(0)]
MECHS += [("connect_orth", 1) + _fixed(lambda s, c, z: _connect(s, c, z, D4)),
          ("connect_all8", 2) + _fixed(lambda s, c, z: _connect(s, c, z, D4 + DG))]
MECHS += [("rays_" + n, 3) + _fixed(lambda s, c, z, d=d: _rays(s, c, z, d)) for n, d in RAYDIRS.items()]
MECHS += [("halo4", 3) + _fixed(lambda s, c, z: _halo(s, c, z, D4)),
          ("halo8", 3) + _fixed(lambda s, c, z: _halo(s, c, z, D4 + DG)),
          ("holes", 3) + _fixed(_holes),
          ("bbox", 3) + _fixed(_bbox),
          ("rowcols", 3) + _fixed(lambda s, c, z: _lines(s, c, z, True, True)),
          ("rows", 3) + _fixed(lambda s, c, z: _lines(s, c, z, True, False)),
          ("cols", 3) + _fixed(lambda s, c, z: _lines(s, c, z, False, True))]
MECHS += [("sym%d_rolemap" % k, 4) + _symrole(k) for k in range(1, 8)]


def _orientations(demos, z):
    """All choices of direction (A->B or B->A) per demonstration, as (src, tgt, c, z) lists."""
    combos = [[]]
    for c, a, b in demos:
        combos = [cb + [d] for cb in combos for d in ((a, b, c, z), (b, a, c, z))]
        if len(combos) > 64:
            return combos[:64]
    return combos


def _mismatch(x, y):
    if len(x) != len(y) or len(x[0]) != len(y[0]):
        return 10 ** 9
    return sum(u != v for rx, ry in zip(x, y) for u, v in zip(rx, ry))


def _solve(g, fallback=True):
    rl = _roles(g)
    if rl is None:
        return None
    demos, (cq, src), z = rl
    combos = _orientations(demos, z)
    for name, _, fit, apply, _ in MECHS:
        for dm in combos:
            prm = fit(dm)
            if prm is not None:
                return apply(src, cq, z, prm)
    if not fallback:
        return None
    best = None
    for name, _, fit, apply, vote in MECHS:
        for dm in combos:
            prm = vote(dm)
            try:
                err = sum(_mismatch(apply(s, c, zz, prm), t) for s, t, c, zz in dm)
            except Exception:
                continue
            if best is None or err < best[0]:
                best = (err, apply, prm)
    return best[1](src, cq, z, best[2]) if best else None


def fam(train):
    if not train:
        return
    for pr in train:
        if _roles(pr["input"]) is None:
            return
    strict = lambda g: _solve(g, fallback=False)
    if not all(strict(pr["input"]) == pr["output"] for pr in train):
        return

    def fn(g):
        out = _solve(g, fallback=True)
        return out if out is not None else [row[:] for row in g]
    yield ("common_frame_analogy", 2, fn)


FAMILIES = [fam]
