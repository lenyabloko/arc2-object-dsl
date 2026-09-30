"""Family: parallel-plate capacitor field (physics / electrostatics).

Every straight line segment of non-background cells is a conducting plate.  Between two parallel plates the
(ideal, fringe-free) field is uniform and runs perpendicular to the plates, and it exists only where the plates
face each other, i.e. where their orthogonal projections overlap.  A background cell is "in the field" when the
perpendicular through its centre meets a plate on both sides; such cells are painted with the field colour.

Everything is induced:
  * background = most frequent colour of each input;
  * plate orientation = the one of the four grid directions (row, column, two diagonals) along which the
    non-background cells split into the fewest maximal runs (decided per input, so rotated grids work);
  * field colour = the single colour that training outputs write onto background cells (finite domain 0..9).
"""
from collections import Counter

# direction vectors of candidate plates, and for each the (along, across) coordinates of a cell
DIRS = {
    'row':  ((0, 1),  lambda r, c: (c, r)),
    'col':  ((1, 0),  lambda r, c: (r, c)),
    'diag': ((1, 1),  lambda r, c: (r + c, r - c)),
    'anti': ((1, -1), lambda r, c: (r - c, r + c)),
}


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _runs(g, bg, step):
    """Maximal runs of non-background cells along direction `step`."""
    h, w = len(g), len(g[0])
    dr, dc = step
    runs = []
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg:
                continue
            pr, pc = r - dr, c - dc
            if 0 <= pr < h and 0 <= pc < w and g[pr][pc] != bg:
                continue  # not the start of a run
            run = []
            rr, cc = r, c
            while 0 <= rr < h and 0 <= cc < w and g[rr][cc] != bg:
                run.append((rr, cc))
                rr += dr
                cc += dc
            runs.append(run)
    return runs


def _plates(g, bg):
    """Choose the plate orientation with the fewest runs; return (coord function, list of plates)."""
    best = None
    for name, (step, coord) in DIRS.items():
        runs = _runs(g, bg, step)
        if best is None or len(runs) < len(best[2]):
            best = (name, coord, runs)
    name, coord, runs = best
    plates = []
    for run in runs:
        pts = [coord(r, c) for r, c in run]
        along = [a for a, _ in pts]
        plates.append((pts[0][1], min(along), max(along)))  # (across position, along-range lo, hi)
    return name, coord, plates


def _field(g, fill):
    bg = _bg(g)
    _, coord, plates = _plates(g, bg)
    out = [row[:] for row in g]
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != bg:
                continue
            a, b = coord(r, c)
            below = above = False
            for pb, lo, hi in plates:
                if lo <= a <= hi:
                    if pb < b:
                        below = True
                    elif pb > b:
                        above = True
            if below and above:
                out[r][c] = fill
    return out


def fam_capacitor(train):
    # induce the field colour: the one colour written onto background cells in every training output
    written = set()
    for p in train:
        gi, go = p['input'], p['output']
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        bg = _bg(gi)
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    if a != bg:
                        return  # plates are never altered
                    written.add(b)
    if len(written) != 1:
        return
    fill = written.pop()
    fn = lambda g, fill=fill: _field(g, fill)
    if all(fn(p['input']) == p['output'] for p in train):
        yield ('physics:capacitor_field[plates=bg-runs,orient=auto,field=%d]' % fill, 3, fn)


FAMILIES = (fam_capacitor,)
