CARD = "da2b0fe3"
READING = ("The shape is split by an empty row or column running through its bounding box; that whole grid row "
           "or column is filled with the new colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _newcol(train):
    s = set()
    for p in train:
        ic = set(x for r in p["input"] for x in r)
        oc = set(x for r in p["output"] for x in r)
        s |= (oc - ic)
    return next(iter(s)) if len(s) == 1 else None


def _make(N):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
        out = [row[:] for row in g]
        if not cells:
            return out
        r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
        c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
        for r in range(r0 + 1, r1):
            if all(g[r][c] == bg for c in range(c0, c1 + 1)):
                for c in range(W):
                    out[r][c] = N
        for c in range(c0 + 1, c1):
            if all(g[r][c] == bg for r in range(r0, r1 + 1)):
                for r in range(H):
                    out[r][c] = N
        return out
    return fn


def fam(train):
    N = _newcol(train)
    cands = []
    if N is not None:
        cands.append(("fill_split_line_%d" % N, 0, _make(N)))
    n = 0
    for name, cost, fn in cands:
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != p["output"]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield (name, cost, fn)
            n += 1
            if n >= 3:
                return


FAMILIES = [fam]
