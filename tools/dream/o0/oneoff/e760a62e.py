CARD = "e760a62e"
READING = ("The grid is a lattice of cells separated by full lines; every pair of cells in the same "
           "lattice row or column holding a marker of the same colour is joined by filling all cells "
           "between them (inclusive) with that colour, and cells covered by two colours get the "
           "combined colour learned from training (sum by default).")


def _lattice(g):
    H, W = len(g), len(g[0])
    for sep in sorted({x for r in g for x in r}):
        if sep == 0:
            continue
        rows = [i for i in range(H) if all(x == sep for x in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == sep for i in range(H))]
        if rows and cols:
            return sep, rows, cols
    return None


def _bands(n, seps):
    out, s = [], 0
    for k in list(seps) + [n]:
        if k > s:
            out.append((s, k))
        s = k + 1
    return out


def _analyse(g):
    lat = _lattice(g)
    if lat is None:
        return None
    sep, rows, cols = lat
    rb, cb = _bands(len(g), rows), _bands(len(g[0]), cols)
    marks = {}
    for a, (r0, r1) in enumerate(rb):
        for b, (c0, c1) in enumerate(cb):
            cs = {g[i][j] for i in range(r0, r1) for j in range(c0, c1)} - {0, sep}
            if len(cs) == 1:
                marks[(a, b)] = cs.pop()
    return rb, cb, marks


def _cover(marks):
    cov = {}
    items = list(marks.items())
    for x in range(len(items)):
        (a1, b1), c1 = items[x]
        for y in range(x + 1, len(items)):
            (a2, b2), c2 = items[y]
            if c1 != c2:
                continue
            if a1 == a2:
                for b in range(min(b1, b2), max(b1, b2) + 1):
                    cov.setdefault((a1, b), set()).add(c1)
            elif b1 == b2:
                for a in range(min(a1, a2), max(a1, a2) + 1):
                    cov.setdefault((a, b1), set()).add(c1)
    return cov


def _make(mix):
    def fn(g):
        an = _analyse(g)
        out = [list(r) for r in g]
        if an is None:
            return out
        rb, cb, marks = an
        for (a, b), cs in _cover(marks).items():
            key = frozenset(cs)
            col = mix.get(key, sum(cs)) if len(cs) > 1 else next(iter(cs))
            r0, r1 = rb[a]
            c0, c1 = cb[b]
            for i in range(r0, r1):
                for j in range(c0, c1):
                    out[i][j] = col
        return out
    return fn


def fam(train):
    mix = {}
    for p in train:
        an = _analyse(p["input"])
        if an is None:
            return
        rb, cb, marks = an
        for (a, b), cs in _cover(marks).items():
            if len(cs) > 1:
                r0 = rb[a][0]
                c0 = cb[b][0]
                v = p["output"][r0][c0]
                k = frozenset(cs)
                if mix.get(k, v) != v:
                    return
                mix[k] = v
    fn = _make(mix)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("lattice_join_same_colour", 1.0, fn)


FAMILIES = [fam]
