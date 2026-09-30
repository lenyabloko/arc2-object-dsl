"""STAMP.template_at_markers: a multi-cell template is copied onto every marker.

One parametrised primitive; every parameter is induced from the training pairs (programs are only
yielded when they reproduce all training outputs exactly):
  seg     : how templates and markers are separated
            iso      markers = isolated non-bg cells (no non-bg 8-neighbour); templates = 8-connected
                     multicolour components with >= 2 cells.  Optionally full-length divider lines are
                     stripped first (they stay on the canvas but belong to no template).
            role:m   markers = every cell of colour m (m enumerated over colours present in every input);
                     templates = 8-connected components of the remaining non-bg cells.
  anchor  : where a template attaches to a marker
            same     the template's unique cell of the marker's colour sits on the marker
            centre   the (single, odd-sized) template's bbox centre sits on the marker
            col:a    the template's unique cell of colour a sits on the marker (role mode)
  paste   : all | noanchor (the anchor cell itself is not painted)
  recol   : keep template colours | recolour copy to the marker colour
  tf      : identity | dihedral about the anchor, learned per anchor colour
  canvas  : keep | erase markers | erase templates | erase both
  layout  : grid (in place) | spread (copies laid along the marker axis with the markers' gaps, anchored at
            the template's own marker) | concat (output = copies concatenated along the marker axis)
            | frame (grid split in bordered frames; templates pooled from all frames, output = the frame
            that holds only markers, stamped)
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of

N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
TFS = [lambda a, b: (a, b), lambda a, b: (a, -b), lambda a, b: (-a, b), lambda a, b: (-a, -b),
       lambda a, b: (b, a), lambda a, b: (b, -a), lambda a, b: (-b, a), lambda a, b: (-b, -a)]
TFN = ['id', 'fh', 'fv', 'r180', 'T', 'r90', 'r270', 'aT']


# ------------------------------------------------------------------ segmentation
def line_cells(g, bg):
    h, w = H(g), W(g); s = set()
    for y in range(h):
        if g[y][0] != bg and all(v == g[y][0] for v in g[y]): s.update((y, x) for x in range(w))
    for x in range(w):
        c = g[0][x]
        if c != bg and all(g[y][x] == c for y in range(h)): s.update((y, x) for y in range(h))
    return s


def components(cells):
    """8-connected components of a dict {(y,x):colour}."""
    seen = set(); out = []
    for p in sorted(cells):
        if p in seen: continue
        seen.add(p); st = [p]; comp = []
        while st:
            y, x = st.pop(); comp.append((y, x))
            for dy, dx in N8:
                q = (y + dy, x + dx)
                if q in cells and q not in seen: seen.add(q); st.append(q)
        out.append({q: cells[q] for q in comp})
    return out


def segment(g, bg, seg, region=None):
    """-> (templates [dict cell->colour], markers [(y,x,c)]) or None."""
    h, w = H(g), W(g)
    ys, xs = (range(h), range(w)) if region is None else (range(region[0], region[2] + 1), range(region[1], region[3] + 1))
    cells = {(y, x): g[y][x] for y in ys for x in xs if g[y][x] != bg}
    if seg == 'iso' or seg == 'iso-strip':
        if seg == 'iso-strip':
            ls = line_cells(g, bg)
            if not ls: return None
            for p in ls: cells.pop(p, None)
        mk = [(y, x, c) for (y, x), c in cells.items() if not any((y + dy, x + dx) in cells for dy, dx in N8)]
        for y, x, _ in mk: del cells[(y, x)]
    else:
        m = seg[1]
        mk = [(y, x, c) for (y, x), c in cells.items() if c == m]
        for y, x, _ in mk: del cells[(y, x)]
    tpls = [t for t in components(cells) if len(t) >= 2]
    if len(tpls) > 12 or len(mk) > 40: return None
    return tpls, sorted(mk)


def unique_cell(t, c):
    ps = [p for p, v in t.items() if v == c]
    return ps[0] if len(ps) == 1 else None


def centre(t):
    ys = [y for y, _ in t]; xs = [x for _, x in t]
    if (max(ys) - min(ys)) % 2 or (max(xs) - min(xs)) % 2: return None
    return ((max(ys) + min(ys)) // 2, (max(xs) + min(xs)) // 2)


def match(tpls, marker, anchor):
    """-> (template, anchor cell, key) or None (marker unmatched); raises ValueError if ambiguous/undefined."""
    y, x, c = marker
    if anchor == 'centre':
        if len(tpls) != 1: raise ValueError
        a = centre(tpls[0])
        if a is None: raise ValueError
        return tpls[0], a, '*'
    ac = c if anchor == 'same' else anchor[1]
    hits = [(t, unique_cell(t, ac)) for t in tpls]
    hits = [(t, a) for t, a in hits if a is not None]
    if not hits: return None
    if len({frozenset(((y - a[0], x - a[1]), v) for (y, x), v in t.items()) for t, a in hits}) > 1:
        raise ValueError   # different templates claim the marker: ambiguous (identical copies are fine)
    return hits[0][0], hits[0][1], ac


def stamp_cells(t, a, marker, paste, recol, tf):
    y, x, c = marker; f = TFS[tf]
    for (ty, tx), v in t.items():
        if (ty, tx) == a and paste == 'noanchor': continue
        dy, dx = f(ty - a[0], tx - a[1])
        yield y + dy, x + dx, (c if recol and (ty, tx) != a else v)


# ------------------------------------------------------------------ in-place engine
def plan(g, bg, cfg, region=None, pool=None):
    seg = segment(g, bg, cfg['seg'], region)
    if seg is None: return None
    tpls, mk = seg
    use = pool if pool is not None else tpls
    if not use: return None
    jobs = []
    for m in mk:
        r = match(use, m, cfg['anchor'])
        if r is not None: jobs.append((m, r))
    return tpls, mk, jobs


def paint(g, bg, cfg, tpls, mk, jobs, tfmap, clip):
    o = [list(r) for r in g]
    er = cfg['canvas']
    if er in ('markers', 'both'):
        for y, x, _ in mk: o[y][x] = bg
    if er in ('tpl', 'both'):
        for t in tpls:
            for (y, x) in t: o[y][x] = bg
    r0, c0, r1, c1 = clip
    for m, (t, a, key) in jobs:
        tf = tfmap.get(key) if tfmap is not None else 0
        if tf is None: return None
        for y, x, v in stamp_cells(t, a, m, cfg['paste'], cfg['recol'], tf):
            if r0 <= y <= r1 and c0 <= x <= c1: o[y][x] = v
    return o


def learn_tf(train, cfg):
    ok = {}
    for p in train:
        g, o = p['input'], p['output']; bg = bg_of(g)
        pl = plan(g, bg, cfg)
        if pl is None or not pl[2]: return None
        for m, (t, a, key) in pl[2]:
            s = set()
            for k in range(8):
                if all(0 <= y < H(o) and 0 <= x < W(o) and o[y][x] == v
                       for y, x, v in stamp_cells(t, a, m, cfg['paste'], cfg['recol'], k)):
                    s.add(k)
            ok[key] = ok.get(key, s) & s
    if any(not s for s in ok.values()): return None
    return {k: min(s) for k, s in ok.items()}


def run_grid(g, cfg, tfmap):
    bg = bg_of(g)
    pl = plan(g, bg, cfg)
    if pl is None or not pl[2]: return None
    return paint(g, bg, cfg, *pl, tfmap, (0, 0, H(g) - 1, W(g) - 1))


# ------------------------------------------------------------------ layouts along the marker axis
def axis_of(mk):
    if len(mk) >= 2 and len({y for y, _, _ in mk}) == 1: return 'h'
    if len(mk) >= 2 and len({x for _, x, _ in mk}) == 1: return 'v'
    if len(mk) == 1: return 'any'
    return None


def tpl_box(t):
    ys = [y for y, _ in t]; xs = [x for _, x in t]
    return min(ys), min(xs), max(ys), max(xs)


def run_concat(g, cfg, axis_pref):
    bg = bg_of(g)
    seg = segment(g, bg, cfg['seg'])
    if seg is None: return None
    tpls, mk = seg
    if len(tpls) != 1 or not mk: return None
    ax = axis_of(mk)
    if ax is None: return None
    if ax == 'any': ax = axis_pref
    t = tpls[0]; r0, c0, r1, c1 = tpl_box(t); th, tw = r1 - r0 + 1, c1 - c0 + 1
    mk = sorted(mk, key=lambda m: (m[1], m[0]) if ax == 'h' else (m[0], m[1]))
    n = len(mk)
    o = [[bg] * (tw * n if ax == 'h' else tw) for _ in range(th if ax == 'h' else th * n)]
    for i, (_, _, c) in enumerate(mk):
        oy, ox = (0, i * tw) if ax == 'h' else (i * th, 0)
        for (y, x), v in t.items():
            o[oy + y - r0][ox + x - c0] = c if cfg['recol'] else v
    return o


def run_spread(g, cfg):
    bg = bg_of(g)
    seg = segment(g, bg, cfg['seg'])
    if seg is None: return None
    tpls, mk = seg
    if len(tpls) != 1 or len(mk) < 2: return None
    t = tpls[0]; cs = set(t.values())
    if len(cs) != 1: return None
    ax = axis_of(mk)
    if ax not in ('h', 'v'): return None
    mk = sorted(mk, key=lambda m: m[1] if ax == 'h' else m[0])
    own = [i for i, m in enumerate(mk) if m[2] in cs]
    if len(own) != 1: return None
    j = own[0]
    r0, c0, r1, c1 = tpl_box(t)
    pos = [m[1] if ax == 'h' else m[0] for m in mk]
    size = (c1 - c0 + 1) if ax == 'h' else (r1 - r0 + 1)
    start = {j: c0 if ax == 'h' else r0}
    for i in range(j + 1, len(mk)): start[i] = start[i - 1] + size - 1 + (pos[i] - pos[i - 1])
    for i in range(j - 1, -1, -1): start[i] = start[i + 1] - size + 1 - (pos[i + 1] - pos[i])
    o = [list(r) for r in g]
    for i, (_, _, c) in enumerate(mk):
        if i == j: continue
        for (y, x), v in t.items():
            yy, xx = (y, x - c0 + start[i]) if ax == 'h' else (y - r0 + start[i], x)
            if not (0 <= yy < H(g) and 0 <= xx < W(g)): return None
            o[yy][xx] = c
    return o


# ------------------------------------------------------------------ frames
def frames(g):
    """Maximal single-colour rectangular borders (>= 3x3) whose interior is not that colour."""
    h, w = H(g), W(g)
    R = [[0] * (w + 1) for _ in range(h + 1)]; D = [[0] * (w + 1) for _ in range(h + 1)]
    for y in range(h - 1, -1, -1):
        for x in range(w - 1, -1, -1):
            R[y][x] = R[y][x + 1] + 1 if x + 1 < w and g[y][x + 1] == g[y][x] else 1
            D[y][x] = D[y + 1][x] + 1 if y + 1 < h and g[y + 1][x] == g[y][x] else 1
    out = []
    for y in range(h):
        for x in range(w):
            if R[y][x] < 4 or D[y][x] < 4: continue
            if x > 0 and g[y][x - 1] == g[y][x] and R[y][x - 1] > R[y][x]: pass
            best = None
            for x1 in range(x + R[y][x] - 1, x + 2, -1):
                if D[y][x1] < 4: continue
                for y1 in range(y + min(D[y][x], D[y][x1]) - 1, y + 2, -1):
                    if R[y1][x] >= x1 - x + 1:
                        best = (y, x, y1, x1); break
                if best: break
            if best:
                y0, x0, y1, x1 = best
                inner = Counter(g[yy][xx] for yy in range(y0 + 1, y1) for xx in range(x0 + 1, x1))
                if inner.most_common(1)[0][0] != g[y][x]: out.append(best)
    out = [f for f in out if not any(o != f and o[0] <= f[0] and o[1] <= f[1] and o[2] >= f[2] and o[3] >= f[3] for o in out)]
    return out if 2 <= len(out) <= 6 else None


def run_frame(g, cfg, tfmap):
    fs = frames(g)
    if fs is None: return None
    info = []
    for f in fs:
        inner = (f[0] + 1, f[1] + 1, f[2] - 1, f[3] - 1)
        bg = Counter(g[y][x] for y in range(inner[0], inner[2] + 1) for x in range(inner[1], inner[3] + 1)).most_common(1)[0][0]
        seg = segment(g, bg, cfg['seg'], inner)
        if seg is None: return None
        info.append((f, inner, bg, seg))
    pool = [t for _, _, _, (ts, _) in info for t in ts]
    tg = [i for i in info if not i[3][0] and i[3][1]]
    if len(tg) != 1 or not pool: return None
    f, inner, bg, (ts, mk) = tg[0]
    jobs = []
    for m in mk:
        r = match(pool, m, cfg['anchor'])
        if r is not None: jobs.append((m, r))
    if not jobs: return None
    o = paint(g, bg, cfg, [], mk, jobs, tfmap, inner)
    if o is None: return None
    return [row[f[1]:f[3] + 1] for row in o[f[0]:f[2] + 1]]


# ------------------------------------------------------------------ induction
def safe(fn):
    def w(g):
        try: return fn(g)
        except (ValueError, KeyError, IndexError): return None
    return w


def fits(fn, train):
    for p in train:
        r = fn(p['input'])
        if r is None or r != p['output']: return False
    return True


def seg_options(train):
    opts = ['iso']
    if all(line_cells(p['input'], bg_of(p['input'])) for p in train): opts.append('iso-strip')
    common = None
    for p in train:
        g = p['input']; bg = bg_of(g)
        cs = {v for r in g for v in r} - {bg}
        common = cs if common is None else common & cs
    for m in sorted(common or ()):
        ok = True
        for p in train:
            g = p['input']
            n = sum(v == m for r in g for v in r)
            if n > 12: ok = False; break
        if ok: opts.append(('role', m))
    return opts


def anchors_for(seg, train):
    if seg in ('iso', 'iso-strip'): return ['same', 'centre']
    cs = set()
    for p in train:
        g = p['input']; bg = bg_of(g)
        cs |= {v for r in g for v in r} - {bg, seg[1]}
    return ['centre'] + [('col', a) for a in sorted(cs)]


def segname(s): return s if isinstance(s, str) else 'role=m%d' % s[1]


def fam_template_at_markers(train):
    g0, o0 = train[0]['input'], train[0]['output']
    same = all((H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)
    if same and all(p['input'] == p['output'] for p in train): return
    segs = seg_options(train)
    out = []
    if same:
        for seg in segs:
            for anc in anchors_for(seg, train):
                # cheap precondition: every pair has at least one matched marker
                ok = True
                for p in train:
                    try:
                        pl = plan(p['input'], bg_of(p['input']), {'seg': seg, 'anchor': anc})
                    except ValueError:
                        pl = None
                    if pl is None or not pl[2]: ok = False; break
                if not ok: continue
                for paste in ('all', 'noanchor'):
                    for recol in (False, True):
                        base = {'seg': seg, 'anchor': anc, 'paste': paste, 'recol': recol}
                        try: tfl = learn_tf(train, base)
                        except ValueError: tfl = None
                        tfopts = [None] + ([tfl] if tfl and any(v for v in tfl.values()) else [])
                        for tfm in tfopts:
                            for canvas in ('keep', 'markers', 'tpl', 'both'):
                                cfg = dict(base, canvas=canvas)
                                fn = safe(lambda g, cfg=cfg, tfm=tfm: run_grid(g, cfg, tfm))
                                if fits(fn, train):
                                    tn = 'id' if tfm is None else ','.join('%s:%s' % (k, TFN[v]) for k, v in sorted(tfm.items(), key=str))
                                    out.append(('stamp:template_at_markers[seg=%s,anchor=%s,paste=%s,recol=%d,tf=%s,erase=%s]'
                                                % (segname(seg), anc if isinstance(anc, str) else 'c%d' % anc[1], paste, recol, tn, canvas),
                                                4 + (tfm is not None) + (canvas != 'keep') // 2, fn))
                                    break
                            if len(out) >= 6: break
        for seg in segs:
            if not isinstance(seg, str): continue
            cfg = {'seg': seg}
            fn = safe(lambda g, cfg=cfg: run_spread(g, cfg))
            if fits(fn, train):
                out.append(('stamp:template_at_markers[layout=spread,seg=%s,recol=1]' % seg, 5, fn))
    else:
        for seg in segs:
            if not isinstance(seg, str): continue
            for recol in (True, False):
                for pref in ('h', 'v'):
                    cfg = {'seg': seg, 'recol': recol}
                    fn = safe(lambda g, cfg=cfg, pref=pref: run_concat(g, cfg, pref))
                    if fits(fn, train):
                        out.append(('stamp:template_at_markers[layout=concat,seg=%s,recol=%d,single=%s]' % (seg, recol, pref), 5, fn))
                        break
        if H(o0) < H(g0) and W(o0) < W(g0) and frames(g0) is not None:
            for anc in ('same',):
                for paste in ('all', 'noanchor'):
                    for recol in (False, True):
                        cfg = {'seg': 'iso', 'anchor': anc, 'paste': paste, 'recol': recol, 'canvas': 'keep'}
                        fn = safe(lambda g, cfg=cfg: run_frame(g, cfg, None))
                        if fits(fn, train):
                            out.append(('stamp:template_at_markers[layout=frame,anchor=%s,paste=%s,recol=%d]' % (anc, paste, recol), 5, fn))
    seen = set()
    for name, cost, fn in out[:8]:
        yield name, cost, fn


FAMILIES = (fam_template_at_markers,)
