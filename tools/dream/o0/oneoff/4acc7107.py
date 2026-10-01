CARD = "4acc7107"
READING = ("Each colour's objects are gathered into a column (colours ordered left-to-right by their "
           "leftmost object), and within a column the objects are stacked up from the bottom edge in "
           "left-to-right input order with one blank row between them, columns separated by one blank column.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _objects(g, bg, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    objs = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            r0 = min(c[0] for c in cells); c0 = min(c[1] for c in cells)
            r1 = max(c[0] for c in cells); c1 = max(c[1] for c in cells)
            objs.append({"col": col, "cells": [(a - r0, b - c0) for a, b in cells],
                         "h": r1 - r0 + 1, "w": c1 - c0 + 1, "r0": r0, "c0": c0})
    return objs


def _make(diag, gap_r, gap_c):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        objs = _objects(g, bg, diag)
        groups = {}
        for o in objs:
            groups.setdefault(o["col"], []).append(o)
        for k in groups:
            groups[k].sort(key=lambda o: (o["c0"], o["r0"]))
        order = sorted(groups, key=lambda k: (groups[k][0]["c0"], groups[k][0]["r0"], k))
        out = [[bg] * W for _ in range(H)]
        x = 0
        for k in order:
            yb = H - 1
            gw = 0
            for o in groups[k]:
                top = yb - o["h"] + 1
                for a, b in o["cells"]:
                    r, c = top + a, x + b
                    if 0 <= r < H and 0 <= c < W:
                        out[r][c] = k
                yb = top - 1 - gap_r
                gw = max(gw, o["w"])
            x += gw + gap_c
        return out
    return fn


def fam(train):
    for diag in (False, True):
        for gr in (1, 0, 2):
            for gc in (1, 0, 2):
                fn = _make(diag, gr, gc)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("stack_by_colour_d%d_g%d%d" % (diag, gr, gc), 1 + diag + gr + gc, fn)
                    return


FAMILIES = [fam]
