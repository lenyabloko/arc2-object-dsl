"""MECHANICS prior: rigid bodies in mechanical equilibrium, and common-sense machines.

Laws (the prior, stated before looking for tasks)
------------------------------------------------
Bodies.  A picture is a set of rigid BODIES (connected components: 4/8-connected, single- or multi-colour;
         or finer units: single cells, 1-wide strips parallel to the motion) lying on a background.
L0 conservation     bodies are neither created nor destroyed by motion: the foreground mass of the output
                    equals the input's (gravity, levers) or is smaller only by swept-away debris / unused keys
                    (lock and key).  Used as a precondition.
L1 rigidity         a body moves as a whole: translation (and, only when fitting a key, a D4 rotation);
                    its shape and colours are preserved (optionally a class-dependent recolouring on landing).
L2 impenetrability  two bodies never overlap; STATIC bodies (colours that never change in any training pair,
                    full-length walls / floors, the grid frame) never move.
L3 field            every movable body is driven by a field direction f(body): a constant direction, a
                    table class -> direction (class = colour / topology (holed | open | solid) / thickness /
                    mass threshold), or an ATTRACTOR (the static body it is aligned with: nearest one, the one
                    of its own colour, or only if that is its nearest anchor overall).
L4 support          a body moves along f until the next step would violate L2 (contact) or leave the grid;
                    the equilibrium is reached by settling bodies leading edge first (piling / stacking).
                    Bodies driven in different directions live in different layers (they may pass each other);
                    bodies of one layer pile on each other.  A body may take the colour of what it lands on
                    (absorption).  In time order: pieces released one after the other build a tower (LIFO).
L5 complementarity  LOCK AND KEY: a lock is a body with cavities (enclosed holes, or notches of its bounding
                    box); a key fits a cavity when a rigid motion maps it onto the cavity so that the cavity is
                    filled exactly and nothing overlaps (the key may protrude only outside the lock's hull), or
                    so that lock + key close into a solid rectangle (all such rectangles congruent).  Keys go
                    to the locks they fit: the unique maximum matching (ties: least total displacement = least
                    action), or an exact cover of all holes by several keys.
L6 levers           an ARM attached to (or sighted from) a PIVOT swings 90 degrees about it: fixed sense (cw /
                    ccw), or it falls to the side with more free room; standing bars topple about their base
                    and knock over the bars they reach (dominoes, chain reaction).

Search space (all parameters induced from the training pairs; every program is verified on all pairs)
  mech:lockkey[seg,lock,fit,group,rest(,side)(,rc)]
      seg   c4|c8|m4|m8          body segmentation
      lock  holed (bodies with enclosed empty holes; cavities = holes) | largest (cavities = its bbox notches)
            | static (bodies of static colours) | pairs (two bodies of one colour: the smaller one / the one on an
              induced side is the key)
      fit   fill (one key per cavity) | tile (exact cover of all holes, several keys per hole) | rect / rect=
            (lock + key = solid rectangle / congruent rectangles)
      group T | R4 | D4          allowed key motions
      rest  keep | erase         unmatched keys; debris colours (in every input, absent from its output) erased
      rc    optional recolour of placed keys to the one new output colour
  mech:lockkey-panels[lock]      two panels: the key panel is inserted in place when it is the exact complement of
                                 the lock panel, else the lock panel is output
  mech:lockkey-crop[seg,cav,fit,group]  the unique body whose cavities can all be filled exactly is the lock;
                                 output = the completed lock's bounding box
  mech:gravity[anchors,seg,unit,field(,recol)]
      anchors none | colour (static colours) | lines (full rows / columns)
      unit    body | cell | vstrip | hstrip
      field   up|down|left|right | table:<key> (key in colour, topo, thick, mass>k; value = direction or stay)
              | attract | attract-colour | attract-near
      recol   none | absorb | table (landing colour as a function of colour / topo / thick)
  mech:gravity[stack-panels,d,order]    panel contents dropped one after the other into one frame
  mech:lever[pivot p,arm a,attached|aligned,cw|ccw|room(,new c)(,old c)]
  mech:lever[topple,floor,trigger t,d]  dominoes
Dropped after measurement (solved < 3 tasks): SLOT MACHINE (a reel = the grid inside a border line is rolled
cyclically until its origin aligns with the single marker on the border; 6d1d5c90, 79cce52d only).
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import product
from gdsl import H, W, bg_of, objects, bbox, static_colours, split_panels

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def same_shape(train):
    return all((H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)


def comps4(cells):
    """4-connected components of a set of cells."""
    cells = set(cells); out = []
    while cells:
        s = cells.pop(); st = [s]; comp = [s]
        while st:
            y, x = st.pop()
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if q in cells:
                    cells.remove(q); st.append(q); comp.append(q)
        out.append(sorted(comp))
    return out


def segment(g, bg, seg):
    return objects(g, bg, diag=seg[1] == '8', by_colour=seg[0] == 'c')


# ------------------------------------------------------------------ D4 variants of a key
def _tf(k, y, x):
    return ((y, x), (y, -x), (-y, x), (-y, -x), (x, y), (x, -y), (-x, y), (-x, -y))[k]


GROUPS = {'T': (0,), 'R4': (0, 3, 6, 5), 'D4': tuple(range(8))}   # R4: id, r180, r90, r270 in _tf indices


def variants(cells, g, group):
    """cells -> list of distinct normalised coloured shapes [(dy,dx,c), ...] under the group."""
    out = []; seen = set()
    for k in GROUPS[group]:
        t = [(*_tf(k, y, x), g[y][x]) for y, x in cells]
        my = min(a for a, _, _ in t); mx = min(b for _, b, _ in t)
        v = tuple(sorted((a - my, b - mx, c) for a, b, c in t))
        if v not in seen: seen.add(v); out.append((k, v))
    return out


# ------------------------------------------------------------------ cavities
def enclosed_holes(L, h, w):
    """Components of non-lock cells inside bbox(L) that cannot reach the bbox margin (4-leak)."""
    r0, c0, r1, c1 = bbox(L); s = set(L)
    R0, C0, R1, C1 = r0 - 1, c0 - 1, r1 + 1, c1 + 1
    st = [(y, x) for y in range(R0, R1 + 1) for x in (C0, C1)] + [(y, x) for x in range(C0, C1 + 1) for y in (R0, R1)]
    seen = set(st)
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            q = (y + dy, x + dx)
            if R0 <= q[0] <= R1 and C0 <= q[1] <= C1 and q not in seen and q not in s:
                seen.add(q); st.append(q)
    return comps4([(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s and (y, x) not in seen])


def notches(L):
    r0, c0, r1, c1 = bbox(L); s = set(L)
    return comps4([(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s])


# ------------------------------------------------------------------ fitting
class Scene:
    """Bodies split into locks, keys and debris; cavities of the locks."""
    def __init__(self, g, bg, seg, lock, cav, stat, pairside, debris=frozenset()):
        self.g = g; self.bg = bg; self.h, self.w = H(g), W(g); self.cav_kind = cav
        bodies = segment(g, bg, seg)
        self.debris = [b for b in bodies if {g[y][x] for y, x in b} <= debris]
        bodies = [b for b in bodies if not {g[y][x] for y, x in b} <= debris]
        self.ok = True; self.fixed = []
        locks, keys = [], []
        if lock == 'pairs':
            byc = {}
            for b in bodies:
                cs = {g[y][x] for y, x in b}
                if len(cs) == 1: byc.setdefault(cs.pop(), []).append(b)
            for c, bs in byc.items():
                if len(bs) != 2: continue
                a, b = bs
                if pairside == 'smaller':
                    if len(a) == len(b): self.ok = False; return
                    key, lk = (a, b) if len(a) < len(b) else (b, a)
                else:
                    ya = sum(y for y, _ in a) / len(a); xa = sum(x for _, x in a) / len(a)
                    yb = sum(y for y, _ in b) / len(b); xb = sum(x for _, x in b) / len(b)
                    va = {'left': xa, 'right': -xa, 'top': ya, 'bottom': -ya}[pairside]
                    vb = {'left': xb, 'right': -xb, 'top': yb, 'bottom': -yb}[pairside]
                    if va == vb: self.ok = False; return
                    key, lk = (a, b) if va < vb else (b, a)
                locks.append(lk); keys.append(key)
            if not locks: self.ok = False; return
            ids = {id(x) for x in locks + keys}
            self.fixed = [c for b in bodies if id(b) not in ids for c in b]
        elif lock == 'holed':
            for b in bodies:
                hs = [hc for hc in enclosed_holes(b, self.h, self.w) if all(g[y][x] == bg for y, x in hc)]
                (locks if hs else keys).append(b)
        elif lock == 'largest':
            m = max((len(b) for b in bodies), default=0)
            big = [b for b in bodies if len(b) == m]
            if len(big) != 1: self.ok = False; return
            locks = big; keys = [b for b in bodies if b is not big[0]]
        elif lock == 'static':
            for b in bodies:
                (locks if all(g[y][x] in stat for y, x in b) else keys).append(b)
        if not locks or not keys or len(keys) > 24: self.ok = False; return
        self.locks, self.keys = locks, keys
        self.occ = set(c for b in locks for c in b) | set(self.fixed)
        self._cav = None

    def cavities(self):
        """[(lock index, cells)] of all-background cavities."""
        if self._cav is None:
            g, bg = self.g, self.bg; out = []
            for i, L in enumerate(self.locks):
                cs = enclosed_holes(L, self.h, self.w) if self.cav_kind == 'hole' else notches(L)
                out += [(i, C) for C in cs if all(g[y][x] == bg for y, x in C)]
            self._cav = out
        return self._cav

    def units(self, fit):
        return [(i, None) for i in range(len(self.locks))] if fit.startswith('rect') else self.cavities()


def fill_options(S, key_id, unit, group, mode):
    """Placements of one key into one unit: 'fill' = the key covers the whole cavity and protrudes only outside
    the lock bbox (exactly the cavity for enclosed holes); 'rect' = lock + key form a solid rectangle."""
    g = S.g; h, w = S.h, S.w; li, C = unit; L = S.locks[li]
    K = S.keys[key_id]; opts = []
    if mode == 'rect':
        r0, c0, r1, c1 = bbox(L); Ls = set(L); n = len(L) + len(K)
        for _, v in variants(K, g, group):
            shape = sorted((a, b) for a, b, _ in v)
            for hh in range(r1 - r0 + 1, n + 1):
                if n % hh: continue
                ww = n // hh
                if ww < c1 - c0 + 1: continue
                for R0 in range(r1 - hh + 1, r0 + 1):
                    for C0 in range(c1 - ww + 1, c0 + 1):
                        if R0 < 0 or C0 < 0 or R0 + hh > h or C0 + ww > w: continue
                        P = [(y, x) for y in range(R0, R0 + hh) for x in range(C0, C0 + ww) if (y, x) not in Ls]
                        if len(P) != len(shape): continue
                        my = min(y for y, _ in P); mx = min(x for _, x in P)
                        if sorted((y - my, x - mx) for y, x in P) != shape: continue
                        if any(p in S.occ for p in P): continue
                        opts.append([(a + my, b + mx, c) for a, b, c in v])
        return opts
    Cs = set(C); lb = bbox(L); c0 = min(C)
    for _, v in variants(K, g, group):
        if len(v) < len(C): continue
        for a, b, _ in v:
            ty, tx = c0[0] - a, c0[1] - b
            P = [(a2 + ty, b2 + tx, c) for a2, b2, c in v]
            cells = {(y, x) for y, x, _ in P}
            if not Cs <= cells: continue
            if any(not (0 <= y < h and 0 <= x < w) or (y, x) in S.occ for y, x in cells): continue
            extra = cells - Cs
            if (S.cav_kind == 'hole' or getattr(S, 'exact', False)) and extra: continue
            if any(lb[0] <= y <= lb[2] and lb[1] <= x <= lb[3] for y, x in extra): continue
            opts.append(P)
    return opts


def _disp(K, P):
    """Manhattan displacement of the centroid (least-action tie-break)."""
    ky = sum(y for y, _ in K) / len(K); kx = sum(x for _, x in K) / len(K)
    py = sum(y for y, _, _ in P) / len(P); px = sum(x for _, x, _ in P) / len(P)
    return abs(ky - py) + abs(kx - px)


def solve_match(S, group, fit):
    """One key per unit: maximum assignment of keys to units (cavities or locks); ties broken by least total
    displacement.  Returns (used key ids, placements) or None when empty / still ambiguous."""
    mode = 'rect' if fit.startswith('rect') else 'fill'
    congruent = fit == 'rect='
    opts = []
    for u in S.units(fit):
        o = []
        for k in range(len(S.keys)):
            for P in fill_options(S, k, u, group, mode):
                dims = None
                if congruent:
                    b = bbox([(y, x) for y, x, _ in P] + S.locks[u[0]]); dims = (b[2] - b[0], b[3] - b[1])
                o.append((k, P, _disp(S.keys[k], P), dims))
        if o: opts.append(o)
    if not opts or len(opts) > 16 or sum(len(o) for o in opts) > 200: return None
    best = {}; nodes = [0]
    def rec(i, used, occ, chosen, score, cost, dims):
        nodes[0] += 1
        if nodes[0] > 4000: raise OverflowError
        if i == len(opts):
            best.setdefault(score, []).append((cost, list(chosen))); return
        top = max(best) if best else -1
        if score + (len(opts) - i) < top: return
        for k, P, c, d in opts[i]:
            if k in used or (dims is not None and d != dims): continue
            cells = {(y, x) for y, x, _ in P}
            if cells & occ: continue
            chosen.append((k, P)); rec(i + 1, used | {k}, occ | cells, chosen, score + 1, cost + c, d); chosen.pop()
        rec(i + 1, used, occ, chosen, score, cost, dims)
    try:
        rec(0, frozenset(), set(), [], 0, 0.0, None)
    except OverflowError:
        return None
    if not best or max(best) <= 0: return None
    sols = best[max(best)]
    mc = min(c for c, _ in sols)
    sols = [ch for c, ch in sols if c <= mc + 1e-9]
    outs = {tuple(sorted(t for _, P in ch for t in P)) for ch in sols}
    if len(outs) != 1: return None
    return [k for k, _ in sols[0]], [P for _, P in sols[0]]


def solve_tile(S, group, cap=300, budget=8000):
    """All cavities are covered EXACTLY by keys lying inside them (several keys per cavity allowed): a global
    exact cover; identical keys are interchangeable.  The painted result must be unique."""
    cavs = S.cavities()
    if not cavs: return None
    cav_of = {}
    for j, (_, C) in enumerate(cavs):
        for c in C: cav_of[c] = j
    U = set(cav_of)
    types = {}
    for k, K in enumerate(S.keys):
        r0, c0, _, _ = bbox(K)
        sig = tuple(sorted((y - r0, x - c0, S.g[y][x]) for y, x in K))
        types.setdefault(sig, []).append(k)
    tlist = list(types.items())
    cand = []                                  # (type index, frozenset cells, P)
    by_cell = {c: [] for c in U}
    for ti, (sig, ks) in enumerate(tlist):
        seen = set()
        for _, v in variants(S.keys[ks[0]], S.g, group):
            a, b, _ = v[0]
            for u in U:
                ty, tx = u[0] - a, u[1] - b
                P = tuple((a2 + ty, b2 + tx, c) for a2, b2, c in v)
                cells = frozenset((y, x) for y, x, _ in P)
                if cells in seen or not cells <= U or len({cav_of[c] for c in cells}) != 1: continue
                seen.add(cells); ci = len(cand); cand.append((ti, cells, P))
                for c in cells: by_cell[c].append(ci)
    left = {ti: len(ks) for ti, (_, ks) in enumerate(tlist)}
    sigs = set(); first = [None]; nodes = [0]; nsol = [0]
    class Stop(Exception): pass
    def rec(rem, chosen):
        nodes[0] += 1
        if nodes[0] > budget: raise Stop
        if not rem:
            s = tuple(sorted(t for ci in chosen for t in cand[ci][2]))
            sigs.add(s); nsol[0] += 1
            if first[0] is None: first[0] = list(chosen)
            if len(sigs) > 1 or nsol[0] >= cap: raise Stop
            return
        best = None
        for c in rem:
            opts = [ci for ci in by_cell[c] if left[cand[ci][0]] > 0 and cand[ci][1] <= rem]
            if best is None or len(opts) < len(best[1]): best = (c, opts)
            if not opts: return
        for ci in best[1]:
            ti, cells, _ = cand[ci]
            left[ti] -= 1; chosen.append(ci)
            rec(rem - cells, chosen)
            chosen.pop(); left[ti] += 1
    try:
        rec(frozenset(U), [])
    except Stop:
        if len(sigs) != 1 or nsol[0] < cap: return None
    if len(sigs) != 1: return None
    used = []; placed = []
    pools = {ti: list(ks) for ti, (_, ks) in enumerate(tlist)}
    for ci in first[0]:
        ti, _, P = cand[ci]
        used.append(pools[ti].pop()); placed.append(list(P))
    return used, placed


def solve(S, group, fit):
    return solve_tile(S, group) if fit == 'tile' else solve_match(S, group, fit)


def lk_scene(g, seg, lock, cav, stat, side, debris=frozenset()):
    S = Scene(g, bg_of(g), seg, lock, cav, stat, side, debris)
    return S if S.ok else None


def lk_render(S, sol, rest, rc, debris):
    g, bg = S.g, S.bg
    used, placed = sol
    out = [row[:] for row in g]
    for i, K in enumerate(S.keys):
        if i in used or rest == 'erase':
            for y, x in K: out[y][x] = bg
    for K in S.debris:
        for y, x in K: out[y][x] = bg
    for P in placed:
        for y, x, c in P:
            out[y][x] = rc if rc is not None else c
    return out


def lockkey(g, seg, lock, cav, fit, group, rest, rc, stat, debris, side):
    S = lk_scene(g, seg, lock, cav, stat, side, debris if rc is None else frozenset())
    if S is None: return None
    sol = solve(S, group, fit)
    return lk_render(S, sol, rest, rc, debris) if sol else None


LOCK_CAV = (('holed', 'hole'), ('largest', 'notch'), ('static', 'notch'), ('pairs', 'notch'))
FITS = (('fill', 'T'), ('rect=', 'T'), ('rect', 'T'), ('tile', 'T'), ('fill', 'R4'), ('rect=', 'R4'), ('rect', 'R4'),
        ('fill', 'D4'), ('rect=', 'D4'), ('rect', 'D4'))


def n_fg(g):
    bg = bg_of(g)
    return sum(v != bg for r in g for v in r)


def fam_mech_lockkey(train):
    if not same_shape(train):
        yield from fam_mech_lockkey_panels(train)
        yield from fam_mech_lockkey_crop(train)
        return
    i0, o0 = train[0]['input'], train[0]['output']
    if i0 == o0: return
    # conservation: keys only move (or vanish as debris / leftovers), so the mass cannot grow
    if any(n_fg(p['output']) > n_fg(p['input']) or bg_of(p['output']) != bg_of(p['input']) for p in train): return
    stat = static_colours(train)
    # debris: colours present in every input and absent from the paired output (dust that is swept away)
    debris = set.intersection(*[{v for r in p['input'] for v in r} - {v for r in p['output'] for v in r} for p in train])
    newc = set.intersection(*[{v for r in p['output'] for v in r} - {v for r in p['input'] for v in r} for p in train])
    rcs = [None] + ([next(iter(newc))] if len(newc) == 1 else [])
    n = 0
    for seg, (lock, cav) in product(('c4', 'c8', 'm4', 'm8'), LOCK_CAV):
        if lock == 'static' and not stat: continue
        for side in (('smaller', 'left', 'right', 'top', 'bottom') if lock == 'pairs' else (None,)):
            for rc in rcs:
              S0 = lk_scene(i0, seg, lock, cav, stat, side, debris if rc is None else frozenset())
              if S0 is None: continue
              for fit, group in FITS:
                if fit == 'tile' and cav != 'hole': continue
                sol0 = solve(S0, group, fit)
                if not sol0: continue
                for rest in ('keep', 'erase'):
                    if lk_render(S0, sol0, rest, rc, debris) != o0: continue
                    args = (seg, lock, cav, fit, group, rest, rc, stat, debris, side)
                    ok = True
                    for p in train[1:]:
                        try:
                            r = lockkey(p['input'], *args)
                        except Exception:
                            r = None
                        if r != p['output']: ok = False; break
                    if not ok: continue
                    name = f"mech:lockkey[{seg},{lock},{fit},{group},{rest}{',' + side if side else ''}{',rc' if rc is not None else ''}]"
                    yield (name, 4, lambda g, a=args: lockkey(g, *a))
                    n += 1
                    if n >= 3: return


def lockkey_panels(g, li):
    """Two panels: the key panel is inserted into the lock panel when it is the exact complement of the lock
    inside the panel frame (in place); otherwise the lock panel is returned unchanged."""
    sp = split_panels(g)
    if not sp: return None
    ps, sc = sp
    if len(ps) != 2: return None
    L, K = ps[li], ps[1 - li]
    bg = bg_of(g)
    if bg == sc: return None
    lf = [[v != bg for v in r] for r in L]; kf = [[v != bg for v in r] for r in K]
    if not any(any(r) for r in lf) or not any(any(r) for r in kf): return None
    fits = all(a != b for ra, rb in zip(lf, kf) for a, b in zip(ra, rb))
    return [[(K[y][x] if kf[y][x] else L[y][x]) if fits else L[y][x] for x in range(W(L))] for y in range(H(L))]


def lockkey_crop(g, seg, cav, fit, group, rc, debris):
    """Scope 'crop': among the bodies that have empty cavities, the unique one whose cavities can ALL be filled by
    the other bodies (keys) is the lock; the keys are inserted and the output is the lock's bounding box."""
    bg = bg_of(g); h, w = H(g), W(g)
    bodies = segment(g, bg, seg)
    bodies = [b for b in bodies if not {g[y][x] for y, x in b} <= debris]
    if len(bodies) < 2 or len(bodies) > 16: return None
    hits = []
    for L in bodies:
        cs = enclosed_holes(L, h, w) if cav == 'hole' else notches(L)
        cs = [C for C in cs if all(g[y][x] == bg for y, x in C)]
        if not cs: continue
        S = Scene.__new__(Scene)
        S.g, S.bg, S.h, S.w, S.cav_kind = g, bg, h, w, cav
        S.locks = [L]; S.keys = [b for b in bodies if b is not L]; S.fixed = []; S.debris = []
        S.occ = set(L); S._cav = [(0, C) for C in cs]; S.ok = True; S.exact = True
        sol = solve(S, group, fit)
        if not sol: continue
        filled = {c for P in sol[1] for y, x, _ in P for c in [(y, x)]}
        if not all(set(C) <= filled for _, C in S._cav): continue
        hits.append((S, sol))
        if len(hits) > 1: return None
    if len(hits) != 1: return None
    S, sol = hits[0]
    out = lk_render(S, sol, 'keep', rc, debris)
    return crop_cells(out, S.locks[0])


