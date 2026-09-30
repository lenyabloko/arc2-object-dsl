"""TOPOLOGY prior: invariants under continuous deformation, used as a general search space.

Concept
-------
A grid is read as a planar cell complex.  Foreground objects (connected components; 4- or 8-connected,
single-colour or multicolour) are the "curves/solids"; everything else is ambient space.  For every
object O we compute its INTERIOR I(O): the cells of its bbox (+1 margin) that cannot be reached from
outside without crossing O, where leakage through the complement uses the DUAL connectivity (8-connected
objects leak 4-wise, 4-connected objects leak 8-wise, i.e. a diagonal gap in a 4-object is a hole in its
boundary).  From the interiors we get the classical topological invariants:

  * holes / genus        n_holes(O) = #components of I(O)  (Euler number = 1 - n_holes)
  * containment tree     P inside O  iff  P ⊂ I(O);  depth(P) = #objects containing P; parent = innermost
  * nesting counts       n_children (objects directly inside), has_children
  * boundary contact     touches_border (the object meets the frame of the plane)
  * adjacency graph      degree = #distinct objects 8-adjacent (region adjacency graph)
  * cell depth           depth(cell) = #objects whose interior contains the cell (winding-number analogue)
  * zones                a zone is a component of I(O); its content = colours of objects inside it

Search space (all parameters induced from training pairs; unseen feature values refuse -> None)
  segmentation  seg = (kind, bg): kind ∈ {c4, c8, m4, m8} (conn × single/multi colour); bg = the input mode
                colour (fixed when shared by all training inputs), or the single input colour of all changed
                cells; plus the full colour partition p4/p8 (every colour is a region: region adjacency graph).
  1. topo:recolour[seg,feat(,col)]  object -> action table over a topological feature (n_holes, has_hole,
                                    depth, is_inside, n_children, parent colour, inside colours, touches
                                    border, RAG degree, euler class, empty-holes, linked colours), optionally
                                    keyed with the object colour.  action = keep | delete | literal colour |
                                    role colour (parent / root of containment tree / unique child / mirror
                                    position in the nesting chain).  Table must compress (#objects > #keys).
  2. topo:fill[seg,rule,paint(,clean)(,glob|comp)]
                                    zones (innermost object holes; or global enclosed background regions; or
                                    all background components) painted (bg cells | whole zone) by rule:
                                    encloser colour | unique / majority content colour | table over a zone
                                    feature (encloser colour, rim = outermost ring of rooms, open = reaches
                                    frame, encloser n_holes, size, width/height/size parity, depth, is_rect,
                                    content set, shape).  'clean' also erases loose single dots outside zones.
  3. topo:cellmap[seg,key(,role)]   cellwise map (colour or bg/fg role, containment key) -> keep | colour,
                                    key ∈ {inside, depth, innermost encloser colour, globally enclosed}.
  4. topo:select-colour/keep/crop   the object with the unique max / min / unique value of a topological
                                    measure (interior area, n_holes, #objects inside, n_children, depth,
                                    degree) -> its colour as a constant output, kept alone, or cropped
                                    (bbox | bbox shrunk by its wall | interior).
  5. topo:seed-region               path-connected background component of each seed cell (non-bg, non-wall
                                    colour) painted whole / on its boundary layer / on its OUTER boundary
                                    component only, with the seed colour or an induced colour; walls not
                                    touching any seeded region kept or deleted.
  6. topo:hole-vote                 host = object with most holes; each empty hole takes the majority colour
                                    of free objects congruent to it (translation or dihedral); output grid or
                                    host crop.
Dropped after measurement (0 solves): inner/outer halo of closed curves; recolour by exemplar with the same
hole count; per-object hole-area count rendering.
"""
import sys
from collections import Counter
from itertools import product
sys.path.append('/home/claude/work/widen')
from gdsl import H, W, bg_of, bbox

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


# ------------------------------------------------------------------ core topology
def _comps(h, w, ok, nb):
    """Components of cells (y,x) with ok(y,x) True."""
    seen = set(); out = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or not ok(r, c): continue
            st = [(r, c)]; seen.add((r, c)); cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and ok(yy, xx):
                        seen.add((yy, xx)); st.append((yy, xx))
            out.append(cells)
    return out


def _objects(g, bg, seg):
    h, w = H(g), W(g); nb = N8 if seg[1] == '8' else N4; mono = seg[0] == 'c'
    seen = [[False] * w for _ in range(h)]; out = []
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == bg: continue
            col = g[r][c]; st = [(r, c)]; seen[r][c] = True; cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and g[yy][xx] != bg \
                            and (not mono or g[yy][xx] == col):
                        seen[yy][xx] = True; st.append((yy, xx))
            out.append(cells)
    return out


