CARD = "36fdfd69"
READING = ("Each cluster of marker-colour cells (cells within a small gap of each other) is a hidden "
           "rectangle: every other cell inside the cluster's bounding box is recoloured with the fill colour.")


def _colors(g):
    s = set()
    for r in g:
        s.update(r)
    return s


def _clusters(g, m, d):
    H, W = len(g), len(g[0])
    cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == m]
    cs = set(cells)
    seen = set()
    out = []
    for c in cells:
        if c in seen:
            continue
        seen.add(c)
        st = [c]
        comp = []
        while st:
            a, b = st.pop()
            comp.append((a, b))
            for da in range(-d, d + 1):
                for db in range(-d, d + 1):
                    n = (a + da, b + db)
                    if n in cs and n not in seen:
                        seen.add(n)
                        st.append(n)
        out.append(comp)
    return out


def _bbox_merge(boxes, gap):
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] <= b[2] + gap + 1 and b[0] <= a[2] + gap + 1 and \
                        a[1] <= b[3] + gap + 1 and b[1] <= a[3] + gap + 1:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    boxes.pop(j)
                    changed = True
                    break
            if changed:
                break
    return boxes


def _make(m, f, d, merge, keep0):
    def fn(g):
        out = [list(r) for r in g]
        boxes = []
        for comp in _clusters(g, m, d):
            rs = [a for a, _ in comp]; cs = [b for _, b in comp]
            boxes.append((min(rs), min(cs), max(rs), max(cs)))
        if merge:
            boxes = _bbox_merge(boxes, d - 1)
        for r0, c0, r1, c1 in boxes:
            for i in range(r0, r1 + 1):
                for j in range(c0, c1 + 1):
                    if g[i][j] != m and not (keep0 and g[i][j] == 0):
                        out[i][j] = f
        return out
    return fn


def fam(train):
    ins = [_colors(p["input"]) for p in train]
    common = set.intersection(*ins)
    news = set.intersection(*[_colors(p["output"]) - _colors(p["input"]) for p in train])
    found = 0
    for d in (1, 2, 3):
        for merge in (False, True):
            for keep0 in (True, False):
                for m in sorted(common):
                    for f in sorted(news):
                        fn = _make(m, f, d, merge, keep0)
                        try:
                            ok = all(fn(p["input"]) == p["output"] for p in train)
                        except Exception:
                            ok = False
                        if ok:
                            found += 1
                            yield ("cluster_bbox_fill_d%d_m%d_k%d" % (d, merge, keep0),
                                   d + merge + (0 if keep0 else 1), fn)
                            if found >= 3:
                                return
FAMILIES = [fam]
