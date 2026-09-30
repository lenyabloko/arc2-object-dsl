"""Abduced priors (Dream, cycle 21): concepts found by lifting a task into a richer world, each defined in its own
domain and reusable by any task.  One family per concept; every parameter is induced from the training pairs and a
program is kept only if it reproduces every training output (gdsl verifies again).

  line of sight (optics)   the one object whose colour occurs nowhere else is a light source; every object in its
                           line of sight along its rows and/or columns takes its colour.            (source: 4f537728)
  nearest neighbour         the body (the unique largest object) takes the colour of the object nearest to it
  (geometry: proximity)    (Euclidean distance between cells, ties must agree); the other objects stay or vanish.
                                                                                                     (source: 6df30ad6)
  innermost (topology:     pairs of same-colour cells on a line are intervals that nest like brackets; only the
  nesting)                 innermost intervals are joined.                                          (source: 5ad8a7c0)
  dashed border            the one colour segment on the border loop is a dash; the loop is dashed all round
  (graphics)               with dash = gap.                                                          (source: 30f42897)
  fronts meet halfway      two bodies grow toward each other at equal speed through the corridor between them;
  (physics: growth)        each line takes the nearer body's colour, equidistant lines stay empty.   (source: d968ffd4)
  rainbow (optics:         the input is a drop; its spectrum is read on the ray from its centre to one corner; the
  dispersion)              light keeps going along that ray, repeating the spectrum out to the corner of a canvas
                           k times the size, and each colour draws a bow around the drop through its ray point.
                                                                                                     (source: 3979b1a8)
"""
import sys
sys.path.append('/home/claude/work/widen')
from gdsl import H, W, bg_of

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _objects(g, bg):
    """4-connected single-colour components of non-background cells: [(colour, cells)]."""
    h, w = H(g), W(g); seen = set(); out = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or (y, x) in seen: continue
            c = g[y][x]; comp = [(y, x)]; seen.add((y, x)); st = [(y, x)]
            while st:
                a, b = st.pop()
                for dy, dx in N4:
                    q = (a + dy, b + dx)
                    if 0 <= q[0] < h and 0 <= q[1] < w and q not in seen and g[q[0]][q[1]] == c:
                        seen.add(q); comp.append(q); st.append(q)
            out.append((c, comp))
    return out


