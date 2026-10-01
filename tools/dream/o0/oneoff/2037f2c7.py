CARD = "2037f2c7"
READING = "Two near-identical objects are overlaid by their bounding boxes; the output is the cropped mask of cells where they differ, drawn in a single colour."

from collections import Counter


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and (r, c) not in seen:
                st, cs = [(r, c)], []
                seen.add((r, c))
                while st:
                    y, x = st.pop()
                    cs.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                                seen.add((ny, nx))
                                st.append((ny, nx))
                out.append(cs)
    return out


def _bbox(cs):
    ys = [y for y, _ in cs]
    xs = [x for _, x in cs]
    return [min(ys), min(xs), max(ys), max(xs)]


def _groups(g, bg):
    groups = [(_bbox(c), list(c)) for c in _comps(g, bg)]
    changed = True
    while changed and len(groups) > 2:
        changed = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                a, b = groups[i][0], groups[j][0]
                if a[0] <= b[2] + 1 and b[0] <= a[2] + 1 and a[1] <= b[3] + 1 and b[1] <= a[3] + 1:
                    cs = groups[i][1] + groups[j][1]
                    groups[i] = (_bbox(cs), cs)
                    del groups[j]
                    changed = True
                    break
            if changed:
                break
    groups.sort(key=lambda t: -len(t[1]))
    return groups[:2]


def _make(color):
    def fn(g):
        bg = Counter(v for row in g for v in row).most_common(1)[0][0]
        gr = _groups(g, bg)
        if len(gr) < 2:
            return [[color]]
        (A, _), (B, _) = gr
        ha, wa = A[2] - A[0] + 1, A[3] - A[1] + 1
        hb, wb = B[2] - B[0] + 1, B[3] - B[1] + 1
        h, w = max(ha, hb), max(wa, wb)

        def get(box, y, x):
            yy, xx = box[0] + y, box[1] + x
            if box[0] <= yy <= box[2] and box[1] <= xx <= box[3]:
                return g[yy][xx]
            return bg

        diff = [(y, x) for y in range(h) for x in range(w) if get(A, y, x) != get(B, y, x)]
        if not diff:
            return [[color]]
        y0 = min(y for y, _ in diff)
        x0 = min(x for _, x in diff)
        y1 = max(y for y, _ in diff)
        x1 = max(x for _, x in diff)
        out = [[bg] * (x1 - x0 + 1) for _ in range(y1 - y0 + 1)]
        for y, x in diff:
            out[y - y0][x - x0] = color
        return out
    return fn


def fam(train):
    cols = Counter()
    for p in train:
        bg = Counter(v for row in p["input"] for v in row).most_common(1)[0][0]
        cols.update(v for row in p["output"] for v in row if v != bg)
    for i, (c, _) in enumerate(cols.most_common(2)):
        fn = _make(c)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("object_diff_mask_%d" % c, 1 + i, fn)
        except Exception:
            pass


FAMILIES = [fam]
