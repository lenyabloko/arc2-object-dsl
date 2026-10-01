"""Concept family "denoise" (test-blind; anti-unified from the lines e26a3af2 and 0607ce86, train pairs only).

One generator: the clean image is constant on the classes of a product partition  class(r, c) = (rho(r), kappa(c)),
and every class is repainted with its majority colour (this is what erases the scattered noise cells).
Each axis labelling is one of two kinds of the same idea "which lines of this axis are copies of each other":
  bands   : the axis is cut into maximal runs of lines; all lines of a run share one label
            (constant along the axis inside the run -> colour panels: row bands, column bands, 2-D block grids)
  lattice : (start, size, period, count), count >= 2, period >= size; a line inside copy i at offset a gets label a
            (copies share labels -> repeated tiles); lines outside every copy get the label BOT, and every cell with
            a BOT row or column belongs to one background class.
Model choice per grid = minimum description length: #changed cells + #classes (for bands: #panels).
  bands  : alternate row bands (runs of the tuple of segment majorities over the current column bands) and column
           bands, starting from either axis; every visited state is MDL-merged (adjacent bands are merged while the
           description does not get longer).
  lattice: every (start, size, period, count) per axis is scored on full lines (per-offset vote tables), the best
           few per axis are combined and all combinations are scored exactly in 2-D.
Parameters: rows, cols in {bands, lattice, any} (any = whichever kind is shorter on that grid) and
outside in {repaint, keep} (what happens to the background class BOT of a lattice).
"""

CARD = "concept_denoise"
CONCEPT = "denoise"
MEMBERS = ["e26a3af2", "0607ce86"]
READING = {
    "generator": "Split the grid into classes = row class x column class, where an axis is either cut into bands "
                 "(lines of a band share a class: colour panels) or folded by a lattice (lines at the same offset "
                 "of every tile copy share a class; lines outside the copies are background), and repaint every "
                 "class with its majority colour, which erases the scattered noise.",
    "stop": "One pass: each class is painted once; bands end where the per-segment majority colours change and are "
            "merged while merging does not lengthen the description (#changed cells + #classes); a lattice has "
            "exactly the copies found in the input (nothing is extended); the grid edge closes the outer bands.",
    "params": "rows ∈ {bands, lattice, any} · cols ∈ {bands, lattice, any} · outside ∈ {repaint, keep} · "
              "per grid: band cuts / lattice (start, size, period >= size, count >= 2) chosen by least "
              "#changed cells + #classes",
    "participants": "Classes: blocks of row bands x column bands, or same-offset cells of all lattice copies, plus "
                    "one background class (cells outside the copies). Noise: every cell whose colour differs from "
                    "its class majority.",
    "preconditions": "Output has the input's shape in every train pair and uses only input colours; the input is "
                     "covered by such a partition with noise a minority in every class; the repaint reproduces the "
                     "train outputs.",
}

_K = 24        # search breadth: best lattice structures per axis that go to the exact 2-D scoring
_NC = 10       # ARC palette size
_BOT = None    # label of lines outside every lattice copy


def _shape(g):
    return (len(g), len(g[0]) if g else 0)


def _freq(g):
    f = [0] * _NC
    for row in g:
        for v in row:
            f[v] += 1
    return f


def _T(g):
    return [list(col) for col in zip(*g)]


# ---------------------------------------------------------------- shared: classes, description length, repaint
def _class_counts(g, rl, cl):
    """Colour counts per class (row label, column label); one background class for BOT lines."""
    ri, ci = {}, {}
    rid = [-1 if a is _BOT else ri.setdefault(a, len(ri)) for a in rl]
    cid = [-1 if b is _BOT else ci.setdefault(b, len(ci)) for b in cl]
    nc, bot = len(ci), len(ri) * len(ci)
    flat = [0] * ((bot + 1) * _NC)
    for r, a in enumerate(rid):
        row = g[r]
        if a < 0:
            for v in row:
                flat[bot * _NC + v] += 1
            continue
        base = a * nc
        for c, b in enumerate(cid):
            flat[(base + b if b >= 0 else bot) * _NC + row[c]] += 1
    return rid, cid, nc, bot, flat


def _score(g, rl, cl):
    """Description length: #changed cells (non-majority) + #classes."""
    *_, flat = _class_counts(g, rl, cl)
    cost = 0
    for k in range(0, len(flat), _NC):
        cell = flat[k:k + _NC]
        s = sum(cell)
        if s:
            cost += s - max(cell) + 1
    return cost


