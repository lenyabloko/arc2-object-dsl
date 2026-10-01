CARD = "72207abc"
READING = ("The seed colours along the single occupied line are repeated cyclically at positions "
           "whose gaps grow by one each step (0, 1, 3, 6, 10, ...) until the line ends.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _make(d0, dd):
    def core(g):
        bg = _bg(g)
        rows = [i for i, r in enumerate(g) if any(x != bg for x in r)]
        if len(rows) != 1:
            return None
        i = rows[0]
        row = g[i]
        seed = [x for x in row if x != bg]
        if not seed:
            return None
        W = len(row)
        new = [bg] * W
        p, n, k = 0, 0, 0
        while p < W:
            new[p] = seed[k % len(seed)]
            k += 1
            p += d0 + n * dd
            n += 1
        out = [list(r) for r in g]
        out[i] = new
        return out

    def fn(g):
        r = core(g)
        if r is not None:
            return r
        r = core(_transpose(g))
        return None if r is None else _transpose(r)
    return fn


def fam(train):
    for dd in (1, 0, 2):
        for d0 in (1, 2, 3):
            fn = _make(d0, dd)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("cyclic_seed_gap%d_inc%d" % (d0, dd), 1, fn)
            except Exception:
                pass


FAMILIES = [fam]
