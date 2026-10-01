CARD = "9ba4a9aa"
READING = ("Several 3x3 tiles are linked by dotted paths; starting from the checkerboard tile, "
           "follow the dotted path of the colour that touches it through every junction to the tile "
           "at its other end, and output that tile.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _tiles(g, bg):
    H, W = len(g), len(g[0])
    tiles = []
    for i in range(H - 2):
        for j in range(W - 2):
            blk = [g[i + a][j + b] for a in range(3) for b in range(3)]
            if bg in blk:
                continue
            border = [blk[k] for k in (0, 1, 2, 3, 5, 6, 7, 8)]
            corners = [blk[k] for k in (0, 2, 6, 8, 4)]
            edges = [blk[k] for k in (1, 3, 5, 7)]
            if len(set(border)) == 1 and blk[4] != border[0]:
                kind = "ring"
            elif len(set(corners)) == 1 and len(set(edges)) == 1 and corners[0] != edges[0]:
                kind = "checker"
            else:
                continue
            tiles.append((i, j, kind))
    return tiles


def _make(touch):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        tiles = _tiles(g, bg)
        incell = {}
        for t, (i, j, _) in enumerate(tiles):
            for a in range(3):
                for b in range(3):
                    incell[(i + a, j + b)] = t
        kinds = [k for _, _, k in tiles]
        starts = [t for t, k in enumerate(kinds) if kinds.count(k) == 1]
        chk = [t for t in starts if kinds[t] == "checker"]
        if chk:
            starts = chk
        if len(starts) != 1:
            raise ValueError("no unique start")
        s = starts[0]
        si, sj, _ = tiles[s]

        def near(i, j):
            # dot cells within `touch` steps orthogonally from tile edge
            res = []
            for a in range(3):
                for d in range(1, touch + 1):
                    res.append((i + a, j - d)); res.append((i + a, j + 2 + d))
                    res.append((i - d, j + a)); res.append((i + 2 + d, j + a))
            return [(x, y) for x, y in res if 0 <= x < H and 0 <= y < W
                    and (x, y) not in incell and g[x][y] != bg]

        seeds = near(si, sj)
        if not seeds:
            raise ValueError("no path")
        cols = set(g[x][y] for x, y in seeds)
        if len(cols) != 1:
            raise ValueError("ambiguous path")
        c = cols.pop()
        seen = set(seeds)
        st = list(seeds)
        while st:
            x, y = st.pop()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                for k in (1, 2):
                    nx, ny = x + dx * k, y + dy * k
                    if (0 <= nx < H and 0 <= ny < W and (nx, ny) not in seen
                            and (nx, ny) not in incell and g[nx][ny] == c):
                        seen.add((nx, ny))
                        st.append((nx, ny))
        hits = []
        for t, (i, j, _) in enumerate(tiles):
            if t == s:
                continue
            if any(p in seen for p in near(i, j)):
                hits.append(t)
        if not hits:
            raise ValueError("dead end")
        i, j, _ = tiles[hits[0]]
        return [[g[i + a][j + b] for b in range(3)] for a in range(3)]
    return fn


def fam(train):
    for touch in (1, 2):
        fn = _make(touch)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("follow_path_from_checker_t%d" % touch, touch, fn)
        except Exception:
            pass


FAMILIES = [fam]
