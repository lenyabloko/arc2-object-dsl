"""Own primitive (no Codex code): slide-until-contact.

One parametrised primitive: every mover unit is translated along one of 4 directions until the next
step would hit a blocking cell (contact mode) or leave the grid, or (through mode) straight to the
grid edge ignoring obstacles, optionally painting the swept cells with an induced trail colour.
All parameters are induced from the training pairs:
  movers   : a colour set (a single colour whose cells change, or the whole set of changing colours)
  objects  : 4-conn single colour | 8-conn single colour | 4-conn multi colour
  unit     : whole object | 1-wide strips parallel to the motion axis
  floor    : global background | local background (the colour the unit sits on: region-aware)
  direction: const d | map(key->d) with key in {colour, hollow, open-concavity, size-threshold,
             region colour} | context {away from the anchor it touches, toward the full static line,
             away from the grid edge it touches}; 'stay' is an allowed map value
  recolour : optional map(key->colour) when moved units change colour by class
  stop     : contact | through(+trail colour)
The map / context is fitted from observed per-unit displacements in the training outputs; the search
harness then verifies the resulting program exactly on all pairs.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import product
from gdsl import H, W, bg_of, fit_cmap, apply_cmap, static_colours

DIRS = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}
OPP = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ------------------------------------------------------------------ objects and units
def components(g, M, diag, byc):
    h, w = H(g), W(g); seen = set(); out = []
    nb = N4 + (((-1, -1), (-1, 1), (1, -1), (1, 1)) if diag else ())
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or g[r][c] not in M: continue
            col = g[r][c]; st = [(r, c)]; seen.add((r, c)); cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and g[yy][xx] in M \
                            and (not byc or g[yy][xx] == col):
                        seen.add((yy, xx)); st.append((yy, xx))
            out.append(sorted(cells))
    return out


def strips(cells, axis):
    """Split an object into maximal contiguous 1-wide runs along axis ('v' = columns, 'h' = rows)."""
    s = set(cells); out = []
    for y, x in sorted(cells, key=(lambda p: (p[1], p[0])) if axis == 'v' else (lambda p: p)):
        prev = (y - 1, x) if axis == 'v' else (y, x - 1)
        if prev in s: continue
        run = []; cy, cx = y, x
        while (cy, cx) in s:
            run.append((cy, cx)); cy, cx = (cy + 1, cx) if axis == 'v' else (cy, cx + 1)
        out.append(run)
    return out


# ------------------------------------------------------------------ unit features
def floor_of(g, cells, allmov, gbg, local):
    if not local: return gbg
    s = set(cells); cnt = Counter()
    for y, x in cells:
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H(g) and 0 <= xx < W(g) and (yy, xx) not in s and (yy, xx) not in allmov:
                cnt[g[yy][xx]] += 1
    return cnt.most_common(1)[0][0] if cnt else gbg


def bbox_bg_split(cells):
    """(has enclosed hole, has open concavity) wrt the object's bounding box."""
    s = set(cells); ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
    empty = {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s}
    if not empty: return False, False
    outside = {(y, x) for (y, x) in empty if y in (r0, r1) or x in (c0, c1)}
    st = list(outside); seen = set(outside)
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            p = (y + dy, x + dx)
            if p in empty and p not in seen: seen.add(p); st.append(p)
    return len(seen) < len(empty), bool(seen)


def key_fns():
    return {
        'colour': lambda u: tuple(sorted({u['g'][y][x] for y, x in u['cells']})),
        'hollow': lambda u: u['shape'][0],
        'open': lambda u: u['shape'][1],
        'region': lambda u: u['floor'],
    }


# ------------------------------------------------------------------ contextual directions
def ctx_away_contact(u):
    g, s, fl = u['g'], set(u['cells']), u['floor']; sides = set()
    for y, x in u['cells']:
        for d, (dy, dx) in DIRS.items():
            yy, xx = y + dy, x + dx
            if 0 <= yy < H(g) and 0 <= xx < W(g) and (yy, xx) not in s and (yy, xx) not in u['allmov'] \
                    and g[yy][xx] != fl:
                sides.add(d)
    return OPP[next(iter(sides))] if len(sides) == 1 else 'stay'


