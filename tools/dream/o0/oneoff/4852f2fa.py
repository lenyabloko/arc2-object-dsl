CARD = "4852f2fa"
READING = ("A fixed-size window centred on the multi-cell shape is cut out and repeated side by side "
           "once for every scattered single counter cell.")


def _colors(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _rnd(x):
    import math
    return int(math.floor(x + 0.5))


def _make(bg, counter, h, w, anchor):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] not in (bg, counter)]
        n = sum(1 for r in g for x in r if x == counter)
        r0 = min(i for i, _ in cells); r1 = max(i for i, _ in cells)
        c0 = min(j for _, j in cells); c1 = max(j for _, j in cells)
        if anchor == "centroid":
            ci = _rnd(sum(i for i, _ in cells) / len(cells))
            cj = _rnd(sum(j for _, j in cells) / len(cells))
            a, b = ci - (h - 1) // 2, cj - (w - 1) // 2
        else:  # bounding-box, aligned to its bottom-right
            a, b = r1 - h + 1, c1 - w + 1
        box = []
        for i in range(a, a + h):
            row = []
            for j in range(b, b + w):
                x = g[i][j] if 0 <= i < H and 0 <= j < W else bg
                row.append(bg if x == counter else x)
            box.append(row)
        return [row * n for row in box]
    return fn


def fam(train):
    bgs = None
    common = None
    for p in train:
        cnt = _colors(p["input"])
        bg = max(cnt, key=lambda k: cnt[k])
        bgs = {bg} if bgs is None else bgs & {bg}
        cs = set(cnt) - {bg}
        common = cs if common is None else common & cs
    if not bgs:
        return
    bg = next(iter(bgs))
    for counter in sorted(common):
        sizes = set()
        for p in train:
            n = sum(1 for r in p["input"] for x in r if x == counter)
            o = p["output"]
            if n == 0 or len(o[0]) % n:
                sizes = None
                break
            sizes.add((len(o), len(o[0]) // n))
        if not sizes or len(sizes) != 1:
            continue
        h, w = next(iter(sizes))
        for anchor in ("centroid", "bbox_br"):
            fn = _make(bg, counter, h, w, anchor)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("tile_window_%s_by_count_%d" % (anchor, counter), 1, fn)
            except Exception:
                pass


FAMILIES = [fam]
