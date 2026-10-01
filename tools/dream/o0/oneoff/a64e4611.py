CARD = "a64e4611"
READING = ("The empty corridors that run between the noise blocks out to the grid edge are filled with the new colour, "
           "leaving a one-cell empty margin along the noise but not along the grid border.")


def _maxrects(g, bg):
    """All maximal all-background rectangles (top, bottom, left, right)."""
    H, W = len(g), len(g[0])
    E = [[g[r][c] == bg for c in range(W)] for r in range(H)]
    res = []
    for top in range(H):
        acc = [True] * W
        for bot in range(top, H):
            acc = [acc[c] and E[bot][c] for c in range(W)]
            if not any(acc):
                break
            c = 0
            while c < W:
                if not acc[c]:
                    c += 1
                    continue
                s = c
                while c < W and acc[c]:
                    c += 1
                e = c - 1
                up = top == 0 or not all(E[top - 1][x] for x in range(s, e + 1))
                dn = bot == H - 1 or not all(E[bot + 1][x] for x in range(s, e + 1))
                if up and dn:
                    res.append((top, bot, s, e))
    return res


def _interior(R, H, W):
    t, b, s, e = R
    t2 = t if t == 0 else t + 1
    b2 = b if b == H - 1 else b - 1
    s2 = s if s == 0 else s + 1
    e2 = e if e == W - 1 else e - 1
    return set((r, c) for r in range(t2, b2 + 1) for c in range(s2, e2 + 1))


def _end_walks(R, H, W):
    """Cross-sections of the interior walked inward from each grid border touched at an end of the
    rectangle's long dimension (a list of lists of cell-lists)."""
    t, b, s, e = R
    h, w = b - t + 1, e - s + 1
    I = _interior(R, H, W)
    rows = sorted(set(r for r, c in I))
    cols = sorted(set(c for r, c in I))
    walks = []
    if h >= w:
        if t == 0:
            walks.append([[(r, c) for c in cols] for r in rows])
        if b == H - 1:
            walks.append([[(r, c) for c in cols] for r in rows[::-1]])
    if w >= h:
        if s == 0:
            walks.append([[(r, c) for r in rows] for c in cols])
        if e == W - 1:
            walks.append([[(r, c) for r in rows] for c in cols[::-1]])
    return walks


def _corridors(g, bg, minnew):
    """Greedy (largest first) corridor rectangles that run into the grid border; each adds the inset
    interior from the border inward until it meets an already-filled corridor."""
    H, W = len(g), len(g[0])
    R = [r for r in _maxrects(g, bg) if r[1] - r[0] >= 2 and r[3] - r[2] >= 2]
    R.sort(key=lambda r: (-(r[1] - r[0] + 1) * (r[3] - r[2] + 1), r))
    cov, news = set(), []
    for r in R:
        added = set()
        for walk in _end_walks(r, H, W):
            for sec in walk:
                if any(rc in cov for rc in sec):
                    break
                added.update(sec)
        if len(added) < max(1, minnew):
            continue
        cov |= added
        news.append(len(added))
    return cov, news


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _fill_colour(train):
    cols = set()
    for p in train:
        gi, go = p["input"], p["output"]
        for r in range(len(gi)):
            for c in range(len(gi[0])):
                if gi[r][c] != go[r][c]:
                    cols.add(go[r][c])
    return cols.pop() if len(cols) == 1 else None


def _make(fc, minnew):
    def fn(g):
        bg = 0 if any(0 in r for r in g) else _bg(g)
        cov, _ = _corridors(g, bg, minnew)
        out = [list(r) for r in g]
        for r, c in cov:
            out[r][c] = fc
        return out
    return fn


def fam(train):
    fc = _fill_colour(train)
    if fc is None:
        return
    # smallest corridor addition seen in training (induced), used by the stricter variant
    mins = []
    for p in train:
        g = p["input"]
        bg = 0 if any(0 in r for r in g) else _bg(g)
        _, news = _corridors(g, bg, 1)
        if news:
            mins.append(min(news))
    strict = min(mins) if mins else 1
    for name, mn in (("corridors_border_end", 1), ("corridors_border_end_min%d" % strict, strict)):
        fn = _make(fc, mn)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
