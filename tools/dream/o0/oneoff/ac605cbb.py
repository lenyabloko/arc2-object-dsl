CARD = "ac605cbb"
READING = ("Each coloured dot shoots a trail of fixed length in its colour's own direction and caps it "
           "with a copy of itself (both learned per colour); where two trails cross, the crossing "
           "turns a new colour and a diagonal ray of that colour runs from it to the edge.")

_DIRS = [(0, 1), (0, -1), (1, 0), (-1, 0)]
_NB8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _dots(g, bg):
    return [(i, j, v) for i, r in enumerate(g) for j, v in enumerate(r) if v != bg]


def _learn(train):
    ins, outs, cnt = set(), set(), {}
    for p in train:
        for r in p["input"]:
            ins.update(r)
        for r in p["output"]:
            for v in r:
                outs.add(v)
                cnt[v] = cnt.get(v, 0) + 1
    new = [v for v in outs if v not in ins]
    if not new:
        return None
    new.sort(key=lambda v: -cnt[v])
    T = new[0]
    X = new[1] if len(new) > 1 else None
    newset = set(new)
    inst = {}
    for k, p in enumerate(train):
        bg = _bg(p["input"])
        for i, j, v in _dots(p["input"], bg):
            inst.setdefault(v, []).append((k, i, j))
    maxL = max(max(len(p["input"]), len(p["input"][0])) for p in train)
    stamps = {}
    for c, lst in inst.items():
        best = None
        for d in _DIRS:
            for L in range(1, maxL + 1):
                for m in [None] + _NB8:
                    ok = True
                    seen_any = False
                    for k, i, j in lst:
                        o = train[k]["output"]
                        H, W = len(o), len(o[0])
                        for s in range(1, L + 1):
                            x, y = i + d[0] * s, j + d[1] * s
                            if 0 <= x < H and 0 <= y < W:
                                seen_any = True
                                if o[x][y] not in newset:
                                    ok = False
                                    break
                        if not ok:
                            break
                        if m is not None:
                            x, y = i + d[0] * L + m[0], j + d[1] * L + m[1]
                            if 0 <= x < H and 0 <= y < W:
                                if o[x][y] != c:
                                    ok = False
                                    break
                    if not ok or not seen_any:
                        continue
                    score = (L, m is not None, m == d)
                    if best is None or score > best[0]:
                        best = (score, d, L, m)
        if best is None:
            return None
        stamps[c] = best[1:]
    return T, X, stamps


def _make(T, X, stamps, ray):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [r[:] for r in g]
        cover = {}
        marks = []
        for i, j, c in _dots(g, bg):
            if c not in stamps:
                continue
            d, L, m = stamps[c]
            for s in range(1, L + 1):
                x, y = i + d[0] * s, j + d[1] * s
                if 0 <= x < H and 0 <= y < W:
                    cover[(x, y)] = cover.get((x, y), 0) + 1
            if m is not None:
                marks.append((i + d[0] * L + m[0], j + d[1] * L + m[1], c))
        for (x, y), n in cover.items():
            if g[x][y] == bg:
                out[x][y] = T
        for x, y, c in marks:
            if 0 <= x < H and 0 <= y < W and g[x][y] == bg:
                out[x][y] = c
        for (x, y), n in cover.items():
            if n >= 2 and X is not None:
                out[x][y] = X
                if ray is not None:
                    a, b = x + ray[0], y + ray[1]
                    while 0 <= a < H and 0 <= b < W:
                        if out[a][b] == bg:
                            out[a][b] = X
                        a += ray[0]
                        b += ray[1]
        return out
    return fn


def fam(train):
    lr = _learn(train)
    if lr is None:
        return
    T, X, stamps = lr
    rays = [(1, -1), (1, 1), (-1, -1), (-1, 1), None, (1, 0), (-1, 0), (0, 1), (0, -1)]
    n = 0
    for k, ray in enumerate(rays):
        fn = _make(T, X, stamps, ray)
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
            yield ("dot_trails_ray%s" % (ray,), 1 + k, fn)
            n += 1
            if n >= 2:
                return


FAMILIES = [fam]
