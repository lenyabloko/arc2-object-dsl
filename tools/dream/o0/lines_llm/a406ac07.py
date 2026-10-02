"""Line expansion for a406ac07: edge key column x edge key row -> diagonal blocks where the keys agree (test-blind; train pairs only)."""
from collections import Counter

CARD = "a406ac07"
LINE = ("The key column and key row on the grid edge list colours; every cell whose key-column colour equals "
        "its key-row colour is painted that colour, giving one block per colour along the diagonal.")
READING = {
    "generator": "For every cell, look up the colour the edge key column holds in that cell's row and the colour the edge "
                 "key row holds in that cell's column; where the two agree (and are not background) paint the cell that colour.",
    "stop": "One pass over the grid: each cell is painted at most once and nothing outside the key-agreement cells changes "
            "(the key lines themselves are kept, or erased if the training outputs say so).",
    "params": "col_side ∈ {left, right} · row_side ∈ {top, bottom} · keys ∈ {keep, erase}; background = most common input colour; "
              "all chosen by fit to the training pairs (cheapest first).",
    "participants": "key column = an edge column (first or last) with no background cells; key row = an edge row (first or last) "
                    "with no background cells; they meet at a shared corner; the block cells = every cell whose two key colours match.",
    "preconditions": "Output has the input's shape; some edge column and some edge row are fully non-background and every other "
                     "cell of the input is background; the chosen variant reproduces every training pair.",
}


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _keys(g, bg, cs, rs):
    """Return (key column index, key row index) if that edge pair is a valid key layout, else None."""
    H, W = len(g), len(g[0])
    if H < 2 or W < 2:
        return None
    kc = 0 if cs == "left" else W - 1
    kr = 0 if rs == "top" else H - 1
    if any(g[r][kc] == bg for r in range(H)) or any(g[kr][c] == bg for c in range(W)):
        return None
    for r in range(H):
        if r == kr:
            continue
        for c in range(W):
            if c != kc and g[r][c] != bg:
                return None
    return kc, kr


def _make(cs, rs, keys):
    def fn(g):
        g = [list(row) for row in g]
        bg = _bg(g)
        k = _keys(g, bg, cs, rs)
        if k is None:
            return None
        kc, kr = k
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        if keys == "erase":
            for r in range(H):
                out[r][kc] = bg
            for c in range(W):
                out[kr][c] = bg
        for r in range(H):
            if r == kr:
                continue
            a = g[r][kc]
            for c in range(W):
                if c == kc:
                    continue
                if g[kr][c] == a and a != bg:
                    out[r][c] = a
        return out
    return fn


def fam(train):
    if not train:
        return
    for p in train:
        I, O = p["input"], p["output"]
        if len(I) != len(O) or len(I[0]) != len(O[0]):
            return
    cost = 0
    for keys in ("keep", "erase"):
        for cs in ("right", "left"):
            for rs in ("bottom", "top"):
                cost += 1
                fn = _make(cs, rs, keys)
                ok = True
                for p in train:
                    try:
                        res = fn(p["input"])
                    except Exception:
                        res = None
                    if res is None or res != [list(r) for r in p["output"]]:
                        ok = False
                        break
                if ok:
                    yield ("keyagree_%s_%s_%s" % (cs, rs, keys), cost, fn)


FAMILIES = [fam]
