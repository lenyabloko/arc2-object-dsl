"""Family: optics:specular_reflection  (laser beams bouncing between mirrors).

Concept.  Every corner-shaped object (a 2x2 block with one cell missing) is a laser: it fires a diagonal
beam out of its corner, in the direction pointing from the missing cell through the opposite (corner) cell.
Every other non-background object is a mirror.  The beam moves diagonally; when the cell ahead of it
along the vertical (resp. horizontal) component of its motion is occupied, that component of its velocity
is reversed (angle of incidence = angle of reflection, as for a billiard ball against a cushion); a
head-on hit of an obstacle's corner retro-reflects.  Beams leave the grid at the border.

Induced parameters (small finite domains, first fitting combination is yielded):
  recolour in (True, False)   - on reflection the beam takes the colour of the mirror it bounced off
                                (the bounce cell itself included) or keeps its own colour.
  border   in ('absorb', 'reflect') - beams leave the grid, or the frame acts as a colourless mirror.
Background = most frequent input colour (role); colours are otherwise taken from objects.
"""
from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    """Single-colour 4-connected components of non-background cells."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append((col, sorted(cells)))
    return comps


def _laser(cells):
    """If the component is a corner (2x2 minus one cell) return (start_cell, direction), else None."""
    if len(cells) != 3:
        return None
    rs = [r for r, _ in cells]; cs = [c for _, c in cells]
    r0, c0 = min(rs), min(cs)
    if max(rs) - r0 != 1 or max(cs) - c0 != 1:
        return None
    box = {(r0 + i, c0 + j) for i in (0, 1) for j in (0, 1)}
    (mr, mc), = box - set(cells)
    cr, cc = 2 * r0 + 1 - mr, 2 * c0 + 1 - mc          # corner diagonally opposite the gap
    dr, dc = cr - mr, cc - mc                           # points from the gap through the corner
    return (cr + dr, cc + dc), (dr, dc)


def _trace(g, bg, start, d, colour, recolour, border):
    H, W = len(g), len(g[0])
    inside = lambda y, x: 0 <= y < H and 0 <= x < W
    (r, c), (dr, dc) = start, d
    path, seen = [], set()
    while inside(r, c) and g[r][c] == bg and (r, c, dr, dc) not in seen:
        seen.add((r, c, dr, dc))
        hit = None
        # vertical component blocked?
        if inside(r + dr, c):
            if g[r + dr][c] != bg:
                hit = g[r + dr][c]; dr = -dr
        elif border == 'reflect':
            dr = -dr
        # horizontal component blocked?
        if inside(r, c + dc):
            if g[r][c + dc] != bg:
                hit = g[r][c + dc] if hit is None else hit; dc = -dc
        elif border == 'reflect':
            dc = -dc
        # head-on hit of an obstacle's corner -> retro-reflection
        if hit is None and inside(r + dr, c + dc) and g[r + dr][c + dc] != bg:
            hit = g[r + dr][c + dc]; dr, dc = -dr, -dc
        if hit is not None and recolour:
            colour = hit
        path.append((r, c, colour))
        r, c = r + dr, c + dc
    return path


def _render(g, recolour, border):
    bg = _bg(g)
    out = [row[:] for row in g]
    painted = set()
    for col, cells in _components(g, bg):
        las = _laser(cells)
        if las is None:
            continue
        start, d = las
        for r, c, k in _trace(g, bg, start, d, col, recolour, border):
            if (r, c) not in painted:           # the first beam to light a cell keeps it
                painted.add((r, c))
                out[r][c] = k
    return out


def fam_specular_reflection(train):
    if not train or any(len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0])
                        for p in train):
        return
    for recolour in (True, False):
        for border in ('absorb', 'reflect'):
            fn = (lambda rc, bd: (lambda g: _render(g, rc, bd)))(recolour, border)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("optics:specular_reflection[recolour=%s,border=%s]" % (recolour, border), 3, fn)
                return


FAMILIES = (fam_specular_reflection,)
