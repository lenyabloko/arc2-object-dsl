CARD = "9720b24f"
READING = ("Delete every small object that lies entirely inside the bounding box of an "
           "object of a different colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            rs = [c[0] for c in cells]
            cs = [c[1] for c in cells]
            out.append((col, cells, (min(rs), min(cs), max(rs), max(cs))))
    return out


def _make(diag, strict, bgc=None):
    def fn(g):
        bg = _bg(g) if bgc is None else bgc
        comps = _comps(g, bg, diag)
        out = [r[:] for r in g]
        for col, cells, (r0, c0, r1, c1) in comps:
            for col2, cells2, (R0, C0, R1, C1) in comps:
                if col2 == col or len(cells2) <= len(cells):
                    continue
                if strict:
                    inside = R0 < r0 and r1 < R1 and C0 < c0 and c1 < C1
                else:
                    inside = R0 <= r0 and r1 <= R1 and C0 <= c0 and c1 <= C1
                if inside:
                    for a, b in cells:
                        out[a][b] = bg
                    break
        return out
    return fn


def fam(train):
    # background: the colour most common over all training inputs (pooled)
    pooled = {}
    for p in train:
        for r in p["input"]:
            for x in r:
                pooled[x] = pooled.get(x, 0) + 1
    bgc = max(pooled, key=lambda k: pooled[k])
    cands = []
    for bname, b, bc in (("pooledbg", bgc, 0), ("gridbg", None, 1)):
        cands += [("drop_inside_bbox_8conn_" + bname, 1 + bc, _make(True, False, b)),
                  ("drop_inside_bbox_8conn_strict_" + bname, 2 + bc, _make(True, True, b)),
                  ("drop_inside_bbox_4conn_" + bname, 3 + bc, _make(False, False, b))]
    cands.sort(key=lambda t: t[1])
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


FAMILIES = [fam]
