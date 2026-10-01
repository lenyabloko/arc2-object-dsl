CARD = "9aec4887"
READING = ("Four coloured bars frame an empty square and a separate shape of the same size lies "
           "elsewhere; crop the frame, drop the shape inside it, and recolour each shape cell with "
           "the colour of the uniquely nearest bar (cells equidistant from two bars keep their colour).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(tie_keep):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        cells = {}
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg:
                    cells.setdefault(g[i][j], []).append((i, j))
        hbars, vbars, rest = [], [], []
        for c, cs in cells.items():
            rows = set(a for a, _ in cs)
            cols = set(b for _, b in cs)
            if len(rows) == 1 and len(cs) > 1 and max(cols) - min(cols) + 1 == len(cs):
                hbars.append((min(rows), min(cols), max(cols), c))
            elif len(cols) == 1 and len(cs) > 1 and max(rows) - min(rows) + 1 == len(cs):
                vbars.append((min(cols), min(rows), max(rows), c))
            else:
                rest.append(c)
        if len(hbars) != 2 or len(vbars) != 2 or len(rest) != 1:
            raise ValueError("no frame")
        hbars.sort()
        vbars.sort()
        top, bot = hbars
        lef, rig = vbars
        r0, r1 = top[0], bot[0]
        c0, c1 = lef[0], rig[0]
        n = r1 - r0 - 1
        m = c1 - c0 - 1
        sc = rest[0]
        sh = cells[sc]
        sr = min(a for a, _ in sh)
        scc = min(b for _, b in sh)
        out = [[g[r0 + i][c0 + j] for j in range(m + 2)] for i in range(n + 2)]
        for a, b in sh:
            i, j = a - sr, b - scc
            if not (0 <= i < n and 0 <= j < m):
                continue
            ds = [(i, top[3]), (n - 1 - i, bot[3]), (j, lef[3]), (m - 1 - j, rig[3])]
            dmin = min(d for d, _ in ds)
            win = [c for d, c in ds if d == dmin]
            if len(win) == 1:
                col = win[0]
            else:
                col = sc if tie_keep else win[0]
            out[i + 1][j + 1] = col
        return out
    return fn


def fam(train):
    for tk in (True, False):
        fn = _make(tk)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("frame_fill_nearest_bar", 1 + int(not tk), fn)
        except Exception:
            pass


FAMILIES = [fam]
