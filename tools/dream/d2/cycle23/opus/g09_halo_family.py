"""Group g09 ("halo of width k around an object") -- one family.

Concept: METRIC BALL (geometry; a.k.a. r-neighbourhood / morphological dilation by a norm ball).
Every source object is surrounded by the ball  {p : d(p, anchor) <= r}  of a lattice norm d
(L1 = Manhattan diamond, Linf = Chebyshev square), painted in a halo colour on background cells only
(objects stay on top).  Declared finite parameter domains:
    metric  in {Linf, L1}
    anchor  in {shape  : r-neighbourhood of the object's own cells (dilation of the shape),
                ball   : ball centred on the object's bbox centre whose radius is the object's
                         circumradius + r  (r = 0 -> smallest enclosing ball)}
    r-rule  in {const r in 0..3, size s//2, size s  (s = max(bbox h, w)),
                clear g in 0..1 : largest ball that stays g cells clear of every other non-bg cell
                                  ("largest empty ball")}
    colour  : halo colour per source-object colour, induced from training (objects whose halo
              is not explained are not sources)
    shadow  (optional secondary layer, parallel projection): direction in {down, up, right, left},
              colour induced; the source objects' shadows run to the border beneath the halos.
"""
from collections import Counter, deque

_METRICS = ('Linf', 'L1')
_ANCHORS = ('shape', 'ball')
_RULES = (('const', 1), ('const', 2), ('const', 3), ('const', 0), ('size', 2), ('size', 1),
          ('clear', 0), ('clear', 1))
_DIRS = (('down', 1, 0), ('up', -1, 0), ('right', 0, 1), ('left', 0, -1))
_N8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _d(metric, dr, dc):
    dr, dc = abs(dr), abs(dc)
    return dr + dc if metric == 'L1' else max(dr, dc)


def _objects(g, bg):
    H, W = len(g), len(g[0]); seen = [[False] * W for _ in range(H)]; out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            col = g[r][c]; cells = []; st = [(r, c)]; seen[r][c] = True
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in _N8:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] == col:
                        seen[yy][xx] = True; st.append((yy, xx))
            ys = [p[0] for p in cells]; xs = [p[1] for p in cells]
            out.append((col, cells, (min(ys), min(xs), max(ys), max(xs))))
    return out


def _bfs(cells, H, W, metric, limit, stop=None):
    """Multi-source lattice BFS (8-nbr = Linf, 4-nbr = L1). Returns dist dict up to `limit`;
    if `stop` (set) is given, returns the distance of the first stop cell reached (or None)."""
    nb = _N4 if metric == 'L1' else _N8
    dist = {p: 0 for p in cells}; q = deque(cells)
    while q:
        y, x = q.popleft(); dd = dist[(y, x)]
        if stop is not None and (y, x) in stop:
            return dd
        if limit is not None and dd >= limit:
            continue
        for dy, dx in nb:
            p = (y + dy, x + dx)
            if 0 <= p[0] < H and 0 <= p[1] < W and p not in dist:
                dist[p] = dd + 1; q.append(p)
    return None if stop is not None else dist


def _ball_geom(cells, bb, metric):
    cy2, cx2 = bb[0] + bb[2], bb[1] + bb[3]          # doubled coordinates of the bbox centre
    R2 = max(_d(metric, 2 * y - cy2, 2 * x - cx2) for y, x in cells)
    return cy2, cx2, R2


def _radius(rule, anchor, metric, obj, g, bg, H, W):
    kind, v = rule; col, cells, bb = obj
    if kind == 'const':
        return v
    if kind == 'size':
        return max(bb[2] - bb[0], bb[3] - bb[1]) + 1 if v == 1 else (max(bb[2] - bb[0], bb[3] - bb[1]) + 1) // 2
    own = set(cells)
    obst = [(y, x) for y in range(H) for x in range(W) if g[y][x] != bg and (y, x) not in own]
    if not obst:
        return None
    if anchor == 'ball':
        cy2, cx2, R2 = _ball_geom(cells, bb, metric)
        m = min(_d(metric, 2 * y - cy2, 2 * x - cx2) for y, x in obst)
        k = (m - R2 - 1) // 2 - v
    else:
        if len(cells) * len(obst) <= 20000:
            m = min(_d(metric, y - a, x - b) for a, b in cells for y, x in obst)
        else:
            m = _bfs(cells, H, W, metric, None, set(obst))
        k = m - 1 - v
    return k if k >= 0 else None


def _halo(obj, anchor, metric, k, H, W):
    col, cells, bb = obj
    if anchor == 'shape':
        if k <= 0:
            return set()
        return set(_bfs(cells, H, W, metric, k)) - set(cells)
    cy2, cx2, R2 = _ball_geom(cells, bb, metric); lim = R2 + 2 * k; rad = lim // 2 + 1
    cy, cx = cy2 // 2, cx2 // 2
    return {(y, x) for y in range(max(0, cy - rad), min(H, cy + rad + 2))
            for x in range(max(0, cx - rad), min(W, cx + rad + 2))
            if _d(metric, 2 * y - cy2, 2 * x - cx2) <= lim}


