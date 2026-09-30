"""ray.orthogonal_directed: seed cells emit axis-aligned half-rays whose direction is given by an
induced rule, painting the seed colour over background.

Seeds:   singleton cells (4-conn, by colour)  |  the odd (minority) cell of a multi-colour object.
Targets: a role, resolved per grid: 'big' = any cell of a non-singleton object,
         'bigsame' = non-singleton object of the seed's own colour, or one induced colour.
Direction rules (induced per seed colour from the training diffs, or uniform):
  toward  - every axis direction whose first non-bg cell is a target; paint up to contact
  away    - the opposite of each 'toward' direction; paint to the edge / first obstacle
  edges   - toward the nearest edge on each axis (ties -> no ray on that axis)
  through - odd cell: along the axis pointing from the odd cell into its object; the ray starts
            after the object and runs to the edge
Optional pre-step (only when outputs are smaller): crop to the rectangle bounded by the two
full rows and two full columns (lines with no background cell)."""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from gdsl import H, W, bg_of, objects, bbox

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _walk(g, bg, y, x, dy, dx, clear=None):
    """Cells from (y,x) exclusive in direction until the first non-bg cell; returns (path, hit).
    clear(cell) -> True marks a non-bg cell the ray passes over."""
    path = []; yy, xx = y + dy, x + dx
    while 0 <= yy < H(g) and 0 <= xx < W(g):
        if g[yy][xx] != bg and not (clear and clear((yy, xx))): return path, (yy, xx)
        path.append((yy, xx)); yy += dy; xx += dx
    return path, None


def _analyse(g):
    bg = bg_of(g)
    obs = objects(g, bg, False, True)
    size = {}
    for ob in obs:
        for c in ob: size[c] = len(ob)
    seeds = [ob[0] for ob in obs if len(ob) == 1]
    big = {}
    for ob in obs:
        c = g[ob[0][0]][ob[0][1]]
        if len(ob) > 1 and len(ob) > len(big.get(c, ())): big[c] = ob
    main = {cell for ob in big.values() for cell in ob}
    size['main'] = main
    size['selfseeds'] = [(y, x) for y in range(H(g)) for x in range(W(g))
                         if g[y][x] != bg and g[y][x] in big and (y, x) not in main]
    return bg, size, seeds


def _target(role, g, size, cell, seedcol):
    y, x = cell
    if role == 'big': return size.get(cell, 0) > 1
    if role == 'bigsame': return size.get(cell, 0) > 1 and g[y][x] == seedcol
    if role == 'mainself': return cell in size['main'] and g[y][x] == seedcol
    return g[y][x] == role


def _rays_cell(g, bg, size, y, x, rule, role):
    """Painted cells for one singleton seed under rule."""
    c = g[y][x]; out = []
    clear = (lambda cl: g[cl[0]][cl[1]] == c and cl not in size['main']) if role == 'mainself' else None
    if rule == 'edges':
        h, w = H(g), W(g)
        for a, b, d1, d2 in ((y, h - 1 - y, (-1, 0), (1, 0)), (x, w - 1 - x, (0, -1), (0, 1))):
            if a == b: continue
            d = d1 if a < b else d2
            out += _walk(g, bg, y, x, *d)[0]
        return out
    for dy, dx in DIRS:
        path, hit = _walk(g, bg, y, x, dy, dx, clear)
        if hit is None or not _target(role, g, size, hit, c): continue
        if rule == 'toward': out += path
        else: out += _walk(g, bg, y, x, -dy, -dx, clear)[0]
    return out


def _odd_rays(g, away=False):
    """Odd cell of each multi-colour object emits a ray through its object to the edge."""
    bg = bg_of(g); res = []
    for ob in objects(g, bg, True, False):
        cols = {}
        for y, x in ob: cols.setdefault(g[y][x], []).append((y, x))
        if len(cols) != 2: continue
        odd = min(cols.values(), key=len)
        if len(odd) != 1 or len(ob) < 3: continue
        (y, x), = odd
        cy = sum(a for a, _ in ob) / len(ob); cx = sum(b for _, b in ob) / len(ob)
        ddy, ddx = cy - y, cx - x
        if abs(ddy) == abs(ddx): continue
        d = ((1 if ddy > 0 else -1), 0) if abs(ddy) > abs(ddx) else (0, (1 if ddx > 0 else -1))
        if away: d = (-d[0], -d[1])
        obset = set(ob); yy, xx = y, x
        while (yy, xx) in obset: yy += d[0]; xx += d[1]
        while 0 <= yy < H(g) and 0 <= xx < W(g) and g[yy][xx] == bg:
            res.append((yy, xx, g[y][x])); yy += d[0]; xx += d[1]
    return res


