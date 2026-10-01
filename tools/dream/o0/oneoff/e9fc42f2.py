CARD = "e9fc42f2"
READING = ("The separate pieces are slid together without rotation so that each pair of "
           "same-coloured marker cells (one on the edge of each piece) end up side by side, and "
           "the assembled shape is cropped to its bounding box on the background colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg, conn8):
    H, W = len(g), len(g[0])
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            r0 = min(a for a, _ in cells); c0 = min(b for _, b in cells)
            r1 = max(a for a, _ in cells); c1 = max(b for _, b in cells)
            out.append({"cells": {(a - r0, b - c0): g[a][b] for a, b in cells},
                        "h": r1 - r0 + 1, "w": c1 - c0 + 1})
    return out


DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _edge_dirs(p, cell):
    a, b = cell
    ds = []
    if a == 0: ds.append((-1, 0))
    if a == p["h"] - 1: ds.append((1, 0))
    if b == 0: ds.append((0, -1))
    if b == p["w"] - 1: ds.append((0, 1))
    return ds


def _make(conn8):
    def fn(g):
        bg = _bg(g)
        pieces = _comps(g, bg, conn8)
        pieces = [p for p in pieces if len(p["cells"]) > 1] or pieces
        if not pieces:
            return [r[:] for r in g]
        # main colour = most common colour over all pieces; markers = other colours
        cnt = {}
        for p in pieces:
            for v in p["cells"].values():
                cnt[v] = cnt.get(v, 0) + 1
        main = max(cnt, key=lambda k: cnt[k])
        marks = []  # (piece index, cell, colour)
        for i, p in enumerate(pieces):
            for c, v in p["cells"].items():
                if v != main:
                    marks.append((i, c, v))
        # start from the largest piece
        start = max(range(len(pieces)), key=lambda i: (len(pieces[i]["cells"]), -i))
        pos = {start: (0, 0)}
        occ = {}
        for c, v in pieces[start]["cells"].items():
            occ[c] = v
        changed = True
        while changed:
            changed = False
            for i, ci, col in marks:
                if i not in pos:
                    continue
                for j, cj, colj in marks:
                    if j in pos or colj != col or j == i:
                        continue
                    for d in _edge_dirs(pieces[i], ci):
                        if (-d[0], -d[1]) not in _edge_dirs(pieces[j], cj):
                            continue
                        oi = pos[i]
                        # global position of j's marker = i's marker + d
                        gr = oi[0] + ci[0] + d[0]
                        gc = oi[1] + ci[1] + d[1]
                        oj = (gr - cj[0], gc - cj[1])
                        if any((oj[0] + a, oj[1] + b) in occ for (a, b) in pieces[j]["cells"]):
                            continue
                        pos[j] = oj
                        for (a, b), v in pieces[j]["cells"].items():
                            occ[(oj[0] + a, oj[1] + b)] = v
                        changed = True
                        break
                    if j in pos:
                        break
        # bounding box of placed pieces' bboxes
        rs = []; cs = []
        for i, o in pos.items():
            rs += [o[0], o[0] + pieces[i]["h"] - 1]
            cs += [o[1], o[1] + pieces[i]["w"] - 1]
        R0, R1, C0, C1 = min(rs), max(rs), min(cs), max(cs)
        out = [[bg] * (C1 - C0 + 1) for _ in range(R1 - R0 + 1)]
        for (a, b), v in occ.items():
            out[a - R0][b - C0] = v
        return out
    return fn


def fam(train):
    for conn8 in (False, True):
        fn = _make(conn8)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("marker_dock_%s" % ("8" if conn8 else "4"), 1.0 + 0.1 * conn8, fn)
        except Exception:
            pass


FAMILIES = [fam]
