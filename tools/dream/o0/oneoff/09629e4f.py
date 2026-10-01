CARD = "09629e4f"
READING = ("Among the blocks separated by grid lines, the block with the fewest coloured cells is "
           "enlarged: each of its cells floods the whole block at the corresponding position, all "
           "other blocks become empty.")


def _grid_lines(g):
    H, W = len(g), len(g[0])
    for c in sorted({x for r in g for x in r}):
        rows = [i for i in range(H) if all(x == c for x in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == c for i in range(H))]
        if rows and cols:
            return c, rows, cols
    return None


def _runs(n, lines):
    s = set(lines)
    runs, cur = [], []
    for i in range(n):
        if i in s:
            if cur:
                runs.append(cur)
                cur = []
        else:
            cur.append(i)
    if cur:
        runs.append(cur)
    return runs


def _make(select):
    def fn(g):
        gl = _grid_lines(g)
        L, lr, lc = gl
        H, W = len(g), len(g[0])
        R, C = _runs(H, lr), _runs(W, lc)
        cnt = {}
        for r in g:
            for x in r:
                if x != L:
                    cnt[x] = cnt.get(x, 0) + 1
        bg = max(cnt, key=lambda k: cnt[k])
        blocks = []
        for bi in range(len(R)):
            for bj in range(len(C)):
                n = sum(1 for a in R[bi] for b in C[bj] if g[a][b] != bg)
                blocks.append((n, bi, bj))
        ns = [b[0] for b in blocks]
        if select == "min":
            n0, bi, bj = min(blocks)
        else:
            n0, bi, bj = max(blocks)
        if ns.count(n0) != 1:
            raise ValueError("ambiguous")
        blk = [[g[a][b] for b in C[bj]] for a in R[bi]]
        out = [list(r) for r in g]
        for i in range(len(R)):
            for j in range(len(C)):
                col = blk[i][j] if i < len(blk) and j < len(blk[0]) else bg
                for a in R[i]:
                    for b in C[j]:
                        out[a][b] = col
        return out
    return fn


def fam(train):
    for name, sel, cost in (("sparsest_block_zoom", "min", 1), ("densest_block_zoom", "max", 2)):
        fn = _make(sel)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield (name, cost, fn)


FAMILIES = [fam]