def _paint_seeds(g, rules, role):
    """rules: dict colour->rule, or a str applied uniformly."""
    bg, size, seeds = _analyse(g)
    if role == 'mainself': seeds = size['selfseeds']
    out = [r[:] for r in g]; n = 0
    for y, x in seeds:
        c = g[y][x]
        if role not in ('big', 'bigsame', 'mainself') and c == role: continue
        r = rules if isinstance(rules, str) else rules.get(c, None if c in rules.get('_seen', ()) else '?')
        if r == '?': return None                    # unseen seed colour under per-colour rules
        if r is None: continue
        for yy, xx in _rays_cell(g, bg, size, y, x, r, role):
            out[yy][xx] = c; n += 1
    return out if n else None


def _frame_crop(g):
    bg = bg_of(g)
    rows = [y for y in range(H(g)) if all(v != bg for v in g[y])]
    cols = [x for x in range(W(g)) if all(g[y][x] != bg for y in range(H(g)))]
    if len(rows) != 2 or len(cols) != 2: return None
    return [r[cols[0]:cols[1] + 1] for r in g[rows[0]:rows[1] + 1]]


def _induce(pairs, role, rules=('toward', 'away', 'edges')):
    """Per seed colour, the rule that paints only correct changed cells and explains most of them."""
    stats = {}
    for i, o in pairs:
        bg, size, seeds = _analyse(i)
        if role == 'mainself': seeds = size['selfseeds']
        for y, x in seeds:
            c = i[y][x]
            if role not in ('big', 'bigsame', 'mainself') and c == role: continue
            s = stats.setdefault(c, {r: [True, 0] for r in rules})
            for r in rules:
                for yy, xx in _rays_cell(i, bg, size, y, x, r, role):
                    if o[yy][xx] == c: s[r][1] += 1
                    else: s[r][0] = False
    res = {}
    for c, s in stats.items():
        ok = [(v[1], r) for r, v in s.items() if v[0] and v[1] > 0]
        res[c] = max(ok)[1] if ok else None
    return res


def fam_directed_rays(train):
    i0, o0 = train[0]['input'], train[0]['output']
    same = (H(i0), W(i0)) == (H(o0), W(o0))
    pre = None
    if not same:
        c0 = _frame_crop(i0)
        if c0 is None or (H(c0), W(c0)) != (H(o0), W(o0)): return
        pre = _frame_crop
    pairs = []
    for p in train:
        i = pre(p['input']) if pre else p['input']
        if i is None or (H(i), W(i)) != (H(p['output']), W(p['output'])): return
        # rays only add colour onto background
        bg = bg_of(i)
        if pre is None and any(i[y][x] != bg and i[y][x] != p['output'][y][x] for y in range(H(i)) for x in range(W(i))): return
        pairs.append((i, p['output']))
    wrap = (lambda f: (lambda g: (lambda c: f(c) if c is not None else None)(pre(g)))) if pre else (lambda f: f)
    tag = 'frame-crop>' if pre else ''
    # colours present in every input (candidate explicit target colours)
    common = None
    for i, _ in pairs:
        cs = {v for r in i for v in r} - {bg_of(i)}
        common = cs if common is None else common & cs
    roles = ['big', 'bigsame', 'mainself'] + sorted(common or ())
    seen = set()
    for role in roles:
        rules = _induce(pairs, role)
        used = {r for r in rules.values() if r}
        if not used: continue
        if len(used) == 1:
            r = used.pop(); key = (r, role if r != 'edges' else '')
            if key in seen: continue
            seen.add(key)
            yield (f"{tag}ray:{r}[target={role}]" if r != 'edges' else f"{tag}ray:edges", 4,
                   wrap(lambda g, r=r, role=role: _paint_seeds(g, r, role)))
        else:
            rr = dict(rules); rr['_seen'] = set(rules)
            yield (f"{tag}ray:per-colour{sorted((k, v) for k, v in rules.items() if v)}[target={role}]", 5,
                   wrap(lambda g, rr=rr, role=role: _paint_seeds(g, rr, role)))
    if pre is None:
        for away in (False, True):
            def odd(g, away=away):
                res = _odd_rays(g, away)
                if not res: return None
                out = [r[:] for r in g]
                for y, x, c in res: out[y][x] = c
                return out
            yield ("ray:odd-cell-" + ("away-from-object" if away else "through-object"), 4, odd)


