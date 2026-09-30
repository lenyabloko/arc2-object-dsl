"""FLUIDS prior: common-sense hydraulics on the grid, used as a general search space.

Laws (the prior)
----------------
The medium is the background colour; every other colour is solid unless it is the fluid itself.
Gravity g is one of the four lattice directions; every engine runs in the frame where g points 'down'.
  L1 gravity      a fluid parcel moves along g whenever the next cell is free.
  L2 support      a parcel blocked along g (by a wall, standing fluid or a closed floor) spreads perpendicular
                  to g, both ways, along the supporting surface; where the support ends it falls again
                  (waterfalls that wrap obstacles; films that run along walls and pass through their gaps).
  L3 hydrostatics a horizontal layer of fluid that is supported everywhere and bounded by walls at both ends is
                  at rest (level free surface); a basin therefore fills up to its SPILL level and then
                  overflows by L2.
  L4 conservation a finite body of fluid keeps its volume: parcels (lowest first, repeated to equilibrium)
                  descend to the lowest cell they can reach by falling or sliding along a support
                  (communicating vessels level out; fluid above a rim spills into the next basin).
  L5 thin stream  the zero-volume limit of L1-L2: a trickle does not split; blocked along g it slides to the
                  NEAREST point from which it can fall again (least detour; tie -> induced side), or always to
                  one side when the surface is tilted; it stops when both ways are blocked.
  L6 pressure     an incompressible fluid injected into a container fills its interior; at every gap in the
                  container wall it escapes as a jet running straight outward (normal to that wall) until an
                  obstacle or the grid edge, optionally with a spray: diagonal rays fanning out from the
                  gap's rims.  A container is a wall set whose openings are all GAPS (flanked by wall cells).

Search space (every parameter induced from the training pairs; unseen situations refuse -> None)
  fluid colour F   a non-background colour present in every training input (sources / liquid / marker), the
                   role 'minor' (least frequent non-bg colour of the grid), or 'multi': all colours that grow in
                   every pair, each pouring its own colour (colliding colours refuse)
  paint            F itself, or the constant colour of all changed cells (induced, may be new)
  gravity          down | up | left | right | edge (each source flows away from the grid edge it touches);
                   frames are rotations, so 'lo'/'hi' sides keep one rotational sense for every gravity
  source term      infinite (F cells are springs) | finite (F cells ARE the liquid, volume conserved) |
                   rain (every cell of the top edge is a spring)
  boundaries       floor open (fluid leaves the grid) / closed; sides open / closed (walls)
  render           wet (every wetted cell) | standing (fluid at rest: basins) | two-tone (flowing and standing
                   fluid in two induced colours); sources kept / drained
  trickle policy   nearest (tie lo/hi side) | one-sided lo/hi (tilted surface) | tilt table: obstacle colour ->
                   side (each obstacle colour is a surface tilted one way)
  jets             container = each single-colour 8-connected object (any colour / induced colour) or all cells
                   of one colour (induced colour / the most frequent non-bg colour); fluid = the unique
                   marker colour inside the container, or the induced constant colour; spray on/off

Families kept (full eval: training 1000 + dev-eval half A; each solves >= 3 tasks, WRONG = 0)
  fluid:gravity  L1-L4   36a08778 (half A: streams wrap bars), 28a6681f (half A: conserved liquid settles into
                         basins, spill-over into the next basin), f9a67cb5 (films run along walls, through gaps)
  fluid:trickle  L5      c87289bb (nearest end, tie), d9f24cd1 (rising streams), 712bf12e (one-sided / tilted),
                         96a8c0cd (tilt table: obstacle colour -> side)
  fluid:jet      L6      d4f3cd78, 292dd178, 551d5bf1 (fill + jet through the gap), aba27056 (with spray),
                         78e78cff (bracket container, marker colour, jets through every gap)
Dropped after measurement (0 tasks fit on the training pairs): contagion along the object adjacency graph
(diffusion/infection between touching objects), competing diffusion from several sources (geodesic Voronoi
flood), look-ahead trickles (shortest remaining path), a 'standing + film' render (fluid at rest on every
surface).  Plain flood fill from seeds is left to prior_topology (seed-region) / distance layers.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter, deque
from itertools import product
from gdsl import H, W, r90, r180, r270, bg_of, objects, bbox

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
# frames: (to, back) ROTATIONS so that the gravity direction becomes 'down' (orientation preserved, so the
# frame's +x side is the same rotational sense - counter-clockwise of the flow - for every gravity)
FRAMES = {"down": (lambda g: [r[:] for r in g], lambda g: [r[:] for r in g]), "up": (r180, r180),
          "right": (r90, r270), "left": (r270, r90)}
GRAVITIES = ('down', 'up', 'left', 'right', 'edge')
MAXC = 200


# ------------------------------------------------------------------ induction helpers
def same_shape(train):
    return all(H(p['input']) == H(p['output']) and W(p['input']) == W(p['output']) for p in train)


def const_colour(train):
    """The single colour taken by every changed cell of every training pair (None if not unique)."""
    cs = {p['output'][y][x] for p in train for y in range(H(p['input'])) for x in range(W(p['input']))
          if p['input'][y][x] != p['output'][y][x]}
    return next(iter(cs)) if len(cs) == 1 else None


def common_colours(train):
    return sorted(set.intersection(*[{v for r in p['input'] for v in r} for p in train]) - {bg_of(train[0]['input'])})


def growing_colours(train):
    """Colours whose cell count grows in every training pair."""
    res = None
    for p in train:
        a = Counter(v for r in p['input'] for v in r); b = Counter(v for r in p['output'] for v in r)
        s = {c for c in b if b[c] > a[c] and a[c] > 0}
        res = s if res is None else res & s
    return sorted(res or ())


def edge_dir(cells, h, w):
    ds = set()
    for y, x in cells:
        if y == 0: ds.add('down')
        if y == h - 1: ds.add('up')
        if x == 0: ds.add('right')
        if x == w - 1: ds.add('left')
    return ds.pop() if len(ds) == 1 else None


def resolve(g, bg, Fs):
    """Source colours: literal tuple, or a role resolved on the grid ('minor' = least frequent non-bg colour)."""
    if Fs != 'minor': return Fs
    cs = Counter(v for r in g for v in r if v != bg)
    if len(cs) < 2: return None
    (a, na), (b, nb) = cs.most_common()[-1], cs.most_common()[-2]
    return (a,) if na < nb else None


def source_groups(g, bg, Fs, gravity):
    """[(gravity dir, colour, cells)]: one group per source colour, or per source object for 'edge' gravity."""
    h, w = H(g), W(g); groups = []
    Fs = resolve(g, bg, Fs)
    if not Fs: return None
    for F in Fs:
        cells = [(y, x) for y in range(h) for x in range(w) if g[y][x] == F]
        if not cells: continue
        if gravity != 'edge':
            groups.append((gravity, F, cells)); continue
        for ob in objects(g, bg, True, True):
            if g[ob[0][0]][ob[0][1]] != F: continue
            d = edge_dir(ob, h, w)
            if d is None: return None
            groups.append((d, F, ob))
    return groups


def in_frame(g, gdir, cells):
    """Grid and a cell mask transformed into the gravity frame."""
    to, _ = FRAMES[gdir]
    mark = [[0] * W(g) for _ in range(H(g))]
    for y, x in cells: mark[y][x] = 1
    gg = to(g); mm = to(mark)
    return gg, [(y, x) for y in range(H(gg)) for x in range(W(gg)) if mm[y][x]]


def from_frame(cells, gdir, hf, wf):
    _, back = FRAMES[gdir]
    lay = [[0] * wf for _ in range(hf)]
    for y, x in cells: lay[y][x] = 1
    lay = back(lay)
    return [(y, x) for y in range(H(lay)) for x in range(W(lay)) if lay[y][x]]


def paint_layers(g, layers, bg, erase=()):
    """layers: [(colour, cells)]; cells painted only over background; conflicting colours refuse."""
    out = [r[:] for r in g]
    for y, x in erase: out[y][x] = bg
    got = {}
    for c, cells in layers:
        for y, x in cells:
            if got.setdefault((y, x), c) != c: return None
            out[y][x] = c
    return out


# ------------------------------------------------------------------ engines (gravity frame: down)
def reservoir(free, h, w, sources, floor, sides):
    """L1-L3 with infinite springs.  Returns (wet, standing) cell sets or None."""
    src = set(sources); standing = set(); wet = set(src)
    def openc(y, x): return 0 <= y < h and 0 <= x < w and (free[y][x] or (y, x) in src) and (y, x) not in standing
    def solid(y, x):
        if y >= h: return floor
        if x < 0 or x >= w: return sides
        return not openc(y, x)
    stack = list(src); dirty = {y for y, _ in src}
    for _ in range(3000):
        while stack:
            y, x = stack.pop()
            if (y, x) in standing: continue
            if y + 1 < h and openc(y + 1, x):
                if (y + 1, x) not in wet: wet.add((y + 1, x)); stack.append((y + 1, x)); dirty.add(y + 1)
                continue
            if y + 1 >= h and not floor: continue
            for nx in (x - 1, x + 1):
                if openc(y, nx) and (y, nx) not in wet:
                    wet.add((y, nx)); stack.append((y, nx)); dirty.add(y)
        newly = []
        for y in sorted(dirty):
            xs = sorted(x for (yy, x) in wet if yy == y and (yy, x) not in standing)
            i = 0
            while i < len(xs):
                j = i
                while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1: j += 1
                a, b = xs[i], xs[j]
                if solid(y, a - 1) and solid(y, b + 1) and all(solid(y + 1, x) for x in range(a, b + 1)):
                    newly.extend((y, x) for x in range(a, b + 1))
                i = j + 1
        dirty = set()
        if not newly: return wet, standing
        standing.update(newly)
        for y, x in newly:
            if (y - 1, x) in wet and (y - 1, x) not in standing: stack.append((y - 1, x)); dirty.add(y - 1)
    return None


def settle(free, h, w, liquid, floor, sides):
    """L4: finite volume.  Parcels processed lowest first, repeated until nothing moves; each goes to the
    lowest cell reachable by falling (unsupported) or sliding sideways (supported); ties -> nearest, stay.
    A parcel that can reach an open floor / open side leaves the grid."""
    occ = set(liquid)
    def openc(y, x): return 0 <= y < h and 0 <= x < w and free[y][x] and (y, x) not in occ
    for _ in range(60):
        moved = False
        for c in sorted(occ, key=lambda c: (-c[0], c[1])):
            occ.discard(c)
            dist = {c: 0}; q = deque([c]); best = None; drain = False
            while q and not drain:
                y, x = q.popleft()
                if y + 1 >= h:
                    if not floor: drain = True; break
                    sup = True
                else:
                    sup = not openc(y + 1, x)
                if sup:
                    key = (y, -dist[(y, x)], (y, x) == c)
                    if best is None or key > best[0]: best = (key, (y, x))
                    nb = ((y, x - 1), (y, x + 1))
                else:
                    nb = ((y + 1, x),)
                for yy, xx in nb:
                    if not 0 <= xx < w:
                        if not sides: drain = True
                        continue
                    if (yy, xx) not in dist and openc(yy, xx):
                        dist[(yy, xx)] = dist[(y, x)] + 1; q.append((yy, xx))
            if drain or best is None:
                moved = True; continue
            d = c if best[0][0] == c[0] else best[1]
            occ.add(d)
            if d != c: moved = True
        if not moved: return occ
    return None


SIDES = {'lo': (-1, 1), 'hi': (1, -1), 'lo!': (-1,), 'hi!': (1,)}


def trickle_paths(free, h, w, starts, policy, gg=None):
    """L5: thin streams from the start cells; returns the set of visited cells.  policy: a side rule, or a
    dict obstacle colour -> side rule (surfaces of each colour tilted one way; gg = the grid in the frame)."""
    painted = set()
    def ok(y, x): return 0 <= y < h and 0 <= x < w and (free[y][x] or (y, x) in painted)
    for sy, sx in starts:
        y, x = sy, sx
        for _ in range(4 * (h + w)):
            painted.add((y, x))
            if y + 1 >= h: break
            if ok(y + 1, x): y += 1; continue
            if isinstance(policy, dict):
                rule = policy.get(gg[y + 1][x])
                if rule is None: return None
                order = SIDES[rule]
            else:
                order = SIDES[policy]
            best = None
            for side in order:
                k = 1
                while ok(y, x + side * k):
                    if ok(y + 1, x + side * k):
                        if best is None or k < best[0]: best = (k, side)
                        break
                    k += 1
            if best is None: break
            k, side = best
            for j in range(1, k + 1): painted.add((y, x + side * j))
            x += side * k
    return painted


# ------------------------------------------------------------------ family 1: gravity-driven liquid (L1-L4)
def simulate(g, bg, Fs, gravity, source, floor, sides):
    """Physics only (no colours): [(F, erase cells, wet cells, standing cells)] in grid coordinates."""
    if source == 'rain':
        if gravity == 'edge': return None
        gg, _ = in_frame(g, gravity, [])
        h, w = H(gg), W(gg)
        free = [[gg[y][x] == bg for x in range(w)] for y in range(h)]
        res = reservoir(free, h, w, [(0, x) for x in range(w) if free[0][x]], floor, sides)
        if res is None: return None
        return [(None, [], from_frame([c for c in res[0] if free[c[0]][c[1]]], gravity, h, w),
                 from_frame([c for c in res[1] if free[c[0]][c[1]]], gravity, h, w))]
    groups = source_groups(g, bg, Fs, gravity)
    if not groups or sum(len(cs) for _, _, cs in groups) > MAXC: return None
    sim = []
    for gdir, F, cells in groups:
        gg, s = in_frame(g, gdir, cells)
        h, w = H(gg), W(gg)
        if source == 'finite':
            free = [[gg[y][x] == bg or gg[y][x] == F for x in range(w)] for y in range(h)]
            occ = settle(free, h, w, s, floor, sides)
            if occ is None: return None
            res = from_frame(occ, gdir, h, w)
            sim.append((F, cells, res, res))
        else:
            free = [[gg[y][x] == bg for x in range(w)] for y in range(h)]
            res = reservoir(free, h, w, s, floor, sides)
            if res is None: return None
            wet, standing = res
            sim.append((F, cells, from_frame([c for c in wet | standing if free[c[0]][c[1]]], gdir, h, w),
                        from_frame([c for c in standing if free[c[0]][c[1]]], gdir, h, w)))
    return sim


def render_liquid(g, bg, sim, source, paint, render, keep):
    """render: 'wet' | 'standing' | ('two', flowing colour, standing colour)."""
    if sim is None: return None
    layers = []; erase = []
    for F, cells, wet, standing in sim:
        if isinstance(render, tuple):
            st = set(standing)
            layers.append((render[1], [c for c in wet if c not in st])); layers.append((render[2], standing))
        else:
            pc = F if paint is None else paint
            if pc is None: return None
            layers.append((pc, wet if render == 'wet' else standing))
        if source == 'finite' or not keep: erase.extend(cells)
    return paint_layers(g, layers, bg, erase)


def gravity_liquid(g, bg, Fs, gravity, source, floor, sides, paint, render, keep):
    """Fs: source/liquid colours (empty for rain).  paint: None -> each source's own colour."""
    return render_liquid(g, bg, simulate(g, bg, Fs, gravity, source, floor, sides), source, paint, render, keep)


