"""Prior family: RECTANGLE_FROM_DELIMITERS (priors3, G68 pass) -- locate rectangles implied by delimiters, then
apply one operation. Widened test-blind by specialising over FITTED BINDINGS (training pairs only).

BINDINGS -- each fitted member's first program, every induced value with the ROLE that explains it
(rank = frequency rank of the marker among the non-background colours of every training input):
  member    locator                          adjust                     op / colour / size
  32597951  bbox(8)  m <- rarest colour      0                          fill all; colour 3 <- the colour new in
                                                                        the outputs (constant)
  36fdfd69  bbox(2,near2) m <- rarest        0                          fill all; 4 <- new colour (bg varies 8/0)
  3f7978a0  bbox(5)  m <- rarest (bars)      (-1,0) <- outset to the    crop; size <- bar span + caps
                                             end caps (literal)
  505fff84  between(1,8) start/end <- the    0                          crop; width <- gap between markers
            two marker colours (literal)
  6b9890af  bbox(2)  m <- dominant (frame)   0                          fit; scale <- interior / shape size
  6f8cd79b  bbox(bg) <- whole canvas         0                          outline bg; 8 <- new colour
  846bdb03  bbox(4)  m <- rarest (4 corner   0                          fit mirror; orientation <- agreement
            dots)                                                       with the adjacent outline
  928ad970  bbox(5)  m <- rarest (4 dots)    (1,1) <- inset by marker   outline bg; colour <- object.colour
                                             thickness (1)
  9aec4887  frame <- hollow ring / 4 bars    0                          fit nearest; colour <- nearest side
  a644e277  lattice <- ruling-line colour    0                          crop; box <- broken crossings
  aab50785  between(8,8) <- equal-shaped     0                          crop; rank of 8 varies -> literal kept
            marker pair (literal)
  af902bf9  bbox(4,rook) m <- dominant (the  (1,1) <- inset by marker   fill bg; 2 <- new colour
            only colour)                     thickness (1)
  d37a1ef5  bbox(2)  m <- dominant (frame)   0                          around bg; colour 2 <- MARKER colour
                                                                        (was literal const 2)
  e7639916  bbox(8)  m <- dominant (only)    0                          outline bg; 1 <- new colour
  e7a25a18  bbox(2)  m <- dominant (frame)   0                          fit; scale <- interior / shape size
Specialisation menu built from these bindings (replacing literals where a role explains the value):
  marker  m in {literal common colour, dom, rare, each}: a literal is replaced by dom/rare when that role names
          it in every input; dom/rare are also tried when the colour itself varies between pairs; each = one
          marker set per non-background colour except the dominant one, colour <- that box's own marker
  colour  const -> marker when the constant equals the marker colour in every pair (colour <- marker.colour)
  adjust  literal insets/outsets, plus snap: distance <- gap to the nearest ruling line (rows/columns with no
          cell of the dominant colour), each side pushed outward onto it
  fit     scale <- interior / shape size (integer, crop) | in place: shape erased and stretched into the box
          interior (int or vertex mapping) | anchor: scale and offset <- the template fragments already inside
  paint   style cells = outline + the lattice cells inside the box (ruling lines left alone)
Widened members (via those role-bound parameters only): 97239e3d (each + snap + cells, colour <- marker),
465b7d93 (dom + fit in place, vertex), 8a004b2b (corner colour, literal, + fit anchor).

One generator, LOCATE-RECT(locator; adjust) -> OP(op params):
  locator   bbox(m, group)   bounding box of the cells of marker colour m, one box per group of markers
                             (group in all | rook (linked by sharing a row/column) | c8 component | near2 cluster
                             (Chebyshev gap <= 2)); m = background means the whole canvas; m may be a role
            corners          the colour with exactly four cells at the corners of a rectangle (crop marks)
            frame            the largest single-colour hollow ring (one cell thick, non-empty interior), else four
                             uniform straight bars on the four sides of a rectangle (corners free)
            between(a,b,ax)  start/end marker pairs: two equal-shaped solid objects of colours a and b on the
                             same rows (ax=0) or columns (ax=1); the rectangle is the strip strictly between them
            lattice          ruling lines of one colour; the crossings that break the line colour span the box
  adjust    inset/outset (dr, dc) applied to every box (positive = inset, negative = outset), or snap
  op        paint(style, which, colour)  style in outline | fill | around | cells; which cells: background only |
                                         every cell except the delimiters; colour: constant (the single colour
                                         added in training) | the marker colour | the dominant other object colour
            recolour                     an induced colour map applied to the cells inside the boxes
            crop                         cut the box out; several boxes are stacked in reading order
            fit(mirror)                  crop the box and redraw the loose shape (every non-background cell not on
                                         the box outline) in its interior, scaled by integer factors to fill it,
                                         optionally mirrored so its colours best agree with the adjacent outline,
                                         or recoloured cell-wise by the uniquely nearest outline side;
                                         fit(inplace, mapper) and fit(anchor) as above
Everything colour/size/position related is read from the grid or induced from the training pairs.
"""
from collections import Counter

