CARD = "995c5fa3"
READING = ("The input is a row of equal panels separated by empty columns; each panel's hole "
           "pattern stands for a colour (learned from the examples), and the output lists those "
           "colours as one uniformly coloured row per panel, in panel order.")


def _panels(g, bg):
    """Split along full-bg columns (axis 0) or full-bg rows (axis 1)."""
    H, W = len(g), len(g[0])
    res = {}
    seps = [j for j in range(W) if all(g[i][j] == bg for i in range(H))]
    cur = []
    out = []
    for j in range(W + 1):
        if j == W or j in seps:
            if cur:
                out.append(tuple(tuple(g[i][c] for c in cur) for i in range(H)))
            cur = []
        else:
            cur.append(j)
    res["cols"] = out
    seps = [i for i in range(H) if all(g[i][j] == bg for j in range(W))]
    cur = []
    out = []
    for i in range(H + 1):
        if i == H or i in seps:
            if cur:
                out.append(tuple(tuple(g[r]) for r in cur))
            cur = []
        else:
            cur.append(i)
    res["rows"] = out
    return res


def _dist(a, b):
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        return 10 ** 9
    return sum(1 for r in range(len(a)) for c in range(len(a[0])) if a[r][c] != b[r][c])


def _build(axis, width_mode, wconst, table, bg):
    def fn(g):
        ps = _panels(g, bg)[axis]
        k = len(ps)
        cols = []
        for p in ps:
            if p in table:
                cols.append(table[p])
            else:
                best = min(table, key=lambda q: _dist(q, p))
                cols.append(table[best])
        w = k if width_mode == "k" else wconst
        return [[c] * w for c in cols]
    return fn


def fam(train):
    bg = 0
    for axis in ("cols", "rows"):
        table = {}
        ok = True
        for pr in train:
            ps = _panels(pr["input"], bg)[axis]
            out = pr["output"]
            if len(ps) != len(out) or len(ps) < 2:
                ok = False
                break
            for p, row in zip(ps, out):
                if len(set(row)) != 1:
                    ok = False
                    break
                if table.get(p, row[0]) != row[0]:
                    ok = False
                    break
                table[p] = row[0]
            if not ok:
                break
        if not ok or not table:
            continue
        ws = set(len(pr["output"][0]) for pr in train)
        cands = []
        if all(len(pr["output"][0]) == len(pr["output"]) for pr in train):
            cands.append(("k", None))
        if len(ws) == 1:
            cands.append(("const", ws.pop()))
        for wm, wc in cands:
            fn = _build(axis, wm, wc, dict(table), bg)
            if all(fn(pr["input"]) == pr["output"] for pr in train):
                yield ("panel_lookup_%s_%s" % (axis, wm), 1, fn)


FAMILIES = [fam]