def _same_shape(train):
    return all((H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)


def _bb(cells):
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


# ------------------------------------------------------------------ line of sight
def _line_of_sight(g, axis):
    bg = bg_of(g); objs = _objects(g, bg)
    count = {}
    for c, _ in objs: count[c] = count.get(c, 0) + 1
    src = [(c, cells) for c, cells in objs if count[c] == 1]
    if len(src) != 1 or len(objs) < 3: return None
    sc, scells = src[0]; r0, c0, r1, c1 = _bb(scells)
    out = [row[:] for row in g]
    for c, cells in objs:
        if cells is scells: continue
        y0, x0, y1, x1 = _bb(cells)
        inrow = not (y1 < r0 or y0 > r1); incol = not (x1 < c0 or x0 > c1)
        if (axis in ('row', 'both') and inrow) or (axis in ('col', 'both') and incol):
            for y, x in cells: out[y][x] = sc
    return out


def fam_line_of_sight(train):
    if not _same_shape(train): return
    for axis in ('both', 'row', 'col'):
        if all(_line_of_sight(p['input'], axis) == p['output'] for p in train):
            yield (f"optics:line-of-sight[{axis}]", 3, lambda g, a=axis: _line_of_sight(g, a))
            return


# ------------------------------------------------------------------ nearest neighbour
def _nearest(g, rest):
    bg = bg_of(g); objs = _objects(g, bg)
    if len(objs) < 2: return None
    m = max(len(c) for _, c in objs)
    big = [o for o in objs if len(o[1]) == m]
    if len(big) != 1: return None
    bc, bcells = big[0]
    best, cols = None, set()
    for c, cells in objs:
        if cells is bcells: continue
        d = min((y - a) ** 2 + (x - b) ** 2 for y, x in cells for a, b in bcells)
        if best is None or d < best: best, cols = d, {c}
        elif d == best: cols.add(c)
    if len(cols) != 1: return None
    col = cols.pop()
    out = [row[:] for row in g] if rest == 'keep' else [[bg] * W(g) for _ in range(H(g))]
    for y, x in bcells: out[y][x] = col
    return out


def fam_nearest_neighbour(train):
    if not _same_shape(train): return
    for rest in ('remove', 'keep'):
        if all(_nearest(p['input'], rest) == p['output'] for p in train):
            yield (f"geometry:nearest-neighbour[{rest}]", 3, lambda g, r=rest: _nearest(g, r))
            return


# ------------------------------------------------------------------ rainbow
def _rainbow(g, k, corner):
    n = H(g)
    if n != W(g) or n < 3 or n % 2 == 0: return None
    # rotate so that the chosen corner is bottom-right, draw, rotate back
    rot = {'br': 0, 'bl': 1, 'tl': 2, 'tr': 3}[corner]
    def r90(a): return [list(r) for r in zip(*a[::-1])]
    x = g
    for _ in range(rot): x = r90(x)
    c = n // 2; spec = [x[i][i] for i in range(c, n)]; p = len(spec); N = k * n
    out = [[None] * N for _ in range(N)]
    for y in range(n):
        for q in range(n): out[y][q] = x[y][q]
    for i in range(n - 1, N):
        col = spec[(i - c) % p]
        if i >= n: out[i][i] = col
        if i + 1 < N:
            for j in range(i + 1): out[j][i + 1] = col; out[i + 1][j] = col
    if any(v is None for row in out for v in row): return None
    for _ in range((4 - rot) % 4): out = r90(out)
    # the drop sits in the corner opposite to the ray's corner; rotating back keeps it there
    return out


def fam_rainbow(train):
    ks = {H(p['output']) // H(p['input']) if H(p['input']) and H(p['output']) % H(p['input']) == 0 else 0 for p in train}
    if len(ks) != 1: return
    k = ks.pop()
    if k < 2 or any(H(p['output']) != W(p['output']) for p in train): return
    for corner in ('br', 'bl', 'tl', 'tr'):
        if all(_rainbow(p['input'], k, corner) == p['output'] for p in train):
            yield (f"optics:rainbow[k{k},{corner}]", 3, lambda g, k=k, c=corner: _rainbow(g, k, c))
            return


FAMILIES = (fam_line_of_sight, fam_nearest_neighbour, fam_rainbow)


# ------------------------------------------------------------------ innermost (topology: nesting)
def _innermost(g, axis):
    """pairs of same-colour cells on a line are intervals; the intervals nest like brackets; only the innermost
    ones (containing no other interval strictly inside their span) are joined by a segment of their colour."""
    x = g if axis == 'row' else [list(r) for r in zip(*g)]
    bg = bg_of(g); ivs = []
    for y, row in enumerate(x):
        cells = [(c, v) for c, v in enumerate(row) if v != bg]
        if not cells: continue
        if len(cells) != 2 or cells[0][1] != cells[1][1]: return None
        ivs.append((y, cells[0][0], cells[1][0], cells[0][1]))
    if len(ivs) < 2: return None
    out = [r[:] for r in x]
    for y, a, b, c in ivs:
        if any(a < a2 and b2 < b for y2, a2, b2, _ in ivs if y2 != y): continue
        for q in range(a + 1, b):
            out[y][q] = c
    return out if axis == 'row' else [list(r) for r in zip(*out)]


def fam_innermost(train):
    if not _same_shape(train): return
    for axis in ('row', 'col'):
        if all(_innermost(p['input'], axis) == p['output'] for p in train):
            yield (f"topology:innermost-interval[{axis}]", 3, lambda g, a=axis: _innermost(g, a))
            return


FAMILIES = FAMILIES + (fam_innermost,)


# ------------------------------------------------------------------ dashed border (graphics: dash = gap)
def _perimeter(h, w):
    return [(0, x) for x in range(w)] + [(y, w - 1) for y in range(1, h)] + \
           [(h - 1, x) for x in range(w - 2, -1, -1)] + [(y, 0) for y in range(h - 2, 0, -1)]


def _dashed_border(g):
    """the one segment of colour on the border loop is a dash; the loop is dashed all round with dash = gap."""
    h, w = H(g), W(g)
    if h < 2 or w < 2: return None
    bg = bg_of(g); loop = _perimeter(h, w); n = len(loop)
    if any(g[y][x] != bg for y in range(1, h - 1) for x in range(1, w - 1)): return None
    on = [g[y][x] != bg for y, x in loop]
    if not any(on) or all(on): return None
    cols = {g[y][x] for (y, x), o in zip(loop, on) if o}
    if len(cols) != 1: return None
    start = next(i for i in range(n) if on[i] and not on[i - 1])
    L = 0
    while on[(start + L) % n]: L += 1
    if sum(on) != L or n % (2 * L): return None
    c = cols.pop(); out = [r[:] for r in g]
    for i, (y, x) in enumerate(loop):
        if (i - start) % (2 * L) < L: out[y][x] = c
    return out


def fam_dashed_border(train):
    if not _same_shape(train): return
    if all(_dashed_border(p['input']) == p['output'] for p in train):
        yield ("graphics:dashed-border", 3, _dashed_border)


FAMILIES = FAMILIES + (fam_dashed_border,)


# ------------------------------------------------------------------ fronts meet halfway (physics: equal-speed growth)
def _meet_halfway(g):
    """two bodies grow toward each other at the same speed through the corridor between them, across the whole
    grid; every line of the corridor takes the colour of the nearer body, lines at equal distance stay empty."""
    bg = bg_of(g); objs = _objects(g, bg)
    if len(objs) != 2 or objs[0][0] == objs[1][0]: return None
    (ca, a), (cb, b) = objs
    ay0, ax0, ay1, ax1 = _bb(a); by0, bx0, by1, bx1 = _bb(b)
    h, w = H(g), W(g); out = [r[:] for r in g]
    if ax1 < bx0 or bx1 < ax0:                       # separated along columns
        if bx1 < ax0: (ca, a, ax0, ax1), (cb, b, bx0, bx1) = (cb, b, bx0, bx1), (ca, a, ax0, ax1)
        for x in range(ax1 + 1, bx0):
            da, db = x - ax1, bx0 - x
            if da == db: continue
            for y in range(h): out[y][x] = ca if da < db else cb
    elif ay1 < by0 or by1 < ay0:                     # separated along rows
        if by1 < ay0: (ca, a, ay0, ay1), (cb, b, by0, by1) = (cb, b, by0, by1), (ca, a, ay0, ay1)
        for y in range(ay1 + 1, by0):
            da, db = y - ay1, by0 - y
            if da == db: continue
            for x in range(w): out[y][x] = ca if da < db else cb
    else:
        return None
    return out


def fam_meet_halfway(train):
    if not _same_shape(train): return
    if all(_meet_halfway(p['input']) == p['output'] for p in train):
        yield ("physics:fronts-meet-halfway", 3, _meet_halfway)


FAMILIES = FAMILIES + (fam_meet_halfway,)
