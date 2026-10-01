CARD = "256b0a75"
READING = "Four L-shaped corners mark a rectangle; draw its border in the majority corner colour, fill its interior and the full-width/full-height bands through it with the odd corner's colour, and extend every dot lying in a band outward to the grid edge."


def _comps(g):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] and not seen[r][c]:
                col = g[r][c]
                st = [(r, c)]
                seen[r][c] = True
                cells = []
                while st:
                    y, x = st.pop()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                            seen[ny][nx] = True
                            st.append((ny, nx))
                out.append((col, cells))
    return out


def _corners(g):
    found = {}
    for col, cells in _comps(g):
        if len(cells) != 3:
            continue
        rs = [r for r, _ in cells]; cs = [c for _, c in cells]
        r0, c0 = min(rs), min(cs)
        if max(rs) - r0 != 1 or max(cs) - c0 != 1:
            continue
        box = {(r0, c0), (r0, c0 + 1), (r0 + 1, c0), (r0 + 1, c0 + 1)}
        miss = (box - set(cells)).pop()
        kind = ("B" if miss[0] == r0 else "T") + ("R" if miss[1] == c0 else "L")
        found.setdefault(kind, []).append((col, cells))
    if any(k not in found for k in ("TL", "TR", "BL", "BR")):
        return None
    return {k: found[k][0] for k in ("TL", "TR", "BL", "BR")}


def _solve(g):
    H, W = len(g), len(g[0])
    cor = _corners(g)
    out = [row[:] for row in g]
    if cor is None:
        return out
    allc = [p for k in cor for p in cor[k][1]]
    r0 = min(r for r, _ in allc); r1 = max(r for r, _ in allc)
    c0 = min(c for _, c in allc); c1 = max(c for _, c in allc)
    cols = [cor[k][0] for k in cor]
    cnt = {}
    for v in cols:
        cnt[v] = cnt.get(v, 0) + 1
    border = max(cnt, key=lambda v: cnt[v])
    odd = [v for v in cols if v != border]
    fill = odd[0] if odd else border
    corner_cells = set(allc)
    inrows = lambda r: r0 <= r <= r1
    incols = lambda c: c0 <= c <= c1
    for r in range(H):
        for c in range(W):
            if (inrows(r) or incols(c)) and g[r][c] == 0:
                out[r][c] = fill
    for c in range(c0, c1 + 1):
        out[r0][c] = border
        out[r1][c] = border
    for r in range(r0, r1 + 1):
        out[r][c0] = border
        out[r][c1] = border
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == 0 or (r, c) in corner_cells:
                continue
            if inrows(r) and not incols(c):
                d = (0, -1) if c < c0 else (0, 1)
            elif incols(c) and not inrows(r):
                d = (-1, 0) if r < r0 else (1, 0)
            else:
                continue
            y, x = r + d[0], c + d[1]
            while 0 <= y < H and 0 <= x < W and g[y][x] == 0:
                out[y][x] = v
                y += d[0]
                x += d[1]
    return out


def fam(train):
    try:
        if all(_solve(p["input"]) == p["output"] for p in train):
            yield ("corner_rect_bands_rays", 1, _solve)
    except Exception:
        pass


FAMILIES = [fam]
