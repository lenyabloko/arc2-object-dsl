"""Prior family: distance_rings_halo  (SURROUND by a distance field).

One generator: compute, for every cell, its lattice distance d (Chebyshev = 8-neighbour squares, or
Manhattan = 4-neighbour diamonds) to a source set, then paint BACKGROUND cells by d:
    halo   : colour c on every background cell with d <= k            (a frame / halo of thickness k)
    rings  : palette[(d - d0) mod P] on every background cell          (concentric rings / ripples)
Sources (participants), read from each input:
    object anchors  shape  - the object's own cells            (dilation)
                    bbox   - the object's bounding box          (rectangular frame; enclosed holes stay)
                    centre - the bbox centre, offset by the object's circumradius (smallest enclosing ball)
    regions         room   - the outside of each room (rooms = 4-components of non-wall cells, wall =
                             2nd most frequent colour); d = 1 on the room's rim
                    canvas - the outside of the canvas (one room = the whole grid)
    point           centre of the bbox of all non-background cells (d = 0 there)
                    fit    - a (possibly off-grid, half-integer) centre on which the visible non-background
                             cells form complete rings (ripple continuation)
Parameters (small finite domains, induced from the training pairs only; no stored sizes/coordinates):
    metric  in {cheb, manh}
    k       in {1, 2, 3, count of minority cells, minority-bbox min side, size//2, size, largest clear
                (distance to the nearest foreign non-bg cell - 1), 0 (centre anchor only)}
    fit     in {clip, shrink (k shrunk so the frame fits in the grid)}
    colour  in {minority colour of the object, own colour, legend partner (2-colour key component),
                map (object colour -> halo colour, induced)}
    rings:  palette printed by the seeds (non-bg cells) at their own distance; P in {span (deepest seed
            + 1), step (gcd of the seed distance gaps)}; unprinted entries in {keep background, colour
            induced from training}
    erase   in {keep, erase} the seed markers (region halo only)
Background = most frequent colour of the grid.
"""
from collections import Counter, deque
import time

CARD = "prior_distance_rings_halo"
CONCEPT = "distance_rings_halo"
MEMBERS = ['13e47133', '3a301edc', '45a5af55', '52fd389e', '5adee1b2', '5c2c9af4', '8cb8642d', '9356391f',
           'b457fec5', 'c97c0139', 'db93a21d', 'e2092e0c', 'f8c80d96', 'fc754716', 'fd4b2b02', 'ff72ca3e']
READING = {
    "generator": "compute every cell's Chebyshev/Manhattan distance d to a source set (object shape, bbox or "
                 "centre ball, room walls / canvas border, or a seed point) and paint background cells "
                 "colour c while d <= k (halo/frame) or palette[d mod P] (concentric rings)",
    "stop": "halo: d > k (k from a constant, a count, a size or the largest clear ball); rings: grid / room "
            "edge (periodic palette never stops)",
    "params": "metric in {cheb, manh} . anchor in {shape, bbox, centre, room, canvas, point, fit} . "
              "k in {1,2,3,count,msize,half,size,clear,0} . fit in {clip, shrink} . colour in {minority, "
              "self, legend, map} . P in {span, step} . fill in {keep, induced colour} . erase in {0,1}",
    "participants": "background = most frequent colour; objects = 8-connected non-background components "
                    "(main colour = most frequent, minority = least frequent); rooms = 4-components of "
                    "non-wall cells (wall = 2nd most frequent colour); seeds = non-bg cells inside a "
                    "room / around a point",
    "preconditions": "same in/out size; every changed cell was background (or an erased seed); some cell "
                     "changes",
}

_N8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_BUDGET = 0.55


# ----------------------------------------------------------------------------------------- participants
_MEMO = {}


def _memo(key, make):
    """Small per-process cache for per-grid derived structures (pure functions of the grid)."""
    if key in _MEMO:
        return _MEMO[key]
    if len(_MEMO) > 256:
        _MEMO.clear()
    v = _MEMO[key] = make()
    return v