def full_lines(g, fl):
    rows = [r for r in range(H(g)) if len(set(g[r])) == 1 and g[r][0] != fl]
    cols = [c for c in range(W(g)) if len({g[r][c] for r in range(H(g))}) == 1 and g[0][c] != fl]
    return rows, cols


def ctx_toward_line(u):
    rows, cols = u['lines']; ys = [y for y, _ in u['cells']]; xs = [x for _, x in u['cells']]
    best = None
    for r in rows:
        if r > max(ys): cand = (r - max(ys), 'down')
        elif r < min(ys): cand = (min(ys) - r, 'up')
        else: continue
        if best is None or cand[0] < best[0]: best = cand
    for c in cols:
        if c > max(xs): cand = (c - max(xs), 'right')
        elif c < min(xs): cand = (min(xs) - c, 'left')
        else: continue
        if best is None or cand[0] < best[0]: best = cand
    return best[1] if best else 'stay'


def ctx_away_edge(u):
    g = u['g']; ys = [y for y, _ in u['cells']]; xs = [x for _, x in u['cells']]
    t = [d for d, hit in (('down', min(ys) == 0), ('up', max(ys) == H(g) - 1),
                           ('right', min(xs) == 0), ('left', max(xs) == W(g) - 1)) if hit]
    return t[0] if len(t) == 1 else 'stay'


CTX = {'away-contact': ctx_away_contact, 'toward-line': ctx_toward_line, 'away-edge': ctx_away_edge}


# ------------------------------------------------------------------ units of a grid under a config
def make_units(g, M, omode, local, unit):
    gbg = bg_of(g)
    kind, arg = M
    M = {v for r in g for v in r} - {gbg}
    if kind == 'excl': M -= arg
    elif kind == 'only': M &= arg
    if gbg in M: return None
    diag, byc = omode
    objs = components(g, M, diag, byc)
    if not objs or len(objs) > 40: return None
    allmov = {p for ob in objs for p in ob}
    units = []
    for ob in objs:
        parts = [ob] if unit == 'obj' else strips(ob, unit)
        for cells in parts:
            fl = floor_of(g, cells, allmov, gbg, local)
            units.append({'g': g, 'cells': cells, 'floor': fl, 'allmov': allmov,
                          'size': len(ob), 'shape': bbox_bg_split(ob)})
    lines = full_lines(g, gbg)
    incol = {v for r in g for v in r}
    for u in units: u['lines'] = lines; u['incol'] = incol
    return units


# ------------------------------------------------------------------ simulation
def simulate(g, units, dirs, stop, trail, recol):
    h, w = H(g), W(g)
    out = [r[:] for r in g]
    pos = []
    for u, d in zip(units, dirs):
        pos.append([(y, x, g[y][x]) for y, x in u['cells']])
    if stop == 'through':
        paint = []
        for u, d, cur in zip(units, dirs, pos):
            for y, x, _ in cur: out[y][x] = u['floor']
        for i, (u, d) in enumerate(zip(units, dirs)):
            if d == 'stay': paint.append(pos[i]); continue
            dy, dx = DIRS[d]; cur = pos[i]; swept = []
            while all(0 <= y + dy < h and 0 <= x + dx < w for y, x, _ in cur):
                swept += [(y, x) for y, x, _ in cur]
                cur = [(y + dy, x + dx, c) for y, x, c in cur]
            if trail is not None:
                for y, x in swept: out[y][x] = trail
            paint.append(cur)
        for i, cur in enumerate(paint):
            for y, x, c in cur: out[y][x] = recol[i] if recol and recol[i] is not None else c
        return out
    # contact: step-wise simultaneous-ish settling, leading units first
    order = sorted(range(len(units)), key=lambda i: 0 if dirs[i] == 'stay' else
                   -max(y * DIRS[dirs[i]][0] + x * DIRS[dirs[i]][1] for y, x, _ in pos[i]))
    moving = True; guard = 0
    while moving and guard < 64:
        moving = False; guard += 1
        for i in order:
            d = dirs[i]
            if d == 'stay': continue
            dy, dx = DIRS[d]; cur = pos[i]; own = {(y, x) for y, x, _ in cur}; fl = units[i]['floor']
            k = 0
            while True:
                nxt = [(y + dy, x + dx) for y, x, _ in cur]
                if any(not (0 <= y < h and 0 <= x < w) or ((y, x) not in own and out[y][x] != fl)
                       for y, x in nxt):
                    break
                for y, x, _ in cur: out[y][x] = fl
                cur = [(y + dy, x + dx, c) for y, x, c in cur]
                for y, x, c in cur: out[y][x] = c
                own = {(y, x) for y, x, _ in cur}; k += 1
            if k: moving = True; pos[i] = cur
    if recol:
        for i, cur in enumerate(pos):
            if recol[i] is not None:
                for y, x, _ in cur: out[y][x] = recol[i]
    return out


