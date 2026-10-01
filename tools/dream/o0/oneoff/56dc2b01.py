CARD = "56dc2b01"
READING = ("The loose shape slides toward the full-length wall line until it touches it, and a new "
           "full-length line (in the colour introduced by the outputs) is drawn against the shape's far side.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _new_colour(train):
    cols = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        outs = set(x for r in p["output"] for x in r)
        c = outs - ins
        cols = c if cols is None else cols & c
    if cols and len(cols) == 1:
        return next(iter(cols))
    return None


def _solve_rows(g, bg, newc, gap):
    # returns None if no full non-bg row
    H, W = len(g), len(g[0])
    lines = [i for i in range(H) if g[i][0] != bg and all(x == g[i][0] for x in g[i])]
    # the wall's colour occurs nowhere outside the wall line
    lines = [i for i in lines
             if not any(g[a][b] == g[i][0] for a in range(H) if a != i for b in range(W))]
    if len(lines) != 1:
        return None
    lr = lines[0]
    cells = [(i, j) for i in range(H) for j in range(W) if i != lr and g[i][j] != bg]
    if not cells:
        return None
    s0 = min(i for i, _ in cells); s1 = max(i for i, _ in cells)
    if s0 > lr:
        shift = lr + 1 + gap - s0
        nl = s1 + shift + 1
    else:
        shift = lr - 1 - gap - s1
        nl = s0 + shift - 1
    out = [[bg] * W for _ in range(H)]
    out[lr] = list(g[lr])
    for i, j in cells:
        ii = i + shift
        if 0 <= ii < H:
            out[ii][j] = g[i][j]
    if newc is not None and 0 <= nl < H:
        out[nl] = [newc] * W
    return out


def _make(newc, gap):
    def fn(g):
        bg = _bg(g)
        r = _solve_rows(g, bg, newc, gap)
        if r is not None:
            return r
        r = _solve_rows(_T(g), bg, newc, gap)
        if r is not None:
            return _T(r)
        return [row[:] for row in g]
    return fn


def fam(train):
    newc = _new_colour(train)
    if newc is None:
        return
    for gap in (0, 1):
        fn = _make(newc, gap)
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
            yield ("slide_to_wall_gap%d" % gap, gap, fn)


FAMILIES = [fam]
