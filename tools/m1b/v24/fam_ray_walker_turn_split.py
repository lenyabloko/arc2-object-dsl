"""ray.walker_turn_split: a walker (ray) leaves a seed and travels straight; when the next cell is
blocked it reacts by an induced POLICY, and every visited background cell is painted.

One engine, one parameter set, all induced from the training pairs:
  seed    - cells of an induced colour s: straight segments (orth or diagonal) emit from both ends
            along their axis; single cells on the grid edge emit away from that edge.
            (spiral: the unique object of colour s - a single cell or a plus; portal: the object whose
            body colour is unique.)
  paint   - the seed colour, or the one colour new in every output.
  policy  -
    split    blocked -> two walkers, perpendicular both ways (and so on recursively)
    flow     global direction d0 (gravity-like): whenever the cell ahead in d0 is free go d0;
             blocked in d0 -> spread sideways both ways; a sideways walker stops when blocked
    reflect  diagonal walker bounces off obstacles (flip the blocked component)
    turn     blocked by colour x -> turn cw / ccw per an induced colour->turn map
    spiral   no deflection by obstacles (they stop the walker); the walker hugs its own/its
             siblings' trail with a 1-cell gap, turning cw/ccw (outward square spiral / pinwheel);
             drawn on a virtual canvas so arms may leave and re-enter the grid
    portal   the walker (a beam as wide as the emitter's marker) enters the object it hits, the
             object takes the paint colour and the beam re-emerges from that object's marker cells
             in the marker direction; objects never reached are erased (or kept)
Obstacles = non-background cells that are neither seed nor paint colour."""
import sys; sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import product
from gdsl import H, W, bg_of, objects

ORTH = ((-1, 0), (0, 1), (1, 0), (0, -1))          # N E S W  (cw order)


def cw(d): return (d[1], -d[0])
def ccw(d): return (-d[1], d[0])


def _same_shape(train):
    return all(H(p['input']) == H(p['output']) and W(p['input']) == W(p['output']) for p in train)


def _new_colour(train):
    s = None
    for p in train:
        new = {v for r in p['output'] for v in r} - {v for r in p['input'] for v in r}
        if len(new) != 1: return None
        c = next(iter(new))
        if s is not None and c != s: return None
        s = c
    return s


def _only_bg_changes(train):
    for p in train:
        i, o = p['input'], p['output']; bg = bg_of(i)
        for y in range(H(i)):
            for x in range(W(i)):
                if i[y][x] != o[y][x] and i[y][x] != bg: return False
    return True


# ---------------------------------------------------------------- seeds
def _line_dir(cells):
    """Return unit axis (dy,dx) if cells form one straight contiguous line of length>=2, else None."""
    cells = sorted(cells)
    if len(cells) < 2: return None
    dy, dx = cells[1][0] - cells[0][0], cells[1][1] - cells[0][1]
    if max(abs(dy), abs(dx)) != 1: return None
    for a, b in zip(cells, cells[1:]):
        if (b[0] - a[0], b[1] - a[1]) != (dy, dx): return None
    return (dy, dx)


def _emitters(g, s, bg):
    """List of (y,x,dy,dx): walker positions (the seed end) and headings."""
    h, w = H(g), W(g); out = []
    for ob in objects(g, bg, True, True):
        if g[ob[0][0]][ob[0][1]] != s: continue
        if len(ob) == 1:
            y, x = ob[0]; ds = []
            if y == 0: ds.append((1, 0))
            if y == h - 1: ds.append((-1, 0))
            if x == 0: ds.append((0, 1))
            if x == w - 1: ds.append((0, -1))
            if len(ds) != 1: continue
            out.append((y, x) + ds[0])
            continue
        d = _line_dir(ob)
        if d is None: return None
        cs = sorted(ob)
        out.append(cs[-1] + d); out.append(cs[0] + (-d[0], -d[1]))
    return out


