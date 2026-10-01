CARD = "1acc24af"
READING = ("A loose piece is recoloured when some rotation of it can be pushed into one of the "
           "pockets that open toward it in the fixed wall shape and fill that pocket exactly "
           "without overlapping the wall; pieces that fit no pocket keep their colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rot(g):
    return [list(r) for r in zip(*g[::-1])]


def _rotk(g, k):
    for _ in range(k % 4):
        g = _rot(g)
    return g


def _comps(cellset):
    cellset = set(cellset)
    out = []
    while cellset:
        s = cellset.pop()
        st = [s]
        comp = [s]
        while st:
            a, b = st.pop()
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (a + da, b + db)
                if q in cellset:
                    cellset.remove(q)
                    comp.append(q)
                    st.append(q)
        out.append(comp)
    return out


def _norm(cells):
    r0 = min(a for a, b in cells)
    c0 = min(b for a, b in cells)
    return sorted((a - r0, b - c0) for a, b in cells)


def _orients(cells, mirror):
    shapes = []
    cur = _norm(cells)
    bases = [cur]
    if mirror:
        bases.append(_norm([(a, -b) for a, b in cur]))
    for base in bases:
        s = base
        for _ in range(4):
            if s not in shapes:
                shapes.append(s)
            s = _norm([(b, -a) for a, b in s])
    return shapes


def _canon(g, bg, wall, piece, new, mirror):
    # canonical orientation: wall above, pieces below; pockets open downward
    H, W = len(g), len(g[0])
    wcells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == wall]
    if not wcells:
        return [list(r) for r in g]
    wr0 = min(a for a, b in wcells)
    wr1 = max(a for a, b in wcells)
    wset = set(wcells)
    zeros = [(i, j) for i in range(wr0, wr1 + 1) for j in range(W) if g[i][j] != wall]
    pockets = [c for c in _comps(zeros) if not any(a == wr0 for a, b in c)
               and any(a == wr1 for a, b in c)]
    pcells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == piece]
    out = [list(r) for r in g]
    for comp in _comps(pcells):
        ok = False
        for shp in _orients(comp, mirror):
            for pk in pockets:
                # anchor: align some piece cell with the pocket's first cell
                pa = min(pk)
                pkset = set(pk)
                for (sa, sb) in shp:
                    dr, dc = pa[0] - sa, pa[1] - sb
                    placed = [(a + dr, b + dc) for a, b in shp]
                    if any(not (0 <= x < H and 0 <= y < W) for x, y in placed):
                        continue
                    ps = set(placed)
                    if ps & wset:
                        continue
                    if not pkset <= ps:
                        continue
                    ok = True
                    break
                if ok:
                    break
            if ok:
                break
        if ok:
            for a, b in comp:
                out[a][b] = new
    return out


def _make(k, wall, piece, new, mirror):
    def fn(g):
        bg = _bg(g)
        h = _rotk(g, k)
        h = _canon(h, bg, wall, piece, new, mirror)
        return _rotk(h, 4 - k)
    return fn


def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    # induce piece colour -> new colour from changed cells; wall = other non-background colour
    maps = set()
    for p in train:
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    maps.add((a, b))
    if len(maps) != 1:
        return
    piece, new = maps.pop()
    bg = _bg(train[0]["input"])
    cols = set()
    for p in train:
        for r in p["input"]:
            cols.update(r)
    walls = sorted(c for c in cols if c not in (bg, piece))
    n = 0
    for mirror in (False, True):
        for k in range(4):
            for wall in walls:
                fn = _make(k, wall, piece, new, mirror)
                if _fits(fn, train):
                    yield ("pocket_fit_rot%d_mirror%d" % (k, mirror), k + 2 * mirror, fn)
                    n += 1
                    if n >= 3:
                        return


FAMILIES = [fam]
