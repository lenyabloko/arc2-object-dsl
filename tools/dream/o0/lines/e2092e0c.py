"""Line family for card e2092e0c (test-blind; induced only from train pairs).

Reading: a line of colour c (the separator) cuts off a rectangular exemplar area: the rectangle whose
every side either lies on the grid border or is flanked by an all-c line (ring cells incl. corners).
The exemplar's exact content is looked up elsewhere in the grid (identical fragment, same orientation);
each occurrence gets a frame of colour c drawn on the ring around it, like the separator around the exemplar.
"""
from collections import Counter

CARD = "e2092e0c"
LINE = ("use exemplar area on the inner side of separator to locale identical fragment and frame it "
        "into the separator-colored frame")
READING = {
    "generator": "Take the exemplar area enclosed by the separator (a rectangle bounded by separator-coloured "
                 "lines and/or the grid border), find the identical fragment elsewhere in the grid, and draw a "
                 "separator-coloured rectangular frame on the ring of cells just around that fragment.",
    "stop": "One frame (thickness t) per occurrence of the fragment outside the exemplar; frame cells falling "
            "off the grid are clipped; nothing else changes.",
    "params": "colour ∈ {constant induced from train diffs, detected per input} · t ∈ {1,2} · "
              "which ∈ {all occurrences, nearest-to-exemplar only} · exemplar choice = largest separator-enclosed "
              "rectangle whose content occurs elsewhere",
    "participants": "Separator: cells of colour c forming lines that, with the grid border, enclose a rectangle "
                    "(the exemplar area); fragment: every window of the exemplar's size, not overlapping the "
                    "exemplar, whose cells equal the exemplar's cell by cell.",
    "preconditions": "Input and output have the same size, all changed cells take one colour c, some rectangle "
                     "is enclosed by c-lines (sides on the grid border allowed, not the whole grid), its content "
                     "is not uniform, and it occurs identically at least once elsewhere.",
}


def _enclosed(g, c, t=1):
    """Rectangles (r0, r1, c0, c1) whose each side is on the grid border or flanked by a c-line of
    thickness t (the ring is clipped to the grid; ring corners included)."""
    H, W = len(g), len(g[0])
    is_c = [[1 if v == c else 0 for v in row] for row in g]

    def allc(ra, rb, ca, cb):
        ra, rb, ca, cb = max(ra, 0), min(rb, H - 1), max(ca, 0), min(cb, W - 1)
        if ra > rb or ca > cb:
            return True
        return all(is_c[r][x] for r in range(ra, rb + 1) for x in range(ca, cb + 1))

    # cheap corner pruning: top-left / bottom-right corners must sit against c (or the border)
    tl = [(r0, c0) for r0 in range(H) for c0 in range(W)
          if (r0 == 0 or r0 >= t) and (c0 == 0 or c0 >= t)
          and (r0 == 0 or is_c[r0 - 1][max(c0 - 1, 0)]) and (c0 == 0 or is_c[max(r0 - 1, 0)][c0 - 1])]
    br = [(r1, c1) for r1 in range(H) for c1 in range(W)
          if (r1 == H - 1 or r1 <= H - 1 - t) and (c1 == W - 1 or c1 <= W - 1 - t)
          and (r1 == H - 1 or is_c[r1 + 1][min(c1 + 1, W - 1)])
          and (c1 == W - 1 or is_c[min(r1 + 1, H - 1)][c1 + 1])]
    out = []
    for r0, c0 in tl:
        for r1, c1 in br:
            if r1 < r0 or c1 < c0:
                continue
            if r0 == 0 and c0 == 0 and r1 == H - 1 and c1 == W - 1:
                continue
            if r0 > 0 and not allc(r0 - t, r0 - 1, c0 - t, c1 + t):
                continue
            if r1 < H - 1 and not allc(r1 + 1, r1 + t, c0 - t, c1 + t):
                continue
            if c0 > 0 and not allc(r0 - t, r1 + t, c0 - t, c0 - 1):
                continue
            if c1 < W - 1 and not allc(r0 - t, r1 + t, c1 + 1, c1 + t):
                continue
            out.append((r0, r1, c0, c1))
    return out


def _occurrences(g, rect):
    H, W = len(g), len(g[0])
    r0, r1, c0, c1 = rect
    h, w = r1 - r0 + 1, c1 - c0 + 1
    ex = [g[r][c0:c1 + 1] for r in range(r0, r1 + 1)]
    occ = []
    for y in range(H - h + 1):
        for x in range(W - w + 1):
            if y <= r1 and y + h - 1 >= r0 and x <= c1 and x + w - 1 >= c0:
                continue  # overlaps the exemplar itself
            if all(g[y + i][x:x + w] == ex[i] for i in range(h)):
                occ.append((y, x))
    return occ, h, w


def _locate(g, colours, t):
    """Largest non-uniform separator-enclosed exemplar that occurs elsewhere -> (c, rect, occ, h, w)."""
    cands = []
    for c in colours:
        for rect in _enclosed(g, c, t):
            r0, r1, c0, c1 = rect
            vals = {g[r][x] for r in range(r0, r1 + 1) for x in range(c0, c1 + 1)}
            if len(vals) < 2:
                continue
            cands.append((-(r1 - r0 + 1) * (c1 - c0 + 1), r0, c0, c, rect))
    cands.sort()
    for _, _, _, c, rect in cands:
        occ, h, w = _occurrences(g, rect)
        if occ:
            return c, rect, occ, h, w
    return None


def _apply(g, colour, t, which):
    H, W = len(g), len(g[0])
    if colour == "detect":
        colours = sorted({v for row in g for v in row} - {Counter(v for row in g for v in row).most_common(1)[0][0]})
    else:
        colours = [colour]
    hit = _locate(g, colours, t)
    if hit is None:
        return None
    c, rect, occ, h, w = hit
    if which == "nearest":
        r0, _, c0, _ = rect
        occ = [min(occ, key=lambda p: (abs(p[0] - r0) + abs(p[1] - c0), p))]
    out = [row[:] for row in g]
    for y, x in occ:
        for r in range(y - t, y + h + t):
            for q in range(x - t, x + w + t):
                if y <= r < y + h and x <= q < x + w:
                    continue
                if 0 <= r < H and 0 <= q < W:
                    out[r][q] = c
    return out


def _make(colour, t, which):
    def fn(grid):
        res = _apply(grid, colour, t, which)
        return [row[:] for row in grid] if res is None else res
    return fn


def fam(train):
    if not train:
        return
    added = set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return
        d = {b[r][q] for r in range(len(a)) for q in range(len(a[0])) if a[r][q] != b[r][q]}
        added |= d
    if not added:
        return
    colours = [(next(iter(added)), 0)] if len(added) == 1 else []
    colours.append(("detect", 2))
    found = []
    for colour, cc in colours:
        for t in (1, 2):
            for which, wc in (("all", 0), ("nearest", 1)):
                fn = _make(colour, t, which)
                try:
                    ok = all(_apply(p["input"], colour, t, which) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    name = "frame_exemplar_match[colour=%s,t=%d,%s]" % (colour, t, which)
                    found.append((10 + cc + 2 * (t - 1) + wc, len(found), name, fn))
    found.sort(key=lambda z: (z[0], z[1]))
    for cost, _, name, fn in found:
        yield name, cost, fn


FAMILIES = [fam]
