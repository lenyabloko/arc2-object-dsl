CARD = "22806e14"
READING = ("Every solid odd-sided square of the shape colour gets its centre cell painted with the colour of the "
           "plus-shaped key (even squares untouched); the key itself is erased or kept by a scene-level test induced from training.")
from collections import Counter

PLUS = {(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            col = g[r][c]
            st = [(r, c)]
            seen[r][c] = True
            cells = []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        st.append((ny, nx))
            out.append((col, cells))
    return out


def _analyse(g):
    bg = _bg(g)
    comps = _comps(g, bg)
    key = None
    for col, cells in comps:
        r0 = min(y for y, _ in cells); c0 = min(x for _, x in cells)
        if {(y - r0, x - c0) for y, x in cells} == PLUS:
            if sum(1 for cc, _ in comps if cc == col) == 1:
                key = (col, cells)
    if key is None:
        return None
    kc = key[0]
    others = [cc for cc, _ in comps if cc != kc]
    if not others:
        return None
    sc = Counter(others).most_common(1)[0][0]
    odd, even = [], []
    for col, cells in comps:
        if col != sc:
            continue
        rs = [y for y, _ in cells]; cs = [x for _, x in cells]
        h = max(rs) - min(rs) + 1; w = max(cs) - min(cs) + 1
        if h == w and len(cells) == h * w:
            (odd if h % 2 else even).append((min(rs), min(cs), h))
    return bg, kc, key[1], sc, odd, even


KEEP_TESTS = [
    ("keep_if_key_colour_gt_shape_colour", lambda kc, sc, odd, even: kc > sc),
    ("keep_if_more_odd_than_even", lambda kc, sc, odd, even: len(odd) > len(even)),
    ("always_erase", lambda kc, sc, odd, even: False),
    ("always_keep", lambda kc, sc, odd, even: True),
]


def _make(test):
    def fn(g):
        a = _analyse(g)
        out = [list(r) for r in g]
        if a is None:
            return out
        bg, kc, kcells, sc, odd, even = a
        for r0, c0, k in odd:
            out[r0 + k // 2][c0 + k // 2] = kc
        if not test(kc, sc, odd, even):
            for y, x in kcells:
                out[y][x] = bg
        return out
    return fn


def fam(train):
    for i, (name, test) in enumerate(KEEP_TESTS):
        fn = _make(test)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("odd_square_centres_" + name, 1 + i, fn)
        except Exception:
            pass


FAMILIES = [fam]
