CARD = "ed74f2f2"
READING = ("The grid holds two same-size shapes side by side; the left shape's pattern selects a colour "
           "(learned from the examples) and the output is the right shape painted in that colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _panels(g, bg):
    """Split the non-background content into column groups separated by empty columns."""
    H, W = len(g), len(g[0])
    occ = [any(g[i][j] != bg for i in range(H)) for j in range(W)]
    groups = []
    j = 0
    while j < W:
        if occ[j]:
            k = j
            while k < W and occ[k]:
                k += 1
            groups.append((j, k - 1))
            j = k
        else:
            j += 1
    rows = [i for i in range(H) if any(g[i][j] != bg for j in range(W))]
    if not rows or len(groups) != 2:
        return None
    r0, r1 = min(rows), max(rows)
    out = []
    for c0, c1 in groups:
        out.append([[g[i][j] for j in range(c0, c1 + 1)] for i in range(r0, r1 + 1)])
    return out


def _key(p, bg):
    return tuple(tuple(int(x != bg) for x in r) for r in p)


def _learn(train, key_idx):
    table = {}
    for pr in train:
        g, o = pr["input"], pr["output"]
        bg = _bg(g)
        ps = _panels(g, bg)
        if ps is None:
            return None
        tgt = ps[1 - key_idx]
        if len(o) != len(tgt) or len(o[0]) != len(tgt[0]):
            return None
        cols = set()
        for i in range(len(o)):
            for j in range(len(o[0])):
                if (tgt[i][j] == bg) != (o[i][j] == bg):
                    return None
                if o[i][j] != bg:
                    cols.add(o[i][j])
        if len(cols) != 1:
            return None
        k = _key(ps[key_idx], bg)
        c = cols.pop()
        if table.get(k, c) != c:
            return None
        table[k] = c
    return table


def _make(table, key_idx):
    def fn(g):
        bg = _bg(g)
        ps = _panels(g, bg)
        k = _key(ps[key_idx], bg)
        if k in table:
            c = table[k]
        else:  # nearest known key by Hamming distance
            def dist(t):
                if len(t) != len(k) or len(t[0]) != len(k[0]):
                    return 10 ** 9
                return sum(a != b for ra, rb in zip(t, k) for a, b in zip(ra, rb))
            c = table[min(sorted(table), key=dist)]
        tgt = ps[1 - key_idx]
        return [[c if x != bg else bg for x in r] for r in tgt]
    return fn


def fam(train):
    for key_idx in (0, 1):
        table = _learn(train, key_idx)
        if not table:
            continue
        fn = _make(table, key_idx)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("key_panel_%d_colours_other" % key_idx, 1 + key_idx, fn)
        except Exception:
            pass


FAMILIES = [fam]
