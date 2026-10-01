CARD = "98cf29f8"
READING = ("The rectangle that has a one-cell-thick arm slides along the arm by the arm's length "
           "(until it touches the other rectangle), and the arm disappears.")


def _mode(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _split(g, bg):
    H, W = len(g), len(g[0])
    cols = {}
    for i in range(H):
        for j in range(W):
            if g[i][j] != bg:
                cols.setdefault(g[i][j], []).append((i, j))
    res = []
    for c, cells in cols.items():
        s = set(cells)
        arm = set()
        for (i, j) in cells:
            v = (i - 1, j) in s or (i + 1, j) in s
            h = (i, j - 1) in s or (i, j + 1) in s
            if not (v and h):
                arm.add((i, j))
        res.append((c, s, arm))
    return res


def _make(mode):
    def fn(g):
        bg = _mode(g)
        H, W = len(g), len(g[0])
        objs = _split(g, bg)
        out = [list(r) for r in g]
        movers = [o for o in objs if o[2]]
        if len(movers) != 1:
            return out
        c, s, arm = movers[0]
        body = s - arm
        if not body:
            return out
        others = set()
        for o in objs:
            if o is not movers[0]:
                others |= o[1]
        arows = {i for i, j in arm}
        acols = {j for i, j in arm}
        bri = sum(i for i, j in body) / len(body)
        brj = sum(j for i, j in body) / len(body)
        ari = sum(i for i, j in arm) / len(arm)
        arj = sum(j for i, j in arm) / len(arm)
        if len(arows) == 1:
            di, dj = 0, (1 if arj > brj else -1)
        elif len(acols) == 1:
            di, dj = (1 if ari > bri else -1), 0
        else:
            return out
        if mode == "armlen":
            k = len(arm)
        else:
            k = 0
            while True:
                nxt = {(i + di * (k + 1), j + dj * (k + 1)) for i, j in body}
                if any(not (0 <= a < H and 0 <= b < W) for a, b in nxt) or (nxt & others):
                    break
                k += 1
        for (i, j) in s:
            out[i][j] = bg
        for (i, j) in body:
            a, b = i + di * k, j + dj * k
            if 0 <= a < H and 0 <= b < W:
                out[a][b] = c
        return out
    return fn


def fam(train):
    for mode, cost in (("armlen", 1.0), ("touch", 1.5)):
        fn = _make(mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("slide_body_along_arm_" + mode, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
