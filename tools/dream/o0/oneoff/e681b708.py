CARD = "e681b708"
READING = ("Lines of 1s with coloured marker cells at their ends and crossings cut the grid into "
           "regions; every isolated 1-dot inside a region is recoloured with the colour that is "
           "most frequent among the marker cells touching that region.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _dot_colour(train):
    # the colour of cells that get recoloured (input colour of changed cells)
    cs = set()
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        for a, b in zip(gi, go):
            for x, y in zip(a, b):
                if x != y:
                    cs.add(x)
    return cs.pop() if len(cs) == 1 else None


def _make(dot, minrun, tiebreak):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)

        def nz(i, j):
            return 0 <= i < H and 0 <= j < W and g[i][j] != bg

        line = [[False] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                if g[i][j] == bg:
                    continue
                if g[i][j] != dot:
                    line[i][j] = True
                    continue
                a = j
                while nz(i, a - 1):
                    a -= 1
                b = j
                while nz(i, b + 1):
                    b += 1
                c = i
                while nz(c - 1, j):
                    c -= 1
                e = i
                while nz(e + 1, j):
                    e += 1
                if b - a + 1 >= minrun or e - c + 1 >= minrun:
                    line[i][j] = True
        out = [row[:] for row in g]
        lab = [[False] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                if line[i][j] or lab[i][j]:
                    continue
                st = [(i, j)]
                lab[i][j] = True
                cells = []
                while st:
                    a, b = st.pop()
                    cells.append((a, b))
                    for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= x < H and 0 <= y < W and not line[x][y] and not lab[x][y]:
                            lab[x][y] = True
                            st.append((x, y))
                seen = set()
                cnt = {}
                for a, b in cells:
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            x, y = a + dx, b + dy
                            if (0 <= x < H and 0 <= y < W and line[x][y]
                                    and g[x][y] not in (bg, dot) and (x, y) not in seen):
                                seen.add((x, y))
                                cnt[g[x][y]] = cnt.get(g[x][y], 0) + 1
                if not cnt:
                    continue
                best = max(cnt.values())
                cands = sorted(k for k in cnt if cnt[k] == best)
                col = cands[0] if tiebreak == 0 else cands[-1]
                for a, b in cells:
                    if g[a][b] == dot:
                        out[a][b] = col
        return out
    return fn


def fam(train):
    dot = _dot_colour(train)
    if dot is None:
        return
    for minrun in (3, 2):
        found = False
        for tb in (0, 1):
            fn = _make(dot, minrun, tb)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    found = True
                    yield ("region_marker_majority_r%d_t%d" % (minrun, tb), 2 + tb + (3 - minrun), fn)
            except Exception:
                pass
        if found:
            return


FAMILIES = [fam]
