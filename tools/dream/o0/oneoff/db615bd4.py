CARD = "db615bd4"
READING = ("The dotted frame becomes a solid outline with its inside cleared, and the dotted pieces outside are "
           "removed and redrawn inside as solid blocks of their bounding-box size, lined up in their original "
           "order along the axis where they fit, one cell apart and centred.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _groups(cells, reach):
    cells = sorted(cells)
    cs = set(cells)
    seen = set()
    out = []
    for s in cells:
        if s in seen:
            continue
        seen.add(s)
        st = [s]
        grp = []
        while st:
            a, b = st.pop()
            grp.append((a, b))
            for da in range(-reach, reach + 1):
                for db in range(-reach, reach + 1):
                    q = (a + da, b + db)
                    if q in cs and q not in seen:
                        seen.add(q)
                        st.append(q)
        out.append(grp)
    return out


def _bbox(cells):
    return (min(a for a, b in cells), max(a for a, b in cells),
            min(b for a, b in cells), max(b for a, b in cells))


def _make(orient_mode):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        order = sorted(cnt, key=lambda k: (-cnt[k], k))
        bg, dot = order[0], order[1]
        rest = order[2:]
        pos = {}
        for r in range(H):
            for c in range(W):
                if g[r][c] in rest:
                    pos.setdefault(g[r][c], []).append((r, c))

        def area(col):
            r0, r1, c0, c1 = _bbox(pos[col])
            return (r1 - r0 + 1) * (c1 - c0 + 1)
        F = max(sorted(rest), key=area)
        R0, R1, C0, C1 = _bbox(pos[F])
        pieces = []
        for col in rest:
            if col == F:
                continue
            for grp in _groups(pos[col], 2):
                r0, r1, c0, c1 = _bbox(grp)
                pieces.append({"col": col, "r0": r0, "c0": c0, "h": r1 - r0 + 1, "w": c1 - c0 + 1, "cells": grp})
        out = [row[:] for row in g]
        for p in pieces:
            for a, b in p["cells"]:
                out[a][b] = bg
        for r in range(R0, R1 + 1):
            for c in range(C0, C1 + 1):
                if r in (R0, R1) or c in (C0, C1):
                    out[r][c] = F
                else:
                    out[r][c] = bg
        if not pieces:
            return out
        IR, IC = R0 + 1, C0 + 1
        IH, IW = R1 - R0 - 1, C1 - C0 - 1
        n = len(pieces)
        hlen = sum(p["w"] for p in pieces) + (n - 1)
        vlen = sum(p["h"] for p in pieces) + (n - 1)
        hfit = hlen <= IW - 2 and max(p["h"] for p in pieces) <= IH - 2
        vfit = vlen <= IH - 2 and max(p["w"] for p in pieces) <= IW - 2
        rs = [p["r0"] + p["h"] / 2.0 for p in pieces]
        cs = [p["c0"] + p["w"] / 2.0 for p in pieces]
        spread_h = (max(cs) - min(cs)) >= (max(rs) - min(rs))
        if orient_mode == "fit":
            if hfit and not vfit:
                horiz = True
            elif vfit and not hfit:
                horiz = False
            else:
                horiz = spread_h
        else:
            horiz = spread_h
        if horiz:
            pieces.sort(key=lambda p: (p["c0"], p["r0"]))
            x = IC + (IW - hlen) // 2
            for p in pieces:
                y = IR + (IH - p["h"]) // 2
                for r in range(y, y + p["h"]):
                    for c in range(x, x + p["w"]):
                        if 0 <= r < H and 0 <= c < W:
                            out[r][c] = p["col"]
                x += p["w"] + 1
        else:
            pieces.sort(key=lambda p: (p["r0"], p["c0"]))
            y = IR + (IH - vlen) // 2
            for p in pieces:
                x = IC + (IW - p["w"]) // 2
                for r in range(y, y + p["h"]):
                    for c in range(x, x + p["w"]):
                        if 0 <= r < H and 0 <= c < W:
                            out[r][c] = p["col"]
                y += p["h"] + 1
        return out
    return fn


def fam(train):
    cands = [("frame_pack_fit", 0, _make("fit")),
             ("frame_pack_spread", 1, _make("spread"))]
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
