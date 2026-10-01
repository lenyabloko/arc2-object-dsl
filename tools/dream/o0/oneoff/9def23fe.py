CARD = "9def23fe"
READING = ("Every row and column of the big solid rectangle is extended as a ray to the grid edge on "
           "each side, except rays that would pass through a scattered dot, which stay empty.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _largest(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    best = None
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            c = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == c:
                        seen[x][y] = True
                        st.append((x, y))
            if best is None or len(cells) > len(best[1]):
                best = (c, cells)
    return best


def _make(block_any):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        lb = _largest(g, bg)
        if lb is None:
            return [list(r) for r in g]
        col, cells = lb
        r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
        c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
        out = [list(r) for r in g]

        def blocked(v):
            return v != bg if block_any else (v != bg and v != col)

        for i in range(r0, r1 + 1):
            for rng in (range(0, c0), range(c1 + 1, W)):
                if not any(blocked(g[i][j]) for j in rng):
                    for j in rng:
                        out[i][j] = col
        for j in range(c0, c1 + 1):
            for rng in (range(0, r0), range(r1 + 1, H)):
                if not any(blocked(g[i][j]) for i in rng):
                    for i in rng:
                        out[i][j] = col
        return out
    return fn


def fam(train):
    for name, ba in (("rect_rays_blocked_by_dots", False), ("rect_rays_blocked_by_any", True)):
        fn = _make(ba)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield (name, 1.0, fn)


FAMILIES = [fam]
