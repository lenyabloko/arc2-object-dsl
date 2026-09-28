"""GEOMETRY prior: symmetry groups, lattices and similarity transforms with arbitrary centres, fitted exhaustively.

Core concept
------------
An ARC picture P (a whole grid, one object, the contents of a frame, the panels around a separator crossing)
is assumed invariant under a subgroup G of the plane isometries that preserve the square lattice: D4 elements
(fh, fv, r180, T, aT, r90, r270) about an UNKNOWN centre c that may sit on a cell or between cells (doubled
coordinates c2 = 2c), translations (lattices) and glide reflections.  The input shows P with unknown cells
(background holes or an occluder colour); the output restores each unknown cell from its G-orbit.

Exhaustive fitting: for every element e and EVERY doubled centre, the counts
    agree = #{known fg p : e_c(p) known, same colour}, conflict = #{... different colour},
    fill  = #{known fg p : e_c(p) unknown},  oob = #{fg p : e_c(p) outside the grid}
are computed at once by 1-D/2-D correlation (scipy.signal.correlate); a group's table is the sum over its
elements.  The chosen centre has zero conflicts and maximal (agree - oob) (ties: fewer fills, nearest the
region centre).  'auto' takes every element (each with its own centre) plus the best translations and glides
that are exact symmetries of the known cells and closes the orbits by union-find (a wallpaper-like group);
'local' additionally uses PARTIAL symmetries: an element fills a cell when it is exact inside the smallest
window around that cell holding >= 12 known pairs.

Families (all parameters induced per task; every program is verified on all training pairs by the harness)
  geom-sym-complete        unknown = bg; group H|V|HV|R2|D|A|DA|R4|D4 (+ lattice|auto on the grid);
                           scope grid | object | frame (group+centre fitted on the frame = its stabiliser,
                           imposed on its contents) | anchor (unique G-invariant object is the centre) |
                           crossing (each separator-line crossing is a centre for its 4 panels);
                           paint orbit colour | the new output colour
  geom-sym-repair(-patch)  unknown = occluder colour (absent from outputs) or the unique solid rectangle;
                           group fixed | auto | local; output repaired grid or only the occluded window
  geom-symmetrize-colour   the largest blob's colour becomes G-invariant (overwriting), centre grid | fitted
  geom-fold-dominant       each object made mirror-symmetric about its in-object line / best axis, the fuller
                           half wins
  geom-twisted-quadrants   D2 symmetry up to a colour substitution per quadrant, induced from hint cells
  geom-similarity-complete template = most-colourful object; partial copies elsewhere under D8 x integer scale
                           (of the template's coarsest resolution) x translation are found by exact matching of
                           their visible colours and completed (ties broken by positional reflection)
  geom-product-sites       congruent motifs at anchors: complete the anchor set to rows x cols
  geom-frieze              output = the input continued as a 1-D frieze per axis (translation, mirror with
                           repeated or shared boundary), copies / orientation induced
  geom-fold                fold along the central separator line: base half overlaid by the mirrored half
  geom-select-by-symmetry  crop the unique object / panel / block that has / lacks a D4 element, the odd
                           symmetry signature, or the most / least symmetric one
  geom-fundamental-domain  output = top-left quadrant / half of the symmetric picture
  geom-orbit-recolour      recolour cells by whether their whole G-orbit is present ((colour, paired) table)
Beyond gdsl fam_symmetry / fam_symmetry_offset (mirrors + offset transposes about thresholded axes, occluder
only): rotations and anti/diagonal mirrors about any half-integer centre, translations and glides, partial
(local) symmetries, bg-as-unknown completion, per-object / frame / anchor / crossing scopes, symmetry used as a
feature (selection, recolouring, fundamental domain), colour-twisted symmetry and similarity transforms.
Dropped: symmetry-consistent denoising (majority over orbits, no occluder) -- solved nothing, over-fire risk.
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
import numpy as np
from scipy.signal import correlate
from itertools import product
from gdsl import H, W, bg_of, objects, bbox

# (dy, dx) -> (a*dy + b*dx, c*dy + d*dx)
EL = {"fh": (1, 0, 0, -1), "fv": (-1, 0, 0, 1), "r180": (-1, 0, 0, -1), "T": (0, 1, 1, 0),
      "aT": (0, -1, -1, 0), "r90": (0, 1, -1, 0), "r270": (0, -1, 1, 0)}
GROUPS = {"H": ("fh",), "V": ("fv",), "HV": ("fh", "fv", "r180"), "R2": ("r180",), "D": ("T",), "A": ("aT",),
          "DA": ("T", "aT", "r180"), "R4": ("r90", "r180", "r270"), "D4": tuple(EL)}


def image(e, cy2, cx2, y, x):
    a, b, c, d = EL[e]; dy, dx = 2 * y - cy2, 2 * x - cx2
    ny, nx = cy2 + a * dy + b * dx, cx2 + c * dy + d * dx
    if ny % 2 or nx % 2: return None
    return ny // 2, nx // 2


def pair_counts(e, A, B):
    """N[cy2, cx2] = #{p : A[p] and B[e_c(p)]} for every doubled centre, shape (2h-1, 2w-1)."""
    h, w = A.shape; N = np.zeros((2 * h - 1, 2 * w - 1), dtype=np.int64)
    if not A.any() or not B.any(): return N
    Af, Bf = A.astype(np.int64), B.astype(np.int64)
    if e == "r180":                                  # q = c2 - p  -> full convolution
        return np.rint(correlate(Bf, Af[::-1, ::-1], mode="full", method="auto")).astype(np.int64)
    if e == "fh":                                    # q = (y, cx2 - x)
        v = sum(np.convolve(Af[y], Bf[y]) for y in range(h)); N[:, :] = v[None, :]; return N
    if e == "fv":
        v = sum(np.convolve(Af[:, x], Bf[:, x]) for x in range(w)); N[:, :] = v[:, None]; return N
    # T: q = (x + k, y - k), k = (cy2 - cx2)/2 ;  aT: q = (s - x, s - y), s = (cy2 + cx2)/2
    # r90: q = (x + u, v - y), u = (cy2 - cx2)/2, v = (cy2 + cx2)/2 ; r270 is its inverse
    Y, X = np.mgrid[0:2 * h - 1, 0:2 * w - 1]; par = (Y - X) % 2 == 0
    P = Af.T                                          # P[x, y] = A[y, x]
    if e == "T":                                      # sum P[x,y] B[x+k, y-k] = corr(B,P)[k+w-1, -k+h-1]
        C = np.rint(correlate(Bf, P, mode="full", method="auto")).astype(np.int64)
        k = (Y - X) // 2; i, j = k + w - 1, -k + h - 1
    elif e == "aT":                                   # sum P[x,y] B[s-x, s-y] = conv(B,P)[s, s]
        C = np.rint(correlate(Bf, P[::-1, ::-1], mode="full", method="auto")).astype(np.int64)
        s_ = (Y + X) // 2; i, j = s_, s_
    elif e == "r270":                                 # #{p: A[p], B[r270 p]} = #{q: B[q], A[r90 q]}
        return pair_counts("r90", B, A)
    else:                                             # r90: sum P[x,y] B[x+u, v-y] = C[u + w - 1, v]
        C = np.rint(correlate(Bf, P[:, ::-1], mode="full", method="auto")).astype(np.int64)
        i, j = (Y - X) // 2 + w - 1, (Y + X) // 2
    ok = par & (i >= 0) & (i < C.shape[0]) & (j >= 0) & (j < C.shape[1])
    N[ok] = C[i[ok], j[ok]]
    return N


