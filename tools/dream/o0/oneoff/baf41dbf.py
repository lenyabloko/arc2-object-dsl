CARD = "baf41dbf"
READING = ("The lined rectangle stretches each outer wall that faces a marker cell until it sits next "
           "to that marker, while its inner dividing lines keep their positions and stretch to the new size.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != bg and not seen[i][j]:
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
                out.append((c, cells))
    return out


def _solve(g, iterate):
    bg = _bg(g)
    comps = _comps(g, bg)
    if not comps:
        return None
    comps.sort(key=lambda t: -len(t[1]))
    C, box = comps[0]
    markers = [p for _, cells in comps[1:] for p in cells]
    r0 = min(p[0] for p in box)
    r1 = max(p[0] for p in box)
    c0 = min(p[1] for p in box)
    c1 = max(p[1] for p in box)
    hl = [r for r in range(r0 + 1, r1) if all(g[r][c] == C for c in range(c0, c1 + 1))]
    vl = [c for c in range(c0 + 1, c1) if all(g[r][c] == C for r in range(r0, r1 + 1))]
    R0, R1, C0, C1 = r0, r1, c0, c1
    while True:
        n0, n1, m0, m1 = R0, R1, C0, C1
        for (a, b) in markers:
            if R0 <= a <= R1:
                if b > C1:
                    m1 = max(m1, b - 1)
                elif b < C0:
                    m0 = min(m0, b + 1)
            if C0 <= b <= C1:
                if a > R1:
                    n1 = max(n1, a - 1)
                elif a < R0:
                    n0 = min(n0, a + 1)
        changed = (n0, n1, m0, m1) != (R0, R1, C0, C1)
        R0, R1, C0, C1 = n0, n1, m0, m1
        if not iterate or not changed:
            break
    out = [list(r) for r in g]
    for (a, b) in box:
        out[a][b] = bg
    for r in range(R0, R1 + 1):
        for c in range(C0, C1 + 1):
            if r in (R0, R1) or c in (C0, C1) or r in hl or c in vl:
                out[r][c] = C
    return out


def fam(train):
    for name, cost, it in (("stretch_to_markers_fixpoint", 1, True), ("stretch_to_markers_once", 2, False)):
        fn = (lambda it: (lambda g: _solve(g, it)))(it)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
