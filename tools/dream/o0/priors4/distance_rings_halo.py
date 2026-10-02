"""Prior family v4: distance_rings_halo  (SURROUND by a distance field), colour parameters re-bound to roles.
priors4 (Fable v11, D38 / G68): every colour parameter is a declared role of colour_roles.py (background,
rank_colour(k), novel_colour) or a role-bound value (the colour of a named participant); no literal colour numbers.
Non-colour parameters, steps and the enumeration order are those of priors3; the wall-clock budget of priors3 is
replaced by step counts (_STEPS candidate programs, _WORK halo-field cells per task).

One generator: compute, for every cell, its lattice distance d (Chebyshev = 8-neighbour squares, or
Manhattan = 4-neighbour diamonds) to a source set, then paint cells by d:
    halo   : colour c on every background cell with d <= k            (a frame / halo of thickness k)
    rings  : palette[(d - d0) mod P] on every background cell          (concentric rings / ripples)
    ridge  : colour c on the cells equidistant from two walls (medial axis), the rest cleared
Sources (participants), read from each input:
    object anchors  shape | bbox | centre (bbox centre, offset by the object's circumradius)
    regions         room (4-components of non-wall cells, wall = ink rank 1) | canvas | object (multi-colour object)
    point           centre of the bbox of all non-background cells | fit (off-grid centre on which the seeds form
                    complete rings) | seeds (every non-background cell of a field room)
Palette (rings): printed by the seeds | legend room in reading order | stripe profile of the input; strike in
    {none, clipped} (struck legend entries take the wall colour).
Parameters (small finite domains, induced from the training pairs only):
    metric in {cheb, manh} ; k in {1, 2, 3, count, msize, half, size, clear, 0} ; fit in {clip, shrink}
    halo colour in {object.minority, object's own colour, legend partner, role map}
    role map: ink rank of the object colour -> role (novel | ink rank), both in every training input
    rays colour (secondary layer): role (novel | ink rank) ; unprinted ring entries: keep | role (novel | ink rank)
    erase in {keep, erase} the seed markers (they become background)
Colour roles used: background = CR.background(g) (ties now by lower colour number; priors3 used first occurrence);
    wall = CR.rank_colour(g, 1) (the 2nd most frequent colour); novel = CR.novel_colour(train); ink rank k =
    CR.rank_colour(g, k); participant colours: object minority / own colour, legend partner, seed colour, legend
    sequence, stripe profile.

BINDINGS (G68) -- per member, the literal colour value priors3 induced and the role it became
("LOST: needs literal c" = no declared role explains it; the member no longer fits).
  13e47133  wall <- rank1 ; palette <- seed colours (participants) ; unprinted <- keep               FITS
  3a301edc  halo colour <- object.minority (participant)                                             FITS
  45a5af55  palette <- stripe profile of the input (participant)                                     FITS
  52fd389e  halo colour <- object.minority                                                           FITS
  5adee1b2  halo colour <- legend partner of the object colour (participant)                         FITS
  5c2c9af4  palette <- seed colour (participant)                                                     FITS
  8cb8642d  ridge colour <- object.minority ; cleared cells <- background                            FITS
  9356391f  palette <- legend room ; struck entries <- wall (rank1)                                  FITS
  c97c0139  map{2->8} <- map{rank1 -> novel}                                                         FITS
  f8c80d96  unprinted entries 5 <- novel                                                             FITS
  fc754716  frame colour <- the seed's colour (participant) ; erased seed <- background              FITS
  db93a21d  map{9->3}: key 9 <- rank1, halo 3 and rays 1  LOST: needs literal 3, 1 (two colours new in the
            outputs, so novel_colour is undefined; neither is an input colour)
  ff72ca3e  map{4->2}: halo 2 <- novel, key 4  LOST: needs literal 4 (4 is ink rank 1 in pairs 1-3 only by the
            tie-break, rank 2 in pair 4; the other single-colour object (5) must get no halo)
  Unfitted in priors3 and still unfitted: b457fec5, e2092e0c, fd4b2b02.
Literal colours removed: halo colour map (object colour -> colour), rays colour, unprinted-ring colour (enumerated
over the output colours), wall/background by first occurrence (-> CR roles).
"""
from collections import Counter, deque

