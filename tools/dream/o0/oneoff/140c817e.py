CARD = "140c817e"
READING = "Every isolated marker pixel extends a full row and full column line in its colour, the marker itself is recoloured to a centre colour and its four diagonal neighbours to a corner colour (both colours learned from training)."

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _markers(g):
    bg = _bg(g)
    return [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]


DIAG = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _make(line_col, centre, diag, diag_over_lines):
    def fn(g):
        H, W = len(g), len(g[0])
        o = [row[:] for row in g]
        ms = _markers(g)
        for r, c, v in ms:
            lc = v if line_col is None else line_col
            for x in range(W):
                o[r][x] = lc
            for y in range(H):
                o[y][c] = lc
        bg = _bg(g)
        for r, c, v in ms:
            for dy, dx in DIAG:
                y, x = r + dy, c + dx
                if 0 <= y < H and 0 <= x < W:
                    if diag_over_lines or o[y][x] == bg:
                        o[y][x] = diag
        for r, c, v in ms:
            o[r][c] = centre
        return o
    return fn


def _learn(train):
    centres, diags, lines = set(), set(), set()
    for p in train:
        g, out = p["input"], p["output"]
        H, W = len(g), len(g[0])
        for r, c, v in _markers(g):
            centres.add(out[r][c])
            for dy, dx in DIAG:
                y, x = r + dy, c + dx
                if 0 <= y < H and 0 <= x < W:
                    diags.add(out[y][x])
    return sorted(centres), sorted(diags)


def fam(train):
    centres, diags = _learn(train)
    for ce in centres:
        for di in diags:
            for lc, lcost in ((None, 0), ):
                for dol, dcost in ((True, 0), (False, 1)):
                    fn = _make(lc, ce, di, dol)
                    try:
                        if all(fn(p["input"]) == p["output"] for p in train):
                            yield ("cross_lines_centre%d_diag%d%s" % (ce, di, "" if dol else "_under"),
                                   1 + lcost + dcost, fn)
                    except Exception:
                        pass
    # fallback: constant line colour learned from training
    lcs = set()
    for p in train:
        g, out = p["input"], p["output"]
        for r, c, v in _markers(g):
            for x in range(len(g[0])):
                if abs(x - c) > 1:
                    lcs.add(out[r][x])
    for lc in sorted(lcs):
        for ce in centres:
            for di in diags:
                fn = _make(lc, ce, di, True)
                try:
                    if all(fn(p["input"]) == p["output"] for p in train):
                        yield ("cross_lines_const%d" % lc, 3, fn)
                except Exception:
                    pass


FAMILIES = [fam]
