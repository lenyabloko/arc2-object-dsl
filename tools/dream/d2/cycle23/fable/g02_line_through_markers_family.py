"""Group g02 "lines drawn through markers"  ->  concept: VORONOI PARTITION (computational geometry), 1-D.

Mechanism (one rule for every member):
  * Every marker (non-background cell) is a *seed line*: it is extended into a full straight line across the grid,
    along one axis (all markers of a task lie on parallel lines; the axis is induced).
  * A fixed stencil is then painted: the seed lines themselves plus (optionally) the grid frame (border ring).
  * Each stencil cell takes the colour of the NEAREST seed line, distance measured perpendicular to the lines
    (1-D Voronoi partition of the grid by the marker lines); equidistant cells go to the first (or last) seed
    in scan order - a two-valued parameter induced from the training pairs.
  So the marker lines are "drawn through" the markers and the frame is split into Voronoi segments owned by
  the closest marker, the frame's corners and edges inheriting the colour of the nearest line.

Parameters, all induced from the task's own training pairs, from small finite domains:
  axis  in {row, col}       - orientation of the seed lines (rows of markers or columns of markers)
  frame in {border, none}   - whether the grid's border ring is part of the stencil
  tie   in {first, last}    - which seed wins a cell equidistant from two seeds
Colours: background = most common colour of the training inputs; everything else is a seed and paints its own colour.
No coordinates, sizes, counts or colour numbers are hard-coded.
"""
from collections import Counter


def _bg(train):
    c = Counter()
    for p in train:
        for row in p["input"]:
            c.update(row)
    return c.most_common(1)[0][0]


def _seeds(grid, bg, axis):
    """Markers grouped by their coordinate along `axis` (0 = rows, 1 = cols).
    Returns a sorted list of (coordinate, colour) or None if some line carries two colours / no marker exists."""
    seeds = {}
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v == bg:
                continue
            k = r if axis == 0 else c
            if seeds.setdefault(k, v) != v:
                return None
    if not seeds:
        return None
    return sorted(seeds.items())


def _nearest_colour(seeds, k, tie):
    """Colour of the seed line nearest to coordinate k; ties -> first/last seed in scan order."""
    best, bestd = None, None
    for coord, col in seeds:
        d = abs(coord - k)
        if bestd is None or d < bestd or (d == bestd and tie == "last"):
            best, bestd = col, d
    return best


def _make(bg, axis, frame, tie):
    def fn(grid):
        h, w = len(grid), len(grid[0])
        seeds = _seeds(grid, bg, axis)
        if seeds is None:
            raise ValueError("no parallel single-colour seed lines")
        out = [list(row) for row in grid]
        seedset = {coord for coord, _ in seeds}
        n = h if axis == 0 else w  # extent along the perpendicular (Voronoi) axis
        colour_at = [_nearest_colour(seeds, k, tie) for k in range(n)]
        for r in range(h):
            for c in range(w):
                k = r if axis == 0 else c
                on_line = k in seedset
                on_frame = frame == "border" and (r == 0 or c == 0 or r == h - 1 or c == w - 1)
                if on_line or on_frame:
                    out[r][c] = colour_at[k]
        return out
    return fn


def fam_voronoi(train):
    """1-D Voronoi partition of the grid by full lines drawn through the markers; frame + lines painted by nearest seed."""
    if not train:
        return
    # quick rejects: same-size in/out, some non-background content in every input
    for p in train:
        if len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0]):
            return
        # every output colour must already be present in the input: seeds only paint their own colour
        if not {v for row in p["output"] for v in row} <= {v for row in p["input"] for v in row}:
            return
    bg = _bg(train)
    for axis in (0, 1):
        if any(_seeds(p["input"], bg, axis) is None for p in train):
            continue
        for frame in ("border", "none"):
            for tie in ("first", "last"):
                fn = _make(bg, axis, frame, tie)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield (f"geometry:voronoi[axis={'row' if axis == 0 else 'col'},frame={frame},tie={tie}]", 3, fn)
                    return


FAMILIES = (fam_voronoi,)
