"""Family for ARC task 20a9e565 -- concept: CROP MARKS (graphics / print production) over an EXTRAPOLATED progression.

Two L-shaped corner brackets of one colour are printer's crop marks: they frame a rectangle of the page that has
not been drawn yet.  The drawing is a progression of 'units' (maximal runs of non-empty lines along one axis)
that grow term by term.  The output is the framed rectangle after the progression has been continued (extrapolated)
far enough to reach it.

Extrapolation of the progression (all parameters induced per input from the observed terms, no stored data):
  * unit placement / size: along-axis length, gap, cross-axis lo/hi each continued by a finite-difference rule whose
    first differences are periodic with the smallest period p in {1,2,3};
  * unit content: term k+P is rebuilt from term k (lag P in {1,2,3}); cells inside term k are copied with a
    colour map s_int, the grown margin is filled with a colour map s_front by one of two growth modes:
      'lines'  - every line of the term (and every new line) extends its own history; the grown ends repeat the
                 last cells of that line in term k (stretch / tiling of the growing edge);
      'halves' - term k is split at its (constant) cross-axis centre and each half is pushed outward by the growth
                 (the outer layer travels with the growing edge; union with the copied interior);
    colour maps and the (P, mode) pair are the simplest ones that reproduce every observed term k+P from term k
    (k >= 1; the seed term 0 is used only if it agrees).
Axis and direction: the frame (right/left/down/up) in which the crop window lies beyond the last unit.
"""
from collections import Counter

LAGS = (1, 2, 3)            # declared finite domain for the content lag
MODES = ('lines', 'halves')  # declared finite domain for the growth mode
DIFF_PERIODS = (1, 2, 3)    # declared finite domain for periodic first differences


# ----------------------------------------------------------------------------------------------- grid utilities
def _T(g): return [list(r) for r in zip(*g)]
def _fl(g): return [r[::-1] for r in g]
def _fu(g): return [r[:] for r in g[::-1]]


FRAMES = (  # name, forward, inverse   (normalised: units progress along columns, left -> right)
    ('right', lambda g: [r[:] for r in g], lambda g: [r[:] for r in g]),
    ('left', _fl, _fl),
    ('down', _T, _T),
    ('up', lambda g: _T(_fu(g)), lambda g: _fu(_T(g))),
)


def _components(grid, colour):
    H, W = len(grid), len(grid[0])
    seen, comps = set(), []
    for r in range(H):
        for c in range(W):
            if grid[r][c] == colour and (r, c) not in seen:
                stack, comp = [(r, c)], []
                seen.add((r, c))
                while stack:
                    y, x = stack.pop()
                    comp.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] == colour and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
                comps.append(comp)
    return comps


def _crop_marks(grid, mc):
    """Two 3-cell L brackets at opposite corners -> window (r0, r1, c0, c1) or None."""
    comps = _components(grid, mc)
    if len(comps) != 2:
        return None
    marks = []
    for comp in comps:
        if len(comp) != 3:
            return None
        r0 = min(r for r, _ in comp)
        c0 = min(c for _, c in comp)
        box = {(r0 + i, c0 + j) for i in (0, 1) for j in (0, 1)}
        if not set(comp) <= box:
            return None
        (mr, mcol), = box - set(comp)
        corner = (2 * r0 + 1 - mr, 2 * c0 + 1 - mcol)       # the bracket's elbow
        marks.append((corner, (mr - corner[0], mcol - corner[1])))  # inward direction
    (p, d), (q, e) = marks
    if (d[0] + e[0], d[1] + e[1]) != (0, 0):
        return None
    if (q[0] - p[0]) * d[0] < 0 or (q[1] - p[1]) * d[1] < 0:
        return None
    return min(p[0], q[0]), max(p[0], q[0]), min(p[1], q[1]), max(p[1], q[1])


# ----------------------------------------------------------------------------------------------- progression
def _line_ext(cells, L, lo, hi, bg):
    ext = []
    for x in range(L):
        ys = [y for y in range(lo, hi + 1) if cells.get((x, y), bg) != bg]
        ext.append((min(ys), max(ys)) if ys else None)
    return ext


