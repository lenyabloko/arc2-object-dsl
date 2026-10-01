CARD = "bf32578f"
READING = ("The single-colour half outline is completed by mirroring it across the axis just beyond "
           "its open side, and the output shows only the interior of the completed closed outline "
           "filled with that colour (the outline itself is erased).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(direction, through):
    # direction: 0 right, 1 left, 2 down, 3 up ; through: 1 -> axis on the extreme line
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg]
        out = [[bg] * W for _ in range(H)]
        if not cells:
            return out
        col = g[cells[0][0]][cells[0][1]]
        rs = [c[0] for c in cells]
        cs = [c[1] for c in cells]
        d = 0 if through else 1
        if direction == 0:
            k = 2 * max(cs) + d
            mir = [(i, k - j) for i, j in cells]
        elif direction == 1:
            k = 2 * min(cs) - d
            mir = [(i, k - j) for i, j in cells]
        elif direction == 2:
            k = 2 * max(rs) + d
            mir = [(k - i, j) for i, j in cells]
        else:
            k = 2 * min(rs) - d
            mir = [(k - i, j) for i, j in cells]
        outline = set(cells) | set(mir)
        r0 = min(a for a, _ in outline) - 1
        r1 = max(a for a, _ in outline) + 1
        c0 = min(b for _, b in outline) - 1
        c1 = max(b for _, b in outline) + 1
        seen = {(r0, c0)}
        st = [(r0, c0)]
        while st:
            a, b = st.pop()
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x, y = a + da, b + db
                if r0 <= x <= r1 and c0 <= y <= c1 and (x, y) not in seen and (x, y) not in outline:
                    seen.add((x, y))
                    st.append((x, y))
        for a in range(r0, r1 + 1):
            for b in range(c0, c1 + 1):
                if (a, b) not in seen and (a, b) not in outline and 0 <= a < H and 0 <= b < W:
                    out[a][b] = col
        return out
    return fn


def fam(train):
    cands = []
    for direction in range(4):
        for through in (0, 1):
            cands.append(("mirror_fill_d%d_t%d" % (direction, through), 1 + direction + through,
                          _make(direction, through)))
    cands.sort(key=lambda t: t[1])
    n = 0
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
            n += 1
            if n >= 3:
                return


FAMILIES = [fam]
