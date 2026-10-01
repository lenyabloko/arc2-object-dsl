CARD = "a79310a0"
READING = ("Every non-background cell is moved by one fixed offset (induced from training, here one "
           "row down) and recoloured by a colour map induced from training.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _apply(g, dr, dc, cmap):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    out = [[bg] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            x = g[r][c]
            if x != bg:
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = cmap.get(x, x)
    return out


def _learn_map(train, dr, dc):
    cmap = {}
    for p in train:
        g, o = p["input"], p["output"]
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return None
        bg = _bg(g)
        H, W = len(g), len(g[0])
        for r in range(H):
            for c in range(W):
                x = g[r][c]
                if x == bg:
                    continue
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W:
                    y = o[rr][cc]
                    if cmap.setdefault(x, y) != y:
                        return None
    return cmap


def fam(train):
    shifts = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3)]
    shifts.sort(key=lambda s: (abs(s[0]) + abs(s[1]), s))
    found = 0
    for dr, dc in shifts:
        cmap = _learn_map(train, dr, dc)
        if cmap is None:
            continue

        def fn(g, dr=dr, dc=dc, cmap=cmap):
            return _apply(g, dr, dc, cmap)

        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("shift_%d_%d_recolor" % (dr, dc), 1 + abs(dr) + abs(dc), fn)
            found += 1
            if found >= 2:
                return


FAMILIES = [fam]
