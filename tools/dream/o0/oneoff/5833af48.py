CARD = "5833af48"
READING = ("The output is the size of the big plain rectangle: the small mask (downscaled to rectangle "
           "size divided by the stamp size) says where to stamp the small two-colour shape, drawn in "
           "the mark colour on the rectangle's colour.")


def _bg(g):
    # most common colour on the grid border
    H, W = len(g), len(g[0])
    cnt = {}
    for i in range(H):
        for j in range(W):
            if i in (0, H - 1) or j in (0, W - 1):
                cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _comps(g, bg):
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
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
            out.append(cells)
    return out


def _box(g, cells):
    r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
    c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _solve(g):
    bg = _bg(g)
    comps = _comps(g, bg)
    if len(comps) < 3:
        return None
    comps.sort(key=lambda c: -len(c))
    rect = _box(g, comps[0])
    F = rect[0][0]
    if any(x != F for r in rect for x in r):
        return None
    others = [_box(g, c) for c in comps[1:3]]
    withF = [o for o in others if any(x == F for r in o for x in r)]
    without = [o for o in others if not any(x == F for r in o for x in r)]
    if len(withF) != 1 or len(without) != 1:
        return None
    mask, shape = withF[0], without[0]
    common = (set(x for r in mask for x in r) & set(x for r in shape for x in r)) - {F, bg}
    if len(common) != 1:
        return None
    M = next(iter(common))
    H, W = len(rect), len(rect[0])
    sh, sw = len(shape), len(shape[0])
    if H % sh or W % sw:
        return None
    nh, nw = H // sh, W // sw
    mh, mw = len(mask), len(mask[0])
    if mh % nh or mw % nw:
        return None
    fh, fw = mh // nh, mw // nw
    out = [[F] * W for _ in range(H)]
    for bi in range(nh):
        for bj in range(nw):
            if mask[bi * fh][bj * fw] != M:
                continue
            for a in range(sh):
                for b in range(sw):
                    if shape[a][b] == M:
                        out[bi * sh + a][bj * sw + b] = M
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
        yield ("mask_kron_stamp", 0, _solve)


FAMILIES = [fam]
