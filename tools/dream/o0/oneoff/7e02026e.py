CARD = "7e02026e"
READING = ("Every plus shape (a cell and its four orthogonal neighbours) made entirely of "
           "background-colour cells is repainted in the marker colour; overlapping pluses merge.")


def _make(t, p):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        for r in range(1, H - 1):
            for c in range(1, W - 1):
                cells = ((r, c), (r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                if all(g[y][x] == t for y, x in cells):
                    for y, x in cells:
                        out[y][x] = p
        return out
    return fn


def fam(train):
    # induce target colour t and paint colour p from changed cells
    pairs = set()
    for ex in train:
        a, b = ex["input"], ex["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    pairs.add((x, y))
    if len(pairs) != 1:
        return
    t, p = pairs.pop()
    fn = _make(t, p)
    if all(fn(ex["input"]) == ex["output"] for ex in train):
        yield ("plus_fill_%d_to_%d" % (t, p), 1, fn)


FAMILIES = [fam]
