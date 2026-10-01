"""Line family for card 7d18a6fb (test-blind; written from the reviewer's line and train pairs only).

Reading: the grid holds one "coloured area" -- a single-colour region (solid block or frame) whose
bounding box also holds foreground markers of other colours -- plus loose glyphs scattered elsewhere.
The area is extracted (cropped, or edited in place), its own colour is removed (turned into the grid
background), and every marker is replaced by the glyph of the same colour found outside the area,
stamped so that a chosen anchor of the glyph (its centre or a corner of its bbox) lands on the same
anchor of the marker.  Only the glyph's coloured pixels are painted; the glyph's background cells
leave the (now cleared) area showing through, so the marker cell itself disappears when the glyph is
hollow there.
"""
from collections import Counter

CARD = "7d18a6fb"
LINE = "extract colored area, remove its background and replace foreground markers with matching color stamps/glyphs"
READING = {
    "generator": "Crop the coloured area (the single-colour block whose bbox holds foreign-coloured markers), "
                 "turn its own colour into the grid background, and on each marker stamp the glyph of the "
                 "marker's colour found elsewhere in the grid, aligning glyph and marker by their bbox centre "
                 "(or a declared corner).",
    "stop": "One stamp per marker, painted once from the input; only the glyph's coloured pixels are drawn, "
            "clipped to the area; markers whose colour has no glyph outside the area stay as they are.",
    "params": "anchor ∈ {centre, centre-ceil, top-left, top-right, bottom-left, bottom-right} · "
              "glyph ∈ {all cells of the colour outside the area, largest 8-connected component of it} · "
              "inset ∈ {0, 1} (crop the area's bbox or its interior) · fill ∈ {background, keep area colour} · "
              "output ∈ {crop to area, in place keeping the rest, in place erasing the used glyphs}",
    "participants": "Background: most frequent colour of the grid. Area: the 4-connected single-colour non-"
                    "background component with the largest bbox among those whose bbox holds a cell of another "
                    "non-background colour. Area colour: most frequent colour inside the (inset) bbox. Markers: "
                    "8-connected single-colour components inside the bbox whose colour is neither background nor "
                    "area colour. Glyphs: cells of each marker colour outside the area's bbox.",
    "preconditions": "Every training input has such an area holding at least one marker, every marker colour "
                     "seen in training has a glyph outside the area, the output has the area's size (crop) or "
                     "the input's size (in place), and the induced settings reproduce every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
D8 = D4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
ANCHORS = ("centre", "centre-ceil", "tl", "tr", "bl", "br")


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _comps(g, keep, conn):
    """Single-colour connected components over cells with keep(y, x) true; sorted, deterministic."""
    H, W = len(g), len(g[0])
    nb = D4 if conn == 4 else D8
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or not keep(y, x):
                continue
            c = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c and keep(p, q):
                        seen[p][q] = True
                        st.append((p, q))
            out.append((c, sorted(pix)))
    out.sort(key=lambda o: (o[1][0], o[0]))
    return out


def _bbox(pix):
    ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
    return min(ys), min(xs), max(ys), max(xs)


def _area(g, bg):
    """bbox (r0, c0, r1, c1) of the coloured area, or None."""
    best = None
    for c, pix in _comps(g, lambda y, x: g[y][x] != bg, 4):
        r0, c0, r1, c1 = _bbox(pix)
        foreign = any(g[y][x] not in (bg, c) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1))
        if not foreign:
            continue
        key = ((r1 - r0 + 1) * (c1 - c0 + 1), len(pix), -r0, -c0)
        if best is None or key > best[0]:
            best = (key, (r0, c0, r1, c1))
    return None if best is None else best[1]


def _anchor(r0, c0, r1, c1, a):
    if a == "centre":
        return r0 + (r1 - r0) // 2, c0 + (c1 - c0) // 2
    if a == "centre-ceil":
        return r0 + (r1 - r0 + 1) // 2, c0 + (c1 - c0 + 1) // 2
    return (r0 if a[0] == "t" else r1), (c0 if a[1] == "l" else c1)


def _parse(g, inset, glyph_mode):
    """-> dict with bg, box (inset bbox), area colour, markers [(c, bbox)], glyphs {c: pixels}; or None."""
    bg = _bg(g)
    box = _area(g, bg)
    if box is None:
        return None
    r0, c0, r1, c1 = box
    r0, c0, r1, c1 = r0 + inset, c0 + inset, r1 - inset, c1 - inset
    if r0 > r1 or c0 > c1:
        return None
    inside = lambda y, x: r0 <= y <= r1 and c0 <= x <= c1
    fc = Counter(g[y][x] for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)).most_common(1)[0][0]
    markers = [(c, _bbox(p)) for c, p in _comps(g, lambda y, x: inside(y, x) and g[y][x] not in (bg, fc), 8)]
    if not markers:
        return None
    H, W = len(g), len(g[0])
    glyphs = {}
    for c in sorted({m[0] for m in markers}):
        if glyph_mode == "colour":
            pix = [(y, x) for y in range(H) for x in range(W) if g[y][x] == c and not inside(y, x)]
        else:
            cs = _comps(g, lambda y, x, c=c: g[y][x] == c and not inside(y, x), 8)
            pix = max((p for _, p in cs), key=len) if cs else []  # max keeps the first of equal size
        if pix:
            glyphs[c] = pix
    return {"bg": bg, "box": (r0, c0, r1, c1), "fc": fc, "markers": markers, "glyphs": glyphs}