def _repaint(g, rl, cl, outside):
    rid, cid, nc, bot, flat = _class_counts(g, rl, cl)
    f = _freq(g)
    maj = [max(range(_NC), key=lambda v: (flat[k + v], f[v], -v)) for k in range(0, len(flat), _NC)]
    out = [list(r) for r in g]
    for r, a in enumerate(rid):
        for c, b in enumerate(cid):
            k = bot if a < 0 or b < 0 else a * nc + b
            if k != bot or outside == "repaint":
                out[r][c] = maj[k]
    return out


# ---------------------------------------------------------------- axis kind: bands
class _Counts:
    """2-D prefix counts per colour: majority colour / #non-majority cells of any rectangle."""

    def __init__(self, g):
        h, w = _shape(g)
        self.cols = sorted({v for r in g for v in r})
        self.P = {}
        for k in self.cols:
            P = [[0] * (w + 1) for _ in range(h + 1)]
            for r in range(h):
                run, row, prev = 0, P[r + 1], P[r]
                for c in range(w):
                    run += g[r][c] == k
                    row[c + 1] = prev[c + 1] + run
            self.P[k] = P
        self.memo = {}

    def block(self, r0, r1, c0, c1):
        key = (r0, r1, c0, c1)
        if key not in self.memo:
            best, bk = -1, None
            for k in self.cols:
                P = self.P[k]
                n = P[r1][c1] - P[r0][c1] - P[r1][c0] + P[r0][c0]
                if n > best:
                    best, bk = n, k
            self.memo[key] = (bk, (r1 - r0) * (c1 - c0) - best)
        return self.memo[key]


def _runs(labels):
    out, s = [], 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[s]:
            out.append((s, i))
            s = i
    return out


def _bands(cnt, S, ax, n):
    """Runs of lines of axis ax by the tuple of majority colours over the other axis' current bands."""
    if ax == 0:
        return _runs([tuple(cnt.block(i, i + 1, a, b)[0] for a, b in S[1]) for i in range(n)])
    return _runs([tuple(cnt.block(a, b, i, i + 1)[0] for a, b in S[0]) for i in range(n)])


def _merge(cnt, S):
    """MDL merging of adjacent bands (either axis) while the description (#changed cells + #panels) does not get
    longer; the change of one merge is computed against the other axis' bands only."""
    S = [list(S[0]), list(S[1])]

    def nz(ax, seg, o):
        return (cnt.block(seg[0], seg[1], o[0], o[1]) if ax == 0 else cnt.block(o[0], o[1], seg[0], seg[1]))[1]
    while True:
        best = None
        for ax in (0, 1):
            O = S[1 - ax]
            for i in range(len(S[ax]) - 1):
                a, b = S[ax][i], S[ax][i + 1]
                d = sum(nz(ax, (a[0], b[1]), o) - nz(ax, a, o) - nz(ax, b, o) for o in O) - len(O)
                if d <= 0 and (best is None or d < best[0]):
                    best = (d, ax, i)
        if best is None:
            return S
        _, ax, i = best
        S[ax] = S[ax][:i] + [(S[ax][i][0], S[ax][i + 1][1])] + S[ax][i + 2:]


def _band_models(g):
    """(row labels, column labels) of every MDL-merged state visited by the row/column alternation."""
    h, w = _shape(g)
    cnt = _Counts(g)
    out, seen_out = [], set()
    for first in (0, 1):
        S, seen, ax = [[(0, h)], [(0, w)]], set(), first
        for _ in range(h + w + 2):
            S[ax] = _bands(cnt, S, ax, (h, w)[ax])
            key = (tuple(S[0]), tuple(S[1]))
            if key in seen:
                break
            seen.add(key)
            M = _merge(cnt, S)
            mk = (tuple(M[0]), tuple(M[1]))
            if mk not in seen_out:
                seen_out.add(mk)
                out.append(tuple([i for i, (a, b) in enumerate(M[x]) for _ in range(a, b)] for x in (0, 1)))
            ax = 1 - ax
    return out