def _interior(cells, h, w, leak):
    """Cells enclosed by `cells` (not reachable from outside the bbox margin through non-object cells)."""
    r0, c0, r1, c1 = bbox(cells)
    if r1 - r0 < 2 or c1 - c0 < 2: return []
    s = set(cells)
    R0, C0, R1, C1 = r0 - 1, c0 - 1, r1 + 1, c1 + 1
    seen = set(); st = []
    for y in range(R0, R1 + 1):
        for x in (C0, C1):
            if (y, x) not in seen: seen.add((y, x)); st.append((y, x))
    for x in range(C0, C1 + 1):
        for y in (R0, R1):
            if (y, x) not in seen: seen.add((y, x)); st.append((y, x))
    while st:
        y, x = st.pop()
        for dy, dx in leak:
            yy, xx = y + dy, x + dx
            if R0 <= yy <= R1 and C0 <= xx <= C1 and (yy, xx) not in seen and (yy, xx) not in s:
                seen.add((yy, xx)); st.append((yy, xx))
    return [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s and (y, x) not in seen]


_CACHE = {}


class Topo:
    def __init__(self, g, seg, bg):
        self.g = g; h, w = self.h, self.w = H(g), W(g)
        self.bg = bg
        self.objs = objs = _objects(g, bg, seg)
        leak = N4 if seg[1] == '8' else N8
        self.inner = [_interior(o, h, w, leak) for o in objs]
        self.innerset = [set(I) for I in self.inner]
        self.owner = {}
        for k, o in enumerate(objs):
            for c in o: self.owner[c] = k
        n = len(objs)
        # containment
        self.contains = [[] for _ in range(n)]
        self.parents = [[] for _ in range(n)]
        for a in range(n):
            if not self.inner[a]: continue
            Ia = self.innerset[a]
            for b in range(n):
                if b != a and objs[b][0] in Ia:
                    self.contains[a].append(b); self.parents[b].append(a)
        self.depth = [len(p) for p in self.parents]
        self.parent = [min(p, key=lambda a: len(self.inner[a])) if p else None for p in self.parents]
        self.children = [[b for b in self.contains[a] if self.parent[b] == a] for a in range(n)]
        # zones = components of each interior (dual connectivity)
        self.zones = []          # (owner index, cells)
        self.nholes = [0] * n
        for a in range(n):
            if not self.inner[a]: continue
            Ia = self.innerset[a]
            zs = _comps(h, w, lambda y, x, Ia=Ia: (y, x) in Ia, leak)
            self.nholes[a] = len(zs)
            for z in zs: self.zones.append((a, z))
        # cell depth
        self.cdepth = [[0] * w for _ in range(h)]
        self.cenc = [[None] * w for _ in range(h)]    # innermost encloser object index
        best = [[10 ** 9] * w for _ in range(h)]
        for a in range(n):
            L = len(self.inner[a])
            for y, x in self.inner[a]:
                self.cdepth[y][x] += 1
                if L < best[y][x]: best[y][x] = L; self.cenc[y][x] = a

    def root(self, k):
        while self.parent[k] is not None: k = self.parent[k]
        return k

    def outside(self):
        """Background cells connected (4-wise) to the grid border through background cells."""
        if getattr(self, '_out', None) is None:
            h, w, g, bg = self.h, self.w, self.g, self.bg
            st = [(y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] == bg]
            seen = set(st)
            while st:
                y, x = st.pop()
                for dy, dx in N4:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and g[yy][xx] == bg:
                        seen.add((yy, xx)); st.append((yy, xx))
            self._out = seen
        return self._out

    def colour(self, k):
        cs = Counter(self.g[y][x] for y, x in self.objs[k]); return cs.most_common(1)[0][0]

    def degree(self, k):
        s = set(); g = self.g
        for y, x in self.objs[k]:
            for dy, dx in N8:
                yy, xx = y + dy, x + dx
                if 0 <= yy < self.h and 0 <= xx < self.w:
                    j = self.owner.get((yy, xx))
                    if j is not None and j != k: s.add(j)
        return len(s)


def seg_bg(g, seg):
    """seg = (kind, bgmode): bgmode 'mode' (most frequent colour), None (partition: every colour is a region)
    or an int colour induced from the training pairs."""
    kind, bm = seg
    if bm == 'mode': return bg_of(g)
    return bm


def topo(g, seg):
    key = (seg, tuple(map(tuple, g)))
    t = _CACHE.get(key)
    if t is None:
        if len(_CACHE) > 256: _CACHE.clear()
        t = _CACHE[key] = Topo(g, seg[0], seg_bg(g, seg))
    return t


