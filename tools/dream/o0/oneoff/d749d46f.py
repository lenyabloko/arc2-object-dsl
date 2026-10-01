CARD = "d749d46f"
READING = ("The solid rectangles hanging along the top edge are laid out twice in left-to-right order "
           "with one-cell gaps: along the top edge each rotated to lie flat (width >= height), and "
           "along the bottom edge each rotated to stand upright (height >= width); output width is "
           "the flat row's length and output height is a constant induced from training.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rects(g, bg):
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
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            out.append((c0, r0, r1 - r0 + 1, c1 - c0 + 1, col))
    out.sort()
    return out


def _make(OH, gap):
    def fn(g):
        bg = _bg(g)
        rs = _rects(g, bg)
        flat = [(min(h, w), max(h, w), col) for _, _, h, w, col in rs]
        width = sum(w for _, w, _ in flat) + gap * max(0, len(flat) - 1)
        width = max(width, 1)
        out = [[bg] * width for _ in range(OH)]
        c = 0
        for h, w, col in flat:  # top row: lying flat
            for i in range(h):
                for j in range(w):
                    if i < OH and c + j < width:
                        out[i][c + j] = col
            c += w + gap
        c = 0
        for h, w, col in flat:  # bottom row: standing upright (h<->w swapped)
            hh, ww = w, h
            for i in range(hh):
                for j in range(ww):
                    r = OH - 1 - i
                    if r >= 0 and c + j < width:
                        out[r][c + j] = col
            c += ww + gap
        return out
    return fn


def fam(train):
    hs = {len(p["output"]) for p in train}
    if len(hs) != 1:
        return
    OH = hs.pop()
    for gap in (1, 0, 2):
        fn = _make(OH, gap)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("flat_top_upright_bottom_gap%d" % gap, 1 + gap, fn)
            return


FAMILIES = [fam]
