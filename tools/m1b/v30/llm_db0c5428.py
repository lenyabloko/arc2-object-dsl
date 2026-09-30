"""Family for ARC task db0c5428 -- concept: UNFOLDING (paper folding / origami geometry).

The figure is a square annulus: a (3*th) x (3*tw) block of colour with a background hole of th x tw in the middle,
so it is a 3x3 arrangement of th x tw tiles whose centre tile is empty.  Its boundaries behave like fold lines
(hinges / mirrors):

  * outer boundary -- each of the 8 border tiles is a flap hinged on the edge(s) of the figure it lies on and is
    unfolded outward: an edge tile is reflected across its edge, a corner tile across both edges (i.e. through the
    corner point).  The flap lands at tile offset (1+gap)*d from the centre tile, d in the 8 compass directions.
  * inner boundary (the hole) -- the rim of the hole is unfolded inward: every hole cell takes the colour of its
    mirror image across the hole boundary, the mirror being chosen radially (the side of the hole the ray from the
    hole centre through the cell leaves by: an edge, or a corner when the ray leaves through a corner).  The exact
    centre cell has no radial direction (all four edges are equally near); it takes the figure's body colour
    (its most common colour) -- the alternative, majority of the four edge mirrors, is kept as a parameter value.

Colours are all by role: background = most common colour of the grid; the figure = every non-background cell;
the hole = the background cells enclosed by the figure.  No coordinates, sizes, counts or colour numbers are fixed.

Induced parameters (small finite domains):
  outer in {'mirror', 'copy'}  -- flaps reflected across their hinge vs. merely translated outward
  gap   in {0, 1}              -- flap lands adjacent to the figure (0) or one tile further out (1)
  inner in {'mirror', 'keep'}  -- hole filled by the inward reflection of its rim vs. left empty
  centre in {'body', 'mirror'} -- directionless hole centre gets the figure's body colour vs. edge-mirror majority
"""
from collections import Counter
from itertools import product


def _background(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _bbox(g, bg):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    if not cells:
        return None
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def _enclosed_background(g, bg, box):
    """Background cells inside the figure's bounding box that cannot reach the box border through background."""
    r0, c0, r1, c1 = box
    seen = set()
    stack = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
             if (r in (r0, r1) or c in (c0, c1)) and g[r][c] == bg]
    seen.update(stack)
    while stack:
        r, c = stack.pop()
        for rr, cc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if r0 <= rr <= r1 and c0 <= cc <= c1 and (rr, cc) not in seen and g[rr][cc] == bg:
                seen.add((rr, cc))
                stack.append((rr, cc))
    return [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
            if g[r][c] == bg and (r, c) not in seen]


def _annulus(g):
    """Return (bg, top, left, th, tw) if the figure is a 3x3 arrangement of th x tw tiles with an empty centre tile."""
    bg = _background(g)
    box = _bbox(g, bg)
    if box is None:
        return None
    r0, c0, r1, c1 = box
    hole = _enclosed_background(g, bg, box)
    if not hole:
        return None
    hr0 = min(r for r, _ in hole); hr1 = max(r for r, _ in hole)
    hc0 = min(c for _, c in hole); hc1 = max(c for _, c in hole)
    th, tw = hr1 - hr0 + 1, hc1 - hc0 + 1
    if len(hole) != th * tw:                      # hole must be a full rectangle
        return None
    if (r1 - r0 + 1, c1 - c0 + 1) != (3 * th, 3 * tw):   # hole must be the centre tile of a 3x3 tiling
        return None
    if (hr0 - r0, hc0 - c0) != (th, tw):
        return None
    return bg, r0, c0, th, tw


def _mirror_index(i, n, flip):
    return n - 1 - i if flip else i


def _hole_source_cells(i, j, th, tw):
    """Radial mirror for hole cell (i, j): list of candidate source offsets (relative to the hole's top-left)."""
    # offset from the hole centre, scaled so the hole is a unit square in both axes (x2 to stay integral)
    di = (2 * i - (th - 1)) * tw
    dj = (2 * j - (tw - 1)) * th
    top_src = (-1 - i, j)            # reflection across the top edge
    bot_src = (2 * th - 1 - i, j)    # across the bottom edge
    lef_src = (i, -1 - j)            # across the left edge
    rig_src = (i, 2 * tw - 1 - j)    # across the right edge
    if di == 0 and dj == 0:          # exact centre: all four edges are equally near
        return [top_src, bot_src, lef_src, rig_src]
    if abs(di) > abs(dj):
        return [top_src if di < 0 else bot_src]
    if abs(dj) > abs(di):
        return [lef_src if dj < 0 else rig_src]
    # ray leaves through a corner: point reflection through that corner
    ri = top_src[0] if di < 0 else bot_src[0]
    cj = lef_src[1] if dj < 0 else rig_src[1]
    return [(ri, cj)]


def unfold(g, outer='mirror', gap=0, inner='mirror', centre='body'):
    info = _annulus(g)
    if info is None:
        return None
    bg, r0, c0, th, tw = info
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    # --- outer boundary: unfold the 8 border tiles outward ---
    for dr, dc in product((-1, 0, 1), repeat=2):
        if dr == 0 and dc == 0:
            continue
        sr, sc = r0 + (1 + dr) * th, c0 + (1 + dc) * tw          # source tile top-left
        # flap at tile offset d (from the centre tile) lands at tile offset (2+gap)*d; gap=0 -> touching the figure
        tr = r0 + th + (2 + gap) * dr * th
        tc = c0 + tw + (2 + gap) * dc * tw
        for i in range(th):
            for j in range(tw):
                if outer == 'mirror':
                    si = _mirror_index(i, th, dr != 0)
                    sj = _mirror_index(j, tw, dc != 0)
                else:
                    si, sj = i, j
                rr, cc = tr + i, tc + j
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = g[sr + si][sc + sj]
    # --- inner boundary: unfold the hole's rim inward ---
    if inner == 'mirror':
        hr, hc = r0 + th, c0 + tw
        body = Counter(v for row in g for v in row if v != bg).most_common(1)[0][0]
        for i in range(th):
            for j in range(tw):
                srcs = _hole_source_cells(i, j, th, tw)
                if len(srcs) > 1 and centre == 'body':     # the hole centre has no radial direction
                    out[hr + i][hc + j] = body
                    continue
                cands = [g[hr + a][hc + b] for a, b in srcs]
                out[hr + i][hc + j] = Counter(cands).most_common(1)[0][0]
    return out


def fam_unfold(train):
    if not all(_annulus(p['input']) is not None for p in train):
        return
    for outer, gap, inner, centre in product(('mirror', 'copy'), (0, 1), ('mirror', 'keep'), ('body', 'mirror')):
        if inner == 'keep' and centre == 'mirror':
            continue                                   # centre option is irrelevant when the hole is kept
        fn = (lambda o, k, n, c: (lambda g: unfold(g, o, k, n, c)))(outer, gap, inner, centre)
        if all(fn(p['input']) == p['output'] for p in train):
            yield ('geometry:unfold[outer=%s,gap=%d,inner=%s,centre=%s]' % (outer, gap, inner, centre), 3, fn)


FAMILIES = (fam_unfold,)
