CARD = "de1cd16c"
READING = ("The grid is divided into coloured regions sprinkled with single noise cells; the output is a 1x1 grid "
           "of the colour of the region holding the most noise cells.")


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for i in range(H):
        for j in range(W):
            if (i, j) in seen or not pred(g[i][j]):
                continue
            col = g[i][j]
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            out.append((col, cells))
    return out


def _noise(g):
    singles = {}
    for col, cells in _comps(g, lambda v: True):
        if len(cells) == 1:
            singles[col] = singles.get(col, 0) + 1
    if not singles:
        return None
    return max(sorted(singles), key=lambda k: singles[k])


def _region_of(g, r, c, nz):
    H, W = len(g), len(g[0])
    cnt = {}
    for d in range(1, max(H, W)):
        for x, y in ((r + d, c), (r - d, c), (r, c + d), (r, c - d)):
            if 0 <= x < H and 0 <= y < W and g[x][y] != nz:
                cnt[(x, y)] = g[x][y]
        if cnt:
            break
    return cnt


def _make(per_component):
    def fn(g):
        H, W = len(g), len(g[0])
        nz = _noise(g)
        # fill noise cells with the majority colour of nearest neighbours to get clean regions
        clean = [row[:] for row in g]
        for r in range(H):
            for c in range(W):
                if g[r][c] == nz:
                    nb = _region_of(g, r, c, nz)
                    vs = {}
                    for v in nb.values():
                        vs[v] = vs.get(v, 0) + 1
                    clean[r][c] = max(sorted(vs), key=lambda k: vs[k]) if vs else g[r][c]
        if per_component:
            best = None
            for col, cells in _comps(clean, lambda v: True):
                k = sum(1 for a, b in cells if g[a][b] == nz)
                if best is None or k > best[0]:
                    best = (k, col)
            return [[best[1]]]
        cnt = {}
        for r in range(H):
            for c in range(W):
                if g[r][c] == nz:
                    cnt[clean[r][c]] = cnt.get(clean[r][c], 0) + 1
        return [[max(sorted(cnt), key=lambda k: cnt[k])]]
    return fn


def fam(train):
    cands = [("most_noise_region_component", 0, _make(True)),
             ("most_noise_region_colour", 1, _make(False))]
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