# ------------------------------------------------------------------ induction from training
def observe(u, o):
    """Directions (and resulting uniform colour, or None if colours kept) consistent with the output."""
    g = u['g']; h, w = H(g), W(g); res = {}
    cells = u['cells']
    if all(o[y][x] == g[y][x] for y, x in cells): res['stay'] = None
    for d, (dy, dx) in DIRS.items():
        for k in range(1, max(h, w)):
            sh = [(y + dy * k, x + dx * k) for y, x in cells]
            if any(not (0 <= y < h and 0 <= x < w) for y, x in sh): break
            if all(o[y2][x2] == g[y][x] for (y, x), (y2, x2) in zip(cells, sh)):
                res.setdefault(d, None)
            else:
                cs = {o[y2][x2] for y2, x2 in sh}
                if len(cs) == 1 and len({g[y][x] for y, x in cells}) == 1:
                    c = next(iter(cs))
                    if c not in u['incol'] and d not in res: res[d] = c
    return res


def mover_sets(train):
    """Mover colour roles: all non-background | non-background minus the static colours | one colour
    whose cells change."""
    ch = set()
    for p in train:
        i, o = p['input'], p['output']
        for y in range(H(i)):
            for x in range(W(i)):
                if i[y][x] != o[y][x]: ch.add(i[y][x])
    out = [('nonbg', None)]
    st = frozenset(static_colours(train) - {bg_of(p['input']) for p in train})
    if st: out.append(('excl', st))
    out += [('only', frozenset([c])) for c in sorted(ch)]
    return out


def allowed(ob):
    """Directions consistent with an observation: a unit seen in place may have been blocked."""
    return set(ob) | (set(DIRS) if 'stay' in ob else set())


def colour_for(ob, d):
    return ob[d] if d in ob else ob.get('stay')


def fit(train_units, obs, keyname):
    """Yield (dir source, recolour map or None) consistent with the observations."""
    flat = [(u, ob) for us, os_ in zip(train_units, obs) for u, ob in zip(us, os_)]
    if keyname in CTX:
        f = CTX[keyname]; rec = {}
        for u, ob in flat:
            d = f(u)
            if d not in allowed(ob): return
            c = colour_for(ob, d)
            if rec.setdefault(d, c) != c: return
        yield 'ctx', (rec if any(v is not None for v in rec.values()) else None)
        return
    if keyname.startswith('size>'):
        t = int(keyname[5:]); kf = lambda u: u['size'] > t
    elif keyname == 'const':
        kf = lambda u: 0
    else:
        kf = key_fns()[keyname]
    cand = {}
    for u, ob in flat:
        k = kf(u); a = allowed(ob)
        cand[k] = cand[k] & a if k in cand else a
        if not cand[k]: return
    opts = {}
    for k, s in cand.items():
        mv = sorted(s - {'stay'})
        opts[k] = ['stay'] if 'stay' in s and len(mv) == 4 else mv
        if not opts[k]: return
    ks = sorted(opts, key=str); n = 0
    for combo in product(*[opts[k] for k in ks]):
        dmap = dict(zip(ks, combo))
        if all(v == 'stay' for v in dmap.values()): continue
        rec = {}; ok = True
        for u, ob in flat:
            k = kf(u); c = colour_for(ob, dmap[k])
            if rec.setdefault(k, c) != c: ok = False; break
        if not ok: continue
        yield (kf, dmap), (rec if any(v is not None for v in rec.values()) else None)
        n += 1
        if n >= 4: return


