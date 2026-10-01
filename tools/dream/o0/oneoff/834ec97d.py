CARD = "834ec97d"
READING = "The lone pixel drops one row, and every column of the same parity as its column is filled with a new colour from the top down to the pixel's original row."

from collections import Counter


def _ink(train):
    inks = set()
    for p in train:
        a = set(v for row in p["input"] for v in row)
        b = set(v for row in p["output"] for v in row)
        inks |= (b - a)
    return inks.pop() if len(inks) == 1 else None


def _make(ink, shift, step):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = Counter(v for row in g for v in row).most_common(1)[0][0]
        cells = [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
        out = [[bg] * W for _ in range(H)]
        if len(cells) != 1:
            return [row[:] for row in g]
        r0, c0, v = cells[0]
        for r in range(0, min(r0 + shift, H)):
            for c in range(W):
                if (c - c0) % step == 0:
                    out[r][c] = ink
        nr = min(r0 + shift, H - 1)
        out[nr][c0] = v
        return out
    return fn


def fam(train):
    ink = _ink(train)
    if ink is None:
        return
    for shift in (1, 2):
        for step in (2, 1, 3):
            fn = _make(ink, shift, step)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("drop%d_stripe%d" % (shift, step), shift + step, fn)
            except Exception:
                pass


FAMILIES = [fam]
