"""compose_objmap: object correspondence + per-object action learner (composition engine, Dream lane 3).

SEARCH(task) -> [{"program", "preds"}] (best first, <= 3); every program reproduces all training pairs.

Pipeline (per task; per background mode (grid / task-level) x segmentation c4 / c8 / m8 / m4 / colour-groups):
 1. Segment every training input into objects (Obj: cells, colours, bbox, D8 images of its patch).
 2. Correspondence (least action).  For each input object find how it appears in the output: in-place keep /
    uniform recolour / colour map / delete, template matches of every D8 image of its coloured patch (exact or
    uniformly recoloured), or cells it creates.  A placement is only usable through an ACTION DESCRIPTOR that
    predicts it from the input alone:
      keep | delete | (vector-expr, D8 transform, colour-expr, keep-original) | add(creation, colour-expr)
      vector-expr : const(dy,dx) | border d | own-size d x m | toward anchor until contact | onto anchor
                    | snap: least displacement touching an anchor / colour | align row/col with an anchor
                    (start/centre/end) | mirror across an anchor | into the matching hole (slot) of another object
                    | slide d / toward an anchor / toward the nearest edge / where the object's marker points,
                      until at rest (any contact / must hit / must hit colour c); sequential per direction group,
                      local test = the placement is at rest IN THE OUTPUT
                    anchors: nearest, nearest of colour c, largest, nearest / largest of own colour, same shape
      colour-expr : same | const c | colour of the touching / containing / contained / nearest / same-shape /
                    largest / row-marker / col-marker / only-other-coloured object | minority / majority own
                    colour | colour map / swap | lookup table over a feature (shape, size, holes, ranks, the key
                    object's shape ...) | colour of the (interior) reference object with the same holes / size /
                    shape / h / w (legend lookup)
      creation    : rays (8 dirs / groups, stop or through) | ray toward an anchor or from the marker cell |
                    outline 4/8 | fill holes | fill bbox
    Each object gets the SET of consistent descriptors with their gains (output cells made correct).
 3. The action is learned as a function of object attributes: greedy decision lists over bitsets (predicates:
    colour, colour-frequency rank, has colour, size / size rank, h, w, shape class, holes, rect / line / single,
    border, unique colour / shape, same-shape count, touches colour c, inside colour c, contains colour c,
    row/col aligned with colour c, same-shape twin, has a legend reference, extreme / rank position, minority-
    colour count, and negations); rules chosen by coverage, then gain, then description length, with
    branching on the first rules; predicate and descriptor alternatives with the same training support are
    tried as variants (they may differ on the test input; the top-2 are returned).
 4. Render (erase movers, in-place recolours, static moves, sliding groups, creations; paint over / under) and
    verify on ALL training pairs.  MDL acceptance: every rule fires in >= 2 pairs or on >= 2 objects (lists of
    4+ rules: >= 2 pairs each); lookup tables need support per entry.  Novelty guard: a test object of an unseen
    colour may not fall into a colour-decided rule learned from a single colour.  Segmentations whose test
    objects fall outside the training size range are penalised.
 5. Composition with the library (only when no single object map fits):
      FIRST: output-independent programs of the original G-DSL families (ranked by agreement with the outputs)
             -> object map (or -> whole-grid D8 for non-reshaper steps);
      LAST : near-miss object map (renders every pair, only makes correct changes, >= 10% of them) -> a second
             object map (<= 3 rules in all) or the library search (lib_search: gdsl.search over the families
             with a deterministic work bound) on the residual pairs (rendered, output).
Conservation laws (per-colour cell counts) pre-classify the pairs (rearrangement / recolour / delete / create)
and prune the descriptor space.  Whole-grid D8 / global colour-map tasks are left to the library.
No task ids or literal task constants: every colour, vector, predicate value and table entry is induced from
the training pairs.

DETERMINISM (Kaggle parity): the engine has no clock and no signal.  Every search is bounded by a WORK budget
(class Budget): the natural units of work -- segmentation contexts, placement scans, (object x transform x
vocabulary expression) tests and placement hits, slide steps, ray / creation cells, snap and anchor scans,
feature / predicate tables, decision-list nodes, rule-list variants and their renders, library programs
generated and applied to a grid -- are charged to an integer counter, with weights calibrated (NNLS on the
1050-task harness) so that WU_S = 1e8 work units ~ 1 s of CPU on the reference machine; the old wall-clock
limits are kept as WU_S x seconds (15 s per task, 2 s / 3 s per first / last-step learner, gates 2-7 s).
Set iteration never decides an order (hash-seed independent).  Predictions are therefore identical on any
machine, under any load.  (The wall-clock original is compose_objmap_timed.py.)
"""
import sys
from collections import Counter
sys.path.insert(0, '/home/claude/work/widen')
import gdsl

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
DIR8 = {'N': (-1, 0), 'S': (1, 0), 'W': (0, -1), 'E': (0, 1), 'NW': (-1, -1), 'NE': (-1, 1), 'SW': (1, -1), 'SE': (1, 1)}
DIR4 = ('N', 'S', 'W', 'E')
TXS = ('id', 'fh', 'fv', 'r180', 'T', 'r90', 'r270', 'aT')
SEGS = ('c4', 'c8', 'm8', 'm4', 'col')
KEEP = ('keep',)
DEL = ('del',)
ZERO = ('const', 0, 0)
DIAG = None


# ============================================================ deterministic work budget

class Budget:
    """Deterministic work budget: integer work units charged by the engine (no clock).  A sub-budget also
    charges its parent and never has more left than its parent."""
    __slots__ = ('cap', 'used', 'parent')

    def __init__(self, units, parent=None):
        self.cap = int(units); self.used = 0; self.parent = parent

    def spend(self, n):
        b = self
        while b is not None:
            b.used += n; b = b.parent

    def left(self):
        v = self.cap - self.used
        return v if self.parent is None else min(v, self.parent.left())

    def over(self): return self.left() <= 0


NOBUDGET = Budget(1 << 62)

# Work-unit weights (integers): units charged per natural unit of work.  Calibrated by non-negative least squares
# on the 1050-task harness (CPU time per learner call / library phase on the reference machine) so that WU_S units
# ~ 1 s of CPU (1 unit ~ 10 ns).  Integer arithmetic only: the budget is exact on every platform.
WU_S = 100_000_000
W_CALL, W_CALL_A = 0, 81                               # a learner call: base, per training input cell
W_CTX, W_CTX_AREA, W_CTX_OBJ = 0, 102, 1549            # segmentation contexts (per grid: cells, objects)
W_HOLES_A, W_TOWARD, W_CR, W_CR_STEP = 223, 27, 576, 16 # holes (bbox cells), toward (steps x cells), creations
W_SNAP, W_SNAP_RING, W_SNAP_PAIR = 1800, 18, 42        # snap: base, anchor cells x nbrs, ring cells x patch cells
W_ANCH, W_CX, W_CX_N = 459, 279, 19                    # anchors (per object), relative colour (base, per object)
W_SEG, W_SEG_OBJ = 0, 1021                             # a new segmentation: signature, output index, descriptors
W_NM, W_NM_TX = 1021, 1189                             # move / transform pre-scan: per object, per D8 image
W_OD, W_OD_CELL, W_ADD, W_ADD_S = 0, 1923, 577, 59     # object_descs: per object, per cell, per creation kind, per cell
W_REL, W_HIT, W_HIT_CELL, W_REST = 1343, 628, 0, 35    # relative-colour scan; placement hit (+ cells); rest test cells
W_VFILT, W_MONO_OCC = 2, 75                            # vocabulary filtered for unchanged objects; recoloured-copy scan
W_TX, W_PL, W_PL_OCC = 5755, 0, 153                    # per D8 image, per placement scan, per scanned output cell
W_VX, W_VX_CELL, W_SLIDE_K = 66, 4, 44                 # per vocabulary expression, x patch cells, per slide step
W_FEAT, W_FEAT2, W_PM = 2534, 418, 70                  # object features (n, n^2), predicate table (preds x objects)
W_LL, W_LL_D, W_LL_P = 0, 751, 0                       # decision-list setup (descriptors, predicates)
W_NODE, W_NODE_PRED, W_NODE_MASK, W_NODE_CAND, W_NODE_CM = 0, 0, 140, 162, 8 # per decision-list search node
W_STRUCT, W_STRUCT_P = 0, 0                            # per rule list: variant construction
W_VAR, W_VAR_F, W_PAINT = 0, 17, 1568                  # per variant: MDL test (objects x rules); per paint mode
W_REND, W_REND_A, W_REND_O = 546, 9, 410               # per render: base, cells, objects
W_NEAR_A = 3                                           # near-miss test, per output cell
W_FS_GEN, W_FS_PROG = 789962, 0                        # first steps: generation, per program generated
W_RUN, W_RUN_A = 3112, 123                             # a library program applied to one grid: base, per cell
W_LIB_GEN, W_LIB_GEN_A, W_LIB_PROG = 60738876, 115488, 0 # lib_candidates on residual pairs: base, per cell, per program
LIB_MAX_PROGS = 3000                                   # at most this many library programs tried on a residual
# residual last step: library families whose generation has no deterministic internal bound are not searched
# (fam_complete_partial lost its 2 s wall-clock cap for Kaggle parity and can take > 10 s on one residual)
LIB_SKIP = ('fam_complete_partial',)


def tx_cell(t, y, x, h, w):
    if t == 'id': return y, x
    if t == 'fh': return y, w - 1 - x
    if t == 'fv': return h - 1 - y, x
    if t == 'r180': return h - 1 - y, w - 1 - x
    if t == 'T': return x, y
    if t == 'r90': return x, h - 1 - y
    if t == 'r270': return w - 1 - x, y
    return w - 1 - x, h - 1 - y          # aT


def segment(g, bg, seg):
    if seg == 'col':
        d = {}
        for y, row in enumerate(g):
            for x, v in enumerate(row):
                if v != bg: d.setdefault(v, []).append((y, x))
        return [d[c] for c in sorted(d)]
    return gdsl.objects(g, bg, seg[1] == '8', seg[0] == 'c')


# ============================================================ objects and context

