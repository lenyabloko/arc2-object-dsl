"""Group g01 family: rays from objects to the border or an obstacle.

Outside concept: RAY CASTING (computer graphics).
Every emitter port on an object casts a ray outward in its compass direction.  The ray is a
rasterised path: a straight line, or a periodic staircase digital ray whose step pattern is
[forward]*k + [turn]*k.  It paints background cells until it leaves the grid or reaches an opaque
cell, meaning any non-background cell of another object.  A diagonal step between two opaque cells
that touch at a corner is also blocked, as in watertight occlusion.  Where rays cross, a z-order
over the ray axes decides which colour ends up on top.

Every parameter is induced from the task's own training pairs and comes from a small finite domain:
  obj     : objects are 8-connected components of one colour ('mono') or of mixed colours ('multi'),
            or every non-background pixel on its own ('pixel')
  emit    : which objects emit: all objects, or the objects that do / do not contain one colour
            induced from training (emitter colour vs. obstacle colour)
  ports   : 'mid' = the middle cell of the object's extreme cells in each of the 8 compass directions
            'end' = line endpoints (cells with exactly one 8-neighbour), pointing away from that neighbour
            'all' = every extreme cell in each compass direction (a beam)
  dirs    : the subset of compass directions that emit (the full set is tried first)
  gait    : orthogonal ports: none | line | stair(k, cw|ccw) with k in {1,2,3};  diagonal ports: none | line
  colour  : for each port class: port-cell colour | object-centre colour (may be background, which
            makes a dark ray that erases) | a constant induced from the changed output cells
  stop    : opaque cells stop the ray ('obstacle'), or the ray passes behind them ('through')
  corner  : a diagonal step squeezing between two corner-touching opaque cells is 'block'ed or 'leak's
  z-order : a permutation of the ray axes H, V, D1 (\\), D2 (/); later axes are drawn on top
Search is bounded by MARCH_BUDGET ray-march steps, so tasks that do not fit are rejected quickly.
"""
from collections import Counter
from itertools import combinations, permutations

ORTH = ((-1, 0), (0, 1), (1, 0), (0, -1))
DIAG = ((-1, 1), (1, 1), (1, -1), (-1, -1))
CLASS_DIRS = {'o': ORTH, 'd': DIAG}
COMPASS = {(-1, 0): 'N', (0, 1): 'E', (1, 0): 'S', (0, -1): 'W',
           (-1, 1): 'NE', (1, 1): 'SE', (1, -1): 'SW', (-1, -1): 'NW'}
AXIS = {(-1, 0): 'V', (1, 0): 'V', (0, 1): 'H', (0, -1): 'H',
        (-1, -1): 'D1', (1, 1): 'D1', (-1, 1): 'D2', (1, -1): 'D2'}
AXES = ('H', 'V', 'D1', 'D2')
ORTH_GAITS = (None, ('line',)) + tuple(('stair', k, ch) for k in (1, 2, 3) for ch in ('cw', 'ccw'))
DIAG_GAITS = (None, ('line',))
EDGE_VARIANTS = ((True, True), (True, False), (False, False))   # (stop at obstacle, block corner squeeze)
MARCH_BUDGET = 200000   # declared search budget: total ray-march steps per task during induction


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _objects(g, bg, objmode):
    H, W = len(g), len(g[0])
    lab = [[-1] * W for _ in range(H)]
    objs = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or lab[r][c] >= 0:
                continue
            col, idx = g[r][c], len(objs)
            lab[r][c] = idx
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and lab[ny][nx] < 0:
                            v = g[ny][nx]
                            if v != bg and (objmode == 'multi' or v == col) and objmode != 'pixel':
                                lab[ny][nx] = idx
                                stack.append((ny, nx))
            objs.append(cells)
    return objs, lab


