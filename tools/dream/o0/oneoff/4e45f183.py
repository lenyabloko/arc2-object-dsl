CARD = "4e45f183"
READING = ("The 3x3 board of tiles is rearranged so each tile moves to the board position that its "
           "pattern occupies inside the tile (top-left pattern -> top-left slot, symmetric pattern -> centre).")


def _bands(lines, sep):
    bands = []
    cur = []
    for i, ok in enumerate(lines):
        if ok:
            cur.append(i)
        else:
            if cur:
                bands.append(cur)
            cur = []
    if cur:
        bands.append(cur)
    return bands


def _make():
    def fn(g):
        H, W = len(g), len(g[0])
        sepc = None
        for i in range(H):
            if len(set(g[i])) == 1:
                sepc = g[i][0]
                break
        if sepc is None:
            return None
        rsep = [len(set(g[i])) == 1 and g[i][0] == sepc for i in range(H)]
        csep = [all(g[i][j] == sepc for i in range(H)) for j in range(W)]
        rb = _bands([not x for x in rsep], sepc)
        cb = _bands([not x for x in csep], sepc)
        n = len(rb)
        if n != 3 or len(cb) != 3:
            return None
        if len(set(len(b) for b in rb)) != 1 or len(set(len(b) for b in cb)) != 1:
            return None
        sh, sw = len(rb[0]), len(cb[0])
        cnt = {}
        for b in rb:
            for i in b:
                for c in cb:
                    for j in c:
                        cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
        bg = max(cnt, key=lambda k: cnt[k])
        dest = {}
        for bi in range(3):
            for bj in range(3):
                tile = [[g[i][j] for j in cb[bj]] for i in rb[bi]]
                cells = [(a, b) for a in range(sh) for b in range(sw) if tile[a][b] != bg]
                if not cells:
                    return None
                sr = sum(a for a, _ in cells) * 2
                sc = sum(b for _, b in cells) * 2
                m = len(cells)
                pr = 0 if sr < m * (sh - 1) else (1 if sr == m * (sh - 1) else 2)
                pc = 0 if sc < m * (sw - 1) else (1 if sc == m * (sw - 1) else 2)
                if (pr, pc) in dest:
                    return None
                dest[(pr, pc)] = tile
        out = [list(r) for r in g]
        for (pr, pc), tile in dest.items():
            for a, i in enumerate(rb[pr]):
                for b, j in enumerate(cb[pc]):
                    out[i][j] = tile[a][b]
        return out
    return fn


def fam(train):
    fn = _make()
    try:
        ok = all(fn(p["input"]) == p["output"] for p in train)
    except Exception:
        ok = False
    if ok:
        yield ("tile_to_pattern_position", 1, fn)


FAMILIES = [fam]
