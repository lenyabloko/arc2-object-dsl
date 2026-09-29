"""recolour.by_distance_layers: cell colour = palette(distance of the cell from a source set, inside a mask).

One parametrised primitive, every parameter induced from the training pairs:
  mask/source  : objects<-exterior | enclosed<-exterior | enclosed<-seeds | open<-seeds | seedregion<-seeds | seedregion<-exterior
  metric       : 4-conn (manhattan/geodesic) | 8-conn (chebyshev/geodesic) BFS inside the mask
  palette      : cyc[k]  out = P[(d-1) mod k]      (d>=1; sources keep)
                 clamp[k] out = P[min(d-1,k-1)]
                 succ     out = S(out of BFS parent) (successor map learned from training)
                 P entries are roles fitted per residue: keep | seed (nearest source colour) | other (the other seed colour) | const c
                 tie cells (equidistant from different-coloured sources) get their own fitted role.
  plus a sibling mode: reverse the nested colour layers of each object (palette = reversed input layers).
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter, deque
from gdsl import H, W, bg_of

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _comp_from_border(g, ok):
    """cells with ok(y,x) reachable 4-conn from the grid border through ok cells"""
    h, w = H(g), W(g); seen = set(); dq = deque()
    for y in range(h):
        for x in range(w):
            if (y in (0, h - 1) or x in (0, w - 1)) and ok(y, x):
                seen.add((y, x)); dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in N4:
            p = (y + dy, x + dx)
            if 0 <= p[0] < h and 0 <= p[1] < w and p not in seen and ok(*p):
                seen.add(p); dq.append(p)
    return seen


def _setup(g, kind, pc):
    """return (mask set, sources dict cell->colour or 'EXT', open_colour) or None"""
    h, w = H(g), W(g)
    cnt = Counter(v for r in g for v in r)
    allc = {(y, x) for y in range(h) for x in range(w)}
    if kind in ('objects', 'enclosed_ext', 'enclosed_seed', 'open_seed'):
        bg = pc[1] if isinstance(pc, tuple) else bg_of(g)
        if kind in ('objects', 'objects_ie'):
            mask = {p for p in allc if g[p[0]][p[1]] != bg}
            return mask, ('EXT' if kind == 'objects' else 'EXTIN'), bg
        if kind == 'open_seed':
            src = {p: g[p[0]][p[1]] for p in allc if g[p[0]][p[1]] != bg}
            if not src or len(src) > 12: return None
            return allc, src, bg
        out = _comp_from_border(g, lambda y, x: g[y][x] == bg)
        frame = {p for p in allc - out if any((p[0] + dy, p[1] + dx) in out for dy, dx in N8)}
        enc = allc - out - frame
        if not enc: return None
        if kind == 'enclosed_ext':
            return {p for p in enc if g[p[0]][p[1]] == bg}, 'EXT', bg
        src = {p: g[p[0]][p[1]] for p in enc if g[p[0]][p[1]] != bg}
        if not src: return None
        return enc, src, bg
    # seed regions: open colour & wall colour are the two most frequent colours (order = pc)
    mc = [c for c, _ in cnt.most_common()]
    if len(mc) < 3: return None
    if isinstance(pc, tuple):
        op = pc[1]
        if op not in cnt: return None
        wall = [c for c in mc if c != op][0]
    else:
        op, wall = (mc[0], mc[1]) if pc == 0 else (mc[1], mc[0])
    seeds = {p: g[p[0]][p[1]] for p in allc if g[p[0]][p[1]] not in (op, wall)}
    if not seeds: return None
    reg = set(seeds); dq = deque(seeds)
    while dq:
        y, x = dq.popleft()
        for dy, dx in N4:
            p = (y + dy, x + dx)
            if p in allc and p not in reg and g[p[0]][p[1]] == op:
                reg.add(p); dq.append(p)
    if kind == 'region_seed':
        return reg, seeds, op
    # region_ext: fill holes of the region, sources = its exterior
    outside = _comp_from_border(g, lambda y, x: (y, x) not in reg)
    filled = allc - outside
    return filled, 'EXT', op


def _dist(g, mask, src, conn):
    """multi-source BFS inside mask. returns {cell: (d, colourset)}"""
    h, w = H(g), W(g); nb = N8 if conn == 8 else N4
    D = {}; dq = deque()
    if src in ('EXT', 'EXTIN'):
        for (y, x) in mask:
            if any(not ((y + dy, x + dx) in mask) and (src == 'EXT' or (0 <= y + dy < h and 0 <= x + dx < w)) for dy, dx in nb):
                D[(y, x)] = [1, set()]; dq.append((y, x))
    else:
        for p, c in src.items():
            if p in mask:
                D[p] = [0, {c}]; dq.append(p)
    while dq:
        p = dq.popleft(); d, cs = D[p]
        for dy, dx in nb:
            q = (p[0] + dy, p[1] + dx)
            if q not in mask or (isinstance(src, dict) and q in src): continue
            if q not in D:
                D[q] = [d + 1, set(cs)]; dq.append(q)
            elif D[q][0] == d + 1:
                D[q][1] |= cs
    return D


def _feats(g, kind, pc, conn, vor=None):
    s = _setup(g, kind, pc)
    if s is None: return None
    mask, src, op = s
    if not mask or len(mask) == 0: return None
    D = _dist(g, mask, src, conn)
    if kind == 'region_ext':  # seed cells are anchors, never repainted
        for q, v in D.items():
            if g[q[0]][q[1]] != op and g[q[0]][q[1]] != _wall(g, op): v[0] = 0
    if vor and isinstance(src, dict):
        S = list(src.items())
        for q, v in D.items():
            if v[0] == 0: continue
            ds = [abs(q[0] - p[0]) + abs(q[1] - p[1]) for p, c in S]
            m = min(ds)
            v[1] = {c for (p, c), d in zip(S, ds) if d == m}
    scols = sorted(set(src.values())) if isinstance(src, dict) else []
    rows = []
    for p, (d, cs) in D.items():
        if d == 0: continue
        seed = next(iter(cs)) if len(cs) == 1 else None
        other = None
        if len(scols) == 2 and seed is not None:
            other = scols[1] if seed == scols[0] else scols[0]
        rows.append((p, d, g[p[0]][p[1]], seed, other, len(cs) > 1))
    return rows, D, mask, op


def _role_val(role, inc, seed, other):
    if role == 'keep': return inc
    if role == 'seed': return seed
    if role == 'other': return other
    return role[1]


def _fit_role(samples):
    """samples: list of (inc, seed, other, out). pick first consistent role"""
    if not samples: return None
    for role in ('keep', 'seed', 'other'):
        if all(_role_val(role, a, b, c) == o and o is not None for a, b, c, o in samples):
            return role
    outs = {s[3] for s in samples}
    if len(outs) == 1: return ('c', outs.pop())
    return None


def _wall(g, op):
    cnt = Counter(v for r in g for v in r); cnt.pop(op, None)
    return cnt.most_common(1)[0][0] if cnt else None


def _clear_outside(g, mask, op):
    """objects (8-conn, non-open colour) outside the mask that do not touch it are erased"""
    out = [r[:] for r in g]; h, w = H(g), W(g); seen = set()
    for y in range(h):
        for x in range(w):
            if (y, x) in mask or (y, x) in seen or g[y][x] == op: continue
            comp = [(y, x)]; seen.add((y, x)); st = [(y, x)]; touch = False
            while st:
                a, b = st.pop()
                for dy, dx in N8:
                    q = (a + dy, b + dx)
                    if q in mask: touch = True
                    elif 0 <= q[0] < h and 0 <= q[1] < w and q not in seen and g[q[0]][q[1]] != op:
                        seen.add(q); comp.append(q); st.append(q)
            if not touch:
                for a, b in comp: out[a][b] = op
    return out


BASE_KINDS = (('objects', 0, None), ('enclosed_ext', 0, None), ('enclosed_seed', 0, None), ('enclosed_seed', 0, 'L1'),
              ('open_seed', 0, None), ('open_seed', 0, 'L1'))


def _kinds(train):
    bgs = {bg_of(p['input']) for p in train}
    bgp = ('c', next(iter(bgs))) if len(bgs) == 1 else 0  # training-constant background colour, else per-grid mode
    for kind, pc, vor in BASE_KINDS:
        yield (kind, bgp, vor)
    common = None
    for p in train:
        cs = {v for r in p['input'] for v in r}
        common = cs if common is None else common & cs
    ops = [0, 1] + [('c', c) for c in sorted(common or ())]
    for kind in ('region_seed', 'region_ext'):
        for pc in ops:
            yield (kind, pc, None)


def fam_distance_layers(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    nyield = 0
    seen = set()
    for kind, pc, vor in _kinds(train):
        for conn in (4, 8):
            F = []
            for p in train:
                f = _feats(p['input'], kind, pc, conn, vor)
                if f is None: F = None; break
                F.append(f)
            if F is None: continue
            # cells outside mask must be unchanged (or cleared for region_ext)
            clear_opts = (False, True) if kind == 'region_ext' else (False,)
            for clear in clear_opts:
                good = True
                for p, (rows, D, mask, op) in zip(train, F):
                    g, o = p['input'], p['output']
                    base = _clear_outside(g, mask, op) if clear else g
                    for y in range(H(g)):
                        for x in range(W(g)):
                            if (y, x) not in D or D[(y, x)][0] == 0:
                                if (y, x) in D or (y, x) not in mask:
                                    if base[y][x] != o[y][x]: good = False; break
                        if not good: break
                    if not good: break
                if not good: continue
                samples = []  # (d, tie, inc, seed, other, out)
                for p, (rows, D, mask, op) in zip(train, F):
                    o = p['output']
                    for (q, d, inc, seed, other, tie) in rows:
                        samples.append((d, tie, inc, seed, other, o[q[0]][q[1]]))
                if not samples: continue
                if all(s[2] == s[5] for s in samples): continue  # nothing recoloured
                maxd = max(s[0] for s in samples)
                ties = [s[2:] for s in samples if s[1]]
                tie_role = _fit_role(ties) if ties else None
                if ties and tie_role is None: tie_role = False
                base_s = [s for s in samples if not (s[1] and tie_role)]
                # palette modes
                for mode in ('cyc', 'clamp'):
                    for k in range(1, 5):
                        if mode == 'clamp' and k < 2: continue
                        if k > maxd: break
                        idx = (lambda d, k=k: (d - 1) % k) if mode == 'cyc' else (lambda d, k=k: min(d - 1, k - 1))
                        P = []
                        for j in range(k):
                            r = _fit_role([s[2:] for s in base_s if idx(s[0]) == j])
                            if r is None: P = None; break
                            P.append(r)
                        if P is None: continue
                        if tie_role is False: continue
                        name = f"distlayers[{kind}{pc}{vor or ''},c{conn},{mode}{k}:{P},tie={tie_role},clear={clear}]"
                        yield (name, 3 + min(k, 3), _make_fn(kind, pc, conn, vor, idx, P, tie_role, clear))
                        nyield += 1
                        break  # smallest k per mode
                # successor mode
                S = _fit_succ(train, F, conn) if vor is None else None
                if S is not None:
                    yield (f"distlayers[{kind}{pc},c{conn},succ,clear={clear}]", 5,
                           _make_succ(kind, pc, conn, S, clear))
                    nyield += 1
                if nyield > 40: return


def _make_fn(kind, pc, conn, vor, idx, P, tie_role, clear):
    def fn(g):
        f = _feats(g, kind, pc, conn, vor)
        if f is None: return None
        rows, D, mask, op = f
        out = _clear_outside(g, mask, op) if clear else [r[:] for r in g]
        for (q, d, inc, seed, other, tie) in rows:
            role = tie_role if (tie and tie_role) else P[idx(d)]
            v = _role_val(role, inc, seed, other)
            if v is None: return None
            out[q[0]][q[1]] = v
        return out
    return fn


def _parents(g, D, conn):
    nb = N8 if conn == 8 else N4
    for q, (d, cs) in D.items():
        if d == 0: continue
        par = [(q[0] + dy, q[1] + dx) for dy, dx in nb if (q[0] + dy, q[1] + dx) in D and D[(q[0] + dy, q[1] + dx)][0] == d - 1]
        yield q, d, par


def _fit_succ(train, F, conn):
    """out(cell) = S[out(parent)] with parents at d-1; sources keep their colour."""
    S = {}
    for p, (rows, D, mask, op) in zip(train, F):
        if not any(v[0] == 0 for v in D.values()): return None
        o = p['output']
        for q, d, par in _parents(p['input'], D, conn):
            v = o[q[0]][q[1]]
            for r in par:
                a = o[r[0]][r[1]]
                if S.get(a, v) != v: return None
                S[a] = v
    if not S or all(a == b for a, b in S.items()): return None
    return S


def _make_succ(kind, pc, conn, S, clear):
    def fn(g):
        f = _feats(g, kind, pc, conn)
        if f is None: return None
        rows, D, mask, op = f
        out = _clear_outside(g, mask, op) if clear else [r[:] for r in g]
        order = sorted((d, q) for q, (d, cs) in D.items())
        nb = N8 if conn == 8 else N4
        for d, q in order:
            if d == 0: continue
            vals = {S.get(out[q[0] + dy][q[1] + dx]) for dy, dx in nb
                    if (q[0] + dy, q[1] + dx) in D and D[(q[0] + dy, q[1] + dx)][0] == d - 1}
            if len(vals) != 1 or None in vals: return None
            out[q[0]][q[1]] = vals.pop()
        return out
    return fn


def _layers(g, bg):
    """per object (4-conn non-bg component; whole grid if bg None): nested colour layers from outside in"""
    h, w = H(g), W(g)
    cells = {(y, x) for y in range(h) for x in range(w) if bg is None or g[y][x] != bg}
    out = [r[:] for r in g]; seen = set(); changed = False
    for s in sorted(cells):
        if s in seen: continue
        comp = {s}; st = [s]
        while st:
            y, x = st.pop()
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if q in cells and q not in comp: comp.add(q); st.append(q)
        seen |= comp
        L = {}; dq = deque()
        for (y, x) in comp:
            if any((y + dy, x + dx) not in comp for dy, dx in N4):
                L[(y, x)] = 0; dq.append((y, x))
        cols0 = {g[y][x] for (y, x) in L}
        if len(cols0) != 1: return None
        while dq:
            p = dq.popleft()
            for dy, dx in N4:
                q = (p[0] + dy, p[1] + dx)
                if q not in comp: continue
                nd = L[p] + (g[q[0]][q[1]] != g[p[0]][p[1]])
                if q not in L or nd < L[q]:
                    L[q] = nd
                    if nd == L[p]: dq.appendleft(q)
                    else: dq.append(q)
        lc = {}
        for q, l in L.items():
            if lc.setdefault(l, g[q[0]][q[1]]) != g[q[0]][q[1]]: return None
        n = max(lc) + 1
        if n < 2: continue
        for q, l in L.items():
            out[q[0]][q[1]] = lc[n - 1 - l]
        changed = True
    return out if changed else None


def fam_reverse_layers(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    for mode in ('bg', 'none'):
        fn = (lambda g: _layers(g, bg_of(g))) if mode == 'bg' else (lambda g: _layers(g, None))
        r = fn(i0)
        if r is None: continue
        yield (f"distlayers:reverse[{mode}]", 4, fn)


FAMILIES = (fam_distance_layers, fam_reverse_layers)
