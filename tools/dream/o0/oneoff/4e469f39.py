CARD = "4e469f39"
READING = ("Each cup with a one-cell gap in its top wall is filled with the new colour, and from the gap a "
           "line of that colour runs along the row just above the cup to the grid edge, heading over the "
           "longer part of the top wall.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = set()
    objs = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or (i, j) in seen:
                continue
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] != bg:
                            seen.add((x, y))
                            st.append((x, y))
            objs.append(cells)
    return objs


def _fill_colour(train):
    fc = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        new = set(x for r in p["output"] for x in r) - ins
        if len(new) != 1:
            return None
        c = next(iter(new))
        if fc is None:
            fc = c
        elif fc != c:
            return None
    return fc


def _make(fc, longer):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [list(r) for r in g]
        for cells in _comps(g, bg):
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            gaps = [c for c in range(c0, c1 + 1) if g[r0][c] == bg]
            if len(gaps) != 1:
                return None
            gc = gaps[0]
            for i in range(r0, r1 + 1):
                for j in range(c0, c1 + 1):
                    if g[i][j] == bg:
                        out[i][j] = fc
            if r0 - 1 < 0:
                continue
            go_right = (c1 - gc) > (gc - c0)
            if not longer:
                go_right = not go_right
            rng = range(gc, W) if go_right else range(gc, -1, -1)
            for j in rng:
                if out[r0 - 1][j] == bg:
                    out[r0 - 1][j] = fc
        return out
    return fn


def fam(train):
    fc = _fill_colour(train)
    if fc is None:
        return
    for longer in (True, False):
        fn = _make(fc, longer)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("cup_fill_spout_%s" % ("long" if longer else "short"), 1 + (not longer), fn)


FAMILIES = [fam]
