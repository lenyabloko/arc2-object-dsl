CARD = "a834deea"
READING = ("Inside each framed hole-colour box, every hole-colour cell of the interior is replaced by the "
           "digit that a fixed key (induced from training) assigns to that relative interior position, "
           "while other cells stay.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _boxes(g, hole):
    """Bounding boxes of 8-connected components of the hole colour."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == hole and not seen[r][c]:
                st = [(r, c)]
                seen[r][c] = True
                r0 = r1 = r
                c0 = c1 = c
                while st:
                    a, b = st.pop()
                    r0, r1, c0, c1 = min(r0, a), max(r1, a), min(c0, b), max(c1, b)
                    for da in (-1, 0, 1):
                        for db in (-1, 0, 1):
                            x, y = a + da, b + db
                            if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == hole:
                                seen[x][y] = True
                                st.append((x, y))
                out.append((r0, r1, c0, c1))
    return out


def _learn(train):
    hole = None
    for p in train:
        g, o = p["input"], p["output"]
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return None
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] != o[r][c]:
                    if hole is None:
                        hole = g[r][c]
                    elif hole != g[r][c]:
                        return None
    if hole is None:
        return None
    key = {}
    kh = kw = None
    for p in train:
        g, o = p["input"], p["output"]
        for r0, r1, c0, c1 in _boxes(g, hole):
            ih, iw = r1 - r0 - 1, c1 - c0 - 1
            if ih <= 0 or iw <= 0:
                continue
            changed = any(g[r][c] != o[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))
            if not changed:
                continue
            if kh is None:
                kh, kw = ih, iw
            elif (kh, kw) != (ih, iw):
                return None
            for i in range(ih):
                for j in range(iw):
                    r, c = r0 + 1 + i, c0 + 1 + j
                    if g[r][c] == hole and o[r][c] != hole:
                        if key.setdefault((i, j), o[r][c]) != o[r][c]:
                            return None
    if kh is None:
        return None
    return hole, kh, kw, key


def _apply(g, hole, kh, kw, key):
    out = [list(r) for r in g]
    for r0, r1, c0, c1 in _boxes(g, hole):
        if (r1 - r0 - 1, c1 - c0 - 1) != (kh, kw):
            continue
        for i in range(kh):
            for j in range(kw):
                r, c = r0 + 1 + i, c0 + 1 + j
                if g[r][c] == hole and (i, j) in key:
                    out[r][c] = key[(i, j)]
    return out


def fam(train):
    L = _learn(train)
    if L is None:
        return
    hole, kh, kw, key = L

    def fn(g, hole=hole, kh=kh, kw=kw, key=key):
        return _apply(g, hole, kh, kw, key)

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("box_key_reveal", 1, fn)


FAMILIES = [fam]
