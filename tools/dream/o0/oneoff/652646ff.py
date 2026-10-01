CARD = "652646ff"
READING = ("The overlapping, partly hidden copies of the ring shape are each completed and stacked "
           "vertically in a column, ordered from the topmost layer (the one drawn over the others) "
           "down to the bottom layer, on the input background.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _template(train):
    tmpl = None
    for p in train:
        I, O = p["input"], p["output"]
        bg = _bg(O)
        if bg != _bg(I):
            return None
        w = len(O[0])
        if len(O) % w:
            return None
        for b in range(len(O) // w):
            s = set()
            cols = set()
            for i in range(w):
                for j in range(w):
                    v = O[b * w + i][j]
                    if v != bg:
                        s.add((i, j))
                        cols.add(v)
            if len(cols) != 1:
                return None
            s = (w, frozenset(s))
            if tmpl is None:
                tmpl = s
            elif tmpl != s:
                return None
    return tmpl


def _make(tmpl, frac):
    w, shape = tmpl
    shape = sorted(shape)

    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        colours = sorted({x for r in g for x in r if x != bg})
        rings = []
        for c in colours:
            best = None
            for r0 in range(-(w - 1), H):
                for c0 in range(-(w - 1), W):
                    n = 0
                    for a, b in shape:
                        x, y = r0 + a, c0 + b
                        if 0 <= x < H and 0 <= y < W and g[x][y] == c:
                            n += 1
                    if best is None or n > best[0]:
                        best = (n, r0, c0)
            if best and best[0] >= frac * len(shape):
                rings.append((c, best[1], best[2], best[0]))
        cellsets = {}
        for c, r0, c0, n in rings:
            cellsets[c] = {(r0 + a, c0 + b) for a, b in shape
                           if 0 <= r0 + a < H and 0 <= c0 + b < W}
        above = {c: set() for c, _, _, _ in rings}
        for c1, _, _, _ in rings:
            for c2, _, _, _ in rings:
                if c1 == c2:
                    continue
                for x, y in cellsets[c1] & cellsets[c2]:
                    if g[x][y] == c1:
                        above[c1].add(c2)
        # transitive closure
        changed = True
        while changed:
            changed = False
            for c in above:
                add = set()
                for d in above[c]:
                    add |= above[d]
                add -= above[c]
                add.discard(c)
                if add:
                    above[c] |= add
                    changed = True
        order = sorted(rings, key=lambda t: (-len(above[t[0]]), -t[3], t[1], t[2]))
        out = []
        for c, _, _, _ in order:
            blk = [[bg] * w for _ in range(w)]
            for a, b in shape:
                blk[a][b] = c
            out.extend(blk)
        return out
    return fn


def fam(train):
    tmpl = _template(train)
    if tmpl is None:
        return
    for frac in (0.5, 0.4, 0.3, 0.6):
        fn = _make(tmpl, frac)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("stack_rings_by_layer", 1.0, fn)
            return


FAMILIES = [fam]