def glide_counts(A, B, axis):
    """axis 'h': C[t + h - 1, c] = #{p : A[p] and B[y + t, c - x]} (mirror in x, shift t along y);
    axis 'v': the transpose analogue (mirror in y, shift along x), indexed [t + w - 1, c]."""
    if axis == "v": return glide_counts(A.T, B.T, "h")
    return np.rint(correlate(B.astype(np.int64), A[:, ::-1].astype(np.int64), mode="full", method="auto")).astype(np.int64)


def shift_counts(A, B):
    """S[dy + h - 1, dx + w - 1] = #{p : A[p] and B[p + (dy, dx)]}."""
    return np.rint(correlate(B.astype(np.int64), A.astype(np.int64), mode="full", method="auto")).astype(np.int64)


class Fit:
    """Correlation tables for one picture: fg (known foreground), K (known), U (unknown)."""
    def __init__(self, g, fg, K):
        self.g = g; self.fg = fg; self.K = K; self.U = ~K; self.t = {}
        self.cols = [c for c in np.unique(g[fg])]

    def tables(self, e):
        if e not in self.t:
            agree = sum(pair_counts(e, self.fg & (self.g == c), self.K & (self.g == c)) for c in self.cols)
            pairs = pair_counts(e, self.fg, self.K)
            fill = pair_counts(e, self.fg, self.U)
            h, w = self.g.shape
            oob = int(self.fg.sum()) - pair_counts(e, self.fg, np.ones_like(self.fg))
            valid = np.ones((2 * h - 1, 2 * w - 1), bool)
            if e in ("T", "aT", "r90", "r270"):
                Y, X = np.mgrid[0:2 * h - 1, 0:2 * w - 1]; valid = (Y - X) % 2 == 0
            self.t[e] = (agree, pairs - agree, fill, valid)
            self.t["oob:" + e] = oob
        return self.t[e]

    def best(self, group, box=None, min_frac=0.0):
        h, w = self.g.shape
        A = np.zeros((2 * h - 1, 2 * w - 1), np.int64); Cf = A.copy(); F = A.copy(); O = A.copy(); V = np.ones_like(A, bool)
        for e in GROUPS[group]:
            a, c, f, v = self.tables(e); A = A + a; Cf = Cf + c; F = F + f; V &= v; O = O + self.t["oob:" + e]
        ok = V & (Cf == 0) & (A > 0)
        if box is not None:
            r0, c0, r1, c1 = box; m = np.zeros_like(ok); m[2 * r0:2 * r1 + 1, 2 * c0:2 * c1 + 1] = True; ok &= m
        nfg = int(self.fg.sum())
        if not ok.any(): return None
        if min_frac and A[ok].max() < min_frac * nfg * len(GROUPS[group]): return None
        ys, xs = np.nonzero(ok)
        if box is None: my, mx = h - 1, w - 1
        else: my, mx = box[0] + box[2], box[1] + box[3]
        key = [(-(A[y, x] - O[y, x]), -F[y, x], abs(y - my) + abs(x - mx), y, x) for y, x in zip(ys, xs)]
        key.sort()
        return key[0][3], key[0][4]


_CACHE = {}


def get_fit(G, fg, K):
    key = (G.shape, G.tobytes(), fg.tobytes(), K.tobytes())
    f = _CACHE.get(key)
    if f is None:
        if len(_CACHE) > 200: _CACHE.clear()
        f = _CACHE[key] = Fit(G, fg, K)
    return f


def orbit_fill(g, known, group, cy2, cx2, cells, paint, bgc, keep=False):
    """For each unknown cell in `cells` take the colour of known fg orbit members (must agree)."""
    h, w = g.shape; out = g.copy(); changed = False
    for y, x in cells:
        vals = set()
        for e in GROUPS[group]:
            q = image(e, cy2, cx2, y, x)
            if q is None: continue
            qy, qx = q
            if 0 <= qy < h and 0 <= qx < w and known[qy, qx]: vals.add(int(g[qy, qx]))
        if not vals: continue
        if len(vals) > 1: return None
        v = vals.pop()
        if v == bgc and paint is not None: continue
        out[y, x] = v if paint is None else paint; changed = True
    return out if changed or keep else None


def to_np(g): return np.array(g, dtype=np.int64)


# --------------------------------------------------------------------------- bg-as-unknown completion

