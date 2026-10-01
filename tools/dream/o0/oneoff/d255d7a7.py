CARD = "d255d7a7"
READING = ("Each 3x3 bracket with a one-cell track running out of its closed side slides, with its contents, "
           "to the far end of the track, and the old bracket and track are erased.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or (i, j) in seen:
                continue
            st = [(i, j)]
            seen.add((i, j))
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                        seen.add((x, y))
                        st.append((x, y))
            out.append(cells)
    return out


def _make(wall):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [list(r) for r in g]
        moves = []
        for cells in _comps(g, wall):
            s = set(cells)
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            h, w = r1 - r0 + 1, c1 - c0 + 1
            if h == 3 and w > 3:
                left = sum((r, c0) in s for r in range(r0, r1 + 1))
                right = sum((r, c1) in s for r in range(r0, r1 + 1))
                if left == right:
                    continue
                if left > right:
                    blk = (r0, c0); dst = (r0, c1 - 2)
                else:
                    blk = (r0, c1 - 2); dst = (r0, c0)
            elif w == 3 and h > 3:
                top = sum((r0, c) in s for c in range(c0, c1 + 1))
                bot = sum((r1, c) in s for c in range(c0, c1 + 1))
                if top == bot:
                    continue
                if top > bot:
                    blk = (r0, c0); dst = (r1 - 2, c0)
                else:
                    blk = (r1 - 2, c0); dst = (r0, c0)
            else:
                continue
            block = [[g[blk[0] + i][blk[1] + j] for j in range(3)] for i in range(3)]
            moves.append((cells, blk, dst, block))
        for cells, blk, dst, block in moves:
            for a, b in cells:
                out[a][b] = bg
            for i in range(3):
                for j in range(3):
                    out[blk[0] + i][blk[1] + j] = bg
        for cells, blk, dst, block in moves:
            for i in range(3):
                for j in range(3):
                    out[dst[0] + i][dst[1] + j] = block[i][j]
        return out
    return fn


def fam(train):
    for wall in range(10):
        if not all(any(wall in r for r in p["input"]) for p in train):
            continue
        fn = _make(wall)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("slide_bracket_wall%d" % wall, 1, fn)
        except Exception:
            continue


FAMILIES = [fam]
