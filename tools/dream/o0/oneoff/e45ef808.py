CARD = "e45ef808"
READING = ("Over a ground profile rising from the bottom, the sky cells of the deepest-valley column are "
           "painted one new colour and the sky cells of the highest-peak column another, each line running "
           "from the ground up to the top of the sky band.")


def _profile(g):
    H, W = len(g), len(g[0])
    cnt = {}
    for v in g[-1]:
        cnt[v] = cnt.get(v, 0) + 1
    ground = max(cnt, key=lambda k: cnt[k])
    tops = []
    for j in range(W):
        i = H - 1
        if g[i][j] != ground:
            tops.append(H)
            continue
        while i - 1 >= 0 and g[i - 1][j] == ground:
            i -= 1
        tops.append(i)
    return ground, tops


def _paint(out, g, j, top, col):
    if top <= 0:
        return
    sky = g[top - 1][j]
    i = top - 1
    while i >= 0 and g[i][j] == sky:
        out[i][j] = col
        i -= 1


def _apply(g, cv, cp, tie_v, tie_p):
    W = len(g[0])
    ground, tops = _profile(g)
    out = [r[:] for r in g]
    idx = list(range(W))
    if tie_v:
        idx_v = idx[::-1]
    else:
        idx_v = idx
    jv = max(idx_v, key=lambda j: tops[j])  # deepest valley: largest top row index
    idx_p = idx[::-1] if tie_p else idx
    if tie_p == 2:
        # farthest from valley column
        best = min(tops)
        cand = [j for j in idx if tops[j] == best]
        jp = max(cand, key=lambda j: (abs(j - jv), j))
    else:
        jp = min(idx_p, key=lambda j: tops[j])
    _paint(out, g, jv, tops[jv], cv)
    _paint(out, g, jp, tops[jp], cp)
    return out


def _make(cv, cp, tv, tp):
    return lambda g: _apply(g, cv, cp, tv, tp)


def fam(train):
    inc = set(v for p in train for r in p["input"] for v in r)
    outc = set(v for p in train for r in p["output"] for v in r)
    new = sorted(outc - inc)
    cands = []
    for cv in new:
        for cp in new:
            if cv == cp:
                continue
            for tv in (0, 1):
                for tp in (2, 1, 0):
                    cands.append(("valley%d_peak%d_tv%d_tp%d" % (cv, cp, tv, tp), tv + (0 if tp == 2 else 1),
                                  _make(cv, cp, tv, tp)))
    cands.sort(key=lambda t: t[1])
    k = 0
    seen = set()
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
            k += 1
            if k >= 3:
                return


FAMILIES = [fam]