CARD = "prior3_rectangle_from_delimiters"
CONCEPT = "rectangle_from_delimiters"
MEMBERS = ["1c02dbbe", "20a9e565", "256b0a75", "32597951", "36fdfd69", "3f7978a0", "465b7d93", "505fff84",
           "692cd3b6", "6b9890af", "6f8cd79b", "846bdb03", "8a004b2b", "928ad970", "9385bd28", "97239e3d",
           "9aec4887", "a644e277", "aab50785", "af902bf9", "d37a1ef5", "db615bd4", "e4075551", "e7639916",
           "e7a25a18"]
READING = {
    "generator": "Find the rectangles implied by delimiters (bounding box of a marker-colour group, four corner "
                 "crop marks, a hollow frame or four side bars, the strip between start/end marker pairs, or the broken crossings "
                 "of a lattice), inset/outset them or snap them to ruling lines, then draw their outline, fill or "
                 "recolour their inside, crop them out (stacking several), or fit the loose shape into one "
                 "(cropped or in place) by stretching it or aligning it with the fragments already inside.",
    "stop": "single pass: every located rectangle is processed once; a fitted shape fills the interior exactly",
    "params": "locator in {bbox(m in {literal, dom, rare, each}, group in {all, rook, c8, near2}), corners, frame, "
              "between(a, b, axis in {0,1}), lattice} . adjust in {(0,0),(1,1),(-1,-1),(2,2),(+-1,0),(0,+-1), "
              "snap to nearest ruling line} . op in {paint(style in {outline, fill, around, cells}, which in "
              "{bg, all-but-delimiters}, colour in {const, marker, object}), recolour(induced map), crop(stack), "
              "fit(mirror in {no, best}, recolour in {keep, nearest side}), fit(inplace, mapper in {int, vertex}), "
              "fit(anchor: scale/offset from fragments inside)}",
    "participants": "background = per-grid most common colour; markers = cells of an anchor colour present in "
                    "every training input (or the corner/frame/bracket objects); loose shape = non-background "
                    "cells off the rectangle outline",
    "preconditions": "same-shape pairs -> paint/recolour ops, the changed cells must lie inside the located boxes; "
                     "shape-changing pairs -> crop/fit ops, the box size (or stacked size) must equal the output size",
}

ADJUSTS = ((0, 0), (1, 1), (-1, -1), (2, 2), (-1, 0), (0, -1), (1, 0), (0, 1), "snap")
_N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
_N8 = _N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


