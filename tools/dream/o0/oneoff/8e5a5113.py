CARD = "8e5a5113"
READING = ("The grid is cut into equal panels by solid separator lines; the empty panels are filled "
           "with fixed rotations/reflections (learned per panel position) of the one filled panel.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _ranges(n, seps):
    out, s = [], 0
    for x in sorted(seps) + [n]:
        if x > s:
            out.append((s, x))
        s = x + 1
    return out


def _panels(g, bg):
    # separator colour: a colour whose full rows/columns cut the grid into >=2 equal panels
    H, W = len(g), len(g[0])
    best = None
    for col in sorted(set(x for r in g for x in r)):
        if col == bg:
            continue
        rows = [i for i in range(H) if all(x == col for x in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == col for i in range(H))]
        if not rows and not cols:
            continue
        rr = _ranges(H, rows)
        cc = _ranges(W, cols)
        ps = [(a, b, c, d) for (a, b) in rr for (c, d) in cc]
        if len(ps) < 2 or len(set((b - a, d - c) for a, b, c, d in ps)) != 1:
            continue
        if best is None or len(ps) > len(best):
            best = ps
    return best or []


def _cut(g, p):
    a, b, c, d = p
    return [row[c:d] for row in g[a:b]]


def _d4():
    def rot(m):
        return [list(r) for r in zip(*m[::-1])]

    def flip(m):
        return [r[::-1] for r in m]
    ts = []
    for f in (False, True):
        for k in range(4):
            def t(m, f=f, k=k):
                x = flip(m) if f else [r[:] for r in m]
                for _ in range(k):
                    x = rot(x)
                return x
            ts.append(((f, k), t))
    return ts


def _source(g, bg, ps):
    filled = [i for i, p in enumerate(ps) if any(x != bg for r in _cut(g, p) for x in r)]
    return filled[0] if len(filled) == 1 else None


def _learn(train):
    D4 = _d4()
    n = None
    src = None
    choice = None
    for pr in train:
        g, o = pr["input"], pr["output"]
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return None
        bg = _bg(g)
        ps = _panels(g, bg)
        if len(ps) < 2:
            return None
        s = _source(g, bg, ps)
        if s is None:
            return None
        if n is None:
            n, src = len(ps), s
            choice = {i: [t for t in D4] for i in range(n) if i != s}
        elif n != len(ps) or src != s:
            return None
        S = _cut(g, ps[s])
        for i in choice:
            tgt = _cut(o, ps[i])
            choice[i] = [(k, t) for (k, t) in choice[i] if t(S) == tgt]
            if not choice[i]:
                return None
    return src, {i: v[0][1] for i, v in choice.items()}


def fam(train):
    try:
        L = _learn(train)
    except Exception:
        L = None
    if L is None:
        return
    src, tmap = L

    def fn(g):
        bg = _bg(g)
        ps = _panels(g, bg)
        s = _source(g, bg, ps)
        if s is None:
            s = src
        out = [row[:] for row in g]
        S = _cut(g, ps[s])
        for i, t in tmap.items():
            if i >= len(ps):
                continue
            a, b, c, d = ps[i]
            m = t(S)
            if len(m) != b - a or len(m[0]) != d - c:
                continue
            for r in range(b - a):
                for q in range(d - c):
                    out[a + r][c + q] = m[r][q]
        return out
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("panel_d4_copy", 1.0, fn)


FAMILIES = [fam]
