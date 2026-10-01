CARD = "1b8318e3"
READING = ("Each single dot travels in a straight king-move line toward the nearest block until it "
           "touches the block (lands in its one-cell ring); if that cell is already taken it uses the "
           "nearest ring cell by axis-wise approach, otherwise it goes to the next nearest block.")


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
            col = g[i][j]
            seen[i][j] = True
            st = [(i, j)]
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


def _sgn(x):
    return (x > 0) - (x < 0)


def _make(metric, tries):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        comps = _comps(g, bg)
        anchors = []
        dots = []
        for col, cells in comps:
            if len(cells) >= 2:
                r0 = min(a for a, b in cells) - 1
                r1 = max(a for a, b in cells) + 1
                c0 = min(b for a, b in cells) - 1
                c1 = max(b for a, b in cells) + 1
                anchors.append(((r0, r1, c0, c1), set(cells)))
            else:
                dots.append((cells[0], col))
        if not anchors:
            return [list(r) for r in g]
        blocked = set()
        for _, cs in anchors:
            blocked |= cs
        plans = []
        for (r, c), col in dots:
            opts = []
            for ai, ((r0, r1, c0, c1), cs) in enumerate(anchors):
                gr = max(0, r0 - r, r - r1)
                gc = max(0, c0 - c, c - c1)
                dr = _sgn((r0 - r) if r < r0 else (r1 - r) if r > r1 else 0)
                dc = _sgn((c0 - c) if c < c0 else (c1 - c) if c > c1 else 0)
                if metric == "manh":
                    key = (gr + gc, max(gr, gc), ai)
                else:
                    key = (max(gr, gc), gr + gc, ai)
                k = max(gr, gc)
                line = (r + dr * k, c + dc * k)
                clamp = (r + dr * gr, c + dc * gc)
                cand = []
                for t in tries:
                    p = line if t == "line" else clamp
                    if r0 <= p[0] <= r1 and c0 <= p[1] <= c1 and p not in cand:
                        cand.append(p)
                opts.append((key, cand))
            opts.sort()
            plans.append((opts[0][0][:2], (r, c), col, opts))
        plans.sort()
        out = [list(row) for row in g]
        for _, (r, c), col in [(p[0], p[1], p[2]) for p in plans]:
            out[r][c] = bg
        taken = set()
        for _, (r, c), col, opts in plans:
            dest = None
            for key, cand in opts:
                for p in cand:
                    if 0 <= p[0] < H and 0 <= p[1] < W and p not in taken and p not in blocked:
                        dest = p
                        break
                if dest is not None:
                    break
            if dest is None:
                dest = (r, c)
            taken.add(dest)
            out[dest[0]][dest[1]] = col
        return out
    return fn


def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    n = 0
    variants = []
    for tries in (("line", "clamp"), ("clamp", "line"), ("line",), ("clamp",)):
        for metric in ("manh", "cheb"):
            variants.append((tries, metric))
    for i, (tries, metric) in enumerate(variants):
        fn = _make(metric, tries)
        if _fits(fn, train):
            yield ("dot_to_block_%s_%s" % ("_".join(tries), metric), i, fn)
            n += 1
            if n >= 3:
                return


FAMILIES = [fam]
