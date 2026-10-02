"""Line family for card f560132c (test-blind; induced only from train pairs).

Reading: one mono-coloured shape (the container) holds a small multi-colour rectangle (the
exemplar, k x m cells, one colour per cell; background cells allowed).  The container together
with the exemplar's box is one piece; every other mono-coloured shape is a fragment.  The container
stays as it is; the fragments are turned (rotated, or rotated/reflected) and attached so that all
pieces tile one solid rectangle of the exemplar's shape.  Pieces are matched one-to-one to the
exemplar's cells (piece centroid vs. the centre of that cell's block of the rectangle, optimal
match); each piece is painted its cell's exemplar colour; the rectangle is the output.  When several
tilings exist, the one whose pieces best match the exemplar layout wins (then the first found).
"""
from collections import Counter

CARD = "f560132c"
LINE = ("apply multi-color exemplar contained inside each mono-colored shape then complete the container "
        "shape by attaching fitting fragments oriented and colored the same way as  the exenplar's color "
        "fragments and forming the same shape as the exemplar")
READING = {
    "generator": "The container shape (with its exemplar box) and all loose mono-coloured fragments, turned as "
                 "needed, are fitted together into one solid rectangle shaped like the exemplar; each piece is "
                 "painted the exemplar colour of the exemplar cell it occupies, and that rectangle is the output.",
    "stop": "Stops when the rectangle is exactly covered: every piece used once, no overlap, no gap; pieces "
            "are matched one per exemplar cell (k*m pieces for a k x m exemplar); among several tilings the "
            "one closest to the exemplar layout is kept.",
    "params": "orientations ∈ {rotations (4), rotations+reflections (8)} · rectangle shape ∈ {proportional to "
              "the exemplar, any factorisation of the total area} · connectivity = 4 · container orientation = "
              "as given · piece-to-cell match = optimal centroid-to-block-centre",
    "participants": "Objects = 4-connected components of non-background cells (background = most frequent "
                    "colour).  The one multi-coloured object is container + exemplar: container colour = its "
                    "majority colour, exemplar = bounding box of its other-coloured cells; every mono-coloured "
                    "object is a fragment.",
    "preconditions": "Exactly one multi-coloured object; its exemplar box contains no container-colour cell; "
                     "#fragments + 1 = number of exemplar cells; total piece area factors into a rectangle that "
                     "the pieces tile exactly (container unturned); output = that rectangle.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
NODE_BUDGET = 60000      # deterministic search budget (placements tried) per grid, shared by all rectangles
MAX_TILINGS = 32


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _objects(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    objs = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in D4:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] != bg:
                        seen[p][q] = True
                        st.append((p, q))
            objs.append(sorted(pix))
    objs.sort()
    return objs


def _norm(cells):
    r0 = min(r for r, _ in cells); c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def _orients(cells, mode):
    out, seen = [], set()
    cur = list(cells)
    for refl in ((0, 1) if mode == "dih8" else (0,)):
        base = [(r, -c) for r, c in cur] if refl else cur
        for _ in range(4):
            n = _norm(base)
            if n not in seen:
                seen.add(n); out.append(n)
            base = [(c, -r) for r, c in base]
    return out


def _parse(g):
    """-> (exemplar k x m colour grid, container shape, [fragment shapes]) or None."""
    bg = _bg(g)
    objs = _objects(g, bg)
    multi = [o for o in objs if len({g[r][c] for r, c in o}) > 1]
    if len(multi) != 1:
        return None
    o = multi[0]
    cc = Counter(g[r][c] for r, c in o).most_common()
    if len(cc) > 1 and cc[0][1] == cc[1][1]:
        return None
    ccol = cc[0][0]
    ex = [(r, c) for r, c in o if g[r][c] != ccol]
    r0 = min(r for r, _ in ex); r1 = max(r for r, _ in ex)
    c0 = min(c for _, c in ex); c1 = max(c for _, c in ex)
    E = [[g[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    if any(v == ccol for row in E for v in row):
        return None
    k, m = len(E), len(E[0])
    if k * m < 2:
        return None
    cont = set(p for p in o if g[p[0]][p[1]] == ccol)
    cont |= {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
    frags = [o2 for o2 in objs if o2 is not o]
    if len(frags) + 1 != k * m:
        return None
    return E, _norm(cont), [_norm(f) for f in frags]


def _dims(area, k, m, aspect):
    fs = [(h, area // h) for h in range(1, area + 1) if area % h == 0 and h >= k and area // h >= m]
    if aspect == "prop":
        return [(h, w) for h, w in fs if h * m == w * k]
    return sorted(fs, key=lambda hw: (abs(hw[0] * m - hw[1] * k), hw[0]))


def _holes_ok(grid, H, W, mina):
    """Every empty 4-connected region must be able to hold the smallest remaining piece."""
    if mina <= 1:
        return True
    seen = [[False] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if grid[y][x] >= 0 or seen[y][x]:
                continue
            st = [(y, x)]; seen[y][x] = True; s = 0
            while st:
                a, b = st.pop(); s += 1
                for dy, dx in D4:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and grid[p][q] < 0:
                        seen[p][q] = True; st.append((p, q))
            if s < mina:
                return False
    return True


def _tilings(H, W, pieces, budget):
    """Exact covers of the H x W rectangle by all pieces (pieces[i] = its allowed orientations,
    normalised cell tuples).  Yields [[piece index]] grids, deterministically, within budget[0] placements."""
    n = len(pieces)
    grid = [[-1] * W for _ in range(H)]
    used = [False] * n
    areas = [len(ors[0]) for ors in pieces]

    def rec(start):
        idx = start
        while idx < H * W and grid[idx // W][idx % W] >= 0:
            idx += 1
        if idx == H * W:
            yield [row[:] for row in grid]
            return
        y, x = idx // W, idx % W
        for pi in range(n):
            if used[pi]:
                continue
            for o in pieces[pi]:
                budget[0] -= 1
                if budget[0] < 0:
                    return
                ar, ac = o[0]
                dy, dx = y - ar, x - ac
                cells = []
                for r, c in o:
                    rr, cc = r + dy, c + dx
                    if not (0 <= rr < H and 0 <= cc < W) or grid[rr][cc] >= 0:
                        cells = None; break
                    cells.append((rr, cc))
                if cells is None:
                    continue
                for rr, cc in cells:
                    grid[rr][cc] = pi
                used[pi] = True
                left = [areas[i] for i in range(n) if not used[i]]
                if not left or _holes_ok(grid, H, W, min(left)):
                    yield from rec(idx + 1)
                used[pi] = False
                for rr, cc in cells:
                    grid[rr][cc] = -1

    yield from rec(0)


def _assign(grid, n, k, m):
    """Optimal one-to-one match of pieces to exemplar cells: piece centroid vs. the centre of the
    exemplar cell's block in the rectangle, squared distance in exemplar-cell units (subset DP).
    Returns (cost, [cell of piece i])."""
    H, W = len(grid), len(grid[0])
    acc = [[0, 0, 0] for _ in range(n)]
    for y in range(H):
        for x in range(W):
            a = acc[grid[y][x]]; a[0] += 1; a[1] += y; a[2] += x
    cent = [((a[1] / a[0] + 0.5) * k / H, (a[2] / a[0] + 0.5) * m / W) for a in acc]
    cells = [(i, j) for i in range(k) for j in range(m)]
    dist = [[(cy - (i + 0.5)) ** 2 + (cx - (j + 0.5)) ** 2 for (i, j) in cells] for cy, cx in cent]
    N = len(cells)
    INF = float("inf")
    dp = [INF] * (1 << N); dp[0] = 0.0
    ch = [None] * (1 << N)
    for mask in range(1 << N):
        if dp[mask] == INF:
            continue
        p = bin(mask).count("1")
        if p >= n:
            continue
        for c in range(N):
            if not mask >> c & 1:
                v = dp[mask] + dist[p][c]
                nm = mask | 1 << c
                if v < dp[nm] - 1e-12:
                    dp[nm] = v; ch[nm] = (mask, c)
    full = (1 << N) - 1
    out = [None] * n
    mask = full
    for p in range(n - 1, -1, -1):
        pm, c = ch[mask]
        out[p] = cells[c]; mask = pm
    return dp[full], out


def _solve(g, orient, aspect):
    P = _parse(g)
    if P is None:
        return None
    E, cont, frags = P
    k, m = len(E), len(E[0])
    pieces = [[cont]] + [_orients(f, orient) for f in frags]
    area = sum(len(p[0]) for p in pieces)
    budget = [NODE_BUDGET]
    for H, W in _dims(area, k, m, aspect):
        best = None
        for t, grid in enumerate(_tilings(H, W, pieces, budget)):
            cost, pos = _assign(grid, len(pieces), k, m)
            if best is None or cost < best[0] - 1e-9:
                best = (cost, grid, pos)
            if t + 1 >= MAX_TILINGS:
                break
        if best is not None:
            _, grid, pos = best
            return [[E[pos[grid[y][x]][0]][pos[grid[y][x]][1]] for x in range(W)] for y in range(H)]
    return None


def fam(train):
    if not train or any(_parse(p["input"]) is None for p in train):
        return
    variants = [("rot4", "prop"), ("dih8", "prop"), ("rot4", "any"), ("dih8", "any")]
    for cost, (orient, aspect) in enumerate(variants, 1):
        def fn(g, orient=orient, aspect=aspect):
            out = _solve(g, orient, aspect)
            if out is None:
                raise ValueError("no tiling")
            return out
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("exemplar_tiling[%s,%s]" % (orient, aspect), cost, fn)


FAMILIES = [fam]
