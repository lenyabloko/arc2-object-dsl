"""Line expansion for 4c7dc4dd: Raven 2x2 matrix of framed panels, one blank (test-blind; train pairs only)."""
from collections import Counter, defaultdict
from itertools import combinations

CARD = "4c7dc4dd"
LINE = 'Raven Matrix: The noisy sheet carries a 2 x 2 matrix of equal-sized framed panels ("windows"). Exactly one panel is blank.'
READING = {
    "generator": "Find the four equal-sized framed panels laid out two above two on the noisy sheet and fill the blank one: "
                 "take its row- or column-mate and transform it the way the complete opposite pair is related (D4 map with recolouring, "
                 "mask complement, toggling straight lines between aligned marks, or XOR), carrying colours across by matching the two pairs' palettes.",
    "stop": "A single panel is drawn: stop once the blank window's interior is filled; connecting lines run only between consecutive aligned marks.",
    "params": "axis ∈ {auto: cheapest relation over row/column pairing (ties row-first), auto col-first, row, col} · "
              "relation ∈ {D4 map + colour map, complement, connect-toggle, xor}, picked per input by cost · out ∈ {interior, framed, in-place}",
    "participants": "panels = rectangles with a one-cell monochrome border and an interior of at least 2x2, four of the same size (border colours may differ), "
                    "non-overlapping, two above two; the blank = the one with a uniform interior (that colour is the panel background); "
                    "marks = non-background interior cells; colour transport = shared colours fixed, unshared ones matched by frequency rank.",
    "preconditions": "Every input holds exactly one such 2x2 set with exactly one blank panel and three non-blank ones; some relation in the domain links "
                     "the complete opposite pair; the output has the interior's shape (or the framed panel's, or the input's).",
}

D4 = [
    ("id", lambda G: G),
    ("flipx", lambda G: tuple(tuple(r[::-1]) for r in G)),
    ("flipy", lambda G: tuple(G[::-1])),
    ("rot180", lambda G: tuple(tuple(r[::-1]) for r in G[::-1])),
    ("transpose", lambda G: tuple(zip(*G))),
    ("anti", lambda G: tuple(tuple(r[::-1]) for r in tuple(zip(*G))[::-1])),
    ("rot90", lambda G: tuple(tuple(r) for r in zip(*G[::-1]))),
    ("rot270", lambda G: tuple(tuple(r) for r in zip(*G))[::-1]),
]


# ---------------------------------------------------------------- panel finding
def _rects(g):
    H, W = len(g), len(g[0])
    R = [[1] * W for _ in range(H)]
    D = [[1] * W for _ in range(H)]
    for r in range(H):
        for c in range(W - 2, -1, -1):
            if g[r][c + 1] == g[r][c]: R[r][c] = R[r][c + 1] + 1
    for c in range(W):
        for r in range(H - 2, -1, -1):
            if g[r + 1][c] == g[r][c]: D[r][c] = D[r + 1][c] + 1
    out = defaultdict(list)
    for r in range(H):
        for c in range(W):
            f = g[r][c]
            if R[r][c] < 4 or D[r][c] < 4: continue
            for w in range(4, R[r][c] + 1):
                cr = c + w - 1
                if D[r][cr] < 4: continue
                for h in range(4, min(D[r][c], D[r][cr]) + 1):
                    rb = r + h - 1
                    if R[rb][c] < w: continue
                    # interior must not be the frame colour at all four corners (prunes uniform areas)
                    if g[r + 1][c + 1] == f and g[r + 1][cr - 1] == f and g[rb - 1][c + 1] == f and g[rb - 1][cr - 1] == f: continue
                    out[(f, h, w)].append((r, c))
    return out


def _interior(g, r, c, h, w):
    return tuple(tuple(g[i][c + 1:c + w - 1]) for i in range(r + 1, r + h - 1))


