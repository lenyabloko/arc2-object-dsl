CARD = "1990f7a8"
READING = ("The four scattered k-by-k shapes are gathered into a 2x2 arrangement (keeping their "
           "top/bottom and left/right relation) with one empty row and column between them.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _groups(g, bg, reach):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            seen[i][j] = True
            st = [(i, j)]
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da in range(-reach, reach + 1):
                    for db in range(-reach, reach + 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
            out.append(cells)
    return out


def _make(k, reach, gap):
    def fn(g):
        bg = _bg(g)
        grs = _groups(g, bg, reach)
        n = len(grs)
        side = int(round(n ** 0.5))
        if side * side != n or side == 0:
            raise ValueError("not a square number of shapes")
        objs = []
        for cells in grs:
            r0 = min(c[0] for c in cells)
            c0 = min(c[1] for c in cells)
            r1 = max(c[0] for c in cells)
            c1 = max(c[1] for c in cells)
            if r1 - r0 + 1 > k or c1 - c0 + 1 > k:
                raise ValueError("shape larger than k")
            objs.append({"r0": r0, "c0": c0, "rc": (r0 + r1) / 2.0, "cc": (c0 + c1) / 2.0,
                         "cells": [(a - r0, b - c0, g[a][b]) for a, b in cells]})
        objs.sort(key=lambda o: (o["rc"], o["cc"]))
        rows = []
        for i in range(side):
            row = objs[i * side:(i + 1) * side]
            row.sort(key=lambda o: o["cc"])
            rows.append(row)
        S = side * k + (side - 1) * gap
        out = [[bg] * S for _ in range(S)]
        for i, row in enumerate(rows):
            for j, o in enumerate(row):
                br, bc = i * (k + gap), j * (k + gap)
                for a, b, v in o["cells"]:
                    out[br + a][bc + b] = v
        return out
    return fn


def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    # shape size k induced from output size: S = side*k + (side-1)*gap, gap in {1, 0}
    ks = set()
    for p in train:
        S = len(p["output"])
        for side in (2, 3):
            for gap in (1, 0):
                if (S - (side - 1) * gap) % side == 0:
                    ks.add(((S - (side - 1) * gap) // side, gap))
    n = 0
    for reach in (1, 2):
        for k, gap in sorted(ks, key=lambda t: (t[1] != 1, t[0])):
            fn = _make(k, reach, gap)
            if _fits(fn, train):
                yield ("gather_grid_k%d_gap%d_reach%d" % (k, gap, reach), reach + (1 - gap), fn)
                n += 1
                if n >= 3:
                    return


FAMILIES = [fam]
