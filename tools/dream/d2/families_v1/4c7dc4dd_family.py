"""Family for ARC task 4c7dc4dd -- concept: RAVEN MATRIX (psychometrics; proportional analogy A:B :: C:?).

The noisy sheet carries a 2 x 2 matrix of equal-sized framed panels ("windows").  Exactly one panel
is blank.  The two panels that do NOT share a matrix row/column with the blank one's partner form a
complete example pair; the relation R that turns one of them into the other is found by trying a
small declared library of relations, and the blank panel is filled with R(partner), where the
partner is the panel sharing a matrix row or column with the blank one.  Output = the blank panel's
interior, filled.

Declared relation library (tried in this order; each is exact or rejected):
  negative   photographic negative: empty cells <-> inked cells; ink laid by the panel's own
             colour lattice (uniform, or checkerboard parity -> colour), induced from that panel.
  closure    ray closure: every pair of inked cells that see each other along a row/column
             through empty cells is joined; the ray ink is the colour of the ray end-points
             (cells with exactly one line-of-sight neighbour), induced from that panel.
  stencil    part -> whole: the example pair is (fragment, whole) with fragment inside whole;
             the answer is the whole re-inked by the colour correspondence read off where the
             partner fragment overlaps it.
Everything else (frame size/colour, panel positions, which panel is blank, which pairing of the
matrix holds the relation, colours) is induced from the grid itself.
"""
from collections import Counter


# ------------------------------------------------------------------ window detection
def _runs(g):
    H, W = len(g), len(g[0])
    right = [[1] * W for _ in range(H)]
    down = [[1] * W for _ in range(H)]
    for r in range(H - 1, -1, -1):
        for c in range(W - 1, -1, -1):
            if c + 1 < W and g[r][c + 1] == g[r][c]:
                right[r][c] = right[r][c + 1] + 1
            if r + 1 < H and g[r + 1][c] == g[r][c]:
                down[r][c] = down[r + 1][c] + 1
    return right, down


def _frames(g):
    """All monochrome (non-zero) rectangle borders, h,w >= 3, whose interior holds an empty cell."""
    H, W = len(g), len(g[0])
    right, down = _runs(g)
    zero_pre = [[0] * (W + 1) for _ in range(H + 1)]
    for r in range(H):
        for c in range(W):
            zero_pre[r + 1][c + 1] = (zero_pre[r][c + 1] + zero_pre[r + 1][c] - zero_pre[r][c]
                                      + (g[r][c] == 0))
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == 0:
                continue
            for h in range(3, min(down[r][c], H - r) + 1):
                for w in range(3, min(right[r][c], W - c) + 1):
                    if right[r + h - 1][c] >= w and down[r][c + w - 1] >= h:
                        r0, c0, r1, c1 = r + 1, c + 1, r + h - 1, c + w - 1
                        z = zero_pre[r1][c1] - zero_pre[r0][c1] - zero_pre[r1][c0] + zero_pre[r0][c0]
                        if z > 0:
                            out.append((r, c, h, w))
    return out