def crop_cells(g, cells):
    r0, c0, r1, c1 = bbox(cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def fam_mech_lockkey_crop(train):
    """(scope of the lock-and-key law: the output is the completed lock)"""
    i0, o0 = train[0]['input'], train[0]['output']
    if H(o0) > H(i0) or W(o0) > W(i0): return
    # debris: colours present in every input and absent from the paired output (dust that is swept away)
    debris = set.intersection(*[{v for r in p['input'] for v in r} - {v for r in p['output'] for v in r} for p in train])
    for seg, cav, (fit, group) in product(('c4', 'c8', 'm4', 'm8'), ('hole', 'notch'), (('fill', 'T'), ('fill', 'D4'), ('tile', 'T'))):
        if fit == 'tile' and cav != 'hole': continue
        try:
            r0 = lockkey_crop(i0, seg, cav, fit, group, None, debris)
        except Exception:
            r0 = None
        if r0 != o0: continue
        ok = True
        for p in train[1:]:
            try:
                r = lockkey_crop(p['input'], seg, cav, fit, group, None, debris)
            except Exception:
                r = None
            if r != p['output']: ok = False; break
        if ok:
            yield (f'mech:lockkey-crop[{seg},{cav},{fit},{group}]', 4,
                   lambda g, a=(seg, cav, fit, group, None, debris): lockkey_crop(g, *a))
            return


def fam_mech_lockkey_panels(train):
    """(scope of the lock-and-key law: panels)"""
    for li in (0, 1):
        if all(lockkey_panels(p['input'], li) == p['output'] for p in train):
            yield (f'mech:lockkey-panels[lock={li}]', 4, lambda g, li=li: lockkey_panels(g, li))
            return


# ================================================================== L3/L4: fields, support and piling
DIRS = {'up': (-1, 0), 'down': (1, 0), 'left': (0, -1), 'right': (0, 1)}


def full_lines(g, bg):
    """Cells of full-length single-colour rows / columns (walls, floors, border lines)."""
    h, w = H(g), W(g); cells = set()
    for y in range(h):
        if g[y][0] != bg and all(v == g[y][0] for v in g[y]): cells |= {(y, x) for x in range(w)}
    for x in range(w):
        if g[0][x] != bg and all(g[y][x] == g[0][x] for y in range(h)): cells |= {(y, x) for y in range(h)}
    return cells


def anchor_cells(g, bg, mode, stat):
    if mode == 'colour':
        return {(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg and g[y][x] in stat}
    if mode == 'lines':
        return full_lines(g, bg)
    return set()


def movers_of(g, bg, anchors, seg, unit):
    """Movable units: bodies of non-anchor cells, split into single cells or strips when asked."""
    sub = [[v if (y, x) not in anchors else bg for x, v in enumerate(r)] for y, r in enumerate(g)]
    bodies = segment(sub, bg, seg)
    if unit == 'body': return bodies
    if unit == 'cell': return [[c] for b in bodies for c in b]
    out = []                                   # strips: split each body into columns ('v') or rows ('h')
    for b in bodies:
        groups = {}
        for y, x in b: groups.setdefault(x if unit == 'vstrip' else y, []).append((y, x))
        for cells in groups.values():          # a strip may itself be split by gaps
            out += comps4(cells) if len(cells) > 1 else [cells]
    return out


def body_key(cells, g, bg, key):
    if key == 'colour':
        cs = sorted({g[y][x] for y, x in cells})
        return cs[0] if len(cs) == 1 else tuple(cs)
    if key == 'topo':
        if enclosed_holes(cells, H(g), W(g)): return 'holed'
        r0, c0, r1, c1 = bbox(cells)
        return 'open' if len(cells) < (r1 - r0 + 1) * (c1 - c0 + 1) else 'solid'
    if key == 'thick':
        s = set(cells)
        return any((y + 1, x) in s and (y, x + 1) in s and (y + 1, x + 1) in s for y, x in cells)
    if key == 'size':
        return len(cells)
    if key.startswith('mass>'):
        return len(cells) > int(key[5:])
    return None


def attract_dir(cells, g, anchors_bodies, same_colour, near=False):
    """Direction toward the nearest anchor body whose row / column span overlaps the mover (None: none / tie).
    near: the attractor is the nearest anchor overall (Chebyshev gap between boxes); the mover moves only when
    that attractor is aligned with it (a unique nearest)."""
    r0, c0, r1, c1 = bbox(cells)
    col = {g[y][x] for y, x in cells}
    if near:
        gaps = []
        for A, ac in anchors_bodies:
            a0, b0, a1, b1 = bbox(A)
            dy = max(0, a0 - r1 - 1, r0 - a1 - 1); dx = max(0, b0 - c1 - 1, c0 - b1 - 1)
            gaps.append((max(dy, dx), A, ac))
        if not gaps: return None
        m = min(x[0] for x in gaps); near_ab = [(A, ac) for d, A, ac in gaps if d == m]
        if len(near_ab) != 1: return None
        d = attract_dir(cells, g, near_ab, same_colour)
        return None if d == 'tie' else d
    best = []
    for A, ac in anchors_bodies:
        if same_colour and not (len(col) == 1 and ac == next(iter(col))): continue
        a0, b0, a1, b1 = bbox(A)
        if b0 <= c1 and c0 <= b1:
            if a0 > r1: best.append((a0 - r1, 'down'))
            elif a1 < r0: best.append((r0 - a1, 'up'))
        if a0 <= r1 and r0 <= a1:
            if b0 > c1: best.append((b0 - c1, 'right'))
            elif b1 < c0: best.append((c0 - b1, 'left'))
    if not best: return None
    m = min(d for d, _ in best); ds = {d for dd, d in best if dd == m}
    return ds.pop() if len(ds) == 1 else 'tie'


def settle_positions(g, bg, movers, dirs):
    """L4: lift every driven mover, then settle each field layer (one direction) leading edge first; a mover stops
    when its next step would leave the grid or enter an occupied cell (anchors, resting bodies, bodies already
    settled in its layer).  Layers are independent.  Returns (landing cells per mover, settling order)."""
    h, w = H(g), W(g)
    if 'tie' in dirs: return None
    lifted = {c for m, d in zip(movers, dirs) if d is not None for c in m}
    base = {(y, x) for y in range(h) for x in range(w) if g[y][x] != bg and (y, x) not in lifted}
    lands = [list(m) for m in movers]; order = []
    layers = {}
    for i, d in enumerate(dirs):
        if d is not None: layers.setdefault(d, []).append(i)
    for d, ids in layers.items():
        dy, dx = DIRS[d]; occ = set(base)
        ids.sort(key=lambda i: -max(y * dy + x * dx for y, x in movers[i]))
        for i in ids:
            cells = movers[i]; k = 0
            while True:
                nxt = [(y + (k + 1) * dy, x + (k + 1) * dx) for y, x in cells]
                if any(not (0 <= y < h and 0 <= x < w) or (y, x) in occ for y, x in nxt): break
                k += 1
            lands[i] = [(y + k * dy, x + k * dx) for y, x in cells]
            occ |= set(lands[i]); order.append(i)
    return lands, order


def settle(g, bg, movers, dirs, recol=None, absorb=False):
    """Paint the equilibrium: moved bodies keep their colours, take a class colour (recol), or take the colour of
    what they come to rest against (absorb).  Overlaps between layers are inconsistent (None)."""
    r = settle_positions(g, bg, movers, dirs)
    if r is None: return None
    lands, order = r
    h, w = H(g), W(g)
    out = [row[:] for row in g]
    for m, d in zip(movers, dirs):
        if d is not None:
            for y, x in m: out[y][x] = bg
    final = {}; layer = {}                     # layer: colours of bodies already settled in the same field layer
    for n, i in enumerate(order):
        if n and dirs[order[n - 1]] != dirs[i]: layer = {}
        new = lands[i]
        if absorb:
            dy, dx = DIRS[dirs[i]]; s = set(new)
            hit = [(y + dy, x + dx) for y, x in new if (y + dy, x + dx) not in s]
            hc = Counter(layer.get(q, out[q[0]][q[1]]) for q in hit
                         if 0 <= q[0] < h and 0 <= q[1] < w and (q in layer or out[q[0]][q[1]] != bg))
            if not hc: return None
            c_abs = hc.most_common(1)[0][0]
        for (y0, x0), q in zip(movers[i], new):
            c = c_abs if absorb else (recol[i] if recol and recol[i] is not None else g[y0][x0])
            if q in final and final[q] != c: return None
            final[q] = c; layer[q] = c
    for (y, x), c in final.items():
        if out[y][x] != bg: return None
        out[y][x] = c
    return out


def consistent_dirs(cells, g, o, bg, strict):
    """Directions d (and 'stay') such that the mover's footprint shifted k>=0 steps along d lies on cells of the
    output that carry its colours (strict) or any non-background colour (recolouring allowed)."""
    h, w = H(g), W(g); res = set()
    if all((o[y][x] == g[y][x]) if strict else (o[y][x] != bg) for y, x in cells): res.add(None)
    for d, (dy, dx) in DIRS.items():
        for k in range(1, max(h, w)):
            ok = True; inside = True
            for y, x in cells:
                yy, xx = y + k * dy, x + k * dx
                if not (0 <= yy < h and 0 <= xx < w): inside = False; break
                if (o[yy][xx] != g[y][x]) if strict else (o[yy][xx] == bg): ok = False; break
            if not inside: break
            if ok: res.add(d); break
    return res


FIELD_KEYS = ('colour', 'topo', 'thick')


def grav_program(g, P):
    """Apply one gravity program P (dict) to grid g."""
    bg = bg_of(g)
    anchors = anchor_cells(g, bg, P['anchor'], P['stat'])
    unit = P['unit']
    movers = movers_of(g, bg, anchors, P['seg'], unit)
    if not movers or len(movers) > 120: return None
    dirs = grav_dirs(g, bg, P, movers)
    if dirs is None: return None
    recol = None
    if P['recol'] == 'table':
        recol = []
        for m in movers:
            v = body_key(m, g, bg, P['rkey'])
            if v not in P['rtable']: return None
            recol.append(P['rtable'][v])
    return settle(g, bg, movers, dirs, recol, P['recol'] == 'absorb')


def stack_panels(g, d, order):
    """Sequential drop (tower building, L4 in time order): the contents of the panels enter one panel frame one
    after the other from the side opposite to d, keep their lateral position and slide along d until they rest
    on the frame or on earlier pieces."""
    sp = split_panels(g)
    if not sp: return None
    ps, sc = sp
    if len(ps) < 2: return None
    bg = bg_of(g)
    if bg == sc: return None
    h, w = H(ps[0]), W(ps[0]); dy, dx = DIRS[d]
    canvas = [[bg] * w for _ in range(h)]
    seq = ps if order == 'fwd' else ps[::-1]
    for P in seq:
        cells = [(y, x, P[y][x]) for y in range(h) for x in range(w) if P[y][x] != bg]
        if not cells: continue
        # start fully outside the frame on the side opposite to d
        k0 = max(h, w) + 1
        cur = [(y - dy * k0, x - dx * k0, c) for y, x, c in cells]
        def free(cs):
            return all(not (0 <= y < h and 0 <= x < w) or canvas[y][x] == bg for y, x, _ in cs) and \
                   all((y < h if dy > 0 else y >= 0 if dy < 0 else True) and (x < w if dx > 0 else x >= 0 if dx < 0 else True)
                       for y, x, _ in cs)
        while True:
            nxt = [(y + dy, x + dx, c) for y, x, c in cur]
            if not free(nxt): break
            cur = nxt
        if any(not (0 <= y < h and 0 <= x < w) for y, x, _ in cur): return None
        for y, x, c in cur: canvas[y][x] = c
    return canvas


def fam_mech_stack_panels(train):
    """(scope of the support law: pieces from panels dropped in sequence into one frame)"""
    for d, order in product(('down', 'up', 'left', 'right'), ('fwd', 'rev')):
        ok = True
        for p in train:
            try:
                r = stack_panels(p['input'], d, order)
            except Exception:
                r = None
            if r != p['output']: ok = False; break
        if ok:
            yield (f'mech:gravity[stack-panels,{d},{order}]', 4, lambda g, a=(d, order): stack_panels(g, *a))
            return


FIELD_COST = {'const': 0, 'attract': 1, 'attract-colour': 1, 'attract-near': 2, 'table': 2}


def fam_mech_gravity(train):
    if not same_shape(train):
        yield from fam_mech_stack_panels(train)
        return
    if all(p['input'] == p['output'] for p in train): return
    # conservation of mass: bodies only move (recolouring allowed)
    if any(n_fg(p['output']) != n_fg(p['input']) or bg_of(p['output']) != bg_of(p['input']) for p in train): return
    import time
    t0 = time.time()
    stat = static_colours(train)
    anchors_modes = ['none'] + (['colour'] if stat else [])
    if all(full_lines(p['input'], bg_of(p['input'])) for p in train): anchors_modes.append('lines')
    found = []; seen = set()
    for amode, seg, unit in product(anchors_modes, ('c4', 'c8', 'm4', 'm8'), ('body', 'cell', 'vstrip', 'hstrip')):
        if unit in ('cell', 'vstrip', 'hstrip') and seg[1] == '8': continue
        if len(found) >= 12: break  # deterministic: wall-clock budget removed (Kaggle parity)
        info = []
        for p in train:
            g, o = p['input'], p['output']; bg = bg_of(g)
            A = anchor_cells(g, bg, amode, stat)
            if amode != 'none' and not A: info = None; break
            ms = movers_of(g, bg, A, seg, unit)
            if not ms or len(ms) > 120: info = None; break
            info.append((g, o, bg, ms))
        if info is None: continue
        sig = tuple(tuple(sorted(tuple(sorted(m)) for m in ms)) for _, _, _, ms in info) + (amode,)
        if sig in seen: continue
        seen.add(sig)
        for recol in ('none', 'absorb', 'table'):
            strict = recol == 'none'
            cons = [[consistent_dirs(m, g, o, bg, strict) for m in ms] for g, o, bg, ms in info]
            if any(not c for cs in cons for c in cs): continue
            fields = []
            for d in DIRS:
                if all(d in c or None in c for cs in cons for c in cs): fields.append((d, None, 'const'))
            if amode != 'none':
                fields += [('attract', None, 'attract'), ('attract-colour', None, 'attract-colour'),
                           ('attract-near', None, 'attract-near')]
            sizes = sorted({len(m) for _, _, _, ms in info for m in ms})
            keys = list(FIELD_KEYS) + [f'mass>{k}' for k in sizes[:-1]][:6]
            for key in keys:
                tab = {}; ok = True
                for (g, o, bg, ms), cs in zip(info, cons):
                    for m, c in zip(ms, cs):
                        v = body_key(m, g, bg, key)
                        tab[v] = tab.get(v, c) & c
                        if not tab[v]: ok = False; break
                    if not ok: break
                if not ok or len(tab) < 2 or len(tab) > 4: continue
                opts = [sorted(tab[v], key=lambda d: (d is not None, str(d))) for v in tab]
                for combo in product(*opts):
                    if len(set(combo)) < 2: continue
                    fields.append(('table:' + key, dict(zip(tab, combo)), 'table'))
            for fname, table, fkind in fields[:40]:
                P = {'anchor': amode, 'stat': stat, 'seg': seg, 'unit': unit, 'field': fname, 'table': table,
                     'recol': recol}
                if recol == 'table':
                    P = induce_recolour(P, train)
                    if P is None: continue
                ok = True
                for p in train:
                    try:
                        r = grav_program(p['input'], P)
                    except Exception:
                        r = None
                    if r != p['output']: ok = False; break
                if not ok: continue
                tname = '' if table is None else ':' + ','.join(f'{k}>{v}' for k, v in sorted(table.items(), key=str))
                rname = '' if recol == 'none' else (f',recol={P.get("rkey")}' if recol == 'table' else ',absorb')
                score = (FIELD_COST[fkind] + (1 if fname.startswith('table:mass') else 0)
                         + {'none': 0, 'absorb': 1, 'table': 2}[recol] + (unit.endswith('strip')) + (seg[0] == 'm')
                         + (amode == 'lines'))
                found.append((score, len(found), f'mech:gravity[{amode},{seg},{unit},{fname}{tname}{rname}]', dict(P)))
    found.sort(key=lambda x: (x[0], x[1]))
    for score, _, name, P in found[:3]:
        yield (name, 4, lambda g, P=P: grav_program(g, P))


def induce_recolour(P, train):
    """Find a key such that the landing colour of every mover is a function of it (moved units only)."""
    for rkey in ('colour', 'topo', 'thick'):
        Q = dict(P); Q['recol'] = 'none'
        rt = {}; ok = True; changed = False
        for p in train:
            g, o = p['input'], p['output']; bg = bg_of(g)
            anchors = anchor_cells(g, bg, Q['anchor'], Q['stat'])
            movers = movers_of(g, bg, anchors, Q['seg'], Q['unit'])
            # simulate without recolour to know where each mover lands
            r = grav_program_trace(g, Q, movers)
            if r is None: ok = False; break
            for m, land in zip(movers, r):
                cs = {o[y][x] for y, x in land}
                if len(cs) != 1: ok = False; break
                v = body_key(m, g, bg, rkey); c = cs.pop()
                if rt.setdefault(v, c) != c: ok = False; break
                if any(g[y][x] != c for y, x in m): changed = True
            if not ok: break
        if ok and rt and changed:
            Q['recol'] = 'table'; Q['rkey'] = rkey; Q['rtable'] = rt
            return Q
    return None


def grav_dirs(g, bg, P, movers):
    f = P['field']
    if f in DIRS:
        return [f] * len(movers)
    if f.startswith('table:'):
        dirs = []
        for m in movers:
            v = body_key(m, g, bg, f[6:])
            if v not in P['table']: return None
            dirs.append(P['table'][v])
        return dirs
    anchors = anchor_cells(g, bg, P['anchor'], P['stat'])      # attract / attract-colour / attract-near
    ab = [(A, g[A[0][0]][A[0][1]]) for A in segment([[v if (y, x) in anchors else bg for x, v in enumerate(r)]
                                                      for y, r in enumerate(g)], bg, 'c4')]
    if not ab: return None
    return [attract_dir(m, g, ab, f == 'attract-colour', f == 'attract-near') for m in movers]


def grav_program_trace(g, P, movers):
    """Landing cells of every mover under program P (no recolouring)."""
    bg = bg_of(g)
    dirs = grav_dirs(g, bg, P, movers)
    if dirs is None: return None
    r = settle_positions(g, bg, movers, dirs)
    return r[0] if r else None


# ================================================================== L6: levers (rotation about a pivot)
ROT = {'cw': lambda dy, dx: (dx, -dy), 'ccw': lambda dy, dx: (-dx, dy)}


def lever_arms(g, bg, p, a, mode):
    """[(pivot cell, [arm cells])].  attached: straight runs of arm colour leaving the pivot whose far end is free
    (next cell background or outside); aligned: arm-colour cells matched one-to-one to pivots on their row /
    column with a clear line of sight, minimum total distance (the matching must be unique)."""
    h, w = H(g), W(g)
    piv = [(y, x) for y in range(h) for x in range(w) if g[y][x] == p]
    out = []
    if mode == 'attached':
        for py, px in piv:
            for dy, dx in N4:
                run = []; y, x = py + dy, px + dx
                while 0 <= y < h and 0 <= x < w and g[y][x] == a:
                    run.append((y, x)); y += dy; x += dx
                if not run: continue
                if 0 <= y < h and 0 <= x < w and g[y][x] != bg: continue
                out.append(((py, px), run))
        used = [c for _, r in out for c in r]
        if len(used) != len(set(used)): return None
        return out
    arms = [(y, x) for y in range(h) for x in range(w) if g[y][x] == a]
    if not arms or len(arms) > len(piv) or len(arms) > 12: return None
    cand = []
    for q in arms:
        cs = []
        for pv in piv:
            if (pv[0] == q[0] or pv[1] == q[1]) and all(g[yy][xx] == bg for yy, xx in _between(pv, q)):
                cs.append((abs(pv[0] - q[0]) + abs(pv[1] - q[1]), pv))
        if not cs: return None
        cand.append(sorted(cs))
    best = [None, []]
    def rec(i, used, cost, ch):
        if best[0] is not None and cost > best[0]: return
        if i == len(arms):
            if best[0] is None or cost < best[0]: best[0] = cost; best[1] = [list(ch)]
            elif cost == best[0]: best[1].append(list(ch))
            return
        for d, pv in cand[i]:
            if pv in used: continue
            ch.append(pv); rec(i + 1, used | {pv}, cost + d, ch); ch.pop()
    rec(0, frozenset(), 0, [])
    if len(best[1]) != 1: return None
    return [(pv, [q]) for pv, q in zip(best[1][0], arms)]


def _between(a, b):
    (y0, x0), (y1, x1) = a, b
    if y0 == y1: return [(y0, x) for x in range(min(x0, x1) + 1, max(x0, x1))]
    return [(y, x0) for y in range(min(y0, y1) + 1, max(y0, y1))]


def _room(g, bg, py, px, dy, dx):
    h, w = H(g), W(g); k = 0; y, x = py + dy, px + dx
    while 0 <= y < h and 0 <= x < w and g[y][x] == bg:
        k += 1; y += dy; x += dx
    return k


def lever(g, p, a, mode, rot, new_c, old_c):
    """L7: every arm swings 90 degrees about its pivot.  rot = cw | ccw (fixed sense, clipped by the frame)
    | room (it falls to the perpendicular side with more free room; that side must hold the whole arm)."""
    bg = bg_of(g); h, w = H(g), W(g)
    arms = lever_arms(g, bg, p, a, mode)
    if not arms: return None
    out = [r[:] for r in g]
    taken = set()
    for (py, px), cells in arms:
        for y, x in cells: out[y][x] = bg if old_c is None else old_c
    for (py, px), cells in arms:
        if rot in ROT:
            f = ROT[rot]
        else:
            s = lambda v: (v > 0) - (v < 0)
            dy0, dx0 = s(cells[0][0] - py), s(cells[0][1] - px)
            r1 = _room(g, bg, py, px, *ROT['cw'](dy0, dx0)); r2 = _room(g, bg, py, px, *ROT['ccw'](dy0, dx0))
            if r1 == r2: return None
            f = ROT['cw'] if r1 > r2 else ROT['ccw']
            if max(r1, r2) < max(abs(y - py) + abs(x - px) for y, x in cells): return None
        new = [(py + f(y - py, x - px)[0], px + f(y - py, x - px)[1]) for y, x in cells]
        for (y, x), (y0, x0) in zip(new, cells):
            if 0 <= y < h and 0 <= x < w:
                if (y, x) in taken: return None
                out[y][x] = g[y0][x0] if new_c is None else new_c
                taken.add((y, x))
    return out


def topple(g, trig, d):
    """Dominoes: vertical bars standing on the floor (bottom row).  Bars of the trigger colour fall toward d,
    rotating 90 degrees about their base and lying on the floor; a falling bar of height h knocks over every
    standing bar whose base lies within distance h (chain reaction)."""
    bg = bg_of(g); h, w = H(g), W(g)
    bars = {}
    for x in range(w):
        if g[h - 1][x] == bg: continue
        c = g[h - 1][x]; y = h - 1
        while y >= 0 and g[y][x] == c: y -= 1
        if y >= 0 and g[y][x] != bg: return None
        if any(g[yy][x] != bg for yy in range(y + 1)): return None
        bars[x] = (c, h - 1 - y)
    if not bars: return None
    for y in range(h):
        for x in range(w):
            if g[y][x] != bg and x not in bars: return None
    s = 1 if d == 'right' else -1
    fallen = set(); todo = [x for x, (c, _) in bars.items() if c == trig]
    if not todo: return None
    while todo:
        x = todo.pop()
        if x in fallen: continue
        fallen.add(x); hh = bars[x][1]
        for k in range(1, hh + 1):
            if x + s * k in bars and x + s * k not in fallen: todo.append(x + s * k)
    out = [r[:] for r in g]
    for x in fallen:
        for y in range(h): out[y][x] = bg
    for x in sorted(fallen, key=lambda x: s * x):
        c, hh = bars[x]
        for k in range(hh):
            xx = x + s * k
            if 0 <= xx < w: out[h - 1][xx] = c
    return out


# frames: which grid side is the floor (the grid is turned so that this side is at the bottom)
FRAMES = {'bottom': (lambda g: g, lambda g: g),
          'top': (lambda g: [r[::-1] for r in g[::-1]], lambda g: [r[::-1] for r in g[::-1]]),
          'left': (lambda g: [list(r) for r in zip(*g)][::-1], lambda g: [list(r) for r in zip(*g[::-1])]),
          'right': (lambda g: [list(r) for r in zip(*g[::-1])], lambda g: [list(r) for r in zip(*g)][::-1])}


def topple_framed(g, fr, trig, d):
    to, back = FRAMES[fr]
    r = topple(to(g), trig, d)
    return back(r) if r is not None else None


def fam_mech_lever(train):
    if not same_shape(train): return
    i0, o0 = train[0]['input'], train[0]['output']
    if i0 == o0: return
    bg0 = bg_of(i0)
    stat = static_colours(train)
    cin = set.intersection(*[{v for r in p['input'] for v in r} for p in train])
    changed = set()
    for p in train:
        for ri, ro in zip(p['input'], p['output']):
            for u, v in zip(ri, ro):
                if u != v: changed.add(u)
    newc = set.intersection(*[{v for r in p['output'] for v in r} - {v for r in p['input'] for v in r} for p in train])
    n = 0
    for fr, trig, d in product(FRAMES, sorted(changed - {bg0}), ('right', 'left')):
        if all(topple_framed(p['input'], fr, trig, d) == p['output'] for p in train):
            yield (f'mech:lever[topple,floor={fr},trigger{trig},{d}]', 4,
                   lambda g, a=(fr, trig, d): topple_framed(g, *a))
            return
    for pc in sorted(c for c in stat & cin if c != bg0):
        for ac in sorted(changed & cin - {bg0, pc}):
            olds = [None] + sorted(c for c in {v for r in o0 for v in r} if c not in (bg0, ac, pc))[:2]
            news = [None] + sorted(newc)[:1]
            for mode, rot, nc, oc in product(('attached', 'aligned'), ('cw', 'ccw', 'room'), news, olds):
                ok = True
                for p in train:
                    try:
                        r = lever(p['input'], pc, ac, mode, rot, nc, oc)
                    except Exception:
                        r = None
                    if r != p['output']: ok = False; break
                if not ok: continue
                rn = rot
                yield (f'mech:lever[pivot{pc},arm{ac},{mode},{rn}{",new" + str(nc) if nc is not None else ""}'
                       f'{",old" + str(oc) if oc is not None else ""}]', 4,
                       lambda g, a=(pc, ac, mode, rot, nc, oc): lever(g, *a))
                n += 1
                if n >= 2: return


FAMILIES = (fam_mech_lockkey, fam_mech_gravity, fam_mech_lever)
