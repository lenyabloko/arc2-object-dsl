CARD = "42918530"
READING = ("The grid is a lattice of equal framed boxes; every box whose interior is empty takes the "
           "interior pattern of a patterned box of the same frame colour (boxes with no such partner stay empty).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _boxes(g, bg):
    """Connected (4-conn) non-bg components; return list of (r0, c0, r1, c1, colour)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            stack = [(i, j)]
            seen[i][j] = True
            cells = []
            while stack:
                a, b = stack.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        stack.append((x, y))
            r0 = min(a for a, _ in cells)
            r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells)
            c1 = max(b for _, b in cells)
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            # frame colour = colour of the border ring (must be uniform)
            ring = [g[r0][c] for c in range(c0, c1 + 1)] + [g[r1][c] for c in range(c0, c1 + 1)] + \
                   [g[r][c0] for r in range(r0, r1 + 1)] + [g[r][c1] for r in range(r0, r1 + 1)]
            if len(set(ring)) != 1:
                continue
            out.append((r0, c0, r1, c1, ring[0]))
    out.sort()
    return out


def _interior(g, box):
    r0, c0, r1, c1, _ = box
    return tuple(tuple(g[r][c0 + 1:c1]) for r in range(r0 + 1, r1))


def _solve(g):
    bg = _bg(g)
    boxes = _boxes(g, bg)
    pats = {}
    for b in boxes:
        it = _interior(g, b)
        if any(x != bg for row in it for x in row):
            key = (b[4], b[2] - b[0], b[3] - b[1])
            pats.setdefault(key, []).append(it)
    out = [list(r) for r in g]
    for b in boxes:
        it = _interior(g, b)
        if any(x != bg for row in it for x in row):
            continue
        key = (b[4], b[2] - b[0], b[3] - b[1])
        if key not in pats:
            continue
        cands = pats[key]
        best = max(cands, key=lambda p: (cands.count(p), -cands.index(p)))
        r0, c0 = b[0], b[1]
        for i, row in enumerate(best):
            for j, x in enumerate(row):
                out[r0 + 1 + i][c0 + 1 + j] = x
    return out


def fam(train):
    try:
        if all(_solve(p["input"]) == p["output"] for p in train):
            yield ("fill_empty_box_from_same_colour", 1.0, _solve)
    except Exception:
        return


FAMILIES = [fam]
