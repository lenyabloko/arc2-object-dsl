CARD = "6d58a25d"
READING = ("Under the large multi-cell 'umbrella' shape, every column of the umbrella that has a scattered dot "
           "beyond the umbrella gets a line of the dot colour from just past the umbrella to the grid edge.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
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
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                            seen[x][y] = True
                            st.append((x, y))
            comps.append((col, cells))
    return comps


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _down(g, bg):
    # rays go downward (increasing row) from below each umbrella column
    H, W = len(g), len(g[0])
    comps = _comps(g, bg)
    if not comps:
        return [r[:] for r in g]
    big = max(comps, key=lambda c: len(c[1]))
    ucol = big[0]
    ucells = set(big[1])
    out = [r[:] for r in g]
    low = {}
    for (a, b) in ucells:
        low[b] = max(low.get(b, -1), a)
    for b, L in low.items():
        dot = None
        for a in range(L + 1, H):
            if g[a][b] != bg and g[a][b] != ucol:
                dot = g[a][b]
                break
        if dot is None:
            continue
        for a in range(L + 1, H):
            if out[a][b] == bg:
                out[a][b] = dot
    return out


def _orient(g, bg):
    comps = _comps(g, bg)
    big = max(comps, key=lambda c: len(c[1]))
    cells = big[1]
    r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
    c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
    if (c1 - c0) >= (r1 - r0):
        top = sum(1 for a, b in cells if a == r0)
        bot = sum(1 for a, b in cells if a == r1)
        return "down" if top <= bot else "up"
    left = sum(1 for a, b in cells if b == c0)
    right = sum(1 for a, b in cells if b == c1)
    return "right" if left <= right else "left"


def _auto(g):
    bg = _bg(g)
    d = _orient(g, bg)
    if d == "down":
        return _down(g, bg)
    if d == "up":
        return _down(g[::-1], bg)[::-1]
    t = _transpose(g)
    if d == "right":
        return _transpose(_down(t, bg))
    return _transpose(_down(t[::-1], bg)[::-1])


def _fixed_down(g):
    return _down(g, _bg(g))


def fam(train):
    for name, fn in (("umbrella_rays_auto_dir", _auto), ("umbrella_rays_down", _fixed_down)):
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
