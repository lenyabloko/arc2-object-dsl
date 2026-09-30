"""Family for ARC task 135a2760 -- concept: DEFECT ANNEALING (crystallography: healing point defects of a lattice).

Reading of the task
-------------------
The grid shows one or more framed windows (a closed, single-colour rectangular outline).  Inside each window lies a
small crystal: a motif repeated by translation along the window, but a few cells are point defects (wrong colour).
Annealing restores the perfect lattice: every cell is reset to the colour its lattice site carries in the majority
of unit cells.  Everything outside the windows (background, frames) is left untouched.

How the lattice is found (no task constants):
  * windows   = innermost connected single-colour components that are exactly the outline of their bounding box
                (interior >= 1x1); if there are none, the whole grid is one window.
  * unit cell = the rectangular translation period (py, px) of the window's interior with minimum description
                length in bits: py*px*log2(k) for the motif + (log2(area) + log2(k-1)) per defect (k = colours
                present).  Along each axis a period is admissible if it repeats >= min_repeats whole times, or equals
                the full side (no translation along that axis), so stripe crystals of either orientation and 2-D
                lattices are covered by the same search.
  * repair    = each cell takes the majority colour of its lattice site (r mod py, c mod px).

Parameters (declared finite domain, induced from train; first fit wins):
  min_repeats in {3, 2, 4}   fewest unit cells that must vote on every lattice site.
"""

from collections import Counter
from math import log2


def _components(g):
    """4-connected single-colour components: list of (colour, set_of_cells)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c]:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], set()
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.add((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append((col, cells))
    return comps


def _windows(g):
    """Interiors (r0, c0, r1, c1 inclusive) of the innermost rectangular outlines; whole grid if none."""
    frames = []
    for col, cells in _components(g):
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
        if r1 - r0 < 2 or c1 - c0 < 2:
            continue
        outline = {(y, x) for y in range(r0, r1 + 1) for x in (c0, c1)} | \
                  {(y, x) for x in range(c0, c1 + 1) for y in (r0, r1)}
        if cells == outline:
            frames.append((r0 + 1, c0 + 1, r1 - 1, c1 - 1))

    def inside(a, b):  # interior a lies inside interior b (and differs)
        return a != b and b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]

    inner = [f for f in frames if not any(inside(o, f) for o in frames)]
    if not inner:
        inner = [(0, 0, len(g) - 1, len(g[0]) - 1)]
    return inner


def _periods(n, reps):
    """Admissible periods along an axis of length n: the full length (no translation along this axis), or any period
    that repeats at least `reps` whole times, so every lattice site is voted on by >= reps unit cells."""
    return [p for p in range(1, n + 1) if p == n or p * reps <= n]


def _anneal_patch(patch, reps):
    """Return the patch with every cell replaced by the majority colour of its lattice site; the unit cell is the one
    of minimum description length (bits): motif = py*px*log2(k), each defect = log2(area) + log2(k-1)."""
    h, w = len(patch), len(patch[0])
    k = len({v for row in patch for v in row})
    if k < 2:
        return [list(row) for row in patch]
    motif_bits = log2(k)
    defect_bits = log2(h * w) + log2(k - 1)
    best = None
    for py in _periods(h, reps):
        for px in _periods(w, reps):
            sites = {}
            for r in range(h):
                for c in range(w):
                    sites.setdefault((r % py, c % px), Counter())[patch[r][c]] += 1
            motif = {s: cnt.most_common(1)[0][0] for s, cnt in sites.items()}
            defects = sum(sum(cnt.values()) - cnt[motif[s]] for s, cnt in sites.items())
            key = (py * px * motif_bits + defects * defect_bits, py * px)
            if best is None or key < best[0]:
                best = (key, py, px, motif)
    _, py, px, motif = best
    return [[motif[(r % py, c % px)] for c in range(w)] for r in range(h)]


def _anneal(g, reps):
    out = [list(row) for row in g]
    for r0, c0, r1, c1 in _windows(g):
        patch = [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
        fixed = _anneal_patch(patch, reps)
        for i, row in enumerate(fixed):
            out[r0 + i][c0:c1 + 1] = row
    return out


def fam_defect_annealing(train):
    for reps in (3, 2, 4):
        fn = (lambda R: (lambda g: _anneal(g, R)))(reps)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("crystallography:defect_annealing[min_repeats=%d]" % reps, 3, fn)
            return


FAMILIES = (fam_defect_annealing,)