# ---------------------------------------------------------------- deflecting walkers
def _walk(g, bg, s, paint, emit, policy, tmap=None, minrun=0):
    h, w = H(g), W(g)
    def free(y, x): return g[y][x] in (bg, s, paint)
    def inside(y, x): return 0 <= y < h and 0 <= x < w
    seen = set(); st = []; painted = set()
    for e in emit:
        y, x, dy, dx = e
        if policy == 'reflect' and (dy == 0 or dx == 0): return None
        if policy != 'reflect' and dy and dx: return None
        st.append((y, x, dy, dx, (dy, dx), min(1, minrun)))
    guard = 0
    while st:
        guard += 1
        if guard > 40000: return None
        stt = st.pop()
        if stt in seen: continue
        seen.add(stt); y, x, dy, dx, d0, mv = stt
        painted.add((y, x))
        if policy == 'flow':
            ay, ax = y + d0[0], x + d0[1]
            if (dy, dx) != d0:
                if not inside(ay, ax): continue
                if free(ay, ax): st.append((y, x) + d0 + (d0, 0)); continue
        ny, nx = y + dy, x + dx
        if not inside(ny, nx): continue
        if free(ny, nx): st.append((ny, nx, dy, dx, d0, min(mv + 1, minrun))); continue
        if mv < minrun: continue
        if policy == 'split':
            for nd in (cw((dy, dx)), ccw((dy, dx))): st.append((y, x) + nd + (d0, 0))
        elif policy == 'flow':
            if (dy, dx) == d0:
                for nd in (cw(d0), ccw(d0)): st.append((y, x) + nd + (d0, 0))
        elif policy == 'turn':
            t = tmap.get(g[ny][nx])
            if t is None: return None
            nd = cw((dy, dx)) if t == 'cw' else ccw((dy, dx))
            st.append((y, x) + nd + (d0, 0))
        elif policy == 'reflect':
            by = inside(y + dy, x) and not free(y + dy, x)
            bx = inside(y, x + dx) and not free(y, x + dx)
            if by and not bx: nd = (-dy, dx)
            elif bx and not by: nd = (dy, -dx)
            else: nd = (-dy, -dx)
            st.append((y, x) + nd + (d0, 0))
    out = [r[:] for r in g]
    for y, x in painted:
        if g[y][x] == bg: out[y][x] = paint
    return out


def fam_walker(train):
    if not _same_shape(train) or not _only_bg_changes(train): return
    i0 = train[0]['input']; bg0 = bg_of(i0)
    common = set.intersection(*[{v for r in p['input'] for v in r} for p in train]) - {bg0}
    newc = _new_colour(train)
    n = 0
    for s in sorted(common):
        ems = [_emitters(p['input'], s, bg_of(p['input'])) for p in train]
        if any(not e for e in ems): continue
        paints = [('seed', s)] + ([('new', newc)] if newc is not None else [])
        obst = sorted({v for p in train for r in p['input'] for v in r} - {bg0, s} - {c for _, c in paints})
        for pn, pc in paints:
            pols = [('split', None), ('split2', None), ('flow', None), ('reflect', None)]
            oc = [c for c in obst if c != pc]
            if 1 <= len(oc) <= 3:
                for combo in product(('cw', 'ccw'), repeat=len(oc)):
                    if len(set(combo)) == 1: continue
                    pols.append(('turn', dict(zip(oc, combo))))
            for pol, tm in pols:
                def fn(g, s=s, pc=pc, pol=pol, tm=tm):
                    bg = bg_of(g); e = _emitters(g, s, bg)
                    if not e: return None
                    if pol == 'split2': return _walk(g, bg, s, pc, e, 'split', tm, 2)
                    return _walk(g, bg, s, pc, e, pol, tm)
                # cheap prefilter on train[0]
                p0 = train[0]
                if fn(p0['input']) != p0['output']: continue
                tag = pol if tm is None else 'turn[' + ','.join(f'{k}:{v}' for k, v in sorted(tm.items())) + ']'
                n += 1
                yield (f'walker[seed={s},paint={pn},policy={tag}]', 4 if tm is None else 5, fn)
                if n > 20: return


# ---------------------------------------------------------------- spiral / pinwheel
def _spiral(g, bg, s, arms, rot, runin, recent=3):
    """Lockstep walkers that keep a 1-cell gap from everything painted except their own last
    `recent` cells, preferring to turn toward `rot` (hug), else straight, else away."""
    h, w = H(g), W(g); P = 2 * max(h, w) + 4
    turn, unturn = (cw, ccw) if rot == 'cw' else (ccw, cw)
    painted = set()
    for y in range(h):
        for x in range(w):
            if g[y][x] == s: painted.add((y, x))
    walkers = []
    for (y, x, d) in arms:
        trail = [(y, x)]; yy, xx = y - d[0], x - d[1]
        while (yy, xx) in painted and len(trail) < recent: trail.insert(0, (yy, xx)); yy -= d[0]; xx -= d[1]
        walkers.append([y, x, d, 0, True, trail])
    NB = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    def ok(c, own):
        if c in painted: return False
        for a, b in NB:
            n = (c[0] + a, c[1] + b)
            if n in painted and n not in own: return False
        return True
    steps = 0
    while any(wk[4] for wk in walkers):
        for wk in walkers:
            if not wk[4]: continue
            steps += 1
            if steps > 200000: return None
            y, x, d, k, _, trail = wk
            own = set(trail[-recent:])
            opts = [turn(d), d, unturn(d)] if k >= runin else [d]
            nd = None
            for o in opts:
                if ok((y + o[0], x + o[1]), own): nd = o; break
            if nd is None: wk[4] = False; continue
            ny, nx = y + nd[0], x + nd[1]
            if not (-P <= ny < h + P and -P <= nx < w + P): wk[4] = False; continue
            if 0 <= ny < h and 0 <= nx < w and g[ny][nx] not in (bg, s): wk[4] = False; continue
            painted.add((ny, nx)); trail.append((ny, nx))
            if len(trail) > recent: del trail[0]
            wk[:4] = [ny, nx, nd, k + 1]
    out = [r[:] for r in g]
    for y, x in painted:
        if 0 <= y < h and 0 <= x < w and g[y][x] == bg: out[y][x] = s
    return out


