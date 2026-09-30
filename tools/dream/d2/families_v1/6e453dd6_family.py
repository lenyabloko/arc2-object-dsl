"""Family for ARC task 6e453dd6 -- concept: SEEPAGE (hydraulics: a sealed, fluid-filled cavity pressed against a
permeable membrane leaks through it).

Reading of the task
-------------------
A straight membrane (a band of full, single-colour lines) splits the grid.  Rigid bodies on one side drift toward it
(gravity-like docking: each body translates perpendicular to the membrane until it touches the membrane or a body that
already docked).  Every body may contain sealed cavities (background cells it encloses).  A cavity holds fluid; where
the cavity has an uninterrupted path of body material to the membrane along its own line (the "ray" that reaches
the membrane without crossing open background), the fluid seeps through and wets the far side of that line, running
from the membrane to the grid edge (or until it meets something that is not background).

Everything is induced, nothing is task-specific:
  * background = most frequent colour of the input;
  * membrane   = the unique band of adjacent full lines (rows or columns) of one non-background colour;
                 orientation (horizontal / vertical) and the side(s) holding bodies are read from each grid,
                 so the same code works for all four orientations (grids are mapped to a canonical frame:
                 vertical membrane, bodies on its left, fluid flowing right);
  * fluid      = the single colour that appears in training outputs but never in training inputs;
  * bodies     = connected components of cells that are neither background, membrane nor fluid.

Parameters (declared finite domains; first combination that is exact on all training pairs wins):
  CONN in (4, 8)              body connectivity;
  LEAK in ('ray', 'row')      'ray': cavity must reach the membrane through body material along its line;
                              'row': any cavity on a line where the body touches the membrane leaks.
"""

from collections import Counter

CONN_DOMAIN = (4, 8)
LEAK_DOMAIN = ('ray', 'row')


# ----------------------------------------------------------------------------------------------------- helpers
def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _flip(g):
    return [list(reversed(r)) for r in g]


def _wall_band(g, bg):
    """Return (orientation, colour, lo, hi) of the unique band of full uniform lines, or None."""
    H, W = len(g), len(g[0])
    cols = [c for c in range(W) if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(H))]
    rows = [r for r in range(H) if g[r][0] != bg and all(v == g[r][0] for v in g[r])]
    if cols and rows:
        return None
    if cols:
        orient, idx, colour = 'v', cols, {g[0][c] for c in cols}
    elif rows:
        orient, idx, colour = 'h', rows, {g[r][0] for r in rows}
    else:
        return None
    if len(colour) != 1 or idx != list(range(idx[0], idx[-1] + 1)):
        return None
    return orient, colour.pop(), idx[0], idx[-1]


def _components(cells, conn):
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    left, comps = set(cells), []
    while left:
        seed = left.pop()
        stack, comp = [seed], {seed}
        while stack:
            y, x = stack.pop()
            for dy, dx in nb:
                q = (y + dy, x + dx)
                if q in left:
                    left.discard(q)
                    comp.add(q)
                    stack.append(q)
        comps.append(comp)
    return comps


def _cavities(comp):
    """Cells enclosed by the body alone (4-connected flood from a 1-cell margin around its bounding box)."""
    ys = [y for y, _ in comp]
    xs = [x for _, x in comp]
    r0, r1, c0, c1 = min(ys) - 1, max(ys) + 1, min(xs) - 1, max(xs) + 1
    outside, stack = {(r0, c0)}, [(r0, c0)]
    while stack:
        y, x = stack.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (y + dy, x + dx)
            if r0 <= q[0] <= r1 and c0 <= q[1] <= c1 and q not in comp and q not in outside:
                outside.add(q)
                stack.append(q)
    return {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)
            if (y, x) not in comp and (y, x) not in outside}


# ------------------------------------------------------------------------------------------- canonical physics
def _seep_left(g, bg, fluid, c0, c1, conn, leak):
    """Canonical frame: membrane = columns c0..c1, bodies at columns < c0 drift right, fluid flows right."""
    H, W = len(g), len(g[0])
    body_cells = [(r, c) for r in range(H) for c in range(c0) if g[r][c] not in (bg, fluid)]
    if not body_cells:
        return g
    comps = _components(body_cells, conn)
    out = [row[:] for row in g]
    for r, c in body_cells:
        out[r][c] = bg
    occupied, placed = set(), []
    for comp in sorted(comps, key=lambda s: -max(x for _, x in s)):   # nearest to the membrane docks first
        d = 0
        while all(x + d + 1 < c0 and (y, x + d + 1) not in occupied for y, x in comp):
            d += 1
        moved = {(y, x + d) for y, x in comp}
        holes = {(y, x + d) for y, x in _cavities(comp) if g[y][x] == bg}
        for (y, x), (oy, ox) in zip(sorted(moved), sorted(comp)):
            out[y][x] = g[oy][ox]
        occupied |= moved
        placed.append((moved, holes))
    solid = set().union(*(m for m, _ in placed))
    wet = set().union(*(h for _, h in placed))
    for r in range(H):
        if (r, c0 - 1) not in solid:
            continue                                            # body not in contact with the membrane here
        if leak == 'ray':
            x, leaks = c0 - 1, False
            while x >= 0 and ((r, x) in solid or (r, x) in wet):
                leaks = leaks or (r, x) in wet
                x -= 1
        else:
            owner = next(i for i, (m, _) in enumerate(placed) if (r, c0 - 1) in m)
            leaks = any(y == r for y, _ in placed[owner][1])
        if leaks:
            x = c1 + 1
            while x < W and out[r][x] == bg:
                out[r][x] = fluid
                x += 1
    return out


def _seepage(g, fluid, conn, leak):
    bg = _bg(g)
    band = _wall_band(g, bg)
    if band is None:
        return None
    orient, _, lo, hi = band
    if orient == 'h':
        g = _transpose(g)
    W = len(g[0])
    g = _seep_left(g, bg, fluid, lo, hi, conn, leak)                      # bodies on the near side
    g = _flip(_seep_left(_flip(g), bg, fluid, W - 1 - hi, W - 1 - lo, conn, leak))   # bodies on the far side
    return _transpose(g) if orient == 'h' else g


# ------------------------------------------------------------------------------------------------------ family
def fam_seepage(train):
    if not train or any(len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0])
                        for p in train):
        return
    in_cols = {v for p in train for row in p['input'] for v in row}
    new = {v for p in train for row in p['output'] for v in row} - in_cols
    if len(new) != 1:
        return
    fluid = new.pop()
    for conn in CONN_DOMAIN:
        for leak in LEAK_DOMAIN:
            def fn(g, conn=conn, leak=leak):
                return _seepage(g, fluid, conn, leak)
            try:
                ok = all(fn(p['input']) == p['output'] for p in train)
            except Exception:
                ok = False
            if ok:
                yield (f"hydraulics:seepage[fluid=new_colour({fluid}),conn={conn},leak={leak}]", 3, fn)
                return


FAMILIES = (fam_seepage,)