def complete_bg(g, group, scope, paint, min_frac):
    G = to_np(g); h, w = G.shape; bgc = bg_of(g)
    fg = G != bgc
    if not fg.any(): return None
    out = G.copy(); acted = False
    if group in ("lattice", "auto"):             # every exact symmetry of the foreground, closed by union-find
        f = get_fit(G, fg, fg)
        el = [t for t in auto_elements(f, h, w, ratio=0.75) if group == "auto" or t[0] == "shift"]
        if not el: return None
        K = fg.copy(); r = union_repair(G, K, el, partial=True)
        if r is None or (r == G).all(): return None
        if paint is not None: r[(r != G)] = paint
        return r.tolist()
    if scope == "grid":
        units = [(fg, None, list(zip(*np.nonzero(~fg))))]
    elif scope == "object":
        units = []
        for ob in objects(g, bgc, True, False):
            if len(ob) < 3: continue
            m = np.zeros_like(fg); ys, xs = zip(*ob); m[list(ys), list(xs)] = True
            units.append((m, bbox(ob), list(zip(*np.nonzero(~fg)))))
        if len(units) < 1: return None
    elif scope == "crossing":  # every crossing of separator lines is a candidate centre for its 4 panels
        rows = [y for y in range(h) if len(set(g[y])) == 1 and g[y][0] != bgc]
        cols = [x for x in range(w) if len({g[y][x] for y in range(h)}) == 1 and g[0][x] != bgc]
        if not rows or not cols: return None
        sep = np.zeros_like(fg); sep[rows, :] = True; sep[:, cols] = True
        for r in rows:
            for c in cols:
                ra = max([y for y in rows if y < r], default=-1); rb = min([y for y in rows if y > r], default=h)
                ca = max([x for x in cols if x < c], default=-1); cb = min([x for x in cols if x > c], default=w)
                m = np.zeros_like(fg); m[ra + 1:rb, ca + 1:cb] = True; m &= ~sep
                pic = m & fg
                if not pic.any(): continue
                cnt_a = 0; ok = True
                for y, x in zip(*np.nonzero(pic)):
                    for e in GROUPS[group]:
                        q = image(e, 2 * r, 2 * c, y, x)
                        if q is None or not (0 <= q[0] < h and 0 <= q[1] < w) or not m[q]: continue
                        if pic[q]:
                            if G[q] == G[y, x]: cnt_a += 1
                            else: ok = False
                if not ok or cnt_a == 0: continue
                cells = list(zip(*np.nonzero(m & ~fg)))
                rr = orbit_fill(out, pic, group, 2 * r, 2 * c, cells, paint, bgc)
                if rr is not None: out = rr; acted = True
        return out.tolist() if acted else None
    elif scope == "anchor":   # the unique G-invariant object (size >= 2) is the centre for everything else
        anc = []
        for ob in objects(g, bgc, True, True):
            if len(ob) < 2: continue
            r0, c0, r1, c1 = bbox(ob); st = set(ob)
            if all(image(e, r0 + r1, c0 + c1, y, x) in st for e in GROUPS[group] for y, x in ob): anc.append((ob, r0 + r1, c0 + c1))
        if len(anc) != 1: return None
        ob, cy2, cx2 = anc[0]
        if int(fg.sum()) == len(ob): return None
        r = orbit_fill(out, fg, group, cy2, cx2, list(zip(*np.nonzero(~fg))), paint, bgc, keep=True)
        return None if r is None else r.tolist()
    else:   # frame: fit on a single-colour container, impose on the content inside its bbox
        units = []
        for ob in objects(g, bgc, True, True):
            if len(ob) < 6: continue
            r0, c0, r1, c1 = bbox(ob)
            if r1 - r0 < 2 or c1 - c0 < 2: continue
            s = set(ob)
            inner = [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s and fg[y, x]]
            if not inner: continue
            m = np.zeros_like(fg); ys, xs = zip(*ob); m[list(ys), list(xs)] = True
            units.append((m, (r0, c0, r1, c1), inner))
        if not units: return None
    for m, box, _ in units:
        if scope == "frame":
            f = get_fit(G, m, m)
            c = f.best(group, box, min_frac=0.99)            # the frame must be fully symmetric under G
            if c is None: continue
            r0, c0, r1, c1 = box
            content = np.zeros_like(fg); s = m
            content[r0:r1 + 1, c0:c1 + 1] = fg[r0:r1 + 1, c0:c1 + 1] & ~s[r0:r1 + 1, c0:c1 + 1]
            cells = [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if not fg[y, x]]
            r = orbit_fill(out, content, group, c[0], c[1], cells, paint, bgc)
        else:
            f = get_fit(G, m, m)
            c = f.best(group, box, min_frac=min_frac)
            if c is None: continue
            cells = list(zip(*np.nonzero(~fg)))
            r = orbit_fill(out, m & (out != bgc), group, c[0], c[1], cells, paint, bgc)
        if r is not None: out = r; acted = True
    return out.tolist() if acted else None


# --------------------------------------------------------------------------- occluder completion

def occ_window(G, occ):
    ys, xs = np.nonzero(G == occ)
    if not len(ys): return None
    return ys.min(), xs.min(), ys.max(), xs.max()


def auto_elements(f, h, w, shifts=True, ratio=0.0):
    """Every D4 element that is an exact symmetry of the known picture (each with its own best centre),
    plus the (up to 4) best exact translation symmetries (a lattice)."""
    nfg = int(f.fg.sum()); acc = []
    for e in EL:
        a, c, fl, v = f.tables(e)
        ok = v & (c == 0) & (a >= 0.25 * nfg) & (a >= ratio * (nfg - f.t["oob:" + e]))
        if not ok.any(): continue
        ys, xs = np.nonzero(ok)
        best = max(zip(ys, xs), key=lambda t: (a[t], -abs(t[0] - (h - 1)) - abs(t[1] - (w - 1))))
        acc.append((e, int(best[0]), int(best[1])))
    if shifts:
        if "shift" not in f.t:
            ag = sum(shift_counts(f.fg & (f.g == c), f.K & (f.g == c)) for c in f.cols)
            f.t["shift"] = (ag, shift_counts(f.fg, f.K) - ag, shift_counts(f.fg, np.ones_like(f.fg)))
        ag, cf, inb = f.t["shift"]
        ok = (cf == 0) & (ag >= 0.25 * nfg) & (ag >= ratio * inb); ok[h - 1, w - 1] = False
        cand = sorted(((-ag[y, x], abs(y - h + 1) + abs(x - w + 1), y - h + 1, x - w + 1) for y, x in zip(*np.nonzero(ok))))
        got = []
        for _, _, dy, dx in cand:
            if (-dy, -dx) in got: continue
            got.append((dy, dx))
            if len(got) == 4: break
        acc += [("shift", dy, dx) for dy, dx in got]
        for ax in ("h", "v"):                            # glide reflections (mirror + shift along the axis)
            key = "glide" + ax
            if key not in f.t:
                ag = sum(glide_counts(f.fg & (f.g == c), f.K & (f.g == c), ax) for c in f.cols)
                f.t[key] = (ag, glide_counts(f.fg, f.K, ax) - ag, glide_counts(f.fg, np.ones_like(f.fg), ax))
            ag, cf, inb = f.t[key]
            n0 = (h if ax == "h" else w) - 1
            ok = (cf == 0) & (ag >= 0.25 * nfg) & (ag >= ratio * inb); ok[n0, :] = False    # t = 0 is a mirror
            if ok.any():
                t_, c_ = max(zip(*np.nonzero(ok)), key=lambda q: ag[q])
                acc.append(("glide" + ax, int(t_) - n0, int(c_)))
    return acc


