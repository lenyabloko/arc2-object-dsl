CARD = "b457fec5"
READING = ("Each diagonal band is recoloured, from its top corner onward, as a chain of nested L-shapes "
           "(arms as long as the band's top width) cycling through the key colours read left to right, "
           "and the leftover tail after the last complete L takes that L's colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    res = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or (i, j) in seen:
                continue
            st = [(i, j)]
            seen.add((i, j))
            cells = set()
            while st:
                a, b = st.pop()
                cells.add((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            res.append(cells)
    return res


def _paint(cells, key):
    # cells normalised so the band runs down-right from its top-left corner
    top = min(r for r, _ in cells)
    toprow = sorted(c for r, c in cells if r == top)
    r0, c0 = top, toprow[0]
    T = len(toprow)
    col = {}
    last = None
    k = 0
    while True:
        L = [(r0 + k, c0 + k + j) for j in range(T)] + [(r0 + k + i, c0 + k) for i in range(1, T)]
        if not all(p in cells for p in L):
            break
        last = key[k % len(key)]
        for p in L:
            col[p] = last
        k += 1
    if last is None:
        return {}
    for p in cells:
        if p not in col:
            col[p] = last
    return col


def fn(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cnt = {}
    for r in g:
        for x in r:
            if x != bg:
                cnt[x] = cnt.get(x, 0) + 1
    if not cnt:
        return [row[:] for row in g]
    shape_col = max(cnt, key=lambda k: cnt[k])
    key = [g[i][j] for i in range(H) for j in range(W) if g[i][j] not in (bg, shape_col)]
    out = [row[:] for row in g]
    if not key:
        return out
    for cells in _comps(g, shape_col):
        top = min(r for r, _ in cells)
        bot = max(r for r, _ in cells)
        tmean = sum(c for r, c in cells if r == top) / float(sum(1 for r, c in cells if r == top))
        bmean = sum(c for r, c in cells if r == bot) / float(sum(1 for r, c in cells if r == bot))
        mirror = bmean < tmean
        norm = set((r, W - 1 - c) if mirror else (r, c) for r, c in cells)
        painted = _paint(norm, key)
        for (r, c), v in painted.items():
            if mirror:
                c = W - 1 - c
            out[r][c] = v
    return out


def fam(train):
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("band_nested_L_key_cycle", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
