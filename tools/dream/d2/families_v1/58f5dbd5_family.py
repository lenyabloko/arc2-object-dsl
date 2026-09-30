"""Family for ARC task 58f5dbd5 -- concept: STENCIL / DIE PUNCH (printing / sheet-metal manufacturing).

Picture: the input holds solid monochrome *plates* (large solid rectangles) and, elsewhere, small loose
*dies* (sparse shapes) of assorted colours.  Each plate is punched by the die of its own colour: the die's
shape is cut out of the plate's interior (a frame of width `border` is left intact), so where the die has
material the plate shows background (a hole) and where the die is empty the plate keeps its colour -- the
plate becomes a stencil of the die.  Dies are consumed; dies with no matching plate are scrap.  The output is
the plate yard only: the bounding box of the plates widened by `margin`, everything else background.

Induced from the training pairs:
  background = most common colour of the input
  plates     = 4-connected monochrome components that are solid rectangles of the maximal area
               (both sides >= 3); every other non-background cell belongs to a die, grouped by colour
Declared finite parameter domains, chosen by fitting the training pairs:
  mode   in ("negative", "positive")  -- stencil (die cut out -> hole)  /  stamp (die printed in plate colour)
  border in (1, 2)                    -- width of the uncut frame of each plate
  margin in (0, 1, 2)                 -- background frame kept around the plate yard in the output
"""
from collections import Counter

MODES = ("negative", "positive")
BORDERS = (1, 2)
MARGINS = (0, 1, 2)


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
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
            comps.append((col, cells))
    return comps


def _plates(g, bg):
    """Solid monochrome rectangles (both sides >= 3) of maximal area: (colour, r0, c0, r1, c1)."""
    rects = []
    for col, cells in _components(g, bg):
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if h >= 3 and w >= 3 and h * w == len(cells):
            rects.append((col, r0, c0, r1, c1))
    if not rects:
        return []
    amax = max((r1 - r0 + 1) * (c1 - c0 + 1) for _, r0, c0, r1, c1 in rects)
    return [t for t in rects if (t[3] - t[1] + 1) * (t[4] - t[2] + 1) == amax]


def _die_windows(g, bg, plates, border):
    """For each colour: the die (a window of the plate-interior size) cut from the loose cells of that colour.
    The window is the die's bounding box; if the die is smaller than the interior, the window is aligned
    with the band of the neighbouring full-size dies (dies are laid out in rows/columns), else top-left."""
    H, W = len(g), len(g[0])
    in_plate = set()
    for _, r0, c0, r1, c1 in plates:
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                in_plate.add((y, x))
    loose = {}
    for y in range(H):
        for x in range(W):
            v = g[y][x]
            if v != bg and (y, x) not in in_plate:
                loose.setdefault(v, []).append((y, x))
    sizes = {}
    for col, r0, c0, r1, c1 in plates:
        sizes[col] = (r1 - r0 + 1 - 2 * border, c1 - c0 + 1 - 2 * border)
    boxes = {}
    for col, cells in loose.items():
        ys = [y for y, _ in cells]
        xs = [x for _, x in cells]
        boxes[col] = (min(ys), min(xs), max(ys), max(xs))
    dies = {}
    for col, (ih, iw) in sizes.items():
        if ih <= 0 or iw <= 0 or col not in boxes:
            continue
        r0, c0, r1, c1 = boxes[col]
        if r1 - r0 + 1 > ih or c1 - c0 + 1 > iw:
            return None  # die larger than the plate interior: outside this concept
        # align short dies with the band of a full-size neighbouring die
        if r1 - r0 + 1 < ih:
            for oc, (a0, b0, a1, b1) in boxes.items():
                if oc != col and a1 - a0 + 1 == ih and a0 <= r0 and r1 <= a1:
                    r0 = a0
                    break
        if c1 - c0 + 1 < iw:
            for oc, (a0, b0, a1, b1) in boxes.items():
                if oc != col and b1 - b0 + 1 == iw and b0 <= c0 and c1 <= b1:
                    c0 = b0
                    break
        win = [[g[r0 + i][c0 + j] == col if (0 <= r0 + i < H and 0 <= c0 + j < W) else False
                for j in range(iw)] for i in range(ih)]
        dies[col] = win
    return dies


def _make(mode, border, margin):
    def fn(g):
        bg = _bg(g)
        plates = _plates(g, bg)
        if not plates:
            return None
        dies = _die_windows(g, bg, plates, border)
        if dies is None:
            return None
        H, W = len(g), len(g[0])
        R0 = max(0, min(p[1] for p in plates) - margin)
        C0 = max(0, min(p[2] for p in plates) - margin)
        R1 = min(H - 1, max(p[3] for p in plates) + margin)
        C1 = min(W - 1, max(p[4] for p in plates) + margin)
        out = [[bg] * (C1 - C0 + 1) for _ in range(R1 - R0 + 1)]
        for col, r0, c0, r1, c1 in plates:
            for y in range(r0, r1 + 1):
                for x in range(c0, c1 + 1):
                    out[y - R0][x - C0] = col
            die = dies.get(col)
            if die is None:
                continue
            for i, row in enumerate(die):
                for j, solid in enumerate(row):
                    if mode == "negative":
                        v = bg if solid else col
                    else:
                        v = col if solid else bg
                    out[r0 + border + i - R0][c0 + border + j - C0] = v
        return out
    return fn


def fam_stencil(train):
    for mode in MODES:
        for border in BORDERS:
            for margin in MARGINS:
                fn = _make(mode, border, margin)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("printing:stencil[mode=%s,border=%d,margin=%d]" % (mode, border, margin), 3, fn)
                    return


FAMILIES = (fam_stencil,)