def union_repair(G, K, elems, partial=False):
    h, w = G.shape; par = list(range(h * w))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for e, cy2, cx2 in elems:
        for y in range(h):
            for x in range(w):
                q = ((y + cy2, x + cx2) if e == "shift" else (y + cy2, cx2 - x) if e == "glideh" else
                     (cx2 - y, x + cy2) if e == "glidev" else image(e, cy2, cx2, y, x))
                if q is None: continue
                qy, qx = q
                if 0 <= qy < h and 0 <= qx < w:
                    a, b = find(y * w + x), find(qy * w + qx)
                    if a != b: par[a] = b
    vals = {}
    for y in range(h):
        for x in range(w):
            if K[y, x]: vals.setdefault(find(y * w + x), set()).add(int(G[y, x]))
    out = G.copy()
    for y in range(h):
        for x in range(w):
            if not K[y, x]:
                s = vals.get(find(y * w + x))
                if not s or len(s) != 1:
                    if partial and not s: continue
                    return None
                out[y, x] = next(iter(s)); K[y, x] = True
    return out


def image_maps(e, cy2, cx2, h, w):
    Y, X = np.mgrid[0:h, 0:w]
    a, b, c, d = EL[e]; dy, dx = 2 * Y - cy2, 2 * X - cx2
    ny, nx = cy2 + a * dy + b * dx, cx2 + c * dy + d * dx
    if (ny % 2).any() or (nx % 2).any(): return None
    ny, nx = ny // 2, nx // 2
    return ny, nx, (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)


def local_candidates(f, per=2):
    """Partial symmetries: for each element the best centres whose agreement ratio on known cells >= 1/2."""
    nfg = int(f.fg.sum()); out = []
    for e in EL:
        a, cf, fl, v = f.tables(e)
        sc = np.where(v & (a >= 0.1 * nfg) & (2 * a >= a + cf), a, -1)
        for i in np.argsort(-sc.ravel())[:per]:
            y, x = np.unravel_index(i, sc.shape)
            if sc[y, x] > 0: out.append((e, int(y), int(x)))
    return out


def box_sum(M, r):
    h, w = M.shape; P = np.zeros((h + 1, w + 1), np.int64); P[1:, 1:] = M.cumsum(0).cumsum(1)
    Y, X = np.mgrid[0:h, 0:w]
    y0, y1 = np.clip(Y - r, 0, h), np.clip(Y + r + 1, 0, h); x0, x1 = np.clip(X - r, 0, w), np.clip(X + r + 1, 0, w)
    return P[y1, x1] - P[y0, x1] - P[y1, x0] + P[y0, x0]


def local_repair(G, K, cands, need=12, rmax=6, rounds=3):
    """Fill unknown p from e(p) when e is an exact symmetry of the known cells in the smallest window around p
    holding >= `need` known pairs; all locally valid candidates must agree."""
    h, w = G.shape; G = G.copy(); K = K.copy()
    maps = [m for m in (image_maps(e, cy2, cx2, h, w) for e, cy2, cx2 in cands) if m is not None]
    for _ in range(rounds):
        if K.all(): break
        votes = {}
        for ny, nx, inb in maps:
            qy, qx = np.where(inb, ny, 0), np.where(inb, nx, 0)
            kn = K & inb & K[qy, qx]
            agr = kn & (G == G[qy, qx]); con = kn & ~agr
            dec = np.zeros((h, w), bool); ok = np.zeros((h, w), bool)
            for r in range(1, rmax + 1):
                n = box_sum(agr.astype(np.int64) + con, r); c = box_sum(con.astype(np.int64), r)
                newly = ~dec & (n >= need)
                ok |= newly & (c == 0); dec |= newly
            src = ~K & ok & inb & K[qy, qx]
            for y, x in zip(*np.nonzero(src)): votes.setdefault((y, x), set()).add(int(G[qy[y, x], qx[y, x]]))
        got = False
        for (y, x), vs in votes.items():
            if len(vs) == 1: G[y, x] = vs.pop(); K[y, x] = True; got = True
        if not got: break
    return G, K


def rect_colour(G):
    """The unique non-background colour whose cells exactly fill their bounding box (area >= 4)."""
    bgc = np.bincount(G.ravel()).argmax(); hits = []
    for c in np.unique(G):
        if c == bgc: continue
        ys, xs = np.nonzero(G == c)
        a = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
        if a >= 4 and a == len(ys): hits.append(int(c))
    return hits[0] if len(hits) == 1 else None


def repair_occ(g, occ, group, patch):
    G = to_np(g); h, w = G.shape
    if occ == "rect":
        occ = rect_colour(G)
        if occ is None: return None
    win = occ_window(G, occ)
    if win is None: return None
    K = G != occ
    # every known cell is informative (bg included): fit on all known cells
    f = get_fit(G, K, K)
    if group in ("auto", "local"):
        el = auto_elements(f, h, w)
        if not el and group == "auto": return None
        K2 = K.copy()
        out = union_repair(G, K2, el, partial=group == "local")
        if out is None: return None
        if group == "local" and not K2.all():
            out, K2 = local_repair(out, K2, local_candidates(f))
            if not K2.all(): return None
    else:
        c = f.best(group, None, min_frac=0.3)
        if c is None: return None
        el = [(e, c[0], c[1]) for e in GROUPS[group]]
        out = union_repair(G, K, el)
    if out is None: return None
    if patch:
        r0, c0, r1, c1 = win
        return out[r0:r1 + 1, c0:c1 + 1].tolist()
    return out.tolist()


# --------------------------------------------------------------------------- families

def _same(train): return all((H(p["input"]), W(p["input"])) == (H(p["output"]), W(p["output"])) for p in train)


def _new_colour(train):
    new = None
    for p in train:
        ci = {v for r in p["input"] for v in r}; co = {v for r in p["output"] for v in r}
        n = co - ci; new = n if new is None else new & n
    return next(iter(new)) if new and len(new) == 1 else None


def fam_sym_complete_bg(train):
    """Background holes restored from the G-orbit (G, centre fitted per grid / object / frame)."""
    if not _same(train): return
    i0, o0 = train[0]["input"], train[0]["output"]; bg = bg_of(i0)
    # output must only add foreground over background
    if all(p["input"] == p["output"] for p in train): return
    for p in train:
        i, o = p["input"], p["output"]; b = bg_of(i)
        if any(i[y][x] != o[y][x] and i[y][x] != b for y in range(H(i)) for x in range(W(i))): return
    nc = _new_colour(train)
    paints = [None] + ([nc] if nc is not None else [])
    for scope in ("grid", "object", "frame", "anchor", "crossing"):
        for grp in tuple(GROUPS) + (("lattice", "auto") if scope == "grid" else ()):
            for paint in paints:
                mf = 0.0 if scope == "frame" else 0.15
                yield (f"geom-sym-complete:{scope}[{grp}{'' if paint is None else ',paint=c%d' % paint}]", 4,
                       lambda g, s=scope, G=grp, p=paint, mf=mf: complete_bg(g, G, s, p, mf))