# ---------------------------------------------------------------- axis kind: lattice
def _lattice_axis(g, bg):
    """Best (start, size, period, count) row structures, scored on full rows with every column its own class:
    cost = #non-bg cells + sum over offsets of (copies - majority count - non-bg count)."""
    H, W = _shape(g)
    nb = [sum(1 for v in row if v != bg) for row in g]
    N = sum(nb)
    out = []
    for p in range(1, H):
        nmax = (H - 1) // p + 1
        Gt = {}
        for s in range(H):
            cnts = [[0] * _NC for _ in range(W)]
            best, tot, nbs = [0] * W, 0, 0
            for i in range(nmax):
                r = s + i * p
                if r >= H:
                    break
                row = g[r]
                nbs += nb[r]
                for c in range(W):
                    d = cnts[c]
                    d[row[c]] += 1
                    if d[row[c]] > best[c]:
                        tot += 1
                        best[c] += 1
                if i >= 1:
                    Gt.setdefault(i + 1, [0] * H)[s] = (i + 1) * W - tot - nbs
        for n, arr in Gt.items():
            pre = [0]
            for v in arr:
                pre.append(pre[-1] + v)
            for h in range(1, p + 1):
                for r0 in range(0, H - (n - 1) * p - h + 1):
                    out.append((N + pre[r0 + h] - pre[r0], h, -n, r0, p))
    out.sort()
    res = []
    for _, h, n, r0, p in out[:_K]:
        lab = [_BOT] * H
        for i in range(-n):
            for a in range(h):
                lab[r0 + i * p + a] = a
        res.append(lab)
    return res


# ---------------------------------------------------------------- per-grid search (memoized per kind)
_MEMO = {}


def _axis_models(g, kind):
    key = (kind, tuple(map(tuple, g)))
    if key not in _MEMO:
        if kind == "bands":
            _MEMO[key] = _band_models(g)
        else:
            f = _freq(g)
            bg = max(range(_NC), key=lambda v: (f[v], -v))
            _MEMO[key] = (_lattice_axis(g, bg), _lattice_axis(_T(g), bg))
    return _MEMO[key]


def _best(g, kr, kc):
    """Least-description (row labels, column labels) with row kind in kr and column kind in kc."""
    key = ("best", kr, kc, tuple(map(tuple, g)))
    if key in _MEMO:
        return _MEMO[key]
    cands = []
    if "bands" in kr and "bands" in kc:
        cands += _axis_models(g, "bands")
    if "lattice" in kr or "lattice" in kc:
        LR, LC = _axis_models(g, "lattice")
        BM = _axis_models(g, "bands")
        rows = ([(1, R) for R in LR] if "lattice" in kr else []) + ([(0, m[0]) for m in BM] if "bands" in kr else [])
        cols = ([(1, C) for C in LC] if "lattice" in kc else []) + ([(0, m[1]) for m in BM] if "bands" in kc else [])
        cands += [(R, C) for lr, R in rows for lc, C in cols if lr or lc]   # bands x bands: joint models above
    best = None
    for R, C in cands:
        sk = ("score", id(R), id(C))
        if sk not in _MEMO:
            _MEMO[sk] = _score(g, R, C)
        s = _MEMO[sk]
        if best is None or s < best[0]:
            best = (s, R, C)
    _MEMO[key] = best
    return best


def _make(kr, kc, outside):
    def fn(grid):
        g = [list(r) for r in grid]
        if not g or not g[0]:
            raise ValueError("empty")
        found = _best(g, kr, kc)
        if found is None:
            raise ValueError("no model")
        return _repaint(g, found[1], found[2], outside)
    return fn


_KIND = {"bands": ("bands",), "lattice": ("lattice",), "any": ("bands", "lattice")}


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or not gi[0] or _shape(gi) != _shape(go):
            return
        if not {v for r in go for v in r} <= {v for r in gi for v in r}:
            return
    if all(p["input"] == p["output"] for p in train):
        return
    _MEMO.clear()
    progs = []
    for kr in ("bands", "lattice", "any"):
        for kc in ("bands", "lattice", "any"):
            lat = "lattice" in _KIND[kr] or "lattice" in _KIND[kc]
            for oi, outside in enumerate(("repaint", "keep") if lat else ("repaint",)):
                cost = 1 + (kr == "any") + (kc == "any") + (kr != kc and "any" not in (kr, kc)) + oi
                progs.append((cost, "denoise[rows=%s,cols=%s,outside=%s]" % (kr, kc, outside),
                              _make(_KIND[kr], _KIND[kc], outside)))
    progs.sort(key=lambda t: t[0])
    for cost, name, fn in progs:
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield name, cost, fn


FAMILIES = [fam]
