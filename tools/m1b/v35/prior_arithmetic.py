"""ARITHMETIC prior: foundational arithmetic and set theory on the cell lattice.

Laws (the prior, stated before looking for tasks)
-------------------------------------------------
Z    The grid is a finite piece of Z x Z.  Every cell has integer coordinates; every item (object, line,
     band, panel, cell of a class) has integer attributes (position, extent, size, count) and an ORDINAL
     index in any total order of its kind.  Offsets u = coordinate - anchor are integers.
===  CONGRUENCE.  A periodic pattern is a function of the residue class of an offset: 1-D u mod k, diagonal
     (uy + ux) mod k, 2-D (uy mod ky, ux mod kx), or a general translation lattice <(p, s), (0, q)>.
     Parity is the case k = 2.  A class is either coloured by a table (colouring) or carries one colour
     that fills its unknown members (completion / continuation).
<    ORDER.  Integers are compared: sign(u) (before / at / after an anchor), the midpoint comparison
     sign(2u - L) (halves), thresholds (size >= t), ranks (ordinal index), and a total order on colours
     that resolves conflicts (priority).
+ *  COUNTING ARITHMETIC.  Multiplicities (scale factor, tile count) are affine a*n + b of a count n of the
     input; parallel bar lengths form arithmetic progressions L + a*d in the offset d from a seed bar.
|    DIVISIBILITY.  A side divisible by k gives a quotient window (side / k, or the minimal period p | side);
     the parity of the side can select which window.
S    SET ALGEBRA.  Panels (separator lattice, N x M blocks, overlapping corner windows) are sets of coloured
     cells: union with an induced colour order, any function of the MEMBERSHIP COUNT (intersection = all,
     union = any, symmetric difference = odd / exactly one, complement = none, consensus = n / n-1), and
     the complement (figure <-> ground) of a 2-colour grid.
AFF  Affine maps of offsets: every line (row / column) is translated by s(u) = a*u (shear) or by a periodic
     sequence s(u) = S[u mod k], u the line offset from an anchor line.

Families (all parameters induced from the training pairs; unseen keys / counts at test time -> None)
------------------------------------------------------------------------------------------------------
arith-residue[feature,class]  out(p) = F(class(p), phi(p)); class = input colour | figure/ground; F a table
        (class, phi) -> keep | literal colour | anchor colour (seed / object / the grid's figure colour).
        phi: grid-anchored u mod k (either edge, k = 2..12), (uy+ux) mod k from a corner, 2-D residues, grid
        half; object-anchored residues, halves, ordinal index mod k or rank (left/right/top/bottom), size
        parity and size threshold (4|8-conn, mono|multi colour); seed-anchored (the unique singleton-colour
        cell) lattices, diagonals, quadrants, half-plane x residue; ranks / residues of occupied lines,
        bands of identical lines, scan order of figure cells.  Guards: phi must matter (a class takes >= 2
        actions), >= 2 cells per key, every change rule recurs, >= 1.5 periods observed, periodic ordinals
        wrap, rank tables are palettes (injective).
arith-shift            each row / column translated by a*u or S[u mod k] from an anchor line (grid edge, figure
                       top/bottom); cyclic, padded, or on a widened canvas (fill colour induced); or a constant
                       cyclic shift whose amount is the index (a count) of a marker in removed border line(s).
arith-count-scale      output = upscale / tile (k x k, 1 x k, k x 1) of the grid or its figure bbox with
                       k = a*n + b, n a count (colours, cells of a colour, objects, figure cells, rarest colour).
arith-union            panels combined by colour-order union or by a membership-count table.
arith-progression      bars parallel to a seed bar with lengths L + a_side*d, colour by (side, d mod m).
arith-congruence       unknown cells (ground / occluder colour) filled from the smallest consistent lattice,
                       output the grid or the occluded window; or the input continued onto a larger canvas.
arith-complement       figure <-> ground swap, then identity / tiling / Kronecker placement at figure|ground.
arith-window           quotient window: constant size, side / k, or minimal period, at a fixed corner or the
                       corner selected by the parity of the grid size.

Measured (eval_fam, 1000 training + 50 half-A): 83 exact, WRONG 0; per family union 33, residue 21, shift 7,
congruence 7, window 5, count-scale 4, complement 3, progression 3.  Dropped / guarded after measurement:
height/width thresholds and parities (coincidental fits, no new solves), 1-cell windows and 1x1 corner
panels (coincidences), non-injective rank tables (over-fired), literal-vs-anchor ambiguity (resolved per class).
Seed-distance and bbox-ring residues solve nothing yet but never fire falsely; kept as part of the law.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import product
import numpy as np
from scipy import ndimage
from gdsl import H, W, bg_of

S4 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
S8 = np.ones((3, 3), dtype=int)
SEGS = ((4, True), (8, True), (4, False), (8, False))


def A(g):
    return np.asarray(g, dtype=np.int64)


def same_shape(train):
    return all(np.shape(p['input']) == np.shape(p['output']) for p in train)


# ------------------------------------------------------------------ segmentation
def label(a, bg, conn, mono):
    """Connected components of non-bg cells: label array (-1 = bg) and count."""
    st = S4 if conn == 4 else S8
    lab = -np.ones(a.shape, dtype=np.int64)
    if mono:
        n = 0
        for c in np.unique(a):
            if c == bg: continue
            l, m = ndimage.label(a == c, structure=st)
            lab[l > 0] = l[l > 0] - 1 + n
            n += m
        return lab, n
    l, m = ndimage.label(a != bg, structure=st)
    return l - 1, m


def boxes(lab, n):
    """(top, left, bottom, right) arrays per label."""
    t = np.zeros(n, dtype=np.int64); l = np.zeros(n, dtype=np.int64)
    b = np.zeros(n, dtype=np.int64); r = np.zeros(n, dtype=np.int64)
    for k, sl in enumerate(ndimage.find_objects(lab + 1)):
        if sl is None: continue
        t[k], b[k] = sl[0].start, sl[0].stop - 1
        l[k], r[k] = sl[1].start, sl[1].stop - 1
    return t, l, b, r


class Ctx:
    """Per-grid cache of arrays used by the features."""
    def __init__(self, g, bg=None):
        self.a = A(g); self.bg = bg_of(g) if bg is None or not np.any(self.a == bg) else bg
        self.h, self.w = self.a.shape
        self.Y, self.X = np.indices(self.a.shape)
        self.fg = self.a != self.bg
        self._seg = {}

    def seg(self, key):
        if key not in self._seg:
            lab, n = label(self.a, self.bg, *key)
            self._seg[key] = (lab, n, boxes(lab, n))
        return self._seg[key]

    def seed(self):
        """The unique cell whose colour occurs exactly once (the origin of a seed-anchored pattern)."""
        if not hasattr(self, '_seed'):
            vals, cnt = np.unique(self.a, return_counts=True)
            one = [int(v) for v, n in zip(vals, cnt) if n == 1 and v != self.bg]
            if len(one) != 1: self._seed = None
            else:
                ys, xs = np.nonzero(self.a == one[0])
                self._seed = (int(ys[0]), int(xs[0]), one[0])
        return self._seed


# ------------------------------------------------------------------ residue / order features
def _u(c, axis, anchor, lo=None, hi=None):
    """Offset of every cell along axis from an anchor edge (grid, or per-cell bounds lo/hi)."""
    P = c.Y if axis == 'y' else c.X
    if lo is None:
        n = c.h if axis == 'y' else c.w
        return P if anchor == 0 else n - 1 - P
    return P - lo if anchor == 0 else hi - P


def _rank(vals):
    """Dense rank of distinct values; None on ties."""
    if len(set(vals)) != len(vals): return None
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    r = [0] * len(vals)
    for k, i in enumerate(order): r[i] = k
    return r


def feature(c, spec):
    """Integer feature per cell (-1 = undefined) or None when not computable (memoised per grid)."""
    key = ('feat',) + spec
    if key not in c._seg: c._seg[key] = _feature(c, spec)
    return c._seg[key]


def _feature(c, spec):
    kind = spec[0]
    if kind == 'g':                                    # ('g', axis, anchor, k)
        _, axis, an, k = spec
        return _u(c, axis, an) % k
    if kind == 'gd':                                   # ('gd', ay, ax, k)
        _, ay, ax, k = spec
        return (_u(c, 'y', ay) + _u(c, 'x', ax)) % k
    if kind == 'g2':                                   # ('g2', ay, ax, ky, kx)
        _, ay, ax, ky, kx = spec
        return (_u(c, 'y', ay) % ky) * kx + _u(c, 'x', ax) % kx
    if kind == 'gh':                                   # ('gh', axis)
        P, n = (c.Y, c.h) if spec[1] == 'y' else (c.X, c.w)
        return np.sign(2 * P - (n - 1)) + 1
    if kind in ('op', 'ot'):                           # ('op', seg, prop, k) | ('ot', seg, prop, t)
        _, seg, prop, k = spec
        lab, n, _ = c.seg(seg)
        if n == 0: return None
        vals = obj_prop(c, seg, prop)
        per = (vals % k) if kind == 'op' else (vals >= k).astype(np.int64)
        return np.where(lab >= 0, per[np.where(lab >= 0, lab, 0)], -1)
    if kind in ('o', 'od', 'oh', 'on'):
        seg = spec[1]
        lab, n, (t, l, b, r) = c.seg(seg)
        if n == 0: return None
        m = lab >= 0; L = np.where(m, lab, 0)
        T_, L_, B_, R_ = t[L], l[L], b[L], r[L]
        if kind == 'o':                                # ('o', seg, axis, anchor, k)
            _, _, axis, an, k = spec
            lo, hi = (T_, B_) if axis == 'y' else (L_, R_)
            f = _u(c, axis, an, lo, hi) % k
        elif kind == 'od':                             # ('od', seg, ay, ax, k)
            _, _, ay, ax, k = spec
            f = (_u(c, 'y', ay, T_, B_) + _u(c, 'x', ax, L_, R_)) % k
        elif kind == 'oh':                             # ('oh', seg, axis)
            f = np.sign(2 * c.Y - (T_ + B_)) + 1 if spec[2] == 'y' else np.sign(2 * c.X - (L_ + R_)) + 1
        else:                                          # ('on', seg, order, k)  k = 0: rank
            _, _, order, k = spec
            key = {'left': list(l), 'right': list(-r), 'top': list(t), 'bottom': list(-b)}[order]
            rk = _rank(key)
            if rk is None: return None
            rk = np.array(rk, dtype=np.int64)
            f = rk[L] if k == 0 else rk[L] % k
        return np.where(m, f, -1)
    if kind == 'rb':                                   # ('rb', seg, k): ring index inside a bbox mod k
        _, seg, k = spec
        lab, n, (t, l, b, r) = c.seg(seg)
        if n == 0: return None
        f = -np.ones(c.a.shape, dtype=np.int64)
        for j in sorted(range(n), key=lambda j: -(b[j] - t[j] + 1) * (r[j] - l[j] + 1)):
            if b[j] - t[j] < 2 or r[j] - l[j] < 2: continue
            Ys, Xs = c.Y[t[j]:b[j] + 1, l[j]:r[j] + 1], c.X[t[j]:b[j] + 1, l[j]:r[j] + 1]
            d = np.minimum(np.minimum(Ys - t[j], b[j] - Ys), np.minimum(Xs - l[j], r[j] - Xs))
            f[t[j]:b[j] + 1, l[j]:r[j] + 1] = d % k
        return f
    if kind == 'sr':                                   # ('sr', metric, k): distance from the seed mod k
        sd = c.seed()
        if sd is None: return None
        dy, dx = np.abs(c.Y - sd[0]), np.abs(c.X - sd[1])
        return (np.maximum(dy, dx) if spec[1] == 'cheb' else dy + dx) % spec[2]
    if kind in ('s2', 'sd', 'sq', 'sqm'):              # seed-anchored offsets dy, dx
        sd = c.seed()
        if sd is None: return None
        dy, dx = c.Y - sd[0], c.X - sd[1]
        if kind == 's2': return (dy % spec[1]) * spec[2] + dx % spec[2]
        if kind == 'sd': return (dy + spec[1] * dx) % spec[2]
        if kind == 'sq': return (np.sign(dy) + 1) * 3 + np.sign(dx) + 1
        _, axis, k = spec                              # half-plane along axis x residue along the other
        d1, d2 = (dy, dx) if axis == 'y' else (dx, dy)
        return (np.sign(d1) + 1) * k + d2 % k
    if kind == 'ln':                                   # ('ln', axis, anchor, k): line rank among fg lines
        _, axis, an, k = spec
        P = c.X if axis == 'x' else c.Y
        occ = sorted(set(P[c.fg].tolist()))
        if not occ: return None
        if an == 1: occ = occ[::-1]
        pos = -np.ones(max(c.h, c.w), dtype=np.int64); pos[occ] = np.arange(len(occ))
        idx = pos[P]
        f = idx if k == 0 else idx % k
        return np.where(c.fg, f, -1)
    if kind == 'bd':                                   # ('bd', axis, anchor, k): band index mod k
        _, axis, an, k = spec
        a = c.a if axis == 'y' else c.a.T
        n = a.shape[0]; bid = np.zeros(n, dtype=np.int64); cur = 0
        for i in range(1, n):
            if not np.array_equal(a[i], a[i - 1]): cur += 1
            bid[i] = cur
        if cur == 0: return None
        if an == 1: bid = cur - bid
        f = (bid % k)[:, None] * np.ones((1, a.shape[1]), dtype=np.int64)
        return f if axis == 'y' else f.T
    if kind == 'sc':                                   # ('sc', order, k): scan index of fg cells mod k
        _, order, k = spec
        ys, xs = np.nonzero(c.fg)
        if len(ys) == 0: return None
        if order == 'strict':
            if len(set(ys.tolist())) == len(ys): order = 'row'
            elif len(set(xs.tolist())) == len(xs): order = 'col'
            else: return None
        idx = np.lexsort((xs, ys)) if order == 'row' else np.lexsort((ys, xs))
        f = -np.ones(c.a.shape, dtype=np.int64)
        f[ys[idx], xs[idx]] = np.arange(len(ys)) % k
        return f
    return None


def obj_prop(c, seg, prop):
    """Integer property per object: size (cells), height, width."""
    key = ('prop', seg, prop)
    if key not in c._seg:
        lab, n, (t, l, b, r) = c.seg(seg)
        if prop == 'size': v = np.bincount(lab[lab >= 0], minlength=n)
        elif prop == 'h': v = b - t + 1
        else: v = r - l + 1
        c._seg[key] = np.asarray(v, dtype=np.int64)
    return c._seg[key]


def extent_ok(spec, ctxs):
    """The period k must be exercised: some training extent n along the axis holds >= 1.5 periods
    (3k <= 2n); on an axis of constant length the raw coordinate (k = n) is allowed."""
    kind = spec[0]
    def per(n, k): return 3 * k <= 2 * n
    def ax_ok(ns, k):
        return per(max(ns), k) or (len(set(ns)) == 1 and k == ns[0])
    if kind == 'g':
        _, axis, _, k = spec
        return per(max((c.h if axis == 'y' else c.w) for c in ctxs), k)
    if kind == 'gd':
        return per(max(c.h + c.w - 1 for c in ctxs), spec[3])
    if kind == 'g2':
        _, _, _, ky, kx = spec
        return ax_ok([c.h for c in ctxs], ky) and ax_ok([c.w for c in ctxs], kx)
    if kind == 'rb':
        ext = 0
        for c in ctxs:
            _, n, (t, l, b, r) = c.seg(spec[1])
            if n: ext = max(ext, int(((np.minimum(b - t, r - l)) // 2 + 1).max()))
        return per(ext, spec[2])
    if kind == 'sr':
        return per(max(max(c.h, c.w) for c in ctxs) // 2, spec[2])
    if kind in ('o', 'od'):
        ext = 0
        for c in ctxs:
            _, n, (t, l, b, r) = c.seg(spec[1])
            if n == 0: continue
            if kind == 'o':
                e = (b - t + 1) if spec[2] == 'y' else (r - l + 1)
            else:
                e = b - t + r - l + 1
            ext = max(ext, int(e.max()))
        return per(ext, spec[-1])
    return True


def feature_specs(train, ctxs):
    """Candidate features, cheapest description first: (level, spec)."""
    hs = [c.h for c in ctxs]; ws = [c.w for c in ctxs]
    out = []
    for axis, n in (('y', max(hs)), ('x', max(ws))):
        for k in range(2, min(12, n - 1) + 1):
            for an in (0, 1):
                out.append((0, ('g', axis, an, k)))
        out.append((0, ('gh', axis)))
    for ay, ax in product((0, 1), (0, 1)):
        for k in range(2, 7):
            out.append((1, ('gd', ay, ax, k)))
    for ay, ax in product((0, 1), (0, 1)):
        for ky in range(2, 5):
            for kx in range(2, 13):
                out.append((2, ('g2', ay, ax, ky, kx)))
                if kx <= 4 and kx != ky:
                    out.append((2, ('g2', ay, ax, kx, ky)))
    for seg in SEGS:
        for axis in ('y', 'x'):
            for an in (0, 1):
                for k in range(2, 5):
                    out.append((1, ('o', seg, axis, an, k)))
            out.append((1, ('oh', seg, axis)))
        for ay, ax in product((0, 1), (0, 1)):
            for k in (2, 3):
                out.append((2, ('od', seg, ay, ax, k)))
        for order in ('left', 'right', 'top', 'bottom'):
            for k in (2, 3, 0):
                out.append((2, ('on', seg, order, k)))
    for axis in ('x', 'y'):
        for an in (0, 1):
            for k in (0, 2, 3):
                out.append((2, ('ln', axis, an, k)))
            for k in (2, 3, 4):
                out.append((2, ('bd', axis, an, k)))
    for order in ('row', 'col', 'strict'):
        for k in (2, 3, 4):
            out.append((2, ('sc', order, k)))
    for seg in SEGS:
        for k in (2, 3, 4):
            out.append((2, ('rb', seg, k)))
    for seg in SEGS:
        for prop in ('size',):
            vals = sorted(set(np.concatenate([obj_prop(c, seg, prop) for c in ctxs]).tolist()))
            if len(vals) < 3: continue
            out.append((1, ('op', seg, prop, 2)))
            for v in vals[:-1]:                        # threshold just above an observed value
                out.append((1, ('ot', seg, prop, v + 1)))
    if all(c.seed() is not None for c in ctxs):
        out.append((1, ('sq',)))
        for ky, kx in product((1, 2, 3), (1, 2, 3)):
            if ky * kx > 1: out.append((1, ('s2', ky, kx)))
        for sg, k in product((1, -1), (2, 3)):
            out.append((1, ('sd', sg, k)))
        for axis, k in product(('y', 'x'), (2, 3)):
            out.append((2, ('sqm', axis, k)))
        for metric, k in product(('cheb', 'manh'), (2, 3, 4)):
            out.append((1, ('sr', metric, k)))
    return out


def anchor_colour(c, spec):
    """Colour of the anchor each cell is measured from (-1 = none): the seed, or a multicolour object's
    majority colour."""
    kind = spec[0]
    if kind in ('s2', 'sd', 'sq', 'sqm', 'sr'):
        return np.full(c.a.shape, c.seed()[2], dtype=np.int64)
    if kind in ('g', 'gd', 'g2', 'gh', 'ln', 'bd', 'sc'):        # the grid's unique figure colour
        if ('fig',) not in c._seg:
            fc = set(np.unique(c.a).tolist()) - {c.bg}
            c._seg[('fig',)] = np.full(c.a.shape, fc.pop() if len(fc) == 1 else -1, dtype=np.int64)
        return c._seg[('fig',)]
    if kind in ('o', 'od', 'oh', 'on', 'op', 'ot') and not spec[1][1]:
        key = ('maj',) + spec[1]
        if key not in c._seg:
            lab, n, _ = c.seg(spec[1])
            m = lab >= 0
            hist = np.zeros((n + 1, 16), dtype=np.int64)
            np.add.at(hist, (lab[m], c.a[m]), 1)
            maj = hist.argmax(axis=1); maj[n] = -1
            c._seg[key] = maj[np.where(m, lab, n)]
        return c._seg[key]
    return None


def fit_table(keys, ins, outs, anc=None):
    """Table key -> literal colour (>= 0), keep (-1) or anchor colour (-2); None if inconsistent.
    A group consistent with both a literal and the anchor colour is resolved per class: anchor when some
    group of the same class needs the anchor, else literal; keep is always preferred."""
    order = np.argsort(keys, kind='stable')
    k = keys[order]; i = ins[order]; o = outs[order]
    starts = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
    omin = np.minimum.reduceat(o, starts); omax = np.maximum.reduceat(o, starts)
    keep = np.minimum.reduceat((o == i).astype(np.int64), starts) == 1
    lit = omin == omax
    if anc is not None:
        an = anc[order]
        ancok = np.minimum.reduceat(((o == an) & (an >= 0)).astype(np.int64), starts) == 1
    else:
        ancok = np.zeros(len(starts), dtype=bool)
    if not np.all(lit | keep | ancok): return None
    kk = k[starts]
    need_anc = {int(x) // KM for x, kp, lt, ao in zip(kk, keep, lit, ancok) if ao and not kp and not lt}
    tab = {}
    for x, kp, lt, ao, v in zip(kk, keep, lit, ancok, omin):
        x = int(x)
        if kp: tab[x] = -1
        elif ao and (not lt or x // KM in need_anc): tab[x] = -2
        else: tab[x] = int(v)
    return tab


KM = 64   # key = class * KM + feature  (features < KM)


def residue_fit(ctxs, outs, spec, cmode):
    keys, ins, os_, ancs = [], [], [], []
    for c, o in zip(ctxs, outs):
        f = feature(c, spec)
        if f is None or f.max() >= KM: return None
        v = f >= 0
        if not np.array_equal(o[~v], c.a[~v]): return None
        cl = c.a if cmode == 'lit' else c.fg.astype(np.int64)
        keys.append((cl * KM + f)[v]); ins.append(c.a[v]); os_.append(o[v])
        an = anchor_colour(c, spec)
        ancs.append(an[v] if an is not None else np.full(int(v.sum()), -1, dtype=np.int64))
    keys = np.concatenate(keys); ins = np.concatenate(ins); os_ = np.concatenate(os_)
    if len(keys) == 0: return None
    tab = fit_table(keys, ins, os_, np.concatenate(ancs))
    if tab is None: return None
    # relevance: some class takes >= 2 different actions over the feature values
    acts = {}
    for kk, v in tab.items(): acts.setdefault(kk // KM, set()).add(v)
    if not any(len(s) > 1 for s in acts.values()): return None
    # it must change something, compress (>= 2 cells per key) and every change rule must recur
    nchg = int(np.sum(ins != os_))
    if nchg == 0: return None
    if 2 * len(tab) > len(keys): return None
    if 2 * sum(1 for v in tab.values() if v != -1) > nchg: return None
    if spec[0] in ('on', 'ln', 'bd', 'sc'):
        k = spec[-1]
        if k > 0:          # a periodic ordinal must wrap around in some pair
            if max(n_items(c, spec) for c in ctxs) <= k: return None
        else:              # a rank table is a palette: distinct ranks of a class get distinct actions
            for cl, s in acts.items():
                vals = [v for kk, v in tab.items() if kk // KM == cl]
                if len(vals) != len(set(vals)): return None
    return tab


def n_items(c, spec):
    kind = spec[0]
    if kind == 'on': return c.seg(spec[1])[1]
    if kind == 'ln':
        P = c.X if spec[1] == 'x' else c.Y
        return len(set(P[c.fg].tolist()))
    if kind == 'bd':
        a = c.a if spec[1] == 'y' else c.a.T
        return 1 + sum(not np.array_equal(a[i], a[i - 1]) for i in range(1, a.shape[0]))
    return int(c.fg.sum())


def residue_apply(g, spec, cmode, tab, bg=None):
    c = Ctx(g, bg)
    f = feature(c, spec)
    if f is None: return None
    out = c.a.copy()
    cl = c.a if cmode == 'lit' else c.fg.astype(np.int64)
    v = f >= 0
    keys = cl * KM + f
    anc = None
    for kk in np.unique(keys[v]).tolist():
        if kk not in tab: return None
        act = tab[kk]
        if act >= 0: out[v & (keys == kk)] = act
        elif act == -2:
            if anc is None: anc = anchor_colour(c, spec)
            m = v & (keys == kk)
            if np.any(anc[m] < 0): return None
            out[m] = anc[m]
    return out.tolist()


def task_bg(train):
    """Background induced over the task: the most frequent colour of all training inputs together, used when
    some input's own majority colour differs (a figure larger than its ground)."""
    tot = Counter(v for p in train for r in p['input'] for v in r)
    b = tot.most_common(1)[0][0]
    if all(bg_of(p['input']) == b for p in train): return None
    if not all(any(b in r for r in p['input']) for p in train): return None
    return b


