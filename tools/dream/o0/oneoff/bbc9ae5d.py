CARD = "bbc9ae5d"
READING = ("The one-row input, a coloured run from the left, becomes a staircase of width/2 rows in "
           "which each row's run is one cell longer than the row above.")


def _solve(g, den):
    if len(g) != 1:
        return None
    row = g[0]
    W = len(row)
    bg = row[-1]
    k = 0
    while k < W and row[k] != bg:
        k += 1
    if k == 0:
        return None
    col = row[0]
    H = W // den
    return [[col if j < min(W, k + i) else bg for j in range(W)] for i in range(H)]


def fam(train):
    for name, cost, den in (("staircase_half_width", 1, 2),):
        fn = (lambda d: (lambda g: _solve(g, d)))(den)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
