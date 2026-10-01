CARD = "8a004b2b"
READING = ("Crop the rectangle marked by four corner cells and complete it with the small pattern found outside "
           "it, scaled up and positioned so that it agrees with the scaled fragments already inside the frame.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _frame(g, bg):
    pos = {}
    for i, r in enumerate(g):
        for j, x in enumerate(r):
            if x != bg:
                pos.setdefault(x, []).append((i, j))
    best = None
    for col, ps in pos.items():
        if len(ps) != 4:
            continue
        rs = sorted(set(p[0] for p in ps))
        cs = sorted(set(p[1] for p in ps))
        if len(rs) == 2 and len(cs) == 2 and set(ps) == {(a, b) for a in rs for b in cs}:
            area = (rs[1] - rs[0]) * (cs[1] - cs[0])
            if best is None or area > best[0]:
                best = (area, col, rs[0], rs[1], cs[0], cs[1])
    return best


def _solve(g, paint_zero=False):
    bg = _bg(g)
    fr = _frame(g, bg)
    if fr is None:
        return None
    _, mk, r0, r1, c0, c1 = fr
    H, W = len(g), len(g[0])
    inside = {}
    tcells = []
    for i in range(H):
        for j in range(W):
            x = g[i][j]
            if x == bg:
                continue
            if r0 <= i <= r1 and c0 <= j <= c1:
                if not (x == mk and i in (r0, r1) and j in (c0, c1)):
                    inside[(i, j)] = x
            else:
                tcells.append((i, j))
    if not tcells or not inside:
        return None
    ti0 = min(p[0] for p in tcells); ti1 = max(p[0] for p in tcells)
    tj0 = min(p[1] for p in tcells); tj1 = max(p[1] for p in tcells)
    T = [[g[i][j] for j in range(tj0, tj1 + 1)] for i in range(ti0, ti1 + 1)]
    th, tw = len(T), len(T[0])
    ii0 = min(p[0] for p in inside); jj0 = min(p[1] for p in inside)
    sols = []
    smax = max(1, min((r1 - r0 + 1) // th, (c1 - c0 + 1) // tw))
    for s in range(smax, 0, -1):
        # offset candidates: top-left so that the inside fragments land on the scaled template
        for oi in range(r0, r1 - th * s + 2):
            for oj in range(c0, c1 - tw * s + 2):
                ok = True
                blocks = set()
                for (i, j), x in inside.items():
                    a, b = i - oi, j - oj
                    if not (0 <= a < th * s and 0 <= b < tw * s) or T[a // s][b // s] != x:
                        ok = False
                        break
                    blocks.add((a // s, b // s))
                # every touched template cell must be present as a whole s-by-s block
                if ok:
                    for (p, q) in blocks:
                        for a in range(p * s, p * s + s):
                            for b in range(q * s, q * s + s):
                                if (oi + a, oj + b) not in inside:
                                    ok = False
                if ok:
                    sols.append((s, oi, oj))
        if sols:
            break
    if not sols:
        return None
    s, oi, oj = sols[0]
    out = [list(g[i][c0:c1 + 1]) for i in range(r0, r1 + 1)]
    for a in range(th * s):
        for b in range(tw * s):
            v = T[a // s][b // s]
            if v == bg and not paint_zero:
                continue
            out[oi + a - r0][oj + b - c0] = v
    return out


def fam(train):
    for pz in (False, True):
        fn = (lambda p: (lambda g: _solve(g, p)))(pz)
        try:
            if all(fn(ex['input']) == ex['output'] for ex in train):
                yield ('frame_scaled_template%s' % ('_z' if pz else ''), 1 + pz, fn)
                return
        except Exception:
            continue


FAMILIES = [fam]
