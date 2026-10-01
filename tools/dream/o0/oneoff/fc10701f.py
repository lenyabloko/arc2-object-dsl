CARD = "fc10701f"
READING = ("The block of the surviving colour slides along its row/column onto the aligned block of "
           "the vanishing colour (replacing it), and wherever its path crosses a dashed line of holes "
           "the crossing gap is filled with a new colour.")


def _colors(g):
    return {x for r in g for x in r}


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or (i, j) in seen:
                continue
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            rs = [c[0] for c in cells]
            cs = [c[1] for c in cells]
            out.append((min(rs), max(rs), min(cs), max(cs), cells))
    return out


def _induce(train):
    roles = None
    for p in train:
        i, o = p["input"], p["output"]
        if len(i) != len(o) or len(i[0]) != len(o[0]):
            return None
        bg = _bg(i)
        ci, co = _colors(i), _colors(o)
        gone = ci - co
        new = co - ci
        if len(gone) != 1 or len(new) != 1:
            return None
        both = ci & co - {bg}
        mover = [c for c in both if any(
            (i[r][x] == c) != (o[r][x] == c) for r in range(len(i)) for x in range(len(i[0])))]
        hole = [c for c in both if c not in mover]
        if len(mover) != 1 or len(hole) != 1:
            return None
        rr = (mover[0], next(iter(gone)), next(iter(new)), hole[0])
        if roles is None:
            roles = rr
        elif roles != rr:
            return None
    return roles


def _make(roles, mode):
    M, T, F, Hc = roles

    def is_gate(g, cells_side_a, cells_side_b):
        H, W = len(g), len(g[0])

        def h(p):
            a, b = p
            return 0 <= a < H and 0 <= b < W and g[a][b] == Hc

        A, B = h(cells_side_a), h(cells_side_b)
        if mode == "both":
            return A and B
        return A or B

    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        movers = _comps(g, M)
        targets = _comps(g, T)
        used = set()
        for (r0, r1, c0, c1, cells) in movers:
            best = None
            for k, (s0, s1, d0, d1, tcells) in enumerate(targets):
                if k in used:
                    continue
                if (s0, s1) == (r0, r1):
                    dist = min(abs(d0 - c1), abs(c0 - d1))
                    cand = (dist, k, "h")
                elif (d0, d1) == (c0, c1):
                    dist = min(abs(s0 - r1), abs(r0 - s1))
                    cand = (dist, k, "v")
                else:
                    continue
                if best is None or cand < best:
                    best = cand
            if best is None:
                continue
            _, k, ax = best
            used.add(k)
            s0, s1, d0, d1, tcells = targets[k]
            for (a, b) in cells:
                out[a][b] = bg
            for (a, b) in tcells:
                out[a][b] = M
            if ax == "h":
                lo, hi = (c1 + 1, d0) if c1 < d0 else (d1 + 1, c0)
                for c in range(lo, hi):
                    if mode == "line":
                        ok = any(g[r][c] == Hc for r in range(H))
                    else:
                        ok = is_gate(g, (r0 - 1, c), (r1 + 1, c))
                    if ok:
                        for r in range(r0, r1 + 1):
                            out[r][c] = F
            else:
                lo, hi = (r1 + 1, s0) if r1 < s0 else (s1 + 1, r0)
                for r in range(lo, hi):
                    if mode == "line":
                        ok = any(g[r][c] == Hc for c in range(W))
                    else:
                        ok = is_gate(g, (r, c0 - 1), (r, c1 + 1))
                    if ok:
                        for c in range(c0, c1 + 1):
                            out[r][c] = F
        return out

    return fn


def fam(train):
    roles = _induce(train)
    if roles is None:
        return
    for cost, mode in enumerate(("both", "either", "line")):
        fn = _make(roles, mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("slide_gate_" + mode, cost + 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
