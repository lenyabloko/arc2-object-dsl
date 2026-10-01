CARD = "d931c21c"
READING = ("Every closed loop (a connected shape that fully encloses some background) gets a ring "
           "of one colour on the background cells touching it from outside and a ring of another "
           "colour on the enclosed cells touching it from inside; open shapes are left unchanged.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _comps(g, bg, nb):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            out.append(set(cells))
    return out


def _make(ocol, icol, adj, conn):
    nbadj = N8 if adj == 8 else N4
    nbconn = N8 if conn == 8 else N4

    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        for comp in _comps(g, bg, nbconn):
            # flood the outside (4-connected) treating only this component as wall
            outside = [[False] * W for _ in range(H)]
            st = []
            for i in range(H):
                for j in range(W):
                    if (i in (0, H - 1) or j in (0, W - 1)) and (i, j) not in comp:
                        outside[i][j] = True
                        st.append((i, j))
            while st:
                a, b = st.pop()
                for da, db in N4:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not outside[x][y] and (x, y) not in comp:
                        outside[x][y] = True
                        st.append((x, y))
            inside = [(i, j) for i in range(H) for j in range(W)
                      if not outside[i][j] and (i, j) not in comp]
            if not inside:
                continue
            for a, b in comp:
                for da, db in nbadj:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and g[x][y] == bg and (x, y) not in comp:
                        out[x][y] = ocol if outside[x][y] else icol
        return out
    return fn


def fam(train):
    news = {}
    for p in train:
        for r1, r2 in zip(p["input"], p["output"]):
            for x, y in zip(r1, r2):
                if x != y:
                    news[y] = news.get(y, 0) + 1
    cols = sorted(news)
    pairs = [(a, b) for a in cols for b in cols if a != b] or [(a, a) for a in cols]
    near = []
    for adj in (8, 4):
        for conn in (8, 4):
            for ocol, icol in pairs:
                fn = _make(ocol, icol, adj, conn)
                miss = 0
                for p in train:
                    o = fn(p["input"])
                    miss += sum(1 for r1, r2 in zip(o, p["output"]) for x, y in zip(r1, r2) if x != y)
                name = "loop_halo_out%d_in%d_adj%d_conn%d" % (ocol, icol, adj, conn)
                if miss == 0:
                    yield (name, 1, fn)
                    return
                near.append((miss, name, fn))
    # training data hold a one-cell anomaly; fall back to the best near fit
    near.sort(key=lambda t: t[0])
    if near and near[0][0] <= 2:
        yield (near[0][1] + "_near", 5, near[0][2])


FAMILIES = [fam]
