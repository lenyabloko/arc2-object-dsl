CARD = "0d87d2a6"
READING = "Matching marker pixels on opposite borders are joined by a straight line of their colour, and every block of the other colour that the line crosses is recoloured to the line colour."


def _lines(g):
    H, W = len(g), len(g[0])
    lines = []  # (colour, set of cells)
    for c in range(W):
        if g[0][c] != 0 and g[0][c] == g[H - 1][c]:
            lines.append((g[0][c], {(r, c) for r in range(H)}))
    for r in range(H):
        if g[r][0] != 0 and g[r][0] == g[r][W - 1]:
            lines.append((g[r][0], {(r, c) for c in range(W)}))
    return lines


def _marker_colours(g, lines):
    # a marker colour is one whose every cell lies on a border endpoint of some line
    H, W = len(g), len(g[0])
    ends = set()
    for col, cells in lines:
        for (r, c) in cells:
            if r in (0, H - 1) or c in (0, W - 1):
                if g[r][c] == col:
                    ends.add((r, c))
    res = set()
    for col in {l[0] for l in lines}:
        allc = {(r, c) for r in range(H) for c in range(W) if g[r][c] == col}
        if allc and allc <= ends:
            res.add(col)
    return res


def _make(conn8):
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    def fn(g):
        H, W = len(g), len(g[0])
        lines = _lines(g)
        mk = _marker_colours(g, lines)
        lines = [l for l in lines if l[0] in mk]
        out = [row[:] for row in g]
        seen = [[False] * W for _ in range(H)]
        comp_id = [[-1] * W for _ in range(H)]
        comps = []
        for r in range(H):
            for c in range(W):
                if g[r][c] != 0 and g[r][c] not in mk and comp_id[r][c] < 0:
                    col = g[r][c]
                    st = [(r, c)]
                    comp_id[r][c] = len(comps)
                    cur = []
                    while st:
                        y, x = st.pop()
                        cur.append((y, x))
                        for dy, dx in nb:
                            yy, xx = y + dy, x + dx
                            if 0 <= yy < H and 0 <= xx < W and comp_id[yy][xx] < 0 and g[yy][xx] == col:
                                comp_id[yy][xx] = len(comps)
                                st.append((yy, xx))
                    comps.append(cur)
        for col, cells in lines:
            hit = set()
            for (r, c) in cells:
                out[r][c] = col
                if comp_id[r][c] >= 0:
                    hit.add(comp_id[r][c])
            for i in hit:
                for (r, c) in comps[i]:
                    out[r][c] = col
        return out
    return fn


def fam(train):
    for name, cost, c8 in (("border_line_recolour_hit_blocks4", 1, False),
                           ("border_line_recolour_hit_blocks8", 2, True)):
        fn = _make(c8)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
