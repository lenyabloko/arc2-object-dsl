CARD = "50aad11f"
READING = ("Each shape of the dominant shape colour is cropped and recoloured with the colour of its "
           "nearest single-cell marker, and the crops are concatenated in reading order along the "
           "axis in which the shapes are laid out.")


def _comps(g, pred, diag=True):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
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
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and pred(g[x][y]):
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _solve(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    order = sorted(cnt, key=lambda k: -cnt[k])
    bg = order[0]
    shape_col = order[1]
    shapes = _comps(g, lambda v: v == shape_col)
    markers = [(i, j, g[i][j]) for i in range(len(g)) for j in range(len(g[0]))
               if g[i][j] not in (bg, shape_col)]
    if not shapes or not markers:
        return None
    infos = []
    for cells in shapes:
        best = None
        for (mi, mj, mc) in markers:
            d = min(max(abs(mi - a), abs(mj - b)) for a, b in cells)
            if best is None or d < best[0]:
                best = (d, mc)
        r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
        c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
        crop = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
        for a, b in cells:
            crop[a - r0][b - c0] = best[1]
        infos.append((r0, r1, c0, c1, crop))
    # layout: horizontal if column ranges pairwise disjoint, else vertical
    def disjoint(k0, k1):
        s = sorted(infos, key=lambda t: t[k0])
        return all(s[i][k1] < s[i + 1][k0] for i in range(len(s) - 1))
    if disjoint(2, 3):
        s = sorted(infos, key=lambda t: t[2])
        H = max(len(t[4]) for t in s)
        out = [[] for _ in range(H)]
        for t in s:
            cr = t[4]
            w = len(cr[0])
            for i in range(H):
                out[i].extend(cr[i] if i < len(cr) else [bg] * w)
        return out
    s = sorted(infos, key=lambda t: t[0])
    W = max(len(t[4][0]) for t in s)
    out = []
    for t in s:
        for row in t[4]:
            out.append(list(row) + [bg] * (W - len(row)))
    return out


def fam(train):
    ok = True
    for p in train:
        try:
            if _solve(p["input"]) != p["output"]:
                ok = False
                break
        except Exception:
            ok = False
            break
    if ok:
        yield ("crop_recolour_concat", 3, _solve)


FAMILIES = [fam]
