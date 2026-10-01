CARD = "c6e1b8da"
READING = ("Each rectangle with a one-cell-wide tail slides in the tail's direction by the tail's "
           "length (tail removed, drawn on top); rectangles without tails stay and have their "
           "occluded parts restored.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _analyse(cells):
    """Return (body_box, direction, tail_len, tail_cells) for one colour's cell set."""
    S = set(cells)
    r0 = min(a for a, b in S); r1 = max(a for a, b in S)
    c0 = min(b for a, b in S); c1 = max(b for a, b in S)
    # try each side: peel thin lines whose single cell is at the same interior position
    best = None
    for side in ("top", "bottom", "left", "right"):
        if side in ("top", "bottom"):
            lines = list(range(r0, r1 + 1))
            if side == "bottom":
                lines = lines[::-1]
            get = lambda L: [b for (a, b) in S if a == L]
        else:
            lines = list(range(c0, c1 + 1))
            if side == "right":
                lines = lines[::-1]
            get = lambda L: [a for (a, b) in S if b == L]
        n = 0
        pos = None
        for L in lines:
            ps = get(L)
            if len(ps) == 1 and (pos is None or ps[0] == pos):
                pos = ps[0]
                n += 1
            else:
                break
        if n == 0 or n >= len(lines):
            continue
        # body range perpendicular
        rest_lines = lines[n:]
        perp = [x for L in rest_lines for x in get(L)]
        lo, hi = min(perp), max(perp)
        if not (lo < pos < hi):
            continue
        if best is None or n > best[1]:
            best = (side, n, lines[:n])
    if best is None:
        return (r0, r1, c0, c1), None, 0, []
    side, n, tl = best
    if side == "top":
        box = (r0 + n, r1, c0, c1); dirv = (-1, 0)
        tail = [(a, b) for (a, b) in S if a in tl]
    elif side == "bottom":
        box = (r0, r1 - n, c0, c1); dirv = (1, 0)
        tail = [(a, b) for (a, b) in S if a in tl]
    elif side == "left":
        box = (r0, r1, c0 + n, c1); dirv = (0, -1)
        tail = [(a, b) for (a, b) in S if b in tl]
    else:
        box = (r0, r1, c0, c1 - n); dirv = (0, 1)
        tail = [(a, b) for (a, b) in S if b in tl]
    # recompute body box from non-tail cells
    tset = set(tail)
    body = [c for c in S if c not in tset]
    box = (min(a for a, b in body), max(a for a, b in body),
           min(b for a, b in body), max(b for a, b in body))
    return box, dirv, n, tail


def _make(mult):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        bycol = {}
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg:
                    bycol.setdefault(g[i][j], []).append((i, j))
        info = {c: _analyse(cs) for c, cs in bycol.items()}
        out = [row[:] for row in g]
        moving = [c for c in info if info[c][1] is not None]
        for c in moving:
            for (a, b) in bycol[c]:
                out[a][b] = bg
        for c, (box, dirv, n, tail) in info.items():
            if dirv is not None:
                continue
            r0, r1, c0, c1 = box
            for a in range(r0, r1 + 1):
                for b in range(c0, c1 + 1):
                    if out[a][b] == bg:
                        out[a][b] = c
        for c in moving:
            (r0, r1, c0, c1), (dr, dc), n, tail = info[c]
            sh = n * mult
            for a in range(r0, r1 + 1):
                for b in range(c0, c1 + 1):
                    x, y = a + dr * sh, b + dc * sh
                    if 0 <= x < H and 0 <= y < W:
                        out[x][y] = c
        return out
    return fn


def fam(train):
    for k, mult in enumerate((1, 2)):
        fn = _make(mult)
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
            yield ("tail_slide_x%d" % mult, 10 + k, fn)


FAMILIES = [fam]
