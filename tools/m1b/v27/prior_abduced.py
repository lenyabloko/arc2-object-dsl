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
  drape over a pole        a patterned row is a sheet held up by one pole below it; it hangs as a tent with
  (physics: tent)          45-degree sides, each cell taking the sheet's colour above it.           (source: bae5c565)
  boundary roles           each solid rectangle recoloured by cell role (corner / edge / interior).  (b6afb2da +3)
  reaction (chemistry)     touching cells of two colours react: A + B -> C.                          (source: d90796e8)
  panel dye (arithmetic)   each separated panel takes its single marker's colour + k.                (source: 54d9e175)
  fronts meet halfway      two bodies grow toward each other at equal speed through the corridor between them;
  (physics: growth)        each line takes the nearer body's colour, equidistant lines stay empty.   (source: d968ffd4)
  rainbow (optics:         the input is a drop; its spectrum is read on the ray from its centre to one corner; the
  dispersion)              light keeps going along that ray, repeating the spectrum out to the corner of a canvas
                           k times the size, and each colour draws a bow around the drop through its ray point.
                                                                                                     (source: 3979b1a8)
"""
import sys
sys.path.append('/home/claude/work/widen')
from gdsl import H, W, bg_of as _bg_mode


def bg_of(g):
    """background: black (0) when present (ARC convention), else the most frequent colour."""
    return 0 if any(0 in row for row in g) else _bg_mode(g)

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


# ------------------------------------------------------------------ boundary roles (topology: vertex / edge / interior)
def _role(y, x, y0, x0, y1, x1):
    ey, ex = y in (y0, y1), x in (x0, x1)
    return 'corner' if ey and ex else ('edge' if ey or ex else 'interior')


def _roles(g, act):
    """each solid rectangle (at least 3x3) is recoloured by the topological role of its cells (corner, edge,
    interior); a role's action is 'own' (keep the body's colour), 'bg', or a literal colour."""
    bg = bg_of(g); out = [r[:] for r in g]; hit = False
    for c, cells in _objects(g, bg):
        y0, x0, y1, x1 = _bb(cells)
        if len(cells) != (y1 - y0 + 1) * (x1 - x0 + 1) or y1 - y0 < 2 or x1 - x0 < 2: continue
        for y, x in cells:
            a = act[_role(y, x, y0, x0, y1, x1)]
            out[y][x] = c if a == 'own' else (bg if a == 'bg' else a)
        hit = True
    return out if hit else None


def fam_boundary_roles(train):
    if not _same_shape(train): return
    obs = {'corner': set(), 'edge': set(), 'interior': set()}
    for p in train:
        g, o = p['input'], p['output']; bg = bg_of(g)
        for c, cells in _objects(g, bg):
            y0, x0, y1, x1 = _bb(cells)
            if len(cells) != (y1 - y0 + 1) * (x1 - x0 + 1) or y1 - y0 < 2 or x1 - x0 < 2: continue
            for y, x in cells:
                obs[_role(y, x, y0, x0, y1, x1)].add((c, o[y][x], bg))
    act = {}
    for role, s in obs.items():
        if not s: return
        if all(i == o for i, o, _ in s): act[role] = 'own'
        elif all(o == b for _, o, b in s): act[role] = 'bg'
        elif len({o for _, o, _ in s}) == 1: act[role] = next(iter(s))[1]
        else: return
    if len(set(act.values())) < 2: return
    if all(_roles(p['input'], act) == p['output'] for p in train):
        tag = ','.join(f"{r}={act[r]}" for r in ('corner', 'edge', 'interior'))
        yield (f"topology:boundary-roles[{tag}]", 3, lambda g, a=act: _roles(g, a))


# ------------------------------------------------------------------ reaction on contact (chemistry: A + B -> C)
def _react(g, a, b, c, at):
    """cells of colours a and b that touch (4-neighbours) react: the product c appears in place of `at` (a or b),
    the other reactant disappears; cells without a partner stay."""
    bg = bg_of(g); h, w = H(g), W(g); out = [r[:] for r in g]; hit = False
    for y in range(h):
        for x in range(w):
            if g[y][x] != a: continue
            parts = [(y + dy, x + dx) for dy, dx in N4 if 0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] == b]
            if not parts: continue
            hit = True
            for py, px in parts:
                if at == 'a': out[py][px] = bg
                else: out[py][px] = c
            out[y][x] = c if at == 'a' else bg
    return out if hit else None


def fam_reaction(train):
    if not _same_shape(train): return
    diffs = set()
    for p in train:
        g, o = p['input'], p['output']
        for y in range(H(g)):
            for x in range(W(g)):
                if g[y][x] != o[y][x]: diffs.add((g[y][x], o[y][x]))
    ins = {d[0] for d in diffs}; outs = {d[1] for d in diffs}
    if len(ins) != 2: return
    bg0 = bg_of(train[0]['input'])
    prods = [c for c in outs if c != bg0]
    if len(prods) != 1: return
    c = prods[0]; a, b = sorted(ins)
    for x, y, at in ((a, b, 'a'), (b, a, 'a')):
        if all(_react(p['input'], x, y, c, at) == p['output'] for p in train):
            yield (f"chemistry:reaction[{x}+{y}->{c}]", 3, lambda g, x=x, y=y, c=c: _react(g, x, y, c, 'a'))
            return


# ------------------------------------------------------------------ panel dyed by its marker (colour arithmetic)
def _panels(g):
    """cells split by full rows/columns of one separator colour; returns (sep, list of panels as cell lists)."""
    h, w = H(g), W(g); bg = bg_of(g)
    for sep in sorted({v for row in g for v in row} - {bg}):
        rows = [y for y in range(h) if all(v == sep for v in g[y])]
        cols = [x for x in range(w) if all(g[y][x] == sep for y in range(h))]
        if not rows and not cols: continue
        ys = [-1] + rows + [h]; xs = [-1] + cols + [w]; panels = []
        for i in range(len(ys) - 1):
            for j in range(len(xs) - 1):
                cells = [(y, x) for y in range(ys[i] + 1, ys[i + 1]) for x in range(xs[j] + 1, xs[j + 1])]
                if cells: panels.append(cells)
        if len(panels) >= 2: return sep, panels
    return None, None


def _dye(g, k):
    sep, panels = _panels(g)
    if not panels: return None
    out = [r[:] for r in g]
    for pan in panels:
        vals = {}
        for y, x in pan: vals[g[y][x]] = vals.get(g[y][x], 0) + 1
        if len(vals) != 2: return None
        marker = min(vals, key=lambda v: vals[v])
        if vals[marker] != 1: return None
        for y, x in pan: out[y][x] = (marker + k) % 10
    return out


def fam_panel_dye(train):
    if not _same_shape(train): return
    for k in range(1, 10):
        if all(_dye(p['input'], k) == p['output'] for p in train):
            yield (f"arithmetic:panel-dye[+{k}]", 3, lambda g, k=k: _dye(g, k))
            return


FAMILIES = FAMILIES + (fam_boundary_roles, fam_reaction, fam_panel_dye)


# ------------------------------------------------------------------ drape over a pole (physics: a sheet on a pole = tent)
def _r90(a):
    return [list(r) for r in zip(*a[::-1])]


def _drape_up(g):
    """the patterned top row is a sheet; the single vertical pole below it holds it up; the sheet falls onto the
    pole and hangs as a tent with 45-degree sides (cell (y, x) under the tent takes the sheet's colour at column x);
    the pole stays, the sheet's old row takes the surrounding colour."""
    h, w = H(g), W(g)
    if h < 4: return None
    body = [v for row in g[1:] for v in row]
    bg = max(set(body), key=body.count)
    pole = [(y, x) for y in range(1, h) for x in range(w) if g[y][x] != bg]
    if not pole: return None
    xs = {x for _, x in pole}
    if len(xs) != 1: return None
    px = xs.pop(); ys = sorted(y for y, _ in pole)
    if ys != list(range(ys[0], h)) or len({g[y][px] for y in ys}) != 1: return None
    top = ys[0]; sheet = g[0][:]
    if sum(v != bg for v in sheet) < 2: return None
    out = [[bg] * w for _ in range(h)]
    for y in ys: out[y][px] = g[y][px]
    for y in range(top + 1, h):
        for x in range(w):
            if x != px and abs(x - px) <= y - top: out[y][x] = sheet[x]
    return out


def _drape(g, rot):
    x = g
    for _ in range(rot): x = _r90(x)
    o = _drape_up(x)
    if o is None: return None
    for _ in range((4 - rot) % 4): o = _r90(o)
    return o


def fam_drape(train):
    if not _same_shape(train): return
    for rot in range(4):
        if all(_drape(p['input'], rot) == p['output'] for p in train):
            yield (f"physics:drape-over-pole[rot{rot}]", 3, lambda g, r=rot: _drape(g, r))
            return


FAMILIES = FAMILIES + (fam_drape,)


# ------------------------------------------------------------------ pour (fluids: a liquid fills a sealed cup, else floods the floor)
def _pour(g):
    """the single drop of liquid (a colour occurring once, in the top part) is poured straight down; on a floor it
    spreads sideways; wherever it can fall further it drains; a level bounded by walls on both sides with no hole
    below is filled, and the cup fills level by level up to its brim; liquid that reaches the bottom of the world
    spreads over the bottom row.  The drop's own cell is emptied."""
    bg = bg_of(g); h, w = H(g), W(g)
    cnt = {}
    for row in g:
        for v in row: cnt[v] = cnt.get(v, 0) + 1
    drops = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg and cnt[g[y][x]] == 1]
    if len(drops) != 1: return None
    (dy, dx) = drops[0]; L = g[dy][dx]
    grid = [r[:] for r in g]; grid[dy][dx] = bg
    y, x = dy, dx
    for _ in range(h * w):
        while y + 1 < h and grid[y + 1][x] == bg: y += 1          # fall
        if y == h - 1:                                           # bottom of the world
            for q in range(w): grid[h - 1][q] = L
            return grid
        lvl = [x]; q = x                                         # spread on this level
        while q - 1 >= 0 and grid[y][q - 1] == bg: q -= 1; lvl.append(q)
        left_wall = q - 1 >= 0
        q = x
        while q + 1 < w and grid[y][q + 1] == bg: q += 1; lvl.append(q)
        right_wall = q + 1 < w
        holes = sorted(c for c in lvl if y + 1 < h and grid[y + 1][c] == bg)
        if holes:                                                # drains through the first hole
            x = holes[0]; continue
        if not (left_wall and right_wall): return None           # spills over an edge: not a cup
        # sealed level: fill it and the levels above while bounded by walls
        yy = y; row_cells = sorted(lvl)
        while yy >= 0:
            a, b = row_cells[0], row_cells[-1]
            if a - 1 < 0 or b + 1 >= w or grid[yy][a - 1] == bg or grid[yy][b + 1] == bg: break
            if any(grid[yy][c] != bg for c in range(a, b + 1)): break
            for c in range(a, b + 1): grid[yy][c] = L
            yy -= 1
        return grid
    return None


