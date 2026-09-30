"""Family for e376de54 -- typography:justification.

Concept: a block of parallel strokes is like a paragraph set flush against one margin with a ragged
other margin.  Justifying it keeps the flush margin (the ends of the strokes that already lie on a
common perpendicular baseline) and sets every stroke to one common measure, the measure being read
off a reference stroke (default: the central stroke of the block).  Strokes that are too long are
cut back, strokes that are too short are extended, always along their own direction.

Everything is induced per grid: background = most frequent colour; stroke direction = the one of the
four grid axes (horizontal, vertical, diagonal, anti-diagonal) whose maximal same-colour runs
partition the foreground into the fewest strokes; flush margin = the end whose projections on the
stroke direction coincide.  Only the measure selector and the margin rule are chosen from small
finite domains, fitted on the training pairs.
"""
from collections import Counter

DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))          # the four grid axes a stroke can follow
MEASURES = ('central', 'median', 'mode', 'max', 'min')  # where the common measure comes from
MARGINS = ('flush', 'head', 'tail')               # which end stays fixed


def _background(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _runs(g, bg, d):
    """Maximal same-colour runs of foreground cells along direction d, each as (colour, [cells])."""
    H, W = len(g), len(g[0])
    dr, dc = d
    runs = []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == bg:
                continue
            pr, pc = r - dr, c - dc
            if 0 <= pr < H and 0 <= pc < W and g[pr][pc] == v:
                continue                          # not the start of a run
            cells = []
            rr, cc = r, c
            while 0 <= rr < H and 0 <= cc < W and g[rr][cc] == v:
                cells.append((rr, cc))
                rr += dr
                cc += dc
            runs.append((v, cells))
    return runs


def _strokes(g, bg):
    """Choose the axis giving the fewest (hence longest) strokes."""
    best = None
    for d in DIRS:
        rs = _runs(g, bg, d)
        if best is None or len(rs) < len(best[1]):
            best = (d, rs)
    return best


def _measure(strokes, d, how):
    lens = [len(cells) for _, cells in strokes]
    if not lens:
        return None
    if how == 'max':
        return max(lens)
    if how == 'min':
        return min(lens)
    if how == 'median':
        s = sorted(lens)
        return s[len(s) // 2] if len(s) % 2 else None
    if how == 'mode':
        cnt = Counter(lens).most_common()
        if len(cnt) > 1 and cnt[0][1] == cnt[1][1]:
            return None
        return cnt[0][0]
    if how == 'central':
        # order strokes across the block (projection on the perpendicular axis) and take the middle one
        pr, pc = -d[1], d[0]
        order = sorted(strokes, key=lambda s: sum(r * pr + c * pc for r, c in s[1]) / len(s[1]))
        if len(order) % 2 == 0:
            return None
        return len(order[len(order) // 2][1])
    return None


def _justify(g, how, margin):
    bg = _background(g)
    d, strokes = _strokes(g, bg)
    if not strokes:
        return [row[:] for row in g]
    L = _measure(strokes, d, how)
    if L is None:
        return None
    H, W = len(g), len(g[0])
    proj = lambda p: p[0] * d[0] + p[1] * d[1]
    heads = {proj(cells[0]) for _, cells in strokes}
    tails = {proj(cells[-1]) for _, cells in strokes}
    if margin == 'flush':
        if len(heads) == 1:
            side = 'head'
        elif len(tails) == 1:
            side = 'tail'
        else:
            return None                           # no common margin -> concept does not apply
    else:
        side = margin
    out = [row[:] for row in g]
    for _, cells in strokes:
        for r, c in cells:
            out[r][c] = bg
    for v, cells in strokes:
        if side == 'head':
            (ar, ac), (ur, uc) = cells[0], d
        else:
            (ar, ac), (ur, uc) = cells[-1], (-d[0], -d[1])
        for k in range(L):
            r, c = ar + k * ur, ac + k * uc
            if 0 <= r < H and 0 <= c < W:
                out[r][c] = v
    return out


def fam_justification(train):
    for margin in MARGINS:
        for how in MEASURES:
            fn = (lambda how, margin: (lambda g: _justify(g, how, margin)))(how, margin)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("typography:justification[measure=%s,margin=%s]" % (how, margin), 3, fn)
                return


FAMILIES = (fam_justification,)
