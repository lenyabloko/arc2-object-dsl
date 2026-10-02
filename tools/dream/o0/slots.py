"""G72 slot values as action-binder wrappers (Fable v13 D41 / v14 O4-O5, Oct 2 2026).

Every family program is a drawing procedure fn(grid) -> grid. A slot value wraps fn without looking at the task:
  iterate=fixpoint      apply fn again to its own output until nothing changes (at most 10 steps)
  accept=no_overlap     cells that held input ink (not the input's background) and that fn changed are restored
  on_stop=paint(c)      at every stroke tip (a changed cell with exactly one changed 4-neighbour, the stroke running
                        from that neighbour to the tip) the next cell along the stroke is painted c; c is a colour
                        role: same (the stroke's colour), novel, new_in_some (colour_roles.py, G68)
  on_stop=turn(s)       from every stroke tip the stroke continues after a 90 degree turn to side s (left, right)
                        over background cells until the border or a non-background cell
The values and their order come from the T72' counts (results/o0/t72p_density_summary.json; G75 (b): >= 5 tasks
each, source tagged 'T72'). anchor values (intersection, midpoint) need the family's own anchor step and are not
wrappers; they are reported, not implemented here.

Binder policies (prior_check / t75_density with SLOTS=<policy>):
  mdl     all base programs first (unchanged order), then the slot variants; a slot can only fill a task no base
          program fits (G2: a slot value is a charged parameter, so the shorter base program wins every tie)
  default iterate=fixpoint and accept=no_overlap are the template's default values: for each base program the
          variant with both defaults, then each default alone, are tried before it; on_stop variants come after all
          base programs
No task ids; deterministic."""
from collections import Counter
import colour_roles as CR

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
SLOT_BITS = 2.0                                   # log2 |menu| per slot use (G2), 4-value menus


def _bg(g): return Counter(v for r in g for v in r).most_common(1)[0][0]


def _same(a, b): return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and a and len(a[0]) == len(b[0])


def w_iter(fn, n=10):
    """v1.1 (Oct 2 11:05 EDT): iterate only while the grid keeps its size (v1.0 iterated size-changing programs, whose
    grids grew until memory ran out; such a variant can never fit, so outcomes are unchanged)"""
    def f(g):
        x = fn(g)
        if not _same(g, x): return x
        for _ in range(n):
            y = fn(x)
            if not _same(x, y) or y == x: return x
            x = y
        return x
    return f


def w_noov(fn):
    def f(g):
        y = fn(g)
        if not _same(g, y): return y
        b = _bg(g)
        return [[g[r][k] if (g[r][k] != b and y[r][k] != g[r][k]) else y[r][k] for k in range(len(g[0]))] for r in range(len(g))]
    return f


def _tips(g, y):
    H, W = len(g), len(g[0])
    C = {(r, k) for r in range(H) for k in range(W) if y[r][k] != g[r][k]}
    out = []
    for r, k in C:
        nb = [(r + dr, k + dk) for dr, dk in N4 if (r + dr, k + dk) in C]
        if len(nb) == 1:
            pr, pk = nb[0]
            out.append(((r, k), (r - pr, k - pk)))
    return out


def w_stop_paint(fn, colour):
    def f(g):
        y = fn(g)
        if not _same(g, y): return y
        H, W = len(g), len(g[0]); z = [row[:] for row in y]
        for (r, k), (dr, dk) in _tips(g, y):
            i, j = r + dr, k + dk
            if 0 <= i < H and 0 <= j < W:
                z[i][j] = y[r][k] if colour == 'same' else colour
        return z
    return f


def w_turn(fn, side):
    def f(g):
        y = fn(g)
        if not _same(g, y): return y
        H, W = len(g), len(g[0]); b = _bg(g); z = [row[:] for row in y]
        for (r, k), (dr, dk) in _tips(g, y):
            d = (-dk, dr) if side == 'left' else (dk, -dr)
            i, j = r + d[0], k + d[1]
            while 0 <= i < H and 0 <= j < W and z[i][j] == b:
                z[i][j] = y[r][k]; i += d[0]; j += d[1]
        return z
    return f


def variants(name, cost, fn, train):
    """(default variants, late variants) of one base program"""
    d = [(name + '|iterate=fixpoint,accept=no_overlap', cost + 2 * SLOT_BITS, w_noov(w_iter(fn))),
         (name + '|iterate=fixpoint', cost + SLOT_BITS, w_iter(fn)), (name + '|accept=no_overlap', cost + SLOT_BITS, w_noov(fn))]
    cols = [('same', 'same')]
    for role, val in (('novel', CR.novel_colour(train)), ('new_in_some', CR.new_in_some(train))):
        if val is not None and val not in [v for _, v in cols]: cols.append((role, val))
    late = [(name + '|on_stop=paint(%s)' % role, cost + SLOT_BITS + 1, w_stop_paint(fn, val)) for role, val in cols]
    late += [(name + '|on_stop=turn(%s)' % s, cost + SLOT_BITS + 1, w_turn(fn, s)) for s in ('left', 'right')]
    return d, late


class Augmented:
    """a family module seen through the slot-augmented action binder"""
    def __init__(self, M, policy, max_base=40):
        self.M, self.policy, self.max_base = M, policy, max_base
        self.MEMBERS = list(getattr(M, 'MEMBERS', []))
        self.FAMILIES = [self.fam]

    def fam(self, train):
        base = [p for f in self.M.FAMILIES for p in f(train)]
        defaults, late = [], []
        for i, (name, cost, fn) in enumerate(base):
            d, l = variants(name, cost, fn, train) if i < self.max_base else ([], [])
            late += l
            if self.policy == 'default':
                for v in d: yield v
            else:
                defaults += d
            yield name, cost, fn
        for v in defaults + late: yield v
