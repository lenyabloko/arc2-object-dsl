"""Geometry roles on_ray / extends and between (Fable v5 D17, v6 D19), as parameterised generators, and a coverage
check: can the changed cells of every training pair be written as a union of generated cells with one global
parameter setting (per-object choice of direction / partner left free)?  This is the role-level analogue of the
seed test (Route A's C_t != top): an upper bound on what the lattice can learn once the role is available.

Parameters come from declared finite domains (G30 b), never from a task:
  on_ray(x, o, d, origin, stop, stride, colour)
      d       8 compass directions
      origin  'all' (every cell of o) | 'lead' (cells of o with no own cell next in direction d)
      stop    'obstacle' (stop before the first non-background cell) | 'border' (continue past, never overwrite)
      stride  1 | 2 (every other cell: a dashed ray)
      colour  'own' (o's colour) | 'const' (one colour for the task)
  between(x, o1, o2, span, fill, colour)
      o1, o2  two objects that face each other along a row, a column or a diagonal with only background between
      span    'overlap' (the corridor as wide as their overlap) | 'line' (one line through the facing cells)
      fill    'all' | 'mid' (the middle cell(s) only) | 'halves' (each half takes the nearer object's colour)
      colour  'o1' | 'o2' | 'const' ('halves' fixes it)
Test outputs are never read.  usage: python3 geo_roles.py <task ids json> [--design-only]"""
import json, sys
from collections import Counter, deque

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
N8 = ((0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1))
DIRS = N8


def bg_of(g):
    c = Counter(v for r in g for v in r)
    return 0 if 0 in c else c.most_common(1)[0][0]


