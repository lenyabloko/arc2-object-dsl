CARD = "b20f7c8b"
READING = ("Each framed box whose inner pattern matches (up to rotation/reflection) a coloured shape in "
           "the legend panel is filled solid with that shape's colour, and each solid box whose colour "
           "is in the legend becomes a frame carrying that legend shape's pattern.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            comps.append(cells)
    return comps


def _d4(m):
    out = []
    cur = [row[:] for row in m]
    for _ in range(4):
        out.append(cur)
        out.append([row[::-1] for row in cur])
        cur = [list(r) for r in zip(*cur[::-1])]
    return out


def _analyse(g):
    bg = _bg(g)
    boxes = []
    legends = []
    for cells in _components(g, bg):
        ys = [c[0] for c in cells]
        xs = [c[1] for c in cells]
        r0, c0 = min(ys), min(xs)
        h, w = max(ys) - r0 + 1, max(xs) - c0 + 1
        sub = [g[r][c0:c0 + w] for r in range(r0, r0 + h)]
        border = sub[0] + sub[-1] + [row[0] for row in sub] + [row[-1] for row in sub]
        if h == w and h >= 3 and len(cells) == h * w and len(set(border)) == 1:
            boxes.append((r0, c0, h, sub))
        else:
            legends.append(cells)
    shapes = {}
    for cells in legends:
        cnt = {}
        for a, b in cells:
            cnt[g[a][b]] = cnt.get(g[a][b], 0) + 1
        lbg = max(cnt, key=lambda k: cnt[k])
        bycol = {}
        for a, b in cells:
            if g[a][b] != lbg:
                bycol.setdefault(g[a][b], []).append((a, b))
        for col, cs in bycol.items():
            ys = [c[0] for c in cs]
            xs = [c[1] for c in cs]
            r0, c0 = min(ys), min(xs)
            h, w = max(ys) - r0 + 1, max(xs) - c0 + 1
            m = [[0] * w for _ in range(h)]
            for a, b in cs:
                m[a - r0][b - c0] = 1
            shapes[col] = m
    return bg, boxes, shapes


def _frame_colors(g):
    _, boxes, _ = _analyse(g)
    for r0, c0, s, sub in boxes:
        f = sub[0][0]
        inner = set(x for row in sub[1:-1] for x in row[1:-1]) - {f}
        if len(inner) == 1:
            return f, inner.pop()
    return None


def _make(default_fp):
    def fn(g):
        bg, boxes, shapes = _analyse(g)
        fp = _frame_colors(g) or default_fp
        out = [row[:] for row in g]
        for r0, c0, s, sub in boxes:
            f = sub[0][0]
            vals = set(x for row in sub for x in row)
            if len(vals) == 1:
                col = f
                if col in shapes and fp is not None:
                    F, P = fp
                    m = shapes[col]
                    if len(m) != s - 2 or len(m[0]) != s - 2:
                        continue
                    for a in range(s):
                        for b in range(s):
                            out[r0 + a][c0 + b] = F
                    for a in range(s - 2):
                        for b in range(s - 2):
                            if m[a][b]:
                                out[r0 + 1 + a][c0 + 1 + b] = P
            else:
                inner = [[1 if x != f else 0 for x in row[1:-1]] for row in sub[1:-1]]
                hits = [col for col, m in shapes.items() if any(t == inner for t in _d4(m))]
                if len(hits) == 1:
                    for a in range(s):
                        for b in range(s):
                            out[r0 + a][c0 + b] = hits[0]
        return out
    return fn


def fam(train):
    cnt = {}
    for p in train:
        fp = _frame_colors(p["input"])
        if fp:
            cnt[fp] = cnt.get(fp, 0) + 1
    default_fp = max(cnt, key=lambda k: cnt[k]) if cnt else None
    fn = _make(default_fp)
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("legend_box_swap", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
