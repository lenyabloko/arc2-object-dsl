"""f931b4a8 -- linear algebra: Kronecker product.

The grid is four equal panels.  Two panels are tallies: their counts of non-background cells give the
output height and width.  A third panel is a motif whose minimal unit cell (smallest exact row/column
period) is the right-hand factor; the fourth panel is the left-hand factor.  Output = left (x) cell,
where block (I, J) is the unit cell with its background "slots" painted left[I][J]; that product is
tiled periodically and cropped to tally_h x tally_w.

Induced parameters (finite domains): background colour (colours seen in training inputs, most
frequent first), viewing frame (8 dihedral transforms: fixes which corner anchors the tiling) and the
assignment of the four panels to roles (24 permutations).
"""
from itertools import permutations
from collections import Counter

PANELS = ('TL', 'TR', 'BL', 'BR')

_T = lambda g: [list(r) for r in zip(*g)]
_FV = lambda g: [list(r) for r in g[::-1]]
_FH = lambda g: [list(r)[::-1] for r in g]
# (name, forward, inverse) for the 8 symmetries of the square
FRAMES = (
    ('id', lambda g: g, lambda g: g),
    ('flipH', _FH, _FH),
    ('flipV', _FV, _FV),
    ('rot180', lambda g: _FH(_FV(g)), lambda g: _FH(_FV(g))),
    ('transpose', _T, _T),
    ('rot90', lambda g: _FH(_T(g)), lambda g: _T(_FH(g))),
    ('rot270', lambda g: _FV(_T(g)), lambda g: _T(_FV(g))),
    ('antitranspose', lambda g: _FV(_FH(_T(g))), lambda g: _T(_FH(_FV(g)))),
)


def _panels(g):
    H, W = len(g), len(g[0]) if g else 0
    if H < 2 or W < 2 or H % 2 or W % 2:
        return None
    h, w = H // 2, W // 2
    return ([r[:w] for r in g[:h]], [r[w:] for r in g[:h]],
            [r[:w] for r in g[h:]], [r[w:] for r in g[h:]])


def _unit_cell(m):
    """Smallest exact (dividing) row and column periods of m -> the crystallographic unit cell."""
    h, w = len(m), len(m[0])
    p = next(p for p in range(1, h + 1) if h % p == 0 and all(m[r] == m[r % p] for r in range(h)))
    q = next(q for q in range(1, w + 1) if w % q == 0 and all(row[c] == row[c % q] for row in m for c in range(w)))
    return [row[:q] for row in m[:p]]


def _tally(m, bg):
    return sum(v != bg for row in m for v in row)


def _make(bg, roles, fwd, inv):
    ih, iw, ileft, icell = roles

    def fn(g):
        out = core(fwd(g))
        return None if out is None else ([] if not out else inv(out))

    def core(g):
        P = _panels(g)
        if P is None:
            return None
        H, W = _tally(P[ih], bg), _tally(P[iw], bg)
        cell = _unit_cell(P[icell])
        left = P[ileft]
        p, q = len(cell), len(cell[0])
        lh, lw = len(left), len(left[0])
        out = []
        for r in range(H):
            row = []
            for c in range(W):
                v = cell[r % p][c % q]
                row.append(v if v != bg else left[(r // p) % lh][(c // q) % lw])
            out.append(row)
        return out
    return fn


def _grid_shape(o):
    """(rows, cols) of a non-empty rectangular grid with non-empty rows, else None."""
    try:
        if not o or not len(o[0]):
            return None
        w = len(o[0])
        return (len(o), w) if all(len(r) == w for r in o) else None
    except Exception:
        return None


# frames whose inverse transposes the H x W core output into W x H
_SWAPS = {'transpose', 'rot90', 'rot270', 'antitranspose'}


def fam_kronecker(train):
    if not train or any(_panels(p['input']) is None for p in train):
        return
    # Necessary condition (any bg/frame/roles): every output value is copied from the input.
    try:
        for p in train:
            ins = set(v for row in p['input'] for v in row)
            if any(v not in ins for row in p['output'] for v in row):
                return
    except Exception:
        pass
    freq = Counter(v for p in train for row in p['input'] for v in row)
    # Exact shape pre-filter: fn(input) is tally(ih) x tally(iw) (transposed by inv for swapping frames);
    # a candidate whose shape differs from a (proper) training output can never pass the equality test.
    shapes = [_grid_shape(p['output']) for p in train]
    use_filter = all(s is not None for s in shapes)
    if use_filter:
        # per frame, per pair: Counter of each panel of fwd(input), and panel sizes
        pc = {}
        try:
            for fname, fwd, inv in FRAMES:
                lst = []
                for p in train:
                    P = _panels(fwd(p['input']))
                    lst.append([(sum(len(r) for r in m), Counter(v for row in m for v in row)) for m in P])
                pc[fname] = lst
        except Exception:
            use_filter = False
    for bg, _ in freq.most_common():
      for fname, fwd, inv in FRAMES:
        if use_filter:
            tallies = [[n - c[bg] for n, c in pl] for pl in pc[fname]]
            swap = fname in _SWAPS
        for roles in permutations(range(4)):
            if use_filter:
                ih, iw = roles[0], roles[1]
                good = True
                for t, (oh, ow) in zip(tallies, shapes):
                    H, W = t[ih], t[iw]
                    if ((W, H) if swap else (H, W)) != (oh, ow):
                        good = False
                        break
                if not good:
                    continue
            fn = _make(bg, roles, fwd, inv)
            try:
                ok = all(fn(p['input']) == p['output'] for p in train)
            except Exception:
                ok = False
            if ok:
                ih, iw, il, ic = roles
                yield ('algebra:kronecker_product[bg=%d,frame=%s,height=tally(%s),width=tally(%s),left=%s,cell=unitcell(%s)]'
                       % (bg, fname, PANELS[ih], PANELS[iw], PANELS[il], PANELS[ic]), 3, fn)
                return


FAMILIES = (fam_kronecker,)