class Obj:
    __slots__ = ('i', 'cells', 'cset', 'cols', 'r0', 'c0', 'r1', 'c1', 'h', 'w', 'size', 'colour', 'colours',
                 'rel', 'shape', '_tx', 'ccount')

    def __init__(self, i, cells, g):
        cells = sorted(cells)
        self.i = i; self.cells = cells; self.cset = frozenset(cells)
        self.cols = [g[y][x] for y, x in cells]
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        self.r0, self.c0, self.r1, self.c1 = min(ys), min(xs), max(ys), max(xs)
        self.h = self.r1 - self.r0 + 1; self.w = self.c1 - self.c0 + 1
        self.size = len(cells)
        cnt = Counter(self.cols); self.ccount = cnt
        self.colour = min(cnt, key=lambda c: (-cnt[c], c))
        self.colours = frozenset(cnt)
        self.rel = tuple((y - self.r0, x - self.c0, c) for (y, x), c in zip(cells, self.cols))
        self.shape = frozenset((y, x) for y, x, _ in self.rel)
        self._tx = {}

    def patch(self, t):
        """D8 image of the coloured patch: (cells sorted (dy,dx,c), nh, nw, in-place top-left ay, ax)."""
        r = self._tx.get(t)
        if r is None:
            h, w = self.h, self.w
            cells = tuple(sorted(tx_cell(t, y, x, h, w) + (c,) for y, x, c in self.rel))
            nh, nw = (h, w) if t in ('id', 'fh', 'fv', 'r180') else (w, h)
            r = (cells, nh, nw, self.r0 + (h - nh) // 2, self.c0 + (w - nw) // 2)
            self._tx[t] = r
        return r


def canon_shape(shape):
    """D8-canonical key of a cell shape."""
    ys = [y for y, _ in shape]; xs = [x for _, x in shape]
    h, w = max(ys) + 1, max(xs) + 1
    best = None
    for t in TXS:
        k = tuple(sorted(tx_cell(t, y, x, h, w) for y, x in shape))
        if best is None or k < best: best = k
    return best


class Ctx:
    def __init__(self, g, bg, seg, budget=NOBUDGET):
        self.g = g; self.h = len(g); self.w = len(g[0]); self.bg = bg; self.seg = seg
        self.objs = [Obj(i, c, g) for i, c in enumerate(segment(g, bg, seg))]
        self.owner = [[-1] * self.w for _ in range(self.h)]
        for o in self.objs:
            for y, x in o.cells: self.owner[y][x] = o.i
        self._c = {}
        self.budget = budget        # the relation / creation computations below charge their work here
        budget.spend(W_CTX_AREA * self.h * self.w + W_CTX_OBJ * len(self.objs))

    # ---------------------------------------------------------------- relations (lazy)
    def holes(self, o):
        """(hole cells, number of hole components): 4-conn regions of non-o cells inside o's bbox that are
        not connected to the outside."""
        k = ('holes', o.i)
        if k in self._c: return self._c[k]
        self.budget.spend(W_HOLES_A * (o.h + 2) * (o.w + 2))
        r0, c0, r1, c1 = o.r0 - 1, o.c0 - 1, o.r1 + 1, o.c1 + 1
        seen = {(r0, c0)}; st = [(r0, c0)]
        while st:
            y, x = st.pop()
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if r0 <= q[0] <= r1 and c0 <= q[1] <= c1 and q not in seen and q not in o.cset:
                    seen.add(q); st.append(q)
        hole = set()
        for y in range(o.r0, o.r1 + 1):
            for x in range(o.c0, o.c1 + 1):
                if (y, x) not in seen and (y, x) not in o.cset: hole.add((y, x))
        n = 0; rem = set(hole)
        while rem:
            n += 1; st = [rem.pop()]
            while st:
                y, x = st.pop()
                for dy, dx in N4:
                    q = (y + dy, x + dx)
                    if q in rem: rem.discard(q); st.append(q)
        r = (hole, n)
        self._c[k] = r
        return r

    def touching(self, o, diag=True):
        k = ('touch', o.i, diag)
        if k in self._c: return self._c[k]
        res = set()
        for y, x in o.cells:
            for dy, dx in (N8 if diag else N4):
                yy, xx = y + dy, x + dx
                if 0 <= yy < self.h and 0 <= xx < self.w:
                    j = self.owner[yy][xx]
                    if j >= 0 and j != o.i: res.add(j)
        self._c[k] = res
        return res

    def containers(self):
        """dict obj index -> index of the smallest object whose holes contain it."""
        if 'cont' in self._c: return self._c['cont']
        res = {}
        for a in sorted(self.objs, key=lambda a: -a.size):
            if a.h < 3 or a.w < 3: continue
            hole, n = self.holes(a)
            if not n: continue
            for b in self.objs:
                if b.i != a.i and b.cells[0] in hole: res[b.i] = a.i
        self._c['cont'] = res
        return res

    def inner_colours(self, o):
        hole, n = self.holes(o)
        return frozenset(self.g[y][x] for y, x in hole if self.g[y][x] != self.bg)

    def dist(self, a, b):
        gy = max(0, b.r0 - a.r1, a.r0 - b.r1); gx = max(0, b.c0 - a.c1, a.c0 - b.c1)
        return (max(gy, gx), gy + gx)

    def anchors(self, o):
        """dict anchor-name -> Obj."""
        k = ('anch', o.i)
        if k in self._c: return self._c[k]
        self.budget.spend(W_ANCH * len(self.objs))
        res = {}
        others = [b for b in self.objs if b.i != o.i]
        if others:
            ds = [(self.dist(o, b), b) for b in others]
            m = min(d for d, _ in ds); hits = [b for d, b in ds if d == m]
            if len(hits) == 1: res['near'] = hits[0]
            bycol = {}
            for d, b in ds: bycol.setdefault(b.colour, []).append((d, b))
            for c, lst in bycol.items():
                m = min(d for d, _ in lst); hits = [b for d, b in lst if d == m]
                if len(hits) == 1:
                    res[('nc', c)] = hits[0]
                    if c == o.colour: res['samec'] = hits[0]
                if c == o.colour:
                    mx = max(b.size for _, b in lst); hits = [b for _, b in lst if b.size == mx]
                    if len(hits) == 1 and hits[0].size > o.size: res['bigsame'] = hits[0]
            mx = max(b.size for b in others); hits = [b for b in others if b.size == mx]
            if len(hits) == 1 and hits[0].size > o.size: res['large'] = hits[0]
            ck = self.canon(o); hits = [b for b in others if self.canon(b) == ck]
            if len(hits) == 1: res['twin'] = hits[0]
        self._c[k] = res
        return res

    def hole_slots(self):
        """Background hole components of every object: list of (shape (normalised cell set), top-left, owner)."""
        if 'slots' in self._c: return self._c['slots']
        res = []
        for a in self.objs:
            if a.h < 3 or a.w < 3: continue
            hole, n = self.holes(a)
            rem = {c for c in hole if self.g[c[0]][c[1]] == self.bg}
            while rem:
                st = [rem.pop()]; comp = [st[0]]
                while st:
                    y, x = st.pop()
                    for dy, dx in N4:
                        q = (y + dy, x + dx)
                        if q in rem: rem.discard(q); st.append(q); comp.append(q)
                r0 = min(y for y, _ in comp); c0 = min(x for _, x in comp)
                res.append((frozenset((y - r0, x - c0) for y, x in comp), (r0, c0), a.i))
        self._c['slots'] = res
        return res

    def feat(self, o):
        k = ('feat', o.i)
        if k not in self._c: self._c[k] = obj_features(self, o)
        return self._c[k]

    def bfeat(self, o):
        """Intrinsic features (no relations), used to match objects with reference objects."""
        k = ('bfeat', o.i)
        if k not in self._c:
            self._c[k] = {'holes': self.holes(o)[1], 'size': o.size, 'shapex': o.shape, 'h': o.h, 'w': o.w,
                          'shape': self.canon(o),
                          'border': o.r0 == 0 or o.c0 == 0 or o.r1 == self.h - 1 or o.c1 == self.w - 1}
        return self._c[k]

    def canon(self, o):
        k = ('canon', o.i)
        if k not in self._c: self._c[k] = canon_shape(o.shape)
        return self._c[k]

    # ---------------------------------------------------------------- relative colour expressions
    def colour_expr(self, o, name):
        k = ('cx', o.i, name)
        if k in self._c: return self._c[k]
        self.budget.spend(W_CX + W_CX_N * len(self.objs))
        v = None
        if name in ('touch', 'touch4'):
            cs = {self.objs[j].colour for j in self.touching(o, name == 'touch')} - {o.colour}
            if len(cs) == 1: v = cs.pop()
        elif name == 'container':
            j = self.containers().get(o.i)
            if j is not None: v = self.objs[j].colour
        elif name == 'inner':
            cs = self.inner_colours(o) - {o.colour}
            if len(cs) == 1: v = next(iter(cs))
        elif name == 'near':
            a = self.anchors(o).get('near')
            if a is not None: v = a.colour
        elif name == 'twin':
            ck = self.canon(o)
            cs = {b.colour for b in self.objs if b.i != o.i and b.colour != o.colour and self.canon(b) == ck}
            if len(cs) == 1: v = cs.pop()
        elif name == 'minor':
            if len(o.colours) == 2: v = min(o.colours, key=lambda c: (o.ccount[c], c))
        elif name == 'major':
            if len(o.colours) >= 2: v = o.colour
        elif name == 'large':
            a = self.anchors(o).get('large')
            if a is not None: v = a.colour
        elif name[:3] in ('eq_', 'eqi'):
            # colour of the reference object(s) sharing feature F (eqi: references not touching the border)
            F = name[4:] if name[:4] == 'eqi_' else name[3:]; fv = self.bfeat(o)[F]
            cs = {b.colour for b in self.objs if b.i != o.i and b.colour != o.colour and self.bfeat(b)[F] == fv
                  and (name[:4] != 'eqi_' or not self.bfeat(b)['border'])}
            if len(cs) == 1: v = cs.pop()
        elif name == 'ocol':
            cs = {b.colour for b in self.objs if b.colour != o.colour}
            if len(cs) == 1: v = cs.pop()
        elif name in ('rowmark', 'colmark'):
            cs = set()
            for b in self.objs:
                if b.i == o.i or b.colour == o.colour: continue
                if name == 'rowmark' and b.r0 <= o.r1 and o.r0 <= b.r1: cs.add(b.colour)
                if name == 'colmark' and b.c0 <= o.c1 and o.c0 <= b.c1: cs.add(b.colour)
            if len(cs) == 1: v = cs.pop()
        self._c[k] = v
        return v

    # ---------------------------------------------------------------- vector expressions
    def dir_to(self, o, a):
        """Orthogonal direction from o toward anchor a along the axis where their projections overlap."""
        colov = o.c0 <= a.c1 and a.c0 <= o.c1; rowov = o.r0 <= a.r1 and a.r0 <= o.r1
        if colov == rowov: return None
        if colov: return 'S' if a.r0 > o.r1 else 'N'
        return 'E' if a.c0 > o.c1 else 'W'

    def mark_dir(self, o):
        """Direction pointed at by the object's marker: its single minority-colour cell (multicolour object) or
        the single-cell object touching it, seen from the object's centroid."""
        k = ('mark', o.i)
        if k in self._c: return self._c[k]
        pts = None
        if len(o.colours) == 2:
            mc = min(o.colours, key=lambda c: (o.ccount[c], c))
            if o.ccount[mc] == 1 and o.size > 2: pts = [cell for cell, c in zip(o.cells, o.cols) if c == mc]
        else:
            ts = [self.objs[j] for j in self.touching(o, True) if self.objs[j].size == 1]
            if len(ts) == 1: pts = ts[0].cells
        d = None
        if pts:
            cy = sum(y for y, _ in o.cells) / o.size; cx = sum(x for _, x in o.cells) / o.size
            vy, vx = pts[0][0] - cy, pts[0][1] - cx
            sy = (vy > 0.25) - (vy < -0.25); sx = (vx > 0.25) - (vx < -0.25)
            for name, v in DIR8.items():
                if v == (sy, sx): d = name
        self._c[k] = d
        self._c[('markpts', o.i)] = pts if d else None
        return d

    def slide_dir(self, o, d):
        if isinstance(d, str): return d
        if d[0] == 'mark': return self.mark_dir(o)
        if d[0] == 'edge':      # toward the nearest grid edge (unique)
            ds = {'N': o.r0, 'S': self.h - 1 - o.r1, 'W': o.c0, 'E': self.w - 1 - o.c1}
            m = min(ds.values()); hits = [k for k, v in ds.items() if v == m]
            return hits[0] if len(hits) == 1 else None
        a = self.anchors(o).get(d[1])
        return self.dir_to(o, a) if a is not None else None

    def border_steps(self, o, t, d):
        cells, nh, nw, ay, ax = o.patch(t); sy, sx = DIR8[d]
        ky = (self.h - nh - ay if sy > 0 else ay) if sy else 99
        kx = (self.w - nw - ax if sx > 0 else ax) if sx else 99
        return min(ky, kx)

    def toward(self, o, t, a):
        """Move straight toward anchor a (along the axis where the projections overlap) until contact."""
        d = self.dir_to(o, a)
        if d is None: return None
        sy, sx = DIR8[d]
        cells, nh, nw, ay, ax = o.patch(t)
        abs_cells = [(ay + dy, ax + dx) for dy, dx, _ in cells]
        acs = a.cset
        for step in range(1, 31):
            for y, x in abs_cells:
                if (y + step * sy, x + step * sx) in acs:
                    self.budget.spend(W_TOWARD * step * len(abs_cells))
                    return ((step - 1) * sy, (step - 1) * sx)
        self.budget.spend(W_TOWARD * 30 * len(abs_cells))
        return None

    def snap(self, o, t, a, conn):
        """Least displacement that makes the (transformed) object touch anchor a -- an object, or a set of cells --
        (4/8-adjacency) without overlapping any other cell; None unless unique."""
        cells, nh, nw, ay, ax = o.patch(t)
        rel = [(ay + dy, ax + dx) for dy, dx, _ in cells]
        nb = N8 if conn == 8 else N4
        acs = a.cset if isinstance(a, Obj) else a
        ring = {(y + dy, x + dx) for y, x in acs for dy, dx in nb} - acs
        self.budget.spend(W_SNAP + W_SNAP_RING * len(acs) * len(nb) + W_SNAP_PAIR * len(ring) * len(rel))
        best = None; ties = 0
        for ry, rx in ring:
            for cy, cx in rel:
                off = (ry - cy, rx - cx)
                if off == (0, 0):
                    return (0, 0) if all(not (0 <= y < self.h and 0 <= x < self.w) or True for y, x in rel) else None
                ok = True
                for y, x in rel:
                    yy, xx = y + off[0], x + off[1]
                    if not (0 <= yy < self.h and 0 <= xx < self.w): ok = False; break
                    j = self.owner[yy][xx]
                    if j >= 0 and j != o.i: ok = False; break
                if not ok: continue
                d = (abs(off[0]) + abs(off[1]), max(abs(off[0]), abs(off[1])))
                if best is None or d < best[0]: best = (d, off); ties = 0
                elif d == best[0] and off != best[1]: ties += 1
        if best is None or ties: return None
        return best[1]

    def vx_offset(self, o, t, vx):
        """Offset (dy, dx) of the in-place transformed patch predicted by a STATIC vector expression."""
        kind = vx[0]
        if kind == 'const': return (vx[1], vx[2])
        cells, nh, nw, ay, ax = o.patch(t)
        if kind == 'border':
            k = self.border_steps(o, t, vx[1]); sy, sx = DIR8[vx[1]]
            return (k * sy, k * sx)
        if kind == 'own':
            d, m = vx[1], vx[2]; sy, sx = DIR8[d]
            return (sy * nh * m, sx * nw * m)
        if kind in ('snap', 'snapc') and (o.size > 6 or t != 'id'): return None     # small pieces only (cost)
        if kind == 'snapc':        # touch the nearest cells of colour c (any object of that colour)
            acs = frozenset(cell for b in self.objs if b.i != o.i and b.colour == vx[1] for cell in b.cells)
            return self.snap(o, t, acs, vx[2]) if acs else None
        if kind == 'slot':
            # the unique background hole of another object whose shape is exactly this (transformed) patch
            shp = frozenset((dy, dx) for dy, dx, _ in cells)
            hits = [tl for s, tl, owner in self.hole_slots() if owner != o.i and s == shp]
            if len(hits) != 1: return None
            return (hits[0][0] - ay, hits[0][1] - ax)
        a = self.anchors(o).get(vx[1])
        if a is None: return None
        if kind == 'toward': return self.toward(o, t, a)
        if kind == 'snap': return self.snap(o, t, a, vx[2])
        if kind == 'onto':
            ny, nx = a.r0 + a.r1 - (2 * ay + nh - 1), a.c0 + a.c1 - (2 * ax + nw - 1)
            if ny % 2 or nx % 2: return None
            return (ny // 2, nx // 2)
        if kind == 'alrow':
            m = vx[2]
            if m == 's': return (a.r0 - ay, 0)
            if m == 'e': return (a.r1 - (ay + nh - 1), 0)
            ny = a.r0 + a.r1 - (2 * ay + nh - 1)
            return None if ny % 2 else (ny // 2, 0)
        if kind == 'alcol':
            m = vx[2]
            if m == 's': return (0, a.c0 - ax)
            if m == 'e': return (0, a.c1 - (ax + nw - 1))
            nx = a.c0 + a.c1 - (2 * ax + nw - 1)
            return None if nx % 2 else (0, nx // 2)
        if kind == 'mirh':
            return (0, a.c0 + a.c1 - (ax + nw - 1) - ax)
        if kind == 'mirv':
            return (a.r0 + a.r1 - (ay + nh - 1) - ay, 0)
        return None


EQ_FEATS = ('holes', 'size', 'shapex', 'shape', 'h', 'w')
REL_CX = ('touch', 'touch4', 'container', 'inner', 'near', 'twin', 'minor', 'major', 'large', 'rowmark', 'colmark',
          'ocol') + \
    tuple('eq_' + F for F in EQ_FEATS) + tuple('eqi_' + F for F in EQ_FEATS)
ANCHORS_FIXED = ('near', 'large', 'samec', 'bigsame', 'twin')


def static_vocab(colours):
    v = [('slot',)] + [('snapc', c, k) for c in colours for k in (4, 8)]
    for d in DIR8:
        v.append(('border', d))
        for m in (1, 2): v.append(('own', d, m))
    anchors = list(ANCHORS_FIXED) + [('nc', c) for c in colours]
    for a in anchors:
        v.append(('toward', a)); v.append(('onto', a)); v.append(('snap', a, 4)); v.append(('snap', a, 8))
        for m in ('s', 'c', 'e'):
            v.append(('alrow', a, m)); v.append(('alcol', a, m))
        v.append(('mirh', a)); v.append(('mirv', a))
    return v


def slide_vocab(colours):
    """Sliding expressions: (direction or ('to', anchor), stop) with stop None / 'hit' / colour."""
    v = []
    dirs = list(DIR8) + [('edge',), ('mark',)] + [('to', a) for a in ANCHORS_FIXED] + [('to', ('nc', c)) for c in colours]
    for d in dirs:
        v.append(('slide', d, None)); v.append(('slide', d, 'hit'))
        if isinstance(d, str) and len(d) == 1:
            for c in colours: v.append(('slide', d, c))
    return v


RAY_DIRS = {'N': ('N',), 'S': ('S',), 'E': ('E',), 'W': ('W',), 'NE': ('NE',), 'NW': ('NW',), 'SE': ('SE',),
            'SW': ('SW',), 'orth': ('N', 'S', 'E', 'W'), 'diag': ('NE', 'NW', 'SE', 'SW'), 'vert': ('N', 'S'),
            'horiz': ('E', 'W'), 'all': tuple(DIR8)}


def add_kinds(colours):
    ks = []
    for dn in RAY_DIRS:
        for stop in ('stop', 'through'):
            ks.append(('ray', (dn, stop)))
    for a in ('near', 'samec', 'large', 'mark') + tuple(('nc', c) for c in colours):
        ks.append(('rayto', a))
    ks += [('outline', False), ('outline', True), ('holes', None), ('bbox', None)]
    return ks


def created(ctx, o, kind, param):
    """Cells created by a creation action (on the input geometry): {cell: emitting colour}."""
    key = ('cr', o.i, kind, param)
    if key in ctx._c: return ctx._c[key]
    g = ctx.g; bg = ctx.bg; h, w = ctx.h, ctx.w; S = {}
    steps = 0           # cells visited (charged as work)
    if kind in ('ray', 'rayto'):
        if kind == 'ray':
            dirs = RAY_DIRS[param[0]]; stop = param[1]
        elif param == 'mark':      # a ray from the marker cell in the direction it points
            d = ctx.mark_dir(o); dirs = (d,) if d else (); stop = 'stop'
            srcs = ctx._c.get(('markpts', o.i)) or []
        else:
            a = ctx.anchors(o).get(param)
            d = ctx.dir_to(o, a) if a is not None else None
            dirs = (d,) if d else (); stop = 'stop'
        emit = list(zip(o.cells, o.cols))
        if kind == 'rayto' and param == 'mark':
            emit = [((y, x), g[y][x]) for y, x in srcs]
        for (y, x), col in emit:
            for d in dirs:
                sy, sx = DIR8[d]; yy, xx = y + sy, x + sx
                while 0 <= yy < h and 0 <= xx < w:
                    if (yy, xx) not in o.cset:
                        if g[yy][xx] != bg:
                            if stop == 'stop': break
                        elif (yy, xx) not in S:
                            S[(yy, xx)] = col
                    yy += sy; xx += sx
                steps += max(abs(yy - y), abs(xx - x))
    elif kind == 'outline':
        steps = o.size * (8 if param else 4)
        for y, x in o.cells:
            for dy, dx in (N8 if param else N4):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and g[yy][xx] == bg and (yy, xx) not in o.cset: S[(yy, xx)] = o.colour
    elif kind == 'holes':
        hole, n = ctx.holes(o)
        steps = len(hole)
        for y, x in hole:
            if g[y][x] == bg: S[(y, x)] = o.colour
    elif kind == 'bbox':
        steps = o.h * o.w
        for y in range(o.r0, o.r1 + 1):
            for x in range(o.c0, o.c1 + 1):
                if g[y][x] == bg: S[(y, x)] = o.colour
    elif kind == 'rep':
        # repeated copies along d with period (own extent + gap), until they leave the grid
        d, gap = param; sy, sx = DIR8[d]
        py, px = sy * (o.h + gap), sx * (o.w + gap)
        for k in range(1, 31):
            inside = False; steps += o.size
            for (y, x), col in zip(o.cells, o.cols):
                yy, xx = y + k * py, x + k * px
                if 0 <= yy < h and 0 <= xx < w:
                    inside = True
                    if g[yy][xx] == bg and (yy, xx) not in S: S[(yy, xx)] = col
            if not inside: break
    ctx.budget.spend(W_CR + W_CR_STEP * steps)
    ctx._c[key] = S
    return S


def add_cost(kind, param):
    if kind == 'ray': return 2.2 + (0 if len(param[0]) <= 2 else 0.3) + (0.2 if param[1] == 'through' else 0)
    if kind == 'rep': return 2.4 + 0.2 * param[1] + (0.3 if len(param[0]) == 2 else 0)
    if kind == 'rayto': return 2.6
    return {'outline': 2.0, 'holes': 1.8, 'bbox': 2.2}[kind]


def vx_cost(vx):
    k = vx[0]
    if k == 'const': return 0 if vx[1:] == (0, 0) else 3.0 + 0.1 * (abs(vx[1]) + abs(vx[2]))
    if k == 'slide':
        d = vx[1]
        c = 2.0 if isinstance(d, str) else 2.3 if d[0] in ('edge', 'mark') else 2.4 + (0.3 if d[1] not in ANCHORS_FIXED else 0)
        if isinstance(d, str) and len(d) == 2: c += 0.3
        if vx[2] == 'hit': c += 0.2
        elif vx[2] is not None: c += 0.5
        return c
    if k == 'border': return 2.1 + (0.3 if len(vx[1]) == 2 else 0)
    if k == 'own': return 2.8 + 0.3 * vx[2]
    if k == 'slot': return 2.5
    if k == 'snapc': return 2.9
    base = {'toward': 2.5, 'onto': 2.6, 'alrow': 2.8, 'alcol': 2.8, 'mirh': 2.9, 'mirv': 2.9, 'snap': 2.7}[k]
    return base + (0.3 if vx[1] not in ANCHORS_FIXED else 0)


def cx_cost(cx):
    if cx == 'same': return 0.0
    k = cx[0]
    if k == 'const': return 1.2
    if k == 'rel': return 1.6
    if k == 'tab': return 1.5 + 0.4 * len(cx[2])
    if k == 'swap': return 1.8
    return 2.5


def desc_cost(d):
    if d == KEEP: return 0.0
    if d == DEL: return 1.0
    if d[0] == 'add': return add_cost(d[1], d[2]) + cx_cost(d[3])
    vx, t, cx, copy = d
    return vx_cost(vx) + (0 if t == 'id' else 1.0) + cx_cost(cx) + (0.5 if copy else 0)


# ============================================================ correspondence (placements) and descriptor sets

def out_index(O):
    idx = {}
    for y, row in enumerate(O):
        for x, v in enumerate(row):
            idx.setdefault(v, []).append((y, x))
    return idx


def placements(o, t, O, Oidx):
    """Offsets where the D8 image t of o's coloured patch appears (exact colours) in O."""
    cells, nh, nw, ay, ax = o.patch(t)
    y0, x0, c0 = cells[0]
    Hh, Ww = len(O), len(O[0]); res = set()
    for (y, x) in Oidx.get(c0, ()):
        ty, tx = y - y0, x - x0
        if ty < 0 or tx < 0 or ty + nh > Hh or tx + nw > Ww: continue
        for dy, dx, c in cells:
            if O[ty + dy][tx + dx] != c: break
        else:
            res.add((ty - ay, tx - ax))
    return res


def mono_placements(o, t, O, Oidx, bg, cap=40):
    """Offsets where the shape of t(o) appears uniformly coloured c (c != bg) in O: {offset: c}."""
    cells, nh, nw, ay, ax = o.patch(t)
    y0, x0, _ = cells[0]
    Hh, Ww = len(O), len(O[0]); res = {}
    for c, lst in Oidx.items():
        if c == bg or len(lst) < len(cells): continue
        for (y, x) in lst:
            ty, tx = y - y0, x - x0
            if ty < 0 or tx < 0 or ty + nh > Hh or tx + nw > Ww: continue
            for dy, dx, _ in cells:
                if O[ty + dy][tx + dx] != c: break
            else:
                res[(ty - ay, tx - ax)] = c
                if len(res) > cap: return res
    return res


def conservation(pairs):
    """'rearrange' (per-colour counts equal) / 'recolour' (fg total equal) / 'delete' / 'create' / 'mixed'."""
    kinds = set()
    for i, o in pairs:
        if len(i) != len(o) or len(i[0]) != len(o[0]): return 'diffsize'
        bg = gdsl.bg_of(i)
        ci = Counter(v for r in i for v in r if v != bg); co = Counter(v for r in o for v in r if v != bg)
        if ci == co: kinds.add('rearrange')
        elif sum(ci.values()) == sum(co.values()): kinds.add('recolour')
        elif sum(co.values()) < sum(ci.values()): kinds.add('delete')
        else: kinds.add('create')
    return kinds.pop() if len(kinds) == 1 else 'mixed'


def at_rest(O, bg, cellsabs, sy, sx):
    """(border?, contact colours) one step further along (sy,sx) from the placed cells, read in O."""
    own = set(cellsabs); cols = set(); border = False
    h, w = len(O), len(O[0])
    for y, x in cellsabs:
        yy, xx = y + sy, x + sx
        if not (0 <= yy < h and 0 <= xx < w): border = True; continue
        if (yy, xx) in own: continue
        v = O[yy][xx]
        if v != bg: cols.add(v)
    return border, cols


def rest_ok(stop, border, cols):
    if stop is None: return border or bool(cols)
    if stop == 'hit': return bool(cols)
    return stop in cols


class DSet(dict):
    """descriptor -> gain (number of output cells it makes correct that the input had wrong)."""
    def add(self, d, gain=0):
        if gain > self.get(d, -1): self[d] = gain

    def discard(self, d):
        self.pop(d, None)


def object_descs(ctx, O, Oidx, o, svocab, lvocab, consts, allow, used=None, budget=NOBUDGET):
    """Descriptors consistent with output O for object o (local test), with their gains.
    used: (vector-expr, transform) pairs used by the changed objects; an unchanged object without other
    placements only needs those (a rule whose descriptor is a no-op on every object it covers is useless).
    The work done is charged to budget."""
    g = ctx.g; bg = ctx.bg; res = DSet()
    wk = W_OD + W_OD_CELL * o.size
    ocols = [O[y][x] for y, x in o.cells]
    keep = all(a == b for a, b in zip(ocols, o.cols))
    gone = all(a != b for a, b in zip(ocols, o.cols)) and bg in ocols
    if keep: res.add(KEEP)
    if gone and allow['del']: res.add(DEL, o.size)
    if not keep and allow['recolour']:
        s = set(ocols)
        nchg = sum(1 for a, b in zip(o.cols, ocols) if a != b)
        if len(s) == 1:
            c = ocols[0]
            if c != bg:
                res.add((ZERO, 'id', ('const', c), False), nchg)
                wk += W_REL
                for n in REL_CX:
                    if ctx.colour_expr(o, n) == c: res.add((ZERO, 'id', ('rel', n), False), nchg)
        elif len(o.colours) >= 2 and bg not in s:
            m = {}
            for a, b in zip(o.cols, ocols):
                if m.setdefault(a, b) != b: m = None; break
            if m:
                res.add((ZERO, 'id', ('map', tuple(sorted(m.items()))), False), nchg)
                if len(m) == 2:
                    (a1, b1), (a2, b2) = sorted(m.items())
                    if a1 == b2 and a2 == b1: res.add((ZERO, 'id', ('swap',), False), nchg)
    if keep and allow.get('add'):
        wk += W_ADD * len(allow['add'])
        for kind, param in allow['add']:
            S = created(ctx, o, kind, param)
            if not S: continue
            wk += W_ADD_S * len(S)
            ocs = {O[y][x] for y, x in S}
            if len(ocs) == 1:
                c = next(iter(ocs))
                if c != bg:
                    res.add(('add', kind, param, ('const', c)), len(S))
                    wk += W_REL
                    for n in REL_CX:
                        if ctx.colour_expr(o, n) == c: res.add(('add', kind, param, ('rel', n)), len(S))
            if all(O[y][x] == c for (y, x), c in S.items()): res.add(('add', kind, param, 'same'), len(S))
    if not allow['move']:
        budget.spend(wk)
        return res
    pcache = {}
    hit = [0, 0, 0]     # placement hits tested by add(): count, cells touched, relative-colour scans
    for t in (TXS if allow['tx'] else ('id',)):
        cells, nh, nw, ay, ax = o.patch(t)
        key = (cells, nh, nw, ay, ax)
        wk += W_TX
        if key not in pcache:
            wk += W_PL + W_PL_OCC * len(Oidx.get(cells[0][2], ()))
            pl = placements(o, t, O, Oidx)
            mono = {}
            if allow['recolour'] and t == 'id' and not (pl - {(0, 0)}):
                wk += W_MONO_OCC * sum(len(v) for c, v in Oidx.items() if c != bg)
                mono = mono_placements(o, t, O, Oidx, bg)
                if len(o.colours) == 1: mono = {k: v for k, v in mono.items() if v != o.colour}
            pcache[key] = (pl, mono)
        pl, mono = pcache[key]
        if not pl and not mono: continue

        def add(vx, off, tabs):
            if off not in pl and off not in mono: return
            hit[0] += 1; hit[1] += len(cells) + o.size
            tgt = {(ay + off[0] + dy, ax + off[1] + dx) for dy, dx, _ in cells}
            vac = [(y, x) for y, x in o.cells if (y, x) not in tgt]
            gp = sum(1 for y, x in tgt if g[y][x] != O[y][x])
            gv = sum(1 for y, x in vac if g[y][x] != O[y][x])
            if off in pl:
                still = bool(vac) and all(O[y][x] == g[y][x] for y, x in vac)
                if not still: res.add((vx, t, 'same', False), gp + gv)
                if keep and allow['copy'] and off != (0, 0): res.add((vx, t, 'same', True), gp)
            if off in mono:
                c = mono[off]; hit[2] += 1
                for cx in [('const', c)] + [('rel', n) for n in REL_CX if ctx.colour_expr(o, n) == c]:
                    res.add((vx, t, cx, False), gp + gv)
                    if keep and allow['copy']: res.add((vx, t, cx, True), gp)
        sv, lv, cs = svocab, lvocab, consts
        if used is not None and keep and not mono and pl <= {(0, 0)}:
            wk += W_VFILT * (len(svocab) + len(lvocab) + len(consts))
            sv = [vx for vx in svocab if (vx, t) in used]
            lv = [vx for vx in lvocab if (vx, t) in used]
            cs = [c for c in consts if (('const',) + c, t) in used]
        wk += W_VX * (len(sv) + len(cs) + len(lv)) + W_VX_CELL * (len(sv) + len(lv)) * len(cells)
        # static expressions
        for vx in sv:
            off = ctx.vx_offset(o, t, vx)
            if off is None: continue
            if off == (0, 0) and t == 'id':
                if keep: res.add((vx, 'id', 'same', False))
                continue
            add(vx, off, None)
        for c in cs:
            if c == (0, 0) and t == 'id': continue
            add(('const',) + c, c, None)
        if t != 'id' and (used is None or not keep or (ZERO, t) in used):
            add(ZERO, (0, 0), None)          # transform in place
        # sliding expressions: placement along the direction that is at rest in the output
        for vx in lv:
            d = ctx.slide_dir(o, vx[1])
            if d is None: continue
            sy, sx = DIR8[d]; stop = vx[2]
            kmax = ctx.border_steps(o, t, d)
            wk += W_SLIDE_K * (kmax + 1)
            for k in range(0, kmax + 1):
                off = (k * sy, k * sx)
                if off not in pl and off not in mono: continue
                cabs = [(ay + off[0] + dy, ax + off[1] + dx) for dy, dx, _ in cells]
                wk += W_REST * len(cells)
                border, cols = at_rest(O, bg, cabs, sy, sx)
                if not rest_ok(stop, border, cols): continue
                if off == (0, 0) and t == 'id':
                    if keep: res.add((vx, 'id', 'same', False))
                else:
                    add(vx, off, None)
                break
    wk += W_HIT * hit[0] + W_HIT_CELL * hit[1] + W_REL * hit[2]
    # least action: an object whose disappearance is explained by a move did not vanish
    if DEL in res and any(len(d) == 4 and d[0] != 'add' and not d[3] and (d[0] != ZERO or d[1] != 'id') and d[2] == 'same'
                          and d[0][0] not in ('slot', 'onto') for d in res):
        res.discard(DEL)    # least action: the disappearance is explained by a move
    budget.spend(wk)
    return res


# ============================================================ predicates

def obj_features(ctx, o):
    """dict feature -> value (hashable) for predicate construction."""
    f = {}
    objs = ctx.objs
    f['col'] = o.colour
    f['size'] = o.size
    sizes = sorted({b.size for b in objs}, reverse=True)
    f['srank'] = sizes.index(o.size)
    f['srank_r'] = len(sizes) - 1 - sizes.index(o.size)
    f['h'] = o.h; f['w'] = o.w
    f['rect'] = o.size == o.h * o.w
    f['line'] = (o.h == 1 or o.w == 1) and o.size == o.h * o.w and o.size > 1
    f['single'] = o.size == 1
    f['square'] = o.h == o.w
    hole, nh = ctx.holes(o)
    f['holes'] = min(nh, 6)
    f['border'] = o.r0 == 0 or o.c0 == 0 or o.r1 == ctx.h - 1 or o.c1 == ctx.w - 1
    ck = ctx.canon(o)
    f['shape'] = ck
    f['shapex'] = tuple(sorted(o.shape))
    f['ushape'] = sum(1 for b in objs if ctx.canon(b) == ck) == 1
    f['ucol'] = sum(1 for b in objs if b.colour == o.colour) == 1
    f['ncol'] = min(len(o.colours), 3)
    f['has'] = o.colours
    f['touch'] = frozenset(objs[j].colour for j in ctx.touching(o, True))
    f['ntouch'] = min(len(ctx.touching(o, True)), 2)
    cont = ctx.containers()
    f['in'] = frozenset([objs[cont[o.i]].colour]) if o.i in cont else frozenset()
    f['contains'] = ctx.inner_colours(o)
    rowc = set(); colc = set()
    for b in objs:
        if b.i == o.i: continue
        if b.r0 <= o.r1 and o.r0 <= b.r1: rowc.add(b.colour)
        if b.c0 <= o.c1 and o.c0 <= b.c1: colc.add(b.colour)
    f['rowal'] = frozenset(rowc); f['colal'] = frozenset(colc)
    f['twin'] = frozenset(b.colour for b in objs if b.i != o.i and ctx.canon(b) == ck)
    ext = set()
    if o.r0 == min(b.r0 for b in objs) and sum(1 for b in objs if b.r0 == o.r0) == 1: ext.add('top')
    if o.r1 == max(b.r1 for b in objs) and sum(1 for b in objs if b.r1 == o.r1) == 1: ext.add('bottom')
    if o.c0 == min(b.c0 for b in objs) and sum(1 for b in objs if b.c0 == o.c0) == 1: ext.add('left')
    if o.c1 == max(b.c1 for b in objs) and sum(1 for b in objs if b.c1 == o.c1) == 1: ext.add('right')
    f['ext'] = frozenset(ext)
    f['minorcnt'] = min(o.ccount.values()) if len(o.colours) >= 2 else 0
    f['hasref'] = frozenset(F for F in EQ_FEATS if ctx.colour_expr(o, 'eqi_' + F) is not None)
    others = [b for b in objs if b.colour != o.colour]
    f['oshape'] = ctx.canon(others[0]) if len(others) == 1 else None     # shape of the single key object
    f['nsame'] = min(sum(1 for b in objs if ctx.canon(b) == ck), 4)
    ccnt = Counter(b.colour for b in objs); vals = sorted(set(ccnt.values()), reverse=True)
    f['colrank'] = vals.index(ccnt[o.colour]); f['colrank_r'] = len(vals) - 1 - f['colrank']
    f['ncolsame'] = min(sum(1 for b in objs if b.colour == o.colour), 4)
    ys = sorted({b.r0 for b in objs}); xs = sorted({b.c0 for b in objs})
    f['yrank'] = ys.index(o.r0); f['xrank'] = xs.index(o.c0)
    f['yrank_r'] = len(ys) - 1 - f['yrank']; f['xrank_r'] = len(xs) - 1 - f['xrank']
    return f


SET_FEATS = ('has', 'touch', 'in', 'contains', 'rowal', 'colal', 'twin', 'ext', 'hasref')
NOPRED = ('shapex', 'oshape')
TAB_FEATS = ('shape', 'shapex', 'size', 'holes', 'h', 'w', 'minorcnt', 'ntouch', 'srank', 'srank_r', 'yrank', 'xrank',
             'yrank_r', 'xrank_r', 'nsame', 'ncolsame', 'oshape')
PRED_COST = {'col': 1.0, 'size': 1.6, 'size>=': 2.0, 'size<=': 2.0, 'srank': 1.2, 'srank_r': 1.2, 'h': 2.0, 'w': 2.0,
             'rect': 1.2, 'line': 1.2, 'single': 1.0, 'square': 1.5, 'holes': 1.3, 'border': 1.2, 'shape': 2.5,
             'ushape': 1.5, 'ucol': 1.5, 'ncol': 1.5, 'has': 1.3, 'touch': 1.4, 'ntouch': 1.6, 'in': 1.4,
             'contains': 1.4, 'rowal': 1.8, 'colal': 1.8, 'twin': 1.8, 'ext': 2.0, 'minorcnt': 2.0,
             'touch*': 1.3, 'in*': 1.3, 'contains*': 1.3, 'twin*': 1.6, 'hasref': 1.8,
             'yrank': 2.0, 'xrank': 2.0, 'yrank_r': 2.0, 'xrank_r': 2.0, 'nsame': 1.8, 'ncolsame': 1.8,
             'colrank': 1.3, 'colrank_r': 1.3}


def pred_eval(p, f):
    """Evaluate predicate p = (feat, value[, neg]) on feature dict f."""
    k = p[0]
    if k == 'true': return True
    if k == 'size>=': r = f['size'] >= p[1]
    elif k == 'size<=': r = f['size'] <= p[1]
    elif k in ('touch*', 'in*', 'contains*', 'twin*'): r = bool(f[k[:-1]])
    elif k in SET_FEATS: r = p[1] in f[k]
    else: r = f[k] == p[1]
    return (not r) if len(p) > 2 else r


def build_preds(feats):
    """All predicates with values observed on training objects."""
    vals = {}
    for f in feats:
        for k, v in f.items():
            if k in NOPRED: continue
            if k in SET_FEATS:
                for c in v: vals.setdefault(k, set()).add(c)
            else:
                vals.setdefault(k, set()).add(v)
    preds = [('true', None)]
    for k, vs in vals.items():
        if k == 'shape':
            cnt = Counter(f['shape'] for f in feats)
            vs = {v for v in vs if cnt[v] >= 2}
        if k in ('srank', 'srank_r', 'yrank', 'xrank', 'yrank_r', 'xrank_r', 'colrank', 'colrank_r'):
            vs = {v for v in vs if v <= (1 if k[0] == 's' else 0)}
        if len(vs) > 12 and k not in SET_FEATS: continue
        for v in sorted(vs, key=repr):
            preds.append((k, v)); preds.append((k, v, True))
        if k == 'size':
            for v in sorted(vs):
                preds.append(('size>=', v)); preds.append(('size<=', v))
    for k in ('touch*', 'in*', 'contains*', 'twin*'):
        preds.append((k, None)); preds.append((k, None, True))
    return preds


def pred_cost(p):
    if p[0] == 'true': return 0.0
    return PRED_COST.get(p[0], 2.0) + (0.4 if len(p) > 2 else 0.0)


# ============================================================ decision-list learning

def popcount(x): return bin(x).count('1')


def learn_lists(n, dmask, pmask, dgain=None, max_rules=5, max_lists=20, budget=NOBUDGET):
    """Greedy decision lists with diversified branching on the first rules.
    dmask: {desc: bitmask of objects it is consistent with}; pmask: {pred: bitmask of objects it holds on}.
    Returns (lists of (pred, mask) whose last pred is 'true', {mask: descriptors sorted by cost}).
    The work done (per search node) is charged to budget."""
    full = (1 << n) - 1
    bymask = {}
    for d, m in dmask.items():
        bymask.setdefault(m, []).append(d)
    dg = dgain or {}
    for m in bymask: bymask[m].sort(key=lambda d: (-dg.get(d, 0), desc_cost(d), repr(d)))
    mcost = {m: desc_cost(ds[0]) for m, ds in bymask.items()}
    mgain = {m: dg.get(ds[0], 0) for m, ds in bymask.items()}
    # a mask whose best descriptor changes nothing on any object it covers is dominated by 'keep'
    masks = sorted((m for m in bymask if mgain[m] > 0 or KEEP in bymask[m]), key=lambda m: mcost[m])
    preds = [(p, pm) for p, pm in sorted(pmask.items(), key=lambda kv: pred_cost(kv[0])) if p[0] != 'true']
    results = []; seen = set()

    def rec(R, rules, depth):
        if len(results) >= max_lists: return
        closing = sorted(((mcost[m], m) for m in masks if R & ~m == 0), key=lambda c: c[0])
        ncl = 2 if depth == 0 else 1
        used_m = set()
        for cst, m in closing:
            if len(used_m) >= ncl: break
            used_m.add(m)
            key = tuple(rules) + ((('true', None), m, R),)
            if key not in seen:
                seen.add(key); results.append(list(key))
        if closing and depth >= 1: return
        if depth + 1 >= max_rules: return
        budget.spend(W_NODE + W_NODE_PRED * len(preds) + W_NODE_MASK * len(masks))
        covmap = {}
        for p, pm in preds:                      # cheapest predicate per distinct cover
            cov = pm & R
            if cov and cov != R and cov not in covmap: covmap[cov] = p
        live = [m for m in masks if m & R]
        cands = []
        for cov, p in covmap.items():
            k = popcount(cov); pc = pred_cost(p)
            for m in live:
                if not (cov & ~m):
                    cands.append((k, pc + mcost[m], p, m, cov))
        budget.spend(W_NODE_CAND * len(cands) + W_NODE_CM * len(covmap) * len(live))
        if not cands: return
        picks = []
        by_cov = sorted(cands, key=lambda c: (-c[0], -mgain[c[3]], c[1]))
        width = 4 if depth == 0 else (2 if depth == 1 else 1)
        seen_cov = set(); seen_m = set()
        for c in by_cov:
            if c[4] in seen_cov or c[3] in seen_m: continue
            seen_cov.add(c[4]); seen_m.add(c[3]); picks.append(c)
            if len(picks) >= width: break
        if depth == 0:   # cheapest-per-object alternatives (different descriptor)
            by_eff = sorted(cands, key=lambda c: (c[1] / c[0], -c[0]))
            extra = 0
            for c in by_eff:
                if c[4] in seen_cov or c[3] in seen_m or c[0] < 2: continue
                seen_cov.add(c[4]); seen_m.add(c[3]); picks.append(c); extra += 1
                if extra >= 2: break
        for c in picks:
            rules.append((c[2], c[3], R))
            rec(R & ~c[4], rules, depth + 1)
            rules.pop()
            if len(results) >= max_lists: break

    rec(full, [], 0)
    return results, bymask


# ============================================================ rendering

def cx_colour(ctx, o, cx, c):
    if cx == 'same': return c
    k = cx[0]
    if k == 'const': return cx[1]
    if k == 'rel': return ctx.colour_expr(o, cx[1])
    if k == 'map': return dict(cx[1]).get(c)
    if k == 'swap':
        if len(o.colours) != 2: return None
        a, b = sorted(o.colours)
        return b if c == a else a
    if k == 'tab':
        return dict(cx[2]).get(ctx.feat(o)[cx[1]])
    return None


def canvas_slide(out, bg, abs_cells, sy, sx, stop):
    """Free steps along (sy,sx) on the current canvas (stop at any non-bg cell or the border);
    None when the stop condition ('hit' / colour) is not met at rest."""
    h, w = len(out), len(out[0]); own = set(abs_cells); step = 1
    while True:
        cols = set(); border = False
        for y, x in abs_cells:
            yy, xx = y + step * sy, x + step * sx
            if not (0 <= yy < h and 0 <= xx < w): border = True; continue
            if (yy, xx) in own: continue
            v = out[yy][xx]
            if v != bg: cols.add(v)
        if border or cols:
            return step - 1 if rest_ok(stop, border, cols) else None
        step += 1


def render(ctx, descs, paint='over'):
    """Apply one descriptor per object; returns the output grid or None."""
    g = ctx.g; bg = ctx.bg; out = [r[:] for r in g]
    static, sliders = [], []
    for o, d in zip(ctx.objs, descs):
        if d == KEEP or d[0] == 'add': continue
        if d == DEL:
            for y, x in o.cells: out[y][x] = bg
            continue
        vx, t, cx, copy = d
        if vx == ZERO and t == 'id':
            if cx == 'same': continue
            for (y, x), c in zip(o.cells, o.cols):
                nc = cx_colour(ctx, o, cx, c)
                if nc is None: return None
                out[y][x] = nc
            continue
        if vx[0] == 'slide':
            dd = ctx.slide_dir(o, vx[1])
            if dd is None: return None
            sliders.append((o, t, cx, copy, dd, vx[2]))
        else:
            off = ctx.vx_offset(o, t, vx)
            if off is None: return None
            static.append((o, t, cx, copy, off))
    for item in static + sliders:
        if not item[3]:
            for y, x in item[0].cells: out[y][x] = bg
    adds = [(o, d) for o, d in zip(ctx.objs, descs) if d[0] == 'add']

    def put(o, t, cx, off):
        cells, nh, nw, ay, ax = o.patch(t)
        for dy, dx, c in cells:
            y, x = ay + off[0] + dy, ax + off[1] + dx
            if not (0 <= y < ctx.h and 0 <= x < ctx.w): continue
            nc = cx_colour(ctx, o, cx, c)
            if nc is None: return False
            if paint == 'over' or out[y][x] == bg: out[y][x] = nc
        return True
    for o, t, cx, copy, off in static:
        if not put(o, t, cx, off): return None

    # sliding objects: each direction group moves on its own copy of the canvas (objects moving in different
    # directions pass each other); within a group the leading object moves first and the others stack on it
    groups = {}
    for item in sliders: groups.setdefault(item[4], []).append(item)
    base = [r[:] for r in out]; paints = []
    for dd in DIR8:
        if dd not in groups: continue
        sy, sx = DIR8[dd]
        cv = [r[:] for r in base]
        for o, t, cx, copy, _, stop in sorted(groups[dd], key=lambda it: -max(y * sy + x * sx for y, x in it[0].cells)):
            cells, nh, nw, ay, ax = o.patch(t)
            abs_cells = [(ay + dy, ax + dx) for dy, dx, _ in cells]
            k = canvas_slide(cv, bg, abs_cells, sy, sx, stop)
            if k is None: return None
            for dy, dx, c in cells:
                y, x = ay + k * sy + dy, ax + k * sx + dx
                if not (0 <= y < ctx.h and 0 <= x < ctx.w): continue
                nc = cx_colour(ctx, o, cx, c)
                if nc is None: return None
                cv[y][x] = nc; paints.append((y, x, nc))
    for y, x, nc in paints:
        if paint == 'over' or out[y][x] == bg: out[y][x] = nc
    for o, (_, kind, param, cx) in adds:
        for (y, x), c in created(ctx, o, kind, param).items():
            nc = cx_colour(ctx, o, cx, c)
            if nc is None: return None
            if paint == 'over' or out[y][x] == bg: out[y][x] = nc
    return out


def assign(feats, rules):
    res = []
    for f in feats:
        for p, d in rules:
            if pred_eval(p, f): res.append(d); break
        else:
            return None
    return res


def fmt_pred(p):
    if p[0] == 'true': return 'else'
    s = f"{p[0]}={p[1]!r}" if p[1] is not None else p[0]
    return ('not ' + s) if len(p) > 2 else s


def fmt_desc(d):
    if d == KEEP: return 'keep'
    if d == DEL: return 'delete'
    if d[0] == 'add':
        cx = d[3]
        return f"add:{d[1]}:{d[2]}" + ('' if cx == 'same' else '|colour=' + ','.join(str(v) for v in cx))
    vx, t, cx, copy = d
    s = ('copy' if copy else 'move') + ':' + ','.join(str(v) for v in vx)
    if vx == ZERO: s = 'inplace'
    if t != 'id': s += '|' + t
    if cx != 'same':
        if cx[0] == 'tab': s += f'|colour=table[{cx[1]}:{len(cx[2])}]'
        else: s += '|colour=' + ','.join(str(v) for v in cx)
    return s


def fmt_rules(seg, rules, paint):
    s = seg[0] + ('' if seg[1] is None else f',bg{seg[1]}')
    return f"objmap[{s},{paint}]: " + ' ; '.join(f"{fmt_pred(p)} -> {fmt_desc(d)}" for p, d in rules)


# ============================================================ learning driver

def grid_bg(g, bgc):
    """Background of a grid: the task-level colour bgc when given and present, else the most common colour."""
    if bgc is not None and any(bgc in r for r in g): return bgc
    return gdsl.bg_of(g)


def same_shape_task(train):
    return all(len(p['input']) == len(p['output']) and len(p['input'][0]) == len(p['output'][0]) for p in train)


def seg_signature(ctxs):
    return tuple(tuple(sorted(tuple(o.cells) for o in c.objs)) for c in ctxs)


def add_tables(ctxs, outs, objs_all, descs_all):
    """Lookup-table recolours: output colour of the (in-place, uniformly coloured) object as a function of one
    shape feature, induced from all objects; added to the descriptor sets of the objects it explains."""
    outc = []
    for pi, o in objs_all:
        O = outs[pi]; cs = {O[y][x] for y, x in o.cells}
        c = cs.pop() if len(cs) == 1 else None
        outc.append(c if c is not None and c != ctxs[pi].bg else None)
    if sum(1 for c in outc if c is not None) < 3: return
    for F in TAB_FEATS:
        groups = {}
        for j, (pi, o) in enumerate(objs_all):
            if outc[j] is None: continue
            groups.setdefault(ctxs[pi].feat(o)[F], Counter())[outc[j]] += 1
        table = {v: next(iter(cnt)) for v, cnt in groups.items() if len(cnt) == 1}
        if len(table) < 2 or len(set(table.values())) < 2: continue
        expl = [j for j, (pi, o) in enumerate(objs_all) if outc[j] is not None and table.get(ctxs[pi].feat(o)[F]) == outc[j]]
        if len(expl) < (len(table) + 2 if len(table) <= 3 else 2 * len(table)): continue
        cx = ('tab', F, tuple(sorted(table.items(), key=repr)))
        d = (ZERO, 'id', cx, False)
        for j in expl:
            pi, o = objs_all[j]
            descs_all[j].add(d, sum(1 for c in o.cols if c != outc[j]))


def learn_objmap(ins, outs, tests, budget, segs=SEGS, max_objs=40, allow_over=None, tag='', near=None):
    """Core learner on (input, output) grids of equal size.  Returns list of (cost, program, preds).
    near (list or None): collects near misses -- object maps that render every pair and only change cells to
    their output value (progress), for a residual last step: (cost, rules, seg, paint, renders).
    budget: work budget (checked between segmentations, objects, rule lists and variants; all work charged)."""
    found = []
    npairs = len(ins)
    budget.spend(W_CALL + W_CALL_A * sum(len(g) * len(g[0]) for g in ins))
    # a whole-grid dihedral transform or a global colour map is not an object map (the library owns those)
    for f in gdsl.D8.values():
        if all(f(i) == o for i, o in zip(ins, outs)): return found
    m = gdsl.fit_cmap(ins, outs)
    if m and all(gdsl.apply_cmap(i, m) == o for i, o in zip(ins, outs)): return found
    cons = conservation(list(zip(ins, outs)))
    if cons == 'rearrange':
        allow = {'del': False, 'recolour': False, 'copy': False, 'move': True, 'tx': True}
    elif cons == 'recolour':
        allow = {'del': False, 'recolour': True, 'copy': False, 'move': True, 'tx': True}
    elif cons == 'delete':
        allow = {'del': True, 'recolour': True, 'copy': False, 'move': True, 'tx': True}
    else:
        allow = {'del': True, 'recolour': True, 'copy': True, 'move': True, 'tx': True}
    if allow_over: allow.update(allow_over)
    seen_sig = set()
    colours = sorted({v for g in ins for r in g for v in r} - {gdsl.bg_of(g) for g in ins})
    tot = Counter(v for g in ins for r in g for v in r)
    tbg = max((c for c in tot if all(any(c in r for r in g) for g in ins)), key=lambda c: tot[c], default=None)
    bgmodes = [None] + ([tbg] if tbg is not None and any(gdsl.bg_of(g) != tbg for g in ins) else [])
    allow['add'] = add_kinds(colours) if cons in ('create', 'mixed') and allow.get('add', True) else None
    train_cols = set()
    for bgc, seg in [(b, s) for b in bgmodes for s in segs]:
        if budget.over(): break
        budget.spend(W_CTX)
        ctxs = [Ctx(g, grid_bg(g, bgc), seg, budget) for g in ins]
        if any(len(c.objs) == 0 or len(c.objs) > max_objs for c in ctxs): continue
        sig = (seg_signature(ctxs), seg_signature([Ctx(g, grid_bg(g, bgc), seg, budget) for g in tests]))
        if sig in seen_sig: continue
        seen_sig.add(sig)
        budget.spend(W_SEG + W_SEG_OBJ * sum(len(c.objs) for c in ctxs))
        Oidxs = [out_index(O) for O in outs]
        # does any object move / need a D8 transform?
        need_move = False; need_tx = False; cc = Counter(); ntx = 0
        for c, O, Oi in zip(ctxs, outs, Oidxs):
            for o in c.objs:
                pl = placements(o, 'id', O, Oi)
                if pl - {(0, 0)}:
                    need_move = True
                    if len(pl) <= 3:
                        for off in pl - {(0, 0)}: cc[off] += 1
                elif allow['recolour'] and (0, 0) not in pl and len({O[y][x] for y, x in o.cells}) > 1:
                    need_move = True
                if allow['tx'] and (0, 0) not in pl and o.size > 1:
                    base = o.patch('id')[0]
                    for t in TXS[1:]:
                        ntx += 1
                        if o.patch(t)[0] != base and placements(o, t, O, Oi):
                            need_tx = True; need_move = True; break
        budget.spend(W_NM * sum(len(c.objs) for c in ctxs) + W_NM_TX * ntx)
        consts = [off for off, n in cc.most_common(8)]
        al = dict(allow); al['tx'] = need_tx; al['move'] = allow['move'] and need_move
        svocab = static_vocab(colours) if al['move'] else []
        lvocab = slide_vocab(colours) if al['move'] else []
        objs_all = []; descs_all = []; nbad = 0
        # changed objects first: the vector expressions they use bound the work on unchanged objects
        order = []
        for pi, (c, O) in enumerate(zip(ctxs, outs)):
            for o in c.objs:
                kp = all(O[y][x] == v for (y, x), v in zip(o.cells, o.cols))
                order.append((kp, pi, o))
        used = set(); dsmap = {}
        for kp, pi, o in sorted(order, key=lambda r: r[0]):
            c, O, Oi = ctxs[pi], outs[pi], Oidxs[pi]
            ds = object_descs(c, O, Oi, o, svocab, lvocab, consts, al, used if kp else None, budget)
            if not kp:
                for d in ds:
                    if len(d) == 4 and d[0] != 'add': used.add((d[0], d[1]))
            if not ds:
                nbad += 1
                if DIAG is None: break
            dsmap[(pi, o.i)] = ds
            if budget.over(): break
        for pi, c in enumerate(ctxs):
            for o in c.objs:
                if (pi, o.i) in dsmap:
                    objs_all.append((pi, o)); descs_all.append(dsmap[(pi, o.i)])
        if not nbad and not budget.over() and allow['recolour']:
            add_tables(ctxs, outs, objs_all, descs_all)
        if not nbad and allow['add']:
            # creation actions that create nothing on an unchanged object are vacuously consistent
            adds = sorted({d for ds in descs_all for d in ds if d[0] == 'add'}, key=repr)   # hash-seed independent
            for (pi, o), ds in zip(objs_all, descs_all):
                if KEEP not in ds: continue
                for d in adds:
                    if d not in ds and not created(ctxs[pi], o, d[1], d[2]): ds.add(d)
        if DIAG is not None:
            DIAG.setdefault('segs', {})[seg] = {'unexpl': nbad, 'n': len(descs_all)}
        if nbad or budget.over(): continue
        budget.spend(sum(W_FEAT * len(c.objs) + W_FEAT2 * len(c.objs) ** 2 for c in ctxs))
        feats_by_pair = [[c.feat(o) for o in c.objs] for c in ctxs]
        feats_all = [f for fl in feats_by_pair for f in fl]
        pair_of = [pi for pi, _ in objs_all]
        n = len(objs_all)
        dmask = {}; dgain = Counter()
        for j, ds in enumerate(descs_all):
            for d, gn in ds.items():
                dmask[d] = dmask.get(d, 0) | (1 << j); dgain[d] += gn
        pmask = {}
        preds_all = build_preds(feats_all)
        budget.spend(W_PM * len(preds_all) * len(feats_all))
        for p in preds_all:
            m = 0
            for j, f in enumerate(feats_all):
                if pred_eval(p, f): m |= 1 << j
            if m: pmask[p] = m
        budget.spend(W_LL + W_LL_D * len(dmask) + W_LL_P * len(pmask))
        lists, bymask = learn_lists(n, dmask, pmask, dgain, budget=budget)
        if DIAG is not None: DIAG['segs'][seg]['lists'] = len(lists)
        test_ctxs = None; tried = set()
        for struct in lists:
            if budget.over(): break
            budget.spend(W_STRUCT + W_STRUCT_P * len(pmask) * len(struct))
            # variants: cheapest predicate / descriptor per rule first, then single substitutions by
            # alternatives with the same training support (they may differ on the test inputs)
            base = [(p, bymask[m][0]) for p, m, R in struct]
            variants = [base]
            for r, (p, m, R) in enumerate(struct):
                for alt in bymask[m][1:3]:
                    v = list(base); v[r] = (p, alt); variants.append(v)
                if p[0] != 'true':
                    cov = pmask[p] & R
                    alts = sorted((q for q, qm in pmask.items() if q != p and q[0] != 'true' and qm & R == cov),
                                  key=pred_cost)[:2]
                    for q in alts:
                        v = list(base); v[r] = (q, base[r][1]); variants.append(v)
            nok = 0
            for rules in variants:
                key = tuple(rules)
                if key in tried: continue
                tried.add(key)
                if budget.over(): break
                budget.spend(W_VAR + W_VAR_F * len(feats_all) * len(rules))
                # MDL acceptance: every rule fires in >= 2 pairs or on >= 2 objects
                fires = [set() for _ in rules]; nf = [0] * len(rules); colsets = [set() for _ in rules]
                for j, f in enumerate(feats_all):
                    for r, (p, d) in enumerate(rules):
                        if pred_eval(p, f):
                            fires[r].add(pair_of[j]); nf[r] += 1; colsets[r].add(f['col']); break
                if any(len(fs) < 2 and k < 2 for fs, k in zip(fires, nf)) and npairs >= 2: break
                # longer lists: every rule must be supported by at least two training pairs
                if len(rules) >= 4 and npairs >= 2 and any(len(fs) < 2 for fs in fires): continue
                # a lookup table must be supported by at least two objects per entry among those its rule covers
                if any(len(d) == 4 and isinstance(d[2], tuple) and d[2][0] == 'tab' and
                       k < (len(d[2][2]) + 2 if len(d[2][2]) <= 3 else 2 * len(d[2][2]))
                       for (p, d), k in zip(rules, nf)): continue
                for paint in ('over', 'under'):
                    good = True; rends = []
                    budget.spend(W_PAINT)
                    for c, O, fl in zip(ctxs, outs, feats_by_pair):
                        ds = assign(fl, rules)
                        budget.spend(W_REND + W_REND_A * c.h * c.w + W_REND_O * len(c.objs))
                        r = render(c, ds, paint) if ds is not None else None
                        rends.append(r)
                        if r != O:
                            good = False
                            if near is None or r is None: break
                    if not good:
                        if near is not None and len(rends) == npairs and all(r is not None for r in rends):
                            budget.spend(W_NEAR_A * sum(len(O) * len(O[0]) for O in outs))
                            prog = all(r[y][x] == O[y][x] for r, g, O in zip(rends, ins, outs)
                                       for y in range(len(O)) for x in range(len(O[0])) if r[y][x] != g[y][x])
                            # the object map must do a real share of the work (>= 10% of the changed cells)
                            prog = prog and all(10 * sum(1 for ra, ga in zip(r, g) for a, b in zip(ra, ga) if a != b) >=
                                                sum(1 for ga, oa in zip(g, O) for a, b in zip(ga, oa) if a != b)
                                                for r, g, O in zip(rends, ins, outs))
                            if prog:
                                cost = sum(pred_cost(p) + desc_cost(d) for p, d in rules) + 1.0 * len(rules)
                                near.append((cost, rules, (seg, bgc), paint, rends))
                        continue
                    if test_ctxs is None:
                        test_ctxs = [Ctx(g, grid_bg(g, bgc), seg, budget) for g in tests]
                        budget.spend(sum(W_FEAT * len(c.objs) + W_FEAT2 * len(c.objs) ** 2 for c in test_ctxs))
                        test_feats = [[c.feat(o) for o in c.objs] for c in test_ctxs]
                        train_cols = {f['col'] for f in feats_all}
                        # segmentation plausibility on the test inputs: objects outside the training size range
                        lo = min(f['size'] for f in feats_all); hi = max(f['size'] for f in feats_all)
                        odd = sum(1 for fl in test_feats for f in fl if f['size'] < lo or f['size'] > hi)
                        seg_pen = 0.6 * odd
                    uses_col = any(p[0] == 'col' for p, d in rules)
                    preds_t = []
                    for c, fl in zip(test_ctxs, test_feats):
                        ds = assign(fl, rules)
                        if ds is None: break
                        if uses_col:
                            bad = False
                            for f in fl:
                                if f['col'] in train_cols: continue
                                for r, (p, d) in enumerate(rules):
                                    if pred_eval(p, f):
                                        if len(colsets[r]) < 2: bad = True
                                        break
                            if bad: break
                        budget.spend(W_REND + W_REND_A * c.h * c.w + W_REND_O * len(c.objs))
                        r = render(c, ds, paint)
                        if r is None: break
                        preds_t.append(r)
                    if len(preds_t) != len(tests): continue
                    cost = sum(pred_cost(p) + desc_cost(d) for p, d in rules) + 1.0 * len(rules) + SEGS.index(seg) * 0.05 + seg_pen
                    found.append((cost + (0.3 if bgc is not None else 0), tag + fmt_rules((seg, bgc), rules, paint), preds_t))
                    nok += 1
                    break
    return found


OLD_FAMS_SKIP = ('fam_codex', 'fam_recolour_by_property')


def first_steps(train):
    """Output-independent programs of the original G-DSL families (usable as a FIRST step)."""
    out = []
    for fam in gdsl.FAMILIES:
        if getattr(fam, '__module__', '') != 'gdsl' or fam.__name__ in OLD_FAMS_SKIP: continue
        try:
            out.extend(fam(train))
        except Exception:
            continue
    out = out + list(gdsl.compose_dihedral(out))
    out.sort(key=lambda x: x[1])
    return out


def agree(a, b):
    return sum(1 for ra, rb in zip(a, b) for x, y in zip(ra, rb) if x == y)


def compose_first(task, budget, max_steps=16):
    """library first step (output-independent) -> object map learned on (step(input), output).
    Candidate steps are ranked by their agreement with the outputs (same-size tasks) and cost."""
    train = task['train']; tests = [t['input'] for t in task['test']]
    outs = [p['output'] for p in train]; ins = [p['input'] for p in train]
    same = same_shape_task(train)
    base = sum(agree(i, o) for i, o in zip(ins, outs)) if same else 0
    cands = []; seen = set()
    steps = first_steps(train)
    budget.spend(W_FS_GEN + W_FS_PROG * len(steps))
    for name, cost, fn in steps:
        if budget.left() < 3 * WU_S: break
        if name.startswith('dihedral:'): continue      # a whole-grid rotation is not a first step for objects
        mids = []
        for p, O in zip(ins, outs):
            budget.spend(W_RUN + W_RUN_A * len(p) * len(p[0]))
            r = gdsl.run(fn, p)
            if r is None or len(r) != len(O) or len(r[0]) != len(O[0]): mids = None; break
            mids.append(r)
        if mids is None or mids == outs: continue
        if same and all(m == i for m, i in zip(mids, ins)): continue
        k = repr(mids)
        if k in seen: continue
        seen.add(k)
        score = sum(agree(m, o) for m, o in zip(mids, outs)) - base
        cands.append((-score, cost, name, fn, mids))
    cands.sort(key=lambda c: (c[0], c[1]))
    found = []; n = 0
    for _, cost, name, fn, mids in cands:
        if budget.left() < 2 * WU_S or n >= max_steps: break
        budget.spend(sum(W_RUN + W_RUN_A * len(t) * len(t[0]) for t in tests))
        tm = [gdsl.run(fn, t) for t in tests]
        if any(t is None for t in tm): continue
        # first step followed by a whole-grid dihedral transform (two library steps).  The library already
        # composes its reshapers with every D8 element, so that case would only duplicate a library program.
        if not name.startswith(gdsl.RESHAPERS):
            for dk, f in gdsl.D8.items():
                if dk != 'id' and all(f(m) == o for m, o in zip(mids, outs)):
                    found.append((cost + 2.0, f"{name} ; dihedral:{dk}", [f(t) for t in tm]))
            if found: break
        n += 1
        sub = Budget(min(budget.left() - WU_S, 2 * WU_S), budget)
        for c, prog, preds in learn_objmap(mids, outs, tm, sub, segs=('c4', 'c8', 'm8'), tag=name + ' ; '):
            found.append((c + cost + 1.0, prog, preds))
        if found: break
    return found


def lib_candidates(train):
    """gdsl.candidates(train) restricted to the families with a deterministic internal work bound (LIB_SKIP
    excluded; same program order and costs otherwise)."""
    out = []
    for fam in gdsl.FAMILIES:
        if fam.__name__ in LIB_SKIP: continue
        try:
            out.extend(fam(train))
        except Exception:
            continue
    out = out + list(gdsl.compose_dihedral(out))
    out.sort(key=lambda x: x[1])
    return out


def lib_search(task, budget, max_programs=6):
    """gdsl.search(task, max_programs, allow2=False) bounded by WORK instead of time: the library's candidate
    programs (lib_candidates) are consumed in their own (cost) order, at most LIB_MAX_PROGS of them and only while
    the budget lasts; generating the candidates and applying a program to a pair are charged.  Identical to
    gdsl.search over those families whenever neither bound binds."""
    train = task['train']; outs = [p['output'] for p in train]
    found = []
    ident = [p['input'] for p in train]
    m = gdsl.fit_cmap(ident, outs)
    if m and any(k != v for k, v in m.items()) and all(gdsl.apply_cmap(a, m) == b for a, b in zip(ident, outs)):
        found.append(("colour-map", 1, lambda g, m=m: gdsl.apply_cmap(g, m)))
    area = sum(len(p['input']) * len(p['input'][0]) for p in train)
    cands = lib_candidates(train)
    budget.spend(W_LIB_GEN + W_LIB_GEN_A * area + W_LIB_PROG * len(cands))
    for name, cost, fn in cands[:LIB_MAX_PROGS]:
        if budget.over(): break
        preds = []
        for p, o in zip(train, outs):
            budget.spend(W_RUN + W_RUN_A * len(p['input']) * len(p['input'][0]))
            r = gdsl.run(fn, p["input"])
            if r is None or len(r) != len(o) or len(r[0]) != len(o[0]): preds = None; break
            if not preds and gdsl.fit_cmap([r], [o]) is None: preds = None; break
            preds.append(r)
        if not preds: continue
        if preds == outs:
            found.append((name, cost, fn))
        else:
            m = gdsl.fit_cmap(preds, outs)
            if m and all(gdsl.apply_cmap(a, m) == b for a, b in zip(preds, outs)):
                found.append((name + "+colour-map", cost + 1, lambda g, fn=fn, m=m: gdsl.apply_cmap(gdsl.run(fn, g), m)))
        if len(found) >= max_programs: break
    res, seen = [], set()
    for name, cost, fn in sorted(found, key=lambda x: x[1]):
        preds = [gdsl.run(fn, t["input"]) for t in task["test"]]
        if any(p is None for p in preds): continue
        k = str(preds)
        if k in seen: continue
        seen.add(k); res.append({"program": name, "cost": cost, "preds": preds})
    return res


def compose_last(task, near, budget, k=2, lib=True):
    """object map (near miss: progress on every pair) -> a LAST step learned on the residual pairs
    (rendered, output): first a second object map (cheap), then the library search."""
    train = task['train']; tests = [t['input'] for t in task['test']]
    outs = [p['output'] for p in train]
    found = []; done = []
    for cost, rules, seg, paint, rends in sorted(near, key=lambda r: r[0]):
        if budget.left() < 3 * WU_S or len(done) >= k: break
        if len(rules) > 2: continue
        key = repr(rends)
        if key in done: continue
        done.append(key)
        tr = []
        for g in tests:
            c = Ctx(g, grid_bg(g, seg[1]), seg[0], budget)
            budget.spend(W_FEAT * len(c.objs) + W_FEAT2 * len(c.objs) ** 2 + W_REND + W_REND_A * c.h * c.w +
                         W_REND_O * len(c.objs))
            ds = assign([c.feat(o) for o in c.objs], rules)
            r = render(c, ds, paint) if ds is not None else None
            if r is None: tr = None; break
            tr.append(r)
        if tr is None: continue
        head = fmt_rules(seg, rules, paint)
        sub_b = Budget(min(3 * WU_S, budget.left() - WU_S), budget)
        for c2, prog2, preds2 in learn_objmap(rends, outs, tr, sub_b):
            if prog2.count(' -> ') + len(rules) > 3: continue     # two object maps: at most 3 rules in all
            found.append((cost + c2 + 1.0, head + ' ; ' + prog2, preds2))
        if found or not lib or budget.left() < 7 * WU_S: continue
        sub = {'train': [{'input': r, 'output': O} for r, O in zip(rends, outs)], 'test': [{'input': r} for r in tr]}
        try:
            res = lib_search(sub, budget, max_programs=2)
        except Exception:
            res = []
        for r in res:
            if r['program'].startswith('codex'): continue        # library programs of our own families only
            found.append((cost + r.get('cost', 3) + 2.0, head + ' ; ' + r['program'], r['preds']))
    return found


def SEARCH(task, budget_s=15.0, compose=True):
    """budget_s: work budget in reference-CPU seconds (WU_S work units each); deterministic, no clock."""
    budget = Budget(budget_s * WU_S)
    train = task['train']; tests = [t['input'] for t in task['test']]
    res = []; near = []
    same = same_shape_task(train)
    # defer to the library when a whole-grid dihedral transform already explains every pair
    for k, f in gdsl.D8.items():
        if all(f(p['input']) == p['output'] for p in train): return []
    m = gdsl.fit_cmap([p['input'] for p in train], [p['output'] for p in train])
    if m and all(gdsl.apply_cmap(p['input'], m) == p['output'] for p in train): return []
    if same:
        ins = [p['input'] for p in train]; outs = [p['output'] for p in train]
        res = learn_objmap(ins, outs, tests, budget, near=near)
    if compose and not res and budget.left() > 4 * WU_S:
        res = compose_first(task, budget)
    if compose and not res and near and budget.left() > 3 * WU_S:
        res = compose_last(task, near, budget)
    res.sort(key=lambda r: r[0])
    out, seen = [], set()
    for cost, prog, preds in res:
        k = repr(preds)
        if k in seen: continue
        seen.add(k); out.append({'program': prog, 'preds': preds})
        if len(out) >= 3: break
    return out