# ------------------------------------------------------------------------------------------------ helpers
def _bg(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _colours(g):
    return {v for row in g for v in row}


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _comps(cells, nbrs):
    cs = set(cells)
    seen, out = set(), []
    for s in sorted(cs):
        if s in seen:
            continue
        seen.add(s)
        st, comp = [s], []
        while st:
            y, x = st.pop()
            comp.append((y, x))
            for dy, dx in nbrs:
                t = (y + dy, x + dx)
                if t in cs and t not in seen:
                    seen.add(t)
                    st.append(t)
        out.append(sorted(comp))
    return out


def _rook(cells):
    parent = list(range(len(cells)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    first_r, first_c = {}, {}
    for i, (r, c) in enumerate(cells):
        for key, table in ((r, first_r), (c, first_c)):
            j = table.setdefault(key, i)
            if j != i:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    comps = {}
    for i, rc in enumerate(cells):
        comps.setdefault(find(i), []).append(rc)
    return [sorted(v) for v in comps.values()]


_NEAR2 = tuple((dy, dx) for dy in range(-2, 3) for dx in range(-2, 3) if (dy, dx) != (0, 0))


# ------------------------------------------------------------------------------------------------ locators
# each returns (list of (box, delimiter_cells), marker_colour or None); box = (r0, r1, c0, c1)
class _Delim(set):
    """delimiter cells of one box, carrying that box's own marker colour (role-bound marker 'each')."""
    col = None


def _ranked(g):
    """background and the non-background colours by decreasing count (ties broken by colour)."""
    cnt = Counter(v for row in g for v in row)
    bg = max(sorted(cnt), key=lambda k: cnt[k])
    nb = sorted((k for k in cnt if k != bg), key=lambda k: (-cnt[k], k))
    return bg, nb, cnt


def _role_colour(g, role):
    """marker colour bound by ROLE instead of by value: dom = the most frequent non-background colour,
    rare = the least frequent one (None on a count tie, so the binding is never arbitrary)."""
    bg, nb, cnt = _ranked(g)
    if not nb:
        return None
    if role == "dom":
        return nb[0] if len(nb) == 1 or cnt[nb[0]] != cnt[nb[1]] else None
    return nb[-1] if len(nb) == 1 or cnt[nb[-1]] != cnt[nb[-2]] else None


def _groups(cells, group):
    if group == "all":
        groups = [cells]
    elif group == "rook":
        groups = _rook(cells)
    elif group == "c8":
        groups = _comps(cells, _N8)
    else:
        groups = _comps(cells, _NEAR2)
    groups.sort(key=lambda gr: (_bbox(gr)[0], _bbox(gr)[2]))
    return groups


def _loc_bbox(g, m, group):
    if m == "each":                       # every marker colour = every non-background colour but the dominant one
        bg, nb, cnt = _ranked(g)
        if len(nb) < 2:
            return [], None
        res = []
        for col in sorted(nb[1:]):
            cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == col]
            for gr in _groups(cells, group):
                d = _Delim(gr)
                d.col = col
                res.append((_bbox(gr), d))
        res.sort(key=lambda t: (t[0], t[1].col))
        return res, None
    if m in ("dom", "rare"):
        m = _role_colour(g, m)
        if m is None:
            return [], None
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == m]
    if not cells:
        return [], m
    return [(_bbox(gr), set(gr)) for gr in _groups(cells, group)], m


def _loc_corners(g, bg):
    pos = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != bg:
                pos.setdefault(v, []).append((r, c))
    best = None
    for col in sorted(pos):
        ps = pos[col]
        if len(ps) != 4:
            continue
        rs = sorted({p[0] for p in ps})
        cs = sorted({p[1] for p in ps})
        if len(rs) != 2 or len(cs) != 2 or rs[1] - rs[0] < 2 or cs[1] - cs[0] < 2:
            continue
        area = (rs[1] - rs[0]) * (cs[1] - cs[0])
        if best is None or area > best[0]:
            best = (area, col, (rs[0], rs[1], cs[0], cs[1]), set(ps))
    if best is None:
        return [], None
    return [(best[2], best[3])], best[1]


def _loc_frame(g, bg):
    pos = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != bg:
                pos.setdefault(v, []).append((r, c))
    best = None
    for col in sorted(pos):
        for comp in _comps(pos[col], _N8):
            r0, r1, c0, c1 = _bbox(comp)
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            if len(comp) != 2 * (r1 - r0 + c1 - c0):
                continue
            s = set(comp)
            if not all((r, c) in s for r in (r0, r1) for c in range(c0, c1 + 1)):
                continue
            if not all((r, c) in s for c in (c0, c1) for r in range(r0, r1 + 1)):
                continue
            area = (r1 - r0 + 1) * (c1 - c0 + 1)
            if best is None or area > best[0]:
                best = (area, col, (r0, r1, c0, c1), s)
    if best is None:
        best = _four_bars(g, bg)
    if best is None:
        return [], None
    return [(best[2], best[3])], best[1]


def _four_bars(g, bg):
    """Four uniform straight bars on the four sides of a rectangle (its corners left free)."""
    hs, vs = {}, {}
    pos = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != bg:
                pos.setdefault(v, []).append((r, c))
    for col in sorted(pos):
        for comp in _comps(pos[col], _N4):
            r0, r1, c0, c1 = _bbox(comp)
            if len(comp) < 2 or len(comp) != (r1 - r0 + 1) * (c1 - c0 + 1):
                continue
            if r0 == r1:
                hs.setdefault((c0, c1), []).append((r0, comp))
            elif c0 == c1:
                vs.setdefault((r0, r1), []).append((c0, comp))
    best = None
    for (c0, c1), lst in sorted(hs.items()):
        for rt, top in lst:
            for rb, bot in lst:
                if rb <= rt + 1:
                    continue
                side = dict(vs.get((rt + 1, rb - 1), []))
                if c0 - 1 in side and c1 + 1 in side:
                    area = (rb - rt + 1) * (c1 - c0 + 3)
                    if best is None or area > best[0]:
                        best = (area, None, (rt, rb, c0 - 1, c1 + 1),
                                set(top) | set(bot) | set(side[c0 - 1]) | set(side[c1 + 1]))
    return best


def _solid_objects(g, col):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == col]
    out = []
    for comp in _comps(cells, _N4):
        r0, r1, c0, c1 = _bbox(comp)
        if len(comp) == (r1 - r0 + 1) * (c1 - c0 + 1):
            out.append(((r0, r1, c0, c1), comp))
    return out


