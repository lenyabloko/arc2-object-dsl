"""STAMP.copy_to_congruent_target: a patterned source is copied onto target regions congruent with it.

One parametrised primitive, three ways of keying the target (all parameters induced on the training pairs;
a program is yielded only when it reproduces every training output):

  shape   objects = connected components of non-bg cells (conn 4|8, multicolour).
          src   : multi   (object with >= 2 colours) | nonplain (monochrome object that is neither a solid
                  rectangle nor a hollow rectangle)
          key   : mask   target cell mask == T(source mask)
                  bbox   target bbox dims == T(source bbox dims)
                  rect   target is a solid rectangle of the source's corner colour, any size; the source
                         pattern is resized by stretching the run that holds the innermost colour
          T     : dihedral transform of the source (identity first)
          recol : keep | recolour a monochrome source to the target colour
          erase : none | source | unmatched monochrome objects | both
  hole    source = the only colour forming exactly one monochrome component; key = the cells of the source
          bbox not in the source (all one colour z); every other placement where those cells are all z
          receives the source cells.
  glyph   blocks (solid monochrome squares, optionally inside a frame that is cropped) are replaced by the
          free-standing glyph of the same colour and size; colour of the copy = the colour paired with the
          block colour in a two-colour legend object (or kept).
"""
import sys; sys.path.insert(0, '/home/claude/work/widen'); sys.path.insert(0, '/home/claude/work/latent')
from collections import Counter
from gdsl import H, W, bg_of, D8
from fam_stamp_template_at_markers import components, safe, fits

N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
N8 = N4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
TNAMES = ['id', 'fh', 'fv', 'r180', 'T', 'r90', 'r270', 'aT']


def comps(cells, nb):
    seen = set(); out = []
    for p in sorted(cells):
        if p in seen: continue
        seen.add(p); st = [p]; comp = []
        while st:
            y, x = st.pop(); comp.append((y, x))
            for dy, dx in nb:
                q = (y + dy, x + dx)
                if q in cells and q not in seen: seen.add(q); st.append(q)
        out.append({q: cells[q] for q in comp})
    return out


class Obj:
    def __init__(self, cells, bg):
        self.cells = cells
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        self.y0, self.x0, self.y1, self.x1 = min(ys), min(xs), max(ys), max(xs)
        self.h, self.w = self.y1 - self.y0 + 1, self.x1 - self.x0 + 1
        self.cols = set(cells.values())
        self.pat = [[cells.get((self.y0 + i, self.x0 + j), bg) for j in range(self.w)] for i in range(self.h)]
        self.mask = [[(self.y0 + i, self.x0 + j) in cells for j in range(self.w)] for i in range(self.h)]
        n = len(cells)
        self.solid = n == self.h * self.w
        self.hollow = (self.h >= 3 and self.w >= 3 and n == 2 * (self.h + self.w) - 4 and
                       all(i in (0, self.h - 1) or j in (0, self.w - 1)
                           for i in range(self.h) for j in range(self.w) if self.mask[i][j]))


def objs_of(g, bg, conn):
    cells = {(y, x): g[y][x] for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg}
    return [Obj(c, bg) for c in comps(cells, N8 if conn == 8 else N4)]


# ------------------------------------------------------------------ resizing (stretch the innermost run)
def innermost(pat, bg):
    boxes = {}
    for i, r in enumerate(pat):
        for j, v in enumerate(r):
            if v == bg: continue
            b = boxes.get(v)
            boxes[v] = (i, j, i, j) if b is None else (min(b[0], i), min(b[1], j), max(b[2], i), max(b[3], j))
    if len(boxes) < 2: return None
    c = min(boxes, key=lambda k: (boxes[k][2] - boxes[k][0] + 1) * (boxes[k][3] - boxes[k][1] + 1))
    b = boxes[c]
    if not all(o[0] <= b[0] and o[1] <= b[1] and o[2] >= b[2] and o[3] >= b[3] for o in boxes.values()): return None
    return c