def fam_arith_residue(train):
    if not same_shape(train): return
    if all(p['input'] == p['output'] for p in train): return
    outs = [A(p['output']) for p in train]
    fits = []
    tb = task_bg(train)
    for bg in (None, tb) if tb is not None else (None,):
        ctxs = [Ctx(p['input'], bg) for p in train]
        for level, spec in feature_specs(train, ctxs):
            if not extent_ok(spec, ctxs): continue
            for cmode in ('lit', 'fg'):
                tab = residue_fit(ctxs, outs, spec, cmode)
                if tab is None: continue
                fits.append((len(tab) + 2 * level, level, spec, cmode, tab, bg))
    fits.sort(key=lambda t: (t[0], t[1]))
    specs = []                       # the 3 best features, each with its literal and fg/bg class variants
    for score, level, spec, cmode, tab, bg in fits:
        if (spec, bg) not in specs:
            if len(specs) == 3: continue
            specs.append((spec, bg))
        yield (f"arith-residue[{spec_name(spec)},{cmode}{'' if bg is None else f',bg{bg}'}]", 4 + min(level, 1),
               lambda g, spec=spec, cmode=cmode, tab=tab, bg=bg: residue_apply(g, spec, cmode, tab, bg))


def spec_name(spec):
    def s(x):
        if isinstance(x, tuple): return f"{x[0]}{'m' if x[1] else 'M'}"
        return str(x)
    return ':'.join(s(x) for x in spec)


