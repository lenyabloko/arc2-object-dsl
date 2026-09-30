"""Group g04 ("shadows cast from objects") -- one family: geometric optics / ray casting.

Concept (optics / computer graphics): RAY CASTING.  Every source object emits parallel rays in a
direction d (one ray per 'front' cell of the object, i.e. a cell whose neighbour along d is outside
the object).  A ray travels in a straight line, skipping its own object, and paints the cells it
crosses with a colour; it ends at the grid edge or after a finite reach L (attenuation / shadow
length).  Optional refracting interfaces: every marker cell defines an interface line perpendicular
to d through it; when a ray enters that line it is displaced laterally by one cell (away from or
toward the marker) and continues parallel (lateral shift of a refracting slab).
A shadow is the same construction with a fixed 'shade' colour (the region the object occludes).

Declared finite parameter domains (all induced from THIS task's training pairs):
  src    : 'all' objects (8-connected, multi-colour, markers excluded) | objects of one input colour
  mark   : none | one input colour (interface markers)            shift: away | toward
  dir    : U D L R UL UR DL DR (fixed) | 'away_border' (away from the single grid edge the object touches)
  len    : edge | ncolors | ncells | depth (extent along d) | width (extent across d) | const 1..9
  colour : 'source' (colour of the emitting cell) | fixed C (the single colour of all changed cells)
  obst   : pass (do not paint non-background, keep going) | stop (ray ends at non-background) | over
Background = most frequent colour of each input grid.
"""
import time
from collections import Counter

DIRS = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1),
        'UL': (-1, -1), 'UR': (-1, 1), 'DL': (1, -1), 'DR': (1, 1)}
DIR_MODES = ('U', 'D', 'L', 'R', 'UL', 'UR', 'DL', 'DR', 'away_border')
LEN_MODES = ('edge', 'ncolors', 'ncells', 'depth', 'width') + tuple(range(1, 10))
OBST_MODES = ('pass', 'stop', 'over')
SHIFT_MODES = ('away', 'toward')
TIME_BUDGET = 0.35


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _objects(g, bg, colour, exclude):
    """8-connected components of non-background cells (only `colour` if given, never `exclude`)."""
    H, W = len(g), len(g[0])
    seen, objs = set(), []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == bg or v == exclude or (colour is not None and v != colour) or (r, c) in seen:
                continue
            comp, stack = [], [(r, c)]
            seen.add((r, c))
            while stack:
                a, b = stack.pop()
                comp.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen:
                            w = g[x][y]
                            if w != bg and w != exclude and (colour is None or w == colour):
                                seen.add((x, y))
                                stack.append((x, y))
            objs.append(frozenset(comp))
    return objs


def _obj_dir(obj, mode, H, W):
    if mode != 'away_border':
        return DIRS[mode]
    rs = [r for r, _ in obj]
    cs = [c for _, c in obj]
    touch = []
    if min(rs) == 0: touch.append((1, 0))
    if max(rs) == H - 1: touch.append((-1, 0))
    if min(cs) == 0: touch.append((0, 1))
    if max(cs) == W - 1: touch.append((0, -1))
    return touch[0] if len(touch) == 1 else None


def _length(obj, g, d, mode):
    if mode == 'edge':
        return 10 ** 9
    if isinstance(mode, int):
        return mode
    if mode == 'ncolors':
        return len({g[r][c] for r, c in obj})
    if mode == 'ncells':
        return len(obj)
    along = [r * d[0] + c * d[1] for r, c in obj]
    across = [r * d[1] - c * d[0] for r, c in obj]
    if mode == 'depth':
        return max(along) - min(along) + 1
    return max(across) - min(across) + 1   # width