import colour_roles as CR

CARD = "prior4_distance_rings_halo"
CONCEPT = "distance_rings_halo"
MEMBERS = ['13e47133', '3a301edc', '45a5af55', '52fd389e', '5adee1b2', '5c2c9af4', '8cb8642d', '9356391f',
           'b457fec5', 'c97c0139', 'db93a21d', 'e2092e0c', 'f8c80d96', 'fc754716', 'fd4b2b02', 'ff72ca3e']
READING = {
    "generator": "compute every cell's Chebyshev/Manhattan distance d to a source set (object shape, bbox or "
                 "centre ball, room walls / canvas border / object rim, a seed point or every seed) and paint "
                 "cells colour c while d <= k (halo/frame), palette[d mod P] (concentric rings; palette printed "
                 "by the seeds or read from a legend / stripe profile) or c on the ridge (equidistant cells)",
    "stop": "halo: d > k (k from a constant, a count, a size or the largest clear ball); rings: grid / room "
            "edge (periodic palette never stops) or the end of the legend",
    "params": "metric in {cheb, manh} . anchor in {shape, bbox, centre, room, canvas, object, point, fit, "
              "seeds} . k in {1,2,3,count,msize,half,size,clear,0} . fit in {clip, shrink} . colour in "
              "{minority, self, legend, map(ink rank -> novel | ink rank)} . palette in {printed, legend, profile} "
              ". P in {span, step} . fill in {keep, novel, ink rank} . rays colour in {novel, ink rank} . "
              "erase in {0,1} . strike in {none, clipped} . outer in {first, last}",
    "participants": "background = role background; objects = 8-connected non-background components "
                    "(main colour = most frequent, minority = least frequent); rooms = 4-components of "
                    "non-wall cells (wall = ink rank 1, the 2nd most frequent colour); legend room = room with the most "
                    "distinct colours; seeds = non-bg cells inside a room / around a point; profile = "
                    "uniform rows (or columns) of the input",
    "preconditions": "same in/out size (except the profile canvas); every changed cell was background, an "
                     "erased seed, a struck legend entry or a cell of a multi-colour object (ridge); some "
                     "cell changes",
}

_N8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_STEPS = 400          # cap on candidate programs tried per task (step count; no wall-clock cut-off)
_WORK = 400000        # cap on halo-field work per task (cells visited, see _halo_field_w); step count, not time


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
    """role background: the most frequent colour of the grid (ties -> lower colour number)."""
    return CR.background(g)


# ------------------------------------------------------------------------------------------ colour roles (G68)
RANKS = CR.RANKS


def _target_role(train, bgs, idx, t, N):
    """the role naming colour t in every training input of idx: novel colour | ink rank k (None if no role)."""
    if not idx:
        return None
    if N is not None and t == N:
        return ('novel',)
    for k in RANKS:
        if all(CR.rank_colour(train[i]['input'], k, bgs[i]) == t for i in idx):
            return ('rank', k)
    return None


def _resolve(role, g, bg, N):
    if role[0] == 'novel':
        return N
    return CR.rank_colour(g, role[1], bg)


def _role_name(r):
    return 'novel' if r[0] == 'novel' else 'rank%d' % r[1]


def _role_map(train, bgs, objss, lit, N):
    """literal object colour -> halo colour map -> ((key rank k, target role), ...): the key is the ink rank naming the
    object colour, the target a role (novel | ink rank), both in every training input holding such an object.
    None when some entry has no role."""
    out = []
    for c in sorted(lit):
        idx = [i for i, os in enumerate(objss) if any(o['ncol'] == 1 and o['main'] == c for o in os)]
        if not idx:
            return None
        key = next((k for k in RANKS
                    if all(CR.rank_colour(train[i]['input'], k, bgs[i]) == c for i in idx)), None)
        tgt = _target_role(train, bgs, idx, lit[c], N)
        if key is None or tgt is None:
            return None
        if any(k == key for k, _ in out):
            return None
        out.append((key, tgt))
    return tuple(out)


def _resolve_map(g, bg, rmap, N):
    out = {}
    for k, tgt in rmap:
        c, v = CR.rank_colour(g, k, bg), _resolve(tgt, g, bg, N)
        if c is not None and v is not None:
            out.setdefault(c, v)
    return out


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
    return _halo_field_w(g, bg, objs, anchor, metric, rule, fit)[0]