def _spiral_seed(g, s, bg):
    obs = [ob for ob in objects(g, bg, True, True) if g[ob[0][0]][ob[0][1]] == s]
    if len(obs) != 1: return None
    ob = set(obs[0])
    if len(ob) == 1: return ('single', next(iter(ob)))
    ys = [y for y, _ in ob]; xs = [x for _, x in ob]
    if (min(ys) + max(ys)) % 2 or (min(xs) + max(xs)) % 2: return None
    cy, cx = (min(ys) + max(ys)) // 2, (min(xs) + max(xs)) // 2
    arms = []
    for d in ORTH:
        y, x = cy + d[0], cx + d[1]; last = None
        while (y, x) in ob: last = (y, x); y += d[0]; x += d[1]
        if last is None: return None
        arms.append(last + (d,))
    return ('plus', arms)


def fam_spiral(train):
    if not _same_shape(train) or not _only_bg_changes(train): return
    i0 = train[0]['input']; bg0 = bg_of(i0)
    for s in sorted({v for r in i0 for v in r} - {bg0}):
        kinds = [_spiral_seed(p['input'], s, bg_of(p['input'])) for p in train]
        if any(k is None for k in kinds) or len({k[0] for k in kinds}) != 1: continue
        kind = kinds[0][0]
        dirs = ORTH if kind == 'single' else (None,)
        for d0, rot, runin in product(dirs, ('cw', 'ccw'), (0, 1, 2)):
            def fn(g, s=s, d0=d0, rot=rot, runin=runin):
                bg = bg_of(g); sd = _spiral_seed(g, s, bg)
                if sd is None or sd[0] != kind: return None
                arms = [sd[1] + (d0,)] if kind == 'single' else sd[1]
                return _spiral(g, bg, s, arms, rot, runin)
            p0 = train[0]
            if fn(p0['input']) != p0['output']: continue
            yield (f'walker[seed={s},policy=spiral[{kind},{d0},{rot},runin={runin}]]', 5, fn)


# ---------------------------------------------------------------- portal (enter object, exit via marker)
def _marker_dir(ob, g):
    cnt = Counter(g[y][x] for y, x in ob)
    if len(cnt) != 2: return None
    body, mk = [c for c, _ in cnt.most_common()]
    bc = [(y, x) for y, x in ob if g[y][x] == body]; mc = [(y, x) for y, x in ob if g[y][x] == mk]
    obs, bs = set(ob), set(bc)
    ds = [d for d in ORTH if all((y + d[0], x + d[1]) not in obs and (y - d[0], x - d[1]) in bs for y, x in mc)]
    if len(ds) != 1: return None
    return body, mk, mc, ds[0]


def _portal(g, keep, sb=None):
    bg = bg_of(g); h, w = H(g), W(g)
    obs = objects(g, bg, False, False)
    info = []
    for ob in obs:
        m = _marker_dir(ob, g)
        if m is None: return None
        info.append(m)
    bodies = Counter(m[0] for m in info)
    seeds = [k for k, m in enumerate(info) if bodies[m[0]] == 1 and (sb is None or m[0] == sb)]
    if len(seeds) != 1 or len(info) < 2: return None
    sk = seeds[0]; paint = info[sk][0]
    owner = {}
    for k, ob in enumerate(obs):
        for c in ob: owner[c] = k
    out = [r[:] for r in g]
    if not keep:
        for ob in obs:
            for y, x in ob: out[y][x] = bg
    visited = {sk}; queue = [sk]
    while queue:
        k = queue.pop()
        for y, x in obs[k]: out[y][x] = paint
        _, _, mc, d = info[k]
        beam = list(mc)
        for _ in range(h + w):
            beam = [(y + d[0], x + d[1]) for y, x in beam]
            ins = [(y, x) for y, x in beam if 0 <= y < h and 0 <= x < w]
            if not ins: break
            hit = {owner[c] for c in ins if c in owner} - {k}
            if hit:
                for j in hit:
                    if j not in visited: visited.add(j); queue.append(j)
                break
            for y, x in ins: out[y][x] = paint
    return out