def _render(g, P, anchor, fill, output):
    bg, fc = P["bg"], P["fc"]
    r0, c0, r1, c1 = P["box"]
    H, W = len(g), len(g[0])
    out = [r[:] for r in g]
    mcells = set()
    for c, (a0, b0, a1, b1) in P["markers"]:
        for y in range(a0, a1 + 1):
            for x in range(b0, b1 + 1):
                if g[y][x] == c:
                    mcells.add((y, x))
    # clear the area: its own colour -> background (or kept); markers -> what lies under them
    for y in range(r0, r1 + 1):
        for x in range(c0, c1 + 1):
            if (y, x) in mcells:
                out[y][x] = bg if fill == "bg" else fc
            elif g[y][x] == fc and fill == "bg":
                out[y][x] = bg
    if output == "erase":
        for c in sorted(P["glyphs"]):
            for y, x in P["glyphs"][c]:
                out[y][x] = bg
    # stamp the glyphs (painted from the input, in marker order)
    for c, mb in P["markers"]:
        pix = P["glyphs"].get(c)
        if pix is None:
            for y, x in sorted(mcells):
                if g[y][x] == c and mb[0] <= y <= mb[2] and mb[1] <= x <= mb[3]:
                    out[y][x] = c
            continue
        gy, gx = _anchor(*_bbox(pix), anchor)
        my, mx = _anchor(*mb, anchor)
        for y, x in pix:
            p, q = y - gy + my, x - gx + mx
            if r0 <= p <= r1 and c0 <= q <= c1:
                out[p][q] = c
    if output == "crop":
        return [row[c0:c1 + 1] for row in out[r0:r1 + 1]]
    return out


def _make(inset, glyph_mode, anchor, fill, output):
    def fn(grid):
        P = _parse(grid, inset, glyph_mode)
        if P is None:
            return [r[:] for r in grid]
        return _render(grid, P, anchor, fill, output)
    return fn


def fam(train):
    if not train:
        return
    found = []
    for inset in (0, 1):
        for gi_, glyph_mode in enumerate(("colour", "component")):
            parsed = [_parse(p["input"], inset, glyph_mode) for p in train]
            if any(P is None for P in parsed):
                continue
            # every marker colour seen in training must have a glyph
            if any(m[0] not in P["glyphs"] for P in parsed for m in P["markers"]):
                continue
            if glyph_mode == "component" and all(
                    P["glyphs"] == parsed_c["glyphs"]
                    for P, parsed_c in zip(parsed, [_parse(p["input"], inset, "colour") for p in train])):
                continue  # identical to the cheaper glyph reading on these inputs
            sizes = []
            for p, P in zip(train, parsed):
                r0, c0, r1, c1 = P["box"]
                go, gin = p["output"], p["input"]
                if (len(go), len(go[0])) == (r1 - r0 + 1, c1 - c0 + 1):
                    sizes.append("crop")
                elif (len(go), len(go[0])) == (len(gin), len(gin[0])):
                    sizes.append("place")
                else:
                    sizes.append(None)
            if None in sizes or len(set(sizes)) != 1:
                continue
            outputs = [("crop", 0)] if sizes[0] == "crop" else [("keep", 0), ("erase", 1)]
            odd = all((b[2] - b[0]) % 2 == 0 and (b[3] - b[1]) % 2 == 0
                      for P in parsed for b in [m[1] for m in P["markers"]] + [_bbox(v) for v in P["glyphs"].values()])
            for ai, anchor in enumerate(ANCHORS):
                if anchor == "centre-ceil" and odd:
                    continue  # same as centre on these inputs
                fills = [("bg", 0)] + ([] if all(P["fc"] == P["bg"] for P in parsed) else [("keep", 1)])
                for fill, fi in fills:
                    for output, oi in outputs:
                        ok = all(_render(p["input"], P, anchor, fill, output) == p["output"]
                                 for p, P in zip(train, parsed))
                        if not ok:
                            continue
                        cost = 10 + ai + 2 * inset + gi_ + fi + oi
                        name = "stamp_markers[%s,glyph=%s,inset=%d,fill=%s,%s]" % (
                            anchor, glyph_mode, inset, fill, output)
                        found.append((cost, len(found), name, (inset, glyph_mode, anchor, fill, output)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


FAMILIES = [fam]
