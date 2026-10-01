CARD = "ecaa0ec1"
READING = ("The square pattern is rotated so that the marker pixel touching one of its corners "
           "moves to the corner facing the cluster of loose markers; the loose markers are "
           "erased and the corner marker is redrawn at its new corner.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps4(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
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
            out.append(cells)
    return out


def _rot_cw(m):
    return [list(r) for r in zip(*m[::-1])]


def _sgn(v):
    return (v > 0) - (v < 0)


def _transforms():
    # (name, fn on square matrix, map of corner sign (sr, sc) -> new corner)
    def r0(m): return [r[:] for r in m]
    def r1(m): return _rot_cw(m)
    def r2(m): return _rot_cw(_rot_cw(m))
    def r3(m): return _rot_cw(_rot_cw(_rot_cw(m)))
    def fh(m): return [r[::-1] for r in m]
    def fv(m): return [r[:] for r in m[::-1]]
    def tr(m): return [list(r) for r in zip(*m)]
    def at(m): return r2(tr(m))
    return [("rot0", r0, lambda s: s), ("rotcw", r1, lambda s: (s[1], -s[0])),
            ("rot180", r2, lambda s: (-s[0], -s[1])), ("rotccw", r3, lambda s: (-s[1], s[0])),
            ("flipH", fh, lambda s: (s[0], -s[1])), ("flipV", fv, lambda s: (-s[0], s[1])),
            ("transpose", tr, lambda s: (s[1], s[0])), ("antitranspose", at, lambda s: (-s[1], -s[0]))]


def _parse(g):
    bg = _bg(g)
    comps = _comps4(g, bg)
    if not comps:
        return None
    big = max(comps, key=len)
    r0 = min(a for a, _ in big); r1 = max(a for a, _ in big)
    c0 = min(b for _, b in big); c1 = max(b for _, b in big)
    if r1 - r0 != c1 - c0:
        return None
    others = [c for comp in comps if comp is not big for c in comp]
    if not others:
        return None
    cnt = {}
    for a, b in others:
        cnt[g[a][b]] = cnt.get(g[a][b], 0) + 1
    mk = max(cnt, key=lambda k: cnt[k])
    corners = {(-1, -1): (r0 - 1, c0 - 1), (-1, 1): (r0 - 1, c1 + 1),
               (1, -1): (r1 + 1, c0 - 1), (1, 1): (r1 + 1, c1 + 1)}
    diag = None
    loose = []
    for a, b in others:
        if g[a][b] != mk:
            continue
        hit = None
        for s, pos in corners.items():
            if pos == (a, b):
                hit = s
        if hit is not None and diag is None:
            diag = hit
        else:
            loose.append((a, b))
    if diag is None or not loose:
        return None
    cr = (r0 + r1) / 2.0
    cc = (c0 + c1) / 2.0
    tgt = (_sgn(sum(a for a, _ in loose) / len(loose) - cr), _sgn(sum(b for _, b in loose) / len(loose) - cc))
    if 0 in tgt:
        return None
    return bg, mk, (r0, r1, c0, c1), diag, tgt, corners


def _make(choose):
    trs = _transforms()

    def fn(g):
        H, W = len(g), len(g[0])
        P = _parse(g)
        if P is None:
            return [r[:] for r in g]
        bg, mk, (r0, r1, c0, c1), diag, tgt, corners = P
        sub = [g[r][c0:c1 + 1] for r in range(r0, r1 + 1)]
        pick = None
        for name, f, cm in trs:
            if name in choose and cm(diag) == tgt:
                pick = f
                break
        if pick is None:
            return [r[:] for r in g]
        new = pick(sub)
        out = [[bg] * W for _ in range(H)]
        for i in range(r1 - r0 + 1):
            for j in range(c1 - c0 + 1):
                out[r0 + i][c0 + j] = new[i][j]
        a, b = corners[tgt]
        if 0 <= a < H and 0 <= b < W:
            out[a][b] = mk
        return out
    return fn


def fam(train):
    options = [("rotation", ("rot0", "rotcw", "rot180", "rotccw")),
               ("reflection", ("flipH", "flipV", "transpose", "antitranspose", "rot180", "rot0"))]
    for name, choose in options:
        fn = _make(choose)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("corner_marker_" + name, 1.0, fn)
        except Exception:
            pass


FAMILIES = [fam]