def fam_slide_until_contact(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    if all(p['input'] == p['output'] for p in train): return
    yielded = 0
    for M in mover_sets(train):
        for omode in ((False, True), (True, True), (False, False)):
            for local in (False, True):
                for unit in ('obj', 'v', 'h'):
                    TU = [make_units(p['input'], M, omode, local, unit) for p in train]
                    if any(t is None for t in TU): continue
                    OB = [[observe(u, p['output']) for u in us] for us, p in zip(TU, train)]
                    if any(not ob for os_ in OB for ob in os_): continue
                    sizes = sorted({u['size'] for us in TU for u in us})
                    keys = ['const', 'colour', 'hollow', 'open', 'region'] + \
                           ['size>%d' % s for s in sizes[:-1]] + list(CTX)
                    if unit != 'obj':
                        keys = ['const', 'colour', 'region'] + list(CTX)
                    for kn in keys:
                      for dsrc, rec in fit(TU, OB, kn):
                        for stop in ('contact', 'through'):
                            trail = None
                            prog = make_prog(M, omode, local, unit, kn, dsrc, rec, stop, None)
                            if stop == 'through':
                                trail = induce_trail(train, prog)
                                if trail == 'fail': continue
                                prog = make_prog(M, omode, local, unit, kn, dsrc, rec, stop, trail)
                            if not fits(train, prog): continue
                            name = 'slide:%s[movers=%s,%s%s,%s,unit=%s,dir=%s%s%s]' % (
                                stop, M[0] if M[0] == 'nonbg' else M[0] + '|'.join(map(str, sorted(M[1]))), '8' if omode[0] else '4',
                                '' if omode[1] else ',multi', 'local' if local else 'global', unit, kn,
                                '' if dsrc == 'ctx' else ':' + ','.join('%s>%s' % kv for kv in sorted(dsrc[1].items(), key=str)),
                                ',recolour' if rec else '') + ('' if trail is None else '+trail%d' % trail)
                            yield (name, 4 + (kn != 'const') + (rec is not None) + (trail is not None), prog)
                            yielded += 1
                            if yielded >= 8: return


def make_prog(M, omode, local, unit, kn, dsrc, rec, stop, trail):
    def fn(g):
        units = make_units(g, M, omode, local, unit)
        if not units: return None
        if dsrc == 'ctx':
            dirs = [CTX[kn](u) for u in units]
        else:
            kf, dmap = dsrc
            ks = [kf(u) for u in units]
            if any(k not in dmap for k in ks): return None
            dirs = [dmap[k] for k in ks]
        if all(d == 'stay' for d in dirs): return None
        recol = None
        if rec:
            if dsrc == 'ctx': recol = [rec.get(d) for d in dirs]
            else:
                if any(k not in rec for k in ks): return None
                recol = [rec[k] for k in ks]
        return simulate(g, units, dirs, stop, trail, recol)
    return fn


def fits(train, prog):
    preds = []
    for p in train:
        try: r = prog(p['input'])
        except Exception: return False
        if r is None: return False
        preds.append(r)
    outs = [p['output'] for p in train]
    if preds == outs: return True
    m = fit_cmap(preds, outs)
    return bool(m) and all(apply_cmap(a, m) == b for a, b in zip(preds, outs))


def induce_trail(train, prog):
    """Through mode: the one colour painted on swept cells, or None when no trail is needed."""
    cs = set()
    for p in train:
        r = prog(p['input'])
        if r is None: return 'fail'
        o = p['output']
        cs |= {o[y][x] for y in range(H(o)) for x in range(W(o)) if r[y][x] != o[y][x]}
    if not cs: return None
    return next(iter(cs)) if len(cs) == 1 else 'fail'


FAMILIES = (fam_slide_until_contact,)
