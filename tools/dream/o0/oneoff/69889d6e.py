CARD = "69889d6e"
READING = ("From the seed cell a two-cell-wide staircase climbs diagonally, alternating a vertical and a "
           "sideways step; when the vertical step is blocked by another cell it steps sideways instead, "
           "until it leaves the grid.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(seedcol, prim, sec):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        seeds = [(i, j) for i in range(H) for j in range(W) if g[i][j] == seedcol]
        out = [row[:] for row in g]
        if len(seeds) != 1:
            return out
        r, c = seeds[0]
        phase = 0  # 0: try primary step, 1: secondary step
        steps = 0
        while steps < 4 * (H + W):
            steps += 1
            if phase == 0:
                nr, nc = r + prim[0], c + prim[1]
                if not (0 <= nr < H and 0 <= nc < W):
                    break
                if g[nr][nc] != bg:
                    nr, nc = r + sec[0], c + sec[1]
                    if not (0 <= nr < H and 0 <= nc < W) or g[nr][nc] != bg:
                        break
                else:
                    phase = 1
            else:
                nr, nc = r + sec[0], c + sec[1]
                if not (0 <= nr < H and 0 <= nc < W) or g[nr][nc] != bg:
                    break
                phase = 0
            r, c = nr, nc
            out[r][c] = seedcol
        return out
    return fn


def _seed_colour(train):
    cols = set()
    for p in train:
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    cols.add(b)
    return cols


def fam(train):
    try:
        cols = _seed_colour(train)
    except Exception:
        return
    if len(cols) != 1:
        return
    seedcol = cols.pop()
    dirs = []
    for prim in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        for sec in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if prim[0] * sec[0] + prim[1] * sec[1] == 0 and prim != sec:
                dirs.append((prim, sec))
    n = 0
    for prim, sec in dirs:
        fn = _make(seedcol, prim, sec)
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != p["output"]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield ("staircase_p%d%d_s%d%d" % (prim[0], prim[1], sec[0], sec[1]), 1, fn)
            n += 1
            if n >= 2:
                return


FAMILIES = [fam]