def fam_sym_repair_occ(train):
    """Occluder colour cells restored from the fitted symmetry group (or all exact symmetries: auto)."""
    i0, o0 = train[0]["input"], train[0]["output"]
    same = _same(train)
    occs = []
    if same:
        occs = [c for c in {v for r in i0 for v in r}
                if all(c in {v for r in p["input"] for v in r} and c not in {v for r in p["output"] for v in r} for p in train)]
    else:
        for c in {v for r in i0 for v in r}:
            ok = True
            for p in train:
                win = occ_window(to_np(p["input"]), c)
                if win is None or (win[2] - win[0] + 1, win[3] - win[1] + 1) != (H(p["output"]), W(p["output"])): ok = False; break
            if ok: occs.append(c)
    if all(rect_colour(to_np(p["input"])) is not None for p in train):
        if same and all(rect_colour(to_np(p["input"])) not in {v for r in p["output"] for v in r} for p in train):
            occs.append("rect")
        if not same and all(occ_window(to_np(p["input"]), rect_colour(to_np(p["input"]))) is not None and
                            (lambda wn, p: (wn[2] - wn[0] + 1, wn[3] - wn[1] + 1) == (H(p["output"]), W(p["output"])))(
                                occ_window(to_np(p["input"]), rect_colour(to_np(p["input"]))), p) for p in train):
            occs.append("rect")
    for c in occs:
        for grp in ("auto", "local") + tuple(GROUPS):
            yield (f"geom-sym-repair{'-patch' if not same else ''}[{c if c == 'rect' else 'c%d' % c},{grp}]", 4,
                   lambda g, c=c, G=grp, pt=not same: repair_occ(g, c, G, pt))


def symmetrize_colour(g, group, centre):
    """The colour of the largest single-colour component becomes G-invariant (union with its orbit),
    overwriting whatever lies under the images; centre = grid centre or fitted on that colour alone."""
    G = to_np(g); h, w = G.shape; bgc = bg_of(g)
    obs = objects(g, -1, False, True)          # every colour competes (the blob may be the mode colour)
    if not obs: return None
    big = max(obs, key=len)
    if sum(len(o) == len(big) for o in obs) > 1: return None
    c = g[big[0][0]][big[0][1]]; m = G == c
    if centre == "grid": cy2, cx2 = h - 1, w - 1
    else:
        f = get_fit(G, m, m); r = f.best(group, None, min_frac=0.15)
        if r is None: return None
        cy2, cx2 = r
    out = G.copy()
    for y, x in zip(*np.nonzero(m)):
        for e in GROUPS[group]:
            q = image(e, cy2, cx2, y, x)
            if q is None: return None
            if 0 <= q[0] < h and 0 <= q[1] < w: out[q] = c
    return out.tolist()


def fam_symmetrize_colour(train):
    if not _same(train): return
    for grp, centre in product(GROUPS, ("grid", "fit")):
        yield (f"geom-symmetrize-colour:{centre}[{grp}]", 4, lambda g, grp=grp, centre=centre: symmetrize_colour(g, grp, centre))


def fold_dominant(g, e0, conn):
    """Each object is made mirror-symmetric under the single reflection e about its best-agreeing axis inside
    its bbox: the half holding more cells is kept and mirrored, the other half is replaced."""
    G = to_np(g); h, w = G.shape; bgc = bg_of(g); out = G.copy(); acted = False
    for ob in objects(g, bgc, True, conn == "c8"):
        if len(ob) < 4: continue
        m = np.zeros((h, w), bool); ys, xs = zip(*ob); m[list(ys), list(xs)] = True
        f = get_fit(G, m, m); r0, c0, r1, c1 = bbox(ob)
        best = []
        if e0 == "line":                                   # axis = straight line of one colour inside the object
            lines = []
            for col in {int(G[y, x]) for y, x in ob}:
                cs = [(y, x) for y, x in ob if G[y, x] == col]
                if len(cs) < 2 or len(cs) * 2 > len(ob): continue
                from collections import Counter
                cnt = Counter()
                for y, x in cs: cnt[("fv", 2 * y)] += 1; cnt[("fh", 2 * x)] += 1; cnt[("T", y - x)] += 1; cnt[("aT", y + x)] += 1
                (k, n), = cnt.most_common(1)
                if n >= 3 and 2 * n > len(cs) and sum(v == n for v in cnt.values()) == 1:
                    lines.append((k[0], k[1], k[1]))
            if len(lines) != 1: continue
            e, a_, b_ = lines[0]
            sc = np.full((2 * h - 1, 2 * w - 1), -1)
            if e == "fv": sc[a_, :] = 1
            elif e == "fh": sc[:, a_] = 1
            elif e == "T": sc[(np.subtract.outer(np.arange(2 * h - 1), np.arange(2 * w - 1))) == 2 * a_] = 1
            else: sc[(np.add.outer(np.arange(2 * h - 1), np.arange(2 * w - 1))) == 2 * a_] = 1
            best.append((1, e, sc))
        for e in (("fh", "fv", "T", "aT") if e0 == "best" else () if e0 == "line" else (e0,)):
            a, cf, fl, v = f.tables(e)
            box = np.zeros_like(v); box[2 * r0:2 * r1 + 1, 2 * c0:2 * c1 + 1] = True
            sc = np.where(v & box, a - cf, -10 ** 6); best.append((sc.max(), e, sc))
        best.sort(key=lambda t: -t[0])
        if len(best) > 1 and best[0][0] == best[1][0]: return None
        _, e, sc = best[0]
        if sc.max() <= 0: continue
        top = np.argwhere(sc == sc.max())
        keys = {(int(y - x) if e == "T" else int(y + x) if e == "aT" else int(y) if e == "fv" else int(x)) for y, x in top}
        if len(keys) != 1: return None
        cy2, cx2 = map(int, top[0])
        side = lambda y, x: np.sign((2 * y - cy2) if e == "fv" else (2 * x - cx2) if e == "fh" else
                                    ((2 * y - cy2) - (2 * x - cx2)) if e == "T" else ((2 * y - cy2) + (2 * x - cx2)))
        cnt = {1: 0, -1: 0}
        for y, x in ob:
            s_ = side(y, x)
            if s_: cnt[int(s_)] += 1
        if cnt[1] == cnt[-1]: continue
        keep = 1 if cnt[1] > cnt[-1] else -1
        for y, x in ob:
            if side(y, x) == -keep: out[y, x] = bgc
        for y, x in ob:
            if side(y, x) == keep:
                q = image(e, cy2, cx2, y, x)
                if q is None or not (0 <= q[0] < h and 0 <= q[1] < w): return None
                out[q] = G[y, x]
        acted = True
    return out.tolist() if acted else None