def _layers(g, bg, objs, cmap, anchor, metric, rule):
    """halo cells (on bg) -> colour, for the objects whose colour is in cmap."""
    H, W = len(g), len(g[0]); paint = {}
    for obj in objs:
        if obj[0] not in cmap:
            continue
        k = _radius(rule, anchor, metric, obj, g, bg, H, W)
        if k is None:
            continue
        for y, x in _halo(obj, anchor, metric, k, H, W):
            if g[y][x] == bg:
                paint[(y, x)] = cmap[obj[0]]
    return paint


def _shadow(g, bg, objs, srcs, dy, dx):
    H, W = len(g), len(g[0]); s = set()
    for col, cells, bb in objs:
        if col not in srcs:
            continue
        for y, x in cells:
            y, x = y + dy, x + dx
            while 0 <= y < H and 0 <= x < W:
                if g[y][x] == bg:
                    s.add((y, x))
                y, x = y + dy, x + dx
    return s


def _make(bg, cmap, anchor, metric, rule, shadow):
    def fn(g):
        objs = _objects(g, bg); out = [row[:] for row in g]
        if shadow:
            _, dy, dx, sc = shadow
            for y, x in _shadow(g, bg, objs, set(cmap), dy, dx):
                out[y][x] = sc
        for (y, x), c in _layers(g, bg, objs, cmap, anchor, metric, rule).items():
            out[y][x] = c
        return out
    return fn


def fam_metric_ball(train):
    import time
    t0 = time.time()
    if not train or any(len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0])
                        for p in train):
        return
    bg = Counter(v for p in train for row in p['input'] for v in row).most_common(1)[0][0]
    changed, newcols = [], set()
    for p in train:
        ch = {}
        for y, (ri, ro) in enumerate(zip(p['input'], p['output'])):
            for x, (a, b) in enumerate(zip(ri, ro)):
                if a != b:
                    if a != bg:          # a halo never recolours an existing object
                        return
                    ch[(y, x)] = b; newcols.add(b)
        changed.append(ch)
    if not any(changed):
        return
    objs = [_objects(p['input'], bg) for p in train]
    incols = sorted({o[0] for os in objs for o in os})
    if not incols:
        return
    for anchor in _ANCHORS:
        for metric in _METRICS:
            for rule in _RULES:
                if time.time() - t0 > 0.4:
                    return
                if anchor == 'shape' and rule == ('const', 0):
                    continue
                # halo of every colour class, per pair (None = undefined radius somewhere)
                U = {}
                for c in incols:
                    per = []
                    for p, os in zip(train, objs):
                        g = p['input']; H, W = len(g), len(g[0]); s = set(); bad = False
                        for o in os:
                            if o[0] != c:
                                continue
                            k = _radius(rule, anchor, metric, o, g, bg, H, W)
                            if k is None:
                                bad = True; break
                            s |= {q for q in _halo(o, anchor, metric, k, H, W) if g[q[0]][q[1]] == bg}
                        if bad:
                            per = None; break
                        per.append(s)
                    U[c] = per
                for sc in [None] + sorted(newcols):           # colour reserved for a shadow layer
                    cmap = {}
                    for c in incols:
                        if U[c] is None or not any(U[c]):
                            continue
                        cols = {ch.get(q) for s, ch in zip(U[c], changed) for q in s}
                        if len(cols) == 1 and None not in cols and sc not in cols:
                            cmap[c] = cols.pop()
                    if not cmap:
                        continue
                    halo = [set().union(*[U[c][i] for c in cmap]) for i in range(len(train))]
                    resid = [{q: v for q, v in ch.items() if q not in h} for ch, h in zip(changed, halo)]
                    shadows = [None]
                    if any(resid):
                        if sc is None or any(v != sc for r in resid for v in r.values()):
                            continue
                        shadows = []
                        for nm, dy, dx in _DIRS:
                            if all(_shadow(p['input'], bg, os, set(cmap), dy, dx) - h == set(r)
                                   for p, os, h, r in zip(train, objs, halo, resid)):
                                shadows.append((nm, dy, dx, sc))
                    elif sc is not None:
                        continue
                    for sh in shadows:
                        fn = _make(bg, cmap, anchor, metric, rule, sh)
                        if all(fn(p['input']) == p['output'] for p in train):
                            name = 'geometry:metric_ball[metric=%s,anchor=%s,r=%s%s,colour=%s%s]' % (
                                metric, anchor, rule[0], rule[1],
                                ','.join('%d>%d' % kv for kv in sorted(cmap.items())),
                                (',shadow=%s:%d' % (sh[0], sh[3])) if sh else '')
                            yield (name, 3, fn)
                            return


FAMILIES = (fam_metric_ball,)
