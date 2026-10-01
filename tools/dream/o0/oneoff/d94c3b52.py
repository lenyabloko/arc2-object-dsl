CARD = "d94c3b52"
READING = ("In the lattice of small shapes, every shape identical to the marker-coloured shape takes the marker "
           "colour, and every shape lying strictly between two marker shapes in the same lattice row or column "
           "takes the new colour.")


def _bands(flags):
    bands = []
    i = 0
    n = len(flags)
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            bands.append((i, j))
            i = j
        else:
            i += 1
    return bands


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _colors(train):
    """marker colour = non-bg, non-majority shape colour in input; new colour = colour only in outputs."""
    mk, nw = set(), set()
    for p in train:
        I, O = p["input"], p["output"]
        bg = _bg(I)
        cnt = {}
        for r in I:
            for x in r:
                if x != bg:
                    cnt[x] = cnt.get(x, 0) + 1
        if len(cnt) != 2:
            return None
        base = max(cnt, key=lambda k: cnt[k])
        mk.add(min(cnt, key=lambda k: cnt[k]))
        ic = set(x for r in I for x in r)
        oc = set(x for r in O for x in r)
        nw |= (oc - ic)
    if len(mk) != 1 or len(nw) != 1:
        return None
    return next(iter(mk)), next(iter(nw))


def _make(M, N, consecutive_only):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        rb = _bands([any(g[r][c] != bg for c in range(W)) for r in range(H)])
        cb = _bands([any(g[r][c] != bg for r in range(H)) for c in range(W)])
        out = [row[:] for row in g]
        R, C = len(rb), len(cb)
        mask = {}
        has_m = {}
        for i, (r0, r1) in enumerate(rb):
            for j, (c0, c1) in enumerate(cb):
                mask[(i, j)] = tuple(tuple(g[r][c] != bg for c in range(c0, c1)) for r in range(r0, r1))
                has_m[(i, j)] = any(g[r][c] == M for r in range(r0, r1) for c in range(c0, c1))
        temps = {mask[k] for k in mask if has_m[k]}
        lab = {}
        for k in mask:
            if mask[k] in temps and any(any(row) for row in mask[k]):
                lab[k] = M
        new = {}
        for i in range(R):
            js = [j for j in range(C) if lab.get((i, j)) == M]
            if len(js) >= 2:
                for j in range(min(js) + 1, max(js)):
                    if (i, j) not in lab:
                        new[(i, j)] = N
        for j in range(C):
            is_ = [i for i in range(R) if lab.get((i, j)) == M]
            if len(is_) >= 2:
                for i in range(min(is_) + 1, max(is_)):
                    if (i, j) not in lab:
                        new[(i, j)] = N
        lab.update(new)
        for (i, j), col in lab.items():
            r0, r1 = rb[i]
            c0, c1 = cb[j]
            for r in range(r0, r1):
                for c in range(c0, c1):
                    if g[r][c] != bg:
                        out[r][c] = col
        return out
    return fn


def fam(train):
    cs = _colors(train)
    cands = []
    if cs is not None:
        cands.append(("lattice_match_between_%d_%d" % cs, 0, _make(cs[0], cs[1], False)))
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
