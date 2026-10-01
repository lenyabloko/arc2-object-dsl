CARD = "8403a5d5"
READING = "From the bottom-row pixel, draw full-height lines of its colour in every second column to the right, and join consecutive lines with a new-colour cap alternating between the top row and the bottom row."

from collections import Counter


def _ink(train):
    inks = set()
    for p in train:
        a = set(v for row in p["input"] for v in row)
        b = set(v for row in p["output"] for v in row)
        inks |= (b - a)
    return inks.pop() if len(inks) == 1 else None


def _make(ink, step):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = Counter(v for row in g for v in row).most_common(1)[0][0]
        cells = [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
        if len(cells) != 1:
            return [row[:] for row in g]
        r0, c0, v = cells[0]
        out = [[bg] * W for _ in range(H)]
        k = 0
        c = c0
        while c < W:
            for r in range(H):
                out[r][c] = v
            g1 = c + step // 2
            if c + step < W + step and g1 < W and step >= 2:
                row = 0 if k % 2 == 0 else H - 1
                out[row][g1] = ink
            k += 1
            c += step
        return out
    return fn


def fam(train):
    ink = _ink(train)
    if ink is None:
        return
    for step in (2, 3, 4):
        fn = _make(ink, step)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("serpent_step%d" % step, step, fn)
        except Exception:
            pass


FAMILIES = [fam]
