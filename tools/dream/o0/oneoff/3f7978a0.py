CARD = "3f7978a0"
READING = ("Crop the rectangle spanned by the two parallel lines of the frame colour, extended one "
           "cell past their ends to include the corner markers.")


def _colors(g):
    s = set()
    for r in g:
        s.update(r)
    return s


def _make(col, er, ec):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == col]
        if not cells:
            return [row[:] for row in g]
        r0 = max(0, min(a for a, _ in cells) - er)
        r1 = min(H - 1, max(a for a, _ in cells) + er)
        c0 = max(0, min(b for _, b in cells) - ec)
        c1 = min(W - 1, max(b for _, b in cells) + ec)
        return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
    return fn


def _ok(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    common = None
    for p in train:
        c = _colors(p["input"])
        common = c if common is None else common & c
    cands = []
    for col in sorted(common or ()):
        for er in range(3):
            for ec in range(3):
                cands.append(("crop_bbox_col%d_pad%d_%d" % (col, er, ec), 1 + er + ec, _make(col, er, ec)))
    cands.sort(key=lambda t: t[1])
    n = 0
    for name, cost, fn in cands:
        if _ok(fn, train):
            yield (name, cost, fn)
            n += 1
            if n >= 3:
                return


FAMILIES = [fam]
