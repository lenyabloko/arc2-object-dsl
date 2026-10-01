CARD = "272f95fa"
READING = "Two full horizontal and two full vertical divider lines cut the grid into a 3x3 of cells; each cell is filled with a colour fixed by its position (learned from training, corners stay background)."


def _dividers(g):
    H, W = len(g), len(g[0])
    rows = [r for r in range(H) if g[r][0] != 0 and all(v == g[r][0] for v in g[r])]
    cols = [c for c in range(W) if g[0][c] != 0 and all(g[r][c] == g[0][c] for r in range(H))]
    return rows, cols


def _bands(lines, n):
    out, start = [], 0
    for x in lines + [n]:
        if x > start:
            out.append((start, x))
        start = x + 1
    return out


def _learn(train):
    table = {}
    for p in train:
        gi, go = p["input"], p["output"]
        H, W = len(gi), len(gi[0])
        rows, cols = _dividers(gi)
        rb, cb = _bands(rows, H), _bands(cols, W)
        if len(rb) != 3 or len(cb) != 3:
            return None
        for i, (r0, r1) in enumerate(rb):
            for j, (c0, c1) in enumerate(cb):
                vals = {go[r][c] for r in range(r0, r1) for c in range(c0, c1)}
                if len(vals) != 1:
                    return None
                v = vals.pop()
                if table.get((i, j), v) != v:
                    return None
                table[(i, j)] = v
    return table


def fam(train):
    table = _learn(train)
    if table is None:
        return

    def fn(g):
        H, W = len(g), len(g[0])
        rows, cols = _dividers(g)
        rb, cb = _bands(rows, H), _bands(cols, W)
        out = [row[:] for row in g]
        if len(rb) != 3 or len(cb) != 3:
            return out
        for i, (r0, r1) in enumerate(rb):
            for j, (c0, c1) in enumerate(cb):
                v = table.get((i, j), 0)
                for r in range(r0, r1):
                    for c in range(c0, c1):
                        out[r][c] = v
        return out

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("grid3x3_position_fill", 1, fn)


FAMILIES = [fam]
