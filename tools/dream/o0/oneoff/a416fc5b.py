CARD = "a416fc5b"
READING = ("In the 3x3 board of cells, two adjacent cells hold the same motif; copies of that motif in the new colours "
           "are placed in the cells at fixed ring offsets (learned from training) around the pivot cell, measured from "
           "the direction of the partner motif; if those copies are already present, the learned 'complete' output is given.")

# 8-ring around a pivot, clockwise from up
_RING = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _board(g):
    """Return (bg, sep, row_spans, col_spans, cells) where cells[(i,j)] = (colour or None, mask)."""
    H, W = len(g), len(g[0])
    bg = _bg(g)
    seprows = [r for r in range(H) if g[r][0] != bg and all(x == g[r][0] for x in g[r])]
    sepcols = [c for c in range(W) if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(H))]
    if not seprows or not sepcols:
        return None
    sep = g[seprows[0]][0]

    def spans(seps, n):
        out, s = [], 0
        for k in sorted(seps) + [n]:
            if k > s:
                out.append((s, k))
            s = k + 1
        return out
    rs, cs = spans(seprows, H), spans(sepcols, W)
    cells = {}
    for i, (r0, r1) in enumerate(rs):
        for j, (c0, c1) in enumerate(cs):
            cols = set()
            mask = []
            for r in range(r0, r1):
                for c in range(c0, c1):
                    x = g[r][c]
                    if x != bg and x != sep:
                        cols.add(x)
                        mask.append((r - r0, c - c0))
            col = cols.pop() if len(cols) == 1 else (None if not cols else -1)
            cells[(i, j)] = (col, tuple(mask))
    return bg, sep, rs, cs, cells


def _source(cells):
    cnt = {}
    for k, (col, m) in cells.items():
        if col is not None and col != -1:
            cnt.setdefault(col, []).append(k)
    return cnt


def _configs(cells, src):
    """Yield (pivot, dir_index) for the two source cells."""
    ks = _source(cells).get(src, [])
    if len(ks) != 2:
        return []
    a, b = ks
    res = []
    for p, q in ((a, b), (b, a)):
        d = (q[0] - p[0], q[1] - p[1])
        if d in _RING:
            res.append((p, _RING.index(d)))
    return res


def _learn(train):
    """Learn source colour and {colour: ring offset} from training pairs."""
    src = None
    for p in train:
        bi = _board(p["input"])
        if bi is None:
            return None
        cand = [c for c, ks in _source(bi[4]).items() if len(ks) == 2]
        if len(cand) != 1:
            return None
        if src is None:
            src = cand[0]
        elif src != cand[0]:
            return None
    offs = {}
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            continue
        bi, bo = _board(gi), _board(go)
        if bo is None:
            return None
        added = [(k, bo[4][k][0]) for k in bi[4] if bi[4][k][0] is None and bo[4][k][0] not in (None, -1)]
        confs = _configs(bi[4], src)
        good = None
        for piv, di in confs:
            o = {}
            ok = True
            for k, col in added:
                d = (k[0] - piv[0], k[1] - piv[1])
                if d not in _RING:
                    ok = False
                    break
                o[col] = (_RING.index(d) - di) % 8
            if ok:
                good = o
                break
        if good is None:
            return None
        for col, v in good.items():
            if offs.get(col, v) != v:
                return None
            offs[col] = v
    if not offs:
        return None
    # degenerate (already complete) outputs seen in training
    complete_out = None
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            complete_out = go
    return src, offs, complete_out


def _apply(g, src, offs, complete_out, use_complete):
    b = _board(g)
    if b is None:
        return None
    bg, sep, rs, cs, cells = b
    nI, nJ = len(rs), len(cs)
    confs = _configs(cells, src)
    srcmask = None
    for k, (col, m) in cells.items():
        if col == src:
            srcmask = m
    for piv, di in sorted(confs, key=lambda t: abs(t[0][0] - (nI - 1) / 2.0) + abs(t[0][1] - (nJ - 1) / 2.0)):
        targets = []
        ok = True
        for col, o in offs.items():
            dr, dc = _RING[(di + o) % 8]
            t = (piv[0] + dr, piv[1] + dc)
            if not (0 <= t[0] < nI and 0 <= t[1] < nJ):
                ok = False
                break
            targets.append((t, col))
        if not ok:
            continue
        if all(cells[t][0] == col for t, col in targets):
            if use_complete and complete_out is not None:
                return [list(r) for r in complete_out]
            return [list(r) for r in g]
        if any(cells[t][0] is not None for t, col in targets):
            continue
        out = [list(r) for r in g]
        for (i, j), col in targets:
            r0, c0 = rs[i][0], cs[j][0]
            for (dr, dc) in srcmask:
                out[r0 + dr][c0 + dc] = col
        return out
    return [list(r) for r in g]


def fam(train):
    L = _learn(train)
    if L is None:
        return
    src, offs, complete_out = L
    for use_complete in (True, False):
        fn = (lambda g, uc=use_complete: _apply(g, src, offs, complete_out, uc))
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("ring_offsets_complete%d" % use_complete, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
