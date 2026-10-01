CARD = "b548a754"
READING = ("The framed rectangle is stretched (border kept, interior extended) until it reaches the lone "
           "marker cell, which is then erased.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = set()
    res = []
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
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] != bg:
                        seen.add((x, y))
                        st.append((x, y))
            res.append(cells)
    return res


def _idx(j, old, new):
    half = old // 2
    if j < half:
        return j
    if j >= new - (old - half):
        return j - (new - old)
    return half


def fn(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    comps = _comps(g, bg)
    if len(comps) < 2:
        return [r[:] for r in g]
    comps.sort(key=len, reverse=True)
    box = comps[0]
    others = [c for cs in comps[1:] for c in cs]
    r0 = min(a for a, _ in box)
    r1 = max(a for a, _ in box)
    c0 = min(b for _, b in box)
    c1 = max(b for _, b in box)
    pat = [g[r][c0:c1 + 1] for r in range(r0, r1 + 1)]
    R0 = min([r0] + [a for a, _ in others])
    R1 = max([r1] + [a for a, _ in others])
    C0 = min([c0] + [b for _, b in others])
    C1 = max([c1] + [b for _, b in others])
    out = [r[:] for r in g]
    for a, b in others:
        out[a][b] = bg
    h, w = r1 - r0 + 1, c1 - c0 + 1
    NH, NW = R1 - R0 + 1, C1 - C0 + 1
    for i in range(NH):
        oi = _idx(i, h, NH)
        for j in range(NW):
            out[R0 + i][C0 + j] = pat[oi][_idx(j, w, NW)]
    return out


def fam(train):
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("stretch_box_to_marker", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