def fam_fluid_gravity(train):
    if not same_shape(train): return
    i0, o0 = train[0]['input'], train[0]['output']
    if i0 == o0: return
    bg0 = bg_of(i0)
    changed = {o0[y][x] for y in range(H(i0)) for x in range(W(i0)) if i0[y][x] != o0[y][x]}
    cc = const_colour(train)
    srcsets = [(str(F), (F,)) for F in common_colours(train)]
    grow = growing_colours(train)
    if len(grow) >= 2: srcsets.append(('multi', tuple(grow)))
    mi = resolve(i0, bg0, 'minor')
    if mi and all(resolve(p['input'], bg_of(p['input']), 'minor') for p in train): srcsets.append(('minor', 'minor'))
    n = 0
    two = sorted(changed - {bg0})                  # flowing and standing fluid drawn in two induced colours
    for (fname, Fs), source in product(srcsets, ('infinite', 'finite')):
        F0 = resolve(i0, bg0, Fs)
        paints = [('own', None)] + ([('c%d' % cc, cc)] if cc is not None and (cc,) != F0 else [])
        # the only colours a program can write are its paint colours (and bg where sources drain)
        views = []
        for pn, pc in paints:
            if not changed <= (set(F0) if pc is None else {pc}) | {bg0}: continue
            if source == 'finite': views.append((pn, pc, 'wet', False))
            else: views += [(pn, pc, r, k) for r, k in product(('wet', 'standing'), (True, False))]
        if source == 'infinite' and len(two) == 2:
            views += [('own', None, ('two', a, b), k) for a, b in (two, two[::-1]) for k in (True, False)]
        if not views: continue
        if source == 'finite':
            geo = [(gr, fl, sd) for gr in GRAVITIES[:4] for fl, sd in product((True, False), (True, False))]
        else:
            geo = [(gr, fl, sd) for gr in GRAVITIES for fl, sd in product((False, True), (False, True))]
        for gravity, floor, sides in geo:
            sim = simulate(i0, bg0, Fs, gravity, source, floor, sides)
            if sim is None: continue
            for pn, pc, render, keep in views:
                if render_liquid(i0, bg0, sim, source, pc, render, keep) != o0: continue
                def fn(g, Fs=Fs, gravity=gravity, source=source, floor=floor, sides=sides, pc=pc, render=render, keep=keep):
                    return gravity_liquid(g, bg_of(g), Fs, gravity, source, floor, sides, pc, render, keep)
                n += 1
                rn = render if isinstance(render, str) else f'flow=c{render[1]}/still=c{render[2]}'
                yield (f"fluid:gravity[F{fname},{pn},{gravity},{source},{'floor' if floor else 'nofloor'},"
                       f"{'walls' if sides else 'open'},{rn}{'' if keep else ',drain'}]", 4, fn)
                if n >= 12: return
    if cc is not None and changed <= {cc}:
        for gravity, floor, sides in product(GRAVITIES[:4], (False, True), (False, True)):
            sim = simulate(i0, bg0, (), gravity, 'rain', floor, sides)
            for render in ('standing', 'wet'):
                if render_liquid(i0, bg0, sim, 'rain', cc, render, True) != o0: continue
                def fn(g, gravity=gravity, floor=floor, sides=sides, render=render):
                    return gravity_liquid(g, bg_of(g), (), gravity, 'rain', floor, sides, cc, render, True)
                n += 1
                yield (f"fluid:gravity[rain,c{cc},{gravity},{'floor' if floor else 'nofloor'},{'walls' if sides else 'open'},{render}]", 4, fn)
                if n >= 16: return