# ------------------------------------------------------------------ AFF: line shifts s(u) = a*u | S[u mod k]
def shift_line(r, s, mode, bg, width=None):
    n = len(r)
    if mode == 'roll':
        return np.roll(r, s)
    if mode == 'pad':
        out = np.full(n, bg, dtype=r.dtype)
        if abs(s) >= n: return out
        if s >= 0: out[s:] = r[:n - s]
        else: out[:n + s] = r[-s:]
        return out
    out = np.full(width, bg, dtype=r.dtype)       # expand: place the line at offset s
    out[s:s + n] = r
    return out


def allowed_shifts(r_in, r_out, mode, bg):
    """Set of shifts mapping r_in onto r_out, or None when every shift does (uniform line)."""
    n = len(r_in)
    if mode == 'roll':
        if np.all(r_in == r_in[0]): return None
        return {s for s in range(n) if np.array_equal(np.roll(r_in, s), r_out)}
    if np.all(r_in == bg):
        return None if np.all(r_out == bg) else set()
    if mode == 'pad':
        return {s for s in range(-n + 1, n) if np.array_equal(shift_line(r_in, s, 'pad', bg), r_out)}
    E = len(r_out) - n
    return {s for s in range(E + 1) if np.array_equal(shift_line(r_in, s, 'expand', bg, len(r_out)), r_out)}


