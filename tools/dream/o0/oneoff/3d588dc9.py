CARD = "3d588dc9"
READING = ("Each stemmed block of the shape colour that lies level with the largest other object "
           "loses its stem and has its side facing that object repainted in the new mark colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, pred, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or not pred(g[i][j]):
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            out.append((col, cells))
    return out


def _largest_rect(cells):
    s = set(cells)
    r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
    c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
    best = None
    for a0 in range(r0, r1 + 1):
        for b0 in range(c0, c1 + 1):
            if (a0, b0) not in s:
                continue
            for a1 in range(a0, r1 + 1):
                if (a1, b0) not in s:
                    break
                for b1 in range(b0, c1 + 1):
                    if any((x, b1) not in s for x in range(a0, a1 + 1)):
                        break
                    area = (a1 - a0 + 1) * (b1 - b0 + 1)
                    if best is None or area > best[0]:
                        best = (area, a0, b0, a1, b1)
    return best


def _learn(train):
    S = set()
    M = set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        bg = _bg(a)
        for i in range(len(a)):
            for j in range(len(a[0])):
                if a[i][j] != b[i][j]:
                    S.add(a[i][j])
                    if b[i][j] != bg:
                        M.add(b[i][j])
    if len(S) != 1 or len(M) != 1:
        return None
    return S.pop(), M.pop()


def _select_level(g, bg, S, axis):
    """targets: S-shapes whose span on the given axis overlaps the largest other object."""
    others = _comps(g, lambda v: v != bg and v != S, True)
    if not others:
        return None, []
    sizes = sorted((len(c) for _, c in others), reverse=True)
    if len(sizes) > 1 and sizes[0] == sizes[1]:
        return None, []
    big = max(others, key=lambda t: len(t[1]))[1]
    k = 0 if axis == "rows" else 1
    b0 = min(c[k] for c in big); b1 = max(c[k] for c in big)
    shapes = _comps(g, lambda v: v == S, False)
    res = []
    for _, cells in shapes:
        s0 = min(c[k] for c in cells); s1 = max(c[k] for c in cells)
        if s0 <= b1 and b0 <= s1:
            res.append(cells)
    return big, res


def _select_center(g, bg, S):
    others = _comps(g, lambda v: v != bg and v != S, True)
    big = max(others, key=lambda t: len(t[1]))[1] if others else None
    H, W = len(g), len(g[0])
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    shapes = [c for _, c in _comps(g, lambda v: v == S, False) if len(c) >= 4]
    if not shapes:
        return big, []

    def d(cells):
        my = sum(a for a, _ in cells) / float(len(cells))
        mx = sum(b for _, b in cells) / float(len(cells))
        return (my - cy) ** 2 + (mx - cx) ** 2
    return big, [min(shapes, key=d)]


def _make(S, M, select, face):
    def fn(g):
        bg = _bg(g)
        out = [row[:] for row in g]
        H, W = len(g), len(g[0])
        big, targets = select(g, bg)
        for cells in targets:
            rect = _largest_rect(cells)
            if rect is None:
                continue
            _, a0, b0, a1, b1 = rect
            if a1 - a0 < 1 or b1 - b0 < 1:
                continue
            for (x, y) in cells:
                if not (a0 <= x <= a1 and b0 <= y <= b1):
                    out[x][y] = bg
            if face == "big" and big is not None:
                by = sum(a for a, _ in big) / float(len(big))
                bx = sum(b for _, b in big) / float(len(big))
            else:
                by, bx = (H - 1) / 2.0, (W - 1) / 2.0
            my, mx = (a0 + a1) / 2.0, (b0 + b1) / 2.0
            if abs(bx - mx) >= abs(by - my):
                col = b1 if bx > mx else b0
                for x in range(a0, a1 + 1):
                    out[x][col] = M
            else:
                row = a1 if by > my else a0
                for y in range(b0, b1 + 1):
                    out[row][y] = M
        return out
    return fn


def fam(train):
    lm = _learn(train)
    if lm is None:
        return
    S, M = lm
    cands = [
        ("level_with_largest_rows_face_big", 1,
         _make(S, M, lambda g, bg: _select_level(g, bg, S, "rows"), "big")),
        ("level_with_largest_cols_face_big", 2,
         _make(S, M, lambda g, bg: _select_level(g, bg, S, "cols"), "big")),
        ("closest_to_centre_face_big", 3,
         _make(S, M, lambda g, bg: _select_center(g, bg, S), "big")),
        ("closest_to_centre_face_centre", 4,
         _make(S, M, lambda g, bg: _select_center(g, bg, S), "centre")),
    ]
    for name, cost, fn in cands:
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
            yield (name, cost, fn)


FAMILIES = [fam]