def _loc_between(g, a, b, axis):
    gg = g if axis == 0 else [list(x) for x in zip(*g)]
    starts = _solid_objects(gg, a)
    ends = starts if a == b else _solid_objects(gg, b)
    used = set()
    res = []
    for k, (sb, scells) in enumerate(sorted(starts)):
        if (sb, a) in used:
            continue
        cand = [(eb, ec) for eb, ec in ends if eb[0] == sb[0] and eb[1] == sb[1] and eb[2] > sb[3] + 1
                and eb[3] - eb[2] == sb[3] - sb[2] and (eb, b) not in used]
        if not cand:
            continue
        eb, ecells = min(cand)
        used.add((sb, a))
        used.add((eb, b))
        box = (sb[0], sb[1], sb[3] + 1, eb[2] - 1)
        delim = set(scells) | set(ecells)
        if axis == 1:
            box = (box[2], box[3], box[0], box[1])
            delim = {(c, r) for r, c in delim}
        res.append((box, delim))
    res.sort()
    return res, None


def _loc_lattice(g, bg):
    H, W = len(g), len(g[0])
    best = None
    for L in sorted(_colours(g)):
        if L == bg:
            continue
        rows = [r for r in range(H) if 2 * sum(1 for x in g[r] if x == L) > W]
        cols = [c for c in range(W) if 2 * sum(1 for r in range(H) if g[r][c] == L) > H]
        if rows and cols and (best is None or len(rows) + len(cols) > best[0]):
            best = (len(rows) + len(cols), L, rows, cols)
    if best is None:
        return [], None
    _, L, rows, cols = best
    holes = [(r, c) for r in rows for c in cols if g[r][c] != L]
    if len(holes) < 2:
        return [], None
    return [(_bbox(holes), set(holes))], L


def _locate(g, key):
    kind = key[0]
    bg = _bg(g)
    if kind == "bbox":
        return _loc_bbox(g, key[1], key[2])
    if kind == "corners":
        return _loc_corners(g, bg)
    if kind == "frame":
        return _loc_frame(g, bg)
    if kind == "between":
        return _loc_between(g, key[1], key[2], key[3])
    return _loc_lattice(g, bg)


def _separators(g):
    """ruling lines of a block layout: the rows / columns holding no cell of the dominant non-background colour."""
    bg, nb, cnt = _ranked(g)
    if not nb:
        return [], []
    blk = nb[0]
    H, W = len(g), len(g[0])
    rows = [r for r in range(H) if all(v != blk for v in g[r])]
    cols = [c for c in range(W) if all(g[r][c] != blk for r in range(H))]
    return rows, cols


def _snap(box, seps, H, W):
    """distance <- gap to the nearest ruling line: push each side outward onto the nearest separator line."""
    (r0, r1, c0, c1), (rows, cols) = box, seps
    lo = [s for s in rows if s <= r0]
    hi = [s for s in rows if s >= r1]
    lc = [s for s in cols if s <= c0]
    hc = [s for s in cols if s >= c1]
    return (max(lo) if lo else 0, min(hi) if hi else H - 1, max(lc) if lc else 0, min(hc) if hc else W - 1)


def _adjust(boxes, adj, H, W, clip, g=None):
    if adj == "snap":
        seps = _separators(g)
        if not seps[0] or not seps[1]:
            return None
        return [(_snap(b, seps, H, W), delim) for b, delim in boxes]
    dr, dc = adj
    out = []
    for (r0, r1, c0, c1), delim in boxes:
        r0, r1, c0, c1 = r0 + dr, r1 - dr, c0 + dc, c1 - dc
        if clip:
            r0, c0, r1, c1 = max(r0, 0), max(c0, 0), min(r1, H - 1), min(c1, W - 1)
        if r0 > r1 or c0 > c1:
            continue
        if r0 < 0 or c0 < 0 or r1 >= H or c1 >= W:
            return None
        out.append(((r0, r1, c0, c1), delim))
    return out


