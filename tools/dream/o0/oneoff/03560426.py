CARD = "03560426"
READING = ("The separate objects lying along one edge are restacked in left-to-right order as a "
           "diagonal chain from the top-left corner, each object's top-left cell placed on the "
           "previous object's bottom-right cell, later objects drawn on top.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _objects(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
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
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            r0 = min(c[0] for c in cells); c0 = min(c[1] for c in cells)
            r1 = max(c[0] for c in cells); c1 = max(c[1] for c in cells)
            objs.append({"col": col, "cells": [(a - r0, b - c0) for a, b in cells],
                         "h": r1 - r0 + 1, "w": c1 - c0 + 1, "r0": r0, "c0": c0, "c1": c1})
    return objs


def _make(corner, order_desc, later_on_top):
    # corner: (vertical_from_bottom, horizontal_from_right)
    vb, hr = corner

    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        objs = _objects(g, bg)
        objs.sort(key=lambda o: (o["c0"], o["r0"]), reverse=order_desc)
        out = [[bg] * W for _ in range(H)]
        seq = objs if later_on_top else list(reversed(objs))
        # compute positions in chain order
        pos = []
        r = c = 0
        for o in objs:
            pos.append((r, c))
            r += o["h"] - 1
            c += o["w"] - 1
        pl = list(zip(objs, pos))
        if not later_on_top:
            pl = pl[::-1]
        for o, (pr, pc) in pl:
            for a, b in o["cells"]:
                rr, cc = pr + a, pc + b
                if vb:
                    rr = H - 1 - (pr + (o["h"] - 1 - a))
                if hr:
                    cc = W - 1 - (pc + (o["w"] - 1 - b))
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = o["col"]
        return out
    return fn


def fam(train):
    cands = []
    for later in (True, False):
        for corner in ((0, 0), (0, 1), (1, 0), (1, 1)):
            for desc in (False, True):
                cost = (0 if later else 1) + sum(corner) + (1 if desc else 0)
                cands.append(("chain_corner%d%d_desc%d_top%d" % (corner[0], corner[1], desc, later),
                              cost, _make(corner, desc, later)))
    cands.sort(key=lambda t: t[1])
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
