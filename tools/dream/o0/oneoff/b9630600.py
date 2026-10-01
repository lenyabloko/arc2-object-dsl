CARD = "b9630600"
READING = ("Hollow rectangles that face each other across empty space are joined into one network by "
           "minimum-spanning-tree corridors: each corridor's walls run along the edges of the shared "
           "interior span and the rectangle walls between them are opened.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _boxes(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != bg and not seen[i][j]:
                st = [(i, j)]
                seen[i][j] = True
                cells = []
                while st:
                    a, b = st.pop()
                    cells.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
                rs = [c[0] for c in cells]
                cs = [c[1] for c in cells]
                out.append((min(rs), min(cs), max(rs), max(cs), g[i][j]))
    return out


def _edges(g, bg, boxes):
    """Candidate corridors: (gap, k1, k2, orient, a, b, lo, hi).
    orient 'h': rows a..b (walls a,b), columns lo..hi (wall to wall inclusive)."""
    E = []
    n = len(boxes)
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            r0, c0, r1, c1, _ = boxes[p]
            s0, d0, s1, d1, _ = boxes[q]
            # horizontal: p left of q
            if c1 < d0:
                a, b = max(r0 + 1, s0 + 1), min(r1 - 1, s1 - 1)
                if a <= b:
                    lo, hi = c1, d0
                    if all(g[i][j] == bg for i in range(a, b + 1) for j in range(lo + 1, hi)):
                        E.append((hi - lo - 1, p, q, 'h', a, b, lo, hi))
            # vertical: p above q
            if r1 < s0:
                a, b = max(c0 + 1, d0 + 1), min(c1 - 1, d1 - 1)
                if a <= b:
                    lo, hi = r1, s0
                    if all(g[i][j] == bg for j in range(a, b + 1) for i in range(lo + 1, hi)):
                        E.append((hi - lo - 1, p, q, 'v', a, b, lo, hi))
    E.sort()
    return E


def _draw(out, e, bg, col):
    _, _, _, o, a, b, lo, hi = e
    for t in range(lo, hi + 1):
        for s in range(a, b + 1):
            v = col if s in (a, b) else bg
            if o == 'h':
                out[s][t] = v
            else:
                out[t][s] = v


def _solve(g, mst):
    bg = _bg(g)
    boxes = _boxes(g, bg)
    E = _edges(g, bg, boxes)
    out = [list(r) for r in g]
    par = list(range(len(boxes)))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for e in E:
        p, q = e[1], e[2]
        if mst:
            fp, fq = find(p), find(q)
            if fp == fq:
                continue
            par[fp] = fq
        _draw(out, e, bg, boxes[p][4])
    return out


def fam(train):
    for name, cost, mst in (("mst_corridors", 1, True), ("all_corridors", 2, False)):
        fn = (lambda m: (lambda g: _solve(g, m)))(mst)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
