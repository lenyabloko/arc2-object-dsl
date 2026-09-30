"""Family for ARC task 9385bd28 -- concept: CROP MARKS (printing / graphic arts), stacked with a z-order key.

Picture: a printer's sheet.  Scattered on the paper are corner brackets ("crop marks") in several colours;
the marks of one colour delimit a rectangle (their joint bounding box).  A small multi-coloured key block
(the colour legend, a strip two cells thick) lists, entry by entry, "mark colour -> ink".  Each rectangle
is inked with its ink, the marks themselves stay printed on top of their own rectangle, and the rectangles
are laid down as layers whose stacking order is the order of the key (a z-order legend).  An ink equal to
the paper colour (or the key's "null" colour) prints blank paper.  A mark colour that is a single solid
object is not a pair of brackets: its rectangle is itself, so it is simply re-inked.

Everything is induced per grid or from the training pairs:
  paper (background) = most common colour
  key block          = the largest 4-connected multi-coloured non-paper component whose bounding box is
                       two cells thick; its paper cells are entries too (ink = paper)
  key orientation    = the reading (entries along the long axis, mark side first/second) whose mark
                       colours are best attested as objects outside the key
Declared finite parameter domains, chosen by fitting the training pairs:
  order in {"first_on_top", "last_on_top"}   -- z-order of key entries (reading order)
  null  in {None, 0..9}                      -- an ink colour that means "blank paper"
  side  in {"first", "second"}               -- tie-break for which side of the key holds the mark colours
"""
from collections import Counter

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _paper(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(cells, nbrs):
    cells = set(cells)
    seen, comps = set(), []
    for s in sorted(cells):
        if s in seen:
            continue
        seen.add(s)
        stack, comp = [s], []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy, dx in nbrs:
                t = (y + dy, x + dx)
                if t in cells and t not in seen:
                    seen.add(t)
                    stack.append(t)
        comps.append(comp)
    return comps


def _bbox(cells):
    ys = [y for y, _ in cells]
    xs = [x for _, x in cells]
    return min(ys), max(ys), min(xs), max(xs)


def _find_key(g, paper, side):
    """Return (key_box, entries) with entries = [(mark_colour, ink), ...] in reading order."""
    H, W = len(g), len(g[0])
    ink_cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] != paper]
    best = None
    for comp in _components(ink_cells, N4):
        if len({g[r][c] for r, c in comp}) < 2:
            continue
        r0, r1, c0, c1 = _bbox(comp)
        if min(r1 - r0, c1 - c0) != 1:  # a key strip is exactly two cells thick
            continue
        if best is None or len(comp) > len(best):
            best = comp
    if best is None:
        return None
    r0, r1, c0, c1 = _bbox(best)
    box = (r0, r1, c0, c1)
    outside = Counter(g[r][c] for r in range(H) for c in range(W)
                      if not (r0 <= r <= r1 and c0 <= c <= c1))
    readings = []
    if c1 - c0 == 1:  # entries are rows
        rows = [(g[r][c0], g[r][c1]) for r in range(r0, r1 + 1)]
        readings.append((r1 - r0 >= c1 - c0, 0, rows))
        readings.append((r1 - r0 >= c1 - c0, 1, [(b, a) for a, b in rows]))
    if r1 - r0 == 1:  # entries are columns
        cols = [(g[r0][c], g[r1][c]) for c in range(c0, c1 + 1)]
        readings.append((c1 - c0 >= r1 - r0, 0, cols))
        readings.append((c1 - c0 >= r1 - r0, 1, [(b, a) for a, b in cols]))
    pref = 0 if side == "first" else 1

    def score(rd):
        long_axis, s, ents = rd
        attested = sum(1 for a, _ in ents if a != paper and outside[a] > 0)
        bad = sum(1 for a, _ in ents if a == paper)
        return (attested - bad, long_axis, s == pref)

    _, _, entries = max(readings, key=score)
    return box, entries


def _print(g, order, null, side):
    paper = _paper(g)
    found = _find_key(g, paper, side)
    if found is None:
        return None
    (r0, r1, c0, c1), entries = found
    H, W = len(g), len(g[0])

    def in_key(r, c):
        return r0 <= r <= r1 and c0 <= c <= c1

    out = [row[:] for row in g]
    layers = entries[::-1] if order == "first_on_top" else entries[:]  # paint bottom layer first
    for mark, ink in layers:
        if mark == paper:
            continue
        marks = [(r, c) for r in range(H) for c in range(W) if g[r][c] == mark and not in_key(r, c)]
        if not marks:
            continue
        ink = paper if (ink == paper or ink == null) else ink
        y0, y1, x0, x1 = _bbox(marks)
        for r in range(y0, y1 + 1):
            for c in range(x0, x1 + 1):
                if not in_key(r, c):
                    out[r][c] = ink
        if len(_components(marks, N8)) >= 2:  # brackets framing a rectangle stay printed
            for r, c in marks:
                out[r][c] = mark
    return out


def fam_crop_marks(train):
    if any(len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0]) for p in train):
        return
    for side in ("first", "second"):
        for order in ("first_on_top", "last_on_top"):
            for null in (None,) + tuple(range(10)):
                def fn(g, order=order, null=null, side=side):
                    return _print(g, order, null, side)
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("printing:crop_marks[order=%s,null=%s,side=%s]" % (order, null, side), 3, fn)
                    return


FAMILIES = (fam_crop_marks,)
