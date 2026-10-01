CARD = "85fa5666"
READING = ("Each solid block has four single-cell colours at its diagonal corners; the four corner "
           "colours rotate one step around the block and then each shoots a diagonal ray outward "
           "from its corner until it hits the grid edge or an existing object.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or (i, j) in seen:
                continue
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            out.append(cells)
    return out


def _blocks(g, bg):
    H, W = len(g), len(g[0])
    colors = sorted(set(x for r in g for x in r) - {bg})
    for col in colors:
        res = []
        good = True
        for cells in _comps(g, col):
            r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
            c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
            if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1) or len(cells) < 2:
                good = False
                break
            # corners TL, TR, BR, BL (clockwise order)
            cs = [(r0 - 1, c0 - 1, -1, -1), (r0 - 1, c1 + 1, -1, 1),
                  (r1 + 1, c1 + 1, 1, 1), (r1 + 1, c0 - 1, 1, -1)]
            vals = []
            for (a, b, da, db) in cs:
                if 0 <= a < H and 0 <= b < W and g[a][b] != bg and g[a][b] != col:
                    vals.append(g[a][b])
                else:
                    vals.append(None)
            if any(v is None for v in vals):
                good = False
                break
            res.append((cs, vals))
        if good and res:
            return res
    return None


def _make(k, stop, block_mode=None):
    # block_mode: None, or a block-ordering key ("col"/"row"); with it, a ray may not cross the
    # corner diagonal (block cell -> corner marker) of an earlier-ordered block whose rotated
    # corner colour equals the ray colour.
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        bl = _blocks(g, bg)
        if bl is None:
            return None
        if block_mode == "col":
            bl = sorted(bl, key=lambda t: (t[0][0][1], t[0][0][0]))
        elif block_mode == "row":
            bl = sorted(bl, key=lambda t: (t[0][0][0], t[0][0][1]))
        out = [list(r) for r in g]
        diag = []  # per block: {midpoint: colour}
        for cs, vals in bl:
            dm = {}
            for idx, (a, b, da, db) in enumerate(cs):
                v = vals[(idx - k) % 4]
                dm[(2 * a - da, 2 * b - db)] = v  # doubled midpoint of block cell -> corner
            diag.append(dm)
        for bi, (cs, vals) in enumerate(bl):
            for idx, (a, b, da, db) in enumerate(cs):
                v = vals[(idx - k) % 4]
                out[a][b] = v
                x, y = a + da, b + db
                while 0 <= x < H and 0 <= y < W:
                    if block_mode is not None:
                        mid = (2 * x - da, 2 * y - db)
                        if any(diag[j].get(mid) == v for j in range(bi)):
                            break
                    if g[x][y] != bg:
                        if stop:
                            break
                    else:
                        out[x][y] = v
                    x += da
                    y += db
        return out
    return fn


def fam(train):
    cands = []
    for k, ck in ((1, 0), (3, 1), (2, 2), (0, 3)):
        for stop, cs in ((True, 0), (False, 1)):
            cands.append(("block_corner_rot%d_rays_%s" % (k, "stop" if stop else "skip"),
                          ck + cs, _make(k, stop)))
            for bm, bc in (("col", 4), ("row", 4)):
                cands.append(("block_corner_rot%d_rays_%s_samecol_diag_%s" % (k, "stop" if stop else "skip", bm),
                              ck + cs + bc, _make(k, stop, bm)))
    cands.sort(key=lambda t: t[1])
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
