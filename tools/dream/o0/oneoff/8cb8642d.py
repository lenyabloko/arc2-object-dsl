CARD = "8cb8642d"
READING = ("Each solid rectangle holding one odd-coloured cell keeps its border, its interior is "
           "cleared, and the odd colour draws the corner diagonals of every concentric inner ring "
           "(an innermost ring that is a single line is drawn fully), forming an X / envelope.")


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
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _apply(g):
    bg = _bg(g)
    out = [row[:] for row in g]
    for cells in _comps(g, bg):
        cnt = {}
        for a, b in cells:
            cnt[g[a][b]] = cnt.get(g[a][b], 0) + 1
        if len(cnt) < 2:
            continue
        odd = min(cnt, key=lambda k: cnt[k])
        R0 = min(a for a, _ in cells); R1 = max(a for a, _ in cells)
        C0 = min(b for _, b in cells); C1 = max(b for _, b in cells)
        r0, r1, c0, c1 = R0 + 1, R1 - 1, C0 + 1, C1 - 1
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if h < 1 or w < 1:
            continue
        K = min((h - 1) // 2, (w - 1) // 2)
        hk, wk = h - 2 * K, w - 2 * K
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                a = min(r - r0, r1 - r)
                b = min(c - c0, c1 - c)
                k = min(a, b)
                on = (a == b) or (k == K and (hk == 1 or wk == 1))
                out[r][c] = odd if on else bg
    return out


def fam(train):
    try:
        if all(_apply(p["input"]) == p["output"] for p in train):
            yield ("rect_ring_diagonals", 1.0, _apply)
    except Exception:
        return


FAMILIES = [fam]
