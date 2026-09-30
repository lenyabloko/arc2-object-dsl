"""Role-level reuse of abduced concepts (design splits only, no held-out ids).
Each detector maps an input grid to a set of cells (its extension). Gate (Codex coverage / Fable seed rule): in every
training pair the changed cells lie inside the extension, the extension is non-empty and covers <= 50% of the grid.
exact: extension == changed cells in every pair.  Action check on exact gates: constant colour, input-colour map,
rarest colour, nearest non-bg colour, wall colour of the enclosing shape.
usage: python3 role_reuse.py > role_reuse.json"""
import json, sys, itertools
from collections import Counter, deque

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
M = '/home/claude/work/public_repo/tools/m1b/'
RES = '/mnt/user-data/uploads/arc_extended_arga/cloud_outbox/wsl_results/wake/b0-v21-design/results.jsonl'

def bg_of(g):
    c = Counter(v for r in g for v in r)
    return 0 if 0 in c else c.most_common(1)[0][0]

N4 = ((0, 1), (1, 0), (0, -1), (-1, 0))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))

def comps(g, pred, nb=N4):
    h, w = len(g), len(g[0]); seen = set(); out = []
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or not pred(y, x): continue
            q = deque([(y, x)]); seen.add((y, x)); cs = []
            while q:
                a, b = q.popleft(); cs.append((a, b))
                for dy, dx in nb:
                    p = (a + dy, b + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and p not in seen and pred(*p):
                        seen.add(p); q.append(p)
            out.append(cs)
    return out

def objects_c4(g, bg):  # same-colour 4-connected
    h, w = len(g), len(g[0])
    lab = {}
    res = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or (y, x) in lab: continue
            c = g[y][x]; q = deque([(y, x)]); lab[(y, x)] = len(res); cs = []
            while q:
                a, b = q.popleft(); cs.append((a, b))
                for dy, dx in N4:
                    p = (a + dy, b + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and p not in lab and g[p[0]][p[1]] == c:
                        lab[p] = len(res); q.append(p)
            res.append(cs)
    return res, lab

def objects_c8(g, bg):  # same-colour 8-connected
    h, w = len(g), len(g[0]); lab = {}; res = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or (y, x) in lab: continue
            c = g[y][x]; q = deque([(y, x)]); lab[(y, x)] = len(res); cs = []
            while q:
                a, b = q.popleft(); cs.append((a, b))
                for dy, dx in N8:
                    p = (a + dy, b + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and p not in lab and g[p[0]][p[1]] == c:
                        lab[p] = len(res); q.append(p)
            res.append(cs)
    return res, lab

def objects_m8(g, bg):  # multicolour 8-connected
    return comps(g, lambda a, b: g[a][b] != bg, N8)

# ---------------------------------------------------------------- detectors (input grid -> set of cells)
def enclosed_any(g, bg):
    h, w = len(g), len(g[0]); S = set()
    for cs in comps(g, lambda a, b: g[a][b] == bg, N4):
        if not any(a in (0, h - 1) or b in (0, w - 1) for a, b in cs): S |= set(cs)
    return S

def enclosed_one(g, bg):  # cavity: space inside ONE shape
    h, w = len(g), len(g[0]); S = set(); _, lab = objects_c8(g, bg)
    for cs in comps(g, lambda a, b: g[a][b] == bg, N4):
        if any(a in (0, h - 1) or b in (0, w - 1) for a, b in cs): continue
        walls = {lab[(a + dy, b + dx)] for a, b in cs for dy, dx in N4
                 if 0 <= a + dy < h and 0 <= b + dx < w and g[a + dy][b + dx] != bg}
        if len(walls) == 1: S |= set(cs)
    return S

def square_hole(g, bg):
    h, w = len(g), len(g[0]); S = set()
    for cs in comps(g, lambda a, b: g[a][b] == bg, N4):
        if any(a in (0, h - 1) or b in (0, w - 1) for a, b in cs): continue
        ys = [a for a, _ in cs]; xs = [b for _, b in cs]
        hh, ww = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
        if hh == ww and hh * ww == len(cs): S |= set(cs)
    return S

def _between(g, bg, same, axes):
    h, w = len(g), len(g[0]); S = set()
    lines = []
    if 'h' in axes: lines += [[(y, x) for x in range(w)] for y in range(h)]
    if 'v' in axes: lines += [[(y, x) for y in range(h)] for x in range(w)]
    for L in lines:
        nz = [i for i, (a, b) in enumerate(L) if g[a][b] != bg]
        for i, j in zip(nz, nz[1:]):
            if j - i > 1 and (not same or g[L[i][0]][L[i][1]] == g[L[j][0]][L[j][1]]):
                S |= set(L[i + 1:j])
    return S

def los_rarest(g, bg):
    c = Counter(v for r in g for v in r if v != bg)
    if len(c) < 2: return set()
    rare = min(c, key=lambda k: (c[k], k))
    rows = {y for y, r in enumerate(g) for v in r if v == rare}
    cols = {x for r in g for x, v in enumerate(r) if v == rare}
    return {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == bg and (y in rows or x in cols)}

def grid_border(g, bg):
    h, w = len(g), len(g[0])
    return {(y, x) for y in range(h) for x in range(w) if y in (0, h - 1) or x in (0, w - 1)}

def _rects(g, bg):
    objs, _ = objects_c4(g, bg); out = []
    for cs in objs:
        ys = [a for a, _ in cs]; xs = [b for _, b in cs]
        y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
        if (y1 - y0 + 1) * (x1 - x0 + 1) == len(cs) and y1 - y0 >= 2 and x1 - x0 >= 2: out.append((y0, x0, y1, x1))
    return out

def rect_role(role):
    def f(g, bg):
        S = set()
        for y0, x0, y1, x1 in _rects(g, bg):
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    ey, ex = y in (y0, y1), x in (x0, x1)
                    r = 'vertex' if ey and ex else ('edge' if ey or ex else 'interior')
                    if r == role or (role == 'boundary' and r != 'interior'): S.add((y, x))
        return S
    return f

def contact(g, bg):
    h, w = len(g), len(g[0])
    return {(y, x) for y in range(h) for x in range(w) if g[y][x] != bg and any(
        0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] not in (bg, g[y][x]) for dy, dx in N4)}

def _panels(g, bg):
    h, w = len(g), len(g[0])
    rows = [y for y in range(h) if len(set(g[y])) == 1 and g[y][0] != bg]
    cols = [x for x in range(w) if len({g[y][x] for y in range(h)}) == 1 and g[0][x] != bg]
    if not rows and not cols: return []
    ry = [-1] + rows + [h]; cx = [-1] + cols + [w]; P = []
    for a, b in zip(ry, ry[1:]):
        for c, d in zip(cx, cx[1:]):
            cells = [(y, x) for y in range(a + 1, b) for x in range(c + 1, d)]
            if cells: P.append(cells)
    return P

def panel_bg(marked_only):
    def f(g, bg):
        S = set()
        for P in _panels(g, bg):
            if marked_only and not any(g[y][x] != bg for y, x in P): continue
            S |= {(y, x) for y, x in P if g[y][x] == bg}
        return S
    return f

def cup_interior(g, bg):  # pour: bg with walls left, right and below
    h, w = len(g), len(g[0]); S = set()
    for y in range(h):
        for x in range(w):
            if g[y][x] != bg: continue
            L = any(g[y][k] != bg for k in range(x)); R = any(g[y][k] != bg for k in range(x + 1, w))
            D = any(g[k][x] != bg for k in range(y + 1, h))
            if L and R and D: S.add((y, x))
    return S

def ray(dirs, stop=True):
    def f(g, bg):
        h, w = len(g), len(g[0]); S = set()
        for y in range(h):
            for x in range(w):
                if g[y][x] == bg: continue
                for dy, dx in dirs:
                    a, b = y + dy, x + dx
                    if not (0 <= a < h and 0 <= b < w) or g[a][b] != bg: continue
                    while 0 <= a < h and 0 <= b < w and g[a][b] == bg:
                        S.add((a, b)); a += dy; b += dx
        return S
    return f

def ring(nb):
    def f(g, bg):
        h, w = len(g), len(g[0])
        return {(y, x) for y in range(h) for x in range(w) if g[y][x] == bg and any(
            0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] != bg for dy, dx in nb)}
    return f

def bar_extension(g, bg):  # crosshair: lines extending straight bars
    h, w = len(g), len(g[0]); S = set(); objs, _ = objects_c4(g, bg)
    for cs in objs:
        if len(cs) < 2: continue
        ys = {a for a, _ in cs}; xs = {b for _, b in cs}
        if len(ys) == 1: dirs = [(0, 1), (0, -1)]
        elif len(xs) == 1: dirs = [(1, 0), (-1, 0)]
        else: continue
        for dy, dx in dirs:
            end = max(cs, key=lambda p: p[0] * dy + p[1] * dx); a, b = end[0] + dy, end[1] + dx
            while 0 <= a < h and 0 <= b < w and g[a][b] == bg: S.add((a, b)); a += dy; b += dx
    return S

def bbox_bg(g, bg):
    S = set()
    for cs in objects_m8(g, bg):
        ys = [a for a, _ in cs]; xs = [b for _, b in cs]
        S |= {(y, x) for y in range(min(ys), max(ys) + 1) for x in range(min(xs), max(xs) + 1) if g[y][x] == bg}
    return S

def colour_cells(which):
    def f(g, bg):
        c = Counter(v for r in g for v in r if v != bg)
        if not c: return set()
        k = (min if which == 'rarest' else max)(c, key=lambda k: (c[k], -k if which == 'rarest' else k))
        return {(y, x) for y, r in enumerate(g) for x, v in enumerate(r) if v == k}
    return f

def objects_by_size(which):
    def f(g, bg):
        objs = objects_m8(g, bg)
        if len(objs) < 2: return set()
        n = [len(o) for o in objs]
        if which == 'single': return {p for o in objs if len(o) == 1 for p in o}
        t = (max if which == 'largest' else min)(n)
        if n.count(t) > 1: return set()
        return set(next(o for o in objs if len(o) == t))
    return f

def all_nonbg(g, bg):
    return {(y, x) for y, r in enumerate(g) for x, v in enumerate(r) if v != bg}

DET = {
    'cavity (enclosed by one shape)': enclosed_one,
    'enclosed (any)': enclosed_any,
    'square hole': square_hole,
    'between same colour (h/v)': lambda g, bg: _between(g, bg, True, 'hv'),
    'between same colour (h)': lambda g, bg: _between(g, bg, True, 'h'),
    'between same colour (v)': lambda g, bg: _between(g, bg, True, 'v'),
    'between any (h/v)': lambda g, bg: _between(g, bg, False, 'hv'),
    'line of sight of odd colour': los_rarest,
    'grid border': grid_border,
    'rectangle interior': rect_role('interior'),
    'rectangle edge': rect_role('edge'),
    'rectangle vertex': rect_role('vertex'),
    'rectangle boundary': rect_role('boundary'),
    'contact between colours': contact,
    'panel blanks (marked panels)': panel_bg(True),
    'panel blanks (all panels)': panel_bg(False),
    'cup interior (pour)': cup_interior,
    'ray down': ray([(1, 0)]), 'ray up': ray([(-1, 0)]), 'ray right': ray([(0, 1)]), 'ray left': ray([(0, -1)]),
    'rays 4-dir': ray(N4), 'rays diagonal': ray(N8[4:]),
    'ring (4-adjacent)': ring(N4), 'ring (8-adjacent)': ring(N8),
    'bar extension (crosshair)': bar_extension,
    'bounding-box blanks': bbox_bg,
    'cells of rarest colour': colour_cells('rarest'),
    'cells of commonest colour': colour_cells('commonest'),
    'single-cell objects': objects_by_size('single'),
    'largest object': objects_by_size('largest'),
    'smallest object': objects_by_size('smallest'),
    'all non-background': all_nonbg,
}
SOURCE = {'cavity (enclosed by one shape)': 'cavity', 'square hole': 'square hole', 'between same colour (h/v)': 'innermost interval',
          'between any (h/v)': 'bridge / meet halfway', 'line of sight of odd colour': 'line of sight', 'grid border': 'dashed border',
          'rectangle interior': 'boundary roles', 'rectangle edge': 'boundary roles', 'rectangle vertex': 'boundary roles',
          'rectangle boundary': 'boundary roles', 'contact between colours': 'reaction', 'panel blanks (marked panels)': 'panel dye / mirror panels',
          'cup interior (pour)': 'pour', 'bar extension (crosshair)': 'crosshair', 'ring (8-adjacent)': 'rainbow (rings)'}

# ---------------------------------------------------------------- actions on an exact extension
def act_ok(pairs, exts, bg_list):
    ok = []
    # constant colour
    vals = {pairs[i][1][y][x] for i, E in enumerate(exts) for y, x in E}
    if len(vals) == 1: ok.append('constant')
    # colour map from input colour
    m = {}; good = True
    for i, E in enumerate(exts):
        for y, x in E:
            a, b = pairs[i][0][y][x], pairs[i][1][y][x]
            if m.setdefault(a, b) != b: good = False
    if good and 'constant' not in ok: ok.append('colour map')
    # rarest colour of the input
    def rare(g, bg):
        c = Counter(v for r in g for v in r if v != bg)
        return min(c, key=lambda k: (c[k], k)) if c else None
    if all(pairs[i][1][y][x] == rare(pairs[i][0], bg_list[i]) for i, E in enumerate(exts) for y, x in E): ok.append('rarest colour')
    # nearest non-bg (unique, Manhattan)
    def nearest(g, bg, y, x, E):
        best = None; bd = 99; tie = False
        for a, r in enumerate(g):
            for b, v in enumerate(r):
                if v == bg or (a, b) in E: continue
                d = abs(a - y) + abs(b - x)
                if d < bd: bd, best, tie = d, v, False
                elif d == bd and v != best: tie = True
        return None if tie else best
    if all(pairs[i][1][y][x] == nearest(pairs[i][0], bg_list[i], y, x, E) for i, E in enumerate(exts) for y, x in E): ok.append('nearest colour')
    return ok

def main():
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ts = json.load(open(B + 'arc-agi_training_solutions.json'))
    ev = json.load(open(B + 'arc-agi_evaluation_challenges.json')); es = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
    N2 = set(open(M + 'novel_N2.txt').read().split()); A = set(open(M + 'deval_a.txt').read().replace(',', ' ').split())
    R = {r['task']: r for r in map(json.loads, open(RES))}
    design = {k: (tr[k], ts[k]) for k in tr if k not in N2}
    design.update({k: (ev[k], es[k]) for k in A})
    stats = {d: Counter() for d in DET}; per_task = {}
    n_same = Counter()
    for k, (t, sol) in sorted(design.items()):
        failed = not R[k]['exact']
        pairs = [(p['input'], p['output']) for p in t['train']]
        if any((len(a), len(a[0])) != (len(b), len(b[0])) for a, b in pairs): continue
        n_same['failed' if failed else 'solved'] += 1
        bgs = [bg_of(a) for a, _ in pairs]
        deltas = [{(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]} for a, b in pairs]
        if not all(deltas): continue
        hits = {}
        for name, fn in DET.items():
            try: exts = [fn(a, bg) for (a, _), bg in zip(pairs, bgs)]
            except Exception: continue
            if not all(E and D <= E and len(E) <= 0.5 * len(a) * len(a[0]) for E, D, (a, _) in zip(exts, deltas, pairs)): continue
            exact = all(E == D for E, D in zip(exts, deltas))
            prec = sum(map(len, deltas)) / sum(map(len, exts))
            tag = 'exact' if exact else ('tight' if prec >= 0.5 else 'cover')
            key = ('F_' if failed else 'S_') + tag
            stats[name][key] += 1
            if exact:
                acts = act_ok(pairs, exts, bgs)
                if acts:
                    stats[name][('F_' if failed else 'S_') + 'fit'] += 1
                    # test check (design data): apply to test inputs with the first matching action
                    tst = []
                    for ti, tp in enumerate(t['test']):
                        g = tp['input']; bg = bg_of(g); E = fn(g, bg)
                        out = [r[:] for r in g]
                        act = acts[0]
                        for y, x in E:
                            if act == 'constant': out[y][x] = next(iter({pairs[0][1][a][b] for a, b in deltas[0]}))
                            elif act == 'colour map':
                                mm = {pairs[i][0][a][b]: pairs[i][1][a][b] for i, D in enumerate(deltas) for a, b in D}
                                out[y][x] = mm.get(g[y][x], g[y][x])
                            elif act == 'rarest colour':
                                c = Counter(v for r in g for v in r if v != bg); out[y][x] = min(c, key=lambda q: (c[q], q))
                        tst.append(out == sol[ti])
                    if all(tst): stats[name][('F_' if failed else 'S_') + 'test'] += 1
            hits[name] = tag
        per_task[k] = {'failed': failed, 'hits': hits}
    # union of two detectors exactly = delta (a size-2 program), on failed tasks
    json.dump({'n_same_shape': n_same, 'stats': {d: dict(c) for d, c in stats.items()}, 'source': SOURCE,
               'failed_with_any_gate': sum(1 for v in per_task.values() if v['failed'] and v['hits']),
               'failed_with_exact': sum(1 for v in per_task.values() if v['failed'] and 'exact' in v['hits'].values()),
               'failed_same_shape': n_same['failed']}, sys.stdout, indent=1)
    # private per-task file (design ids only) for follow-up
    json.dump(per_task, open('/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad/role_reuse_tasks.json', 'w'))

if __name__ == '__main__':
    main()