def _overlap(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def find_matrix(g):
    """Largest frame size that occurs at least 4 times without overlap -> the 2x2 panel matrix."""
    fr = _frames(g)
    by = {}
    for f in fr:
        by.setdefault((f[2], f[3]), []).append(f)
    for (h, w) in sorted(by, key=lambda s: -s[0] * s[1]):
        chosen = []
        for f in sorted(by[(h, w)]):
            if all(not _overlap(f, x) for x in chosen):
                chosen.append(f)
        if len(chosen) == 4:
            chosen.sort()
            top, bot = sorted(chosen[:2], key=lambda f: f[1]), sorted(chosen[2:], key=lambda f: f[1])
            # sanity: two matrix rows, two matrix columns
            if top[0][0] + h <= bot[0][0] or top[1][0] + h <= bot[1][0]:
                cells = [[top[0], top[1]], [bot[0], bot[1]]]
                return [[[row[f[1] + 1:f[1] + w - 1] for row in g[f[0] + 1:f[0] + h - 1]]
                         for f in mr] for mr in cells]
    return None


# ------------------------------------------------------------------ colour lattice of a panel
def _lattice(p):
    """Ink as a function of cell parity class, induced from the panel's inked cells."""
    cols = {v for row in p for v in row if v}
    if len(cols) == 1:
        c = cols.pop()
        return {0: c, 1: c}
    m = {}
    for i, row in enumerate(p):
        for j, v in enumerate(row):
            if v:
                k = (i + j) % 2
                if m.setdefault(k, v) != v:
                    return None
    return m if len(m) == 2 else None


# ------------------------------------------------------------------ relation library
def negative(p):
    lat = _lattice(p)
    if lat is None:
        return None
    return [[0 if v else lat[(i + j) % 2] for j, v in enumerate(row)] for i, row in enumerate(p)]


def _sight_lines(p):
    """Pairs of inked cells that see each other along a row or column (consecutive inked cells)."""
    H, W = len(p), len(p[0])
    pairs = []
    for i in range(H):
        js = [j for j in range(W) if p[i][j]]
        pairs += [((i, a), (i, b)) for a, b in zip(js, js[1:])]
    for j in range(W):
        is_ = [i for i in range(H) if p[i][j]]
        pairs += [((a, j), (b, j)) for a, b in zip(is_, is_[1:])]
    return pairs


def closure(p):
    pairs = _sight_lines(p)
    deg = Counter()
    for a, b in pairs:
        deg[a] += 1
        deg[b] += 1
    ends = {p[i][j] for (i, j), d in deg.items() if d == 1}
    if len(ends) != 1:
        return None
    ink = ends.pop()
    out = [row[:] for row in p]
    for (i0, j0), (i1, j1) in pairs:
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                if out[i][j] == 0:
                    out[i][j] = ink
    return out


def _stencil_fits(part, whole):
    if part == whole:
        return False
    return all(v == 0 or v == whole[i][j] for i, row in enumerate(part) for j, v in enumerate(row))


def _stencil_apply(q, whole):
    m = {}
    for i, row in enumerate(q):
        for j, v in enumerate(row):
            if v:
                w = whole[i][j]
                if w == 0 or m.setdefault(w, v) != v:
                    return None
    if len(set(m.values())) != len(m):
        return None
    return [[m.get(v, v) for v in row] for row in whole]


RELATIONS = ('negative', 'closure', 'stencil')


def _relate(name, src, dst, q):
    """If relation `name` maps src -> dst, return its image of q, else None."""
    if name == 'stencil':
        return _stencil_apply(q, dst) if _stencil_fits(src, dst) else None
    f = negative if name == 'negative' else closure
    if f(src) != dst:
        return None
    return f(q)


def _empty(p):
    return all(v == 0 for row in p for v in row)


def solve(g, relations=RELATIONS):
    M = find_matrix(g)
    if M is None:
        return None
    blanks = [(a, b) for a in range(2) for b in range(2) if _empty(M[a][b])]
    if len(blanks) != 1:
        return None
    a, b = blanks[0]
    # partner in the same matrix row, example pair = the other matrix row; then the same by columns
    options = [(M[a][1 - b], M[1 - a][b], M[1 - a][1 - b]),   # row-wise analogy
               (M[1 - a][b], M[a][1 - b], M[1 - a][1 - b])]   # column-wise analogy
    for name in relations:
        for q, x, y in options:
            for src, dst in ((x, y), (y, x)):
                r = _relate(name, src, dst, q)
                if r is not None:
                    return r
    return None


# ------------------------------------------------------------------ family
def fam_raven_matrix(train):
    fn = lambda g: solve(g)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("psychometrics:raven_matrix[relations=%s]" % ",".join(RELATIONS), 3, fn)


FAMILIES = (fam_raven_matrix,)