def segs_for(train, partition=True):
    """Segmentations to try: 4 kinds x background modes. Besides the most frequent colour, a colour c is
    tried as background when every changed cell of every training pair had input colour c (the painted
    ambient space) and c is not the mode."""
    modes = {bg_of(p['input']) for p in train}
    bms = [next(iter(modes))] if len(modes) == 1 else ['mode']   # a background shared by all pairs is fixed
    ch = set()
    for p in train:
        i, o = p['input'], p['output']
        if (H(i), W(i)) != (H(o), W(o)): ch = None; break
        ch |= {i[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]}
    if ch and len(ch) == 1:
        c = next(iter(ch))
        if c not in bms: bms.append(c)
    out = [(k, b) for b in bms for k in ('c4', 'c8', 'm4', 'm8')]
    if partition: out += [('c4', None), ('c8', None)]
    return out


def sname(seg):
    k, b = seg
    return k if b == 'mode' else (k.replace('c', 'p') if b is None else f"{k}/bg{b}")


def fixed_bg(train):
    modes = {bg_of(p['input']) for p in train}
    return next(iter(modes)) if len(modes) == 1 else 'mode'


def same_shape(train):
    return all((H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)


# ------------------------------------------------------------------ object features
OFEATS = ('n_holes', 'has_hole', 'depth', 'is_inside', 'n_children', 'has_children', 'parent_colour',
          'inside_colours', 'touches_border', 'degree', 'euler_class', 'zone_empty', 'linked_colours')


def ofeat(t, k, f):
    if f == 'n_holes': return t.nholes[k]
    if f == 'has_hole': return t.nholes[k] > 0
    if f == 'depth': return t.depth[k]
    if f == 'is_inside': return t.depth[k] > 0
    if f == 'n_children': return len(t.children[k])
    if f == 'has_children': return len(t.children[k]) > 0
    if f == 'parent_colour': return None if t.parent[k] is None else t.colour(t.parent[k])
    if f == 'inside_colours': return frozenset(t.g[y][x] for y, x in t.inner[k] if t.g[y][x] != t.bg)
    if f == 'touches_border': return any(y in (0, t.h - 1) or x in (0, t.w - 1) for y, x in t.objs[k])
    if f == 'degree': return t.degree(k)
    if f == 'euler_class': return (t.nholes[k] > 0, len(t.children[k]) > 0)
    if f == 'linked_colours':   # other colours in the same 8-connected foreground component (path-connected to it)
        if t.bg is None: return None
        if not hasattr(t, '_m8'):
            t._m8 = {}
            for cells in _objects(t.g, t.bg, 'm8'):
                cs = frozenset(t.g[y][x] for y, x in cells)
                for c in cells: t._m8[c] = cs
        return t._m8[t.objs[k][0]] - {t.colour(k)}
    if f == 'zone_empty':   # has a hole and every hole is empty (bg only)
        if not t.inner[k]: return 'nohole'
        return all(t.g[y][x] == t.bg for y, x in t.inner[k])
    raise KeyError(f)


def role_colour(t, k, role):
    if role == 'parent': return None if t.parent[k] is None else t.colour(t.parent[k])
    if role == 'root': return t.colour(t.root(k))
    if role == 'child':
        cs = {t.colour(b) for b in t.children[k]}
        return cs.pop() if len(cs) == 1 else None
    if role == 'mirror':   # nesting chain root..leaf read backwards (each level has one child)
        ch = chain(t, k)
        return None if ch is None else t.colour(ch[len(ch) - 1 - ch.index(k)])
    raise KeyError(role)


def chain(t, k):
    r = t.root(k); ch = [r]
    while t.children[ch[-1]]:
        if len(t.children[ch[-1]]) != 1: return None
        ch.append(t.children[ch[-1]][0])
    return ch if k in ch and len(ch) > 1 else None


ROLES = ('parent', 'root', 'child', 'mirror')


def _choose(acts):
    if 'keep' in acts: return 'keep'
    for r in ROLES:
        if ('r', r) in acts: return ('r', r)
    if 'del' in acts: return 'del'
    return sorted(a for a in acts if isinstance(a, tuple))[0]


def _mdl_entries(table):
    """cycle 21 (MDL on used atoms): a lookup table costs 0.5 per entry beyond two, so the shortest table
    that reproduces the training pairs ranks first (e.g. inside -> root colour over a table keyed by colour)."""
    return 0.5 * max(0, len(table) - 2)


# ------------------------------------------------------------------ 1. recolour objects by topological class
def fam_topo_recolour(train):
    if not same_shape(train): return
    for seg in segs_for(train):
        tops = [topo(p['input'], seg) for p in train]
        if any(not t.objs or len(t.objs) > 250 for t in tops): continue
        obs = []; ok = True
        for t, p in zip(tops, train):
            o = p['output']; g = p['input']
            if any(g[y][x] != o[y][x] and (y, x) not in t.owner for y in range(t.h) for x in range(t.w)):
                ok = False; break
            beh = []
            for k, cells in enumerate(t.objs):
                outs = {o[y][x] for y, x in cells}
                acts = set()
                if all(o[y][x] == g[y][x] for y, x in cells): acts.add('keep')
                if len(outs) == 1:
                    c = outs.pop(); acts.add(('c', c))
                    if c == t.bg: acts.add('del')
                    for r in ROLES:
                        if role_colour(t, k, r) == c: acts.add(('r', r))
                if not acts: ok = False; break
                beh.append(acts)
            if not ok: break
            obs.append(beh)
        if not ok or all('keep' in a for beh in obs for a in beh): continue
        mono = seg[0][0] == 'c'
        for f, withcol in product(OFEATS, (False, True)):
            if withcol and not mono: continue
            table = {}; good = True
            for t, beh in zip(tops, obs):
                for k, acts in enumerate(beh):
                    v = ofeat(t, k, f)
                    key = (v, t.colour(k)) if withcol else v
                    table[key] = table[key] & acts if key in table else set(acts)
                    if not table[key]: good = False; break
                if not good: break
            if not good or len({k[0] if withcol else k for k in table}) < 2: continue
            if sum(len(b) for b in obs) <= len(table): continue   # table must compress
            fin = {key: _choose(a) for key, a in table.items()}
            if len(set(fin.values())) < 2: continue

            def fn(g, seg=seg, f=f, withcol=withcol, fin=fin):
                t = topo(g, seg); out = [r[:] for r in g]
                if not t.objs or len(t.objs) > 400: return None
                for k, cells in enumerate(t.objs):
                    v = ofeat(t, k, f)
                    key = (v, t.colour(k)) if withcol else v
                    if key not in fin: return None
                    a = fin[key]
                    if a == 'keep': continue
                    if a == 'del': c = t.bg
                    elif a[0] == 'r': c = role_colour(t, k, a[1])
                    else: c = a[1]
                    if c is None: return None
                    for y, x in cells: out[y][x] = c
                return out
            yield (f"topo:recolour[{sname(seg)},{f}{',col' if withcol else ''}]", 4 + withcol + (seg[1] is None) + _mdl_entries(fin), fn)


# ------------------------------------------------------------------ 2. fill zones (holes) by a topological rule
ZFEATS = ('enc_colour', 'rim', 'open', 'enc_nholes', 'size', 'w_parity', 'h_parity', 'size_parity', 'depth', 'is_rect',
          'content', 'enc_colour_size', 'shape')


def enc_colour(t, a, z):
    """Colour of the zone's encloser: the enclosing object, or (global zones, a is None) the majority colour
    of the non-background cells 4-adjacent to the zone."""
    if a is not None: return t.colour(a)
    cs = Counter(); zs = set(z)
    for y, x in z:
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < t.h and 0 <= xx < t.w and (yy, xx) not in zs and t.g[yy][xx] != t.bg: cs[t.g[yy][xx]] += 1
    if not cs: return None
    top = cs.most_common(2)
    return top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else None


def global_zones(t):
    """Components (4-wise) of non-exterior cells that contain background: regions sealed off from the
    grid border by the union of all objects (the encloser may be several objects)."""
    out = t.outside(); g, bg = t.g, t.bg
    zs = _comps(t.h, t.w, lambda y, x: (y, x) not in out and g[y][x] == bg, N4)
    return [(None, z, z) for z in zs]


def _rim(t, a, z):
    key = 'obj' if a is not None else 'glob'
    if not hasattr(t, '_zcell'): t._zcell = {}
    if key not in t._zcell:
        Z = _innermost_zones(t) if a is not None else bg_components(t)   # enclosed bg zones are bg components
        m = {}
        for zi, (_, zz, _) in enumerate(Z):
            for c in zz: m[c] = zi
        t._zcell[key] = m
    m = t._zcell[key]; zs = set(z); me = m.get(z[0])
    for y, x in z:
        for dy, dx in N4:
            yy, xx = y + dy, x + dx; ok = True
            while 0 <= yy < t.h and 0 <= xx < t.w:
                j = m.get((yy, xx))
                if j is not None and j != me: ok = False; break
                yy += dy; xx += dx
            if ok: return True
    return False


def bg_components(t):
    """Every 4-connected component of background cells (open and closed regions of the complement)."""
    g, bg = t.g, t.bg
    return [(None, z, z) for z in _comps(t.h, t.w, lambda y, x: g[y][x] == bg, N4)]


def zfeat(t, a, z, f):
    if f == 'enc_colour': return enc_colour(t, a, z)
    if f == 'rim':   # outermost ring of rooms: some axis ray leaves the grid without entering another zone
        return _rim(t, a, z)
    if f == 'enc_nholes': return None if a is None else t.nholes[a]
    if f == 'open': return any(y in (0, t.h - 1) or x in (0, t.w - 1) for y, x in z)   # reaches the frame
    if f == 'size': return len(z)
    if f in ('w_parity', 'h_parity'):
        r0, c0, r1, c1 = bbox(z); return ((c1 - c0 + 1) if f[0] == 'w' else (r1 - r0 + 1)) % 2
    if f == 'size_parity': return len(z) % 2
    if f == 'depth': return None if a is None else t.depth[a] + 1
    if f == 'is_rect':
        r0, c0, r1, c1 = bbox(z); return len(z) == (r1 - r0 + 1) * (c1 - c0 + 1)
    if f == 'content': return frozenset(t.g[y][x] for y, x in z if t.g[y][x] != t.bg)
    if f == 'enc_colour_size': return (enc_colour(t, a, z), len(z))
    if f == 'shape':
        r0, c0, _, _ = bbox(z); return tuple(sorted((y - r0, x - c0) for y, x in z))
    raise KeyError(f)


def content_colour(t, z, how):
    cs = Counter(t.g[y][x] for y, x in z if t.g[y][x] != t.bg)
    if not cs: return None
    if how == 'content': return next(iter(cs)) if len(cs) == 1 else None
    top = cs.most_common(2)
    return top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else None


def _innermost_zones(t):
    """Each enclosed cell belongs to its smallest enclosing zone -> list of (owner, zone, cells)."""
    best = {}
    for zi, (a, z) in enumerate(t.zones):
        L = len(z)
        for c in z:
            if c not in best or L < len(t.zones[best[c]][1]): best[c] = zi
    per = {}
    for c, zi in best.items(): per.setdefault(zi, []).append(c)
    return [(t.zones[zi][0], t.zones[zi][1], cells) for zi, cells in sorted(per.items())]


def _loose_dots(t, Z):
    """Single-cell objects lying in no zone (noise in the ambient space)."""
    inz = set()
    for _, z, _ in Z: inz.update(z)
    return [cells[0] for cells in t.objs if len(cells) == 1 and cells[0] not in inz]


def fam_topo_fill(train):
    if not same_shape(train): return
    for seg in segs_for(train, partition=False):
        tops = [topo(p['input'], seg) for p in train]
        if any(len(t.objs) > 250 for t in tops): continue
        for zk in ('obj', 'glob', 'comp'):
            if zk != 'obj' and seg[0] != 'c4': continue    # global zones do not depend on the segmentation kind
            zfun = {'obj': _innermost_zones, 'glob': global_zones, 'comp': bg_components}[zk]
            zl = [zfun(t) for t in tops]
            if not any(zl): continue
            nz_ok = not all(zl)   # a zone-less training pair was left unchanged
            for paint, clean in product(('bg', 'all'), (False, True)):
                if zk != 'obj' and paint == 'all': continue
                obsz = []; ok = True; ndots = 0
                for t, p, Z in zip(tops, train, zl):
                    g, o = p['input'], p['output']
                    cover = set(); row = []
                    for a, z, cells in Z:
                        tgt = [c for c in cells if paint == 'all' or g[c[0]][c[1]] == t.bg]
                        cover.update(tgt)
                        if not tgt: row.append(None); continue
                        outs = {o[y][x] for y, x in tgt}
                        if len(outs) != 1: ok = False; break
                        c = outs.pop()
                        row.append(('keep', c) if all(o[y][x] == g[y][x] for y, x in tgt) else ('set', c))
                    if not ok: break
                    if clean:
                        dots = _loose_dots(t, Z)
                        if any(o[y][x] != t.bg for y, x in dots): ok = False; break
                        cover.update(dots); ndots += len(dots)
                    if any(g[y][x] != o[y][x] and (y, x) not in cover for y in range(t.h) for x in range(t.w)):
                        ok = False; break
                    obsz.append(row)
                if not ok or not any(r and r[0] == 'set' for row in obsz for r in row): continue
                if clean and not ndots: continue

                def apply(g, seg, paint, clean, colour_of, nz_ok=nz_ok, zfun=zfun):
                    t = topo(g, seg); out = [r[:] for r in g]
                    if len(t.objs) > 400: return None
                    Z = zfun(t)
                    if not Z and not nz_ok: return None
                    if clean:
                        for y, x in _loose_dots(t, Z): out[y][x] = t.bg
                    for a, z, cells in Z:
                        tgt = [c for c in cells if paint == 'all' or g[c[0]][c[1]] == t.bg]
                        if not tgt: continue
                        c = colour_of(t, a, z)
                        if c == 'refuse': return None
                        if c is None: continue
                        for y, x in tgt: out[y][x] = c
                    return out

                tag = paint + (',clean' if clean else '') + ('' if zk == 'obj' else ',' + zk)
                for rule in ('encloser', 'content', 'majority'):
                    col = enc_colour if rule == 'encloser' else \
                          (lambda t, a, z, rule=rule: content_colour(t, z, rule))
                    good = True
                    for t, Z, row in zip(tops, zl, obsz):
                        for (a, z, cells), r in zip(Z, row):
                            if r is None: continue
                            c = col(t, a, z)
                            if (c is None and r[0] == 'set') or (c is not None and c != r[1]): good = False; break
                        if not good: break
                    if good:
                        yield (f"topo:fill[{sname(seg)},{rule},{tag}]", 4,
                               lambda g, seg=seg, paint=paint, clean=clean, col=col: apply(g, seg, paint, clean, col))
                for f in ZFEATS:
                    table = {}; good = True
                    for t, Z, row in zip(tops, zl, obsz):
                        for (a, z, cells), r in zip(Z, row):
                            if r is None: continue
                            v = zfeat(t, a, z, f)
                            acts = {('c', r[1])} | ({'keep'} if r[0] == 'keep' else set())
                            table[v] = table[v] & acts if v in table else acts
                            if not table[v]: good = False; break
                        if not good: break
                    nobs = sum(r is not None for row in obsz for r in row)
                    if not good or len(table) < 2 or nobs <= len(table): continue   # table must compress
                    fin = {v: ('keep' if 'keep' in a else next(iter(a))[1]) for v, a in table.items()}
                    if len(set(fin.values())) < 2: continue

                    def col(t, a, z, f=f, fin=fin):
                        v = zfeat(t, a, z, f)
                        if v not in fin: return 'refuse'
                        return None if fin[v] == 'keep' else fin[v]
                    yield (f"topo:fill[{sname(seg)},{f},{tag}]", 5 + _mdl_entries(fin),
                           lambda g, seg=seg, paint=paint, clean=clean, col=col: apply(g, seg, paint, clean, col))


# ------------------------------------------------------------------ 3. inside/outside-dependent cellwise colour map
CKEYS = ('inside', 'depth', 'enc_colour', 'enclosed')


def ckey(t, y, x, kname):
    if kname == 'inside': return t.cdepth[y][x] > 0
    if kname == 'depth': return t.cdepth[y][x]
    if kname == 'enc_colour':
        a = t.cenc[y][x]; return None if a is None else t.colour(a)
    if kname == 'enclosed':    # global: not reachable from the border through background
        out = t.outside()
        if t.g[y][x] == t.bg: return (y, x) not in out
        return not any((y + dy, x + dx) in out or not (0 <= y + dy < t.h and 0 <= x + dx < t.w) for dy, dx in N4)
    raise KeyError(kname)


def fam_topo_cellmap(train):
    if not same_shape(train): return
    for seg in segs_for(train, partition=False):
        tops = [topo(p['input'], seg) for p in train]
        if any(len(t.objs) > 250 for t in tops): continue
        for vrole, kname in product((True, False), CKEYS):
            if kname != 'enclosed' and not all(t.zones for t in tops): continue
            if kname == 'enclosed' and seg[0] != 'c4': continue   # global notion: independent of segmentation
            table = {}; good = True
            for t, p in zip(tops, train):
                g, o = p['input'], p['output']
                for y in range(t.h):
                    for x in range(t.w):
                        v = g[y][x]
                        k = (('bg' if v == t.bg else 'fg') if vrole else v, ckey(t, y, x, kname))
                        acts = {('c', o[y][x])} | ({'keep'} if o[y][x] == v else set())
                        table[k] = table[k] & acts if k in table else acts
                        if not table[k]: good = False; break
                    if not good: break
                if not good: break
            if not good: continue
            fin = {k: ('keep' if 'keep' in a else next(iter(a))[1]) for k, a in table.items()}
            if all(a == 'keep' for a in fin.values()): continue
            byv = {}
            for (v, _), a in fin.items(): byv.setdefault(v, set()).add(a)
            if not any(len(s) > 1 for s in byv.values()): continue   # containment must matter

            def fn(g, seg=seg, kname=kname, vrole=vrole, fin=fin, byv=byv):
                t = topo(g, seg); out = [r[:] for r in g]
                if len(t.objs) > 400: return None
                for y in range(t.h):
                    for x in range(t.w):
                        v = g[y][x]
                        k = (('bg' if v == t.bg else 'fg') if vrole else v, ckey(t, y, x, kname))
                        a = fin.get(k, None)
                        if a is None:
                            # unseen containment value: allowed only if the colour's action never depended on it
                            s = byv.get(k[0])
                            if s is None or len(s) != 1: return None
                            a = next(iter(s))
                        if a != 'keep': out[y][x] = a
                return out
            yield (f"topo:cellmap[{sname(seg)},{kname}{',role' if vrole else ''}]", 4 + (not vrole) + _mdl_entries(fin), fn)


# ------------------------------------------------------------------ 4. select the object by topological class
SFEATS = ('inner_size', 'n_holes', 'n_inside_objs', 'n_children', 'depth', 'degree')


def sfeat(t, k, f):
    if f == 'inner_size': return len(t.inner[k])
    if f == 'n_inside_objs': return len(t.contains[k])
    return ofeat(t, k, f)


def pick(t, f, ext):
    n = len(t.objs)
    if n < 2: return None
    vals = [sfeat(t, k, f) for k in range(n)]
    if ext == 'unique':
        cs = Counter(vals); hits = [k for k in range(n) if cs[vals[k]] == 1]
    else:
        b = max(vals) if ext == 'max' else min(vals)
        hits = [k for k in range(n) if vals[k] == b]
    return hits[0] if len(hits) == 1 else None


def fam_topo_select(train):
    same = same_shape(train)
    shp = {(H(p['output']), W(p['output'])) for p in train}
    const = len(shp) == 1 and all(len({v for r in p['output'] for v in r}) == 1 for p in train)
    for seg in segs_for(train):
        tops = [topo(p['input'], seg) for p in train]
        if any(len(t.objs) < 2 or len(t.objs) > 250 for t in tops): continue
        for f, ext in product(SFEATS, ('max', 'min', 'unique')):
            ks = [pick(t, f, ext) for t in tops]
            if any(k is None for k in ks): continue
            if const:
                if all(t.colour(k) == p['output'][0][0] for t, k, p in zip(tops, ks, train)):
                    oh, ow = next(iter(shp))

                    def fn(g, seg=seg, f=f, ext=ext, oh=oh, ow=ow):
                        t = topo(g, seg); k = pick(t, f, ext)
                        return None if k is None else [[t.colour(k)] * ow for _ in range(oh)]
                    yield (f"topo:select-colour[{sname(seg)},{f},{ext}]", 4 + (seg[1] is None), fn)
            elif same:
                if seg[1] is None: continue

                def fn(g, seg=seg, f=f, ext=ext):
                    t = topo(g, seg); k = pick(t, f, ext)
                    if k is None: return None
                    out = [[t.bg] * t.w for _ in range(t.h)]
                    for y, x in t.objs[k] + t.inner[k]: out[y][x] = g[y][x]
                    return out
                yield (f"topo:keep[{sname(seg)},{f},{ext}]", 4, fn)
            else:
                for part in ('bbox', 'shrink', 'inner'):
                    def fn(g, seg=seg, f=f, ext=ext, part=part):
                        t = topo(g, seg); k = pick(t, f, ext)
                        if k is None: return None
                        cells = t.inner[k] if part == 'inner' else t.objs[k]
                        if not cells: return None
                        r0, c0, r1, c1 = bbox(cells)
                        if part == 'shrink':
                            r0, c0, r1, c1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
                            if r1 < r0 or c1 < c0: return None
                        return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
                    yield (f"topo:crop[{sname(seg)},{f},{ext},{part}]", 4 + (seg[1] is None), fn)


# ------------------------------------------------------------------ 5. path-connected component of a seed point
def fam_topo_seed_region(train):
    """Seeds = cells that are neither background nor the dominant wall colour.  The region of a seed is the
    path-connected component of background cells touching it (walls = every other non-background cell).
    The region (whole, or only its boundary layer: cells adjacent to a wall or to the grid frame) is painted
    with the seed's colour or an induced colour; walls that do not touch any seeded region are kept or
    deleted (induced)."""
    if not same_shape(train): return

    fb = fixed_bg(train)

    def parse(g, fixed_wall=None):
        bg = bg_of(g) if fb == 'mode' else fb
        cs = Counter(v for r in g for v in r if v != bg)
        if len(cs) < 2: return None
        wall = cs.most_common(1)[0][0] if fixed_wall is None else fixed_wall
        seeds = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] not in (bg, wall)]
        return bg, wall, seeds

    def regions(g, bg, seeds, conn):
        nb = N8 if conn == 8 else N4; h, w = H(g), W(g)
        lab = {}; res = []
        for sy, sx in seeds:
            st = [(sy + dy, sx + dx) for dy, dx in nb if 0 <= sy + dy < h and 0 <= sx + dx < w and g[sy + dy][sx + dx] == bg]
            st = [c for c in st if c not in lab]
            idx = len(res); cells = []
            for c in st: lab[c] = idx
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in lab and g[yy][xx] == bg:
                        lab[(yy, xx)] = idx; st.append((yy, xx))
            res.append(((sy, sx), cells))
        return res

    def render(g, conn, paint, colour, walls, fw=None):
        pr = parse(g, fw)
        if pr is None: return None
        bg, wall, seeds = pr
        if not seeds or len(seeds) > 30: return None
        h, w = H(g), W(g); out = [r[:] for r in g]
        regs = regions(g, bg, seeds, conn)
        allr = set(seeds)
        island = set()      # wall cells of components not touching the grid frame (inner boundary components)
        if paint == 'outer8':
            for cells in _objects(g, bg, 'm8'):
                if not any(y in (0, h - 1) or x in (0, w - 1) for y, x in cells): island.update(cells)
        for (sy, sx), cells in regs:
            allr.update(cells)
            c = g[sy][sx] if colour == 'seed' else colour
            mine = set(cells) | {(sy, sx)}
            for y, x in cells:
                if paint != 'whole':
                    nb = N4 if paint == 'edge4' else N8
                    if all(0 <= y + dy < h and 0 <= x + dx < w and ((y + dy, x + dx) in mine or (y + dy, x + dx) in island)
                           for dy, dx in nb): continue
                out[y][x] = c
        if walls == 'del':
            for cells in _objects(g, bg, 'm8'):
                if any(g[y][x] != wall for y, x in cells): continue
                if not any((y + dy, x + dx) in allr for y, x in cells for dy, dx in N8):
                    for y, x in cells: out[y][x] = bg
        return out

    pr = [parse(p['input']) for p in train]
    if any(q is None or not q[2] for q in pr): return
    ws = {q[1] for q in pr}
    fw = next(iter(ws)) if len(ws) == 1 else None     # wall colour shared by all pairs is fixed
    # literal colour candidates: output colours on changed cells
    lit = Counter(p['output'][y][x] for p in train for y in range(H(p['input'])) for x in range(W(p['input']))
                  if p['input'][y][x] != p['output'][y][x])
    if not lit: return
    cols = ['seed'] + [c for c, _ in lit.most_common(2)]
    for conn, paint, colour, walls in product((4, 8), ('whole', 'edge8', 'edge4', 'outer8'), cols, ('keep', 'del')):
        fn = lambda g, conn=conn, paint=paint, colour=colour, walls=walls: render(g, conn, paint, colour, walls, fw)
        if fn(train[0]['input']) != train[0]['output']: continue
        yield (f"topo:seed-region[{conn},{paint},{colour},{walls}]", 4, fn)


