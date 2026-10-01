CARD = "4c177718"
READING = ("Above the separator line sit three shapes (template, arrow, partner); the template shape below "
           "the line keeps its place and the partner shape is drawn directly against it on the side "
           "opposite the arrow's bar (bar on top -> partner below, bar at bottom -> partner above).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg, r_lo, r_hi):
    H, W = len(g), len(g[0])
    seen = set()
    objs = []
    for i in range(r_lo, r_hi):
        for j in range(W):
            if g[i][j] == bg or (i, j) in seen:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if r_lo <= x < r_hi and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                            seen.add((x, y))
                            st.append((x, y))
            r0 = min(c[0] for c in cells); c0 = min(c[1] for c in cells)
            r1 = max(c[0] for c in cells); c1 = max(c[1] for c in cells)
            objs.append({"col": col, "rel": frozenset((a - r0, b - c0) for a, b in cells),
                         "r0": r0, "c0": c0, "h": r1 - r0 + 1, "w": c1 - c0 + 1})
    return objs


def _T(g):
    return [list(r) for r in zip(*g)]


def _solve_rows(g, gap, align):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    sep = None
    for i in range(H):
        if len(set(g[i])) == 1 and g[i][0] != bg:
            sep = i
            break
    if sep is None:
        return None
    top = _comps(g, bg, 0, sep)
    bot = _comps(g, bg, sep + 1, H)
    if len(top) != 3 or len(bot) != 1:
        return None
    top.sort(key=lambda o: o["c0"])
    left, arrow, right = top
    b = bot[0]
    if (b["col"], b["rel"]) == (left["col"], left["rel"]):
        other = right
    elif (b["col"], b["rel"]) == (right["col"], right["rel"]):
        other = left
    else:
        return None
    # arrow bar: row with most cells
    rows = {}
    for a, _ in arrow["rel"]:
        rows[a] = rows.get(a, 0) + 1
    best = max(rows.values())
    bar_rows = [a for a in rows if rows[a] == best]
    if bar_rows == [0]:
        below = True
    elif bar_rows == [arrow["h"] - 1]:
        below = False
    else:
        return None
    out = [list(r) for r in g[sep + 1:]]
    oh = len(out)
    br0 = b["r0"] - (sep + 1)
    if below:
        r0 = br0 + b["h"] + gap
    else:
        r0 = br0 - gap - other["h"]
    if align == 0:
        c0 = b["c0"]
    elif align == 1:
        c0 = b["c0"] + (b["w"] - other["w"]) // 2
    else:
        c0 = b["c0"] + b["w"] - other["w"]
    for a, c in other["rel"]:
        r, cc = r0 + a, c0 + c
        if 0 <= r < oh and 0 <= cc < W:
            out[r][cc] = other["col"]
    return out


def _make(gap, align, transpose):
    def fn(g):
        if transpose:
            r = _solve_rows(_T(g), gap, align)
            return _T(r) if r is not None else None
        return _solve_rows(g, gap, align)
    return fn


def fam(train):
    for tr in (False, True):
        for gap in (0, 1):
            for align in (0, 1, 2):
                fn = _make(gap, align, tr)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("arrow_attach_g%d_a%d_t%d" % (gap, align, tr), 1 + gap + align + tr, fn)
                    return


FAMILIES = [fam]
