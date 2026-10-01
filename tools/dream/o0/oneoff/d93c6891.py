CARD = "d93c6891"
READING = ("Each block of the block colour absorbs the line segments of the line colour touching it: the segments "
           "vanish into background and the block recolours to the line colour as many cells as the segments had, "
           "filling whole lines parallel to the segments starting from the segment's row/column.")


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
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
                for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            out.append(cells)
    return out


def _roles(train):
    """Return (block, line, bg) from the training diffs: block->line and line->bg."""
    pairs = set()
    for p in train:
        I, O = p["input"], p["output"]
        if len(I) != len(O) or len(I[0]) != len(O[0]):
            return None
        for r in range(len(I)):
            for c in range(len(I[0])):
                if I[r][c] != O[r][c]:
                    pairs.add((I[r][c], O[r][c]))
    srcs = {a for a, b in pairs}
    dsts = {b for a, b in pairs}
    mid = srcs & dsts
    if len(mid) != 1:
        return None
    L = next(iter(mid))
    ks = {a for a, b in pairs if b == L}
    bs = {b for a, b in pairs if a == L}
    if len(ks) != 1 or len(bs) != 1:
        return None
    return next(iter(ks)), L, next(iter(bs))


def _make(K, L, B):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        lcomps = _comps(g, L)
        owner = {}
        for idx, cs in enumerate(lcomps):
            for c in cs:
                owner[c] = idx
        for cells in _comps(g, K):
            cset = set(cells)
            r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
            c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
            touch = set()
            for a, b in cells:
                for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if (x, y) in owner:
                        touch.add(owner[(x, y)])
            if not touch:
                continue
            n = 0
            votes = {}
            for t in touch:
                seg = lcomps[t]
                n += len(seg)
                rows = {a for a, b in seg}
                cols = {b for a, b in seg}
                if len(rows) == 1 and len(cols) > 1:
                    key = ("h", next(iter(rows)))
                elif len(cols) == 1 and len(rows) > 1:
                    key = ("v", next(iter(cols)))
                else:
                    # single cell / blob: orientation by the side it touches
                    a, b = seg[0]
                    if r0 <= a <= r1:
                        key = ("h", a)
                    else:
                        key = ("v", b)
                votes[key] = votes.get(key, 0) + len(seg)
            ori, pos = max(sorted(votes), key=lambda k: votes[k])
            if ori == "h":
                anchor = min(max(pos, r0), r1)
                lines = sorted(range(r0, r1 + 1), key=lambda r: (abs(r - anchor), r))
                order = [(r, c) for r in lines for c in range(c0, c1 + 1) if (r, c) in cset]
            else:
                anchor = min(max(pos, c0), c1)
                lines = sorted(range(c0, c1 + 1), key=lambda c: (abs(c - anchor), c))
                order = [(r, c) for c in lines for r in range(r0, r1 + 1) if (r, c) in cset]
            for (r, c) in order[:n]:
                out[r][c] = L
            for t in touch:
                for a, b in lcomps[t]:
                    out[a][b] = B
        return out
    return fn


def fam(train):
    roles = _roles(train)
    cands = []
    if roles is not None:
        cands.append(("absorb_segments_%d_%d_%d" % roles, 0, _make(*roles)))
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