def fam_fold_dominant(train):
    if not _same(train): return
    for e, conn in product(("line", "best", "fh", "fv", "T", "aT"), ("m8", "c8")):
        yield (f"geom-fold-dominant[{e},{conn}]", 4, lambda g, e=e, conn=conn: fold_dominant(g, e, conn))


def twisted_quadrants(g, dihedral):
    """Colour-twisted D2 symmetry: the picture (fg bbox, even sides) is split into quadrants; the fullest
    quadrant Q is the motif; every other quadrant equals e(Q) (e = mirror / rotation taking Q there) up to a
    colour substitution sigma_e induced from that quadrant's visible hint cells."""
    G = to_np(g); bgc = bg_of(g); fg = G != bgc
    ys, xs = np.nonzero(fg)
    if not len(ys): return None
    h, w = G.shape; R0, C0, R1, C1 = ys.min(), xs.min(), ys.max(), xs.max(); cands = []
    for sa, sb in ((0, 0), (0, 1), (1, 0), (1, 1)):     # motif = largest solid square at a bbox corner
        k = 0
        while True:
            k1 = k + 1
            y0 = R0 if sa == 0 else R1 - k1 + 1; x0 = C0 if sb == 0 else C1 - k1 + 1
            if y0 < 0 or x0 < 0 or y0 + k1 > h or x0 + k1 > w or not fg[y0:y0 + k1, x0:x0 + k1].all(): break
            k = k1
        if k < 2: continue
        r0 = R0 if sa == 0 else R1 - 2 * k + 1; c0 = C0 if sb == 0 else C1 - 2 * k + 1
        r1, c1 = r0 + 2 * k - 1, c0 + 2 * k - 1
        if r0 < 0 or c0 < 0 or r1 >= h or c1 >= w or R1 > r1 or C1 > c1: continue
        cands.append((k, sa, sb, r0, c0, r1, c1))
    if len(cands) != 1: return None
    k, sa, sb, r0, c0, r1, c1 = cands[0]
    P = G[r0:r1 + 1, c0:c1 + 1].copy(); qh = qw = k
    quads = {(a, b): P[a * qh:(a + 1) * qh, b * qw:(b + 1) * qw] for a in (0, 1) for b in (0, 1)}
    full = [(sa, sb)]
    sa, sb = full[0]; Q = quads[full[0]]
    for (a, b), T_ in quads.items():
        if (a, b) == (sa, sb): continue
        if dihedral == "mirror":
            M = Q[::-1 if a != sa else 1, ::-1 if b != sb else 1]
        else:                                           # rotation about the picture centre
            if qh != qw: return None
            k = {(0, 1): 3, (1, 1): 2, (1, 0): 1}[((a - sa) % 2, (b - sb) % 2)] if (sa, sb) == (0, 0) else None
            if k is None: return None
            M = np.rot90(Q, k)
        sig = {}
        for u, v in zip(M.ravel(), T_.ravel()):
            if v == bgc: continue
            if sig.setdefault(int(u), int(v)) != v: return None
        if not sig: return None
        quads[(a, b)][:, :] = np.vectorize(lambda u: sig.get(int(u), bgc))(M)   # unseen colours vanish
    out = G.copy(); out[r0:r1 + 1, c0:c1 + 1] = P
    return out.tolist()


def fam_twisted_quadrants(train):
    if not _same(train): return
    for d in ("mirror", "rotation"):
        yield (f"geom-twisted-quadrants[{d}]", 5, lambda g, d=d: twisted_quadrants(g, d))


# --------------------------------------------------------------------------- product lattice of sites

def product_sites(g, paint, conn):
    """Congruent copies of one motif sit at (row, col) anchors; the anchor set is completed to the full
    Cartesian product rows x cols (a possibly irregular rectangular lattice), new copies painted `paint`."""
    bgc = bg_of(g); h, w = H(g), W(g)
    obs = objects(g, bgc, True, conn == "c8")
    if len(obs) < 3: return None
    shapes = {}
    for ob in obs:
        r0, c0, _, _ = bbox(ob)
        shapes.setdefault(tuple(sorted((y - r0, x - c0, g[y][x]) for y, x in ob)), []).append((r0, c0))
    if len(shapes) != 1: return None
    (shape, anchors), = shapes.items()
    rows = sorted({a for a, _ in anchors}); cols = sorted({b for _, b in anchors})
    if len(rows) * len(cols) == len(anchors): return None
    out = [r[:] for r in g]
    for a in rows:
        for b in cols:
            if (a, b) in anchors: continue
            for dy, dx, v in shape:
                y, x = a + dy, b + dx
                if not (0 <= y < h and 0 <= x < w) or g[y][x] != bgc: return None
                out[y][x] = v if paint is None else paint
    return out


def fam_product_sites(train):
    if not _same(train): return
    nc = _new_colour(train)
    for paint, conn in product([None] + ([nc] if nc is not None else []), ("c8", "m8")):
        yield (f"geom-product-sites[{conn}{'' if paint is None else ',paint=c%d' % paint}]", 4,
               lambda g, paint=paint, conn=conn: product_sites(g, paint, conn))


# --------------------------------------------------------------------------- similarity-transform completion

def block_factor(P, bgc):
    """Largest f such that the picture is an f-fold upscaling of a smaller one."""
    h, w = len(P), len(P[0])
    for f in range(min(h, w), 1, -1):
        if h % f or w % f: continue
        if all(P[y][x] == P[y - y % f][x - x % f] for y in range(h) for x in range(w)): return f
    return 1


