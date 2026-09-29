"""COMBINATORICS prior: the output is a PERMUTATION of parts of the input.

Concept
-------
A grid is decomposed into an ordered sequence of parts (slots).  The output keeps the slot
structure but reassigns content to slots by a permutation pi.  pi is never memorised per task;
it is explained by one of a small set of generic permutation generators:

    rev            pi(i) = n-1-i                         (reversal)
    shift+k        pi(i) = (i+k) mod n, k in {+-1,+-2}   (cyclic rotation)
    sort:key:dir   items stably sorted by an induced key (asc/desc)
    fixed          a constant index permutation (only when n is identical in every pair and test)
    slot order     items (in canonical order) written into slots in another traversal
                   (row-major / col-major / snake / reversed) -- dihedral action on a panel lattice

Search space (all parameters induced from the training pairs, verified on every pair)
-------------------------------------------------------------------------------------
F1 axis parts   : rows|cols decomposed as unit lines, k-line groups, separator-delimited
                  strips (separator colour induced) or bands (maximal runs with equal majority colour);
                  the part sequence is permuted (rev / shift / sort by key / fixed).
F2 panel lattice: separator lattice of equal panels; panels sorted by key (or kept) and written
                  into a slot traversal (8 traversals).
F3 item attrs   : items = objects (or cells of a simple path); ordered along x, y, angle about
                  their common centroid, nesting (bbox area) or the path; the COLOUR sequence and
                  the SHAPE sequence (shape re-anchored at an alignment point) are permuted
                  independently (id / rev / shift / sort by size).  Rules are inferred by matching
                  the input and output item sequences, then re-verified by the harness.
F4 legend perm  : a small solid legend block of adjacent colour pairs defines a colour permutation
                  (swap = transpositions, or directed map) applied to the rest of the grid.
F5 sort & pack  : objects / panels cropped, ordered by key or position, concatenated along an axis
                  (optionally with an induced separator line between them).
"""
import sys
sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from itertools import product
import math
from gdsl import H, W, T, bg_of, objects, bbox, crop, colours, static_colours

# ------------------------------------------------------------------ permutation generators
SHIFTS = (1, -1, 2, -2)

def perm_rules(n, keys=None):
    """Yield (rule_name, perm) where new position i receives item perm[i]."""
    if n < 2: return
    yield 'rev', list(range(n - 1, -1, -1))
    for k in SHIFTS:
        if abs(k) < n:
            yield f'shift{k:+d}', [(i + k) % n for i in range(n)]
    if keys:
        for kn, kv in keys.items():
            if len(set(kv)) < 2: continue
            yield f'sort:{kn}:asc', sorted(range(n), key=lambda i: (kv[i], i))
            yield f'sort:{kn}:desc', sorted(range(n), key=lambda i: (-kv[i], i))

def apply_rule(rule, n, keys=None, fixed=None):
    if rule == 'id': return list(range(n))
    if rule == 'rev': return list(range(n - 1, -1, -1))
    if rule.startswith('shift'):
        k = int(rule[5:])
        if abs(k) >= n: return None
        return [(i + k) % n for i in range(n)]
    if rule.startswith('sort:'):
        _, kn, d = rule.split(':')
        kv = keys.get(kn) if keys else None
        if kv is None: return None
        s = 1 if d == 'asc' else -1
        return sorted(range(n), key=lambda i: (s * kv[i], i))
    if rule == 'fixed':
        return list(fixed) if fixed is not None and len(fixed) == n else None
    return None

def infer_fixed(src, dst):
    """Index permutation p with dst[i] == src[p[i]] (greedy on duplicates)."""
    if len(src) != len(dst): return None
    used = set(); p = []
    for d in dst:
        j = next((j for j, s in enumerate(src) if j not in used and s == d), None)
        if j is None: return None
        used.add(j); p.append(j)
    return p

def part_keys(parts, bg, cols):
    """Generic sort keys of sub-grids."""
    keys = {'fg': [sum(v != bg for r in p for v in r) for p in parts],
            'ncol': [len({v for r in p for v in r} - {bg}) for p in parts],
            'nobj': [len(objects(p, bg, False, True)) for p in parts]}
    for c in sorted(cols):
        keys[f'c{c}'] = [sum(v == c for r in p for v in r) for p in parts]
    return keys

