"""Line family for card 0d87d2a6 (test-blind; induced only from train pairs).

Reading: markers are lone cells (size-1 components).  Two markers of the same colour are partners when
they face each other from opposite borders of the grid (cheapest setting), or more loosely when they share
a row / column (optionally a diagonal).  Partners are joined by a straight beam of their colour drawn from
one to the other, and every shape the beam passes through (optionally: touches) is recoloured, whole,
into the beam colour.  Everything else is left as it was.
"""
from collections import Counter

CARD = "0d87d2a6"
LINE = ("draw strait colored lines/beam  between same-colored markers and convert every shape on the "
        "beams' way into that color")
READING = {
    "generator": "Join each pair of same-coloured markers with a straight beam of their colour, "
                 "and repaint every shape the beam crosses, whole, in that colour.",
    "stop": "Each beam runs from one marker to its partner and no further; only shapes met on that segment change "
            "(a shape met by beams of different colours is left as is); unpaired markers draw nothing.",
    "params": "partners ∈ {lone cells facing each other from opposite borders, any lone cells on a common "
              "row/column, lone border cells on a common row/column, the last two also with diagonals} "
              "· on the way ∈ {beam passes through the shape, beam passes through or runs alongside it} "
              "· shape ∈ {one-colour component, any non-background component} · connectivity ∈ {4, 8}",
    "participants": "Background = most frequent colour.  Markers = size-1 components (8-connected, single colour); "
                    "partners = two markers of the same colour, straight across the grid from each other on opposite "
                    "borders (or, loosely, on any common line).  Shapes = the remaining non-background connected "
                    "components.",
    "preconditions": "Input and output have the same size, some cell changes in every pair, every training input "
                     "holds at least one partnered pair of same-coloured markers, and the induced setting reproduces "
                     "every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
D8 = D4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _comps(g, keep, conn, mono):
    """Connected components over cells where keep(y, x); mono => neighbours must share the colour."""
    H, W = len(g), len(g[0])
    nb = D4 if conn == 4 else D8
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not keep(y, x):
                continue
            seen[y][x] = True
            st, pix = [(y, x)], []
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if (0 <= p < H and 0 <= q < W and not seen[p][q] and keep(p, q)
                            and (not mono or g[p][q] == g[a][b])):
                        seen[p][q] = True
                        st.append((p, q))
            out.append(pix)
    return out


def _markers(g, bg, who):
    H, W = len(g), len(g[0])
    ms = []
    for pix in _comps(g, lambda y, x: g[y][x] != bg, 8, True):
        if len(pix) != 1:
            continue
        y, x = pix[0]
        if who == "border" and not (y in (0, H - 1) or x in (0, W - 1)):
            continue
        ms.append((y, x))
    return ms


def _beams(g, ms, diag, pairing):
    """Segments (colour, cells strictly between the two markers) for same-colour marker pairs.
    pairing 'facing': the two markers sit on opposite borders of the grid, straight across from each other
    (a border marker beams perpendicular to its border); 'collinear': any common row / column (/ diagonal)."""
    H, W = len(g), len(g[0])
    out = []
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            (y0, x0), (y1, x1) = ms[i], ms[j]
            c = g[y0][x0]
            if g[y1][x1] != c:
                continue
            dy, dx = y1 - y0, x1 - x0
            if pairing == "facing":
                if not ((dy == 0 and {x0, x1} == {0, W - 1}) or (dx == 0 and {y0, y1} == {0, H - 1})):
                    continue
            elif not (dy == 0 or dx == 0 or (diag and abs(dy) == abs(dx))):
                continue
            n = max(abs(dy), abs(dx))
            sy, sx = (dy > 0) - (dy < 0), (dx > 0) - (dx < 0)
            out.append((c, [(y0 + k * sy, x0 + k * sx) for k in range(1, n)]))
    return out


def _apply(g, who, pairing, diag, way, mono, conn):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    ms = _markers(g, bg, who)
    beams = _beams(g, ms, diag, pairing)
    if not beams:
        return None
    mset = set(ms)
    shapes = _comps(g, lambda y, x: g[y][x] != bg and (y, x) not in mset, conn, mono)
    owner = {}
    for si, pix in enumerate(shapes):
        for p in pix:
            owner[p] = si
    hit = {}
    for c, cells in beams:
        probe = set(cells)
        if way == "touch":
            probe |= {(a + dy, b + dx) for a, b in cells for dy, dx in D4}
        for p in probe:
            si = owner.get(p)
            if si is not None:
                hit.setdefault(si, set()).add(c)
    out = [r[:] for r in g]
    for c, cells in beams:
        for a, b in cells:
            out[a][b] = c
    for si, cols in hit.items():
        if len(cols) == 1:
            c = next(iter(cols))
            for a, b in shapes[si]:
                out[a][b] = c
    return out


def fam(train):
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]) or gi == go:
            return
    space = []
    pairs = (("border", "facing", False, 0), ("any", "collinear", False, 1), ("border", "collinear", False, 2),
             ("any", "collinear", True, 2), ("border", "collinear", True, 3))
    for who, pairing, diag, pc in pairs:
        for way, yc in (("through", 0), ("touch", 2)):
            for mono, mc in ((True, 0), (False, 1)):
                for conn, cc in ((4, 0), (8, 1)):
                    space.append((10 + pc + yc + mc + cc, (who, pairing, diag, way, mono, conn)))
    space.sort(key=lambda t: t[0])
    for cost, spec in space:
        if not all(_apply(pr["input"], *spec) == pr["output"] for pr in train):
            continue
        who, pairing, diag, way, mono, conn = spec
        name = "beam_between_markers[%s,%s,%s,%s,%s,c%d]" % (
            who, pairing, "orth+diag" if diag else "orth", way, "mono" if mono else "multi", conn)
        yield name, cost, _make(spec)


def _make(spec):
    def fn(grid):
        o = _apply(grid, *spec)
        return [r[:] for r in grid] if o is None else o
    return fn


FAMILIES = [fam]