def fam_pour(train):
    if not _same_shape(train): return
    if all(_pour(p['input']) == p['output'] for p in train):
        yield ("fluids:pour", 3, _pour)


FAMILIES = FAMILIES + (fam_pour,)


# ------------------------------------------------------------------ bridge the gaps (masonry: a stone rests on two stones)
def _bridge_down(g, c2):
    """a row of stones (colour c1) with gaps; on each next layer (two rows further on) a stone is laid over every gap
    that is flanked by stones on both sides; layers alternate colours c2, c1, c2, ... until no gap is flanked."""
    h, w = H(g), W(g); bg = bg_of(g)
    rows = [y for y in range(h) if any(v != bg for v in g[y])]
    if len(rows) != 1: return None
    y0 = rows[0]; cols = {v for v in g[y0] if v != bg}
    if len(cols) != 1: return None
    c1 = cols.pop()
    if c2 == c1 or c2 == bg: return None
    out = [r[:] for r in g]; prev = [v != bg for v in g[y0]]; y = y0; gen = 1
    while True:
        new = [0 < x < w - 1 and prev[x - 1] and prev[x + 1] and not prev[x] for x in range(w)]
        y += 2
        if not any(new) or y >= h: break
        for x in range(w):
            if new[x]: out[y][x] = c2 if gen % 2 else c1
        prev = new; gen += 1
    return out


