"""Line family for card 4c416de3 (test-blind; induced only from train pairs).

Reading: the grid holds rectangular frames (outlines of one frame colour, possibly clipped by the
grid edge).  At one frame corner an exemplar shape is drawn in some colour (it may overwrite frame
cells).  At other frame corners a marker (a few cells of one colour) sits where part of that shape
would be.  Each marked corner is completed with the exemplar shape, re-oriented to that corner
(mirrored across the frame's axes, or rotated), and painted in the marker's colour.
"""
from collections import Counter

CARD = "4c416de3"
LINE = "complete geometric shape starting at markers using exemplar shape and marker's color"
READING = {
    "generator": "At every frame corner that holds a marker, draw the exemplar corner shape (taken from the "
                 "corner where it is complete), re-oriented to that corner, in the marker's colour.",
    "stop": "One copy per marked corner: exactly the exemplar's cells (relative to its corner) are painted, "
            "clipped at the grid edge; corners without a marker, and off-grid frame corners, get nothing.",
    "params": "orientation ∈ {mirror across the frame axes, rotate about the frame} · "
              "paint ∈ {overwrite anything, background only}",
    "participants": "Background = most frequent colour; frame colour = most frequent other colour; frames = "
                    "8-connected non-background blobs, their frame-colour bounding box giving four candidate "
                    "corners, a corner being real when both its edges are mostly frame colour; the exemplar = "
                    "the largest one-colour 8-connected blob of a non-frame, non-background colour, anchored at "
                    "the nearest real corner; a marker = the non-frame, non-background cells (one colour) found "
                    "on the exemplar's cell positions at another real corner.",
    "preconditions": "Input and output have the same size; at least one real frame corner; an exemplar blob of "
                     "two or more cells; and the completed copies reproduce every training pair.",
}

D8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _frame_colour(g, bg):
    c = Counter(v for r in g for v in r if v != bg)
    return c.most_common(1)[0][0] if c else None


def _comps(g, ok, same_colour):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not ok(g[y][x]):
                continue
            col = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in D8:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and ok(g[p][q]) \
                            and (not same_colour or g[p][q] == col):
                        seen[p][q] = True
                        st.append((p, q))
            out.append((col, sorted(pix)))
    return out


def _corners(g, bg, F):
    """Real frame corners as (r, c, sv, sh): (sv, sh) points into the frame."""
    H, W = len(g), len(g[0])
    res = []
    for _, pix in _comps(g, lambda v: v != bg, False):
        fp = [(y, x) for y, x in pix if g[y][x] == F]
        if len(fp) < 3:
            continue
        r0 = min(y for y, _ in fp); r1 = max(y for y, _ in fp)
        c0 = min(x for _, x in fp); c1 = max(x for _, x in fp)
        if r1 - r0 < 2 or c1 - c0 < 2:
            continue

        def real_row(r):
            n = sum(1 for x in range(c0, c1 + 1) if g[r][x] == F)
            return 2 * n > c1 - c0 + 1

        def real_col(c):
            n = sum(1 for y in range(r0, r1 + 1) if g[y][c] == F)
            return 2 * n > r1 - r0 + 1

        top, bot, lef, rig = real_row(r0), real_row(r1), real_col(c0), real_col(c1)
        if top and lef: res.append((r0, c0, 1, 1))
        if top and rig: res.append((r0, c1, 1, -1))
        if bot and lef: res.append((r1, c0, -1, 1))
        if bot and rig: res.append((r1, c1, -1, -1))
    return res


def _orient(i, j, ref, k, mode):
    if mode == "rotate" and ref[2] * ref[3] != k[2] * k[3]:
        return j, i
    return i, j


def _solve(g, mode, paint):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    F = _frame_colour(g, bg)
    if F is None:
        return None
    corners = _corners(g, bg, F)
    if not corners:
        return None
    blobs = _comps(g, lambda v: v != bg and v != F, True)
    if not blobs:
        return None
    blobs.sort(key=lambda b: (-len(b[1]), b[1][0]))
    col, pix = blobs[0]
    if len(pix) < 2:
        return None
    ref = min(corners, key=lambda k: (min(max(abs(y - k[0]), abs(x - k[1])) for y, x in pix), k))
    S = [((y - ref[0]) * ref[2], (x - ref[1]) * ref[3]) for y, x in pix]
    out = [row[:] for row in g]
    for k in corners:
        if k == ref:
            continue
        pos = []
        for i, j in S:
            a, b = _orient(i, j, ref, k, mode)
            y, x = k[0] + k[2] * a, k[1] + k[3] * b
            if 0 <= y < H and 0 <= x < W:
                pos.append((y, x))
        cols = {g[y][x] for y, x in pos if g[y][x] != bg and g[y][x] != F}
        if len(cols) != 1:
            continue
        m = cols.pop()
        for y, x in pos:
            if paint == "all" or g[y][x] == bg:
                out[y][x] = m
    return out


def fam(train):
    if not train:
        return
    for p in train:
        if len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0]):
            return
    cost = 0
    for mode in ("mirror", "rotate"):
        for paint in ("all", "bg"):
            cost += 1

            def fn(g, mode=mode, paint=paint):
                r = _solve(g, mode, paint)
                return r if r is not None else [row[:] for row in g]

            try:
                ok = all(_solve(p["input"], mode, paint) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("exemplar_corner_complete[%s,%s]" % (mode, paint), cost, fn)


FAMILIES = [fam]
