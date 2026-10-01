CARD = "97239e3d"
READING = ("For each marker colour, snap the bounding box of its marker cells outward to the "
           "nearest separator lines, draw that rectangle's outline in the marker colour and fill "
           "the empty centres of the enclosed blocks with it.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _make(fill_centres):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        order = sorted(cnt, key=lambda k: (-cnt[k], k))
        bg = order[0]
        block = order[1] if len(order) > 1 else bg
        markers = order[2:]
        # separator lines: rows / cols containing no block-colour cell
        srows = [i for i in range(H) if all(x != block for x in g[i])]
        scols = [j for j in range(W) if all(g[i][j] != block for i in range(H))]
        srow_set, scol_set = set(srows), set(scols)
        out = [r[:] for r in g]
        for m in markers:
            cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == m]
            r0 = min(c[0] for c in cells); r1 = max(c[0] for c in cells)
            c0 = min(c[1] for c in cells); c1 = max(c[1] for c in cells)
            lo = [s for s in srows if s <= r0]; hi = [s for s in srows if s >= r1]
            R0 = max(lo) if lo else 0; R1 = min(hi) if hi else H - 1
            lo = [s for s in scols if s <= c0]; hi = [s for s in scols if s >= c1]
            C0 = max(lo) if lo else 0; C1 = min(hi) if hi else W - 1
            for j in range(C0, C1 + 1):
                out[R0][j] = m
                out[R1][j] = m
            for i in range(R0, R1 + 1):
                out[i][C0] = m
                out[i][C1] = m
            if fill_centres:
                for i in range(R0 + 1, R1):
                    if i in srow_set:
                        continue
                    for j in range(C0 + 1, C1):
                        if j in scol_set:
                            continue
                        if g[i][j] == bg:
                            out[i][j] = m
        return out
    return fn


def fam(train):
    for name, cost, fn in (("snap_rect_fill_centres", 1, _make(True)),
                           ("snap_rect_outline", 2, _make(False))):
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
