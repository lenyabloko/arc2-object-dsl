CARD = "52fd389e"
READING = ("Each solid rectangle carries a few odd-coloured dots; it is surrounded by a frame of the "
           "dot colour whose thickness equals the number of dots.")


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
            out.append(cells)
    return out


def _make(diag, mult):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        for cells in _comps(g, bg, diag):
            cnt = {}
            for a, b in cells:
                cnt[g[a][b]] = cnt.get(g[a][b], 0) + 1
            if len(cnt) < 2:
                continue
            body = max(cnt, key=lambda k: (cnt[k], -k))
            minor = {k: v for k, v in cnt.items() if k != body}
            col = max(minor, key=lambda k: (minor[k], -k))
            n = sum(minor.values()) * mult
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            for a in range(max(0, r0 - n), min(H, r1 + n + 1)):
                for b in range(max(0, c0 - n), min(W, c1 + n + 1)):
                    if out[a][b] == bg:
                        out[a][b] = col
        return out
    return fn


def fam(train):
    cands = []
    for diag in (False, True):
        for mult in (1, 2):
            cands.append(("frame_dotcount_d%d_x%d" % (diag, mult), (mult - 1) * 2 + diag, _make(diag, mult)))
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