def anchor_line(a, bg, anchor):
    if anchor == 'top': return 0
    if anchor == 'bottom': return a.shape[0] - 1
    rows = np.flatnonzero((a != bg).any(axis=1))
    if len(rows) == 0: return None
    return int(rows[0]) if anchor == 'fgtop' else int(rows[-1])


def shift_profile(n, y0, model, par):
    """Shift of every line 0..n-1 (None = undetermined)."""
    if model == 'lin':
        return [par * (y - y0) for y in range(n)]
    k, S = par
    return [S[(y - y0) % k] for y in range(n)]


def apply_shift(g, orient, mode, anchor, model, par, fill=None):
    a = A(g)
    if orient == 'col': a = a.T
    bg = bg_of(g); n, w = a.shape
    y0 = anchor_line(a, bg, anchor)
    if y0 is None: return None
    prof = shift_profile(n, y0, model, par)
    if mode == 'expand':
        lo, hi = min(prof), max(prof)
        width = w + hi - lo
        rows = [shift_line(a[y], prof[y] - lo, 'expand', bg if fill is None else fill, width) for y in range(n)]
    else:
        rows = []
        for y in range(n):
            s = prof[y]
            if s is None:
                if mode == 'roll' and np.all(a[y] == a[y][0]) or mode == 'pad' and np.all(a[y] == bg):
                    s = 0
                else:
                    return None
            rows.append(shift_line(a[y], s % w if mode == 'roll' else s, mode, bg))
    out = np.array(rows)
    return (out if orient == 'row' else out.T).tolist()


EDGE_SETS = (('left',), ('right',), ('top',), ('bottom',), ('top', 'left'), ('top', 'right'),
             ('bottom', 'left'), ('bottom', 'right'))


def border_line(a, e):
    return a[0] if e == 'top' else a[-1] if e == 'bottom' else a[:, 0] if e == 'left' else a[:, -1]


def marker_roll(g, edges, mcol, signs):
    """Remove the marker border line(s); roll the rest by the marker's index (a count of cells) along each."""
    a = A(g); h, w = a.shape
    r0, r1 = (1 if 'top' in edges else 0), h - (1 if 'bottom' in edges else 0)
    c0, c1 = (1 if 'left' in edges else 0), w - (1 if 'right' in edges else 0)
    R = a[r0:r1, c0:c1]
    if R.size == 0: return None
    sy = sx = 0
    for e in edges:
        pos = np.flatnonzero(border_line(a, e) == mcol)
        if len(pos) != 1: return None
        if e in ('top', 'bottom'): sx = int(pos[0]) - c0
        else: sy = int(pos[0]) - r0
    return np.roll(np.roll(R, signs[0] * sy, axis=0), signs[1] * sx, axis=1)