def similarity_complete(g, tie):
    """A template (the multicolour object with the most colours) exists; elsewhere only its 'shown' colours
    appear (colours of the template also present outside it), as copies of the template under a similarity
    transform (D8 x integer scale of the template's coarsest resolution x translation). Each copy is found by
    exact matching of its shown cells and completed with the template's hidden colours."""
    bgc = bg_of(g); h, w = H(g), W(g)
    seprow = {y for y in range(h) if len(set(g[y])) == 1 and g[y][0] != bgc}
    sepcol = {x for x in range(w) if len({g[y][x] for y in range(h)}) == 1 and g[0][x] != bgc}
    m = [[bgc if (y in seprow or x in sepcol) else g[y][x] for x in range(w)] for y in range(h)]
    obs = objects(m, bgc, True, False)
    if len(obs) < 2: return None
    ncol = [len({m[y][x] for y, x in o}) for o in obs]
    top = max(ncol)
    if top < 2 or ncol.count(top) != 1: return None
    T = obs[ncol.index(top)]; Tset = set(T)
    r0, c0, r1, c1 = bbox(T)
    P = [[m[y][x] if (y, x) in Tset else bgc for x in range(c0, c1 + 1)] for y in range(r0, r1 + 1)]
    f = block_factor(P, bgc); P0 = [row[::f] for row in P[::f]]
    tcols = {v for r in P0 for v in r} - {bgc}
    outside = {m[y][x] for y in range(h) for x in range(w) if m[y][x] != bgc and (y, x) not in Tset}
    shown = tcols & outside; hidden = tcols - shown
    if not shown or not hidden or outside - tcols: return None
    seeds = [o for o in objects(m, bgc, True, True) if (o[0][0], o[0][1]) not in Tset]
    used = set(); out = [r[:] for r in g]; acted = False
    tcy, tcx = (r0 + r1) / 2 - (h - 1) / 2, (c0 + c1) / 2 - (w - 1) / 2
    for sd in seeds:
        if (sd[0][0], sd[0][1]) in used: continue
        sc = m[sd[0][0]][sd[0][1]]; sb = bbox(sd); sshape = {(y - sb[0], x - sb[1]) for y, x in sd}
        cands = {}
        for D, k in product(D8, range(1, 7)):
            Q = D8[D](P0); Q = [[v for v in row for _ in range(k)] for row in Q for _ in range(k)]
            qh, qw = len(Q), len(Q[0])
            qcells = [(y, x) for y in range(qh) for x in range(qw) if Q[y][x] == sc]
            for comp in objects([[1 if Q[y][x] == sc else 0 for x in range(qw)] for y in range(qh)], 0, True, True):
                cb = bbox(comp)
                if {(y - cb[0], x - cb[1]) for y, x in comp} != sshape: continue
                oy, ox = sb[0] - cb[0], sb[1] - cb[1]
                ok = True; paint = []; cover = []
                for y in range(qh):
                    for x in range(qw):
                        v = Q[y][x]
                        if v == bgc: continue
                        yy, xx = y + oy, x + ox
                        if not (0 <= yy < h and 0 <= xx < w):
                            if v in shown: ok = False; break
                            continue                                  # hidden parts are clipped at the edge
                        if v in shown:
                            if m[yy][xx] != v: ok = False; break
                            cover.append((yy, xx))
                        elif m[yy][xx] != bgc and m[yy][xx] != v: ok = False; break
                        else: paint.append((yy, xx, v))
                    if not ok: break
                if ok and paint:
                    key = tuple(sorted(paint))
                    cands.setdefault(key, (D, cover))
        if not cands: continue
        if len(cands) > 1:
            if tie != "positional": return None
            scy, scx = (sb[0] + sb[2]) / 2 - (h - 1) / 2, (sb[1] + sb[3]) / 2 - (w - 1) / 2
            fy, fx = (scy * tcy < 0), (scx * tcx < 0)
            want = {(False, False): "id", (False, True): "fh", (True, False): "fv", (True, True): "r180"}[(fy, fx)]
            pick = [k_ for k_, (D, _) in cands.items() if D == want]
            if len(pick) != 1: return None
            key = pick[0]
        else:
            key = next(iter(cands))
        for y, x, v in key: out[y][x] = v
        for p in cands[key][1]: used.add(p)
        acted = True
    return out if acted else None


def fam_similarity_complete(train):
    if not _same(train): return
    for tie in ("unique", "positional"):
        yield (f"geom-similarity-complete[{tie}]", 5, lambda g, tie=tie: similarity_complete(g, tie))


# --------------------------------------------------------------------------- folding along a mirror line

def fold(g, base):
    """The grid is folded along its central separator line (a full row / column of one colour): the output is
    the `base` half with the mirror image of the other half showing through its background cells."""
    gg = g if base in ("L", "R") else [list(r) for r in zip(*g)]
    h, w = H(gg), W(gg); bgc = bg_of(g)
    if w % 2 == 0: return None
    m = w // 2
    if len({gg[y][m] for y in range(h)}) != 1 or gg[0][m] == bgc: return None
    A = [r[:m] for r in gg]; B = [r[m + 1:][::-1] for r in gg]
    if base in ("R", "B"): A, B = [r[::-1] for r in B], [r[::-1] for r in A]
    out = [[a if a != bgc else b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)]
    return out if base in ("L", "R") else [list(r) for r in zip(*out)]


def fam_fold(train):
    i, o = train[0]["input"], train[0]["output"]
    if not ((H(o) == H(i) and 2 * W(o) + 1 == W(i)) or (W(o) == W(i) and 2 * H(o) + 1 == H(i))): return
    for base in ("L", "R", "T", "B"):
        yield (f"geom-fold[base={base}]", 3, lambda g, base=base: fold(g, base))


# --------------------------------------------------------------------------- reflective (frieze) extension

def frieze_index(L, n, mode, rev):
    """Index map of a 1-D frieze: tile (translation), pp-dup (glide/mirror, boundary repeated),
    pp-shared (mirror sharing the boundary cell)."""
    if mode == "tile": p, f = n, (lambda t: t)
    elif mode == "dup": p, f = 2 * n, (lambda t: t if t < n else 2 * n - 1 - t)
    else:
        if n < 2: return None
        p, f = 2 * n - 2, (lambda t: t if t < n else 2 * n - 2 - t)
    idx = [f(k % p) for k in range(L)]
    return [n - 1 - v for v in idx] if rev else idx


def frieze_len(n, mode, m):
    return m * (n - 1) + 1 if mode == "shared" else m * n


