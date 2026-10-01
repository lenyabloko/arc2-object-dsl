CARD = "c6141b15"
READING = ("The roles of the straight line and the repeated marker shape swap: copies of the marker are "
           "centred on the line's two endpoints, and the line colour draws the closed polygon joining "
           "the centres of the original markers.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    comps = []
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
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                            seen.add((x, y))
                            st.append((x, y))
            comps.append(cells)
    return comps


def _straight(cells):
    if len(cells) < 2:
        return None
    s = sorted(cells)
    a, b = s[0]
    for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
        for start in s:
            pts = set(cells)
            path = [(start[0] + k * dr, start[1] + k * dc) for k in range(len(cells))]
            if set(path) == pts:
                return path[0], path[-1]
    return None


def _segment(p, q):
    (a, b), (e, f) = p, q
    n = max(abs(e - a), abs(f - b))
    if n == 0:
        return [p]
    res = []
    for k in range(n + 1):
        res.append((a + round(k * (e - a) / n), b + round(k * (f - b) / n)))
    return res


def _parse(g):
    bg = _bg(g)
    cols = sorted(set(x for r in g for x in r) - {bg})
    if len(cols) != 2:
        return None
    info = {c: _comps(g, c) for c in cols}
    line = marker = None
    for c in cols:
        o = [x for x in cols if x != c][0]
        if len(info[c]) == 1 and _straight(info[c][0]) and len(info[o]) >= 2:
            line, marker = c, o
    if line is None:
        return None
    ends = _straight(info[line][0])
    shapes = []
    centres = []
    for cells in info[marker]:
        r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
        c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
        cr, cc = (r0 + r1) // 2, (c0 + c1) // 2
        centres.append((cr, cc))
        shapes.append(sorted((a - cr, b - cc) for a, b in cells))
    return bg, line, marker, ends, shapes, centres


def _polygon_order(pts):
    if len(pts) <= 2:
        return list(pts)
    import math
    my = sum(p[0] for p in pts) / len(pts)
    mx = sum(p[1] for p in pts) / len(pts)
    return sorted(pts, key=lambda p: math.atan2(p[0] - my, p[1] - mx))


def _make(closed):
    def fn(g):
        H, W = len(g), len(g[0])
        pr = _parse(g)
        if pr is None:
            return [list(r) for r in g]
        bg, line, marker, ends, shapes, centres = pr
        out = [[bg] * W for _ in range(H)]
        order = _polygon_order(centres)
        n = len(order)
        segs = []
        for k in range(n - 1 if (n <= 2 or not closed) else n):
            segs.append((order[k], order[(k + 1) % n]))
        for p, q in segs:
            for a, b in _segment(p, q):
                if 0 <= a < H and 0 <= b < W:
                    out[a][b] = line
        shape = shapes[0]
        for (er, ec) in ends:
            for a, b in shape:
                x, y = er + a, ec + b
                if 0 <= x < H and 0 <= y < W:
                    out[x][y] = marker
        return out
    return fn


def fam(train):
    for name, cost, closed in (("swap_closed_polygon", 1, True), ("swap_open_path", 2, False)):
        fn = _make(closed)
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
