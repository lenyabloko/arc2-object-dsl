CARD = "73c3b0d8"
READING = ("Every loose cell drops one step toward gravity; any cell that comes to rest right "
           "against the full divider line shoots two diagonal rays back away from the line to the grid edge.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rot(g):
    return [list(r) for r in zip(*g[::-1])]


def _rotn(g, n):
    for _ in range(n % 4):
        g = _rot(g)
    return g


def _core(g):
    # gravity downward; divider is a full uniform non-bg row
    H, W = len(g), len(g[0])
    bg = _bg(g)
    lines = [i for i in range(H) if g[i][0] != bg and all(x == g[i][0] for x in g[i])]
    if len(lines) != 1:
        return None
    L = lines[0]
    out = [[bg] * W for _ in range(H)]
    out[L] = list(g[L])
    landed = []
    for i in range(H):
        if i == L:
            continue
        for j in range(W):
            if g[i][j] != bg:
                ni = i + 1
                if ni >= H or ni == L:
                    ni = i
                out[ni][j] = g[i][j]
                if ni == L - 1:
                    landed.append((ni, j, g[i][j]))
    for i, j, c in landed:
        for dj in (-1, 1):
            a, b = i - 1, j + dj
            while 0 <= a < H and 0 <= b < W:
                out[a][b] = c
                a -= 1
                b += dj
    return out


def _make(k):
    def fn(g):
        r = _core(_rotn(g, k))
        return None if r is None else _rotn(r, 4 - k)
    return fn


def fam(train):
    for k in range(4):
        fn = _make(k)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("drop_and_ray_rot%d" % k, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
