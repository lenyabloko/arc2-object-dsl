"""Family for ARC task 221dfab4 -- concept: GRADUATED SCALE (metrology: a ruler with minor and major ticks).

Reading of the task
-------------------
A short bar of a special colour sits on one border of the grid: it is the zero mark of a ruler.  The ruler is laid
from that bar straight across the grid, as wide as the bar (the "stripe").  Walking away from the zero mark, the
distance d (in cells) is graduated:
  * d not a multiple of the tick spacing s      -> gap: the stripe is wiped to background;
  * d a multiple of s (tick t = d // s):
      - t % m != phase  -> minor tick: the stripe is painted in the bar's colour;
      - t % m == phase  -> major graduation: a gridline drawn across the whole grid at that distance.  It is painted
                           in the major colour inside the stripe and wherever it cuts through an object (cells of any
                           object colour); background outside the stripe stays as it is.

Colour roles (nothing hard-coded):
  background   = most common colour of the input
  bar (zero)   = the non-background colour whose cells all lie on one border line as a single contiguous run
  object cols  = every other colour present in the input
  major colour = the colour that appears in every training output and in no training input (induced)

Parameters and their declared finite domains (searched in order, first fit wins):
  s     in {1, 2, 3}          tick spacing
  m     in {1, 2, 3, 4}       every m-th tick is a major graduation
  phase in {0 .. m-1}         which tick index (mod m) is major; tick 0 is the zero mark itself
The ruler direction is not a parameter: it is read from which border the bar lies on (always pointing inward).
"""

from collections import Counter


# ----------------------------------------------------------------------------------------------- grid helpers
def _rot_cw(g):
    """Rotate a grid 90 degrees clockwise."""
    return [list(r) for r in zip(*g[::-1])]


def _rot(g, k):
    for _ in range(k % 4):
        g = _rot_cw(g)
    return g


def _background(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _find_bar(g, bg):
    """Return (colour, k) where k = number of clockwise rotations that bring the bar onto the bottom row,
    or None.  The bar is a non-background colour whose cells all lie on one border line as one contiguous run."""
    H, W = len(g), len(g[0])
    cells = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                cells.setdefault(g[r][c], []).append((r, c))
    candidates = []
    for col, pts in cells.items():
        rows = {r for r, _ in pts}
        cols = {c for _, c in pts}
        # which border line holds all the cells; k = clockwise rotations that move that border to the bottom
        options = []
        if rows == {H - 1}:
            options.append((0, sorted(cols)))
        if cols == {0}:
            options.append((3, sorted(rows)))   # left border -> bottom after three cw rotations
        if rows == {0}:
            options.append((2, sorted(cols)))
        if cols == {W - 1}:
            options.append((1, sorted(rows)))   # right border -> bottom after one cw rotation
        for k, span in options:
            if span[-1] - span[0] + 1 == len(span):          # one contiguous run
                candidates.append((len(pts), col, k))
    if not candidates:
        return None
    candidates.sort()
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0] and candidates[0][1] != candidates[1][1]:
        return None                                           # ambiguous zero mark
    _, col, k = candidates[0]
    return col, k


def _graduate(g, s, m, phase, major):
    """Apply the graduated scale to grid g (any size, bar on any border)."""
    bg = _background(g)
    found = _find_bar(g, bg)
    if found is None:
        return None
    bar, k = found
    a = _rot(g, k)                                           # canonical frame: bar on the bottom row
    H, W = len(a), len(a[0])
    stripe = [c for c in range(W) if a[H - 1][c] == bar]
    objects = {v for row in a for v in row} - {bg, bar}
    out = [list(row) for row in a]
    for r in range(H):
        d = H - 1 - r                                         # distance from the zero mark
        if d % s:
            for c in stripe:
                out[r][c] = bg                                # gap between ticks
            continue
        t = d // s
        if t % m == phase:                                    # major graduation: gridline through objects
            for c in range(W):
                if a[r][c] in objects:
                    out[r][c] = major
            for c in stripe:
                out[r][c] = major
        else:                                                 # minor tick
            for c in stripe:
                out[r][c] = bar
    return _rot(out, (4 - k) % 4)


def _induce_major_colour(train):
    """The colour introduced by the transformation: present in every output, absent from every input."""
    in_cols = {v for p in train for row in p["input"] for v in row}
    new = None
    for p in train:
        cols = {v for row in p["output"] for v in row} - in_cols
        new = cols if new is None else new & cols
    if not new or len(new) != 1:
        return None
    return next(iter(new))


# ----------------------------------------------------------------------------------------------- family
S_DOMAIN = (1, 2, 3)
M_DOMAIN = (1, 2, 3, 4)


def fam_graduated_scale(train):
    major = _induce_major_colour(train)
    if major is None:
        return
    for s in S_DOMAIN:
        for m in M_DOMAIN:
            for phase in range(m):
                def fn(g, s=s, m=m, phase=phase, major=major):
                    return _graduate(g, s, m, phase, major)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("metrology:graduated_scale[tick=%d,major_every=%d,major_phase=%d,major_colour=new]"
                           % (s, m, phase), 3, fn)
                    return


FAMILIES = (fam_graduated_scale,)
