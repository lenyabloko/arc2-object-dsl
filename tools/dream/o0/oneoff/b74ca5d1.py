CARD = "b74ca5d1"
READING = ("Each small shape carries one odd cell whose colour matches a grid-corner marker; the shape "
           "swaps its body and odd-cell colours in place, and every shape is also stamped (overlaid, "
           "in the marker colour) into the corner carrying its odd-cell colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _analyse(g):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    corners = {(0, 0): (0, 0), (0, W - 1): (0, 1), (H - 1, 0): (1, 0), (H - 1, W - 1): (1, 1)}
    markers = {}
    for (r, c), k in corners.items():
        if g[r][c] != bg:
            markers.setdefault(g[r][c], []).append(k)
    body = {}
    specials = []
    for i in range(H):
        for j in range(W):
            v = g[i][j]
            if v == bg or (i, j) in corners:
                continue
            if v in markers:
                specials.append((i, j, v))
            else:
                body.setdefault(v, []).append((i, j))
    shapes = []
    for col, cells in body.items():
        shapes.append({"col": col, "cells": cells, "sp": [],
                       "box": [min(a for a, _ in cells), min(b for _, b in cells),
                               max(a for a, _ in cells), max(b for _, b in cells)]})
    for (i, j, v) in specials:
        best = None
        for s in shapes:
            r0, c0, r1, c1 = s["box"]
            d = max(r0 - i, i - r1, 0) + max(c0 - j, j - c1, 0)
            if best is None or d < best[0]:
                best = (d, s)
        if best is not None:
            best[1]["sp"].append((i, j, v))
    for s in shapes:
        allc = s["cells"] + [(i, j) for i, j, _ in s["sp"]]
        s["box"] = [min(a for a, _ in allc), min(b for _, b in allc),
                    max(a for a, _ in allc), max(b for _, b in allc)]
    return bg, markers, shapes


def _make(swap_inplace, include_special):
    def fn(g):
        H, W = len(g), len(g[0])
        bg, markers, shapes = _analyse(g)
        out = [row[:] for row in g]
        if swap_inplace:
            for s in shapes:
                if len(s["sp"]) != 1:
                    continue
                sc = s["sp"][0][2]
                for (i, j) in s["cells"]:
                    out[i][j] = sc
                i, j, _ = s["sp"][0]
                out[i][j] = s["col"]
        for s in shapes:
            if len(s["sp"]) != 1:
                continue
            mc = s["sp"][0][2]
            r0, c0, r1, c1 = s["box"]
            h, w = r1 - r0 + 1, c1 - c0 + 1
            cells = list(s["cells"])
            if include_special:
                cells.append(s["sp"][0][:2])
            for (vb, hr) in markers.get(mc, []):
                orow = 0 if vb == 0 else H - h
                ocol = 0 if hr == 0 else W - w
                for (i, j) in cells:
                    a, b = orow + i - r0, ocol + j - c0
                    if 0 <= a < H and 0 <= b < W:
                        out[a][b] = mc
        return out
    return fn


def fam(train):
    best = None
    for k, (sw, inc) in enumerate(((True, True), (True, False))):
        fn = _make(sw, inc)
        score = sum(fn(p["input"]) == p["output"] for p in train)
        if score == len(train):
            yield ("odd_cell_corner_stamp_%d" % k, 1.0 + 0.1 * k, fn)
            return
        if best is None or score > best[0]:
            best = (score, k, fn)
    # no exact fit (one training pair looks inconsistent); offer best attempt at high cost
    if best is not None and best[0] >= len(train) - 1:
        yield ("odd_cell_corner_stamp_partial_%d" % best[1], 9.0, best[2])


FAMILIES = [fam]