def _halo_field_w(g, bg, objs, anchor, metric, rule, fit):
    """(field, work): work = deterministic count of the cells the field computation visits (stored with the memo,
    so a step cap built on it does not depend on what is cached)."""
    key = ('halo', _gkey(g), bg, tuple(o['cells'][0] for o in objs), anchor, metric, rule, fit)
    return _memo(key, lambda: _halo_field_raw(g, bg, objs, anchor, metric, rule, fit))


def _halo_field_raw(g, bg, objs, anchor, metric, rule, fit):
    H, W = len(g), len(g[0])
    best = {}
    work = len(objs)
    nonbg = sum(1 for row in g for v in row if v != bg) if rule == 'clear' else 0
    for i, o in enumerate(objs):
        if rule == 'clear':                      # grid scan + distance to every foreign non-background cell
            n = len(o['cells'])
            work += H * W + ((nonbg - n) * n if anchor == 'shape' and (nonbg - n) * n <= 40000 else nonbg - n)
        k = _k(rule, o, anchor, metric, g, bg, H, W, fit)
        if k is None:
            continue
        dist = _anchor_dist(o, anchor, metric, H, W, k)
        work += len(dist)
        hole = _holes(g, bg, o) if anchor == 'bbox' else ()
        for p, d in dist.items():
            if g[p[0]][p[1]] != bg or p in hole:
                continue
            b = best.get(p)
            if b is None or d < b[0]:
                best[p] = (d, i)
    return best, work


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


def _make_halo(anchor, metric, rule, fit, role, rmap, shadow=None, N=None):
    """rmap: role-keyed halo colour map (role 'map'); shadow: (direction, colour role).  Resolved on each grid."""
    def fn(g):
        bg = _bg(g)
        objs = _objects(g, bg)
        out = [row[:] for row in g]
        legend = _legend(g, objs) if role == 'legend' else {}
        cmap = _resolve_map(g, bg, rmap, N) if role == 'map' else {}
        srcs = [o for o in objs if _colour_of(o, role, cmap, legend) is not None]
        if shadow:
            sc = _resolve(shadow[1], g, bg, N)
            if sc is None:
                return None
            dy, dx = _DIRS[shadow[0]]
            for y, x in _rays(g, bg, srcs, dy, dx):
                out[y][x] = sc
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
        wall = CR.rank_colour(g, 1, bg)                 # wall <- ink colour of rank 1 (2nd most frequent colour)
        if wall is None:
            return None
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


def _make_rings(source, metric, prule, frole, N=None):
    """frole: colour role of the unprinted palette entries (None = keep background), resolved on each grid."""
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        fill = None
        if frole is not None:
            fill = _resolve(frole, g, bg, N)
            if fill is None:
                return None
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


# ----------------------------------------------------------------------- v3: legend / profile / ridge
def _legend_split(g, bg):
    """(legend cells in reading order, legend sequence, field rooms, wall) or None.

    Legend room = the room (cut off by the wall) with the most distinct non-bg colours (>= 2); the
    sequence is its colours in reading order, trailing background trimmed.  Field rooms = the others."""
    rr = _regions(g, bg, 'room')
    if rr is None:
        return None
    rooms, wall = rr
    if len(rooms) < 2:
        return None
    best = None
    for i, room in enumerate(rooms):
        nc = len({g[y][x] for y, x in room} - {bg})
        key = (nc, -len(room))
        if nc >= 2 and (best is None or key > best[0]):
            best = (key, i)
    if best is None:
        return None
    li = best[1]
    cells = sorted(rooms[li])
    seq = [g[y][x] for y, x in cells]
    while seq and seq[-1] == bg:
        seq.pop()
    if len(seq) < 2 or len(seq) > max(len(g), len(g[0])):
        return None
    return cells, seq, [r for i, r in enumerate(rooms) if i != li], wall


