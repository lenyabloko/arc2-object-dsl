CARD = "9f8de559"
READING = ("The line ending in a single head cell is extended from the head in the line's direction "
           "across the interior, and the first frame cell it reaches is recoloured to the interior colour.")


def _cells(g, c):
    return [(i, j) for i, r in enumerate(g) for j, x in enumerate(r) if x == c]


def _make(hc, tc):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        heads = _cells(g, hc)
        if len(heads) != 1:
            return out
        hi, hj = heads[0]
        dirs = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if (di or dj) and 0 <= hi + di < H and 0 <= hj + dj < W and g[hi + di][hj + dj] == tc:
                    dirs.append((-di, -dj))
        if len(dirs) != 1:
            return out
        di, dj = dirs[0]
        i, j = hi + di, hj + dj
        if not (0 <= i < H and 0 <= j < W):
            return out
        inner = g[i][j]
        while 0 <= i < H and 0 <= j < W and g[i][j] == inner:
            i += di; j += dj
        if 0 <= i < H and 0 <= j < W:
            out[i][j] = inner
        return out
    return fn


def fam(train):
    singles = None
    for p in train:
        cnt = {}
        for r in p["input"]:
            for x in r:
                cnt[x] = cnt.get(x, 0) + 1
        s = {c for c, n in cnt.items() if n == 1}
        singles = s if singles is None else singles & s
    allc = set()
    for p in train:
        for r in p["input"]:
            allc.update(r)
    k = 0
    for hc in sorted(singles or ()):
        for tc in sorted(allc - {hc}):
            fn = _make(hc, tc)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("extend_head_ray_%d_%d" % (hc, tc), 1.0 + k, fn)
                k += 1
                if k >= 2:
                    return


FAMILIES = [fam]