# ------------------------------------------------------------------ family 2: thin streams (L5)
def trickle(g, bg, Fs, gravity, policy, paint):
    groups = source_groups(g, bg, Fs, gravity)
    if not groups: return None
    if sum(len(cs) for _, _, cs in groups) > MAXC: return None
    layers = []
    for gdir, F, cells in groups:
        gg, s = in_frame(g, gdir, cells)
        h, w = H(gg), W(gg); ss = set(s)
        free = [[gg[y][x] == bg or gg[y][x] == F for x in range(w)] for y in range(h)]
        starts = [(y, x) for y, x in s if (y + 1, x) not in ss]         # leading cells of each source
        tp = trickle_paths(free, h, w, starts, policy, gg)
        if tp is None: return None
        cells = [(y, x) for y, x in tp if gg[y][x] == bg]
        layers.append((F if paint is None else paint, from_frame(cells, gdir, h, w)))
    return paint_layers(g, layers, bg)


def fam_fluid_trickle(train):
    if not same_shape(train): return
    i0, o0 = train[0]['input'], train[0]['output']
    if i0 == o0: return
    cc = const_colour(train)
    srcsets = [(str(F), (F,)) for F in common_colours(train)]
    grow = growing_colours(train)
    if len(grow) >= 2: srcsets.append(('multi', tuple(grow)))
    n = 0
    bg0 = bg_of(i0)
    changed = {o0[y][x] for y in range(H(i0)) for x in range(W(i0)) if i0[y][x] != o0[y][x]}
    if bg0 in changed: return
    mi = resolve(i0, bg0, 'minor')
    if mi and all(resolve(p['input'], bg_of(p['input']), 'minor') for p in train): srcsets.append(('minor', 'minor'))
    allc = sorted({v for p in train for r in p['input'] for v in r} - {bg0})
    for (fname, Fs), gravity in product(srcsets, GRAVITIES):
        F0 = resolve(i0, bg0, Fs)
        # side rules: uniform (nearest with a tie side, or always one side), or one side per obstacle colour
        obst = [c for c in allc if c not in F0]
        policies = ['lo', 'hi', 'lo!', 'hi!']
        if 2 <= len(obst) <= 3:
            policies += [dict(zip(obst, t)) for t in product(('lo!', 'hi!'), repeat=len(obst)) if len(set(t)) > 1]
        paints = [('own', None)] + ([('c%d' % cc, cc)] if cc is not None and (cc,) != F0 else [])
        for policy, (pn, pc) in product(policies, paints):
            if not changed <= (set(F0) if pc is None else {pc}): continue
            def fn(g, Fs=Fs, gravity=gravity, policy=policy, pc=pc):
                return trickle(g, bg_of(g), Fs, gravity, policy, pc)
            if fn(i0) != o0: continue
            n += 1
            pname = policy if isinstance(policy, str) else 'tilt:' + ','.join(f'c{k}{v}' for k, v in sorted(policy.items()))
            yield (f"fluid:trickle[F{fname},{pn},{gravity},{pname}]", 4 if isinstance(policy, str) else 5, fn)
            if n >= 10: return