def _gkey(g):
    return tuple(map(tuple, g))


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _dm(metric, dr, dc):
    dr, dc = abs(dr), abs(dc)
    return dr + dc if metric == 'manh' else max(dr, dc)


def _objects(g, bg):
    return _memo(('obj', _gkey(g), bg), lambda: _objects_raw(g, bg))


def _objects_raw(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    objs = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            st = [(r, c)]; seen[r][c] = True; cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in _N8:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] != bg:
                        seen[yy][xx] = True; st.append((yy, xx))
            cnt = Counter(g[y][x] for y, x in cells)
            order = sorted(cnt, key=lambda k: (-cnt[k], k))
            ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
            o = {'cells': cells, 'bb': (min(ys), min(xs), max(ys), max(xs)), 'main': order[0],
                 'ncol': len(cnt), 'cnt': cnt}
            if len(cnt) >= 2:
                mi = order[-1]
                o['minor'] = mi
                o['mcount'] = sum(v for k, v in cnt.items() if k != order[0])
                mc = [(y, x) for y, x in cells if g[y][x] == mi]
                o['msize'] = min(max(p[0] for p in mc) - min(p[0] for p in mc),
                                 max(p[1] for p in mc) - min(p[1] for p in mc)) + 1
            objs.append(o)
    return objs


def _legend(g, objs):
    """2-colour components act as a key: key colour (an object colour elsewhere) -> partner colour."""
    single = {o['main'] for o in objs if o['ncol'] == 1}
    mp = {}
    for o in objs:
        if o['ncol'] != 2:
            continue
        a, b = sorted(o['cnt'])
        if a in single and b not in single:
            mp[a] = b
        elif b in single and a not in single:
            mp[b] = a
    return mp


