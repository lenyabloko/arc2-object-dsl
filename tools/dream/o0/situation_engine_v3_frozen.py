"""Situation engine (Fable v19, Oct 2 2026): a situation is S = <HOW; arg_1..arg_k; WHY>.

  HOW    a column: tile, stamp, extend, mirror, recolour, fill, move, extract (closed set, C.1/B.1)
  arg_i  a ROW (a picked-out property of the input: its definition is fixed here, its value is computed on whichever
         grid the situation is applied to) or 'train' (a constant bound from the training pairs)
  WHY    the column's invariant, checked on every result; a result that breaks it is not a prediction (C.3)

C.2 column induction by fit: for each column and each admissible row assignment, bind the constants on the training
pairs and keep the assignment only if the column reproduces every training output from the rows evaluated on the
input. fit(train) returns every fitted situation; apply(S, grid) evaluates the rows on grid, applies the column with
the bound constants and checks WHY (C.3). Rows are deterministic, task-free detectors (G83): no task ids, no
per-task parameters. Training pairs only: nothing here reads a test output.

Engine v2 (Fable v20 B.2, Oct 2 18:40 EDT): rows and constants Len ticked from the vocabulary of the 38 T83 lines,
each implemented from his words only (G83):
  segments   "line segments: straight runs of cells, the thing that is extended or acted on"
  region     "a region: an enclosed area, treated as one thing"
  panels     "panels are wide stripes stretched across / along the entire grid"
  between    "the cells lying between two objects"
  corners / centre   "the corners or centre of the grid, an object or a frame"
  across     "across a separator: the matching place in the other panel"
  target     "toward a target: the target is the object that is changed, or only present in the output" (on a new
             input the target is recognised by what training shows about it: the colour of the objects that change)
  repeat     "until the output is complete, nothing more needed": the step is applied until nothing changes
  other colour   "another object's colour": a line takes the colour of the object it meets; a recoloured object
             takes the colour of its nearest other object; cells between two objects take their colour
Engine v3 (Oct 2 22:47 EDT, Len's correction of his markers x stamp cell, entered into the schema; G83):
  "some markers got no stamp because they are used by exemplar to map the mark color to the stamp. Only the marks
   at left top corner of the exemplar indicate place for stamp"
  marks      row: single-cell marks, without the legend's marks (a mark touching a shape gives no stamp unless it sits
             at that shape's top-left corner)
  stamp      new arguments: rest (the rest of the input is kept / cleared) and place (each unit cell belongs to the
             nearest anchor / to the nearest anchor above-left of it: the stamp's top-left corner on the mark)
v1 is kept unchanged as situation_engine_v1_frozen.py (sha f14127b651fe); v2 as situation_engine_v2_frozen.py
(sha 4b4a22370d20).
usage: python3 situation_engine.py fit <task id>...      fitted situations per task (training pairs only)"""
import itertools, json, os, sys
from collections import Counter

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = tuple((a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0))
DIRS = {'N': (-1, 0), 'S': (1, 0), 'W': (0, -1), 'E': (0, 1), 'NW': (-1, -1), 'NE': (-1, 1), 'SW': (1, -1), 'SE': (1, 1)}
MAX_FITS_PER_COLUMN = 3


# ------------------------------------------------------------------ grid helpers
def bgc(g):
    """background: black (0) when the grid has it, else the most common colour"""
    vs = Counter(v for r in g for v in r)
    return 0 if 0 in vs else vs.most_common(1)[0][0]
def dims(g): return len(g), len(g[0])
def copy(g): return [list(r) for r in g]
def inb(g, y, x): return 0 <= y < len(g) and 0 <= x < len(g[0])


def comps(cells, nb=N8):
    cells = set(cells); out = []
    while cells:
        s = min(cells); cells.discard(s); st = [s]; c = {s}
        while st:
            y, x = st.pop()
            for dy, dx in nb:
                n = (y + dy, x + dx)
                if n in cells: cells.discard(n); c.add(n); st.append(n)
        out.append(c)
    return out


def objects(g, b):
    """8-connected single-colour components on the background, in reading order of their first cell."""
    H, W = dims(g); out = []
    for col in sorted({v for r in g for v in r} - {b}):
        for c in comps({(y, x) for y in range(H) for x in range(W) if g[y][x] == col}):
            out.append({'colour': col, 'cells': c})
    return sorted(out, key=lambda o: min(o['cells']))


def multis(g, b):
    """8-connected components of non-background cells, colours ignored."""
    H, W = dims(g)
    return sorted(comps({(y, x) for y in range(H) for x in range(W) if g[y][x] != b}), key=min)


def bbox(cells):
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


def crop(g, box):
    y0, x0, y1, x1 = box
    return [row[x0:x1 + 1] for row in g[y0:y1 + 1]]


def unique_by(objs, key):
    """the one object whose key value is unique and extreme / odd; None unless exactly one qualifies"""
    return objs[0] if len(objs) == 1 else None


# ------------------------------------------------------------------ ROWS: picked-out properties (C.1)
# each row(g, b) -> value; None means "not present in this grid" (then the situation does not apply)
def r_fg(g, b): return {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != b} or None
def r_bg(g, b): return {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == b} or None


def r_markers(g, b):
    """isolated cells: a non-background cell whose 8 neighbours are all background"""
    H, W = dims(g)
    m = {(y, x) for y in range(H) for x in range(W) if g[y][x] != b and
         all(not inb(g, y + dy, x + dx) or g[y + dy][x + dx] == b for dy, dx in N8)}
    return m or None


def r_input(g, b): return g


def r_exemplar(g, b):
    """the largest multi-coloured component (at least 2 colours); None if absent or tied"""
    ms = [c for c in multis(g, b) if len({g[y][x] for y, x in c}) > 1]
    if not ms: return None
    n = max(len(c) for c in ms)
    big = [c for c in ms if len(c) == n]
    return big[0] if len(big) == 1 else None