def fam_frieze(train):
    """Output = the input continued along each axis as a frieze (translation, mirror with repeated or shared
    boundary), m copies; per-axis mode, copy count and starting orientation induced from the training pairs."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) == (H(i), W(i)) or H(o) < H(i) or W(o) < W(i): return
    def ms(n, L, mode):
        if mode == "shared": return (L - 1) // (n - 1) if n > 1 and (L - 1) % (n - 1) == 0 else None
        return L // n if L % n == 0 else None
    for my, mx in product(("tile", "dup", "shared"), repeat=2):
        ky, kx = ms(H(i), H(o), my), ms(W(i), W(o), mx)
        if not ky or not kx or ky * kx == 1 or ky > 8 or kx > 8: continue
        if all(ms(H(p["input"]), H(p["output"]), my) == ky and ms(W(p["input"]), W(p["output"]), mx) == kx for p in train) is False: continue
        for ry, rx in product((False, True), repeat=2):
            if (ky == 1 and ry) or (kx == 1 and rx): continue
            def fn(g, my=my, mx=mx, ky=ky, kx=kx, ry=ry, rx=rx):
                n, m = H(g), W(g)
                iy = frieze_index(frieze_len(n, my, ky), n, my, ry); ix = frieze_index(frieze_len(m, mx, kx), m, mx, rx)
                if iy is None or ix is None: return None
                return [[g[a][b] for b in ix] for a in iy]
            yield (f"geom-frieze[{my}x{ky}{',rev' if ry else ''};{mx}x{kx}{',rev' if rx else ''}]", 3, fn)


# --------------------------------------------------------------------------- symmetry as a feature

from gdsl import D8, crop, split_panels

INV = {"fh": "fh", "fv": "fv", "r180": "r180", "T": "T", "aT": "aT", "r90": "r90", "r270": "r270"}


def signature(p):
    """Set of non-identity D4 elements leaving the picture (a list grid) invariant about its own centre."""
    sq = H(p) == W(p)
    return frozenset(e for e in ("fh", "fv", "r180", "T", "aT", "r90") if (sq or e in ("fh", "fv", "r180")) and D8[e](p) == p)


def parts(g, src):
    bg = bg_of(g)
    if src == "panels":
        sp = split_panels(g)
        return [p for p in sp[0]] if sp else []
    if src == "blocks":                               # k equal square blocks along the long side
        h, w = H(g), W(g)
        if h > w and h % w == 0: return [g[k:k + w] for k in range(0, h, w)]
        if w > h and w % h == 0: return [[r[k:k + h] for r in g] for k in range(0, w, h)]
        return []
    obs = objects(g, bg, True, src == "c8")
    return [crop(g, bbox(o)) for o in obs if len(o) >= 3]


def pick_by_symmetry(g, src, how):
    ps = parts(g, src)
    if len(ps) < 2: return None
    sig = [signature(p) for p in ps]
    if how.startswith("has:") or how.startswith("lacks:"):
        e = how.split(":")[1]; want = how.startswith("has:")
        hits = [p for p, s in zip(ps, sig) if (e in s) == want]
    elif how == "odd-signature":
        from collections import Counter
        cnt = Counter(sig); hits = [p for p, s in zip(ps, sig) if cnt[s] == 1]
        if len(cnt) != 2: return None
    else:
        k = [len(s) for s in sig]; t = max(k) if how == "most-symmetric" else min(k)
        hits = [p for p, v in zip(ps, k) if v == t]
    return hits[0] if len(hits) == 1 else None


def fam_select_by_symmetry(train):
    """Crop the unique object / panel whose symmetry group has (lacks) an element, or is the odd one out."""
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) >= H(i) * W(i): return
    hows = [f"{m}:{e}" for m in ("has", "lacks") for e in ("fh", "fv", "r180", "T", "aT", "r90")] + \
           ["odd-signature", "most-symmetric", "least-symmetric"]
    for src in ("c8", "m8", "panels", "blocks"):
        for how in hows:
            yield (f"geom-select-by-symmetry:{src}[{how}]", 4, lambda g, src=src, how=how: pick_by_symmetry(g, src, how))


def fundamental_domain(g, part, req):
    bg = bg_of(g); h, w = H(g), W(g)
    cells = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg]
    if not cells: return None
    p = crop(g, bbox(cells)); sg = signature(p)
    if not set(req) <= sg: return None
    ph, pw = H(p), W(p)
    if part == "quadrant": return [r[:(pw + 1) // 2] for r in p[:(ph + 1) // 2]]
    if part == "left": return [r[:(pw + 1) // 2] for r in p]
    return [r[:] for r in p[:(ph + 1) // 2]]


def fam_fundamental_domain(train):
    """Output = the fundamental domain (top-left quadrant / half) of the symmetric foreground picture."""
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) >= H(i) * W(i): return
    for part, req in (("quadrant", ("r180",)), ("left", ("fh",)), ("top", ("fv",))):
        yield (f"geom-fundamental-domain:{part}", 3, lambda g, part=part, req=req: fundamental_domain(g, part, req))


def paired_mask(g, group, centre, bgc=None):
    G = to_np(g); h, w = G.shape; bgc = bg_of(g) if bgc is None else bgc; fg = G != bgc
    if centre == "grid": cy2, cx2 = h - 1, w - 1
    else:
        ys, xs = np.nonzero(fg)
        if not len(ys): return None
        cy2, cx2 = ys.min() + ys.max(), xs.min() + xs.max()
    M = np.zeros_like(fg)
    for y, x in zip(*np.nonzero(fg)):
        ok = True
        for e in GROUPS[group]:
            q = image(e, cy2, cx2, y, x)
            if q is None or not (0 <= q[0] < h and 0 <= q[1] < w) or G[q] != G[y, x]: ok = False; break
        M[y, x] = ok
    return G, M


def fam_orbit_recolour(train):
    """Foreground cells are recoloured according to whether their whole G-orbit (about the grid / picture
    centre) is present; the (colour, paired) -> colour table is induced from training."""
    if not _same(train): return
    st = None
    for p in train:
        i, o = to_np(p["input"]), to_np(p["output"])
        s_ = {int(c) for c in np.unique(i) if (o[i == c] == c).all()}
        st = s_ if st is None else st & s_
    bgs = [None] + ([next(iter(st))] if st and len(st) == 1 else [])
    for grp, centre, bgx in product(("H", "V", "HV", "R2", "D", "A", "R4", "D4"), ("grid", "fg"), bgs):
        if True:
            table = {}; ok = True
            for p in train:
                r = paired_mask(p["input"], grp, centre, bgx)
                if r is None: ok = False; break
                G, M = r; O = to_np(p["output"]); bgc = bg_of(p["input"]) if bgx is None else bgx
                for y, x in zip(*np.nonzero(G != bgc)):
                    k = (int(G[y, x]), bool(M[y, x]))
                    if table.setdefault(k, int(O[y, x])) != O[y, x]: ok = False; break
                if not ok or (O[G == bgc] != bgc).any(): ok = False; break
            if not ok or all(k[0] == v for k, v in table.items()): continue
            if len({v for k, v in table.items() if k[1]} ^ {v for k, v in table.items() if not k[1]}) == 0: continue

            def fn(g, grp=grp, centre=centre, table=table, bgx=bgx):
                r = paired_mask(g, grp, centre, bgx)
                if r is None: return None
                G, M = r; out = G.copy(); bgc = bg_of(g) if bgx is None else bgx
                for y, x in zip(*np.nonzero(G != bgc)):
                    k = (int(G[y, x]), bool(M[y, x]))
                    if k not in table: return None
                    out[y, x] = table[k]
                return out.tolist()
            yield (f"geom-orbit-recolour[{grp},{centre}{'' if bgx is None else ',bg=static'}]", 4, fn)


FAMILIES = (fam_sym_complete_bg, fam_sym_repair_occ, fam_symmetrize_colour, fam_fold_dominant, fam_twisted_quadrants, fam_frieze, fam_product_sites, fam_fold, fam_similarity_complete, fam_select_by_symmetry, fam_fundamental_domain, fam_orbit_recolour)