def _units(g, bg):
    H, W = len(g), len(g[0])
    full = [any(g[r][c] != bg for r in range(H)) for c in range(W)]
    units, c = [], 0
    while c < W:
        if not full[c]:
            c += 1
            continue
        a = c
        while c < W and full[c]:
            c += 1
        b = c - 1
        ys = [r for r in range(H) if any(g[r][x] != bg for x in range(a, b + 1))]
        lo, hi = min(ys), max(ys)
        cells = {(x - a, y): g[y][x] for x in range(a, b + 1) for y in range(lo, hi + 1)}
        units.append({'a': a, 'L': b - a + 1, 'lo': lo, 'hi': hi, 'cells': cells,
                      'ext': _line_ext(cells, b - a + 1, lo, hi, bg)})
    return units


def _next(seq):
    """Continue an integer sequence whose first differences are periodic (smallest period in DIFF_PERIODS)."""
    if len(seq) == 1:
        return seq[0]
    d = [y - x for x, y in zip(seq, seq[1:])]
    for p in DIFF_PERIODS:
        if (p == 1 or len(d) >= p + 1) and all(d[i] == d[i + p] for i in range(len(d) - p)):
            return seq[-1] + d[-p]
    return seq[-1] + d[-1]


def _sources(src, tgt, mode, bg):
    """For every cell of the target box: list of (kind, source colour) contributions, or None (unknown)."""
    L, lo, hi = tgt['L'], tgt['lo'], tgt['hi']
    dL, dlo, dhi = L - src['L'], src['lo'] - lo, hi - src['hi']
    cells = src['cells']
    out = {}
    if mode == 'lines':            # every line (along-axis position) grows at its own ends by repeating them
        for x in range(L):
            for y in range(lo, hi + 1):
                out[(x, y)] = [('i', bg)]
            te = tgt['ext'][x]
            xs = x if x < src['L'] else x - dL
            if te is None:
                continue
            se = src['ext'][xs] if 0 <= xs < src['L'] else None
            for y in range(te[0], te[1] + 1):
                if se is None:
                    out[(x, y)] = None
                    continue
                if se[0] <= y <= se[1]:
                    ys, kind = y, ('i' if x < src['L'] else 'f')
                elif y > se[1]:
                    ys, kind = y - (te[1] - se[1]), 'f'
                else:
                    ys, kind = y + (se[0] - te[0]), 'f'
                out[(x, y)] = [(kind, cells[(xs, ys)])] if se[0] <= ys <= se[1] else None
        return out
    # 'halves': constant cross-axis centre required
    if src['lo'] + src['hi'] != lo + hi or min(dL, dlo, dhi) < 0:
        return None
    c2 = src['lo'] + src['hi']
    for x in range(L):
        for y in range(lo, hi + 1):
            out[(x, y)] = []
    for (xs, ys), v in cells.items():
        if v != bg:
            out[(xs, ys)].append(('i', v))
    for (xs, ys), v in cells.items():
        if v == bg:
            continue
        if 2 * ys >= c2 and (xs + dL, ys + dhi) in out:
            out[(xs + dL, ys + dhi)].append(('f', v))
        if 2 * ys <= c2 and (xs + dL, ys - dlo) in out:
            out[(xs + dL, ys - dlo)].append(('f', v))
    return out


def _check(src, tgt, mode, maps, bg):
    cand = _sources(src, tgt, mode, bg)
    if cand is None:
        return False
    for pos, cs in cand.items():
        if cs is None:
            continue
        actual = tgt['cells'].get(pos, bg)
        coloured = [(k, v) for k, v in cs if v != bg]
        if not coloured:
            if actual != bg:
                return False
            continue
        if actual == bg:
            return False
        for k, v in coloured:
            if maps[k].setdefault(v, actual) != actual:
                return False
    return True


def _fit(units, bg):
    n = len(units)
    for P in LAGS:
        for mode in MODES:
            ks = range(1, n - P)
            if not ks:
                continue
            maps = {'i': {}, 'f': {}}
            if not all(_check(units[k], units[k + P], mode, maps, bg) for k in ks):
                continue
            trial = {'i': dict(maps['i']), 'f': dict(maps['f'])}
            if _check(units[0], units[P], mode, trial, bg):
                maps = trial
            return P, mode, maps
    return None


def _apply(m, v, palette):
    if v in m:
        return m[v]
    free_keys = [c for c in palette if c not in m]
    free_vals = [c for c in palette if c not in m.values()]
    if len(set(m.values())) == len(m) and len(free_keys) == 1 and len(free_vals) == 1:
        return free_vals[0]
    return v


