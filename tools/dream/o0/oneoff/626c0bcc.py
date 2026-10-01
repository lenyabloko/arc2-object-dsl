CARD = "626c0bcc"
READING = ("Each single-colour blob is cut exactly into small pieces whose shapes occur in the "
           "training outputs (2x2 square and L-trominoes), and every piece is recoloured with the "
           "colour that its shape has in training.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _norm(cells):
    r0 = min(a for a, b in cells)
    c0 = min(b for a, b in cells)
    return tuple(sorted((a - r0, b - c0) for a, b in cells))


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
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
            out.append((col, cells))
    return out


def _library(train):
    lib = {}
    for p in train:
        I, O = p["input"], p["output"]
        if len(I) != len(O) or len(I[0]) != len(O[0]):
            return None
        bg = _bg(I)
        for i in range(len(I)):
            for j in range(len(I[0])):
                if (I[i][j] == bg) != (O[i][j] == bg):
                    return None
        for col, cells in _comps(O, bg):
            s = _norm(cells)
            if lib.get(s, col) != col:
                return None
            lib[s] = col
    return lib


def _tile(cells, shapes, cap=200):
    # exact cover: the first uncovered cell (row-major) is the first cell of its piece
    cells = set(cells)
    order = sorted(cells)
    sols = []
    used = set()
    chosen = []
    anchored = []
    for s, col in shapes:
        f = s[0]
        anchored.append(([(a - f[0], b - f[1]) for a, b in s], col))

    def rec(k):
        if len(sols) >= cap:
            return
        while k < len(order) and order[k] in used:
            k += 1
        if k == len(order):
            sols.append(list(chosen))
            return
        r, c = order[k]
        for offs, col in anchored:
            pc = [(r + a, c + b) for a, b in offs]
            if all(x in cells and x not in used for x in pc):
                for x in pc:
                    used.add(x)
                chosen.append((pc, col))
                rec(k + 1)
                chosen.pop()
                for x in pc:
                    used.discard(x)
    rec(0)
    return sols


def _make(lib):
    shapes = sorted(lib.items(), key=lambda kv: (len(kv[0]), kv[0]))

    def fn(g):
        bg = _bg(g)
        out = [row[:] for row in g]
        H, W = len(g), len(g[0])
        seen = set()
        # foreground blobs (any non-bg, 4-connected)
        for i in range(H):
            for j in range(W):
                if g[i][j] == bg or (i, j) in seen:
                    continue
                st = [(i, j)]
                seen.add((i, j))
                blob = []
                while st:
                    a, b = st.pop()
                    blob.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] != bg:
                            seen.add((x, y))
                            st.append((x, y))
                sols = _tile(blob, shapes)
                if not sols:
                    continue
                best = max(sols, key=lambda s: len(s))  # prefer finer cut; first found on ties
                for pc, col in best:
                    for a, b in pc:
                        out[a][b] = col
        return out
    return fn


def fam(train):
    lib = _library(train)
    if not lib:
        return
    fn = _make(lib)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("tile_by_shape_library", 1.0, fn)


FAMILIES = [fam]
