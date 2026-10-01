CARD = "e4941b18"
READING = ("Two single marker cells sit beside a solid rectangle: the other marker takes the "
           "corner-marker's place, and the corner-marker jumps to the cell just outside the "
           "rectangle's far corner (far edge row, on the side the marker pair points toward).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rot(g):  # rotate 90 deg clockwise
    H, W = len(g), len(g[0])
    return [[g[H - 1 - j][i] for j in range(H)] for i in range(W)]


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    res = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            c = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == c:
                        seen[x][y] = True
                        st.append((x, y))
            res.append((c, cells))
    return res


def _solve_top(g, bg, cc, mode):
    """g normalised so markers lie above the rectangle; returns new grid or None."""
    comps = _comps(g, bg)
    comps.sort(key=lambda t: -len(t[1]))
    rc, rcells = comps[0]
    r0 = min(a for a, b in rcells); r1 = max(a for a, b in rcells)
    c0 = min(b for a, b in rcells); c1 = max(b for a, b in rcells)
    marks = [(c, cells[0]) for c, cells in comps[1:] if len(cells) == 1]
    if len(marks) != 2 or len(comps) != 3:
        return None
    if not all(p[0] < r0 for _, p in marks):
        return None
    B = [m for m in marks if m[0] == cc]
    A = [m for m in marks if m[0] != cc]
    if len(B) != 1 or len(A) != 1:
        return None
    (bc, (bi, bj)), (ac, (ai, aj)) = B[0], A[0]
    if mode == "dir":
        right = bj > aj
    else:
        right = (c1 - bj) <= (bj - c0)
    tj = c1 + 1 if right else c0 - 1
    H, W = len(g), len(g[0])
    if not (0 <= tj < W):
        return None
    out = [row[:] for row in g]
    out[ai][aj] = bg
    out[bi][bj] = ac
    out[r1][tj] = bc
    return out


def _make(cc, mode):
    def fn(g):
        bg = _bg(g)
        cur = g
        for k in range(4):
            res = _solve_top(cur, bg, cc, mode)
            if res is not None:
                for _ in range((4 - k) % 4):
                    res = _rot(res)
                return res
            cur = _rot(cur)
        return [row[:] for row in g]
    return fn


def fam(train):
    cols = set()
    for p in train:
        g = p["input"]
        bg = _bg(g)
        comps = _comps(g, bg)
        comps.sort(key=lambda t: -len(t[1]))
        for c, cells in comps[1:]:
            if len(cells) == 1:
                cols.add(c)
    for mode in ("dir", "near"):
        for cc in sorted(cols):
            fn = _make(cc, mode)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("marker_swap_corner_%s_%d" % (mode, cc), 2 if mode == "dir" else 3, fn)
            except Exception:
                pass


FAMILIES = [fam]
