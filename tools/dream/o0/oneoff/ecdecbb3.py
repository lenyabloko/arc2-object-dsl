CARD = "ecdecbb3"
READING = ("Each isolated dot shoots a ray of its colour toward the nearest full line in every direction "
           "where one exists, and where the ray meets the line a 3x3 block of the line colour is drawn "
           "with the dot colour at its centre.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _lines(g, bg):
    H, W = len(g), len(g[0])
    rows, cols = {}, {}
    for i in range(H):
        if g[i][0] != bg and all(g[i][j] == g[i][0] for j in range(W)):
            rows[i] = g[i][0]
    for j in range(W):
        if g[0][j] != bg and all(g[i][j] == g[0][j] for i in range(H)):
            cols[j] = g[0][j]
    return rows, cols


def _make(rad):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        rows, cols = _lines(g, bg)
        out = [r[:] for r in g]
        dots = []
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg and i not in rows and j not in cols:
                    dots.append((i, j, g[i][j]))
        boxes = []
        for i, j, c in dots:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                path = []
                hit = None
                while 0 <= a < H and 0 <= b < W:
                    if (di != 0 and a in rows) or (dj != 0 and b in cols):
                        hit = (a, b)
                        break
                    path.append((a, b))
                    a += di
                    b += dj
                if hit is None:
                    continue
                for a, b in path:
                    out[a][b] = c
                lc = rows[hit[0]] if di != 0 else cols[hit[1]]
                boxes.append((hit, lc, c))
        for (a, b), lc, c in boxes:
            for x in range(a - rad, a + rad + 1):
                for y in range(b - rad, b + rad + 1):
                    if 0 <= x < H and 0 <= y < W:
                        out[x][y] = lc
            out[a][b] = c
        return out
    return fn


def fam(train):
    for rad in (1, 0, 2):
        fn = _make(rad)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("ray_to_line_box_r%d" % rad, 1 + rad, fn)
        except Exception:
            pass


FAMILIES = [fam]