def _objs_by_size(g, b, pick):
    obs = objects(g, b)
    if len(obs) < 2: return None
    sz = [len(o['cells']) for o in obs]; s = pick(sz)
    return obs[sz.index(s)] if sz.count(s) == 1 else None


def r_largest(g, b): return _objs_by_size(g, b, max)
def r_smallest(g, b): return _objs_by_size(g, b, min)


def r_odd(g, b):
    """the one object whose colour no other object has, or else whose shape no other object has"""
    obs = objects(g, b)
    if len(obs) < 3: return None
    cc = Counter(o['colour'] for o in obs)
    one = [o for o in obs if cc[o['colour']] == 1]
    if len(one) == 1: return one[0]
    sh = lambda o: frozenset((y - min(a for a, _ in o['cells']), x - min(c for _, c in o['cells'])) for y, x in o['cells'])
    sc = Counter(sh(o) for o in obs)
    one = [o for o in obs if sc[sh(o)] == 1]
    return one[0] if len(one) == 1 else None


def r_pixel_count(g, b): return sum(v != b for r in g for v in r) or None
def r_object_count(g, b): return len(objects(g, b)) or None
def r_border(g, b): return dims(g)
def r_obstacle(g, b): return r_fg(g, b)          # the stop set: any non-background cell (the first one met stops)


def r_separators(g, b):
    """full rows / columns of one non-background colour"""
    H, W = dims(g)
    rows = [y for y in range(H) if len(set(g[y])) == 1 and g[y][0] != b]
    cols = [x for x in range(W) if len({g[y][x] for y in range(H)}) == 1 and g[0][x] != b]
    return (rows, cols) if rows or cols else None