def objects(g, bg):
    h, w = len(g), len(g[0]); seen = set(); out = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or (y, x) in seen: continue
            c = g[y][x]; q = deque([(y, x)]); seen.add((y, x)); cs = []
            while q:
                a, b = q.popleft(); cs.append((a, b))
                for dy, dx in N8:
                    p = (a + dy, b + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and p not in seen and g[p[0]][p[1]] == c:
                        seen.add(p); q.append(p)
            out.append((c, frozenset(cs)))
    return out


def ray_cells(g, bg, cells, d, origin, stop, stride):
    h, w = len(g), len(g[0]); dy, dx = d; S = set()
    starts = [p for p in cells if origin == 'all' or (p[0] + dy, p[1] + dx) not in cells]
    for (y, x) in starts:
        a, b = y + dy, x + dx; k = 1
        while 0 <= a < h and 0 <= b < w:
            if g[a][b] != bg:
                if stop == 'obstacle': break
            elif (k - 1) % stride == 0:
                S.add((a, b))
            a += dy; b += dx; k += 1
    return S - set(cells)


def turned(d, turn):
    dy, dx = d
    return (dx, -dy) if turn == 'cw' else (-dx, dy)


def ray_options(g, bg):
    """per object: list of (param key, direction, cells, own colour). key = (origin, stop, stride, turn): with a turn,
    the ray bends 90 degrees at the grid border and the second leg stops before input obstacles or first legs."""
    objs = objects(g, bg); out = []; h, w = len(g), len(g[0])
    first = {}
    for oi, (c, cells) in enumerate(objs):
        for d in DIRS[:4]:
            first[(oi, d)] = ray_cells(g, bg, cells, d, 'lead', 'obstacle', 1)
    all_first = set().union(*first.values()) if first else set()
    for oi, (c, cells) in enumerate(objs):
        opts = []
        for d in DIRS:
            for origin in ('all', 'lead'):
                for stop in ('obstacle', 'border'):
                    for stride in (1, 2):
                        S = ray_cells(g, bg, cells, d, origin, stop, stride)
                        if S: opts.append(((origin, stop, stride, 'none'), d, S, c))
        for d in DIRS[:4]:
            leg = first[(oi, d)]
            if not leg: continue
            end = max(leg, key=lambda p: p[0] * d[0] + p[1] * d[1])
            if 0 <= end[0] + d[0] < h and 0 <= end[1] + d[1] < w: continue     # did not reach the border
            for turn in ('cw', 'ccw'):
                e = turned(d, turn); S = set(leg); a, b = end[0] + e[0], end[1] + e[1]
                while 0 <= a < h and 0 <= b < w and g[a][b] == bg and (a, b) not in (all_first - leg):
                    S.add((a, b)); a += e[0]; b += e[1]
                opts.append((('lead', 'obstacle', 1, turn), d, S, c))
        out.append(opts)
    return out


def facing_pairs(g, bg):
    objs = objects(g, bg); out = []
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            (c1, A), (c2, Bc) = objs[i], objs[j]
            for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                # cells of A whose ray in (dy, dx) reaches B through background only
                line = set(); hit = []
                for (y, x) in A:
                    a, b = y + dy, x + dx; walk = []
                    while 0 <= a < len(g) and 0 <= b < len(g[0]) and g[a][b] == bg:
                        walk.append((a, b)); a += dy; b += dx
                    if walk and (a, b) in Bc: hit.append(walk)
                    elif not walk and (a, b) in Bc: pass
                if hit: out.append(((c1, A), (c2, Bc), (dy, dx), hit))
                # and the other way round (B -> A)
                hit2 = []
                for (y, x) in Bc:
                    a, b = y + dy, x + dx; walk = []
                    while 0 <= a < len(g) and 0 <= b < len(g[0]) and g[a][b] == bg:
                        walk.append((a, b)); a += dy; b += dx
                    if walk and (a, b) in A: hit2.append(walk)
                if hit2: out.append(((c2, Bc), (c1, A), (dy, dx), hit2))
    return out


def between_options(g, bg):
    """list of (param key, cells->colour map) for every facing pair."""
    out = []
    for (c1, A), (c2, Bc), d, walks in facing_pairs(g, bg):
        for span in ('overlap', 'line', 'inset'):
            if span == 'inset' and len(walks) < 3: continue
            ws = walks if span == 'overlap' else ([walks[len(walks) // 2]] if span == 'line' else sorted(walks)[1:-1])
            for fill in ('all', 'mid', 'halves', 'mid_cross'):
                cols = ('halves',) if fill == 'halves' else ('o1', 'o2', 'const')
                for col in cols:
                    m = {}
                    for walk in ws:
                        n = len(walk)
                        for t, p in enumerate(walk):
                            if fill in ('mid', 'mid_cross') and t not in ((n - 1) // 2, n // 2): continue
                            if fill == 'mid_cross':
                                for qy, qx in ((0, 0), (0, 1), (1, 0), (0, -1), (-1, 0)):
                                    q = (p[0] + qy, p[1] + qx)
                                    if 0 <= q[0] < len(g) and 0 <= q[1] < len(g[0]) and g[q[0]][q[1]] == bg:
                                        m[q] = c1 if col == 'o1' else (c2 if col == 'o2' else 'C')
                                continue
                            if fill == 'halves':
                                m[p] = c1 if t < n / 2 - 0.25 else (c2 if t > (n - 1) / 2 + 0.25 else None)
                            else:
                                m[p] = c1 if col == 'o1' else (c2 if col == 'o2' else 'C')
                    m = {p: v for p, v in m.items() if v is not None}
                    if m: out.append(((span, fill, col), m))
    return out


def covered_ray(pairs):
    """exists global (origin, stop, stride) and colour mode with Delta = union of consistent rays in every pair."""
    keys = [(o, st, sr, 'none') for o in ('all', 'lead') for st in ('obstacle', 'border') for sr in (1, 2)] + \
           [('lead', 'obstacle', 1, 'cw'), ('lead', 'obstacle', 1, 'ccw')]
    for origin, stop, stride, turn in keys:
                for cmode in ('own', 'const'):
                    consts = None; ok = True
                    for a, b, D in pairs:
                        bg = bg_of(a); cover = set()
                        for opts in ray_options(a, bg):
                            for key, d, S, c in opts:
                                if key != (origin, stop, stride, turn): continue
                                vals = {b[y][x] for y, x in S}
                                if len(vals) != 1: continue
                                v = next(iter(vals))
                                if cmode == 'own' and v != c: continue
                                if cmode == 'const':
                                    if consts is not None and v != consts: continue
                                if not S <= D: continue
                                cover |= S
                                if cmode == 'const': consts = v
                        if cover != D: ok = False; break
                    if ok: return (origin, stop, stride, turn, cmode)
    return None


def ray_paint(g, bg, cells, own, d, mode, stride=1):
    """cells -> colour for one ray family from o in direction d under an optics colour mode:
    'hit'    stop before the first obstacle and take its colour (the ray shows what it points at)
    'filter' pass through objects; after passing through an object of colour c continue with colour c
    'alt'    alternate own colour and background-marker 'C' (a dashed two-colour ray; C resolved per task)
    'bounce' diagonal ray reflecting at the border until it re-enters its own cells or 60 steps"""
    h, w = len(g), len(g[0]); dy, dx = d; m = {}
    starts = [p for p in cells if (p[0] + dy, p[1] + dx) not in cells]
    for (y, x) in starts:
        a, b = y + dy, x + dx; col = own; k = 0; walk = []
        if mode == 'bounce':
            ddy, ddx = dy, dx; steps = 0
            while steps < 60:
                if not (0 <= a < h): ddy = -ddy; a += 2 * ddy
                if not (0 <= b < w): ddx = -ddx; b += 2 * ddx
                if not (0 <= a < h and 0 <= b < w) or (a, b) in cells or g[a][b] != bg: break
                m[(a, b)] = own; a += ddy; b += ddx; steps += 1
            continue
        while 0 <= a < h and 0 <= b < w:
            v = g[a][b]
            if v != bg:
                if mode == 'hit':
                    for p in walk: m[p] = v
                    walk = None; break
                if mode == 'filter': col = v
                if mode not in ('filter',): break
            else:
                if mode == 'alt': m[(a, b)] = own if k % 2 == 0 else 'C'
                elif mode == 'filter': m[(a, b)] = col
                elif mode == 'hit': walk.append((a, b))
                k += 1
            a += dy; b += dx
    return {p: v for p, v in m.items() if p not in cells}


def covered_ray_optics(pairs):
    for mode in ('hit', 'filter', 'alt', 'bounce'):
        const = None; ok = True
        dirs = DIRS if mode != 'bounce' else DIRS[4:]
        for a, b, D in pairs:
            bg = bg_of(a); cover = set()
            for c, cells in objects(a, bg):
                for d in dirs:
                    m = ray_paint(a, bg, cells, c, d, mode)
                    if not m or not set(m) <= D: continue
                    good = True; cc = const
                    for (y, x), v in m.items():
                        want = b[y][x]
                        if v == 'C':
                            if cc is None: cc = want
                            if want != cc: good = False; break
                        elif want != v: good = False; break
                    if good: cover |= set(m); const = cc
            if cover != D: ok = False; break
        if ok: return ('optics', mode)
    return None


def covered_between(pairs):
    keys = {k for a, b, D in pairs for k, _ in between_options(a, bg_of(a))}
    for key in sorted(keys):
        const = None; ok = True
        for a, b, D in pairs:
            cover = set()
            for k, m in between_options(a, bg_of(a)):
                if k != key: continue
                good = True; cc = const
                for (y, x), v in m.items():
                    want = b[y][x]
                    if v == 'C':
                        if cc is None: cc = want
                        if want != cc: good = False; break
                    elif want != v: good = False; break
                if good and set(m) <= D:
                    cover |= set(m); const = cc
            if cover != D: ok = False; break
        if ok: return key
    return None


def main():
    ids = json.load(open(sys.argv[1]))
    ids = ids['tasks'] if isinstance(ids, dict) and 'tasks' in ids else ids
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    res = {}
    for k in ids:
        t = tr.get(k) or ev[k]; pairs = []
        for p in t['train']:
            a, b = p['input'], p['output']
            if (len(a), len(a[0])) != (len(b), len(b[0])): pairs = None; break
            D = {(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]}
            pairs.append((a, b, D))
        if not pairs: res[k] = {'ray': None, 'between': None, 'note': 'shape change'}; continue
        r = covered_ray(pairs) or covered_ray_optics(pairs); bt = covered_between(pairs)
        res[k] = {'ray': r, 'between': bt}
    json.dump(res, open('geo_roles_cover.json', 'w'), indent=0)
    print(json.dumps({'n': len(ids), 'ray_covered': sum(1 for v in res.values() if v['ray']),
                      'between_covered': sum(1 for v in res.values() if v['between']),
                      'either': sum(1 for v in res.values() if v['ray'] or v['between'])}))


if __name__ == '__main__':
    main()