def panels(g):
    """-> dict(f, h, w, bg, pos{(i,j): (r,c)}, grid{(i,j): interior}, blank (i,j)) or None."""
    best = None
    by_size = defaultdict(list)
    for (f, h, w), lst in _rects(g).items():
        by_size[(h, w)] += [(r, c, f) for r, c in lst]
    for (h, w), lst in sorted(by_size.items()):
        if len(lst) < 4 or len(lst) > 12: continue
        for combo in combinations(sorted(lst), 4):
            if any(abs(a[0] - b[0]) < h and abs(a[1] - b[1]) < w for a, b in combinations(combo, 2)): continue
            ints = [_interior(g, r, c, h, w) for r, c, _ in combo]
            uni = [k for k, I in enumerate(ints) if len({v for row in I for v in row}) == 1]
            if len(uni) != 1: continue
            bg = ints[uni[0]][0][0]
            if any(bg == x[2] for x in combo): continue
            if not all(any(bg in row for row in I) for I in ints): continue
            srt = sorted(range(4), key=lambda k: (combo[k][0], combo[k][1]))
            top, bot = sorted(srt[:2], key=lambda k: combo[k][1]), sorted(srt[2:], key=lambda k: combo[k][1])
            if max(combo[k][0] for k in top) >= min(combo[k][0] for k in bot): continue
            if max(combo[top[0]][1], combo[bot[0]][1]) >= min(combo[top[1]][1], combo[bot[1]][1]): continue
            lay = {(0, 0): top[0], (0, 1): top[1], (1, 0): bot[0], (1, 1): bot[1]}
            cand = {"f": combo[uni[0]][2], "h": h, "w": w, "bg": bg,
                    "pos": {ij: combo[k][:2] for ij, k in lay.items()},
                    "grid": {ij: ints[k] for ij, k in lay.items()},
                    "blank": next(ij for ij, k in lay.items() if k == uni[0])}
            key = h * w
            if best is None or key > best[0]: best = (key, cand)
    return best[1] if best else None


# ---------------------------------------------------------------- relations
def _cols(G, bg):
    return Counter(v for row in G for v in row if v != bg)


def _transport(P, Q, R, bg):
    src = _cols(P, bg) + _cols(Q, bg); dst = _cols(R, bg)
    m = {c: c for c in src if c in dst}
    so = sorted((c for c in src if c not in dst), key=lambda c: (-src[c], c))
    do = sorted((c for c in dst if c not in src), key=lambda c: (-dst[c], c))
    if len(so) == len(do):
        m.update(zip(so, do))
    return m


def connect(G, c, bg):
    H, W = len(G), len(G[0]); X = [list(r) for r in G]
    for r in range(H):
        idx = [j for j in range(W) if G[r][j] != bg]
        for a, b in zip(idx, idx[1:]):
            for j in range(a + 1, b): X[r][j] = c
    for j in range(W):
        idx = [i for i in range(H) if G[i][j] != bg]
        for a, b in zip(idx, idx[1:]):
            for i in range(a + 1, b): X[i][j] = c
    return tuple(map(tuple, X))


def strip(G, c, bg):
    H, W = len(G), len(G[0]); X = [list(r) for r in G]
    lines = [[(r, j) for j in range(W)] for r in range(H)] + [[(i, j) for i in range(H)] for j in range(W)]
    for ln in lines:
        k = 0
        while k < len(ln):
            if G[ln[k][0]][ln[k][1]] == bg: k += 1; continue
            e = k
            while e + 1 < len(ln) and G[ln[e + 1][0]][ln[e + 1][1]] != bg: e += 1
            inner = ln[k + 1:e]
            if inner and all(G[i][j] == c for i, j in inner):
                for i, j in inner: X[i][j] = bg
            k = e + 1
    S = tuple(map(tuple, X))
    return S if connect(S, c, bg) == G else None


def _mask(G, bg):
    return tuple(tuple(v != bg for v in row) for row in G)


