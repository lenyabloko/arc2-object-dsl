CARD = "d5c634a2"
READING = ("Each distinct object shape (e.g. T pointing up vs T pointing down) is counted, and each "
           "count is written as that many marker cells of the shape's assigned colour into a fixed "
           "slot sequence of a small fixed-size output grid.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
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
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            r0 = min(a for a, _ in cells)
            c0 = min(b for _, b in cells)
            out.append(tuple(sorted((a - r0, b - c0, g[a][b]) for a, b in cells)))
    return out


def _counts(g, diag):
    bg = _bg(g)
    cnt = {}
    for k in _comps(g, bg, diag):
        cnt[k] = cnt.get(k, 0) + 1
    return cnt


def _learn(train, diag, order):
    shapes = [(len(p["output"]), len(p["output"][0])) for p in train]
    if len(set(shapes)) != 1:
        return None
    H, W = shapes[0]
    obg = None
    # output background: most common output colour overall
    tot = {}
    for p in train:
        for r in p["output"]:
            for x in r:
                tot[x] = tot.get(x, 0) + 1
    obg = max(tot, key=lambda k: tot[k])
    cnts = [_counts(p["input"], diag) for p in train]
    allkeys = set()
    for c in cnts:
        allkeys |= set(c)
    colours = sorted({x for p in train for r in p["output"] for x in r if x != obg})
    rules = []
    used = set()
    for col in colours:
        ncol = [sum(1 for r in p["output"] for x in r if x == col) for p in train]
        cand = [k for k in allkeys if all(c.get(k, 0) == n for c, n in zip(cnts, ncol))]
        cand = [k for k in cand if k not in used]
        if len(cand) != 1:
            return None
        key = cand[0]
        used.add(key)
        pos = set()
        for p in train:
            for i in range(H):
                for j in range(W):
                    if p["output"][i][j] == col:
                        pos.add((i, j))
        slots = sorted(pos) if order == "row" else sorted(pos, key=lambda t: (t[1], t[0]))
        for p, n in zip(train, ncol):
            got = {(i, j) for i in range(H) for j in range(W) if p["output"][i][j] == col}
            if got != set(slots[:n]):
                return None
        rules.append((key, col, slots))
    return H, W, obg, rules


def _make(diag, H, W, obg, rules):
    def fn(g):
        cnt = _counts(g, diag)
        out = [[obg] * W for _ in range(H)]
        for key, col, slots in rules:
            n = min(cnt.get(key, 0), len(slots))
            for i, j in slots[:n]:
                out[i][j] = col
        return out
    return fn


def fam(train):
    for diag in (False, True):
        for order in ("row", "col"):
            m = _learn(train, diag, order)
            if m is None:
                continue
            fn = _make(diag, *m)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("shape_count_slots_%s_%s" % ("8" if diag else "4", order), 1 + diag + (order == "col"), fn)
                return


FAMILIES = [fam]