def _render(src, tgt, mode, maps, bg, palette):
    cand = _sources(src, tgt, mode, bg)
    cells = {}
    for pos, cs in cand.items():
        val = bg
        for k, v in cs or ():
            if v != bg:
                val = _apply(maps[k], v, palette)
                break
        cells[pos] = val
    tgt = dict(tgt, cells=cells)
    tgt['ext'] = _line_ext(cells, tgt['L'], tgt['lo'], tgt['hi'], bg)
    return tgt


# ----------------------------------------------------------------------------------------------- solver
def _solve(grid, mc):
    win = _crop_marks(grid, mc)
    if win is None:
        return None
    bg = Counter(v for row in grid for v in row).most_common(1)[0][0]
    H, W = len(grid), len(grid[0])
    clean = [[bg if v == mc else v for v in row] for row in grid]
    mask = [[1 if win[0] <= r <= win[1] and win[2] <= c <= win[3] else 0 for c in range(W)] for r in range(H)]
    for _, fwd, inv in FRAMES:
        g, m = fwd(clean), fwd(mask)
        rows = [r for r in range(len(m)) if any(m[r])]
        cols = [c for c in range(len(m[0])) if any(m[r][c] for r in range(len(m)))]
        wr0, wr1, wc0, wc1 = rows[0], rows[-1], cols[0], cols[-1]
        units = _units(g, bg)
        if len(units) < 3 or wc1 <= units[-1]['a'] + units[-1]['L'] - 1 or wc0 <= units[0]['a']:
            continue
        fit = _fit(units, bg)
        if fit is None:
            continue
        P, mode, maps = fit
        palette = sorted({v for u in units for v in u['cells'].values()} - {bg})
        seq = {k: [u[k] for u in units] for k in ('a', 'L', 'lo', 'hi')}
        canvas = {(y, x): g[y][x] for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != bg}
        for _ in range(60):
            gaps = [seq['a'][i + 1] - seq['a'][i] - seq['L'][i] for i in range(len(seq['a']) - 1)]
            na = seq['a'][-1] + seq['L'][-1] + _next(gaps)
            nL, nlo, nhi = _next(seq['L']), _next(seq['lo']), _next(seq['hi'])
            src = units[len(units) - P]
            ext = None
            if mode == 'lines' and nL >= 1:     # each line's own extent continues its own history
                ext = []
                for x in range(nL):
                    hist = [u['ext'][x] for u in units if x < u['L'] and u['ext'][x]]
                    if not hist:
                        xs = x - (nL - src['L'])
                        hist = [u['ext'][xs] for u in units if 0 <= xs < u['L'] and u['ext'][xs]]
                    ext.append((_next([e[0] for e in hist]), _next([e[1] for e in hist])) if hist else None)
                spans = [e for e in ext if e]
                if not spans:
                    break
                nlo, nhi = min(e[0] for e in spans), max(e[1] for e in spans)
            if na > wc1 or nL < 1 or nhi < nlo:
                break
            new = _render(src, {'L': nL, 'lo': nlo, 'hi': nhi, 'ext': ext}, mode, maps, bg, palette)
            new['a'] = na
            units.append(new)
            for k in seq:
                seq[k].append(new[k])
            for (x, y), v in new['cells'].items():
                if v != bg:
                    canvas[(y, na + x)] = v
                else:
                    canvas.pop((y, na + x), None)
        crop = [[canvas.get((y, x), bg) for x in range(wc0, wc1 + 1)] for y in range(wr0, wr1 + 1)]
        return inv(crop)
    return None


def fam_crop_marks(train):
    colours = sorted({v for p in train for row in p['input'] for v in row})
    for mc in colours:
        if not all(_crop_marks(p['input'], mc) for p in train):
            continue

        def fn(g, mc=mc):
            return _solve(g, mc)
        try:
            ok = all(fn(p['input']) == p['output'] for p in train)
        except Exception:
            ok = False
        if ok:
            yield (f"graphics:crop_marks[mark={mc},extrapolate=periodic-diff+lag{{1,2,3}}x{{lines,halves}}]", 3, fn)
            return


FAMILIES = (fam_crop_marks,)
