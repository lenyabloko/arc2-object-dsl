CARD = "1e5d6875"
READING = "Each L-tromino casts a recoloured copy of itself shifted one diagonal step, towards its open corner or away from it depending on its colour, painted onto background only."

from collections import Counter
from itertools import permutations, product


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and (r, c) not in seen:
                col = g[r][c]
                st, cs = [(r, c)], []
                seen.add((r, c))
                while st:
                    y, x = st.pop()
                    cs.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] == col:
                            seen.add((ny, nx))
                            st.append((ny, nx))
                out.append((col, cs))
    return out


def _lvec(cs):
    """For an L-tromino return the diagonal vector from its corner cell to its open cell."""
    if len(cs) != 3:
        return None
    ys = [y for y, _ in cs]
    xs = [x for _, x in cs]
    if max(ys) - min(ys) != 1 or max(xs) - min(xs) != 1:
        return None
    s = set(cs)
    box = {(y, x) for y in (min(ys), max(ys)) for x in (min(xs), max(xs))}
    miss = (box - s).pop()
    corner = [p for p in s if p[0] != miss[0] and p[1] != miss[1]][0]
    return (miss[0] - corner[0], miss[1] - corner[1])


def _make(rule, order):
    # rule: colour -> (new colour, sign); order: paint order of source colours
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        comps = _comps(g, bg)
        rank = {c: i for i, c in enumerate(order)}
        comps.sort(key=lambda t: rank.get(t[0], len(order)))
        for col, cs in comps:
            if col not in rule:
                continue
            v = _lvec(cs)
            if v is None:
                continue
            k, s = rule[col]
            dy, dx = s * v[0], s * v[1]
            for y, x in cs:
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == bg:
                    out[ny][nx] = k
        return out
    return fn


def fam(train):
    in_cols, out_new = set(), set()
    for p in train:
        bg = _bg(p["input"])
        ic = {v for row in p["input"] for v in row if v != bg}
        oc = {v for row in p["output"] for v in row if v != bg}
        in_cols |= ic
        out_new |= oc - ic
    srcs = sorted(in_cols)
    news = sorted(out_new)
    if not srcs or not news or len(srcs) > 4:
        return
    opts = [(k, s) for k in news for s in (1, -1)]
    found = 0
    for combo in product(opts, repeat=len(srcs)):
        rule = dict(zip(srcs, combo))
        for order in permutations(srcs):
            fn = _make(rule, order)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                found += 1
                yield ("ltromino_shadow_%s_%s" % ("".join("%d%d%+d" % (c, k, s) for c, (k, s) in sorted(rule.items())),
                                                   "".join(map(str, order))), found, fn)
                break
        if found >= 3:
            return


FAMILIES = [fam]
