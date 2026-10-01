CARD = "32e9702f"
READING = ("Every object is shifted one cell (direction induced, here left) and all background cells, "
           "including the vacated ones, are repainted with a single new background colour.")


def _bg(grids):
    cnt = {}
    for g in grids:
        for r in g:
            for x in r:
                cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _shift(g, dy, dx, bg):
    H, W = len(g), len(g[0])
    out = [[bg] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            rr, cc = r - dy, c - dx
            if 0 <= rr < H and 0 <= cc < W:
                out[r][c] = g[rr][cc]
    return out


def fam(train):
    if not all(len(p["input"]) == len(p["output"]) and len(p["input"][0]) == len(p["output"][0])
               for p in train):
        return
    bg = _bg([p["input"] for p in train])
    shifts = sorted([(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)],
                    key=lambda s: (abs(s[0]) + abs(s[1]), s))
    for dy, dx in shifts:
        fill = set()
        ok = True
        for p in train:
            s = _shift(p["input"], dy, dx, bg)
            for r, row in enumerate(s):
                for c, x in enumerate(row):
                    y = p["output"][r][c]
                    if x == bg:
                        fill.add(y)
                    elif x != y:
                        ok = False
            if not ok:
                break
        if not ok or len(fill) != 1:
            continue
        F = fill.pop()

        def fn(g, dy=dy, dx=dx, F=F):
            s = _shift(g, dy, dx, bg)
            return [[F if x == bg else x for x in row] for row in s]

        yield ("shift%d_%d_fill%d" % (dy, dx, F), 1 + abs(dy) + abs(dx), fn)


FAMILIES = [fam]