# ---------------------------------------------------------------- marker-keyed rays from congruent bars
def _canon(g, ob):
    """ob: cells of a solid rectangle t x L (t < L).  Returns (pattern, coord) where coord[r][p] is the
    original cell at canonical row r, position p, for the lexicographically smallest of the 8 frames
    (first such frame on ties)."""
    from gdsl import T, fh, fv
    y0, x0, y1, x1 = bbox(ob)
    if len(ob) != (y1 - y0 + 1) * (x1 - x0 + 1): return None
    cg = [[(y, x) for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    if len(cg) > len(cg[0]): cg = T(cg)
    t, L = len(cg), len(cg[0])
    if t < 2 or t >= L: return None
    best = None
    for f in (lambda a: a, fh, fv, lambda a: fh(fv(a))):
        c = f(cg); pat = tuple(tuple(g[y][x] for y, x in r) for r in c)
        if best is None or pat < best[0]: best = (pat, c)
    return best

def _bars_markers(g):
    bg = bg_of(g); bars = []; marks = []
    for ob in objects(g, bg, False, False):
        if len(ob) == 1:
            y, x = ob[0]
            if y in (0, H(g) - 1) or x in (0, W(g) - 1): marks.append((y, x))
            else: return None
            continue
        cb = _canon(g, ob)
        if cb is None: return None
        bars.append(cb)
    if not bars or len({b[0] for b in bars}) != 1: return None
    return bg, bars, marks

def _face_rays(g, bg, coord, face, p):
    t = len(coord); a = coord[0 if face == 0 else t - 1][p]; b = coord[1 if face == 0 else t - 2][p]
    dy, dx = a[0] - b[0], a[1] - b[1]
    y, x = a[0] + dy, a[1] + dx; path = []
    while 0 <= y < H(g) and 0 <= x < W(g):
        path.append((y, x)); y += dy; x += dx
    return path

def _marker_legend(g):
    r = _bars_markers(g)
    if r is None: return None
    bg, bars, marks = r
    face = None; leg = {}
    for my, mx in marks:
        hit = []
        for pat, coord in bars:
            for f in (0, 1):
                for p in range(len(coord[0])):
                    path = _face_rays(g, bg, coord, f, p)
                    if path and path[-1] == (my, mx) and all(g[y][x] == bg for y, x in path[:-1]):
                        hit.append((f, p))
        if len(hit) != 1: return None
        f, p = hit[0]
        if face not in (None, f) or leg.get(p, g[my][mx]) != g[my][mx]: return None
        face = f; leg[p] = g[my][mx]
    if face is None: return None
    return bg, bars, face, leg

def _marker_bar_rays(g, stop):
    r = _marker_legend(g)
    if r is None: return None
    bg, bars, face, leg = r
    out = [row[:] for row in g]
    for pat, coord in bars:
        for p, c in leg.items():
            for y, x in _face_rays(g, bg, coord, face, p):
                if g[y][x] != bg:
                    if stop and g[y][x] != c: break
                    continue
                out[y][x] = c
    return out

def fam_marker_bar_rays(train):
    """Congruent solid bars (same pattern up to the dihedral frame) and single border markers.
    Each marker sits at the end of a straight clear line leaving one face of one bar at some position
    along it; the markers jointly give a legend (face, position -> colour) in the bars' canonical frame,
    and every bar emits those rays from that face to the edge."""
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)) or _marker_legend(i0) is None: return
    for stop in (False, True):
        yield ("ray:marker-legend-bars[%s]" % ("stop" if stop else "through"), 5,
               lambda g, stop=stop: _marker_bar_rays(g, stop))

FAMILIES = (fam_directed_rays, fam_marker_bar_rays)