def _ports(g, objs, sel, mode):
    """-> list of (object id, port cell, direction)."""
    out = []
    for oid, cells in enumerate(objs):
        if sel is not None and any(g[r][c] == sel[1] for r, c in cells) != (sel[0] == 'only'):
            continue
        if mode == 'end':
            S = set(cells)
            for (r, c) in cells:
                nb = [(r + dy, c + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                      if (dy or dx) and (r + dy, c + dx) in S]
                if len(nb) == 1:
                    out.append((oid, (r, c), (r - nb[0][0], c - nb[0][1])))
            continue
        for d in ORTH + DIAG:
            m = max(p[0] * d[0] + p[1] * d[1] for p in cells)
            ext = [p for p in cells if p[0] * d[0] + p[1] * d[1] == m]
            if mode == 'all':
                out.extend((oid, p, d) for p in ext)
                continue
            q = {p[1] * d[0] - p[0] * d[1]: p for p in ext}      # coordinate across the direction
            lo, hi = min(q), max(q)
            if (lo + hi) % 2 == 0 and (lo + hi) // 2 in q:
                out.append((oid, q[(lo + hi) // 2], d))
    return out


def _steps(d, gait):
    if gait[0] == 'line':
        return (d,)
    _, k, ch = gait
    t = (d[1], -d[0]) if ch == 'cw' else (-d[1], d[0])
    return (d,) * k + (t,) * k


def _cast(g, lab, bg, oid, start, steps, stop, squeeze, out=None):
    """March from start; returns (painted cells, hit flags: 1 = obstacle met, 2 = corner squeeze met).
    With a target grid `out` (training only, when no ray can carry the background colour) the march
    aborts with None as soon as it paints a cell that stays background in the target."""
    H, W = len(g), len(g[0])
    r, c = start
    cells, hit, n = [], 0, len(steps)
    for i in range(H * W + H + W):
        dr, dc = steps[i % n]
        nr, nc = r + dr, c + dc
        if not (0 <= nr < H and 0 <= nc < W):
            break
        if dr and dc:
            a, b = g[nr][c], g[r][nc]
            if a != bg and lab[nr][c] != oid and b != bg and lab[r][nc] != oid:
                hit |= 2
                if squeeze:
                    break
        v = g[nr][nc]
        if v != bg:
            if lab[nr][nc] != oid:
                hit |= 1
                if stop:
                    break
        else:
            if out is not None and out[nr][nc] == bg:
                return None, hit
            cells.append((nr, nc))
        r, c = nr, nc
    return cells, hit


def _colour(g, objs, oid, port, opt):
    if opt == 'port':
        return g[port[0]][port[1]]
    if opt == 'center':
        rs = [p[0] for p in objs[oid]]
        cs = [p[1] for p in objs[oid]]
        if (min(rs) + max(rs)) % 2 or (min(cs) + max(cs)) % 2:
            return None
        return g[(min(rs) + max(rs)) // 2][(min(cs) + max(cs)) // 2]
    return opt


def _render(I, rays, order):
    rank = {a: i for i, a in enumerate(order)}
    out = [list(row) for row in I]
    for d, col, cells in sorted(rays, key=lambda t: rank[AXIS[t[0]]]):
        for r, c in cells:
            out[r][c] = col
    return out


def _make(P):
    objmode, sel, mode, stop, squeeze, og, dg, oc, dc, so, sd, order = P

    def fn(I):
        bg = _bg(I)
        objs, lab = _objects(I, bg, objmode)
        rays = []
        for oid, p, d in _ports(I, objs, sel, mode):
            orth = d in ORTH
            gait = og if orth else dg
            if gait is None or d not in (so if orth else sd):
                continue
            col = _colour(I, objs, oid, p, oc if orth else dc)
            if col is None:
                continue
            cells, _ = _cast(I, lab, bg, oid, p, _steps(d, gait), stop, squeeze)
            rays.append((d, col, cells))
        return _render(I, rays, order)
    return fn


def _name(P):
    objmode, sel, mode, stop, squeeze, og, dg, oc, dc, so, sd, order = P

    def g(gait, dirs, cls, col):
        if gait is None:
            return 'none'
        s = 'line' if gait[0] == 'line' else 'stair%d%s' % (gait[1], gait[2])
        ds = 'all' if set(dirs) == set(CLASS_DIRS[cls]) else '+'.join(COMPASS[d] for d in dirs)
        return '%s(%s)/%s' % (s, ds, col)
    return ('graphics:ray_casting[obj=%s,emit=%s,ports=%s,orth=%s,diag=%s,stop=%s,corner=%s,z=%s]' % (
        objmode, 'all' if sel is None else '%s-colour%d' % sel, mode,
        g(og, so, 'o', oc), g(dg, sd, 'd', dc), 'obstacle' if stop else 'through',
        'block' if squeeze else 'leak', '<'.join(order)))


def _subsets(allowed, required):
    """Direction subsets containing `required`, largest first (the full symmetric set comes first)."""
    free = [d for d in allowed if d not in required]
    for n in range(len(free), -1, -1):
        for extra in combinations(free, n):
            s = tuple(d for d in allowed if d in required or d in extra)
            if s:
                yield s


def fam_ray_casting(train):
    pairs = [(p['input'], p['output']) for p in train]
    info = []
    for I, O in pairs:                      # quick rejection: same shape, only background cells change
        H, W = len(I), len(I[0])
        if len(O) != H or any(len(row) != W for row in O):
            return
        bg = _bg(I)
        ch = []
        for r in range(H):
            for c in range(W):
                if I[r][c] != O[r][c]:
                    if I[r][c] != bg:
                        return
                    ch.append((r, c))
        info.append((bg, ch))
    if not any(ch for _, ch in info):
        return
    consts = None
    for (bg, ch), (I, O) in zip(info, pairs):
        if ch:
            s = {O[r][c] for r, c in ch}
            consts = s if consts is None else consts & s
    col_opts = ['port', 'center'] + sorted(consts)
    common = None
    for (bg, _), (I, O) in zip(info, pairs):
        s = {v for row in I for v in row if v != bg}
        common = s if common is None else common & s
    sels = [None] + [(m, c) for m in ('only', 'not') for c in sorted(common)]

    seen, spent, deferred = set(), [0], []
    for objmode in ('mono', 'multi', 'pixel'):
        objl = [_objects(I, bg, objmode) for (bg, _), (I, O) in zip(info, pairs)]
        dark = [{oid for oid in range(len(objs)) if _colour(I, objs, oid, None, 'center') == bg}
                for (objs, _), (bg, _), (I, O) in zip(objl, info, pairs)]   # emitters with a background centre
        ocols = [[{I[r][c] for r, c in cells} for cells in objs] for (objs, _), (I, O) in zip(objl, pairs)]
        for mode in ('mid', 'end', 'all'):
            allports = [_ports(I, objs, None, mode) for (objs, _), (I, O) in zip(objl, pairs)]
            for sel in sels:
                ports = [[t for t in pl if sel is None or (sel[1] in oc[t[0]]) == (sel[0] == 'only')]
                         for pl, oc in zip(allports, ocols)]
                if any(ch and not pl for pl, (_, ch) in zip(ports, info)):
                    continue
                sig = (tuple(len(o[0]) for o in objl), tuple(tuple(pl) for pl in ports))
                if sig in seen:          # same emitters as an earlier configuration
                    continue
                seen.add(sig)
                # a ray can carry the background colour only via an emitter whose centre is background;
                # without such emitters every painted cell must be non-background in the output
                strict = [bg not in consts and not any(t[0] in dk for t in pl)
                          for pl, dk, (bg, _) in zip(ports, dark, info)]
                cache, hits = {}, [0]

                def rays_for(gait, cls, stop, squeeze):
                    """-> (per pair: {direction: [(oid, port, d, cells)]}, allowed directions) or None."""
                    key = (gait, cls, stop, squeeze)
                    if key in cache:
                        return cache[key]
                    per, bad = [], set()
                    for k, (I, O) in enumerate(pairs):
                        objs, lab = objl[k]
                        bg = info[k][0]
                        byd = {}
                        for oid, p, d in ports[k]:
                            if gait is None or (d in ORTH) != (cls == 'o') or d in bad:
                                continue
                            cells, h = _cast(I, lab, bg, oid, p, _steps(d, gait), stop, squeeze,
                                             O if strict[k] else None)
                            hits[0] |= h
                            spent[0] += 1 + (len(cells) if cells else 0)
                            if cells is None:     # this direction would paint a cell that stays background
                                bad.add(d)
                                byd.pop(d, None)
                                continue
                            byd.setdefault(d, []).append((oid, p, d, cells))
                        per.append(byd)
                    allowed = tuple(d for d in CLASS_DIRS[cls] if d not in bad) if gait else ()
                    cache[key] = None if gait is not None and not allowed else (per, allowed)
                    return cache[key]

                for stop, squeeze in EDGE_VARIANTS:
                    if (stop, squeeze) == (True, False) and not hits[0] & 2:
                        continue
                    if (stop, squeeze) == (False, False) and not hits[0] & 1:
                        continue
                    for og in ORTH_GAITS:
                        for dg in DIAG_GAITS:
                            if og is None and dg is None:
                                continue
                            if spent[0] > MARCH_BUDGET:
                                return
                            ro = rays_for(og, 'o', stop, squeeze)
                            rd = ro and rays_for(dg, 'd', stop, squeeze)
                            if not rd:
                                continue
                            head = (objmode, sel, mode, stop, squeeze, og, dg)
                            P = _fit(pairs, objl, info, col_opts, ro, rd, spent, head, True)
                            if P:
                                yield (_name(P), 3, _make(P))
                                return
                            if P is None:   # covered, but only a direction subset might fit: try later
                                deferred.append((objl, ro, rd, head))
    # second pass: emission restricted to a subset of compass directions
    for objl, ro, rd, head in deferred:
        if spent[0] > MARCH_BUDGET:
            return
        P = _fit(pairs, objl, info, col_opts, ro, rd, spent, head, False)
        if P:
            yield (_name(P), 3, _make(P))
            return


def _cover(per, dirs, k):
    return {c for d in dirs for *_, cells in per[k].get(d, ()) for c in cells}


def _fit(pairs, objl, info, col_opts, ro, rd, spent, head, full_only):
    """-> parameters P, or False (cannot fit), or None (full direction sets fail; subsets untried)."""
    (po, ao), (pd, ad) = ro, rd
    # coverage with every allowed direction; then which directions are indispensable
    for k, (bg, ch) in enumerate(info):
        cov = _cover(po, ao, k) | _cover(pd, ad, k)
        if any(c not in cov for c in ch):
            return False
    og, dg = head[5], head[6]
    full = (not og or ao == ORTH) and (not dg or ad == DIAG)
    if full_only:        # first pass: symmetric emission in every compass direction of each class
        return (full and _fit_colours(pairs, objl, info, col_opts, po, pd, ao, ad, spent, head)) or None
    need = set()
    for per, allowed in ((po, ao), (pd, ad)):
        for d in allowed:
            rest = [x for x in allowed if x != d]
            for k, (bg, ch) in enumerate(info):
                other = (po, ao) if per is pd else (pd, ad)
                cov = _cover(per, rest, k) | _cover(other[0], other[1], k)
                if any(c not in cov for c in ch):
                    need.add(d)
                    break
    for so in (_subsets(ao, need) if ao else [()]):
        for sd in (_subsets(ad, need) if ad else [()]):
            if spent[0] > MARCH_BUDGET:
                return False
            res = _fit_colours(pairs, objl, info, col_opts, po, pd, so, sd, spent, head)
            if res:
                return res
    return False


def _fit_colours(pairs, objl, info, col_opts, po, pd, so, sd, spent, head):
    objmode, sel, mode, stop, squeeze, og, dg = head
    # 1. every ray needs one colour: the output colours on the cells only it covers must agree
    per_pair, axes = [], set()
    opts = {'o': list(col_opts) if so else [None], 'd': list(col_opts) if sd else [None]}
    for k, (I, O) in enumerate(pairs):
        objs = objl[k][0]
        rays = [('o' if d in ORTH else 'd', oid, p, d, cells)
                for per, dirs in ((po, so), (pd, sd)) for d in dirs for oid, p, d, cells in per[k].get(d, ())]
        cover = Counter(c for *_, cells in rays for c in cells)
        spent[0] += len(cover)
        for cls, oid, p, d, cells in rays:
            want = {O[r][c] for (r, c) in cells if cover[(r, c)] == 1}
            if len(want) > 1:
                return None
            if want:        # 2. keep only the colour roles that give this ray that colour
                w = want.pop()
                opts[cls] = [o for o in opts[cls] if _colour(I, objs, oid, p, o) == w]
                if not opts[cls]:
                    return None
            axes.add(AXIS[d])
        per_pair.append(rays)
    present = [a for a in AXES if a in axes]
    for oc in opts['o']:
        for dc in opts['d']:
            coloured, bad = [], False
            for k, rays in enumerate(per_pair):
                I, objs = pairs[k][0], objl[k][0]
                cr = []
                for cls, oid, p, d, cells in rays:
                    col = _colour(I, objs, oid, p, oc if cls == 'o' else dc)
                    if col is None:
                        bad = True
                        break
                    cr.append((d, col, cells))
                if bad:
                    break
                coloured.append(cr)
            if bad:
                continue
            # 3. z-order: which ray axis is drawn on top where rays cross
            for perm in permutations(present):
                order = tuple(perm) + tuple(a for a in AXES if a not in axes)
                if all(_render(I, cr, order) == O for (I, O), cr in zip(pairs, coloured)):
                    P = head + (oc, dc, so, sd, order)
                    if all(_make(P)(I) == O for I, O in pairs):
                        return P
    return None


FAMILIES = (fam_ray_casting,)
