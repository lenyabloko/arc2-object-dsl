CARD = "28e73c20"
READING = "Draw a clockwise square spiral of the output colour starting at the top-left corner, leaving a one-cell gap between successive turns."


def _spiral(h, w, c, bg):
    g = [[bg] * w for _ in range(h)]
    dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    r, q, d = 0, 0, 0
    g[r][q] = c

    def can(r, q, d):
        dr, dq = dirs[d]
        nr, nq = r + dr, q + dq
        if not (0 <= nr < h and 0 <= nq < w) or g[nr][nq] == c:
            return False
        ar, aq = nr + dr, nq + dq
        if 0 <= ar < h and 0 <= aq < w and g[ar][aq] == c:
            return False
        return True

    turns = 0
    while True:
        if can(r, q, d):
            r, q = r + dirs[d][0], q + dirs[d][1]
            g[r][q] = c
            turns = 0
        else:
            d = (d + 1) % 4
            turns += 1
            if turns > 1:
                break
    return g


def fam(train):
    cols = set()
    bgs = set()
    for p in train:
        for row in p['output']:
            cols.update(row)
        for row in p['input']:
            bgs.update(row)
    if len(bgs) != 1:
        return
    bg = bgs.pop()
    cols.discard(bg)
    if len(cols) != 1:
        return
    c = cols.pop()

    def f(g):
        return _spiral(len(g), len(g[0]), c, bg)
    if all(f(p['input']) == p['output'] for p in train):
        yield ('spiral', 1, f)


FAMILIES = [fam]