# ------------------------------------------------------------------ F1: axis parts
def axis_parts(lines, mode):
    """lines: list of tuples. Returns (segments, movable flags) covering all lines in order."""
    n = len(lines)
    if mode == 'unit':
        return [(i, i + 1) for i in range(n)], [True] * n
    if mode.startswith('k'):
        k = int(mode[1:])
        if n % k or n // k < 2: return None
        return [(i, i + k) for i in range(0, n, k)], [True] * (n // k)
    if mode == 'sep':
        # separator colour: a colour whose uniform lines cut the axis into >= 2 equal parts
        ucols = Counter(ln[0] for ln in lines if len(set(ln)) == 1)
        for sc, _ in sorted(ucols.items(), key=lambda t: (t[1], t[0])):
            issep = [len(set(ln)) == 1 and ln[0] == sc for ln in lines]
            if all(issep): continue
            segs, mov = [], []; i = 0
            while i < n:
                j = i
                while j < n and issep[j] == issep[i]: j += 1
                segs.append((i, j)); mov.append(not issep[i]); i = j
            if sum(mov) < 2: continue
            if len({b - a for (a, b), m in zip(segs, mov) if m}) != 1: continue
            return segs, mov
        return None
    if mode == 'band':
        sig = [Counter(ln).most_common(1)[0][0] for ln in lines]
        segs = []; i = 0
        while i < n:
            j = i
            while j < n and sig[j] == sig[i]: j += 1
            segs.append((i, j)); i = j
        if len(segs) < 2 or len(segs) == n: return None
        return segs, [True] * len(segs)
    return None

def permute_axis(g, axis, mode, rule, keyname, fixed):
    lines = [tuple(r) for r in (g if axis == 'rows' else T(g))]
    ap = axis_parts(lines, mode)
    if not ap: return None
    segs, mov = ap
    items = [lines[a:b] for (a, b), m in zip(segs, mov) if m]
    n = len(items)
    keys = None
    if rule.startswith('sort:'):
        bg = bg_of(g)
        parts = [[list(l) for l in it] for it in items]
        keys = part_keys(parts, bg, colours(g))
    p = apply_rule(rule, n, keys, fixed)
    if p is None: return None
    new = [items[j] for j in p]
    if mode != 'sep' and any(len(a) != len(b) for a, b in zip(new, items)) and mode != 'band':
        return None
    out = []; it = iter(new)
    for (a, b), m in zip(segs, mov):
        out.extend(next(it) if m else lines[a:b])
    out = [list(r) for r in out]
    return out if axis == 'rows' else T(out)

def fam_axis_permute(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if all(p['input'] == p['output'] for p in train): return
    for axis in ('rows', 'cols'):
        # the multiset of lines across the axis must be preserved in every pair
        def L(g): return [tuple(r) for r in (g if axis == 'rows' else T(g))]
        if not all(Counter(L(p['input'])) == Counter(L(p['output'])) for p in train): continue
        n0 = len(L(i0))
        modes = ['unit', 'sep', 'band'] + [f'k{k}' for k in (2, 3, 4, 5) if n0 % k == 0]
        for mode in modes:
            aps = [axis_parts(L(p['input']), mode) for p in train]
            if not all(aps): continue
            # candidate rules consistent with pair 0
            ok_rules = []
            fixed = None
            segs, mov = aps[0]; lines = L(i0); lo = L(o0)
            items = [tuple(lines[a:b]) for (a, b), m in zip(segs, mov) if m]
            n = len(items)
            if n < 2: continue
            parts = [[list(l) for l in it] for it in items]
            keys = part_keys(parts, bg_of(i0), colours(i0))
            cand = ['rev'] + [f'shift{k:+d}' for k in SHIFTS] + \
                   [f'sort:{kn}:{d}' for kn in keys for d in ('asc', 'desc')]
            ns = {len([m for m in axis_parts(L(p['input']), mode)[1] if m]) for p in train}
            if len(ns) == 1:
                ns_test = True
                # fixed permutation inferred from pair 0 (output segmented like input)
                if mode != 'band':
                    outs_items = [tuple(lo[a:b]) for (a, b), m in zip(segs, mov) if m]
                    fixed = infer_fixed(items, outs_items)
                    if fixed and fixed != list(range(n)): cand.append('fixed')
            for rule in cand:
                if all(permute_axis(p['input'], axis, mode, rule, None, fixed) == p['output'] for p in train):
                    ok_rules.append(rule)
            for rule in ok_rules[:6]:
                yield (f'perm-axis[{axis},{mode}]:{rule}', 4 if rule != 'fixed' else 5,
                       lambda g, axis=axis, mode=mode, rule=rule, fixed=fixed: permute_axis(g, axis, mode, rule, None, fixed))

# ------------------------------------------------------------------ F2: panel lattice
def lattice(g):
    """Separator lattice: returns (row_ranges, col_ranges) of equal-size panels, or None."""
    h, w = H(g), W(g)
    best = None
    for sc in colours(g):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols: continue
        if len(rows) == h or len(cols) == w: continue
        def runs(sep, n):
            out = []; s = 0
            for x in list(sep) + [n]:
                if x > s: out.append((s, x))
                s = x + 1
            return out
        rr, cc = runs(rows, h), runs(cols, w)
        if len(rr) * len(cc) < 2: continue
        if len({b - a for a, b in rr}) != 1 or len({b - a for a, b in cc}) != 1: continue
        if best is None or len(rr) * len(cc) > len(best[0]) * len(best[1]): best = (rr, cc)
    return best

def slot_order(R, C, how):
    """Traversal of an R x C lattice: primary axis (row/col), start corner, plain or boustrophedon."""
    prim, fr, fc, snake = how.split('.')
    rs = list(range(R))[::-1] if fr == '1' else list(range(R))
    cs = list(range(C))[::-1] if fc == '1' else list(range(C))
    o = []
    if prim == 'row':
        for k, r in enumerate(rs): o += [(r, c) for c in (cs[::-1] if snake == 's' and k % 2 else cs)]
    else:
        for k, c in enumerate(cs): o += [(r, c) for r in (rs[::-1] if snake == 's' and k % 2 else rs)]
    return o

SLOTS = tuple(f'{p}.{a}.{b}.{s}' for p in ('row', 'col') for a in '01' for b in '01' for s in ('p', 's'))

def permute_lattice_fixed(g, fixed):
    lt = lattice(g)
    if not lt: return None
    rr, cc = lt
    boxes = [(a, b, e, f) for (a, e) in rr for (b, f) in cc]
    if len(boxes) != len(fixed): return None
    panels = [crop(g, (a, b, e - 1, f - 1)) for a, b, e, f in boxes]
    out = [r[:] for r in g]
    for (a, b, e, f), j in zip(boxes, fixed):
        for y in range(e - a):
            for x in range(f - b): out[a + y][b + x] = panels[j][y][x]
    return out

def permute_lattice(g, key, d, slots):
    lt = lattice(g)
    if not lt: return None
    rr, cc = lt
    panels = [(r, c, crop(g, (a, b, e - 1, f - 1))) for r, (a, e) in enumerate(rr) for c, (b, f) in enumerate(cc)]
    bg = bg_of(g)
    if key == 'none':
        order = list(range(len(panels)))
    else:
        keys = part_keys([p[2] for p in panels], bg, colours(g))
        if key not in keys: return None
        s = 1 if d == 'asc' else -1
        order = sorted(range(len(panels)), key=lambda i: (s * keys[key][i], i))
    so = slot_order(len(rr), len(cc), slots)
    out = [r[:] for r in g]
    for (r, c), j in zip(so, order):
        (a, e), (b, f) = rr[r], cc[c]
        pg = panels[j][2]
        for y in range(e - a):
            for x in range(f - b):
                out[a + y][b + x] = pg[y][x]
    return out

def fam_lattice_permute(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if not lattice(i0): return
    keys = list(part_keys([i0], bg_of(i0), colours(i0)).keys())
    cnt = 0
    lt = lattice(i0); lo = lattice(o0)
    if lt and lt == lo and len({len(lattice(p['input'])[0]) * len(lattice(p['input'])[1]) if lattice(p['input']) else 0 for p in train}) == 1:
        rr, cc = lt
        pi = [str(crop(i0, (a, b, e - 1, f - 1))) for (a, e) in rr for (b, f) in cc]
        po = [str(crop(o0, (a, b, e - 1, f - 1))) for (a, e) in rr for (b, f) in cc]
        fx = infer_fixed(pi, po)
        if fx and fx != list(range(len(fx))) and len(set(pi)) == len(pi):
            fn = lambda g, fx=fx: permute_lattice_fixed(g, fx)
            if all(fn(p['input']) == p['output'] for p in train):
                cnt += 1
                yield ('perm-lattice:fixed', 5, fn)
    for key in ['none'] + keys:
        for d in (('asc',) if key == 'none' else ('asc', 'desc')):
            for sl in SLOTS:
                if key == 'none' and sl == 'row.0.0.p': continue
                if all(permute_lattice(p['input'], key, d, sl) == p['output'] for p in train):
                    cnt += 1
                    yield (f'perm-lattice:{key}:{d}->{sl}', 4 if key == 'none' else 5,
                           lambda g, key=key, d=d, sl=sl: permute_lattice(g, key, d, sl))
                    if cnt >= 4: return

# ------------------------------------------------------------------ F3: item attribute permutation
def get_items(g, bg, mode, st):
    """Items = list of cell lists; mode: obj4 / obj8 (single colour objects, static colours optionally excluded) / path."""
    if mode == 'path':
        obs = objects(g, bg, False, False)
        obs = [o for o in obs if not all(g[y][x] in st for y, x in o)]
        if len(obs) != 1: return None
        ob = set(obs[0])
        deg = {c: sum((c[0] + dy, c[1] + dx) in ob for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))) for c in ob}
        ends = [c for c, k in deg.items() if k == 1]
        if len(ends) != 2 or any(k > 2 for k in deg.values()): return None
        cur = min(ends); seq = [cur]; seen = {cur}
        while True:
            nx = [(cur[0] + dy, cur[1] + dx) for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nx = [c for c in nx if c in ob and c not in seen]
            if not nx: break
            cur = nx[0]; seq.append(cur); seen.add(cur)
        if len(seq) != len(ob): return None
        return [[c] for c in seq]
    diag = mode.endswith('8')
    obs = objects(g, -1 if 'all' in mode else bg, diag, True)
    if mode.startswith('ns'):
        obs = [o for o in obs if g[o[0][0]][o[0][1]] not in st]
    return obs

def order_items(items, how):
    if how == 'path': return items
    if how == 'x': return sorted(items, key=lambda o: (bbox(o)[1], bbox(o)[0]))
    if how == 'y': return sorted(items, key=lambda o: (bbox(o)[0], bbox(o)[1]))
    if how == 'nest':
        return sorted(items, key=lambda o: (-(bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1), bbox(o)))
    if how == 'angle':
        cs = [(sum(y for y, _ in o) / len(o), sum(x for _, x in o) / len(o)) for o in items]
        cy = sum(c[0] for c in cs) / len(cs); cx = sum(c[1] for c in cs) / len(cs)
        ang = [math.atan2(c[1] - cx, -(c[0] - cy)) % (2 * math.pi) for c in cs]
        if any(abs(c[0] - cy) < 1e-9 and abs(c[1] - cx) < 1e-9 for c in cs): return None
        return [o for _, o in sorted(zip(ang, items), key=lambda t: (round(t[0], 9), bbox(t[1])))]
    return None

def norm_shape(o):
    r0, c0, _, _ = bbox(o)
    return tuple(sorted((y - r0, x - c0) for y, x in o))

def anchor(o, align):
    r0, c0, r1, c1 = bbox(o)
    if align == 'tl': return (r0, c0)
    if align == 'tr': return (r0, c1)
    if align == 'bl': return (r1, c0)
    if align == 'br': return (r1, c1)
    return (r0 + r1, c0 + c1)          # centre (doubled coordinates)

def place(shape, a, align):
    hs = max(y for y, _ in shape) + 1; ws = max(x for _, x in shape) + 1
    if align == 'tl': r0, c0 = a
    elif align == 'tr': r0, c0 = a[0], a[1] - ws + 1
    elif align == 'bl': r0, c0 = a[0] - hs + 1, a[1]
    elif align == 'br': r0, c0 = a[0] - hs + 1, a[1] - ws + 1
    else:
        if (a[0] - hs + 1) % 2 or (a[1] - ws + 1) % 2: return None     # centre undefined at half cells
        r0, c0 = (a[0] - hs + 1) // 2, (a[1] - ws + 1) // 2
    return [(r0 + y, c0 + x) for y, x in shape]

SHAPE_KEYS = {'size': len, 'h': lambda s: max(y for y, _ in s) + 1, 'w': lambda s: max(x for _, x in s) + 1}

def is_rect(s):
    return len(s) == (max(y for y, _ in s) + 1) * (max(x for _, x in s) + 1)

def seq_rules(src, dst, allow_sort, keys=None):
    """Rules r with [src[p[i]]] == dst."""
    n = len(src); res = []
    if src == dst: res.append('id')
    if allow_sort and keys is None: keys = {k: [f(s) for s in src] for k, f in SHAPE_KEYS.items()}
    if not allow_sort: keys = None
    for name, p in perm_rules(n, keys):
        if [src[j] for j in p] == dst: res.append(name)
    return res

def attr_permute(g, st, imode, how, crule, srule, align):
    bg = bg_of(g)
    items = get_items(g, bg, imode, st)
    if not items or len(items) < 2: return None
    items = order_items(items, how)
    if items is None: return None
    n = len(items)
    if len({len({g[y][x] for y, x in o}) for o in items}) != 1 or any(len({g[y][x] for y, x in o}) != 1 for o in items): return None
    cols = [g[o[0][0]][o[0][1]] for o in items]
    shapes = [norm_shape(o) for o in items]
    keys = {k: [f(s) for s in shapes] for k, f in SHAPE_KEYS.items()}
    pc = apply_rule(crule, n)
    if srule.startswith('L'):                 # permute only the bar length along one axis
        if not all(is_rect(sh) for sh in shapes): return None
        ax, r = srule[1], srule[3:]
        dims = [(SHAPE_KEYS['h'](sh), SHAPE_KEYS['w'](sh)) for sh in shapes]
        lens = [d[0] if ax == 'h' else d[1] for d in dims]
        pl = apply_rule(r, n, {'len': lens})
        if pl is None: return None
        newdims = [(lens[pl[i]], dims[i][1]) if ax == 'h' else (dims[i][0], lens[pl[i]]) for i in range(n)]
        shapes = shapes + [tuple((y, x) for y in range(a) for x in range(b)) for a, b in newdims]
        ps = [n + i for i in range(n)]
    else:
        ps = apply_rule(srule, n, keys)
    if pc is None or ps is None: return None
    out = [r[:] for r in g]
    if srule == 'id':
        for o, j in zip(items, pc):
            for y, x in o: out[y][x] = cols[j]
        return out
    for o in items:
        for y, x in o: out[y][x] = bg
    for i, o in enumerate(items):
        cells = place(shapes[ps[i]], anchor(o, align), align)
        if cells is None: return None
        for y, x in cells:
            if not (0 <= y < H(g) and 0 <= x < W(g)): return None
            out[y][x] = cols[pc[i]]
    return out

IMODES = ('obj4', 'ns-obj4', 'obj8', 'ns-obj8', 'all4', 'ns-all4', 'path')
ORDERS = ('angle', 'nest', 'x', 'y')

def fam_attr_permute(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    if all(p['input'] == p['output'] for p in train): return
    st = static_colours(train)
    found = 0
    for imode in IMODES:
        if imode.startswith('ns') and not st: continue
        for how in (('path',) if imode == 'path' else ORDERS):
            cands = None
            for p in train:
                gi, go = p['input'], p['output']; bg = bg_of(gi)
                a = get_items(gi, bg, imode, st); b = get_items(go, bg, imode, st)
                if not a or not b or len(a) != len(b) or len(a) < 2: cands = set(); break
                a = order_items(a, how); b = order_items(b, how)
                if a is None or b is None: cands = set(); break
                if any(len({gi[y][x] for y, x in o}) != 1 for o in a) or any(len({go[y][x] for y, x in o}) != 1 for o in b):
                    cands = set(); break
                ca = [gi[o[0][0]][o[0][1]] for o in a]; cb = [go[o[0][0]][o[0][1]] for o in b]
                sa = [norm_shape(o) for o in a]; sb = [norm_shape(o) for o in b]
                cr = seq_rules(ca, cb, False)
                sr = seq_rules(sa, sb, True)
                if all(is_rect(x) for x in sa + sb) and 'id' not in sr:
                    for ax, k0, k1 in (('h', 0, 1), ('w', 1, 0)):
                        da = [(SHAPE_KEYS['h'](x), SHAPE_KEYS['w'](x)) for x in sa]
                        db = [(SHAPE_KEYS['h'](x), SHAPE_KEYS['w'](x)) for x in sb]
                        if [d[k1] for d in da] != [d[k1] for d in db]: continue
                        la = [d[k0] for d in da]; lb = [d[k0] for d in db]
                        sr += [f'L{ax}:{r}' for r in seq_rules(la, lb, True, {'len': la}) if r != 'id']
                al = [x for x in ('tl', 'tr', 'bl', 'br', 'c') if all(anchor(u, x) == anchor(v, x) for u, v in zip(a, b))]
                here = {(c, s, x) for c in cr for s in sr for x in (al if s != 'id' else ['-'])}
                if 'id' in sr and len(set(sa)) == 1:     # shapes all equal: shape rule irrelevant
                    here |= {(c, 'id', '-') for c in cr}
                cands = here if cands is None else cands & here
                if not cands: break
            if not cands: continue
            cands = [c for c in cands if (c[0], c[1]) != ('id', 'id')]
            if any(c[1] == 'id' for c in cands):          # colour-only explanation: simplest, keep it alone
                cands = [c for c in cands if c[1] == 'id']
            for crule, srule, align in sorted(cands)[:4]:
                fn = lambda g, imode=imode, how=how, crule=crule, srule=srule, align=align: \
                    attr_permute(g, st, imode, how, crule, srule, align)
                if all(fn(p['input']) == p['output'] for p in train):
                    found += 1
                    yield (f'perm-attr[{imode},{how}]:colour={crule},shape={srule}@{align}', 5, fn)
                    if found >= 6: return

# ------------------------------------------------------------------ F4: legend colour permutation
def legend_blocks(g, bg):
    """Solid (bg-free) rectangular multi-colour objects whose cells are all distinct colours."""
    out = []
    for o in objects(g, bg, True, False):
        r0, c0, r1, c1 = bbox(o)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if len(o) != h * w or len(o) < 2: continue
        vals = [g[y][x] for y, x in o]
        if len(set(vals)) != len(vals): continue
        out.append((r0, c0, r1, c1))
    return out

def legend_perm(g, orient, kind):
    bg = bg_of(g)
    bl = legend_blocks(g, bg)
    if len(bl) != 1: return None
    r0, c0, r1, c1 = bl[0]
    h, w = r1 - r0 + 1, c1 - c0 + 1
    m = {}
    if orient == 'h':
        if w != 2: return None
        pairs = [(g[y][c0], g[y][c0 + 1]) for y in range(r0, r1 + 1)]
    else:
        if h != 2: return None
        pairs = [(g[r0][x], g[r0 + 1][x]) for x in range(c0, c1 + 1)]
    for a, b in pairs:
        if kind in ('swap', 'fwd'): m[a] = b
        if kind in ('swap', 'bwd'): m[b] = a
    if kind == 'swap' and len(m) != 2 * len(pairs): return None
    out = [r[:] for r in g]
    for y in range(H(g)):
        for x in range(W(g)):
            if r0 <= y <= r1 and c0 <= x <= c1: continue
            out[y][x] = m.get(g[y][x], g[y][x])
    return out

def fam_legend_perm(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if len(legend_blocks(i0, bg_of(i0))) != 1: return
    for orient, kind in product(('h', 'v'), ('swap', 'fwd', 'bwd')):
        fn = lambda g, orient=orient, kind=kind: legend_perm(g, orient, kind)
        if all(fn(p['input']) == p['output'] for p in train):
            yield (f'perm-legend[{orient}]:{kind}', 4, fn)

# ------------------------------------------------------------------ F5: sort & pack
PACK_ORDERS = {
    'x': lambda o: (bbox(o)[1], bbox(o)[0]), 'y': lambda o: (bbox(o)[0], bbox(o)[1]),
    'size-asc': lambda o: (len(o), bbox(o)[0], bbox(o)[1]), 'size-desc': lambda o: (-len(o), bbox(o)[0], bbox(o)[1]),
    'xr': lambda o: (-bbox(o)[3], bbox(o)[0]), 'yr': lambda o: (-bbox(o)[2], bbox(o)[1])}

def pack_items(g, conn, filt):
    bg = bg_of(g)
    obs = objects(g, bg, conn == 8, conn == 4)
    if filt == 'hollow':
        obs = [o for o in obs if len(o) < (bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1)]
    elif filt == 'solid':
        obs = [o for o in obs if len(o) == (bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1)]
    elif filt == 'common-shape':
        c = Counter(norm_shape(o) for o in obs)
        if not c: return None
        top = c.most_common(2)
        if len(top) > 1 and top[0][1] == top[1][1]: return None
        obs = [o for o in obs if norm_shape(o) == top[0][0]]
    return obs, bg

def pack(g, conn, filt, order, axis, canvas=None, slots=None):
    r = pack_items(g, conn, filt)
    if not r: return None
    obs, bg = r
    if not obs: return None
    obs = sorted(obs, key=PACK_ORDERS[order])
    crops = []
    for o in obs:
        r0, c0, r1, c1 = bbox(o); cs = set(o)
        crops.append([[g[y][x] if (y, x) in cs else bg for x in range(c0, c1 + 1)] for y in range(r0, r1 + 1)])
    if canvas:                                  # equal-size items written into a fixed lattice
        R, C = canvas
        h, w = H(crops[0]), W(crops[0])
        if any((H(c), W(c)) != (h, w) for c in crops) or R % h or C % w: return None
        so = slot_order(R // h, C // w, slots)
        if len(crops) > len(so): return None
        out = [[bg] * C for _ in range(R)]
        for (r, c), cr in zip(so, crops):
            for y in range(h):
                for x in range(w): out[r * h + y][c * w + x] = cr[y][x]
        return out
    if axis == 'auto':
        ys = [bbox(o)[0] for o in obs]; xs = [bbox(o)[1] for o in obs]
        sy, sx = max(ys) - min(ys), max(xs) - min(xs)
        if sy == sx: return None
        axis = 'h' if sx > sy else 'v'
        if order in ('x', 'y'):
            crops = [crops[i] for i in sorted(range(len(obs)), key=lambda i: (bbox(obs[i])[1], bbox(obs[i])[0]) if axis == 'h' else (bbox(obs[i])[0], bbox(obs[i])[1]))]
    if axis == 'h':
        if len({H(c) for c in crops}) != 1: return None
        return [sum((c[y] for c in crops), []) for y in range(H(crops[0]))]
    if len({W(c) for c in crops}) != 1: return None
    return [row for c in crops for row in c]

def fam_sort_pack(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if H(o0) * W(o0) >= H(i0) * W(i0): return
    shapes = {(H(p['output']), W(p['output'])) for p in train}
    canvas = shapes.pop() if len(shapes) == 1 else None
    n = 0
    for conn, filt in product((4, 8), ('all', 'hollow', 'solid', 'common-shape')):
        pre = pack_items(i0, conn, filt)
        if not pre or len(pre[0]) < 2: continue
        tried = []
        for order in PACK_ORDERS:
            for axis in ('auto', 'h', 'v'):
                if axis == 'auto' and order not in ('x', 'y'): continue
                tried.append((order, axis, None, None))
            if canvas:
                for sl in SLOTS: tried.append((order, None, canvas, sl))
        for order, axis, cv, sl in tried:
            fn = lambda g, conn=conn, filt=filt, order=order, axis=axis, cv=cv, sl=sl: pack(g, conn, filt, order, axis, cv, sl)
            if fn(i0) != o0: continue
            if all(fn(p['input']) == p['output'] for p in train[1:]):
                n += 1
                yield (f'sort-pack[{conn},{filt}]:{order}->{axis or sl}', 5, fn)
                if n >= 4: return

# ------------------------------------------------------------------ F6: panel chain (Hamiltonian path of edge-compatible panels)
def lattice_panels(g):
    lt = lattice(g)
    if not lt: return None
    rr, cc = lt
    sep = None
    if len(rr) > 1: sep = g[rr[0][1]][0]
    elif len(cc) > 1: sep = g[0][cc[0][1]]
    return [crop(g, (a, b, e - 1, f - 1)) for (a, e) in rr for (b, f) in cc], sep

def edge_set(p, side, bg):
    if side == 'top': ln = p[0]
    elif side == 'bottom': ln = p[-1]
    elif side == 'left': ln = [r[0] for r in p]
    else: ln = [r[-1] for r in p]
    return frozenset(i for i, v in enumerate(ln) if v != bg)

def chain_order(panels, axis, bg):
    far, near = ('bottom', 'top') if axis == 'v' else ('right', 'left')
    n = len(panels)
    F = [edge_set(p, far, bg) for p in panels]; N = [edge_set(p, near, bg) for p in panels]
    sols = []
    def rec(path, used):
        if len(sols) > 1: return
        if len(path) == n: sols.append(path[:]); return
        last = path[-1]
        for j in range(n):
            if j not in used and F[last] and F[last] == N[j]:
                path.append(j); used.add(j); rec(path, used); path.pop(); used.discard(j)
    for s0 in range(n):
        if N[s0]: continue                      # the chain starts at a panel with an empty near edge
        rec([s0], {s0})
    return sols[0] if len(sols) == 1 else None

def panel_chain(g, axis_rule):
    lp = lattice_panels(g)
    if not lp: return None
    panels, sep = lp
    bg = bg_of(g)
    if len({(H(p), W(p)) for p in panels}) != 1 or len(panels) < 2: return None
    found = []
    for axis in ('v', 'h'):
        o = chain_order(panels, axis, bg)
        if o: found.append((axis, o))
    if len(found) != 1: return None
    axis, o = found[0]
    ps = [panels[j] for j in o]
    if axis == 'v':
        out = []
        for k, p in enumerate(ps):
            if k: out.append([sep] * W(p))
            out += [r[:] for r in p]
        return out
    out = [[] for _ in range(H(ps[0]))]
    for k, p in enumerate(ps):
        for y in range(H(p)):
            out[y] += ([sep] if k else []) + p[y]
    return out

def fam_panel_chain(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) == (H(o0), W(o0)) and not lattice(i0): return
    if not lattice(i0): return
    fn = lambda g: panel_chain(g, 'auto')
    if all(fn(p['input']) == p['output'] for p in train):
        yield ('panel-chain:edge-match', 5, fn)

# ------------------------------------------------------------------ F7: class transposition (two shape classes swap)
def class_swap(g, conn, carry, align):
    bg = bg_of(g)
    obs = objects(g, bg, conn == 8, True)
    cl = {}
    for o in obs: cl.setdefault(g[o[0][0]][o[0][1]], []).append(o)
    if len(cl) != 2: return None
    (ca, A), (cb, B) = sorted(cl.items())
    sa = {norm_shape(o) for o in A}; sb = {norm_shape(o) for o in B}
    if len(sa) != 1 or len(sb) != 1 or sa == sb: return None
    sa, sb = sa.pop(), sb.pop()
    out = [r[:] for r in g]
    for o in obs:
        for y, x in o: out[y][x] = bg
    for group, own, other_shape, other_col in ((A, ca, sb, cb), (B, cb, sa, ca)):
        for o in group:
            cells = place(other_shape, anchor(o, align), align)
            if cells is None: return None
            for y, x in cells:
                if not (0 <= y < H(g) and 0 <= x < W(g)): return None
                out[y][x] = other_col if carry else own
    return out

def fam_class_swap(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    n = 0
    for conn, carry, align in product((4, 8), (True, False), ('tl', 'tr', 'bl', 'br', 'c')):
        fn = lambda g, conn=conn, carry=carry, align=align: class_swap(g, conn, carry, align)
        if fn(i0) != o0: continue
        if all(fn(p['input']) == p['output'] for p in train[1:]):
            n += 1
            yield (f'class-swap[{conn}]:{"carry" if carry else "keep"}-colour@{align}', 4, fn)
            if n >= 3: return

# ------------------------------------------------------------------ F8: sorted stack against a wall
def sorted_stack(g, st, edge, order, cross):
    """Remove the movable items, sort them, and stack them one per band starting at the first free line
    next to `edge` (the wall), each aligned to the start/end of the cross axis."""
    gg = g if edge in ('bottom', 'top') else T(g)
    if edge in ('top', 'left'): gg = gg[::-1]
    bg = bg_of(g)
    obs = [o for o in objects(gg, bg, False, True) if gg[o[0][0]][o[0][1]] not in st]
    if len(obs) < 2: return None
    out = [r[:] for r in gg]
    for o in obs:
        for y, x in o: out[y][x] = bg
    y = H(out) - 1
    while y >= 0 and any(v != bg for v in out[y]): y -= 1
    if y < 0: return None
    obs = sorted(obs, key=PACK_ORDERS[order])
    for o in obs:
        sh = norm_shape(o); col = gg[o[0][0]][o[0][1]]
        hs = max(a for a, _ in sh) + 1; ws = max(b for _, b in sh) + 1
        r0 = y - hs + 1; c0 = 0 if cross == 'start' else W(out) - ws
        if r0 < 0: return None
        for a, b in sh:
            if out[r0 + a][c0 + b] != bg: return None
            out[r0 + a][c0 + b] = col
        y = r0 - 1
    if edge in ('top', 'left'): out = out[::-1]
    return out if edge in ('bottom', 'top') else T(out)

def fam_sorted_stack(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    st = static_colours(train)
    n = 0
    for edge, order, cross in product(('bottom', 'top', 'left', 'right'), ('size-desc', 'size-asc'), ('start', 'end')):
        fn = lambda g, edge=edge, order=order, cross=cross: sorted_stack(g, st, edge, order, cross)
        if fn(i0) != o0: continue
        if all(fn(p['input']) == p['output'] for p in train[1:]):
            n += 1
            yield (f'sorted-stack[{edge}]:{order},{cross}', 5, fn)
            if n >= 2: return

FAMILIES = (fam_axis_permute, fam_lattice_permute, fam_attr_permute, fam_legend_perm, fam_sort_pack, fam_panel_chain, fam_class_swap, fam_sorted_stack)