def r_frame(g, b):
    """interior box of the one rectangular outline object (a single-colour component equal to its bbox border)"""
    out = []
    for o in objects(g, b):
        y0, x0, y1, x1 = bbox(o['cells'])
        if y1 - y0 < 2 or x1 - x0 < 2: continue
        ring = {(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if y in (y0, y1) or x in (x0, x1)}
        if o['cells'] == ring: out.append((y0 + 1, x0 + 1, y1 - 1, x1 - 1))
    return out[0] if len(out) == 1 else None


def r_key(g, b):
    """colour key: every 2-cell component made of two different colours is a pair a -> b (left/top first)"""
    m = {}
    for c in multis(g, b):
        if len(c) != 2: continue
        p, q = sorted(c)
        a, z = g[p[0]][p[1]], g[q[0]][q[1]]
        if a == z or m.get(a, z) != z: continue
        m[a] = z
    return m or None


def r_axis(g, b):
    """candidate axes: grid centre lines, foreground bbox centre lines, full separator lines (as doubled coordinates)"""
    H, W = dims(g); out = {'grid': (H - 1, W - 1)}
    f = r_fg(g, b)
    if f: y0, x0, y1, x1 = bbox(f); out['bbox'] = (y0 + y1, x0 + x1)
    s = r_separators(g, b)
    if s and len(s[0]) + len(s[1]) == 1: out['line'] = (2 * s[0][0] if s[0] else None, 2 * s[1][0] if s[1] else None)
    return out


def straight_line(cells):
    """1-wide straight run of length >= 2: one row, one column, or one diagonal; returns its unit direction or None"""
    if len(cells) < 2: return None
    ys = {y for y, _ in cells}; xs = {x for _, x in cells}
    if len(ys) == 1 and max(xs) - min(xs) + 1 == len(cells): return (0, 1)
    if len(xs) == 1 and max(ys) - min(ys) + 1 == len(cells): return (1, 0)
    if len({y - x for y, x in cells}) == 1 and max(ys) - min(ys) + 1 == len(cells): return (1, 1)
    if len({y + x for y, x in cells}) == 1 and max(ys) - min(ys) + 1 == len(cells): return (1, -1)
    return None


def r_segments(g, b):
    """line segments: single-colour objects that are straight 1-wide runs (v2, Len)"""
    s = [o for o in objects(g, b) if straight_line(o['cells'])]
    return s or None


def r_region(g, b):
    """a region: the enclosed background areas (4-connected, not reaching the border); the largest as one thing (v2, Len)"""
    cs = comps(enclosed(g, b), N4)
    if not cs: return None
    n = max(len(c) for c in cs); big = [c for c in cs if len(c) == n]
    return big[0] if len(big) == 1 else None


def r_panels(g, b):
    """panels: wide stripes across / along the entire grid, cut by full separator lines or full background lines;
    returns (orientation, [(y0, x0, y1, x1), ...]) with at least 2 stripes of equal size (v2, Len)"""
    H, W = dims(g)
    for ori in ('h', 'v'):
        n = H if ori == 'h' else W
        line = (lambda i: [g[i][x] for x in range(W)]) if ori == 'h' else (lambda i: [g[y][i] for y in range(H)])
        cut = [i for i in range(n) if len(set(line(i))) == 1]
        runs = []; cur = []
        for i in range(n):
            if i in cut:
                if cur: runs.append(cur); cur = []
            else: cur.append(i)
        if cur: runs.append(cur)
        if len(runs) >= 2 and len({len(r) for r in runs}) == 1 and cut:
            boxes = [(r[0], 0, r[-1], W - 1) if ori == 'h' else (0, r[0], H - 1, r[-1]) for r in runs]
            return ori, boxes
    return None


def r_between(g, b):
    """the background cells lying between two objects on one row or one column, with only background between (v2, Len)"""
    H, W = dims(g); oid = {}
    for i, o in enumerate(objects(g, b)):
        for c in o['cells']: oid[c] = i
    out = set()
    for y in range(H):
        ink = [x for x in range(W) if g[y][x] != b]
        for a, z in zip(ink, ink[1:]):
            if z - a > 1 and oid[(y, a)] != oid[(y, z)]: out |= {(y, x) for x in range(a + 1, z)}
    for x in range(W):
        ink = [y for y in range(H) if g[y][x] != b]
        for a, z in zip(ink, ink[1:]):
            if z - a > 1 and oid[(a, x)] != oid[(z, x)]: out |= {(y, x) for y in range(a + 1, z)}
    return out or None


def r_grid_corners(g, b):
    H, W = dims(g); return {(0, 0), (0, W - 1), (H - 1, 0), (H - 1, W - 1)}


def r_obj_corners(g, b):
    """the corner cells of every object's box"""
    out = set()
    for o in objects(g, b):
        y0, x0, y1, x1 = bbox(o['cells']); out |= {(y0, x0), (y0, x1), (y1, x0), (y1, x1)}
    return out or None


def r_centre(g, b):
    """the centre cell of every object whose box has odd height and width, and of the grid when its sides are odd"""
    out = set(); H, W = dims(g)
    for o in objects(g, b):
        y0, x0, y1, x1 = bbox(o['cells'])
        if (y1 - y0) % 2 == 0 and (x1 - x0) % 2 == 0: out.add(((y0 + y1) // 2, (x0 + x1) // 2))
    if H % 2 and W % 2: out.add((H // 2, W // 2))
    return out or None


def r_marks(g, b):
    """v3 (Len 22:47 EDT Oct 2): single-cell marks, without the legend's marks. A one-cell object touching a larger
    object (8-neighbour) is a legend mark and is left out, unless it sits at that object's top-left box corner."""
    obs = objects(g, b); big = [o['cells'] for o in obs if len(o['cells']) > 1]
    out = set()
    for o in obs:
        if len(o['cells']) != 1: continue
        (y, x), = o['cells']; keep = True
        for c in big:
            if any(abs(y - a) <= 1 and abs(x - z) <= 1 for a, z in c):
                if (y, x) != (min(a for a, _ in c), min(z for _, z in c)): keep = False
        if keep: out.add((y, x))
    return out or None


ROWS = {'marks': r_marks, 'fg': r_fg, 'bg': r_bg, 'markers': r_markers, 'input': r_input, 'exemplar': r_exemplar, 'largest': r_largest,
        'smallest': r_smallest, 'odd': r_odd, 'pixel_count': r_pixel_count, 'object_count': r_object_count,
        'border': r_border, 'obstacle': r_obstacle, 'separator': r_separators, 'frame': r_frame, 'key': r_key, 'axis': r_axis,
        'segments': r_segments, 'region': r_region, 'panels': r_panels, 'between': r_between, 'grid_corners': r_grid_corners,
        'obj_corners': r_obj_corners, 'centre': r_centre}
# the review page's row names for these (the grid shows C.1's coarser rows)
PAGE_ROW = {'marks': 'markers', 'fg': 'fg', 'bg': 'bg', 'markers': 'markers', 'input': 'input', 'exemplar': 'exemplar', 'largest': 'odd',
            'smallest': 'odd', 'odd': 'odd', 'pixel_count': 'count', 'object_count': 'count', 'border': 'border',
            'obstacle': 'obstacle', 'objects': 'fg', 'segments': 'segments', 'region': 'region', 'panels': 'panels', 'between': 'between', 'grid_corners': 'corners', 'obj_corners': 'corners', 'centre': 'centre', 'target': 'target', 'across': 'across', 'separator': 'separator', 'frame': 'frame', 'key': 'key', 'axis': 'axis', 'train': 'train'}


def rv(name, g, b): return ROWS[name](g, b)


def cells_of(v):
    """a row value as a set of cells: a cell set as is, an object by its cells, a component as is"""
    if v is None: return None
    if isinstance(v, dict) and 'cells' in v: return set(v['cells'])
    if isinstance(v, (set, frozenset)): return set(v)
    if isinstance(v, list) and v and isinstance(v[0], list): return {(y, x) for y in range(len(v)) for x in range(len(v[0]))}
    if isinstance(v, list) and v and isinstance(v[0], dict): return set().union(*[o['cells'] for o in v])
    return None


def same_dims(train): return all(dims(p['input']) == dims(p['output']) for p in train)


# ------------------------------------------------------------------ COLUMNS (HOW) with their arguments
# each column: args = [(name, admissible values)], bind(train, A) -> candidate constant dicts (derived from the
# training pairs, few), apply(g, A, K) -> output grid or None. apply returns None whenever the column's WHY fails on
# the result (C.3), so a fit on the training pairs also means WHY held on every training pair.

# --- stamp(anchors, unit) WHY: one copy of the unit at every anchor, copies identical (no two copies disagree)
# anchors: markers / fg cells (the cell itself) or objects (each object's bbox top-left, with the object's colour).
# unit 'train': the copy pattern bound on the training pairs (offsets from the anchor; each colour fixed or the anchor's
# own); with byc=1 one pattern per anchor colour (a colour-indexed constant), and an anchor colour never seen in
# training gives no prediction. unit 'exemplar': the input's multi-coloured shape, placed with its cell of the anchor's
# colour on the anchor.
def stamp_anchors(g, b, A, K):
    if A['anchors'] == 'objects':
        a = [(min(y for y, _ in o['cells']), min(x for _, x in o['cells']), o['colour'], frozenset(o['cells'])) for o in objects(g, b)]
    else:
        c = cells_of(rv(A['anchors'], g, b))
        if not c: return None
        a = [(y, x, g[y][x], frozenset([(y, x)])) for y, x in c]
    if K.get('ac') is not None: a = [t for t in a if t[2] == K['ac']]
    return sorted(a) or None


def stamp_bind(train, A):
    if not same_dims(train): return []
    if A['anchors'] == 'across':                                      # v2: the matching place in the other panels
        if A['unit'] != 'train' or A.get('rest', 'kept') != 'kept' or A.get('place', 'nearest') != 'nearest': return []
        pal = set.intersection(*[{v for r in p['output'] for v in r} for p in train])
        return [{'col': c} for c in [None] + sorted(pal)]
    if A.get('place') == 'topleft' and A['anchors'] not in ('markers', 'marks', 'fg', 'objects'): return []   # v3: a corner or
    # centre anchor with the unit's top-left on it pins a fixed pattern to a fixed place (memorising, round 20 §5)
    out = []
    an0 = [stamp_anchors(p['input'], bgc(p['input']), A, {}) or [] for p in train]
    cols = set.intersection(*[{t[2] for t in an} for an in an0])
    for ac in [None] + sorted(cols):
        if A['unit'] == 'exemplar':
            if A.get('rest', 'kept') != 'kept' or A.get('place', 'nearest') != 'nearest': continue
            out += [{'ac': ac, 'mode': m} for m in ('bg', 'all')]; continue
        for byc in ((0, 1) if ac is None else (0,)):
            pat = {}; ok = True; seen = set()
            for p in train:
                g, o = p['input'], p['output']; b = bgc(g)
                an = stamp_anchors(g, b, A, {'ac': ac}) or []
                seen |= {t[2] for t in an}
                if A.get('rest') == 'cleared': delta = [(y, x) for y in range(len(o)) for x in range(len(o[0])) if o[y][x] != b]
                else: delta = [(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != o[y][x]]
                if delta and not an: ok = False; break
                for y, x in delta:
                    if A.get('place') == 'topleft':                     # v3: the unit's top-left corner on the anchor
                        ds = [max(y - ay, x - ax) if ay <= y and ax <= x else 10 ** 6 for ay, ax, _, _ in an]
                        if min(ds) >= 10 ** 6: ok = False; break
                    else: ds = [min(max(abs(y - cy), abs(x - cx)) for cy, cx in cl) for _, _, _, cl in an]
                    m = min(ds)
                    for (ay, ax, ca, _), d in zip(an, ds):
                        if d != m: continue
                        opt = {('k', o[y][x])} | ({('a', 0)} if o[y][x] == ca else set())
                        key = (ca if byc else None, y - ay, x - ax)
                        pat[key] = pat.get(key, opt) & opt
                        if not pat[key]: ok = False; break
                    if not ok: break
                if not ok: break
            if not ok or not pat or all(k[1:] == (0, 0) for k in pat): continue    # a unit is more than the anchor itself
            unit = sorted([k[0], k[1], k[2], 'a' if ('a', 0) in v else 'k', 0 if ('a', 0) in v else next(x for t, x in v if t == 'k')]
                          for k, v in pat.items())
            out += [{'ac': ac, 'byc': byc, 'seen': sorted(seen), 'mode': m, 'unit': unit} for m in (('all',) if A.get('rest') == 'cleared' else ('bg', 'all'))]
    return out


def across_apply(g, K):
    """every panel receives, at the same place inside it, the ink any panel has there (own colours or one colour)"""
    b = bgc(g); P = r_panels(g, b)
    if not P: return None
    boxes = P[1]; ink = {}
    for y0, x0, y1, x1 in boxes:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if g[y][x] != b and ink.setdefault((y - y0, x - x0), g[y][x]) != g[y][x] and K.get('col') is None: return None   # WHY
    out = copy(g)
    for y0, x0, y1, x1 in boxes:
        for (dy, dx), v in ink.items():
            if out[y0 + dy][x0 + dx] == b: out[y0 + dy][x0 + dx] = v if K.get('col') is None else K['col']
    return out


def stamp_apply(g, A, K):
    if A['anchors'] == 'across': return across_apply(g, K)
    b = bgc(g); an = stamp_anchors(g, b, A, K)
    if not an: return None
    if A['unit'] == 'exemplar':
        E = cells_of(rv('exemplar', g, b))
        if not E: return None
        an = [t for t in an if not (t[3] & E)]
        if not an: return None
    out = [[b] * len(g[0]) for _ in g] if A.get('rest') == 'cleared' else copy(g); painted = {}   # v3: rest cleared
    for ay, ax, ca, _ in an:
        if A['unit'] == 'exemplar':
            ref = [e for e in E if g[e[0]][e[1]] == ca]
            if len(ref) != 1: return None                          # WHY: the unit has exactly one cell like the anchor
            ry, rx = ref[0]; unit = [(y - ry, x - rx, g[y][x]) for y, x in E]
        else:
            if K.get('byc') and ca not in K['seen']: return None   # an anchor colour training never showed
            unit = [(dy, dx, ca if t == 'a' else v) for c0, dy, dx, t, v in K['unit'] if not K.get('byc') or c0 == ca]
        for dy, dx, v in unit:
            y, x = ay + dy, ax + dx
            if not inb(g, y, x): continue
            if K['mode'] == 'bg' and g[y][x] != b and (dy, dx) != (0, 0): continue
            if painted.setdefault((y, x), v) != v: return None     # WHY: two copies disagree
            out[y][x] = v
    return out


# --- extend(stop, source, colour) WHY: every line reaches exactly the first stop cell and never crosses it
# stop 'obstacle': the first non-background cell met ends the line (hit_only: only lines that do meet one, optionally
# one of a given colour or of the source's own colour); stop 'border': lines run to the grid edge, passing behind ink.
# Directions are bound on the training pairs, for all sources or (byc=1) per source colour.
def ext_sources(g, b, A, K):
    if A['source'] == 'train': s = {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == K['sc']}
    else:
        s = cells_of(rv(A['source'], g, b)) or set()
        if K.get('sc') is not None: s = {p for p in s if g[p[0]][p[1]] == K['sc']}
    return sorted(s)


def ext_bind(train, A):
    if not same_dims(train): return []
    if A['colour'] == 'hit' and A['stop'] != 'obstacle': return []
    if A['source'] == 'segments':
        pal = set.intersection(*[{v for r in p['input'] for v in r} - {bgc(p['input'])} for p in train])
        lc = {p['output'][y][x] for p in train for y in range(len(p['input'])) for x in range(len(p['input'][0])) if p['input'][y][x] != p['output'][y][x]}
        if A['colour'] == 'train' and len(lc) != 1: return []
        return [{'sc': sc, 'ends': e, 'lc': min(lc) if A['colour'] == 'train' else None, 'hit_only': h, 'stopc': None}
                for sc in [None] + sorted(pal) for e in ('both', 'pos', 'neg') for h in ((False, True) if A['stop'] == 'obstacle' else (False,))]
    pal = set.intersection(*[{v for r in p['input'] for v in r} - {bgc(p['input'])} for p in train])
    scs = sorted(pal) if A['source'] == 'train' else [None] + sorted(pal)
    out = []
    for sc in scs:
        dirs = {}; lc = set()
        for p in train:
            g, o = p['input'], p['output']; b = bgc(g)
            for y, x in ext_sources(g, b, A, {'sc': sc}):
                dirs.setdefault(g[y][x], set())
                for n, (dy, dx) in DIRS.items():
                    yy, xx = y + dy, x + dx
                    if inb(g, yy, xx) and g[yy][xx] == b and o[yy][xx] != b: dirs[g[y][x]].add(n)
            lc |= {o[y][x] for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != o[y][x]}
        alld = set().union(*dirs.values()) if dirs else set()
        if not alld: continue
        if A['colour'] == 'train' and len(lc) != 1: continue
        if A['colour'] == 'hit' and A['stop'] != 'obstacle': continue
        ORTH, DIAG = {'N', 'S', 'W', 'E'}, {'NW', 'NE', 'SW', 'SE'}
        cand = []
        for d in (alld, alld & ORTH, alld & DIAG):                    # the learned set, or only its straight / diagonal part
            if d and sorted(d) not in cand: cand.append(sorted(d))
        dsets = [(0, d) for d in cand] + ([(1, sorted([c, sorted(d)] for c, d in dirs.items()))] if len(dirs) > 1 and sc is None else [])
        for byc, ds in dsets:
            for hit in ((False, True) if A['stop'] == 'obstacle' else (False,)):
                for stc in ([None, 'own'] + sorted(pal) if hit else [None]):
                    out.append({'sc': sc, 'byc': byc, 'dirs': ds, 'lc': min(lc) if A['colour'] == 'train' else None, 'hit_only': hit or A['colour'] == 'hit', 'stopc': stc})
    return out


def _ray(g, b, A, K, y, x, dy, dx, painted, out):
    """one line from (y, x) in direction (dy, dx); False when WHY fails (two lines disagree)"""
    yy, xx = y + dy, x + dx; seg = []; hit = None
    while inb(g, yy, xx):
        if g[yy][xx] != b:
            if A['stop'] == 'obstacle':
                st = K.get('stopc')
                if st is None or g[yy][xx] == (g[y][x] if st == 'own' else st): hit = g[yy][xx]
                break
        else: seg.append((yy, xx))
        yy += dy; xx += dx
    if A['stop'] == 'obstacle' and (K['hit_only'] or A['colour'] == 'hit') and hit is None: return True
    col = g[y][x] if A['colour'] == 'own' else hit if A['colour'] == 'hit' else K['lc']
    for c in seg:
        if painted.setdefault(c, col) != col: return False          # WHY: two lines cross with different colours
        out[c[0]][c[1]] = col
    return True


def ext_apply(g, A, K):
    b = bgc(g); out = copy(g); painted = {}
    if A['source'] == 'segments':                                     # v2: a segment extends along its own direction
        segs = r_segments(g, b)
        if not segs: return None
        if K.get('sc') is not None: segs = [o for o in segs if o['colour'] == K['sc']]
        for o in segs:
            dy, dx = straight_line(o['cells'])
            pr = sorted(o['cells'], key=lambda c: c[0] * dy + c[1] * dx)
            ends = {'pos': [(pr[-1], (dy, dx))], 'neg': [(pr[0], (-dy, -dx))]}
            for (y, x), (ddy, ddx) in (ends['pos'] + ends['neg'] if K['ends'] == 'both' else ends[K['ends']]):
                if not _ray(g, b, A, K, y, x, ddy, ddx, painted, out): return None
        return out
    src = ext_sources(g, b, A, K)
    if not src: return None
    bydir = dict((c, d) for c, d in K['dirs']) if K.get('byc') else None
    for y, x in src:
        if bydir is not None:
            if g[y][x] not in bydir: return None                   # a source colour training never showed
            dl = bydir[g[y][x]]
        else: dl = K['dirs']
        for n in dl:
            if not _ray(g, b, A, K, y, x, DIRS[n][0], DIRS[n][1], painted, out): return None
    return out


# --- tile(extent, unit) WHY: every block of the output is the unit or empty
def tile_bind(train, A):
    if A['extent'] == 'train':
        k = {(len(p['output']) // len(p['input']), len(p['output'][0]) // len(p['input'][0])) for p in train
             if len(p['output']) % len(p['input']) == 0 and len(p['output'][0]) % len(p['input'][0]) == 0}
        kk = list(next(iter(k))) if len(k) == 1 else None
        return [{'k': kk, 'flip': f} for f in (0, 1)] if len(k) == 1 and len(train) == sum(1 for p in train if len(p['output']) % len(p['input']) == 0 and len(p['output'][0]) % len(p['input'][0]) == 0) else []
    if A['extent'] in ('pixel_count', 'object_count'): return [{'lay': l} for l in ('h', 'v', 'sq')]
    if A['extent'] == 'border': return [{}] if same_dims(train) else []
    return [{}]


def period(g, b):
    H, W = dims(g); ink = [(y, x, g[y][x]) for y in range(H) for x in range(W) if g[y][x] != b]
    if not ink: return None
    for area in range(1, H * W):
        for pr in range(1, H + 1):
            if area % pr or area // pr > W: continue
            pc = area // pr; pat = {}; ok = True
            for y, x, v in ink:
                if pat.setdefault((y % pr, x % pc), v) != v: ok = False; break
            if ok: return pr, pc, pat
    return None


def tile_apply(g, A, K):
    b = bgc(g); H, W = dims(g); e = A['extent']
    if e == 'train':
        kr, kc = K['k']
        if kr * kc <= 1 or kr * H > 30 or kc * W > 30: return None
        if K.get('flip'):                                             # odd blocks mirrored (the unit reflected)
            return [[g[(y % H) if (y // H) % 2 == 0 else H - 1 - y % H][(x % W) if (x // W) % 2 == 0 else W - 1 - x % W]
                     for x in range(kc * W)] for y in range(kr * H)]
        return [[g[y % H][x % W] for x in range(kc * W)] for y in range(kr * H)]
    if e in ('pixel_count', 'object_count'):
        n = rv(e, g, b)
        if not n or n < 2: return None
        kr, kc = {'h': (1, n), 'v': (n, 1), 'sq': (n, n)}[K['lay']]
        if kr * H > 30 or kc * W > 30: return None
        return [[g[y % H][x % W] for x in range(kc * W)] for y in range(kr * H)]
    if e in ('fg', 'bg'):
        if H * H > 30 or W * W > 30: return None
        on = lambda i, j: (g[i][j] != b) == (e == 'fg')
        return [[g[y % H][x % W] if on(y // H, x // W) else b for x in range(W * W)] for y in range(H * H)]
    if e == 'border':
        pp = period(g, b)
        if not pp: return None
        pr, pc, pat = pp
        if pr == H and pc == W: return None
        out = [[pat.get((y % pr, x % pc), b) for x in range(W)] for y in range(H)]
        return out
    return None


# --- mirror(axis, subject) WHY: the output is symmetric about the axis detected on the input
def mir_bind(train, A):
    if not same_dims(train): return []
    return [{'which': w, 'orient': o} for w in ('grid', 'bbox', 'line') for o in ('v', 'h', 'both', 'd')]


def mir_apply(g, A, K):
    b = bgc(g); ax = r_axis(g, b).get(K['which'])
    if not ax: return None
    Y2, X2 = ax; o = K['orient']
    if (o in ('v', 'both') and X2 is None) or (o in ('h', 'both') and Y2 is None) or (o == 'd' and (X2 is None or Y2 is None)): return None
    S = cells_of(rv(A['subject'], g, b))
    if not S: return None
    out = copy(g)
    def images(y, x):
        if o == 'v': return [(y, X2 - x)]
        if o == 'h': return [(Y2 - y, x)]
        if o == 'both': return [(y, X2 - x), (Y2 - y, x), (Y2 - y, X2 - x)]
        if (Y2 - X2) % 2: return []
        return [((Y2 - X2) // 2 + x, (X2 - Y2) // 2 + y)]
    for y, x in sorted(S):
        for yy, xx in images(y, x):
            if not inb(g, yy, xx): continue
            if g[yy][xx] == b and out[yy][xx] in (b, g[y][x]): out[yy][xx] = g[y][x]
            elif out[yy][xx] != g[y][x]: return None                 # WHY: the two sides disagree
    return out


# --- recolour(key, subject) WHY: every subject cell of colour a becomes key(a); nothing else changes
def subj_cells(g, b, name, K=None):
    if name == 'train':
        return {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == (K or {}).get('sc')} or None
    return cells_of(rv(name, g, b))


def subj_colours(train):
    return sorted(set.intersection(*[{v for r in p['input'] for v in r} - {bgc(p['input'])} for p in train]))


def rec_bind(train, A):
    if not same_dims(train): return []
    scs = subj_colours(train) if A['subject'] == 'train' else [None]
    if A['key'] in ('key', 'nearest'): return [{'sc': sc} for sc in scs]
    out = []
    for sc in scs:
        m = {}; ok = True
        for p in train:
            g, o = p['input'], p['output']; b = bgc(g); S = subj_cells(g, b, A['subject'], {'sc': sc})
            if not S: ok = False; break
            for y, x in S:
                if m.setdefault(g[y][x], o[y][x]) != o[y][x]: ok = False; break
            if not ok: break
        if ok and not all(k == v for k, v in m.items()): out.append({'sc': sc, 'map': sorted([k, v] for k, v in m.items())})
    return out


def rec_apply(g, A, K):
    b = bgc(g); S = subj_cells(g, b, A['subject'], K)
    if not S: return None
    if A['key'] == 'nearest':                                         # v2: each subject object takes its nearest other object's colour
        out = copy(g); obs = objects(g, b)
        for o in obs:
            if not o['cells'] <= S: continue
            best = None; cols = set()
            for q in obs:
                if q is o or q['cells'] <= S: continue
                d = min(max(abs(a - c), abs(e - f)) for a, e in o['cells'] for c, f in q['cells'])
                if best is None or d < best: best, cols = d, {q['colour']}
                elif d == best: cols.add(q['colour'])
            if len(cols) != 1: return None                              # WHY: no single nearest other colour
            c = next(iter(cols))
            for y, x in o['cells']: out[y][x] = c
        return out
    if A['key'] == 'key':
        m = r_key(g, b)
        if not m: return None
        legend = {c for comp in multis(g, b) if len(comp) == 2 for c in comp}
        S = S - legend
    else: m = dict((k, v) for k, v in K['map'])
    out = copy(g)
    for y, x in S:
        c = g[y][x]
        if c in m: out[y][x] = m[c]
        elif A['key'] == 'train': return None                       # WHY: a subject colour the key does not cover
    return out


# --- fill(region, colour) WHY: every cell of the region is filled, nothing outside it changes
def enclosed(g, b):
    H, W = dims(g); seen = set(); st = [(y, x) for y in range(H) for x in range(W) if (y in (0, H - 1) or x in (0, W - 1)) and g[y][x] == b]
    seen |= set(st)
    while st:
        y, x = st.pop()
        for dy, dx in N4:
            n = (y + dy, x + dx)
            if inb(g, *n) and n not in seen and g[n[0]][n[1]] == b: seen.add(n); st.append(n)
    return {(y, x) for y in range(H) for x in range(W) if g[y][x] == b and (y, x) not in seen}


def fill_region(g, b, name):
    if name == 'bg': return enclosed(g, b) or None
    if name in ('between', 'region'): return cells_of(rv(name, g, b))
    if name == 'frame':
        f = r_frame(g, b)
        if not f: return None
        return {(y, x) for y in range(f[0], f[2] + 1) for x in range(f[1], f[3] + 1) if g[y][x] == b} or None
    return None


def fill_bind(train, A):
    if not same_dims(train): return []
    if A['colour'] == 'own': return [{}]
    cs = set()
    for p in train:
        g, o = p['input'], p['output']; R = fill_region(g, bgc(g), A['region'])
        if not R: return []
        cs |= {o[y][x] for y, x in R}
    return [{'c': cs.pop()}] if len(cs) == 1 else []


def fill_apply(g, A, K):
    b = bgc(g); R = fill_region(g, b, A['region'])
    if not R: return None
    out = copy(g)
    for comp in comps(R, N4):
        if A['colour'] == 'own':
            nb = {g[y + dy][x + dx] for y, x in comp for dy, dx in N4 if inb(g, y + dy, x + dx)} - {b}
            if len(nb) != 1: return None                              # WHY: the enclosing colour is not unique
            c = nb.pop()
        else: c = K['c']
        for y, x in comp: out[y][x] = c
    return out


# --- move(subject, target) WHY: the subject keeps its shape; with target 'obstacle' it ends in contact
def mov_bind(train, A):
    if not same_dims(train): return []
    scs = subj_colours(train) if A['subject'] == 'train' else [None]
    if A['target'] == 'target':
        return [{'sc': sc, 'tc': tc} for sc in scs for tc in target_colours(train)]
    if A['target'] != 'train':
        return [{'sc': sc, 'd': n} for sc in scs for n in (('toward', 'N', 'S', 'W', 'E') if A['target'] == 'obstacle' else ('N', 'S', 'W', 'E'))]
    out = []
    for sc in scs:
        g, o = train[0]['input'], train[0]['output']; b = bgc(g); S = subj_cells(g, b, A['subject'], {'sc': sc})
        if not S: continue
        H, W = dims(g)
        for dy in range(-H + 1, H):
            for dx in range(-W + 1, W):
                if (dy, dx) != (0, 0) and all(inb(o, y + dy, x + dx) and o[y + dy][x + dx] == g[y][x] for y, x in S): out.append({'sc': sc, 'v': [dy, dx]})
    return out[:8]


def target_colours(train):
    """v2 'target': the object that is changed (in every training pair some input object of this colour changes)"""
    out = None
    for p in train:
        g, o = p['input'], p['output']; b = bgc(g)
        cs = {ob['colour'] for ob in objects(g, b) if any(o[y][x] != g[y][x] for y, x in ob['cells'])} if dims(g) == dims(o) else set()
        out = cs if out is None else out & cs
    return sorted(out or [])


def mov_apply(g, A, K):
    b = bgc(g); S = subj_cells(g, b, A['subject'], K)
    if not S: return None
    if A['target'] == 'target':                                       # slide toward the target until it touches it
        T = {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] == K['tc']} - S
        if not T: return None
        res = []
        for n in ('N', 'S', 'W', 'E'):
            r = mov_apply(g, dict(A, target='obstacle'), dict(K, d=n))
            if r is None: continue
            sy, sx = DIRS[n]
            moved = {(y, x) for y in range(len(g)) for x in range(len(g[0])) if r[y][x] != b and (y, x) not in (set(T) | (cells_of(rv('fg', g, b)) - S))}
            if any((y + sy, x + sx) in T for y, x in moved): res.append(r)
        return res[0] if len(res) == 1 else None
    rest = copy(g)
    for y, x in S: rest[y][x] = b
    if A['target'] == 'train': dy, dx = K['v']
    elif K['d'] == 'toward':                                          # the one direction in which the subject meets ink
        hits = [n for n in ('N', 'S', 'W', 'E') if mov_apply(g, A, dict(K, d=n)) is not None]
        if len(hits) != 1: return None
        return mov_apply(g, A, dict(K, d=hits[0]))
    else:
        sy, sx = DIRS[K['d']]; k = 0
        while True:
            nxt = [(y + (k + 1) * sy, x + (k + 1) * sx) for y, x in S]
            if not all(inb(g, *c) for c in nxt): break
            if any(rest[c[0]][c[1]] != b for c in nxt): break
            k += 1
        nxt = [(y + (k + 1) * sy, x + (k + 1) * sx) for y, x in S]
        touched = all(inb(g, *c) for c in nxt)                        # stopped by ink, not by the border
        if A['target'] == 'obstacle' and not touched: return None      # WHY: no contact
        if A['target'] == 'border' and touched: return None
        if k == 0: return None
        dy, dx = k * sy, k * sx
    out = rest
    for y, x in S:
        if not inb(g, y + dy, x + dx): return None
        out[y + dy][x + dx] = g[y][x]
    return out


# --- extract(region) WHY: the output is exactly the region's box of the input
def ext_region_box(g, b, name, K=None):
    K = K or {}
    if name == 'frame': return r_frame(g, b)
    if name == 'region':
        R = r_region(g, b)
        if not R: return None
        y0, x0, y1, x1 = bbox(R); p = K.get('pad', 0)
        return max(0, y0 - p), max(0, x0 - p), min(len(g) - 1, y1 + p), min(len(g[0]) - 1, x1 + p)
    if name == 'panels':
        P = r_panels(g, b)
        if not P: return None
        boxes = P[1]
        if K.get('pick') == 'odd':
            cs = [json.dumps(crop(g, bx)) for bx in boxes]; c = Counter(cs)
            odd = [bx for bx, x in zip(boxes, cs) if c[x] == 1]
            return odd[0] if len(odd) == 1 and len(boxes) >= 3 else None
        i = K.get('pick')
        return boxes[i] if isinstance(i, int) and i < len(boxes) else None
    S = cells_of(rv(name, g, b))
    return bbox(S) if S else None


def xtr_bind(train, A):
    if not all(len(p['output']) <= len(p['input']) and len(p['output'][0]) <= len(p['input'][0]) for p in train): return []
    if A['region'] == 'region': return [{'pad': 0}, {'pad': 1}]
    if A['region'] == 'panels': return [{'pick': 'odd'}] + [{'pick': i} for i in range(4)]
    return [{}]


def xtr_apply(g, A, K):
    box = ext_region_box(g, bgc(g), A['region'], K)
    if not box or box[0] > box[2] or box[1] > box[3]: return None
    out = crop(g, box)
    return out


OBJ_ROWS = ['fg', 'markers', 'largest', 'smallest', 'odd', 'train', 'segments']
REPEATABLE = {'extend', 'stamp', 'fill'}
COLUMNS = {
    'tile':     {'args': [('extent', ['train', 'pixel_count', 'object_count', 'fg', 'bg', 'border']), ('unit', ['input'])],
                 'bind': tile_bind, 'apply': tile_apply, 'why': 'every block of the output is the unit or empty'},
    'stamp':    {'args': [('anchors', ['markers', 'marks', 'fg', 'objects', 'grid_corners', 'obj_corners', 'centre', 'across']), ('unit', ['train', 'exemplar']),
                          ('rest', ['kept', 'cleared']), ('place', ['nearest', 'topleft'])],
                 'bind': stamp_bind, 'apply': stamp_apply, 'why': 'one copy of the unit at every anchor, copies identical'},
    'extend':   {'args': [('stop', ['obstacle', 'border']), ('source', ['markers', 'fg', 'train', 'segments']), ('colour', ['own', 'train', 'hit'])],
                 'bind': ext_bind, 'apply': ext_apply, 'why': 'every line reaches exactly the first stop cell and never crosses it'},
    'mirror':   {'args': [('axis', ['axis']), ('subject', ['fg'])],
                 'bind': mir_bind, 'apply': mir_apply, 'why': 'the output is symmetric about the axis detected on the input'},
    'recolour': {'args': [('key', ['train', 'key', 'nearest']), ('subject', OBJ_ROWS + ['input'])],
                 'bind': rec_bind, 'apply': rec_apply, 'why': 'every subject cell of colour a becomes key(a); nothing else changes'},
    'fill':     {'args': [('region', ['bg', 'frame', 'between', 'region']), ('colour', ['train', 'own'])],
                 'bind': fill_bind, 'apply': fill_apply, 'why': 'every cell of the region is filled; nothing outside it changes'},
    'move':     {'args': [('subject', OBJ_ROWS), ('target', ['train', 'border', 'obstacle', 'target'])],
                 'bind': mov_bind, 'apply': mov_apply, 'why': 'the subject keeps its shape (and ends in contact for obstacle)'},
    'extract':  {'args': [('region', ['largest', 'smallest', 'odd', 'frame', 'fg', 'exemplar', 'region', 'panels'])],
                 'bind': xtr_bind, 'apply': xtr_apply, 'why': 'the output is exactly the region box of the input'},
}


def apply_raw(S, g):
    """the column's result on g (possibly g itself); None when WHY fails or a row is absent. With consts.repeat the step
    is applied again to its own result until nothing changes (v2: "until the output is complete"), at most 30 times."""
    try:
        f = COLUMNS[S['how']]['apply']; out = f(g, S['args'], S['consts'])
        if S['consts'].get('repeat'):
            for _ in range(30):
                if out is None: return None
                nxt = f(out, S['args'], S['consts'])
                if nxt is None or nxt == out: break
                out = nxt
        return out
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, RecursionError): return None


def apply(S, g):
    """C.3: evaluate the rows on g, apply the column with the bound constants; None when WHY fails or nothing changes"""
    out = apply_raw(S, g)
    return out if out is not None and out != g else None


def fit(train, columns=None):
    """C.2: every (column, row assignment, constants) that reproduces every training pair; training pairs only"""
    out = []
    for how, C in COLUMNS.items():
        if columns and how not in columns: continue
        names = [a for a, _ in C['args']]; nfit = 0
        for vals in itertools.product(*[d for _, d in C['args']]):
            A = dict(zip(names, vals))
            try: Ks = C['bind'](train, A)
            except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError): Ks = []
            if how in REPEATABLE: Ks = Ks + [dict(K, repeat=1) for K in Ks]
            for K in Ks:
                S = {'how': how, 'args': A, 'consts': K}
                if all(apply_raw(S, p['input']) == p['output'] for p in train) and any(p['input'] != p['output'] for p in train):
                    out.append(S); nfit += 1; break
            if nfit >= MAX_FITS_PER_COLUMN: break
    return out


def situation_key(S, page=False):
    return S['how'] + '(' + ', '.join('%s:=%s' % (k, PAGE_ROW.get(v, v) if page else v) for k, v in S['args'].items()) + ')'


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import line_check as LC
    if sys.argv[1] == 'fit':
        for k in sys.argv[2:]:
            t = LC.task(k)
            if t is None: print(k, 'not readable'); continue
            print(k, [situation_key(S) for S in fit(t[0]['train'])])
