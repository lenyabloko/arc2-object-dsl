CARD = "06df4c85"
READING = ("In a grid of cells divided by lines, any two cells of the same colour in the same row or "
           "column of cells are joined by colouring all the empty cells between them.")


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


def _make(order):
    def fn(g):
        gl = _grid_lines(g)
        if gl is None:
            return [list(r) for r in g]
        L, lr, lc = gl
        H, W = len(g), len(g[0])
        R = _runs(H, lr)
        C = _runs(W, lc)
        # background colour of cells = most common non-line colour
        cnt = {}
        for r in g:
            for x in r:
                if x != L:
                    cnt[x] = cnt.get(x, 0) + 1
        bg = max(cnt, key=lambda k: cnt[k]) if cnt else 0
        cell = [[g[R[i][0]][C[j][0]] for j in range(len(C))] for i in range(len(R))]
        nr, nc = len(R), len(C)
        new = [row[:] for row in cell]
        fills = {"h": [], "v": []}
        for i in range(nr):
            byc = {}
            for j in range(nc):
                if cell[i][j] != bg:
                    byc.setdefault(cell[i][j], []).append(j)
            for col, js in byc.items():
                if len(js) >= 2:
                    for j in range(min(js), max(js) + 1):
                        if cell[i][j] == bg:
                            fills["h"].append((i, j, col))
        for j in range(nc):
            byc = {}
            for i in range(nr):
                if cell[i][j] != bg:
                    byc.setdefault(cell[i][j], []).append(i)
            for col, is_ in byc.items():
                if len(is_) >= 2:
                    for i in range(min(is_), max(is_) + 1):
                        if cell[i][j] == bg:
                            fills["v"].append((i, j, col))
        # later order wins
        for key in order:
            for i, j, col in fills[key]:
                new[i][j] = col
        out = [list(r) for r in g]
        for i in range(nr):
            for j in range(nc):
                if new[i][j] != cell[i][j]:
                    for a in R[i]:
                        for b in C[j]:
                            out[a][b] = new[i][j]
        return out
    return fn


def fam(train):
    for name, order, cost in (("join_cells_vwins", ("h", "v"), 1), ("join_cells_hwins", ("v", "h"), 2)):
        fn = _make(order)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield (name, cost, fn)


FAMILIES = [fam]
