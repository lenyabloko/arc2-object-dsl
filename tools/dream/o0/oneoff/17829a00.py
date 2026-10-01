CARD = "17829a00"
READING = ("Each object (8-connected same-colour pieces) slides, rigidly, toward the border wall of its own colour until "
           "it touches that wall or another object; objects nearest their wall move first.")

from collections import Counter


def _walls(g):
    h, w = len(g), len(g[0])
    walls = {}
    sides = {
        (-1, 0): g[0], (1, 0): g[h - 1],
        (0, -1): [g[r][0] for r in range(h)], (0, 1): [g[r][w - 1] for r in range(h)],
    }
    for d, line in sides.items():
        if len(set(line)) == 1:
            walls.setdefault(line[0], d)
    return walls


def _run(g, conn8=True):
    h, w = len(g), len(g[0])
    walls = _walls(g)
    cnt = Counter(v for row in g for v in row)
    bg = cnt.most_common(1)[0][0]
    # wall cells are fixed
    fixed = set()
    for (dr, dc) in walls.values():
        if dr == -1:
            fixed |= {(0, c) for c in range(w)}
        if dr == 1:
            fixed |= {(h - 1, c) for c in range(w)}
        if dc == -1:
            fixed |= {(r, 0) for r in range(h)}
        if dc == 1:
            fixed |= {(r, w - 1) for r in range(h)}
    seen = set(fixed)
    objs = []
    nbrs = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    if not conn8:
        nbrs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or g[r][c] == bg:
                continue
            col = g[r][c]
            comp = [(r, c)]
            seen.add((r, c))
            st = [(r, c)]
            while st:
                y, x = st.pop()
                for a, b in nbrs:
                    yy, xx = y + a, x + b
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and g[yy][xx] == col:
                        seen.add((yy, xx))
                        comp.append((yy, xx))
                        st.append((yy, xx))
            objs.append((col, comp))
    occ = {}
    for (y, x) in fixed:
        occ[(y, x)] = g[y][x]
    movers = []
    for col, comp in objs:
        if col in walls:
            dr, dc = walls[col]
            if dr == -1:
                key = min(y for y, x in comp)
            elif dr == 1:
                key = h - 1 - max(y for y, x in comp)
            elif dc == -1:
                key = min(x for y, x in comp)
            else:
                key = w - 1 - max(x for y, x in comp)
            movers.append((key, col, comp, (dr, dc)))
        else:
            for p in comp:
                occ[p] = col
    for _, col, comp, _ in movers:
        for p in comp:
            occ[p] = col
    movers.sort(key=lambda t: t[0])
    for _, col, comp, (dr, dc) in movers:
        for p in comp:
            del occ[p]
        cur = comp
        while True:
            nxt = [(y + dr, x + dc) for y, x in cur]
            if all(0 <= y < h and 0 <= x < w and (y, x) not in occ for y, x in nxt):
                cur = nxt
            else:
                break
        for p in cur:
            occ[p] = col
    out = [[bg] * w for _ in range(h)]
    for (y, x), v in occ.items():
        out[y][x] = v
    return out


def _mismatch(fn, train):
    bad = 0
    for p in train:
        o = fn(p["input"])
        O = p["output"]
        if len(o) != len(O) or len(o[0]) != len(O[0]):
            return None
        bad += sum(1 for r in range(len(O)) for c in range(len(O[0])) if o[r][c] != O[r][c])
    return bad


def fam(train):
    exact = False
    for name, cost, c8 in (("slide_to_own_wall_8conn", 1, True), ("slide_to_own_wall_4conn", 2, False)):
        fn = (lambda c8: (lambda g: _run(g, c8)))(c8)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                exact = True
                yield (name, cost, fn)
        except Exception:
            pass
    if not exact:
        # Best attempt: one training pair (train[0]) carries an unexplained 2-pixel extension of a
        # moved segment; yield the slide rule as an explicitly approximate program if the total
        # disagreement is tiny.
        fn = lambda g: _run(g, True)
        try:
            bad = _mismatch(fn, train)
        except Exception:
            bad = None
        total = sum(len(p["output"]) * len(p["output"][0]) for p in train)
        if bad is not None and bad <= max(2, total // 200):
            yield ("slide_to_own_wall_8conn_approx", 9, fn)


def best_attempt(g):
    return _run(g, True)


FAMILIES = [fam]