def relation(P, Q, R, bg, use_xor=True):
    """Find the cheapest relation P->Q and return (cost, name, X) with X its analogue applied to R."""
    sig = _transport(P, Q, R, bg)
    sg = lambda c: sig.get(c, c)
    inv = {v: k for k, v in sig.items()}
    # 1. D4 map + colour map
    for gi, (gname, g) in enumerate(D4):
        GP = g(P)
        if len(GP) != len(Q) or len(GP[0]) != len(Q[0]): continue
        kap = {bg: bg}; ok = True
        for ra, rb in zip(GP, Q):
            for a, b in zip(ra, rb):
                if kap.setdefault(a, b) != b: ok = False; break
            if not ok: break
        if not ok or len(set(kap.values())) != len(kap): continue
        GR = g(R)
        if len(GR) != len(Q) or len(GR[0]) != len(Q[0]): continue
        rec = {}
        for x in _cols(R, bg):
            s = inv.get(x)
            rec[x] = sg(kap[s]) if s is not None and s in kap else x
        X = tuple(tuple(rec.get(v, v) for v in row) for row in GR)
        ident = all(a == b for a, b in kap.items())
        return (1 if gi == 0 else 2) + (0 if ident else 1), "geo:" + gname, X
    if len(P) != len(Q) or len(P[0]) != len(Q[0]) or len(P) != len(R) or len(P[0]) != len(R[0]): return None
    # 2. complement
    mP, mQ = _mask(P, bg), _mask(Q, bg)
    qc = _cols(Q, bg)
    if len(qc) == 1 and all(a != b for ra, rb in zip(mP, mQ) for a, b in zip(ra, rb)):
        q = sg(next(iter(qc)))
        X = tuple(tuple(bg if v != bg else q for v in row) for row in R)
        if any(v != bg for row in X for v in row): return 3, "complement", X
    # 3. connect-toggle
    diff = [(a, b) for ra, rb in zip(P, Q) for a, b in zip(ra, rb) if a != b]
    if diff:
        if all(a == bg for a, b in diff) and len({b for a, b in diff}) == 1:
            c, p_sparse = diff[0][1], True
            ok = connect(P, c, bg) == Q
        elif all(b == bg for a, b in diff) and len({a for a, b in diff}) == 1:
            c, p_sparse = diff[0][0], False
            ok = connect(Q, c, bg) == P
        else:
            ok = False
        if ok:
            c2 = sg(c)
            up = connect(R, c2, bg); down = strip(R, c2, bg)
            opts = [up, down] if p_sparse else [down, up]
            for X in opts:
                if X is not None and X != R: return 3, "connect-toggle", X
    # 4. xor (monochrome masks only)
    if use_xor:
        cp, cq, cr = _cols(P, bg), _cols(Q, bg), _cols(R, bg)
        if len(cp) <= 1 and len(cq) == 1 and len(cr) <= 1:
            q = sg(next(iter(cq)))
            mR = _mask(R, bg)
            X = tuple(tuple(q if (a ^ b ^ d) else bg for a, b, d in zip(ra, rb, rd)) for ra, rb, rd in zip(mP, mQ, mR))
            if any(v != bg for row in X for v in row): return 5, "xor", X
    return None


def solve(g, axes, out="interior", use_xor=True):
    pn = panels(g)
    if pn is None: return None
    (bi, bj), G, bg = pn["blank"], pn["grid"], pn["bg"]
    P = G[(1 - bi, 1 - bj)]
    best = None
    for ax in axes:
        if ax == "row": R, Q = G[(bi, 1 - bj)], G[(1 - bi, bj)]
        else: R, Q = G[(1 - bi, bj)], G[(bi, 1 - bj)]
        rel = relation(P, Q, R, bg, use_xor)
        if rel and (best is None or rel[0] < best[0]): best = rel
    if best is None: return None
    X = [list(r) for r in best[2]]
    if out == "interior": return X
    f = pn["f"]; w = len(X[0]) + 2
    if out == "framed": return [[f] * w] + [[f] + r + [f] for r in X] + [[f] * w]
    r0, c0 = pn["pos"][(bi, bj)]
    Y = [list(r) for r in g]
    for i, row in enumerate(X):
        Y[r0 + 1 + i][c0 + 1:c0 + 1 + len(row)] = row
    return Y


VARIANTS = [("auto", ("row", "col")), ("auto-colfirst", ("col", "row")), ("row", ("row",)), ("col", ("col",))]


def fam(train):
    pns = []
    for p in train:
        pn = panels(p["input"])
        if pn is None: return
        pns.append(pn)
    outs = []
    for o in ("interior", "framed", "inplace"):
        def shp(pn, g, o=o):
            ih, iw = pn["h"] - 2, pn["w"] - 2
            return {"interior": (ih, iw), "framed": (ih + 2, iw + 2), "inplace": (len(g), len(g[0]))}[o]
        if all(shp(pn, p["input"]) == (len(p["output"]), len(p["output"][0])) for pn, p in zip(pns, train)): outs.append(o)
    k = 0
    for o in outs:
        for use_xor in (True, False):
            for vname, axes in VARIANTS:
                fn = (lambda axes, o, ux: (lambda g: solve(g, axes, o, ux)))(axes, o, use_xor)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("raven2x2:%s:%s%s" % (vname, o, "" if use_xor else ":noxor"), 10 + k, fn)
                    k += 1


FAMILIES = [fam]