def fam_arith_shift(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    if all(np.array_equal(i, o) for i, o in zip(ins, outs)): return
    # constant cyclic shift read from a marker's index in removed border line(s)
    for edges in EDGE_SETS:
        dh, dw = sum(e in ('top', 'bottom') for e in edges), sum(e in ('left', 'right') for e in edges)
        if any(o.shape != (i.shape[0] - dh, i.shape[1] - dw) for i, o in zip(ins, outs)): continue
        mcols = set.intersection(*[{c for c in np.unique(border_line(i, e)).tolist()
                                    if int((border_line(i, e) == c).sum()) == 1} for i in ins for e in edges])
        for mcol, signs in product(sorted(mcols), product((1, -1), (1, -1))):
            if dh == 0 and signs[1] == -1 or dw == 0 and signs[0] == -1: continue
            preds = [marker_roll(p['input'], edges, mcol, signs) for p in train]
            if any(r is None or not np.array_equal(r, o) for r, o in zip(preds, outs)): continue
            if all(np.array_equal(r, marker_roll(p['input'], edges, mcol, (0, 0))) for r, p in zip(preds, train)):
                continue
            yield (f"arith-shift[marker{list(edges)},c{mcol}]:roll{signs}", 4,
                   lambda g, e=edges, m=mcol, sg=signs: (lambda r: None if r is None else r.tolist())(
                       marker_roll(g, e, m, sg)))
            return
    found = 0
    for orient in ('row', 'col'):
        I = [i if orient == 'row' else i.T for i in ins]
        O = [o if orient == 'row' else o.T for o in outs]
        if any(i.shape[0] != o.shape[0] for i, o in zip(I, O)): continue
        if all(i.shape == o.shape for i, o in zip(I, O)): modes = ('roll', 'pad')
        elif all(o.shape[1] > i.shape[1] for i, o in zip(I, O)): modes = ('expand',)
        else: continue
        bgs0 = [bg_of(p['input']) for p in train]
        fills = [None]
        if modes == ('expand',):
            newc = set.intersection(*[set(np.unique(o).tolist()) - set(np.unique(i).tolist()) for i, o in zip(I, O)])
            fills += sorted(newc)
        for mode, fill in product(modes, fills):
            bgs = bgs0 if fill is None else [fill] * len(train)
            AL = [[allowed_shifts(i[y], o[y], mode, bg) for y in range(i.shape[0])] for i, o, bg in zip(I, O, bgs)]
            if any(s is not None and not s for al in AL for s in al): continue
            if all(s is None or s == {0} for al in AL for s in al): continue
            for anchor in ('top', 'bottom', 'fgtop', 'fgbot'):
                y0s = [anchor_line(i, bg, anchor) for i, bg in zip(I, bgs0)]
                if any(y0 is None for y0 in y0s): continue
                # linear shear s = a * (y - y0)
                for aa in (1, -1, 2, -2):
                    ok = True
                    for i, al, y0 in zip(I, AL, y0s):
                        prof = shift_profile(i.shape[0], y0, 'lin', aa)
                        if mode == 'expand':
                            lo = min(prof); prof = [s - lo for s in prof]
                        for y, s in enumerate(prof):
                            if al[y] is None: continue
                            if (s % i.shape[1] if mode == 'roll' else s) not in al[y]: ok = False; break
                        if not ok: break
                    if ok:
                        found += 1
                        yield (f"arith-shift[{orient},{mode}{'' if fill is None else f',fill{fill}'},{anchor}]:lin{aa:+d}", 4,
                               lambda g, o_=orient, m=mode, an=anchor, aa=aa, fl=fill: apply_shift(g, o_, m, an, 'lin', aa, fl))
                        break
                if mode == 'expand': continue
                # periodic shift sequence s = S[(y - y0) mod k]
                for k in (2, 3, 4):
                    S = [None] * k; ok = True
                    for i, al, y0 in zip(I, AL, y0s):
                        w = i.shape[1]
                        for y in range(i.shape[0]):
                            if al[y] is None: continue
                            r = (y - y0) % k
                            cand = {s if mode != 'roll' else (s if s <= w // 2 else s - w) for s in al[y]}
                            S[r] = cand if S[r] is None else S[r] & cand
                            if not S[r]: ok = False; break
                        if not ok: break
                    if not ok or all(s is None for s in S): continue
                    SS = [None if s is None else min(s, key=lambda v: (abs(v), v)) for s in S]
                    if len({s for s in SS if s is not None}) < 2: continue
                    if sum(s is not None for s in SS) < k: continue
                    found += 1
                    yield (f"arith-shift[{orient},{mode},{anchor}]:per{k}{SS}", 5,
                           lambda g, o_=orient, m=mode, an=anchor, k=k, SS=tuple(SS): apply_shift(g, o_, m, an, 'per', (k, SS)))
                    break
                if found >= 4: return


# ------------------------------------------------------------------ + * : multiplicity = a * count + b
def count_features(train):
    """Count functions n(g) (name, fn), colours restricted to those present in every training input."""
    common = set.intersection(*[set(np.unique(A(p['input'])).tolist()) for p in train])
    feats = [('ncol', lambda g: len(set(np.unique(g).tolist()) - {bg_of(g.tolist())})),
             ('ncolall', lambda g: len(np.unique(g))),
             ('nfg', lambda g: int((g != bg_of(g.tolist())).sum())),
             ('nbg', lambda g: int((g == bg_of(g.tolist())).sum()))]
    for conn, mono in SEGS:
        feats.append((f'nobj{conn}{"m" if mono else "M"}', lambda g, s=(conn, mono): label(g, bg_of(g.tolist()), *s)[1]))
    for c in sorted(common):
        feats.append((f'ncell{c}', lambda g, c=c: int((g == c).sum())))
        for conn in (4, 8):
            feats.append((f'nobj{conn}c{c}', lambda g, c=c, conn=conn:
                          ndimage.label(g == c, structure=S4 if conn == 4 else S8)[1]))
    feats.append(('nminor', lambda g: min(Counter(g.ravel().tolist()).values())))
    return feats


def source(g, how):
    if how == 'grid': return g
    bg = bg_of(g.tolist()); ys, xs = np.nonzero(g != bg)
    if len(ys) == 0: return None
    return g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def multiply(S, op, k):
    if k < 1 or k * max(S.shape) > 30: return None
    if op == 'up': return np.kron(S, np.ones((k, k), dtype=S.dtype))
    if op == 'upy': return np.kron(S, np.ones((k, 1), dtype=S.dtype))
    if op == 'upx': return np.kron(S, np.ones((1, k), dtype=S.dtype))
    if op == 'tile': return np.tile(S, (k, k))
    if op == 'tiley': return np.tile(S, (k, 1))
    return np.tile(S, (1, k))


def fam_arith_count_scale(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    if len(train) < 2: return
    feats = None; n_yield = 0
    for how in ('grid', 'fg'):
        srcs = [source(i, how) for i in ins]
        if any(s is None for s in srcs): continue
        if how == 'fg' and all(s.shape == i.shape for s, i in zip(srcs, ins)): continue
        for op in ('up', 'tile', 'upx', 'upy', 'tilex', 'tiley'):
            ks = []
            for s, o in zip(srcs, outs):
                ky, kx = o.shape[0] / s.shape[0], o.shape[1] / s.shape[1]
                k = {'up': ky if ky == kx else 0, 'tile': ky if ky == kx else 0, 'upx': kx if ky == 1 else 0,
                     'upy': ky if kx == 1 else 0, 'tilex': kx if ky == 1 else 0, 'tiley': ky if kx == 1 else 0}[op]
                if k != int(k) or k < 1: break
                m = multiply(s, op, int(k))
                if m is None or not np.array_equal(m, o): break
                ks.append(int(k))
            if len(ks) != len(train) or len(set(ks)) < 2: continue
            if feats is None: feats = count_features(train)
            for fname, fn in feats:
                ns = [fn(i) for i in ins]
                for a, b in ((1, 0), (1, -1), (1, 1), (2, 0)):
                    if all(a * n + b == k for n, k in zip(ns, ks)):
                        n_yield += 1
                        yield (f"arith-count-scale[{how},{op}]:k={a}*{fname}{b:+d}", 4,
                               lambda g, how=how, op=op, fn=fn, a=a, b=b:
                               (lambda S: None if S is None else (lambda m: None if m is None else m.tolist())(
                                   multiply(S, op, a * fn(A(g)) + b)))(source(A(g), how)))
                        break
                if n_yield >= 3: return


# ------------------------------------------------------------------ S: union of panels, conflicts by colour order
def uniform_seps(a):
    """Candidate separators: (colour, full rows, full cols) of one uniform colour, most lines first."""
    out = []
    for c in np.unique(a).tolist():
        rs = [y for y in range(a.shape[0]) if np.all(a[y] == c)]
        cs = [x for x in range(a.shape[1]) if np.all(a[:, x] == c)]
        if (rs or cs) and len(rs) < a.shape[0] and len(cs) < a.shape[1]:
            out.append((c, rs, cs))
    out.sort(key=lambda t: -(len(t[1]) + len(t[2])))
    return out


def cut(lines, n):
    segs, s = [], 0
    for L in sorted(lines) + [n]:
        if L > s: segs.append((s, L))
        s = L + 1
    return segs


def panels(a, how, shape=None):
    """Equal-size panels of a grid: 'sep' (uniform separator lines), 'bNxM' (N x M blocks, no separators),
    'corners' (4 corner windows of a given shape, may overlap)."""
    if how == 'sep':
        for _, rs, cs in uniform_seps(a):
            P = [a[y0:y1, x0:x1] for y0, y1 in cut(rs, a.shape[0]) for x0, x1 in cut(cs, a.shape[1])]
            if len(P) >= 2 and all(p.shape == P[0].shape for p in P): return P
        return None
    elif how == 'corners':
        if shape is None: return None
        h, w = shape
        if h > a.shape[0] or w > a.shape[1] or (h, w) == a.shape: return None
        if min(h, w) < 2 or 2 * h < a.shape[0] - 1 or 2 * w < a.shape[1] - 1: return None
        P = [a[:h, :w], a[:h, -w:], a[-h:, :w], a[-h:, -w:]]
    else:
        n, m = map(int, how[1:].split('x'))
        if a.shape[0] % n or a.shape[1] % m: return None
        h, w = a.shape[0] // n, a.shape[1] // m
        P = [a[i * h:(i + 1) * h, j * w:(j + 1) * w] for i in range(n) for j in range(m)]
    if len(P) < 2 or any(p.shape != P[0].shape for p in P) or min(P[0].shape) < 2: return None
    return P


def panel_bg(P, pref=None):
    allv = np.concatenate([p.ravel() for p in P])
    if pref is not None and np.any(allv == pref): return pref
    return Counter(allv.tolist()).most_common(1)[0][0]


def closure(edges, cols):
    """Transitive closure of 'x beats y' edges; None when cyclic."""
    beats = {c: set() for c in cols}
    for x, y in edges: beats[x].add(y)
    changed = True
    while changed:
        changed = False
        for x in cols:
            new = set().union(*[beats[y] for y in beats[x]]) if beats[x] else set()
            if not new <= beats[x]: beats[x] |= new; changed = True
    if any(x in beats[x] for x in cols): return None
    return beats


def union_apply(g, how, shape, beats, tbg=None):
    P = panels(A(g), how, shape)
    if P is None: return None
    bg = panel_bg(P, tbg); h, w = P[0].shape
    out = np.full((h, w), bg, dtype=np.int64)
    for y in range(h):
        for x in range(w):
            vals = {int(p[y, x]) for p in P} - {bg}
            if not vals: continue
            if len(vals) == 1: out[y, x] = vals.pop(); continue
            top = [v for v in vals if v in beats and all(u in beats[v] for u in vals if u != v)]
            if len(top) != 1: return None
            out[y, x] = top[0]
    return out.tolist()


def fam_arith_union(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    if any(o.shape == i.shape for i, o in zip(ins, outs)): return
    oshapes = {o.shape for o in outs}
    hows = ['sep'] + [f'b{n}x{m}' for n in (1, 2, 3, 4) for m in (1, 2, 3, 4) if n * m >= 2]
    if len(oshapes) == 1: hows.append('corners')
    shape = next(iter(oshapes)) if len(oshapes) == 1 else None
    n_yield = 0
    for how in hows:
        Ps = [panels(i, how, shape) for i in ins]
        if any(P is None or P[0].shape != o.shape for P, o in zip(Ps, outs)): continue
        tbg = Counter(np.concatenate([p.ravel() for P in Ps for p in P]).tolist()).most_common(1)[0][0]
        edges, cols, ok, multi = set(), set(), True, 0
        for P, o in zip(Ps, outs):
            bg = panel_bg(P, tbg); h, w = o.shape
            for y in range(h):
                for x in range(w):
                    vals = {int(p[y, x]) for p in P} - {bg}
                    v = int(o[y, x])
                    if not vals:
                        if v != bg: ok = False
                        continue
                    if v not in vals: ok = False; break
                    if len(vals) > 1: multi += 1
                    cols |= vals
                    edges |= {(v, u) for u in vals if u != v}
                if not ok: break
            if not ok: break
        beats = closure(edges, cols) if ok else None
        if beats is not None:
            n_yield += 1
            yield (f"arith-union[{how}]:{'colour-order' if multi else 'or'}", 4,
                   lambda g, how=how, shape=shape, beats=beats, tbg=tbg: union_apply(g, how, shape, beats, tbg))
            if n_yield >= 2: return
            continue
        # membership count: out = T[number of panels holding a figure cell here]
        T = count_table(Ps, outs, tbg)
        if T is not None:
            n_yield += 1
            yield (f"arith-union[{how}]:count{sorted(T.items())}", 4,
                   lambda g, how=how, shape=shape, T=T, tbg=tbg: count_apply(g, how, shape, T, tbg))
            if n_yield >= 2: return


def count_table(Ps, outs, tbg=None):
    """count -> literal colour | 'val' (the common figure colour) | 'bg'; must differ from a plain union."""
    T = {}
    for P, o in zip(Ps, outs):
        bg = panel_bg(P, tbg); st = np.stack(P); fgm = st != bg
        cnt = fgm.sum(axis=0)
        for c in np.unique(cnt).tolist():
            m = cnt == c
            ov = o[m]
            opts = set()
            if np.all(ov == ov[0]): opts.add(('lit', int(ov[0])) if ov[0] != bg else ('bg',))
            if c > 0:
                # the figure colour of each cell (all figure panels agree)
                fv = np.where(fgm[:, m], st[:, m], -1).max(axis=0)
                agree = np.all((st[:, m] == fv) | ~fgm[:, m])
                if agree and np.array_equal(ov, fv): opts.add(('val',))
            T[c] = opts if c not in T else T[c] & opts
            if not T[c]: return None
    res = {}
    for c, opts in T.items():
        res[c] = sorted(opts)[0] if ('val',) not in opts or len(opts) == 1 else ('val',)
        if ('bg',) in opts and c == 0: res[c] = ('bg',)
    plain = all(v == ('val',) or (c == 0 and v == ('bg',)) for c, v in res.items())
    if plain or len(res) < 2: return None
    return res


def count_apply(g, how, shape, T, tbg=None):
    P = panels(A(g), how, shape)
    if P is None: return None
    bg = panel_bg(P, tbg); st = np.stack(P); fgm = st != bg
    cnt = fgm.sum(axis=0)
    out = np.full(cnt.shape, bg, dtype=np.int64)
    for c in np.unique(cnt).tolist():
        if c not in T: return None
        m = cnt == c; act = T[c]
        if act[0] == 'lit': out[m] = act[1]
        elif act[0] == 'val':
            fv = np.where(fgm[:, m], st[:, m], -1).max(axis=0)
            if not np.all((st[:, m] == fv) | ~fgm[:, m]): return None
            out[m] = fv
    return out.tolist()


# ------------------------------------------------------------------ + : arithmetic progression of parallel bars
def seed_bar(a, bg):
    """The single straight 1-thick bar of one colour formed by all fg cells, in a frame where the bar is a row
    segment anchored at the left edge: returns (transform name, r0, L, colour) or None."""
    ys, xs = np.nonzero(a != bg)
    if len(ys) < 2 or len(set(a[ys, xs].tolist())) != 1: return None
    col = int(a[ys[0], xs[0]])
    if len(set(ys.tolist())) == 1 and xs.max() - xs.min() + 1 == len(xs):
        if xs.min() == 0: return ('id', int(ys[0]), len(xs), col)
        if xs.max() == a.shape[1] - 1: return ('fh', int(ys[0]), len(xs), col)
    if len(set(xs.tolist())) == 1 and ys.max() - ys.min() + 1 == len(ys):
        if ys.min() == 0: return ('T', int(xs[0]), len(ys), col)
        if ys.max() == a.shape[0] - 1: return ('Tfh', int(xs[0]), len(ys), col)
    return None


def to_frame(a, t):
    if t == 'id': return a
    if t == 'fh': return a[:, ::-1]
    if t == 'T': return a.T
    return a.T[:, ::-1]


def from_frame(a, t):
    if t == 'id': return a
    if t == 'fh': return a[:, ::-1]
    if t == 'T': return a.T
    return a[:, ::-1].T


def progression_apply(g, steps, ctab):
    a = A(g); bg = bg_of(g); sb = seed_bar(a, bg)
    if sb is None: return None
    t, r0, L, col = sb
    f = to_frame(a, t).copy(); n, w = f.shape
    for side, step in zip((-1, 1), steps):
        if step is None: continue
        d = 1
        while 0 <= r0 + side * d < n:
            ln = min(w, L + step * d)
            if ln <= 0: break
            key = (side, d % ctab['m'])
            if key not in ctab['tab']: return None
            c = ctab['tab'][key]
            f[r0 + side * d, :ln] = col if c == 'seed' else c
            d += 1
    return from_frame(f, t).tolist()


def fam_arith_progression(train):
    """Bars parallel to a seed bar at offset d on each side have length L + a_side * d (a_side in -3..3, or no
    bars on that side), anchored at the seed's grid-edge end; colour = table (side, d mod m) of literal colours
    or the seed colour."""
    if not same_shape(train): return
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    seeds = [seed_bar(i, bg_of(p['input'])) for i, p in zip(ins, train)]
    if any(s is None for s in seeds): return
    lens = [[], []]                            # per side: (d, L, w, observed length)
    obs = []                                   # (side, d, colour, is_seed_colour)
    for (t, r0, L, col), i, o, p in zip(seeds, ins, outs, train):
        fi, fo = to_frame(i, t), to_frame(o, t); bg = bg_of(p['input']); n, w = fo.shape
        if not np.array_equal(fo[r0], fi[r0]): return
        if np.any(fi[np.arange(n) != r0] != bg): return
        for si, side in enumerate((-1, 1)):
            d = 1
            while 0 <= r0 + side * d < n:
                row = fo[r0 + side * d]
                nz = np.flatnonzero(row != bg)
                ln = len(nz)
                if ln and (nz[-1] != ln - 1 or len(set(row[:ln].tolist())) != 1): return
                lens[si].append((d, L, w, ln))
                if ln: obs.append((side, d, int(row[0]), int(row[0]) == col))
                d += 1
    if not obs: return
    st = []
    for si in (0, 1):
        if all(ln == 0 for _, _, _, ln in lens[si]):
            st.append(None); continue
        ok = [s for s in range(-3, 4) if all(min(w, max(0, L + s * d)) == ln for d, L, w, ln in lens[si])]
        if not ok: return
        st.append(min(ok, key=lambda v: (abs(v), v)))
    st = tuple(st)
    if all(s in (0, None) for s in st): return
    for m in (1, 2):
        tab = {}; ok = True
        for side, d, c, isseed in obs:
            key = (side, d % m)
            v = 'seed' if all(o[3] for o in obs if (o[0], o[1] % m) == key) else c
            if tab.setdefault(key, v) != v: ok = False; break
        if ok:
            yield (f"arith-progression:steps{st}:m{m}", 4,
                   lambda g, st=st, ct={'m': m, 'tab': tab}: progression_apply(g, st, ct))
            return


# ------------------------------------------------------------------ ===: completion of congruence classes
def lattice_classes(h, w, p, q, sft):
    """Class of every cell under the translation lattice generated by (p, sft) and (0, q)."""
    Y, X = np.indices((h, w))
    return (Y % p) * q + (X - sft * (Y // p)) % q


def vec_ok(a, known, dy, dx):
    """Known cells p and p + (dy, dx) (dy >= 0) always agree."""
    h, w = a.shape
    if dy >= h or abs(dx) >= w: return True
    x0, x1 = max(0, -dx), w - max(0, dx)
    A1, A2 = a[0:h - dy, x0:x1], a[dy:h, x0 + dx:x1 + dx]
    K = known[0:h - dy, x0:x1] & known[dy:h, x0 + dx:x1 + dx]
    return bool(np.all(A1[K] == A2[K]))


def congruence_fill(a, u, rep=2):
    """Fill cells of colour u from the smallest translation lattice <(p, sft), (0, q)> whose classes are
    single-coloured on known cells and all observed (>= 2 known cells per class on average)."""
    h, w = a.shape; known = a != u
    nk = int(known.sum())
    if nk == 0 or nk == a.size: return None
    Q = [q for q in range(1, w + 1) if q == w or vec_ok(a, known, 0, q)]
    cands = []
    for q in Q:
        for p in range(1, h + 1):
            if p * q < 2 or rep * p * q > nk or p * q >= nk or (p == h and q == w): continue
            for sft in (range(q) if p < h else (0,)):
                cands.append((p * q, sft != 0, p, q, sft))
    cands.sort()
    av = a[known]
    for _, _, p, q, sft in cands:
        if p < h and not vec_ok(a, known, p, sft if sft <= q // 2 else sft - q): continue
        full = lattice_classes(h, w, p, q, sft)
        cl = full[known]
        keys = np.unique(cl * 16 + av)
        ucl = np.unique(keys // 16)
        if len(ucl) != p * q or len(keys) != len(ucl): continue
        colour = np.zeros(p * q, dtype=np.int64); colour[keys // 16] = keys % 16
        out = a.copy()
        out[~known] = colour[full[~known]]
        return out
    return None


def unknown_colours(train):
    """Candidate unknown colours: the input background, and colours present in every input but in no output."""
    cands = []
    bgs = {bg_of(p['input']) for p in train}
    if len(bgs) == 1: cands.append(('bg', None))
    occ = set.intersection(*[set(np.unique(A(p['input'])).tolist()) - set(np.unique(A(p['output'])).tolist())
                             for p in train])
    for c in sorted(occ): cands.append(('c', c))
    return cands


def fam_arith_congruence(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    for kind, c in unknown_colours(train):
        us = [bg_of(p['input']) if kind == 'bg' else c for p in train]
        for mode in ('grid', 'patch'):
            ok = True
            for i, o, u in zip(ins, outs, us):          # cheap preconditions before any lattice search
                if mode == 'grid' and (i.shape != o.shape or not np.array_equal(i[i != u], o[i != u])
                                       or np.any(o[i == u] == u) or not np.any(i == u)):
                    ok = False; break
            if not ok: continue
            for i, o, u in zip(ins, outs, us):
                if mode == 'grid' and i.shape != o.shape: ok = False; break
                if mode == 'patch':
                    ys, xs = np.nonzero(i == u)
                    if len(ys) == 0 or (ys.max() - ys.min() + 1, xs.max() - xs.min() + 1) != o.shape: ok = False; break
                f = congruence_fill(i, u)
                if f is None: ok = False; break
                if mode == 'patch': f = f[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                if not np.array_equal(f, o): ok = False; break
            if not ok: continue
            def fn(g, kind=kind, c=c, mode=mode):
                a = A(g); u = bg_of(g) if kind == 'bg' else c
                f = congruence_fill(a, u)
                if f is None: return None
                if mode == 'patch':
                    ys, xs = np.nonzero(a == u)
                    f = f[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
                return f.tolist()
            yield (f"arith-congruence[{kind}{'' if c is None else c},{mode}]", 4, fn)
            return
    # extension: the output canvas is larger; the input (all known) is continued by its smallest lattice
    if all(o.shape[0] >= i.shape[0] and o.shape[1] >= i.shape[1] and o.shape != i.shape for i, o in zip(ins, outs)):
        from fractions import Fraction as Fr
        rat = {(Fr(o.shape[0], i.shape[0]), Fr(o.shape[1], i.shape[1])) for i, o in zip(ins, outs)}
        shp = {o.shape for o in outs}
        rule = ('ratio', rat.pop()) if len(rat) == 1 else ('const', shp.pop()) if len(shp) == 1 else None
        if rule is None: return
        def ext(g, rule=rule):
            a = A(g)
            if rule[0] == 'ratio':
                ry, rx = rule[1]
                if (a.shape[0] * ry).denominator != 1 or (a.shape[1] * rx).denominator != 1: return None
                hh, ww = int(a.shape[0] * ry), int(a.shape[1] * rx)
            else:
                hh, ww = rule[1]
            if hh < a.shape[0] or ww < a.shape[1] or hh > 30 or ww > 30: return None
            cv = np.full((hh, ww), 15, dtype=np.int64); cv[:a.shape[0], :a.shape[1]] = a
            f = congruence_fill(cv, 15, rep=1)
            return None if f is None else f.tolist()
        from gdsl import fit_cmap, apply_cmap
        preds = [ext(p['input']) for p in train]
        if any(r is None for r in preds): return
        m = fit_cmap(preds, [p['output'] for p in train])
        if m is None or any(apply_cmap(r, m) != p['output'] for r, p in zip(preds, train)): return
        yield (f"arith-congruence[extend,{rule[0]}]", 4, ext)


# ------------------------------------------------------------------ S: complement (figure <-> ground) then repeat
def complement(a, ground=None):
    """Swap figure and ground of a 2-colour grid (ground = induced colour, else the majority colour)."""
    cs = np.unique(a).tolist()
    if len(cs) != 2: return None
    bg = ground if ground in cs else bg_of(a.tolist())
    fgc = cs[0] if cs[1] == bg else cs[1]
    return np.where(a == bg, fgc, bg), bg


def comp_apply(g, how, shape, ground):
    a = A(g); r = complement(a, ground)
    if r is None: return None
    c, bg = r
    if how == 'id': return c.tolist()
    if how == 'tile':
        n, m = shape
        return np.tile(c, (n, m)).tolist()
    h, w = a.shape
    out = np.full((h * h, w * w), bg, dtype=np.int64)
    for y in range(h):
        for x in range(w):
            if (a[y, x] != bg) == (how == 'kron-fg'):
                out[y * h:(y + 1) * h, x * w:(x + 1) * w] = c
    return out.tolist()


def fam_arith_complement(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    if any(len(np.unique(i)) != 2 for i in ins): return
    common = set.intersection(*[set(np.unique(i).tolist()) for i in ins])
    ground = common.pop() if len(common) == 1 else None
    i0, o0 = ins[0], outs[0]
    hows = []
    if all(i.shape == o.shape for i, o in zip(ins, outs)): hows.append(('id', None))
    if o0.shape[0] % i0.shape[0] == 0 and o0.shape[1] % i0.shape[1] == 0:
        sh = (o0.shape[0] // i0.shape[0], o0.shape[1] // i0.shape[1])
        if sh != (1, 1): hows.append(('tile', sh))
    if all(o.shape == (i.shape[0] ** 2, i.shape[1] ** 2) for i, o in zip(ins, outs)):
        hows += [('kron-fg', None), ('kron-bg', None)]
    for how, sh in hows:
        if all(comp_apply(p['input'], how, sh, ground) == p['output'] for p in train):
            yield (f"arith-complement[{how}{'' if sh is None else sh}]", 4,
                   lambda g, how=how, sh=sh, gr=ground: comp_apply(g, how, sh, gr))


# ------------------------------------------------------------------ |: quotient windows (divisibility, parity)
def min_period(a):
    """Smallest (p, q) with p | H, q | W such that the grid is p-periodic in y and q-periodic in x."""
    h, w = a.shape
    p = next(d for d in range(1, h + 1) if h % d == 0 and np.array_equal(a, np.tile(a[:d], (h // d, 1))))
    q = next(d for d in range(1, w + 1) if w % d == 0 and np.array_equal(a, np.tile(a[:, :d], (1, w // d))))
    return p, q


def win_size(a, rule):
    h, w = a.shape
    if rule[0] == 'const': return rule[1], rule[2]
    if rule[0] == 'div':
        ky, kx = rule[1], rule[2]
        if h % ky or w % kx: return None
        return h // ky, w // kx
    p, q = min_period(a)
    return (p, q) if (p, q) != (h, w) else None


def window(a, size, corner):
    h, w = a.shape; wh, ww = size
    if wh > h or ww > w or wh < 2 or ww < 2: return None
    if corner == 'C':
        if (h - wh) % 2 or (w - ww) % 2: return None
        y0, x0 = (h - wh) // 2, (w - ww) // 2
    else:
        y0 = 0 if corner[0] == 'T' else h - wh
        x0 = 0 if corner[1] == 'L' else w - ww
    return a[y0:y0 + wh, x0:x0 + ww]


def window_apply(g, rule, ctab):
    a = A(g); size = win_size(a, rule)
    if size is None: return None
    corner = ctab.get((a.shape[0] % 2, a.shape[1] % 2)) if isinstance(ctab, dict) else ctab
    if corner is None: return None
    r = window(a, size, corner)
    return None if r is None else r.tolist()


def fam_arith_window(train):
    ins = [A(p['input']) for p in train]; outs = [A(p['output']) for p in train]
    if any(o.shape[0] > i.shape[0] or o.shape[1] > i.shape[1] or o.shape == i.shape for i, o in zip(ins, outs)): return
    if any(min(o.shape) < 2 for o in outs): return
    rules = []
    if len({o.shape for o in outs}) == 1: rules.append(('const',) + outs[0].shape)
    rat = {(i.shape[0] / o.shape[0], i.shape[1] / o.shape[1]) for i, o in zip(ins, outs)}
    if len(rat) == 1:
        ky, kx = rat.pop()
        if ky == int(ky) and kx == int(kx): rules.append(('div', int(ky), int(kx)))
    rules.append(('period',))
    n = 0
    for rule in rules:
        sizes = [win_size(i, rule) for i in ins]
        if any(sz is None or sz != o.shape for sz, o in zip(sizes, outs)): continue
        hits = []
        for i, o, sz in zip(ins, outs, sizes):
            hits.append({c for c in ('TL', 'TR', 'BL', 'BR', 'C')
                         if (lambda r: r is not None and np.array_equal(r, o))(window(i, sz, c))})
        common = set.intersection(*hits)
        if common:
            c = sorted(common, key=lambda c: ('TL', 'TR', 'BL', 'BR', 'C').index(c))[0]
            n += 1
            yield (f"arith-window[{rule[0]}]:{c}", 3 if rule[0] != 'period' else 4,
                   lambda g, rule=rule, c=c: window_apply(g, rule, c))
        else:                          # corner chosen by the parity of the grid size
            tab = {}; ok = True
            for i, hs in zip(ins, hits):
                key = (i.shape[0] % 2, i.shape[1] % 2)
                tab[key] = tab.get(key, hs) & hs
                if not tab[key]: ok = False; break
            if not ok or len(tab) < 2: continue
            ct = {k: sorted(v)[0] for k, v in tab.items()}
            if len(set(ct.values())) < 2: continue
            n += 1
            yield (f"arith-window[{rule[0]}]:parity{sorted(ct.items())}", 4,
                   lambda g, rule=rule, ct=ct: window_apply(g, rule, ct))
        if n >= 2: return


FAMILIES = (fam_arith_residue, fam_arith_shift, fam_arith_count_scale, fam_arith_union, fam_arith_progression,
            fam_arith_congruence, fam_arith_complement, fam_arith_window)
