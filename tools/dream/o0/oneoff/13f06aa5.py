CARD = "13f06aa5"
READING = "Each arrow-shaped object points toward the side where its single odd-coloured cell sits; from that cell shoot a dotted line of its colour (every other cell) to the grid edge, paint that whole edge row/column in that colour, and blank the corners where two painted edges meet."

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            comps.append(comp)
    return comps


def _rays(g):
    """Return list of (special_row, special_col, colour, dy, dx)."""
    bg = _bg(g)
    out = []
    for comp in _components(g, bg):
        cnt = Counter(g[y][x] for y, x in comp)
        if len(cnt) < 2:
            continue
        col, n = min(cnt.items(), key=lambda kv: (kv[1], kv[0]))
        if n != 1:
            continue
        sy, sx = [(y, x) for y, x in comp if g[y][x] == col][0]
        my = sum(y for y, _ in comp) / len(comp)
        mx = sum(x for _, x in comp) / len(comp)
        dy, dx = sy - my, sx - mx
        if abs(dy) > abs(dx):
            d = (1 if dy > 0 else -1, 0)
        elif abs(dx) > abs(dy):
            d = (0, 1 if dx > 0 else -1)
        else:
            continue
        out.append((sy, sx, col, d[0], d[1]))
    return out


def _make(step, corner):
    def fn(g):
        H, W = len(g), len(g[0])
        o = [row[:] for row in g]
        rays = _rays(g)
        edges = []  # (kind, index, colour)
        for sy, sx, col, dy, dx in rays:
            y, x = sy + step * dy, sx + step * dx
            while 0 <= y < H and 0 <= x < W:
                o[y][x] = col
                y += step * dy
                x += step * dx
            if dy:
                edges.append(("row", H - 1 if dy > 0 else 0, col))
            else:
                edges.append(("col", W - 1 if dx > 0 else 0, col))
        for kind, i, col in edges:
            if kind == "row":
                for x in range(W):
                    o[i][x] = col
            else:
                for y in range(H):
                    o[y][i] = col
        rows = [i for k, i, _ in edges if k == "row"]
        cols = [i for k, i, _ in edges if k == "col"]
        for r in rows:
            for c in cols:
                o[r][c] = corner
        return o
    return fn


def _corner_colours(train):
    cs = set()
    for p in train:
        g, out = p["input"], p["output"]
        H, W = len(g), len(g[0])
        rays = _rays(g)
        rows = [(H - 1 if dy > 0 else 0) for _, _, _, dy, dx in rays if dy]
        cols = [(W - 1 if dx > 0 else 0) for _, _, _, dy, dx in rays if dx]
        for r in rows:
            for c in cols:
                cs.add(out[r][c])
    return sorted(cs) if cs else [0]


def fam(train):
    for corner in _corner_colours(train):
        for step, cost in ((2, 1), (1, 2), (3, 3)):
            fn = _make(step, corner)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("arrow_dotted_ray_edge_s%d_c%d" % (step, corner), cost, fn)
            except Exception:
                pass


FAMILIES = [fam]
