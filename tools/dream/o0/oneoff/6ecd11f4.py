CARD = "6ecd11f4"
READING = ("A large single-colour shape is an up-scaled binary mask the size of the small multicoloured "
           "tile; the output is the tile with cells outside the mask set to zero.")


def _comps(g):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == 0 or seen[i][j]:
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != 0:
                            seen[x][y] = True
                            st.append((x, y))
            comps.append(cells)
    return comps


def _bbox(cells):
    return (min(a for a, b in cells), min(b for a, b in cells),
            max(a for a, b in cells), max(b for a, b in cells))


def fn(g):
    comps = _comps(g)
    tile = None
    shape = []
    for cells in comps:
        cols = set(g[a][b] for a, b in cells)
        r0, c0, r1, c1 = _bbox(cells)
        solid = len(cells) == (r1 - r0 + 1) * (c1 - c0 + 1)
        if len(cols) > 1 and solid:
            if tile is None or len(cells) < len(tile):
                tile = cells
        elif len(cols) == 1:
            shape.extend(cells)
    if tile is None or not shape:
        return None
    tr0, tc0, tr1, tc1 = _bbox(tile)
    h, w = tr1 - tr0 + 1, tc1 - tc0 + 1
    sr0, sc0, sr1, sc1 = _bbox(shape)
    SH, SW = sr1 - sr0 + 1, sc1 - sc0 + 1
    if SH % h or SW % w:
        return None
    bh, bw = SH // h, SW // w
    out = [[0] * w for _ in range(h)]
    for i in range(h):
        for j in range(w):
            if g[sr0 + i * bh + bh // 2][sc0 + j * bw + bw // 2] != 0:
                out[i][j] = g[tr0 + i][tc0 + j]
    return out


def fam(train):
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("tile_masked_by_downscaled_shape", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