# ------------------------------------------------------------------ family 3: pressure jets through gaps (L6)
def _runs(vals):
    vals = sorted(vals); runs = []
    for v in vals:
        if runs and v == runs[-1][1] + 1: runs[-1][1] = v
        else: runs.append([v, v])
    return runs


def jet(g, bg, wall, mode, paint, spray):
    """wall: a colour, None (any colour, 'obj' mode) or 'major' ('colour' mode).  paint: 'marker' or a colour."""
    h, w = H(g), W(g); out = [r[:] for r in g]
    conts = []
    if mode == 'obj':
        for ob in objects(g, bg, True, True):
            if wall is None or g[ob[0][0]][ob[0][1]] == wall: conts.append(ob)
    else:
        wc = wall
        if wc == 'major':
            cs = Counter(v for r in g for v in r if v != bg)
            if not cs: return None
            wc = cs.most_common(1)[0][0]
        cells = [(y, x) for y in range(h) for x in range(w) if g[y][x] == wc]
        if cells: conts.append(cells)
    n = 0
    for ob in conts:
        r0, c0, r1, c1 = bbox(ob)
        if r1 - r0 < 2 or c1 - c0 < 2: continue
        obs = set(ob)
        inner = [(y, x) for y in range(r0 + 1, r1) for x in range(c0 + 1, c1) if (y, x) not in obs]
        if not inner: continue
        marks = [(y, x) for y, x in inner if g[y][x] != bg]
        if paint == 'marker':
            mc = {g[y][x] for y, x in marks}
            if len(mc) != 1: continue
            pc = mc.pop(); seeds = marks
        else:
            if marks: continue
            pc = paint; seeds = inner
        seen = set(seeds); st = list(seeds)
        while st:
            y, x = st.pop()
            for dy, dx in N4:
                yy, xx = y + dy, x + dx
                if r0 <= yy <= r1 and c0 <= xx <= c1 and (yy, xx) not in seen and (yy, xx) not in obs \
                        and g[yy][xx] in (bg, pc):
                    seen.add((yy, xx)); st.append((yy, xx))
        # openings per side: (outward direction) -> positions along the side
        sides = {(-1, 0): [x for y, x in seen if y == r0], (1, 0): [x for y, x in seen if y == r1],
                 (0, -1): [y for y, x in seen if x == c0], (0, 1): [y for y, x in seen if x == c1]}
        runs = {}
        ok = True
        for d, vals in sides.items():
            rs = _runs(vals); runs[d] = rs
            for a, b in rs:           # every opening must be a GAP: flanked by container cells along the side
                if d[0]:
                    fy = r0 if d[0] < 0 else r1
                    if (fy, a - 1) not in obs or (fy, b + 1) not in obs: ok = False
                else:
                    fx = c0 if d[1] < 0 else c1
                    if (a - 1, fx) not in obs or (b + 1, fx) not in obs: ok = False
        if not ok: continue
        n += 1
        for y, x in seen:
            if g[y][x] == bg: out[y][x] = pc
        for (dy, dx), rs in runs.items():
            for a, b in rs:
                fixed = (r0 if dy < 0 else r1) if dy else (c0 if dx < 0 else c1)
                for v in range(a, b + 1):
                    y, x = (fixed, v) if dy else (v, fixed)
                    y += dy; x += dx
                    while 0 <= y < h and 0 <= x < w and g[y][x] == bg:
                        out[y][x] = pc; y += dy; x += dx
                if spray:
                    for end, s in ((a, -1), (b, 1)):
                        if dy: y, x, sy, sx = fixed + dy, end + s, dy, s
                        else: y, x, sy, sx = end + s, fixed + dx, s, dx
                        while 0 <= y < h and 0 <= x < w and g[y][x] == bg:
                            out[y][x] = pc; y += sy; x += sx
    return out if n else None


def fam_fluid_jet(train):
    if not same_shape(train): return
    i0, o0 = train[0]['input'], train[0]['output']
    if i0 == o0: return
    cc = const_colour(train)
    walls = [('obj', c) for c in common_colours(train)] + [('obj', None)] + \
            [('colour', c) for c in common_colours(train)] + [('colour', 'major')]
    paints = ['marker'] + ([cc] if cc is not None else [])
    if bg_of(i0) in {o0[y][x] for y in range(H(i0)) for x in range(W(i0)) if i0[y][x] != o0[y][x]}: return
    for (mode, wall), paint, spray in product(walls, paints, (False, True)):
        def fn(g, mode=mode, wall=wall, paint=paint, spray=spray):
            return jet(g, bg_of(g), wall, mode, paint, spray)
        if fn(i0) != o0: continue
        wn = 'any' if wall is None else (wall if wall == 'major' else 'c%d' % wall)
        yield (f"fluid:jet[{mode}:{wn},{'marker' if paint == 'marker' else 'c%d' % paint}{',spray' if spray else ''}]", 4, fn)


FAMILIES = (fam_fluid_gravity, fam_fluid_trickle, fam_fluid_jet)