# ------------------------------------------------------------------------------------------------ operations
def _object_colour(g, bg, m):
    cnt = Counter(v for row in g for v in row if v != bg and v != m)
    if not cnt:
        return None
    top = cnt.most_common(2)
    if len(top) == 2 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def _paint(g, boxes, m, style, which, colour, cmap):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    per_box = colour == "marker" and m is None and boxes and all(getattr(d, "col", None) is not None
                                                                 for _, d in boxes)
    if colour == "marker":
        colour = m
    elif colour == "object":
        colour = _object_colour(g, bg, m)
    if colour is None and cmap is None and not per_box:
        return None
    seps = _separators(g) if style == "cells" else None
    out = [row[:] for row in g]
    for (r0, r1, c0, c1), delim in boxes:
        if per_box:
            colour = delim.col
        hole = None
        if style == "around":
            inner = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
                     if g[r][c] != bg and (r, c) not in delim and g[r][c] != m]
            if inner:
                hole = _bbox(inner)
        for r in range(r0, r1 + 1):
            edge = r == r0 or r == r1
            for c in range(c0, c1 + 1):
                if style == "outline" and not (edge or c == c0 or c == c1):
                    continue
                if style == "cells" and not (edge or c == c0 or c == c1) and (r in seps[0] or c in seps[1]):
                    continue                  # outline + the lattice cells inside (ruling lines left alone)
                if hole is not None and hole[0] <= r <= hole[1] and hole[2] <= c <= hole[3]:
                    continue
                v = g[r][c]
                if cmap is not None:
                    if v in cmap and (r, c) not in delim:
                        out[r][c] = cmap[v]
                elif which == "bg":
                    if v == bg:
                        out[r][c] = colour
                elif (r, c) not in delim:
                    out[r][c] = colour
    return out


def _crop(g, boxes):
    parts = [[row[c0:c1 + 1] for row in g[r0:r1 + 1]] for (r0, r1, c0, c1), _ in boxes]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    if len({len(p[0]) for p in parts}) == 1:
        return [row for p in parts for row in p]
    if len({len(p) for p in parts}) == 1:
        order = sorted(range(len(parts)), key=lambda i: (boxes[i][0][2], boxes[i][0][0]))
        return [sum((parts[i][r] for i in order), []) for r in range(len(parts[0]))]
    return None


_MIRRORS = (lambda P: P, lambda P: [row[::-1] for row in P], lambda P: P[::-1],
            lambda P: [row[::-1] for row in P[::-1]])


def _side_colour(cells, bg):
    cnt = Counter(v for v in cells if v != bg)
    return max(sorted(cnt), key=lambda k: cnt[k]) if cnt else None


