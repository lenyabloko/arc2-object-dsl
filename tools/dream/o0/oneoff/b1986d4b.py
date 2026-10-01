CARD = "b1986d4b"
READING = ("Count the solid k-by-k squares of each colour (each colour has its own size) and draw a "
           "row of nested top-left-aligned square glyphs, glyph i holding every colour whose count "
           "exceeds i (the count capped at twice the smallest count), each glyph followed by a "
           "background gap and a background row below.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _squares(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    found = {}
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            ys = [c[0] for c in cells]
            xs = [c[1] for c in cells]
            h = max(ys) - min(ys) + 1
            w = max(xs) - min(xs) + 1
            if h == w and h >= 2 and len(cells) == h * w:
                found.setdefault(col, {}).setdefault(h, 0)
                found[col][h] += 1
    res = []
    for col, sizes in found.items():
        s = max(sizes, key=lambda k: (sizes[k], k))
        res.append((s, col, sizes[s]))
    res.sort(reverse=True)
    return res


def _caps(name):
    if name == "none":
        return lambda counts: counts
    if name == "twice_min":
        def f(counts):
            m = 2 * min(counts)
            return [min(c, m) for c in counts]
        return f
    if name == "twice_largest":
        def f(counts):
            m = 2 * counts[0]
            return [min(c, m) for c in counts]
        return f
    raise ValueError(name)


def _make(capname):
    cap = _caps(capname)

    def fn(g):
        bg = _bg(g)
        sq = _squares(g, bg)
        if not sq:
            return [[bg]]
        counts = cap([c for _, _, c in sq])
        n = max(counts)
        S = sq[0][0]
        glyphs = []
        for i in range(n):
            members = [(s, col) for (s, col, _), c in zip(sq, counts) if c > i]
            if not members:
                continue
            gs = members[0][0]
            gl = [[bg] * gs for _ in range(gs)]
            for s, col in members:
                for a in range(s):
                    for b in range(s):
                        gl[a][b] = col
            glyphs.append(gl)
        W = sum(len(gl) + 1 for gl in glyphs)
        out = [[bg] * W for _ in range(S + 1)]
        x = 0
        for gl in glyphs:
            for a in range(len(gl)):
                for b in range(len(gl)):
                    out[a][x + b] = gl[a][b]
            x += len(gl) + 1
        return out
    return fn


def fam(train):
    for i, capname in enumerate(("none", "twice_min", "twice_largest")):
        fn = _make(capname)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("square_count_glyphs_" + capname, 1 + i, fn)
        except Exception:
            pass


FAMILIES = [fam]
