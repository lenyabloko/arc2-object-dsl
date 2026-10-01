CARD = "df978a02"
READING = ("Several arrow-shaped objects point at a common centre; every object except the largest loses "
           "its tip cell(s), and the largest grows by the same number of cells as a centred segment "
           "added just behind its back edge.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _objects(g, bg, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    objs = []
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
            objs.append((col, cells))
    return objs


def _make(diag, winner):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        objs = _objects(g, bg, diag)
        if len(objs) < 2:
            return [row[:] for row in g]
        cents = [(sum(a for a, b in c) / len(c), sum(b for a, b in c) / len(c)) for _, c in objs]
        mr = sum(c[0] for c in cents) / len(cents)
        mc = sum(c[1] for c in cents) / len(cents)
        if winner == "largest":
            wi = max(range(len(objs)), key=lambda i: len(objs[i][1]))
        else:
            wi = min(range(len(objs)), key=lambda i: len(objs[i][1]))
        out = [row[:] for row in g]
        removed = 0
        dirs = []
        for i, (col, cells) in enumerate(objs):
            dr = mr - cents[i][0]
            dc = mc - cents[i][1]
            if abs(dr) >= abs(dc):
                d = (1 if dr > 0 else -1, 0)
            else:
                d = (0, 1 if dc > 0 else -1)
            dirs.append(d)
            if i == wi:
                continue
            key = [a * d[0] + b * d[1] for a, b in cells]
            m = max(key)
            for (a, b), k in zip(cells, key):
                if k == m:
                    out[a][b] = bg
                    removed += 1
        col, cells = objs[wi]
        d = dirs[wi]
        key = [a * d[0] + b * d[1] for a, b in cells]
        back = min(key)
        if d[0] != 0:
            # vertical arrow: back row, centred on column span
            c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
            row = (min(a for a, b in cells) - 1) if d[0] > 0 else (max(a for a, b in cells) + 1)
            mid2 = c0 + c1
            start = (mid2 - (removed - 1)) // 2
            for b in range(start, start + removed):
                if 0 <= row < H and 0 <= b < W:
                    out[row][b] = col
        else:
            r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
            cc = (min(b for a, b in cells) - 1) if d[1] > 0 else (max(b for a, b in cells) + 1)
            mid2 = r0 + r1
            start = (mid2 - (removed - 1)) // 2
            for a in range(start, start + removed):
                if 0 <= a < H and 0 <= cc < W:
                    out[a][cc] = col
        return out
    return fn


def fam(train):
    cands = []
    for diag in (True, False):
        for winner in ("largest", "smallest"):
            cost = (0 if diag else 1) + (0 if winner == "largest" else 2)
            cands.append(("arrows_tip_to_%s_diag%d" % (winner, diag), cost, _make(diag, winner)))
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