def _fit(g, boxes, mirror, nearest=False):
    if len(boxes) != 1:
        return None
    (r0, r1, c0, c1), _ = boxes[0]
    ih, iw = r1 - r0 - 1, c1 - c0 - 1
    if ih < 1 or iw < 1:
        return None
    bg = _bg(g)
    loose = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg
             and not (r0 <= r <= r1 and c0 <= c <= c1 and (r in (r0, r1) or c in (c0, c1)))]
    if not loose:
        return None
    a0, a1, b0, b1 = _bbox(loose)
    ph, pw = a1 - a0 + 1, b1 - b0 + 1
    if ih % ph or iw % pw:
        return None
    sh, sw = ih // ph, iw // pw
    P = [g[a][b0:b1 + 1] for a in range(a0, a1 + 1)]
    out = [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
    cands = _MIRRORS if mirror else _MIRRORS[:1]
    best = None
    for k, f in enumerate(cands):
        Q = f(P)
        if mirror:
            score = 0
            for i in range(ih):
                for j in range(iw):
                    v = Q[i // sh][j // sw]
                    if v == bg:
                        continue
                    for di, dj in _N4:
                        y, x = i + 1 + di, j + 1 + dj
                        if (y in (0, ih + 1) or x in (0, iw + 1)) and out[y][x] == v:
                            score += 1
        else:
            score = 0
        if best is None or score > best[0]:
            best = (score, Q)
    Q = best[1]
    sides = None
    if nearest:
        sides = (_side_colour(out[0][1:-1], bg), _side_colour(out[-1][1:-1], bg),
                 _side_colour([row[0] for row in out[1:-1]], bg), _side_colour([row[-1] for row in out[1:-1]], bg))
        if None in sides:
            return None
    for i in range(ih):
        for j in range(iw):
            v = Q[i // sh][j // sw]
            if sides is not None and v != bg:
                ds = (i, ih - 1 - i, j, iw - 1 - j)
                dm = min(ds)
                if ds.count(dm) == 1:
                    v = sides[ds.index(dm)]
            out[1 + i][1 + j] = v
    return out


def _fit_anchor(g, boxes):
    """fit with scale and position bound by ROLE: scale <- size of the fragments already inside the box relative to
    the loose template outside it, offset <- where those fragments sit; the template is drawn over the crop."""
    if len(boxes) != 1:
        return None
    (r0, r1, c0, c1), delim = boxes[0]
    bg = _bg(g)
    outside, inside = [], {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v == bg:
                continue
            if r0 <= r <= r1 and c0 <= c <= c1:
                if (r, c) not in delim:
                    inside[(r, c)] = v
            else:
                outside.append((r, c))
    if not outside or not inside:
        return None
    a0, a1, b0, b1 = _bbox(outside)
    T = [g[a][b0:b1 + 1] for a in range(a0, a1 + 1)]
    th, tw = len(T), len(T[0])
    (fi, fj), fv = min(inside.items())
    for s in range(min((r1 - r0 + 1) // th, (c1 - c0 + 1) // tw), 0, -1):
        sols = []
        # the first fragment cell must land on a template cell of its colour: candidate offsets from that alone
        offs = sorted({(fi - a * s - u, fj - b * s - w) for a in range(th) for b in range(tw) if T[a][b] == fv
                       for u in range(s) for w in range(s)})
        for oi, oj in offs:
            if oi < r0 or oj < c0 or oi + th * s - 1 > r1 or oj + tw * s - 1 > c1:
                continue
            blocks, ok = set(), True
            for (i, j), x in inside.items():
                a, b = i - oi, j - oj
                if not (0 <= a < th * s and 0 <= b < tw * s) or T[a // s][b // s] != x:
                    ok = False
                    break
                blocks.add((a // s, b // s))
            if ok and all((oi + a, oj + b) in inside for p, q in blocks
                          for a in range(p * s, p * s + s) for b in range(q * s, q * s + s)):
                sols.append((oi, oj))
                break
        if sols:
            oi, oj = sols[0]
            out = [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
            for a in range(th * s):
                for b in range(tw * s):
                    v = T[a // s][b // s]
                    if v != bg:
                        out[oi + a - r0][oj + b - c0] = v
            return out
    return None


def _stretch_idx(i, n, k, mapper):
    """template indices covering interior index i of n when a k-cell template is stretched over n cells:
    int = integer blow-up (n a multiple of k); vertex = template cells as corners (edges become lines)."""
    if mapper == "int":
        return [i // (n // k)]
    if k == 1:
        return [0]
    if n == 1:
        return list(range(k))
    q, rem = divmod(i * (k - 1), n - 1)
    return [q] if rem == 0 else [q, q + 1]


def _fit_in(g, boxes, mapper):
    """fit in place: the loose shape (non-background cells off the box outline) is erased and redrawn in the box
    interior, stretched to fill it (scale <- interior size / shape size)."""
    if len(boxes) != 1:
        return None
    (r0, r1, c0, c1), delim = boxes[0]
    ih, iw = r1 - r0 - 1, c1 - c0 - 1
    if ih < 1 or iw < 1:
        return None
    bg = _bg(g)
    loose = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg and (r, c) not in delim
             and not (r0 <= r <= r1 and c0 <= c <= c1 and (r in (r0, r1) or c in (c0, c1)))]
    if not loose:
        return None
    a0, a1, b0, b1 = _bbox(loose)
    ph, pw = a1 - a0 + 1, b1 - b0 + 1
    if mapper == "int" and (ih % ph or iw % pw):
        return None
    P = [g[a][b0:b1 + 1] for a in range(a0, a1 + 1)]
    out = [row[:] for row in g]
    for r, c in loose:
        out[r][c] = bg
    for i in range(ih):
        ri = _stretch_idx(i, ih, ph, mapper)
        for j in range(iw):
            cj = _stretch_idx(j, iw, pw, mapper)
            vals = [P[x][y] for x in ri for y in cj]
            if all(v != bg for v in vals):
                cnt = Counter(vals)
                out[r0 + 1 + i][c0 + 1 + j] = max(sorted(cnt), key=lambda k: cnt[k])
            else:
                out[r0 + 1 + i][c0 + 1 + j] = bg
    return out


def _apply(g, lockey, adj, op, located=None):
    boxes, m = _locate(g, lockey) if located is None else located
    if not boxes:
        return None
    H, W = len(g), len(g[0])
    boxes = _adjust(boxes, adj, H, W, op[0] in ("paint", "recolour"), g)
    if not boxes:
        return None
    if op[0] == "fit" and op[1] == "anchor":
        return _fit_anchor(g, boxes)
    if op[0] == "fit" and op[1] == "inplace":
        return _fit_in(g, boxes, op[2])
    if op[0] == "paint":
        return _paint(g, boxes, m, op[1], op[2], op[3], None)
    if op[0] == "recolour":
        return _paint(g, boxes, m, "fill", "all", None, op[1])
    if op[0] == "crop":
        return _crop(g, boxes)
    return _fit(g, boxes, op[1], op[2])


def _make(lockey, adj, op):
    def fn(g):
        return _apply(g, lockey, adj, op)
    return fn


# ------------------------------------------------------------------------------------------------ family
def _lockeys(train, same):
    common = set.intersection(*(_colours(p["input"]) for p in train))
    bgs = {_bg(p["input"]) for p in train}
    order = sorted(common - bgs) + sorted(common & bgs)
    # role-bound marker: a literal marker colour is replaced by its role when one role explains it in every input
    bound = {}
    for role in ("dom", "rare"):
        cols = [_role_colour(p["input"], role) for p in train]
        if None not in cols:
            bound[role] = cols
    keys, used, groups = [], set(), ("all", "rook", "c8", "near2")
    for m in order:
        role = next((r for r in ("dom", "rare") if r in bound and set(bound[r]) == {m}), None)
        if role is not None and m not in bgs:
            if role in used:
                continue
            used.add(role)
            m = role
        for group in groups:
            keys.append((("bbox", m, group), 0 if m not in bgs else 2))
    for role in ("dom", "rare"):          # widening: the role holds while the colour itself varies between pairs
        if role in bound and role not in used and len(set(bound[role])) > 1:
            keys += [(("bbox", role, group), 1) for group in groups]
    if same:
        keys += [(("bbox", "each", group), 1) for group in groups]
    keys.append((("corners",), 0))
    keys.append((("frame",), 0))
    if not same:
        for a in sorted(common - bgs):
            for b in sorted(common - bgs):
                for axis in (0, 1):
                    keys.append((("between", a, b, axis), 1))
    keys.append((("lattice",), 1))
    return keys


def _diff(train):
    """changed cells per pair, constant added colour (or None), induced colour map (or None)."""
    diffs, added, cmap = [], set(), {}
    for p in train:
        a, b = p["input"], p["output"]
        d = []
        for r, (ra, rb) in enumerate(zip(a, b)):
            for c, (x, y) in enumerate(zip(ra, rb)):
                if x != y:
                    d.append((r, c))
                    added.add(y)
                    if cmap is not None and cmap.setdefault(x, y) != y:
                        cmap = None
        diffs.append(d)
    return diffs, (next(iter(added)) if len(added) == 1 else None), cmap


def fam(train):
    if not train:
        return
    try:
        if any(not p["input"] or not p["output"] for p in train):
            return
        same = all(len(p["input"]) == len(p["output"]) and len(p["input"][0]) == len(p["output"][0])
                   for p in train)
    except Exception:
        return
    found = []
    cache = {}

    def located(i, key):
        k = (i, key)
        if k not in cache:
            try:
                cache[k] = _locate(train[i]["input"], key)
            except Exception:
                cache[k] = ([], None)
        return cache[k]

    def fits(key, adj, op):
        for i, p in enumerate(train):
            try:
                if _apply(p["input"], key, adj, op, located(i, key)) != p["output"]:
                    return False
            except Exception:
                return False
        return True

    if same:
        diffs, const, cmap = _diff(train)
        if not any(diffs):
            return
        ops = []
        if const is not None:
            ops += [(("paint", s, w, const), 0) for s in ("outline", "fill") for w in ("bg", "all")]
        ops += [(("paint", s, w, col), 1) for col in ("object", "marker") for s in ("outline", "fill")
                for w in ("bg", "all")]
        ops += [(("paint", "around", "bg", col), 2) for col in ([const] if const is not None else [])
                + ["marker", "object"]]
        ops += [(("paint", "cells", "bg", col), 2) for col in ([const] if const is not None else []) + ["marker"]]
        ops += [(("fit", "inplace", mp), 2) for mp in ("int", "vertex")]
        if cmap:
            ops.append((("recolour", cmap), 1))
        if not all(p["input"][r][c] == _bg(p["input"]) for p, d in zip(train, diffs) for r, c in d):
            ops = [o for o in ops if o[0][0] != "paint" or o[0][2] != "bg"]
        for key, kc in _lockeys(train, True):
            for ai, adj in enumerate(ADJUSTS):
                ok = move = True              # move: changes outside the box are only erasures (fit in place)
                for i, p in enumerate(train):
                    boxes, _ = located(i, key)
                    H, W = len(p["input"]), len(p["input"][0])
                    bx = _adjust(boxes, adj, H, W, True, p["input"]) if boxes else None
                    if not bx:
                        ok = move = False
                        break
                    bgi = _bg(p["input"])
                    for r, c in diffs[i]:
                        if not any(b[0] <= r <= b[1] and b[2] <= c <= b[3] for b, _ in bx):
                            ok = False
                            if p["output"][r][c] != bgi or len(bx) != 1:
                                move = False
                                break
                    if not (ok or move):
                        break
                if not (ok or move):
                    continue
                kops = ops if ok else [o for o in ops if o[0][0] == "fit"]
                if ok and const is not None and all(located(i, key)[1] == const for i in range(len(train))):
                    # colour <- marker.colour: the constant is explained by the marker role, so bind it to the role
                    kops = [((o[0], o[1], o[2], "marker"), c) if o[0] == "paint" and o[3] == const else (o, c)
                            for o, c in ops]
                for op, oc in kops:
                    if fits(key, adj, op):
                        found.append((kc + oc + (0 if ai == 0 else 1 + ai / 10.0), key, adj, op,
                                      _make(key, adj, op)))
                        if len(found) >= 3:
                            break
                if len(found) >= 3:
                    break
            if len(found) >= 3:
                break
    else:
        for key, kc in _lockeys(train, False):
            for ai, adj in enumerate(ADJUSTS):
                ok_crop = ok_fit = True
                for i, p in enumerate(train):
                    boxes, _ = located(i, key)
                    H, W = len(p["input"]), len(p["input"][0])
                    bx = _adjust(boxes, adj, H, W, False, p["input"]) if boxes else None
                    if not bx:
                        ok_crop = ok_fit = False
                        break
                    oh, ow = len(p["output"]), len(p["output"][0])
                    hs = [b[1] - b[0] + 1 for b, _ in bx]
                    ws = [b[3] - b[2] + 1 for b, _ in bx]
                    if len(bx) != 1 or (hs[0], ws[0]) != (oh, ow):
                        ok_fit = False
                    if not ((len(set(ws)) == 1 and (sum(hs), ws[0]) == (oh, ow)) or
                            (len(set(hs)) == 1 and (hs[0], sum(ws)) == (oh, ow))):
                        ok_crop = False
                    if not (ok_crop or ok_fit):
                        break
                cands = []
                if ok_crop:
                    cands.append((("crop",), 0))
                if ok_fit:
                    cands += [(("fit", False, False), 1), (("fit", True, False), 2), (("fit", False, True), 2),
                              (("fit", "anchor", False), 2)]
                for op, oc in cands:
                    if fits(key, adj, op):
                        found.append((kc + oc + (0 if ai == 0 else 1 + ai / 10.0), key, adj, op,
                                      _make(key, adj, op)))
                        break
                if len(found) >= 3:
                    break
            if len(found) >= 3:
                break
    found.sort(key=lambda t: t[0])
    for cost, key, adj, op, fn in found:
        opname = op[0] if op[0] != "recolour" else "recolour"
        if op[0] in ("paint",):
            opname = "paint:%s:%s:%s" % op[1:]
        elif op[0] == "fit":
            opname = ("fit:anchor" if op[1] == "anchor" else "fit:inplace:" + op[2] if op[1] == "inplace"
                      else "fit:mirror=%d:nearest=%d" % (op[1], op[2]))
        adjname = adj if isinstance(adj, str) else "%d,%d" % adj
        yield ("rect[%s|adj=%s|%s]" % (":".join(str(x) for x in key), adjname, opname), cost, fn)


FAMILIES = [fam]
