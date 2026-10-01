CARD = "3befdf3e"
READING = ("Each framed square swaps its frame and core colours, and grows an arm of the old frame "
           "colour off each side, as thick as the core is wide (corners stay empty).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
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
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
            out.append(cells)
    return out


def _make(mode):
    # mode: how arm thickness is chosen: "core" = core size, "one" = 1, "frame" = full side
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        for cells in _comps(g, bg):
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            h, w = r1 - r0 + 1, c1 - c0 + 1
            if h < 3 or w < 3:
                continue
            outer = g[r0][c0]
            inner = g[r0 + 1][c0 + 1]
            for i in range(r0, r1 + 1):
                for j in range(c0, c1 + 1):
                    border = i in (r0, r1) or j in (c0, c1)
                    out[i][j] = inner if border else outer
            if mode == "core":
                th, tw = h - 2, w - 2
            elif mode == "one":
                th, tw = 1, 1
            else:
                th, tw = h, w
            for i in range(r0, r1 + 1):
                for d in range(1, tw + 1):
                    for j in (c0 - d, c1 + d):
                        if 0 <= j < W:
                            out[i][j] = outer
            for j in range(c0, c1 + 1):
                for d in range(1, th + 1):
                    for i in (r0 - d, r1 + d):
                        if 0 <= i < H:
                            out[i][j] = outer
        return out
    return fn


def fam(train):
    n = 0
    for cost, mode in ((1, "core"), (2, "one"), (3, "frame")):
        fn = _make(mode)
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
            yield ("swap_frame_core_arms_" + mode, cost, fn)
            n += 1


FAMILIES = [fam]