# ------------------------------------------------------------------------------------------ distances
def _anchor_dist(o, anchor, metric, H, W, lim):
    """dict cell -> d (d <= lim) for an object anchor; d = 0 on the anchor."""
    r0, c0, r1, c1 = o['bb']
    out = {}
    if anchor == 'shape':
        nb = _N4 if metric == 'manh' else _N8
        out = {p: 0 for p in o['cells']}; q = deque(o['cells'])
        while q:
            y, x = q.popleft(); dd = out[(y, x)]
            if dd >= lim:
                continue
            for dy, dx in nb:
                p = (y + dy, x + dx)
                if 0 <= p[0] < H and 0 <= p[1] < W and p not in out:
                    out[p] = dd + 1; q.append(p)
        return out
    if anchor == 'bbox':
        for y in range(max(0, r0 - lim), min(H, r1 + lim + 1)):
            dy = r0 - y if y < r0 else (y - r1 if y > r1 else 0)
            for x in range(max(0, c0 - lim), min(W, c1 + lim + 1)):
                dx = c0 - x if x < c0 else (x - c1 if x > c1 else 0)
                d = _dm(metric, dy, dx)
                if d <= lim:
                    out[(y, x)] = d
        return out
    # centre ball: d = ceil((D2 - R2) / 2) with doubled coordinates
    cy2, cx2 = r0 + r1, c0 + c1
    R2 = max(_dm(metric, 2 * y - cy2, 2 * x - cx2) for y, x in o['cells'])
    rad = (R2 + 2 * lim) // 2 + 1
    cy, cx = cy2 // 2, cx2 // 2
    for y in range(max(0, cy - rad), min(H, cy + rad + 2)):
        for x in range(max(0, cx - rad), min(W, cx + rad + 2)):
            d = -((R2 - _dm(metric, 2 * y - cy2, 2 * x - cx2)) // 2)
            if d <= lim:
                out[(y, x)] = max(d, 0)
    return out


def _holes(g, bg, o):
    """Background cells inside the object's bbox not 4-reachable from the bbox rim (enclosed holes)."""
    r0, c0, r1, c1 = o['bb']
    inside = {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if g[y][x] == bg}
    st = [p for p in inside if p[0] in (r0, r1) or p[1] in (c0, c1)]
    seen = set(st)
    while st:
        y, x = st.pop()
        for dy, dx in _N4:
            p = (y + dy, x + dx)
            if p in inside and p not in seen:
                seen.add(p); st.append(p)
    return inside - seen


def _k(rule, o, anchor, metric, g, bg, H, W, fit):
    kind = rule
    r0, c0, r1, c1 = o['bb']
    if kind in (1, 2, 3, 0):
        k = kind
    elif kind == 'count':
        k = o.get('mcount')
    elif kind == 'msize':
        k = o.get('msize')
    elif kind == 'half':
        k = (max(r1 - r0, c1 - c0) + 1) // 2
    elif kind == 'size':
        k = max(r1 - r0, c1 - c0) + 1
    else:  # clear: largest k whose halo touches no foreign non-background cell
        own = set(o['cells'])
        obst = [(y, x) for y in range(H) for x in range(W) if g[y][x] != bg and (y, x) not in own]
        if not obst:
            return None
        if anchor == 'shape' and len(own) * len(obst) > 40000:
            return None
        if anchor == 'shape':
            m = min(_dm(metric, y - a, x - b) for a, b in own for y, x in obst)
        elif anchor == 'bbox':
            m = min(_dm(metric, max(r0 - y, 0, y - r1), max(c0 - x, 0, x - c1)) for y, x in obst)
        else:
            cy2, cx2 = r0 + r1, c0 + c1
            R2 = max(_dm(metric, 2 * y - cy2, 2 * x - cx2) for y, x in own)
            m = min(-((R2 - _dm(metric, 2 * y - cy2, 2 * x - cx2)) // 2) for y, x in obst)
        k = m - 1
    if k is None or k < 0:
        return None
    if fit == 'shrink':
        k = min(k, r0, c0, H - 1 - r1, W - 1 - c1)
    return k


def _halo_field(g, bg, objs, anchor, metric, rule, fit):
    """cell -> (d, object index): nearest source among all objects (colour decided later)."""
    key = ('halo', _gkey(g), bg, tuple(o['cells'][0] for o in objs), anchor, metric, rule, fit)
    return _memo(key, lambda: _halo_field_raw(g, bg, objs, anchor, metric, rule, fit))


def _halo_field_raw(g, bg, objs, anchor, metric, rule, fit):
    H, W = len(g), len(g[0])
    best = {}
    for i, o in enumerate(objs):
        k = _k(rule, o, anchor, metric, g, bg, H, W, fit)
        if k is None:
            continue
        dist = _anchor_dist(o, anchor, metric, H, W, k)
        hole = _holes(g, bg, o) if anchor == 'bbox' else ()
        for p, d in dist.items():
            if g[p[0]][p[1]] != bg or p in hole:
                continue
            b = best.get(p)
            if b is None or d < b[0]:
                best[p] = (d, i)
    return best


def _colour_of(o, role, cmap, legend):
    if role == 'minority':
        return o.get('minor')
    if role == 'self':
        return o['main'] if o['ncol'] == 1 else None
    if role == 'legend':
        return legend.get(o['main']) if o['ncol'] == 1 else None
    return cmap.get(o['main']) if o['ncol'] == 1 else None


_DIRS = {'down': (1, 0), 'up': (-1, 0), 'right': (0, 1), 'left': (0, -1)}


def _rays(g, bg, srcs, dy, dx):
    """Secondary layer (parallel projection): background cells hit by rays cast from the sources."""
    H, W = len(g), len(g[0]); s = set()
    for o in srcs:
        for y, x in o['cells']:
            y, x = y + dy, x + dx
            while 0 <= y < H and 0 <= x < W:
                if g[y][x] == bg:
                    s.add((y, x))
                y, x = y + dy, x + dx
    return s


def _make_halo(anchor, metric, rule, fit, role, cmap, shadow=None):
    def fn(g):
        bg = _bg(g)
        objs = _objects(g, bg)
        out = [row[:] for row in g]
        legend = _legend(g, objs) if role == 'legend' else {}
        srcs = [o for o in objs if _colour_of(o, role, cmap, legend) is not None]
        if shadow:
            dy, dx = _DIRS[shadow[0]]
            for y, x in _rays(g, bg, srcs, dy, dx):
                out[y][x] = shadow[1]
        for p, (d, i) in _halo_field(g, bg, srcs, anchor, metric, rule, fit).items():
            out[p[0]][p[1]] = _colour_of(srcs[i], role, cmap, legend)
        return out
    return fn


# --------------------------------------------------------------------------------- region / point rings
def _regions(g, bg, source):
    """list of (cells, dist dict, d0): d = distance to the outside of the region (rim d = 1)."""
    H, W = len(g), len(g[0])
    if source == 'canvas':
        rooms = [[(y, x) for y in range(H) for x in range(W)]]
        wall = None
    else:
        cnt = Counter(v for r in g for v in r).most_common(2)
        if len(cnt) < 2:
            return None
        wall = cnt[1][0]
        lab = [[-1] * W for _ in range(H)]
        rooms = []
        for r in range(H):
            for c in range(W):
                if g[r][c] == wall or lab[r][c] >= 0:
                    continue
                cells = [(r, c)]; lab[r][c] = len(rooms); q = [(r, c)]
                while q:
                    y, x = q.pop()
                    for dy, dx in _N4:
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and lab[yy][xx] < 0 and g[yy][xx] != wall:
                            lab[yy][xx] = len(rooms); cells.append((yy, xx)); q.append((yy, xx))
                rooms.append(cells)
    return rooms, wall


def _room_dist(room, H, W, metric):
    return _memo(('room', tuple(room), H, W, metric), lambda: _room_dist_raw(room, H, W, metric))


def _room_dist_raw(room, H, W, metric):
    nb = _N4 if metric == 'manh' else _N8
    inside = set(room)
    dist = {}; q = deque()
    for (y, x) in room:
        for dy, dx in nb:
            yy, xx = y + dy, x + dx
            if not (0 <= yy < H and 0 <= xx < W) or (yy, xx) not in inside:
                dist[(y, x)] = 1; q.append((y, x)); break
    while q:
        y, x = q.popleft()
        for dy, dx in nb:
            p = (y + dy, x + dx)
            if p in inside and p not in dist:
                dist[p] = dist[(y, x)] + 1; q.append(p)
    return dist


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def _palette(seeds, d0, prule):
    """seeds: d -> colour.  Returns (P, {index: colour}) or None."""
    ds = sorted(seeds)
    if prule == 'span':
        P = ds[-1] - d0 + 1
    else:
        if len(ds) < 2:
            return None
        P = 0
        for a in ds[1:]:
            P = _gcd(P, a - ds[0])
    if P <= 0:
        return None
    pal = {}
    for d, col in seeds.items():
        i = (d - d0) % P
        if pal.setdefault(i, col) != col:
            return None
    return P, pal


def _paint_rings(g, out, bg, cells, dist, d0, prule, fill):
    seeds = {}
    for p in cells:
        v = g[p[0]][p[1]]
        if v != bg:
            d = dist(p)
            if seeds.setdefault(d, v) != v:
                return False
    if not seeds:
        return True
    pp = _palette(seeds, d0, prule)
    if pp is None:
        return False
    P, pal = pp
    for p in cells:
        if g[p[0]][p[1]] == bg:
            c = pal.get((dist(p) - d0) % P, fill)
            if c is not None:
                out[p[0]][p[1]] = c
    return True


def _fit_centre(g, bg, metric):
    return _memo(('fit', _gkey(g), bg, metric), lambda: _fit_centre_raw(g, bg, metric))


def _fit_centre_raw(g, bg, metric):
    """A doubled-coordinate centre on which the non-bg cells form complete, single-coloured rings."""
    H, W = len(g), len(g[0])
    S = [(y, x) for y in range(H) for x in range(W) if g[y][x] != bg]
    if not S or len(S) > 120 or len({g[y][x] for y, x in S}) > 4:
        return None
    nS = len(S)
    for R2 in range(-2, 2 * H + 1):
        for C2 in range(-2, 2 * W + 1):
            if metric == 'cheb' and (R2 - C2) % 2:
                continue
            col = {}
            ok = True
            for y, x in S:
                D = _dm(metric, 2 * y - R2, 2 * x - C2)
                if col.setdefault(D, g[y][x]) != g[y][x]:
                    ok = False; break
            if not ok or len(col) < 2:
                continue
            Ds = set(col); n = 0
            for y in range(H):
                for x in range(W):
                    if _dm(metric, 2 * y - R2, 2 * x - C2) in Ds:
                        n += 1
                        if n > nS:
                            break
                if n > nS:
                    break
            if n == nS:
                return R2, C2
    return None


def _make_rings(source, metric, prule, fill):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        if source in ('room', 'canvas'):
            rr = _regions(g, bg, source)
            if rr is None:
                return None
            for room in rr[0]:
                dd = _room_dist(room, H, W, metric)
                if not _paint_rings(g, out, bg, room, dd.__getitem__, 1, prule, fill):
                    return None
            return out
        if source == 'point':
            S = [(y, x) for y in range(H) for x in range(W) if g[y][x] != bg]
            if not S:
                return None
            R2 = min(p[0] for p in S) + max(p[0] for p in S)
            C2 = min(p[1] for p in S) + max(p[1] for p in S)
        else:
            rc = _fit_centre(g, bg, metric)
            if rc is None:
                return None
            R2, C2 = rc
        par = R2 % 2 if metric == 'cheb' else 0
        dist = lambda p: (_dm(metric, 2 * p[0] - R2, 2 * p[1] - C2) - par) // 2
        cells = [(y, x) for y in range(H) for x in range(W)]
        if not _paint_rings(g, out, bg, cells, dist, 0, prule, fill):
            return None
        return out
    return fn


def _make_region_halo(source, metric, k, erase):
    """Inward frame of thickness k along each room's rim (or the canvas border), in the room's seed colour."""
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        rr = _regions(g, bg, source)
        if rr is None:
            return None
        rooms, wall = rr
        out = [row[:] for row in g]
        for room in rooms:
            cols = {g[y][x] for y, x in room if g[y][x] != bg}
            if len(cols) != 1:
                continue
            c = cols.pop()
            dd = _room_dist(room, H, W, metric)
            for p in room:
                v = g[p[0]][p[1]]
                if v != bg:
                    if erase:
                        out[p[0]][p[1]] = bg
                    else:
                        continue
                if dd[p] <= k:
                    out[p[0]][p[1]] = c
        return out
    return fn


# ------------------------------------------------------------------------------------------- the family
def _fits(fn, train):
    for p in train:
        try:
            if fn(p['input']) != p['output']:
                return False
        except Exception:
            return False
    return True


def _induce_cmap(train, bgs, objss, anchor, metric, rule, fit):
    """object colour -> halo colour, from the halos of single-colour objects of that colour."""
    seen = {}
    for p, bg, objs in zip(train, bgs, objss):
        g, o = p['input'], p['output']
        field = _halo_field(g, bg, [x for x in objs if x['ncol'] == 1], anchor, metric, rule, fit)
        singles = [x for x in objs if x['ncol'] == 1]
        for q, (d, i) in field.items():
            seen.setdefault(singles[i]['main'], set()).add(o[q[0]][q[1]])
    cmap = {}
    for c, cols in seen.items():
        if len(cols) == 1:
            v = cols.pop()
            if v != bgs[0]:
                cmap[c] = v
    return cmap


def fam(train):
    t0 = time.time()
    if not train:
        return
    for p in train:
        a, b = p['input'], p['output']
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
    bgs = [_bg(p['input']) for p in train]
    erased = False; changed = False
    for p, bg in zip(train, bgs):
        for ra, rb in zip(p['input'], p['output']):
            for x, y in zip(ra, rb):
                if x != y:
                    changed = True
                    if x != bg:
                        if y != bg:
                            return
                        erased = True
    if not changed:
        return
    outcols = sorted({v for p in train for r in p['output'] for v in r} - set(bgs))
    found = 0

    def ok(fn):
        return _fits(fn, train)

    # 1. object halos (outward)
    if not erased:
        objss = [_objects(p['input'], bg) for p, bg in zip(train, bgs)]
        chg = [{(y, x): b for y, (ra, rb) in enumerate(zip(p['input'], p['output']))
                for x, (a, b) in enumerate(zip(ra, rb)) if a != b} for p in train]
        if all(0 < len(os) <= 60 for os in objss):
            multi = any(o['ncol'] >= 2 for os in objss for o in os)
            roles = (['minority'] if multi else []) + ['legend', 'self', 'map']
            rules = (1, 2, 3, 'count', 'msize', 'half', 'size', 'clear', 0)
            cost = 0
            for anchor in ('bbox', 'shape', 'centre'):
                for metric in ('cheb', 'manh'):
                    for rule in rules:
                        if rule == 0 and anchor != 'centre':
                            continue
                        if rule in ('count', 'msize') and not multi:
                            continue
                        prev = None
                        for fit in ('clip', 'shrink'):
                            cost += 1
                            if time.time() - t0 > _BUDGET:
                                return
                            fields = [_halo_field(p['input'], bg, os, anchor, metric, rule, fit)
                                      for p, bg, os in zip(train, bgs, objss)]
                            if fields == prev:
                                continue
                            prev = fields
                            # every painted cell must lie in the halo, or else be one colour (ray layer)
                            resid = [{q: v for q, v in ch.items() if q not in f} for ch, f in zip(chg, fields)]
                            rcols = {v for r in resid for v in r.values()}
                            if len(rcols) > 1 or not any(fields):
                                continue
                            shadows = [None]
                            if rcols:
                                sc = rcols.pop()
                                shadows = [(nm, sc) for nm in _DIRS]
                            for role in roles:
                                cmap = None
                                if role == 'map':
                                    cmap = _induce_cmap(train, bgs, objss, anchor, metric, rule, fit)
                                    if not cmap:
                                        continue
                                hit = False
                                for sh in shadows:
                                    fn = _make_halo(anchor, metric, rule, fit, role, cmap, sh)
                                    if ok(fn):
                                        yield ('surround:halo[anchor=%s,metric=%s,k=%s,fit=%s,colour=%s%s]'
                                               % (anchor, metric, rule, fit, role,
                                                  ',rays=%s:%d' % sh if sh else ''), 1 + cost * 0.01, fn)
                                        found += 1
                                        if found >= 2:
                                            return
                                        hit = True
                                        break
                                if hit:
                                    break
    # 2. inward frames along room rims / the canvas border
    for source in ('canvas', 'room'):
        for metric in ('cheb', 'manh'):
            for k in (1, 2, 3):
                for erase in ((False, True) if erased else (False,)):
                    if time.time() - t0 > _BUDGET:
                        return
                    fn = _make_region_halo(source, metric, k, erase)
                    if ok(fn):
                        yield ('surround:frame[source=%s,metric=%s,k=%d,erase=%d]' % (source, metric, k, erase),
                               2, fn)
                        found += 1
                        if found >= 2:
                            return
                        break
    if erased:
        return
    # 3. concentric rings: palette printed by the seeds, repeated with period P
    for source in ('room', 'canvas', 'point', 'fit'):
        for metric in ('cheb', 'manh'):
            if source == 'fit' and _fit_centre(train[0]['input'], bgs[0], metric) is None:
                continue
            for prule in ('span', 'step'):
                for fill in [None] + outcols:
                    if time.time() - t0 > _BUDGET:
                        return
                    fn = _make_rings(source, metric, prule, fill)
                    if ok(fn):
                        yield ('surround:rings[source=%s,metric=%s,P=%s,fill=%s]'
                               % (source, metric, prule, 'keep' if fill is None else fill), 3, fn)
                        found += 1
                        if found >= 2:
                            return
                        break


FAMILIES = [fam]
