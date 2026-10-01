"""Prior family: RECTANGLE_FROM_DELIMITERS -- locate rectangles implied by delimiters, then apply one operation.

One generator, LOCATE-RECT(locator; adjust) -> OP(op params):
  locator   bbox(m, group)   bounding box of the cells of marker colour m, one box per group of markers
                             (group in all | rook (linked by sharing a row/column) | c8 component | near2 cluster
                             (Chebyshev gap <= 2)); m = background means the whole canvas
            corners          the colour with exactly four cells at the corners of a rectangle (crop marks)
            frame            the largest single-colour hollow ring (one cell thick, non-empty interior), else four
                             uniform straight bars on the four sides of a rectangle (corners free)
            between(a,b,ax)  start/end marker pairs: two equal-shaped solid objects of colours a and b on the
                             same rows (ax=0) or columns (ax=1); the rectangle is the strip strictly between them
            lattice          ruling lines of one colour; the crossings that break the line colour span the box
  adjust    inset/outset (dr, dc) applied to every box (positive = inset, negative = outset)
  op        paint(style, which, colour)  style in outline | fill | around (fill except the bounding box of
                                         the enclosed non-background cells); which cells: background only | every cell
                                         except the delimiters; colour: constant (the single colour added in
                                         training) | the marker colour | the dominant other object colour
            recolour                     an induced colour map applied to the cells inside the boxes
            crop                         cut the box out; several boxes are stacked in reading order
            fit(mirror)                  crop the box and redraw the loose shape (every non-background cell not on
                                         the box outline) in its interior, scaled by integer factors to fill it,
                                         optionally mirrored so its colours best agree with the adjacent outline,
                                         or recoloured cell-wise by the uniquely nearest outline side
Everything colour/size/position related is read from the grid or induced from the training pairs.
"""
from collections import Counter

CARD = "prior_rectangle_from_delimiters"
CONCEPT = "rectangle_from_delimiters"
MEMBERS = ["1c02dbbe", "20a9e565", "256b0a75", "32597951", "36fdfd69", "3f7978a0", "465b7d93", "505fff84",
           "692cd3b6", "6b9890af", "6f8cd79b", "846bdb03", "8a004b2b", "928ad970", "9385bd28", "97239e3d",
           "9aec4887", "a644e277", "aab50785", "af902bf9", "d37a1ef5", "db615bd4", "e4075551", "e7639916",
           "e7a25a18"]
READING = {
    "generator": "Find the rectangles implied by delimiters (bounding box of a marker-colour group, four corner "
                 "crop marks, a hollow frame or four side bars, the strip between start/end marker pairs, or the broken crossings "
                 "of a lattice), inset/outset them, then draw their outline, fill or recolour their inside, crop "
                 "them out (stacking several), or crop one and fit the loose shape into its interior by integer "
                 "scaling and optional mirroring.",
    "stop": "single pass: every located rectangle is processed once; a fitted shape fills the interior exactly",
    "params": "locator in {bbox(m, group in {all, rook, c8, near2}), corners, frame, between(a, b, axis in {0,1}), "
              "lattice} . adjust (dr, dc) in {(0,0),(1,1),(-1,-1),(2,2),(+-1,0),(0,+-1)} . "
              "op in {paint(style in {outline, fill, around}, which in {bg, all-but-delimiters}, colour in "
              "{const, marker, object}), recolour(induced map), crop(stack), fit(mirror in {no, best}, "
              "recolour in {keep, nearest side})}",
    "participants": "background = per-grid most common colour; markers = cells of an anchor colour present in "
                    "every training input (or the corner/frame/bracket objects); loose shape = non-background "
                    "cells off the rectangle outline",
    "preconditions": "same-shape pairs -> paint/recolour ops, the changed cells must lie inside the located boxes; "
                     "shape-changing pairs -> crop/fit ops, the box size (or stacked size) must equal the output size",
}

ADJUSTS = ((0, 0), (1, 1), (-1, -1), (2, 2), (-1, 0), (0, -1), (1, 0), (0, 1))
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
def _loc_bbox(g, m, group):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == m]
    if not cells:
        return [], m
    if group == "all":
        groups = [cells]
    elif group == "rook":
        groups = _rook(cells)
    elif group == "c8":
        groups = _comps(cells, _N8)
    else:
        groups = _comps(cells, _NEAR2)
    groups.sort(key=lambda gr: (_bbox(gr)[0], _bbox(gr)[2]))
    return [(_bbox(gr), set(gr)) for gr in groups], m


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


def _adjust(boxes, adj, H, W, clip):
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
    if colour == "marker":
        colour = m
    elif colour == "object":
        colour = _object_colour(g, bg, m)
    if colour is None and cmap is None:
        return None
    out = [row[:] for row in g]
    for (r0, r1, c0, c1), delim in boxes:
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


def _apply(g, lockey, adj, op, located=None):
    boxes, m = _locate(g, lockey) if located is None else located
    if not boxes:
        return None
    H, W = len(g), len(g[0])
    boxes = _adjust(boxes, adj, H, W, op[0] in ("paint", "recolour"))
    if not boxes:
        return None
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
    keys = []
    for m in order:
        for group in ("all", "rook", "c8", "near2"):
            keys.append((("bbox", m, group), 0 if m not in bgs else 2))
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
        if cmap:
            ops.append((("recolour", cmap), 1))
        if not all(p["input"][r][c] == _bg(p["input"]) for p, d in zip(train, diffs) for r, c in d):
            ops = [o for o in ops if o[0][0] != "paint" or o[0][2] != "bg"]
        for key, kc in _lockeys(train, True):
            for ai, adj in enumerate(ADJUSTS):
                ok = True
                for i, p in enumerate(train):
                    boxes, _ = located(i, key)
                    H, W = len(p["input"]), len(p["input"][0])
                    bx = _adjust(boxes, adj, H, W, True) if boxes else None
                    if not bx:
                        ok = False
                        break
                    for r, c in diffs[i]:
                        if not any(b[0] <= r <= b[1] and b[2] <= c <= b[3] for b, _ in bx):
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    continue
                for op, oc in ops:
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
                    bx = _adjust(boxes, adj, H, W, False) if boxes else None
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
                    cands += [(("fit", False, False), 1), (("fit", True, False), 2), (("fit", False, True), 2)]
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
            opname = "fit:mirror=%d:nearest=%d" % (op[1], op[2])
        yield ("rect[%s|adj=%d,%d|%s]" % (":".join(str(x) for x in key), adj[0], adj[1], opname), cost, fn)


FAMILIES = [fam]