def axis_map(lines, c, n):
    runs = []
    for i, l in enumerate(lines):
        if runs and lines[runs[-1][0]] == l: runs[-1][1] += 1
        else: runs.append([i, 1])
    hit = [k for k, (s, ln) in enumerate(runs) if c in lines[s]]
    if len(hit) != 1: return None
    k = hit[0]; extra = n - len(lines)
    if runs[k][1] + extra < 1: return None
    idx = []
    for m, (s, ln) in enumerate(runs):
        idx += [s] * (ln + extra if m == k else ln)
    return idx


def resize(pat, h, w, bg):
    if (len(pat), len(pat[0])) == (h, w): return pat
    c = innermost(pat, bg)
    if c is None: return None
    ri = axis_map([tuple(r) for r in pat], c, h)
    ci = axis_map([tuple(r) for r in zip(*pat)], c, w)
    if ri is None or ci is None: return None
    return [[pat[i][j] for j in ci] for i in ri]


# ------------------------------------------------------------------ mode: shape
def run_shape(g, cfg):
    conn, src, key, tn, recol, erase = cfg
    bg = bg_of(g); tf = D8[tn]
    obs = objs_of(g, bg, conn)
    if len(obs) > 40: return None
    if src == 'multi': S = [o for o in obs if len(o.cols) >= 2]
    else: S = [o for o in obs if len(o.cols) == 1 and not o.solid and not o.hollow]
    if not S or len(S) > 4: return None
    if recol and any(len(s.cols) != 1 for s in S): return None
    Tg = [o for o in obs if o not in S and len(o.cols) == 1]
    out = [r[:] for r in g]; done = 0; unmatched = []; jobs = []
    for t in Tg:
        tc = next(iter(t.cols)); P = None
        for s in S:
            if key == 'rect':
                if not t.solid or s.pat[0][0] != tc or recol: continue
                q = resize(s.pat, t.h, t.w, bg)
                if q is None: continue
            else:
                q = tf(s.pat)
                if key == 'mask':
                    if tf(s.mask) != t.mask: continue
                elif (len(q), len(q[0])) != (t.h, t.w): continue
                if recol:
                    sc = next(iter(s.cols)); q = [[tc if v == sc else v for v in r] for r in q]
            if P is not None and P != q: return None
            P = q
        if P is None: unmatched.append(t); continue
        jobs.append((t, P)); done += 1
    if not done: return None
    if erase in ('src', 'both'):
        for s in S:
            for (y, x) in s.cells: out[y][x] = bg
    if erase in ('unm', 'both'):
        for t in unmatched:
            for (y, x) in t.cells: out[y][x] = bg
    for t, P in jobs:
        for i in range(t.h):
            for j in range(t.w):
                y, x = t.y0 + i, t.x0 + j; v = P[i][j]
                if v != bg: out[y][x] = v
                elif (y, x) in t.cells: out[y][x] = bg
    return out


def fam_shape(train):
    g0, o0 = train[0]['input'], train[0]['output']
    if (H(g0), W(g0)) != (H(o0), W(o0)) or g0 == o0: return
    n = 0
    for conn in (8, 4):
        for src in ('multi', 'nonplain'):
            for key in ('mask', 'bbox', 'rect'):
                for tn in (TNAMES if key != 'rect' else ['id']):
                    for recol in ((0, 1) if key != 'rect' else (0,)):
                        for erase in ('none', 'src', 'unm', 'both'):
                            cfg = (conn, src, key, tn, recol, erase)
                            fn = safe(lambda g, cfg=cfg: run_shape(g, cfg))
                            if fits(fn, train):
                                yield ('copy-congruent:shape[%s]' % ','.join(map(str, cfg)), 4, fn); n += 1
                                if n >= 4: return
        if n: return


# ------------------------------------------------------------------ mode: hole
def run_hole(g):
    h, w = H(g), W(g)
    bycol = {}
    for y in range(h):
        for x in range(w): bycol.setdefault(g[y][x], {})[(y, x)] = g[y][x]
    src = []
    for c, cells in bycol.items():
        if len(cells) < 4: continue
        if len(comps(cells, N8)) == 1: src.append(Obj(cells, -1))
    if len(src) != 1: return None
    s = src[0]
    K = [(i, j) for i in range(s.h) for j in range(s.w) if not s.mask[i][j]]
    if not K: return None
    zs = {g[s.y0 + i][s.x0 + j] for i, j in K}
    if len(zs) != 1: return None
    z = zs.pop(); sc = next(iter(s.cols))
    M = [(i, j) for i in range(s.h) for j in range(s.w) if s.mask[i][j]]
    out = [r[:] for r in g]; n = 0
    for y in range(h - s.h + 1):
        for x in range(w - s.w + 1):
            if (y, x) == (s.y0, s.x0): continue
            if all(g[y + i][x + j] == z for i, j in K) and not all(g[y + i][x + j] == z for i, j in M):
                for i, j in M: out[y + i][x + j] = sc
                n += 1
    return out if n else None


