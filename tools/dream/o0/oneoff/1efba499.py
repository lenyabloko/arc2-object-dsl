CARD = "1efba499"
READING = "Along every row/column crossing the main shape that has a dot of one colour on one side and a dot of the other colour on the opposite side, the two dots swap sides and snap flush against the shape."

from collections import Counter


def _make(orients):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = Counter(v for row in g for v in row)
        bg = cnt.most_common(1)[0][0]
        nb = [(n, c) for c, n in cnt.items() if c != bg]
        out = [row[:] for row in g]
        if not nb:
            return out
        shape = max(nb)[1]
        lines = []
        if "c" in orients:
            lines += [[(r, x) for r in range(H)] for x in range(W)]
        if "r" in orients:
            lines += [[(y, c) for c in range(W)] for y in range(H)]
        for line in lines:
            vals = [g[y][x] for y, x in line]
            idx = [i for i, v in enumerate(vals) if v == shape]
            if not idx:
                continue
            lo, hi = min(idx), max(idx)
            a = next((i for i in range(lo - 1, -1, -1) if vals[i] not in (bg, shape)), None)
            b = next((i for i in range(hi + 1, len(vals)) if vals[i] not in (bg, shape)), None)
            if a is None or b is None or vals[a] == vals[b]:
                continue
            ca, cb = vals[a], vals[b]
            ya, xa = line[a]
            yb, xb = line[b]
            out[ya][xa] = bg
            out[yb][xb] = bg
            y, x = line[lo - 1]
            out[y][x] = cb
            y, x = line[hi + 1]
            out[y][x] = ca
        return out
    return fn


def fam(train):
    for name, cost, o in (("swap_through_shape_both", 1, "rc"), ("swap_through_shape_cols", 2, "c"),
                          ("swap_through_shape_rows", 2, "r")):
        fn = _make(o)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
