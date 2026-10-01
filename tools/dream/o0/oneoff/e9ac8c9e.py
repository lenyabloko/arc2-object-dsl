CARD = "e9ac8c9e"
READING = ("Each solid block is split into four equal quadrants coloured by the four single "
           "pixels sitting diagonally off its corners (each quadrant takes its nearest corner "
           "pixel), and everything else is erased.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
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
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            out.append((col, cells))
    return out


def _make(block_col):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [[bg] * W for _ in range(H)]
        for col, cells in _comps(g, bg):
            if col != block_col or len(cells) < 2:
                continue
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1):
                continue

            def px(r, c):
                if 0 <= r < H and 0 <= c < W:
                    return g[r][c]
                return bg
            corners = {(0, 0): px(r0 - 1, c0 - 1), (0, 1): px(r0 - 1, c1 + 1),
                       (1, 0): px(r1 + 1, c0 - 1), (1, 1): px(r1 + 1, c1 + 1)}
            h = r1 - r0 + 1
            w = c1 - c0 + 1
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    vr = 0 if (r - r0) < h // 2 else 1
                    vc = 0 if (c - c0) < w // 2 else 1
                    out[r][c] = corners[(vr, vc)]
        return out
    return fn


def fam(train):
    # block colour: present in every input, absent from every output
    cand = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        outs = set(x for r in p["output"] for x in r)
        s = ins - outs
        cand = s if cand is None else cand & s
    for bc in sorted(cand or []):
        fn = _make(bc)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("quadrant_corner_fill_c%d" % bc, 1.0, fn)
        except Exception:
            pass


FAMILIES = [fam]
