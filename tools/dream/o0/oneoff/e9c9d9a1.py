CARD = "e9c9d9a1"
READING = ("Full-length lines split the grid into rectangular cells; the four corner cells and "
           "the interior cells (touching no grid border) are each filled with their own colour "
           "(learned from the examples), while the other border cells stay unchanged.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _bands(lines, n):
    bands = []
    start = None
    for i in range(n):
        if i in lines:
            if start is not None:
                bands.append((start, i - 1))
                start = None
        else:
            if start is None:
                start = i
    if start is not None:
        bands.append((start, n - 1))
    return bands


def _cells(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    rl = set(i for i in range(H) if g[i][0] != bg and all(x == g[i][0] for x in g[i]))
    cl = set(j for j in range(W) if g[0][j] != bg and all(g[i][j] == g[0][j] for i in range(H)))
    rb = _bands(rl, H)
    cb = _bands(cl, W)
    res = []
    for bi, (r0, r1) in enumerate(rb):
        for bj, (c0, c1) in enumerate(cb):
            top = bi == 0
            bot = bi == len(rb) - 1
            lef = bj == 0
            rig = bj == len(cb) - 1
            if top and lef:
                cls = "TL"
            elif top and rig:
                cls = "TR"
            elif bot and lef:
                cls = "BL"
            elif bot and rig:
                cls = "BR"
            elif not (top or bot or lef or rig):
                cls = "IN"
            else:
                cls = "ED"
            res.append((cls, r0, r1, c0, c1))
    return res


def _learn(train):
    m = {}
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        for cls, r0, r1, c0, c1 in _cells(gi):
            changed = any(go[r][c] != gi[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))
            vals = set(go[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1))
            v = ("fill", vals.pop()) if (changed and len(vals) == 1) else (("keep",) if not changed else None)
            if v is None:
                return None
            if cls in m and m[cls] != v:
                # a 'keep' cell whose content equals the fill colour is ambiguous; prefer fill
                if m[cls][0] == "keep" and v[0] == "fill":
                    m[cls] = v
                    continue
                if m[cls][0] == "fill" and v[0] == "keep":
                    continue
                return None
            m[cls] = v
    return m


def _make(m):
    def fn(g):
        out = [row[:] for row in g]
        for cls, r0, r1, c0, c1 in _cells(g):
            v = m.get(cls, ("keep",))
            if v[0] == "fill":
                for r in range(r0, r1 + 1):
                    for c in range(c0, c1 + 1):
                        out[r][c] = v[1]
        return out
    return fn


def fam(train):
    m = _learn(train)
    if m is None:
        return
    fn = _make(m)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("grid_cell_class_fill", 1.0, fn)


FAMILIES = [fam]
