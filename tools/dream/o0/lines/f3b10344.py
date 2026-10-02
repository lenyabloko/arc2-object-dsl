"""Line family for card f3b10344 (test-blind; induced only from train pairs).

Reading: shapes are single-colour connected components.  Two shapes of the same colour that face
each other along a row band or a column band, with nothing in between, are joined by a solid
rectangular channel of one fixed colour.  The channel bridges the gap between their facing sides;
across, it is as wide as the shared side (the smaller shape's side when it lies inside the larger
one's) allows, trimmed by one pixel at each edge so it is narrower than that side.
"""
from collections import Counter

CARD = "f3b10344"
LINE = ("connect same colored shapes with rectangular channels of fixed color as wide as the smaller "
        "shape allows but one pixel narrower than that shape's connected side")
READING = {
    "generator": "Between every two same-coloured shapes that face each other horizontally or vertically "
                 "with only background between them, fill a rectangle of one fixed colour spanning the gap; "
                 "across the gap it covers the shared extent of their facing sides (the smaller shape's side) "
                 "minus a trim at the edges, i.e. one pixel narrower than that side at each edge.",
    "stop": "The channel stops at the two facing sides (it fills exactly the gap); one channel per facing "
            "pair, drawn simultaneously from the input; a pair is skipped if anything non-background lies "
            "between them, if they share no extent, or if the trimmed width is not positive.",
    "params": "colour ∈ {constant induced from changed cells, same as the shapes} · trim (lo, hi) ∈ "
              "{(1,1), (0,0), (2,2), (1,0), (0,1)} · width basis ∈ {overlap of the two sides, smaller "
              "shape's side} · blocking ∈ {whole shared strip, channel cells only} · connectivity ∈ {4, 8}",
    "participants": "Single-colour connected components of non-background cells (background = most frequent "
                    "colour); their bounding boxes give the sides; pairs are found by scanning, for each "
                    "shape, the shapes whose row (or column) range overlaps its own and lie strictly beyond it.",
    "preconditions": "Input and output have the same size, some cells change, every changed cell goes from "
                     "background to a non-background colour, and at least two same-coloured shapes face each "
                     "other across a background gap.",
}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _objects(g, bg, conn):
    H, W = len(g), len(g[0])
    nb = ((-1, 0), (1, 0), (0, -1), (0, 1))
    if conn == 8:
        nb = nb + ((-1, -1), (-1, 1), (1, -1), (1, 1))
    seen = [[False] * W for _ in range(H)]
    objs = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            c = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c:
                        seen[p][q] = True
                        st.append((p, q))
            ys = [p[0] for p in pix]
            xs = [p[1] for p in pix]
            objs.append((c, min(ys), max(ys), min(xs), max(xs)))
    objs.sort(key=lambda o: (o[1], o[3], o[0]))
    return objs


def _channels(g, bg, conn, trim, basis, block):
    """Return list of (colour_of_shapes, r0, r1, c0, c1) channel rectangles (inclusive)."""
    objs = _objects(g, bg, conn)
    out = []
    tlo, thi = trim
    n = len(objs)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            A, B = objs[i], objs[j]
            if A[0] != B[0]:
                continue
            for axis in (0, 1):
                # axis 0: horizontal channel (A left of B, lanes are rows)
                # axis 1: vertical channel (A above B, lanes are columns)
                if axis == 0:
                    a_lo, a_hi, b_lo, b_hi = A[1], A[2], B[1], B[2]
                    g0, g1 = A[4] + 1, B[3] - 1
                else:
                    a_lo, a_hi, b_lo, b_hi = A[3], A[4], B[3], B[4]
                    g0, g1 = A[2] + 1, B[1] - 1
                if g1 < g0:
                    continue
                lo, hi = max(a_lo, b_lo), min(a_hi, b_hi)
                if lo > hi:
                    continue
                if basis == "smaller":
                    if (a_hi - a_lo) <= (b_hi - b_lo):
                        s_lo, s_hi = a_lo, a_hi
                    else:
                        s_lo, s_hi = b_lo, b_hi
                else:
                    s_lo, s_hi = lo, hi
                w_lo, w_hi = s_lo + tlo, s_hi - thi
                if w_lo > w_hi:
                    continue
                b_lo2, b_hi2 = (lo, hi) if block == "strip" else (w_lo, w_hi)
                clear = True
                for k in range(g0, g1 + 1):
                    for L in range(b_lo2, b_hi2 + 1):
                        y, x = (L, k) if axis == 0 else (k, L)
                        if not (0 <= y < len(g) and 0 <= x < len(g[0])) or g[y][x] != bg:
                            clear = False
                            break
                    if not clear:
                        break
                if not clear:
                    continue
                if axis == 0:
                    out.append((A[0], w_lo, w_hi, g0, g1))
                else:
                    out.append((A[0], g0, g1, w_lo, w_hi))
    return out


def _paint(g, bg, chans, mode, col):
    H, W = len(g), len(g[0])
    o = [r[:] for r in g]
    for c, r0, r1, c0, c1 in chans:
        v = c if mode == "same" else col
        for y in range(max(r0, 0), min(r1, H - 1) + 1):
            for x in range(max(c0, 0), min(c1, W - 1) + 1):
                if g[y][x] == bg:
                    o[y][x] = v
    return o


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if not gi or not gi[0] or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    changed = set()
    for pr in train:
        gi, go = pr["input"], pr["output"]
        bg = _bg(gi)
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    if a != bg or b == bg:
                        return  # channels only paint over background
                    changed.add(b)
    if not changed:
        return
    modes = [("const", 0, c) for c in sorted(changed)] if len(changed) == 1 else []
    modes.append(("same", 1, None))
    trims = [((1, 1), 0), ((0, 0), 2), ((2, 2), 3), ((1, 0), 4), ((0, 1), 4)]
    found = []
    for conn in (4, 8):
        if conn == 8 and all(_objects(p["input"], _bg(p["input"]), 4) == _objects(p["input"], _bg(p["input"]), 8)
                             for p in train):
            continue
        for basis, bc in (("overlap", 0), ("smaller", 1)):
            for block, kc in (("strip", 0), ("channel", 1)):
                for trim, tc in trims:
                    chs = []
                    for p in train:
                        bg = _bg(p["input"])
                        chs.append((bg, _channels(p["input"], bg, conn, trim, basis, block)))
                    if not any(c for _, c in chs):
                        continue
                    for mode, mc, col in modes:
                        if all(_paint(p["input"], bg, c, mode, col) == p["output"]
                               for p, (bg, c) in zip(train, chs)):
                            cost = 10 + tc + bc + kc + mc + (conn == 8)
                            name = "channel[%s,trim=%d/%d,%s,%s,c%d]" % (
                                "colour=%d" % col if mode == "const" else "same", trim[0], trim[1],
                                basis, block, conn)
                            found.append((cost, len(found), name, (conn, trim, basis, block, mode, col)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


def _make(conn, trim, basis, block, mode, col):
    def fn(grid):
        bg = _bg(grid)
        return _paint(grid, bg, _channels(grid, bg, conn, trim, basis, block), mode, col)
    return fn


FAMILIES = [fam]