def _bridge(g, c2, rot):
    x = g
    for _ in range(rot): x = _r90(x)
    o = _bridge_down(x, c2)
    if o is None: return None
    for _ in range((4 - rot) % 4): o = _r90(o)
    return o


def fam_bridge(train):
    if not _same_shape(train): return
    news = set()
    for p in train:
        news |= {v for row in p['output'] for v in row} - {v for row in p['input'] for v in row}
    if len(news) != 1: return
    c2 = news.pop()
    for rot in range(4):
        if all(_bridge(p['input'], c2, rot) == p['output'] for p in train):
            yield (f"masonry:bridge-gaps[c{c2},rot{rot}]", 3, lambda g, c=c2, r=rot: _bridge(g, c, r))
            return


FAMILIES = FAMILIES + (fam_bridge,)


# ------------------------------------------------------------------ crosshair (geometry: four arrows point at one target)
def _crosshair(g, c2, gap):
    """a cell at which four bars point from the four sides (each bar at least two cells long, lying on the cell's
    row or column, separated from it by exactly `gap` empty cells) is the target and takes colour c2."""
    h, w = H(g), W(g); bg = bg_of(g); out = [r[:] for r in g]; hit = False
    for y in range(h):
        for x in range(w):
            if g[y][x] != bg: continue
            ok = True; col = None
            for dy, dx in N4:
                ys = [y + dy * k for k in range(1, gap + 3)]; xs = [x + dx * k for k in range(1, gap + 3)]
                if not all(0 <= a < h and 0 <= b < w for a, b in zip(ys, xs)): ok = False; break
                cells = [g[a][b] for a, b in zip(ys, xs)]
                gapc, bar = cells[:gap], cells[gap:]
                if any(v != bg for v in gapc) or bar[0] == bg or bar[0] != bar[1]: ok = False; break
                if col is None: col = bar[0]
                elif bar[0] != col: ok = False; break
            if ok: out[y][x] = c2; hit = True
    return out if hit else None


def fam_crosshair(train):
    if not _same_shape(train): return
    news = set()
    for p in train:
        news |= {v for row in p['output'] for v in row} - {v for row in p['input'] for v in row}
    if len(news) != 1: return
    c2 = news.pop()
    for gap in (1, 0, 2):
        if all(_crosshair(p['input'], c2, gap) == p['output'] for p in train):
            yield (f"geometry:crosshair[c{c2},gap{gap}]", 3, lambda g, c=c2, k=gap: _crosshair(g, c, k))
            return


FAMILIES = FAMILIES + (fam_crosshair,)
