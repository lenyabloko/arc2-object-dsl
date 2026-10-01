CARD = "50846271"
READING = ("The scattered cross-colour cells are explained by the fewest plus-shaped crosses "
           "(arm lengths as seen in training), and every missing cell of each cross is filled "
           "with the fill colour.")


def _palette(train):
    cs = set()
    for p in train:
        for r in p["input"] + p["output"]:
            cs.update(r)
    return cs


def _comps(g, pred):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or not pred(g[i][j]):
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and pred(g[x][y]):
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _cross(r, c, L, H, W):
    pts = [(r, c)]
    for k in range(1, L + 1):
        pts += [(r - k, c), (r + k, c), (r, c - k), (r, c + k)]
    return [(a, b) for a, b in pts if 0 <= a < H and 0 <= b < W]


def _arm_lengths(go, C, F):
    """Return arm lengths if every {C,F} component of the output is a (possibly clipped) plus."""
    H, W = len(go), len(go[0])
    Ls = set()
    for cells in _comps(go, lambda v: v in (C, F)):
        s = set(cells)
        found = False
        for (r, c) in cells:
            for L in range(1, max(H, W)):
                cr = set(_cross(r, c, L, H, W))
                if cr == s:
                    Ls.add(L)
                    found = True
                    break
                if not cr <= s:
                    break
            if found:
                break
        if not found:
            return None
    return Ls


def _make(C, F, Ls):
    Ls = sorted(Ls)

    def fn(g):
        H, W = len(g), len(g[0])
        todo = set((i, j) for i in range(H) for j in range(W) if g[i][j] == C)
        out = [list(r) for r in g]
        cands = []
        for i in range(H):
            for j in range(W):
                for L in Ls:
                    cands.append((i, j, L, _cross(i, j, L, H, W)))
        while todo:
            best = None
            for (i, j, L, cells) in cands:
                n = sum(1 for x in cells if x in todo)
                if n == 0:
                    continue
                key = (n, -L, 1 if g[i][j] == C else 0)
                if best is None or key > best[0]:
                    best = (key, cells)
            if best is None:
                break
            for (a, b) in best[1]:
                todo.discard((a, b))
                if out[a][b] != C:
                    out[a][b] = F
        return out
    return fn


def fam(train):
    changed = set()
    for p in train:
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    changed.add(b)
    if len(changed) != 1:
        return
    F = next(iter(changed))
    for C in sorted(_palette(train)):
        if C == F:
            continue
        Ls = set()
        ok = True
        for p in train:
            l = _arm_lengths(p["output"], C, F)
            if not l:
                ok = False
                break
            Ls |= l
        if not ok:
            continue
        fn = _make(C, F, Ls)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("complete_crosses_c%d_f%d" % (C, F), 3, fn)


FAMILIES = [fam]