def fam_hole(train):
    g0, o0 = train[0]['input'], train[0]['output']
    if (H(g0), W(g0)) != (H(o0), W(o0)) or g0 == o0: return
    fn = safe(run_hole)
    if fits(fn, train): yield ('copy-congruent:hole', 4, fn)


# ------------------------------------------------------------------ mode: glyph (legend-keyed block substitution)
def big_frame(g):
    """Largest monochrome hollow rectangle (by-colour 8-component equal to its bbox border)."""
    bycol = {}
    for y in range(H(g)):
        for x in range(W(g)): bycol.setdefault(g[y][x], {})[(y, x)] = g[y][x]
    best = None
    for c, cells in bycol.items():
        for comp in comps(cells, N4):
            if len(comp) < 12: continue
            o = Obj(comp, -1)
            if o.hollow and (best is None or o.h * o.w > best.h * best.w): best = o
    return best


def run_glyph(g, crop, recol):
    bg = bg_of(g); h, w = H(g), W(g)
    if crop:
        f = big_frame(g)
        if f is None: return None
        inside = lambda y, x: f.y0 <= y <= f.y1 and f.x0 <= x <= f.x1
        fc = next(iter(f.cols))
    else:
        f = None; inside = lambda y, x: True; fc = None
    ib = Counter(g[y][x] for y in range(h) for x in range(w) if inside(y, x) and g[y][x] != fc).most_common(1)[0][0]
    cells_in = {(y, x): g[y][x] for y in range(h) for x in range(w)
                if inside(y, x) and g[y][x] not in (ib, fc)}
    blocks = [Obj(c, ib) for c in comps(cells_in, N4)]
    if not blocks or any(not b.solid or len(b.cols) != 1 for b in blocks): return None
    if len({(b.h, b.w) for b in blocks}) != 1: return None
    bh, bw = blocks[0].h, blocks[0].w
    if bh * bw < 4: return None
    outside = {(y, x): g[y][x] for y in range(h) for x in range(w) if not inside(y, x) and g[y][x] != bg}
    if not outside: return None
    oc = comps(outside, N8)
    glyph, legend = {}, {}
    mono = {}
    for comp in oc:
        cs = set(comp.values())
        if len(cs) == 1:
            mono.setdefault(next(iter(cs)), {}).update(comp)
        elif len(cs) == 2 and recol:
            for c in cs:
                cells = [p for p, v in comp.items() if v == c]
                o = Obj({p: c for p in cells}, bg)
                if o.x0 == min(x for _, x in comp) and o.y0 == min(y for y, _ in comp):
                    d = (cs - {c}).pop()
                    if legend.get(c, d) != d: return None
                    legend[c] = d
    for c, cells in mono.items():   # a glyph may consist of several pieces of its colour
        o = Obj(cells, bg)
        if (o.h, o.w) == (bh, bw) and not o.solid: glyph[c] = o
    out = [r[:] for r in g]
    for b in blocks:
        c = next(iter(b.cols))
        if c not in glyph: return None
        d = legend.get(c) if recol else c
        if d is None: return None
        P = glyph[c].pat
        for i in range(bh):
            for j in range(bw):
                out[b.y0 + i][b.x0 + j] = d if P[i][j] == c else ib
    if f is not None:
        out = [r[f.x0:f.x1 + 1] for r in out[f.y0:f.y1 + 1]]
    return out


def fam_glyph(train):
    for crop in (1, 0):
        for recol in (1, 0):
            fn = safe(lambda g, crop=crop, recol=recol: run_glyph(g, crop, recol))
            if fits(fn, train):
                yield ('copy-congruent:glyph[crop=%d,recol=%d]' % (crop, recol), 5, fn); return


FAMILIES = (fam_shape, fam_hole, fam_glyph)
