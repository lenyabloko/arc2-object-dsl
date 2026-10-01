CARD = "1c02dbbe"
READING = ("Each marker colour has a cell at a corner of the big rectangle plus one outside mark beside a "
           "side row and one beside a side column; the rectangle region from that corner to that row and "
           "column is painted in the marker colour and the outside marks are erased.")


def _bg(g):
    # background = most common colour on the grid border
    H, W = len(g), len(g[0])
    cnt = {}
    for i in range(H):
        for j in range(W):
            if i in (0, H - 1) or j in (0, W - 1):
                x = g[i][j]
                cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _main(g, bg):
    cnt = {}
    for r in g:
        for x in r:
            if x != bg:
                cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(erase):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        m = _main(g, bg)
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == m]
        R0 = min(a for a, b in cells)
        R1 = max(a for a, b in cells)
        C0 = min(b for a, b in cells)
        C1 = max(b for a, b in cells)
        marks = {}
        for i in range(H):
            for j in range(W):
                v = g[i][j]
                if v != bg and v != m:
                    marks.setdefault(v, []).append((i, j))
        out = [list(r) for r in g]
        regions = []
        for col in sorted(marks):
            inside = [(a, b) for a, b in marks[col] if R0 <= a <= R1 and C0 <= b <= C1]
            rowm = [a for a, b in marks[col] if R0 <= a <= R1 and not (C0 <= b <= C1)]
            colm = [b for a, b in marks[col] if C0 <= b <= C1 and not (R0 <= a <= R1)]
            if erase:
                for a, b in marks[col]:
                    if not (R0 <= a <= R1 and C0 <= b <= C1):
                        out[a][b] = bg
            if not rowm or not colm:
                continue
            tr, tc = rowm[0], colm[0]
            if inside:
                cr, cc = inside[0]
            else:
                cr = R0 if abs(tr - R0) > abs(tr - R1) else R1
                cc = C0 if abs(tc - C0) > abs(tc - C1) else C1
            regions.append((col, min(cr, tr), max(cr, tr), min(cc, tc), max(cc, tc)))
        for col, a0, a1, b0, b1 in regions:
            for a in range(a0, a1 + 1):
                for b in range(b0, b1 + 1):
                    out[a][b] = col
        return out
    return fn


def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    for erase in (True, False):
        fn = _make(erase)
        if _fits(fn, train):
            yield ("corner_marker_fill_erase%d" % erase, 1 - erase, fn)


FAMILIES = [fam]