def _rays(g, bg, src, mark, dmode, shift, cache=None):
    """All rays for one configuration: list of (object, dir, emitter colour, [cells in order])."""
    H, W = len(g), len(g[0])
    key = (src, mark)
    if cache is not None and key in cache:
        markers, objs = cache[key]
    else:
        markers = [] if mark is None else [(r, c) for r in range(H) for c in range(W) if g[r][c] == mark]
        objs = _objects(g, bg, None if src == 'all' else src, mark)
        if cache is not None:
            cache[key] = (markers, objs)
    sgn = 1 if shift == 'away' else -1
    rays = []
    for obj in objs:
        d = _obj_dir(obj, dmode, H, W)
        if d is None:
            continue
        axis = d[0] == 0 or d[1] == 0
        lines = {}
        if markers and axis:
            for mr, mc in markers:   # interface line perpendicular to d through the marker
                along, perp = (mr, mc) if d[1] == 0 else (mc, mr)
                lines.setdefault(along, []).append(perp)
        for (r, c) in sorted(obj):
            if (r + d[0], c + d[1]) in obj:
                continue              # not a front cell
            path, x, y = [], r, c
            for _ in range(2 * (H + W)):
                x, y = x + d[0], y + d[1]
                if lines:
                    along, perp = (x, y) if d[1] == 0 else (y, x)
                    if along in lines:
                        s = sgn * sum((perp > m) - (perp < m) for m in lines[along])
                        if d[1] == 0: y += s
                        else: x += s
                if not (0 <= x < H and 0 <= y < W):
                    break
                if (x, y) in obj:
                    continue
                path.append((x, y))
            rays.append((obj, d, g[r][c], path))
    return rays


def _render(g, bg, rays, lmode, colour, obst):
    out = [row[:] for row in g]
    for obj, d, ecol, path in rays:
        L = _length(obj, g, d, lmode)
        col = ecol if colour == 'source' else colour
        n = 0
        for (x, y) in path:
            if n >= L:
                break
            if g[x][y] != bg:
                if obst == 'stop':
                    break
                if obst == 'pass':
                    n += 1
                    continue
            out[x][y] = col
            n += 1
    return out


def fam_ray_casting(train):
    t0 = time.time()
    if not train or any(len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0])
                        for p in train):
        return
    pairs = []
    for p in train:
        g, o = p['input'], p['output']
        bg = _bg(g)
        ch = {(r, c) for r in range(len(g)) for c in range(len(g[0])) if g[r][c] != o[r][c]}
        pairs.append((g, o, bg, ch, {}))
    if not any(ch for g, o, bg, ch, _ in pairs):
        return
    changed_cols = {o[r][c] for g, o, bg, ch, _ in pairs for r, c in ch}
    colour_modes = ['source'] + ([changed_cols.pop()] if len(changed_cols) == 1 else [])
    common = set.intersection(*[{v for row in g for v in row} - {bg} for g, o, bg, ch, _ in pairs])
    common = sorted(common)
    srcs = ['all'] + common
    marks = [None] + common
    for src in srcs:
        for mark in marks:
            if mark is not None and mark == src:
                continue
            for shift in (SHIFT_MODES if mark is not None else ('away',)):
                for dmode in DIR_MODES:
                    if time.time() - t0 > TIME_BUDGET:
                        return
                    if mark is not None and dmode in ('UL', 'UR', 'DL', 'DR'):
                        continue
                    allrays, ok = [], True
                    for g, o, bg, ch, cache in pairs:       # coverage test: every change lies on a ray
                        rays = _rays(g, bg, src, mark, dmode, shift, cache)
                        cover = {cell for *_, path in rays for cell in path}
                        if not ch <= cover:
                            ok = False
                            break
                        allrays.append(rays)
                    if not ok:
                        continue
                    for colour in colour_modes:
                        for obst in OBST_MODES:
                            for lmode in LEN_MODES:
                                if all(_render(g, bg, rays, lmode, colour, obst) == o
                                       for (g, o, bg, ch, _), rays in zip(pairs, allrays)):
                                    params = (src, mark, shift, dmode, lmode, colour, obst)
                                    name = ('optics:ray_casting[src=%s,marker=%s/%s,dir=%s,len=%s,colour=%s,obst=%s]'
                                            % ((src, mark, shift if mark is not None else '-', dmode, lmode,
                                                'source' if colour == 'source' else 'fixed', obst)))

                                    def fn(grid, params=params):
                                        s, m, sh, dm, lm, col, ob = params
                                        b = _bg(grid)
                                        return _render(grid, b, _rays(grid, b, s, m, dm, sh), lm, col, ob)
                                    yield (name, 3, fn)
                                    return


FAMILIES = (fam_ray_casting,)