def _unique_bodies(g):
    bg = bg_of(g); info = [_marker_dir(ob, g) for ob in objects(g, bg, False, False)]
    if not info or any(m is None for m in info): return set()
    cnt = Counter(m[0] for m in info)
    return {c for c, n in cnt.items() if n == 1}


def fam_portal(train):
    if not _same_shape(train): return
    sbs = set.intersection(*[_unique_bodies(p['input']) for p in train])
    if len(sbs) != 1: return
    sb = sbs.pop()
    for keep in (False, True):
        fn = lambda g, keep=keep: _portal(g, keep, sb)
        if fn(train[0]['input']) != train[0]['output']: continue
        yield (f'walker[policy=portal,seed_body={sb},unreached={"keep" if keep else "erase"}]', 5, fn)


# ---------------------------------------------------------------- key-palette staircase walker
def _squares(g):
    """Solid k x k single-colour squares (k>=2) that are whole 4-connected components."""
    out = []
    for ob in objects(g, -1, False, True):
        ys = [y for y, _ in ob]; xs = [x for _, x in ob]
        hh, ww = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
        if hh == ww >= 2 and hh * ww == len(ob): out.append((min(ys), min(xs), hh, g[ob[0][0]][ob[0][1]], ob))
    return out


def _key(g):
    """Key = the largest row (>=2) of equal squares on the same rows, read left to right; terminal = the
    one other square of that size. Returns (palette, terminal colour, cells to erase) or None."""
    sq = _squares(g)
    rows = {}
    for q in sq: rows.setdefault((q[0], q[2]), []).append(q)
    best = max(rows.values(), key=len, default=[])
    if len(best) < 2: return None
    best.sort(key=lambda q: q[1]); k = best[0][2]
    gaps = {b[1] - a[1] for a, b in zip(best, best[1:])}
    if len(gaps) != 1: return None
    others = [q for q in sq if q[2] == k and q not in best]
    if len(others) > 1: return None
    pal = [q[3] for q in best]
    term = others[0][3] if others else None
    r0, c0 = best[0][0], best[0][1]; r1, c1 = r0 + k - 1, best[-1][1] + k - 1
    erase = [[(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)]] + ([others[0][4]] if others else [])
    return pal, term, erase


def _stair(g, first):
    h, w = H(g), W(g)
    kk = _key(g)
    if kk is None: return None
    pal, term, erase = kk
    out = [r[:] for r in g]
    for cells in erase:
        ring = Counter()
        cs = set(cells)
        for y, x in cells:
            for dy, dx in ORTH:
                n = (y + dy, x + dx)
                if n not in cs and 0 <= n[0] < h and 0 <= n[1] < w: ring[g[n[0]][n[1]]] += 1
        if not ring: return None
        fill = ring.most_common(1)[0][0]
        for y, x in cells: out[y][x] = fill
    base = [r[:] for r in out]
    seeds = []
    for y in range(h):
        for x in range(w):
            if base[y][x] != pal[0] or not (y in (0, h - 1) or x in (0, w - 1)): continue
            ds = [d for d, c in (((1, 0), y == 0), ((-1, 0), y == h - 1), ((0, 1), x == 0), ((0, -1), x == w - 1)) if c]
            if len(ds) != 1: continue
            seeds.append((y, x, ds[0]))
    if not seeds: return None
    for y, x, d in seeds:
        ny, nx = y + d[0], x + d[1]
        if not (0 <= ny < h and 0 <= nx < w): return None
        free = base[ny][nx]
        i = 0; t = first; steps = 0
        while True:
            steps += 1
            if steps > 4 * h * w: return None
            ny, nx = y + d[0], x + d[1]
            if not (0 <= ny < h and 0 <= nx < w): break
            if base[ny][nx] == free:
                y, x = ny, nx; i += 1; out[y][x] = pal[i % len(pal)]; continue
            if term is not None: out[ny][nx] = term
            d = cw(d) if t == 'cw' else ccw(d); t = 'ccw' if t == 'cw' else 'cw'
            ny, nx = y + d[0], x + d[1]
            if not (0 <= ny < h and 0 <= nx < w) or base[ny][nx] != free: break
    return out


def fam_stair(train):
    if not _same_shape(train): return
    if _key(train[0]['input']) is None: return
    for first in ('ccw', 'cw'):
        fn = lambda g, first=first: _stair(g, first)
        if fn(train[0]['input']) != train[0]['output']: continue
        yield (f'walker[policy=alternate({first}),paint=key_cycle,mark=terminal]', 6, fn)


FAMILIES = (fam_walker, fam_spiral, fam_portal, fam_stair)
