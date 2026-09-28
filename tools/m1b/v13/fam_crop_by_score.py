"""crop.by_score: segment the input into units, pick the unit that is the arg-extremum of a score,
output a part of it (bbox / interior / bbox-minus-marker / enclosed content).

One parametrised primitive  crop-by-score[units, score, extremum, part]:
  units    : c4 | c8 (single-colour comps) | m4 | m8 (multi-colour comps) | k2 (clusters, gap<=1)
             | frames (rectangles with a complete one-colour border) | panels (separator lines) | halves
  score    : area | bbox-area | n-colours | minority | count[c] | n-comps[c] | n-shape[c,S]
             | near[c,k] (marker cells within k of the unit, unit itself not of colour c) | has[c]
  extremum : max | min (unique winner required) | all (union of every unit with has[c])
  part     : bbox | inner (bbox shrunk by 1) | nomark[c] (marker colour erased, bbox of rest) | content
All parameters (unit kind, colour c, shape S, distance k, extremum, part) are induced: a program is
only yielded when on every training pair the chosen unit's part equals the output.
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox, crop

# ------------------------------------------------------------------ units
def _rect_cells(r0, c0, r1, c1):
    return [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)]

def _clusters(g, bg, gap):
    h, w = H(g), W(g); seen = set(); out = []
    fg = {(y, x) for y in range(h) for x in range(w) if g[y][x] != bg}
    d = gap + 1
    for s in fg:
        if s in seen: continue
        seen.add(s); st = [s]; cells = []
        while st:
            y, x = st.pop(); cells.append((y, x))
            for dy in range(-d, d + 1):
                for dx in range(-d, d + 1):
                    q = (y + dy, x + dx)
                    if q in fg and q not in seen: seen.add(q); st.append(q)
        out.append(cells)
    return out

def _frames(g, bg):
    """Rectangles >=3x3 whose whole border is one non-bg colour (noise elsewhere allowed); maximal only."""
    h, w = H(g), W(g)
    R = [[0] * (w + 1) for _ in range(h + 1)]; D = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            v = g[y][x]
            R[y][x] = 1 + (R[y][x + 1] if x + 1 < w and g[y][x + 1] == v else 0)
            D[y][x] = 1 + (D[y + 1][x] if y + 1 < h and g[y + 1][x] == v else 0)
    rects = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or R[y][x] < 3 or D[y][x] < 3: continue
            for ww in range(R[y][x], 2, -1):
                for hh in range(D[y][x], 2, -1):
                    x1, y1 = x + ww - 1, y + hh - 1
                    if D[y][x1] >= hh and R[y1][x] >= ww:
                        rects.append((y, x, y1, x1))
    rects = [r for r in rects if not any(o != r and o[0] <= r[0] and o[1] <= r[1] and o[2] >= r[2] and o[3] >= r[3] and g[o[0]][o[1]] == g[r[0]][r[1]] for o in rects)]
    if len(rects) > 40: return []
    return [_rect_cells(*r) for r in rects]

def _panels(g):
    h, w = H(g), W(g)
    for sc in sorted({v for r in g for v in r}):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols or len(rows) == h or len(cols) == w: continue
        rb = [-1] + rows + [h]; cb = [-1] + cols + [w]; out = []
        for a in range(len(rb) - 1):
            for b in range(len(cb) - 1):
                if rb[a + 1] - rb[a] > 1 and cb[b + 1] - cb[b] > 1:
                    out.append(_rect_cells(rb[a] + 1, cb[b] + 1, rb[a + 1] - 1, cb[b + 1] - 1))
        if len(out) >= 2: return out
    return []

def _halves(g):
    h, w = H(g), W(g); out = []
    if w % 2 == 0: out += [_rect_cells(0, 0, h - 1, w // 2 - 1), _rect_cells(0, w // 2, h - 1, w - 1)]
    if h % 2 == 0: out += [_rect_cells(0, 0, h // 2 - 1, w - 1), _rect_cells(h // 2, 0, h - 1, w - 1)]
    return out

UNITS = ('m4', 'm8', 'c4', 'c8', 'k1', 'frames', 'panels', 'halves')
RECT_UNITS = ('frames', 'panels', 'halves')

def border_bg(g):
    h, w = H(g), W(g)
    cells = [g[0][x] for x in range(w)] + [g[h - 1][x] for x in range(w)] + [g[y][0] for y in range(h)] + [g[y][w - 1] for y in range(h)]
    return Counter(cells).most_common(1)[0][0]

BGS = {'mode': bg_of, 'border': border_bg}

def units(g, kind, bg):
    if kind == 'c4': return objects(g, bg, False, True)
    if kind == 'c8': return objects(g, bg, True, True)
    if kind == 'm4': return objects(g, bg, False, False)
    if kind == 'm8': return objects(g, bg, True, False)
    if kind == 'k1': return _clusters(g, bg, 1)
    if kind == 'frames': return _frames(g, bg)
    if kind == 'panels': return _panels(g)
    if kind == 'halves': return _halves(g)
    return []

# ------------------------------------------------------------------ parts
def part(g, u, how, bg):
    if how == 'bbox': return crop(g, bbox(u))
    if how == 'inner':
        r0, c0, r1, c1 = bbox(u)
        if r1 - r0 < 2 or c1 - c0 < 2: return None
        return crop(g, (r0 + 1, c0 + 1, r1 - 1, c1 - 1))
    if how.startswith('nomark'):
        c = int(how[6:])
        if not any(g[y][x] == c for y, x in u): return None
        rest = [(y, x) for y, x in u if g[y][x] != c]
        if not rest: return None
        return [[bg if v == c else v for v in r] for r in crop(g, bbox(rest))]
    if how == 'content':
        r0, c0, r1, c1 = bbox(u); us = set(u)
        sub = [[g[y][x] if (y, x) in us else bg for x in range(W(g))] for y in range(H(g))]
        inner = [ob for ob in objects(sub, bg, False, True)
                 if all(r0 < y < r1 and c0 < x < c1 for y, x in ob)]
        cells = [c for ob in inner for c in ob]
        if not cells: return None
        return crop(g, bbox(cells))
    return None

# ------------------------------------------------------------------ scores
def _shape(cells):
    r0, c0, _, _ = bbox(cells); return tuple(sorted((y - r0, x - c0) for y, x in cells))

def score(g, u, s, bg):
    """Numeric score of unit u, or None when the unit is not a candidate for this score."""
    kind = s[0]
    if kind == 'area': return sum(g[y][x] != bg for y, x in u)
    if kind == 'barea':
        r0, c0, r1, c1 = bbox(u); return (r1 - r0 + 1) * (c1 - c0 + 1)
    vals = [g[y][x] for y, x in u if g[y][x] != bg]
    if kind == 'ncol': return len(set(vals))
    if kind == 'minority':
        if not vals: return 0
        return len(vals) - Counter(vals).most_common(1)[0][1]
    c = s[1]
    if kind == 'cnt': return sum(v == c for v in vals)
    if kind == 'has': return int(c in vals)
    if kind == 'ncomp':
        cells = [(y, x) for y, x in u if g[y][x] == c]
        if not cells: return 0
        sub = [[bg] * W(g) for _ in range(H(g))]
        for y, x in cells: sub[y][x] = c
        return len(objects(sub, bg, False, True))
    if kind == 'nshape':   # occurrences of template S (all cells colour c) inside the unit
        us = set(u); S = s[2]
        return sum(all((y + dy, x + dx) in us and g[y + dy][x + dx] == c for dy, dx in S) for y, x in u)
    if kind == 'near':
        if c in vals: return None
        k = s[2]; r0, c0, r1, c1 = bbox(u)
        return sum(g[y][x] == c for y in range(max(0, r0 - k), min(H(g), r1 + k + 1))
                   for x in range(max(0, c0 - k), min(W(g), c1 + k + 1)))
    return None

def choose(g, us, s, ext, bg, pt=None):
    sc = [score(g, u, s, bg) if (pt is None or ext == 'all' or part(g, u, pt, bg) is not None) else None for u in us]
    idx = [i for i, v in enumerate(sc) if v is not None]
    if len(idx) < 2: return None
    if ext == 'all':
        hits = [i for i in idx if sc[i] == 1]
        if not hits or len(hits) == len(idx): return None
        return [c for i in hits for c in us[i]]
    key = (lambda i: sc[i]) if ext == 'max' else (lambda i: -sc[i])
    best = max(key(i) for i in idx)
    hits = [i for i in idx if key(i) == best]
    return us[hits[0]] if len(hits) == 1 else None

def _sname(s):
    return s[0] if len(s) == 1 else s[0] + '[' + ','.join('S' if isinstance(a, tuple) else str(a) for a in s[1:]) + ']'

# ------------------------------------------------------------------ family
def _programs(train, bgm):
    bgf = BGS[bgm]
    o0 = train[0]['output']
    bgs = [bgf(p['input']) for p in train]
    cols = sorted(set.intersection(*[{v for r in p['input'] for v in r} - {b} for p, b in zip(train, bgs)]))
    parts = ['bbox', 'inner', 'content'] + ['nomark%d' % c for c in cols]
    # score library (colour / shape / distance parameters drawn from the training pairs)
    lib = [('area',), ('barea',), ('ncol',), ('minority',)]
    for c in cols:
        lib += [('cnt', c), ('ncomp', c), ('has', c)] + [('near', c, k) for k in (1, 2, 3)]
        # templates: multi-cell colour-c shapes present as components in every training output
        shp = None
        for p in train:
            o = p['output']; ob = bg_of(o)
            here = {_shape(q) for q in objects(o, ob, False, True) if o[q[0][0]][q[0][1]] == c and len(q) > 1}
            shp = here if shp is None else shp & here
        if shp and len(shp) <= 3: lib += [('nshape', c, S) for S in sorted(shp)]
    for uk in UNITS:
        per = []
        for p, bg in zip(train, bgs):
            g = p['input']; us = units(g, uk, bg)
            if len(us) < 2 or len(us) > 60: per = None; break
            per.append((g, us, bg, p['output']))
        if not per: continue
        for pt in parts:
            if pt == 'content' and uk != 'k1': continue
            match = [{i for i, u in enumerate(us) if part(g, u, pt, bg) == o} for g, us, bg, o in per]
            single_ok = all(match)
            for s in lib:
                exts = ('max', 'min') + (('all',) if s[0] == 'has' else ())
                for ext in exts:
                    if ext != 'all' and not single_ok: continue
                    ok = True
                    for (g, us, bg, o), m in zip(per, match):
                        ch = choose(g, us, s, ext, bg, pt)
                        if ch is None: ok = False; break
                        if ext == 'all':
                            if part(g, ch, pt, bg) != o: ok = False; break
                        elif not any(ch is us[i] for i in m): ok = False; break
                    if not ok: continue
                    def fn(g, uk=uk, pt=pt, s=s, ext=ext, bgf=bgf):
                        bg = bgf(g); us = units(g, uk, bg)
                        if len(us) < 2: return None
                        ch = choose(g, us, s, ext, bg, pt)
                        return part(g, ch, pt, bg) if ch else None
                    yield (f"crop-by-score[{uk},{_sname(s)},{ext},{pt}{',bg=mode' if bgm == 'mode' else ''}]", 4, fn)

def fam_crop_by_score(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if H(o0) > H(i0) or W(o0) > W(i0) or (H(o0), W(o0)) == (H(i0), W(i0)): return
    for p in train:
        if H(p['output']) > H(p['input']) or W(p['output']) > W(p['input']): return
    bgmodes = ['border'] + (['mode'] if any(border_bg(p['input']) != bg_of(p['input']) for p in train) else [])
    n = 0
    for bgm in bgmodes:
        for prog in _programs(train, bgm):
            yield prog; n += 1
            if n >= 12: return

FAMILIES = (fam_crop_by_score,)