def _make_legend_rings(metric, strike):
    """Rings around every seed of the field rooms; ring d gets legend[d] (background entries keep)."""
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        ls = _legend_split(g, bg)
        if ls is None:
            return None
        lcells, seq, fields, wall = ls
        L = len(seq)
        out = [row[:] for row in g]
        struck = set()
        for room in fields:
            inside = set(room)
            seeds = [p for p in room if g[p[0]][p[1]] != bg]
            if not seeds or len(seeds) > 8:
                continue
            for p in room:
                d = min(_dm(metric, p[0] - s[0], p[1] - s[1]) for s in seeds)
                if d < L and seq[d] != bg:
                    out[p[0]][p[1]] = seq[d]
            if strike:
                for sy, sx in seeds:
                    for d in range(L):
                        for y in range(sy - d, sy + d + 1):
                            hit = False
                            for x in range(sx - d, sx + d + 1):
                                if _dm(metric, y - sy, x - sx) == d and (y, x) not in inside:
                                    hit = True; break
                            if hit:
                                struck.add(d); break
        for d in struck:
            y, x = lcells[d]
            out[y][x] = wall
        return out
    return fn


def _stripes(g, orient):
    rows = g if orient == 'rows' else [list(r) for r in zip(*g)]
    prof = []
    for r in rows:
        if any(v != r[0] for v in r):
            return None
        prof.append(r[0])
    return prof


def _make_profile_canvas(orient, outer):
    """Canvas rings with palette <- the input's stripe profile read from the rim (outer end) inwards.

    axis <- middle of the innermost stripe run; canvas side <- twice the axis distance (odd run -> the
    axis passes through a cell); cell colour = profile[canvas rim distance - 1]."""
    def fn(g):
        prof = _stripes(g, orient)
        if prof is None or len(prof) < 2:
            return None
        if outer == 'last':
            prof = prof[::-1]
        r = 1
        while r < len(prof) and prof[-1 - r] == prof[-1]:
            r += 1
        L = len(prof) - r + (r + 1) // 2
        N = 2 * L if r % 2 == 0 else 2 * L - 1
        if N > 60:
            return None
        return [[prof[min(i, j, N - 1 - i, N - 1 - j)] for j in range(N)] for i in range(N)]
    return fn


def _make_ridge(k):
    """Every multi-colour object is a room: rim (d <= k) kept, deeper cells cleared, and the ridge (cells
    whose nearest wall is reached along two axis directions at the same distance) painted the minority colour."""
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        did = False
        for o in _objects(g, bg):
            if o['ncol'] < 2:
                continue
            S = set(o['cells']); c = o['minor']
            for (y, x) in S:
                ds = []
                for dy, dx in _N4:
                    n = 0; yy, xx = y, x
                    while (yy, xx) in S:
                        n += 1; yy += dy; xx += dx
                    ds.append(n)
                m = min(ds)
                if m <= k:
                    continue
                out[y][x] = c if ds.count(m) >= 2 else bg
                did = True
        return out if did else None
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


