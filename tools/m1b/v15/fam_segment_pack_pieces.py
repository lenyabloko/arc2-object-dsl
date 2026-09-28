"""segment.pack_pieces: the input's pieces (objects) are moved -- translated, optionally rotated /
reflected -- so that together they tile a target shape exactly; the output is that shape.

One parametrised primitive  pack[seg, target, moves, dims, canon, recolour]:
  seg      : c8 (single-colour 8-connected objects) | m8 (multi-colour 8-connected objects)
             | m8h (m8, enclosed background holes count as part of the piece)
  target   : full (solid h x w rectangle, h*w = #fg cells)
           | frame (border of an h x w rectangle, 2(h+w)-4 = #fg cells; interior = input background)
  moves    : T (translate only) | R (+ 90-degree rotations) | D (+ reflections)
  dims     : wide | tall  -- among the factorisations of the area with that orientation, the most
             square one that admits a (canonical, unique) tiling is used
  canon    : none   -- the tiling must be unique
           | keycell -- the single off-colour cell inside a piece (key) ends at the top-left corner
           | keypiece -- the piece carrying the key keeps its input orientation
           | largest -- the (unique) largest piece keeps its input orientation
  recolour : none | key -- the key is a kh x kw off-colour block inside one piece (kh*kw = #pieces);
             the output is cut into a kh x kw zone grid and every piece takes the key colour of the
             zone it mostly covers (pieces <-> zones must be a bijection)
All parameters are induced: a program is yielded only when it reproduces every training output.
Tilings are found by exact-cover backtracking (first empty cell in row-major order).
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects

MAX_PIECES, MAX_AREA, MAX_SOL, NODE_BUDGET = 9, 225, 48, 60000
class _Budget(Exception): pass

# ------------------------------------------------------------------ pieces
def _holes(cells, h, w):
    """bg cells enclosed by the piece (not 4-connected to the bbox border outside the piece)."""
    s = {(y, x) for y, x, _ in cells}
    y0 = min(y for y, _ in s); x0 = min(x for _, x in s); y1 = max(y for y, _ in s); x1 = max(x for _, x in s)
    free = {(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if (y, x) not in s}
    st = [c for c in free if c[0] in (y0, y1) or c[1] in (x0, x1)]; out = set(st)
    while st:
        y, x = st.pop()
        for q in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if q in free and q not in out: out.add(q); st.append(q)
    return free - out

def _pieces(g, bg, seg):
    objs = objects(g, bg, diag=True, by_colour=(seg == 'c8'))
    ps = [[(y, x, g[y][x]) for y, x in o] for o in objs]
    if seg == 'm8h':  # enclosed background holes belong to the piece (take its main colour)
        for p in ps:
            main = Counter(v for _, _, v in p).most_common(1)[0][0]
            p.extend((y, x, main) for y, x in _holes(p, H(g), W(g)))
    return ps

def _norm(cells):
    y0 = min(c[0] for c in cells); x0 = min(c[1] for c in cells)
    s = sorted((y - y0, x - x0, v) for y, x, v in cells)
    # anchor = first cell in row-major order
    ay, ax = s[0][0], s[0][1]
    return tuple((y - ay, x - ax, v) for y, x, v in s)

def _variants(cells, moves):
    out, seen = [], set()
    cur = [(y, x, v) for y, x, v in cells]
    ops = []
    for refl in ((False, True) if moves == 'D' else (False,)):
        for k in (range(4) if moves in ('R', 'D') else range(1)):
            ops.append((refl, k))
    for refl, k in ops:
        c = [(y, -x, v) for y, x, v in cur] if refl else list(cur)
        for _ in range(k):
            c = [(x, -y, v) for y, x, v in c]  # rotate 90 cw
        n = _norm(c)
        if n not in seen:
            seen.add(n); out.append(n)
    return out  # out[0] is the identity orientation

def _key(pieces, kind, g=None):
    """Locate the key: off-colour cells inside the one multi-colour piece.
    kind 'cell' -> a single cell; 'block' -> the bbox of the off-colour cells, read from the grid
    (a kh x kw layout of colours, possibly with bg holes), with kh*kw == number of pieces."""
    found = None
    for i, p in enumerate(pieces):
        cnt = Counter(v for _, _, v in p)
        if len(cnt) < 2: continue
        main = cnt.most_common(1)[0][0]
        minor = [(y, x, v) for y, x, v in p if v != main]
        if found is not None: return None
        found = (i, main, minor)
    if found is None: return None
    i, main, minor = found
    if kind == 'cell':
        return (i, minor[0]) if len(minor) == 1 else None
    if len(minor) < 4: return None
    y0 = min(c[0] for c in minor); x0 = min(c[1] for c in minor)
    y1 = max(c[0] for c in minor); x1 = max(c[1] for c in minor)
    kh, kw = y1 - y0 + 1, x1 - x0 + 1
    if kh < 2 or kw < 2 or kh * kw != len(pieces): return None
    if len(minor) < kh * kw - 1: return None
    kb = [row[x0:x1 + 1] for row in g[y0:y1 + 1]]
    cells = {(y, x): v for y, x, v in pieces[i]}
    kb = [[cells.get((y, x), main) for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    return (i, kb, main)

# ------------------------------------------------------------------ exact cover
def _tilings(h, w, target, pvars, cap):
    order = [(y, x) for y in range(h) for x in range(w) if target[y][x]]
    grid = [[-1] * w for _ in range(h)]
    n = len(pvars); used = [False] * n; place = [None] * n; sols = []; budget = [NODE_BUDGET]
    def rec(k):
        if len(sols) >= cap: return
        budget[0] -= 1
        if budget[0] < 0: raise _Budget()
        while k < len(order) and grid[order[k][0]][order[k][1]] != -1: k += 1
        if k == len(order):
            if all(used): sols.append(list(place))
            return
        y, x = order[k]
        for i in range(n):
            if used[i]: continue
            for vi, var in enumerate(pvars[i]):
                ok = True
                for dy, dx, _ in var:
                    yy, xx = y + dy, x + dx
                    if not (0 <= yy < h and 0 <= xx < w) or not target[yy][xx] or grid[yy][xx] != -1:
                        ok = False; break
                if not ok: continue
                for dy, dx, _ in var: grid[y + dy][x + dx] = i
                used[i] = True; place[i] = (vi, y, x)
                rec(k + 1)
                used[i] = False; place[i] = None
                for dy, dx, _ in var: grid[y + dy][x + dx] = -1
                if len(sols) >= cap: return
    try:
        rec(0)
    except _Budget:
        return None
    return sols

def _dims(n, target, orient):
    c = []
    if target == 'full':
        c = [(a, n // a) for a in range(1, n + 1) if n % a == 0]
    else:
        for a in range(3, n):
            b2 = n + 4 - 2 * a
            if b2 % 2 == 0 and b2 // 2 >= 3: c.append((a, b2 // 2))
    c = [(a, b) for a, b in c if (a <= b if orient == 'wide' else a >= b)]
    c.sort(key=lambda d: (abs(d[0] - d[1]), d))
    return c

def pack(g, seg, target, moves, orient, canon, recolour, tie='unique'):
    bg = bg_of(g)
    pieces = _pieces(g, bg, seg)
    if not (2 <= len(pieces) <= MAX_PIECES): return None
    n = sum(len(p) for p in pieces)
    if n > MAX_AREA: return None
    key = None
    if recolour == 'key':
        key = _key(pieces, 'block', g)
        if key is None: return None
    elif canon == 'keycell':
        key = _key(pieces, 'cell')
        if key is None: return None
    elif canon == 'keypiece':
        key = _key(pieces, 'cell') or _key(pieces, 'block', g)
        if key is None: return None
    pvars = [_variants(p, moves) for p in pieces]
    if canon == 'keypiece':
        pvars[key[0]] = pvars[key[0]][:1]
    elif canon == 'largest':
        sz = sorted((len(p) for p in pieces), reverse=True)
        if sz[0] == sz[1]: return None
        big = max(range(len(pieces)), key=lambda i: len(pieces[i]))
        pvars[big] = pvars[big][:1]
    for h, w in _dims(n, target, orient):
        if h > 30 or w > 30: continue
        tgt = [[1] * w for _ in range(h)] if target == 'full' else \
              [[1 if y in (0, h - 1) or x in (0, w - 1) else 0 for x in range(w)] for y in range(h)]
        sols = _tilings(h, w, tgt, pvars, MAX_SOL)
        if sols is None: return None
        outs = {}
        cen = [(sum(y for y, _, _ in p) / len(p), sum(x for _, x, _ in p) / len(p)) for p in pieces]
        for s in sols:
            o = [[bg] * w for _ in range(h)]
            owner = [[-1] * w for _ in range(h)]
            for i, (vi, y, x) in enumerate(s):
                for dy, dx, v in pvars[i][vi]:
                    o[y + dy][x + dx] = v; owner[y + dy][x + dx] = i
            if canon == 'keycell' and o[0][0] != key[1][2]: continue
            if canon == 'keycell' and owner[0][0] != key[0]: continue
            if recolour == 'key':
                kb = key[1]; kh, kw = len(kb), len(kb[0])
                ov = Counter((owner[y][x], y * kh // h, x * kw // w) for y in range(h) for x in range(w) if owner[y][x] >= 0)
                best = {}
                for (i, zy, zx), c in ov.items():
                    if i not in best or c > best[i][0]: best[i] = (c, zy, zx)
                zones = {(zy, zx) for _, zy, zx in best.values()}
                if len(zones) != len(pieces): continue
                cm = {i: kb[zy][zx] for i, (_, zy, zx) in best.items()}
                o = [[cm[owner[y][x]] if owner[y][x] >= 0 else o[y][x] for x in range(w)] for y in range(h)]
            sc = 0
            if tie == 'order':  # pairwise above/left relations kept from the input layout
                oc = []
                for i, (vi, y, x) in enumerate(s):
                    var = pvars[i][vi]
                    oc.append((y + sum(c[0] for c in var) / len(var), x + sum(c[1] for c in var) / len(var)))
                for i in range(len(pieces)):
                    for j in range(i + 1, len(pieces)):
                        for a in (0, 1):
                            d0 = cen[i][a] - cen[j][a]; d1 = oc[i][a] - oc[j][a]
                            if abs(d0) > 0.5 and d0 * d1 > 0: sc += 1
            k = tuple(map(tuple, o))
            outs[k] = max(outs.get(k, -1), sc)
            if tie == 'unique' and len(outs) > 1: break
        if outs:
            top = max(outs.values()); best = [k for k, v in outs.items() if v == top]
            if len(best) == 1 and (tie == 'order' or len(outs) == 1) and len(sols) < MAX_SOL:
                return [list(r) for r in best[0]]
            return None  # ambiguous at the preferred size
        if len(sols) >= MAX_SOL:
            return None
    return None

# ------------------------------------------------------------------ family
def _fg_count(g):
    bg = bg_of(g); return sum(v != bg for r in g for v in r)

def fam_pack_pieces(train):
    p0 = train[0]; i0, o0 = p0['input'], p0['output']
    if H(o0) * W(o0) >= H(i0) * W(i0): return
    n0 = _fg_count(i0)
    targets = []
    if H(o0) * W(o0) == n0: targets.append('full')
    if H(o0) >= 3 and W(o0) >= 3 and 2 * (H(o0) + W(o0)) - 4 == n0: targets.append('frame')
    if not targets: return
    orient = 'wide' if H(o0) <= W(o0) else 'tall'
    orients = [orient] + (['tall'] if H(o0) == W(o0) else [])
    combos = []
    for target in targets:
        for seg in ('c8', 'm8', 'm8h'):
            for moves in ('T', 'R', 'D'):
                canons = ['none'] + (['largest'] if moves != 'T' else []) + \
                         (['keycell', 'keypiece'] if seg != 'c8' and moves != 'T' else [])
                for canon in canons:
                    recs = ['none'] + (['key'] if seg != 'c8' and canon in ('none', 'keypiece') else [])
                    for rec in recs:
                        for ori in orients:
                            for tie in ('unique', 'order'):
                                combos.append((seg, target, moves, ori, canon, rec, tie))
    rank = {'unique': 0, 'order': 1, 'T': 0, 'R': 1, 'D': 2, 'c8': 0, 'm8': 1, 'm8h': 2}
    combos.sort(key=lambda c: (rank[c[6]], rank[c[2]], rank[c[0]], c[3] != orient))
    fits = []
    for c in combos:
        ok = True
        for p in train:
            try:
                r = pack(p['input'], *c)
            except RecursionError:
                r = None
            if r != p['output']: ok = False; break
        if ok:
            fits.append(c)
            if len(fits) >= 8: break
    if not fits: return
    # one program: the training-consistent parametrisations tried in order of simplicity;
    # the first that yields a (unique) packing of the test input answers.
    def fn(g, fits=fits):
        for c in fits:
            try:
                r = pack(g, *c)
            except RecursionError:
                r = None
            if r is not None: return r
        return None
    c = fits[0]
    name = 'pack[seg=%s,target=%s,moves=%s,dims=%s,canon=%s,recolour=%s,tie=%s]' % c
    yield (name + ('+%dalt' % (len(fits) - 1) if len(fits) > 1 else ''), 5, fn)

FAMILIES = (fam_pack_pieces,)
