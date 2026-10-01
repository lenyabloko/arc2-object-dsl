CARD = "05a7bcf2"
READING = ("Each small object on one side of the full separator line is recoloured, the gap between "
           "it and the separator is filled with the object colour, and beyond the separator its rows/"
           "columns are filled with the separator colour, pushing that lane's ground-colour cells to "
           "the far edge.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _V(g):
    return [list(r) for r in g[::-1]]


# canonical transforms: (forward, inverse)
_TRANS = [
    (lambda g: [list(r) for r in g], lambda g: [list(r) for r in g]),
    (_V, _V),
    (_T, _T),
    (lambda g: _V(_T(g)), lambda g: _T(_V(g))),
]


def _canon(g):
    """Return (k, s, S, G) for the first transform where a full row s of colour S separates
    objects (above) from a full ground row of colour G (below)."""
    bg = _bg(g)
    for k, (f, inv) in enumerate(_TRANS):
        h = f(g)
        H = len(h)
        full = [(i, h[i][0]) for i in range(H)
                if h[i][0] != bg and all(x == h[i][0] for x in h[i])]
        for s, S in full:
            above = any(x != bg for r in h[:s] for x in r)
            for gi, G in full:
                if gi > s and G != S and above:
                    # objects above must not contain the ground colour line
                    return k, s, S, G, bg
    return None


def _apply(g, newcol_map, newcol_default):
    c = _canon(g)
    if c is None:
        return None
    k, s, S, G, bg = c
    f, inv = _TRANS[k]
    h = f(g)
    H, W = len(h), len(h[0])
    out = [list(r) for r in h]
    for col in range(W):
        objrows = [i for i in range(s) if h[i][col] not in (bg, S, G)]
        if not objrows:
            continue
        m = max(objrows)
        ocol = h[m][col]
        nc = newcol_map.get(ocol, newcol_default)
        for i in objrows:
            out[i][col] = newcol_map.get(h[i][col], nc)
        for i in range(m + 1, s):
            out[i][col] = ocol
        kcnt = sum(1 for i in range(s + 1, H) if h[i][col] == G)
        for i in range(s + 1, H):
            out[i][col] = S
        for i in range(H - kcnt, H):
            out[i][col] = G
    return inv(out)


def _learn(train):
    mp = {}
    for p in train:
        c = _canon(p["input"])
        if c is None:
            return None
        k, s, S, G, bg = c
        a, b = p["input"], p["output"]
        f = _TRANS[k][0]
        ha, hb = f(a), f(b)
        for i in range(s):
            for j in range(len(ha[0])):
                x = ha[i][j]
                if x not in (bg, S, G):
                    y = hb[i][j]
                    if mp.get(x, y) != y:
                        return None
                    mp[x] = y
    return mp


def fam(train):
    mp = _learn(train)
    if mp is None:
        return
    vals = list(mp.values())
    default = vals[0] if vals and all(v == vals[0] for v in vals) else None

    def fn(g, mp=mp, default=default):
        r = _apply(g, mp, default if default is not None else 0)
        return r if r is not None else [list(x) for x in g]

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("beam_push", 1, fn)


FAMILIES = [fam]