def _fam_v2(train, steps, N):
    """The v2 search (halo / frame / printed rings); colour parameters re-bound to roles (G68)."""
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
    # unprinted ring entries: roles (novel | ink rank) naming an output colour in every pair, deduplicated by value
    fill_roles, seenv = [], set()
    for role in ([('novel',)] if N is not None else []) + [('rank', k) for k in RANKS]:
        vals = tuple(_resolve(role, p['input'], bg, N) for p, bg in zip(train, bgs))
        if any(v is None or v == bg or not any(v in r for r in p['output'])
               for v, p, bg in zip(vals, train, bgs)) or vals in seenv:
            continue
        seenv.add(vals)
        fill_roles.append(role)
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
                            steps[0] += 1
                            if steps[0] > _STEPS:
                                return
                            # every painted cell must lie in the halo, or else be one colour (ray layer);
                            # fields are built pair by pair and the candidate dropped as soon as that fails
                            fields, rcols = [], set()
                            for p, bg, os, ch in zip(train, bgs, objss, chg):
                                f, w = _halo_field_w(p['input'], bg, os, anchor, metric, rule, fit)
                                steps[1] += w
                                if steps[1] > _WORK:
                                    return
                                fields.append(f)
                                rcols |= {v for q, v in ch.items() if q not in f}
                                if len(rcols) > 1:
                                    break
                            if len(rcols) > 1:
                                prev = None
                                continue
                            if fields == prev:
                                continue
                            prev = fields
                            if not any(fields):
                                continue
                            shadows = [None]
                            if rcols:
                                sr = _target_role(train, bgs, list(range(len(train))), rcols.pop(), N)
                                if sr is None:
                                    continue                  # ray colour has no role (would need a literal)
                                shadows = [(nm, sr) for nm in _DIRS]
                            for role in roles:
                                rmap = ()
                                if role == 'map':
                                    cmap = _induce_cmap(train, bgs, objss, anchor, metric, rule, fit)
                                    if not cmap:
                                        continue
                                    rmap = _role_map(train, bgs, objss, cmap, N)
                                    if not rmap:
                                        continue              # some key / halo colour has no role
                                hit = False
                                for sh in shadows:
                                    fn = _make_halo(anchor, metric, rule, fit, role, rmap, sh, N)
                                    if ok(fn):
                                        tag = role
                                        if role == 'map':
                                            tag = 'map{%s}' % ','.join('rank%d>%s' % (k, _role_name(t)) for k, t in rmap)
                                        yield ('surround:halo[anchor=%s,metric=%s,k=%s,fit=%s,colour=%s%s]'
                                               % (anchor, metric, rule, fit, tag,
                                                  ',rays=%s:%s' % (sh[0], _role_name(sh[1])) if sh else ''),
                                               1 + cost * 0.01, fn)
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
                    steps[0] += 1
                    if steps[0] > _STEPS:
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
                for fill in [None] + fill_roles:
                    steps[0] += 1
                    if steps[0] > _STEPS:
                        return
                    fn = _make_rings(source, metric, prule, fill, N)
                    if ok(fn):
                        yield ('surround:rings[source=%s,metric=%s,P=%s,fill=%s]'
                               % (source, metric, prule, 'keep' if fill is None else _role_name(fill)), 3, fn)
                        found += 1
                        if found >= 2:
                            return
                        break


def fam(train):
    steps = [0, 0]
    if not train:
        return

    def ok(fn):
        return _fits(fn, train)

    same = all(len(p['input']) == len(p['output']) and len(p['input'][0]) == len(p['output'][0])
               for p in train)
    if not same:
        # 0. canvas rebuilt around the stripe profile (palette <- profile, axis <- innermost run middle)
        for orient in ('rows', 'cols'):
            if not all(_stripes(p['input'], orient) for p in train):
                continue
            for outer in ('first', 'last'):
                fn = _make_profile_canvas(orient, outer)
                if ok(fn):
                    yield ('surround:rings[source=canvas,palette=profile,orient=%s,outer=%s,axis=run-middle]'
                           % (orient, outer), 3, fn)
                    return
        return
    found = 0
    N = CR.novel_colour(train)                   # role novel_colour, fixed by the training pairs
    for item in _fam_v2(train, steps, N):
        yield item
        found += 1
    if found >= 2:
        return
    bgs = [_bg(p['input']) for p in train]
    if not any(a != b for p in train for ra, rb in zip(p['input'], p['output']) for a, b in zip(ra, rb)):
        return
    # 4. rings around every seed, palette <- legend room (optionally strike clipped entries)
    if all(_legend_split(p['input'], bg) is not None for p, bg in zip(train, bgs)):
        for metric in ('cheb', 'manh'):
            for strike in (False, True):
                steps[0] += 1
                if steps[0] > _STEPS:
                    return
                fn = _make_legend_rings(metric, strike)
                if ok(fn):
                    yield ('surround:rings[source=seeds,metric=%s,palette=legend,strike=%s]'
                           % (metric, 'clipped' if strike else 'none'), 3, fn)
                    found += 1
                    if found >= 2:
                        return
                    break
    # 5. ridge (medial axis) of every multi-colour object, colour <- object.minority, rim kept
    if all(any(o['ncol'] >= 2 for o in _objects(p['input'], bg)) for p, bg in zip(train, bgs)):
        for k in (1, 2):
            steps[0] += 1
            if steps[0] > _STEPS:
                return
            fn = _make_ridge(k)
            if ok(fn):
                yield ('surround:ridge[source=object,metric=cheb,k=%d,colour=minority,erase=1]' % k, 3, fn)
                return


FAMILIES = [fam]
