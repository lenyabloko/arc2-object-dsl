CARD = "a1aa0c1e"
READING = ("Each horizontal band under a coloured full-width line holds a ladder; the output has one row per band "
           "with a bar of the band colour as long as the ladder's rung count, then the floor-line colour, then the "
           "stray marker placed in the row of the shortest (non-empty) ladder.")


def _parse(g):
    H, W = len(g), len(g[0])
    lines = [(r, g[r][0]) for r in range(H) if g[r][0] != 0 and all(x == g[r][0] for x in g[r])]
    if len(lines) < 2:
        return None
    line_cols = set(c for _, c in lines)
    floor_r, floor_c = lines[-1]
    bands = []
    for i in range(len(lines) - 1):
        r0, col = lines[i]
        r1 = lines[i + 1][0]
        rows = list(range(r0 + 1, r1))
        pat_rows = [r for r in rows if any(g[r][c] == col for c in range(W))]
        width = 0
        for r in pat_rows:
            width = max(width, sum(1 for c in range(W) if g[r][c] == col))
        rungs = sum(1 for r in pat_rows if width >= 2 and sum(1 for c in range(W) if g[r][c] == col) == width)
        bands.append({"col": col, "height": len(rows), "plen": len(pat_rows), "rungs": rungs})
    marker = None
    for r in range(H):
        for c in range(W):
            x = g[r][c]
            if x != 0 and x not in line_cols:
                marker = x
    return bands, floor_c, marker


def _pick(bands, key):
    cand = [i for i, b in enumerate(bands) if b["plen"] > 0]
    if not cand:
        return None
    best = None
    for i in cand:
        v = bands[i][key]
        if best is None or v <= bands[best][key]:   # ties -> lowest band
            best = i
    return best


def _make(key, width_mode):
    def fn(g):
        p = _parse(g)
        if p is None:
            return None
        bands, floor_c, marker = p
        if width_mode == "max":
            Wb = max(b["rungs"] for b in bands)
        else:
            Wb = len(bands)
        sel = _pick(bands, key)
        out = []
        for i, b in enumerate(bands):
            row = [b["col"]] * b["rungs"] + [0] * (Wb - b["rungs"])
            row += [floor_c, marker if (i == sel and marker is not None) else 0]
            out.append(row)
        return out
    return fn


def fam(train):
    for key in ("rungs", "plen", "height"):
        for wm in ("max", "nbands"):
            fn = _make(key, wm)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("bars_marker_min_%s_%s" % (key, wm), 1, fn)
            except Exception:
                pass


FAMILIES = [fam]