# ------------------------------------------------------------------ 6. holes filled by homotopy-free shape vote
def _norm(cells, d8=False):
    res = []
    for t in (range(8) if d8 else (0,)):
        cs = []
        for y, x in cells:
            if t & 1: y, x = x, y
            if t & 2: y = -y
            if t & 4: x = -x
            cs.append((y, x))
        y0 = min(y for y, _ in cs); x0 = min(x for _, x in cs)
        res.append(tuple(sorted((y - y0, x - x0) for y, x in cs)))
    return min(res)


def fam_topo_hole_vote(train):
    """Host = the object with the most holes.  Each hole (a zone of background cells) takes the majority
    colour of the free objects (outside the host's interior) congruent to the hole (translation, or up to
    dihedral maps); holes with no congruent object stay.  Output: the whole grid, or the host's crop."""
    same = same_shape(train)
    fb = fixed_bg(train)
    for seg, d8 in product((('c8', fb), ('c4', fb)), (False, True)):
        def render(g, seg=seg, d8=d8, crop_out=not same):
            t = topo(g, seg)
            if len(t.objs) < 2 or len(t.objs) > 400: return None
            k = pick(t, 'n_holes', 'max')
            if k is None or not t.nholes[k]: return None
            votes = {}
            for j, cells in enumerate(t.objs):
                if j == k or cells[0] in t.innerset[k]: continue
                votes.setdefault(_norm(cells, d8), Counter())[t.colour(j)] += 1
            out = [r[:] for r in g]; n = 0
            for a, z in t.zones:
                if a != k: continue
                hole = [c for c in z if g[c[0]][c[1]] == t.bg]
                if len(hole) != len(z): continue
                v = votes.get(_norm(hole, d8))
                if not v: continue
                top = v.most_common(2)
                if len(top) > 1 and top[0][1] == top[1][1]: return None
                n += 1
                for y, x in hole: out[y][x] = top[0][0]
            if not n: return None
            if crop_out:
                r0, c0, r1, c1 = bbox(t.objs[k]); return [row[c0:c1 + 1] for row in out[r0:r1 + 1]]
            return out
        yield (f"topo:hole-vote[{sname(seg)}{',d8' if d8 else ''}{',crop' if not same else ''}]", 5, render)


FAMILIES = (fam_topo_recolour, fam_topo_fill, fam_topo_cellmap, fam_topo_select, fam_topo_seed_region, fam_topo_hole_vote)
