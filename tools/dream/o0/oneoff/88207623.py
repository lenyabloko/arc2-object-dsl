CARD = "88207623"
READING = ("Each shape attached to a straight axis line is mirrored across that line, and the mirror "
           "image is painted in the colour of the lone marker cell lying on the other side.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(cells, diag):
    cells = set(cells)
    seen = set()
    out = []
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for c in sorted(cells):
        if c in seen:
            continue
        st = [c]
        seen.add(c)
        comp = []
        while st:
            a, b = st.pop()
            comp.append((a, b))
            for da, db in nb:
                q = (a + da, b + db)
                if q in cells and q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(comp)
    return out


def _lines(g, bg, col):
    H, W = len(g), len(g[0])
    cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == col]
    res = []
    for comp in _comps(cells, False):
        rs = set(a for a, b in comp)
        cs = set(b for a, b in comp)
        if len(comp) < 2:
            return None
        if len(cs) == 1:
            res.append(("v", comp))
        elif len(rs) == 1:
            res.append(("h", comp))
        else:
            return None
    return res


def _solve(g):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    colors = sorted(set(x for r in g for x in r) - {bg})
    for axc in colors:
        lines = _lines(g, bg, axc)
        if not lines:
            continue
        # shape colour = non-axis colour touching the axis lines
        touch = {}
        for kind, comp in lines:
            for a, b in comp:
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and g[x][y] not in (bg, axc):
                            touch[g[x][y]] = touch.get(g[x][y], 0) + 1
        if not touch:
            continue
        shc = max(touch, key=lambda k: (touch[k], -k))
        shape_cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == shc]
        scomps = _comps(shape_cells, True)
        markers = [(i, j) for i in range(H) for j in range(W) if g[i][j] not in (bg, axc, shc)]
        out = [list(r) for r in g]
        for kind, comp in lines:
            cset = set(comp)
            mine = []
            for sc in scomps:
                if any((a + da, b + db) in cset for a, b in sc for da in (-1, 0, 1) for db in (-1, 0, 1)):
                    mine.extend(sc)
            if not mine:
                continue
            if kind == "v":
                x = comp[0][1]
                mirror = [(a, 2 * x - b) for a, b in mine]
            else:
                y = comp[0][0]
                mirror = [(2 * y - a, b) for a, b in mine]
            mset = set(mirror)
            mk = [m for m in markers if m in mset]
            if not mk:
                continue
            mc = g[mk[0][0]][mk[0][1]]
            for a, b in mirror:
                if 0 <= a < H and 0 <= b < W and out[a][b] == bg:
                    out[a][b] = mc
        return out
    return None


def fam(train):
    fn = _solve
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return
        except Exception:
            return
    yield ("mirror_shape_across_axis_marker_colour", 1, fn)


FAMILIES = [fam]
