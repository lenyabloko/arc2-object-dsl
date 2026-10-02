"""Concept family: extract_marked_region (test-blind; anti-unified from the member lines and their train pairs).

One generator: segment the grid into pieces, single out ONE piece by a selector (the piece bearing a mark,
the piece whose centre is marked, the largest piece, the piece whose box encloses other content), crop its
box, keep or recolour its ink (own dominant colour / the colour of the rest), then normalise the size
(as is, shrink each constant block to one pixel, or stretch onto the ticks of a neighbouring empty piece).
Members differ only in parameter values:
  3de23699  seg=colour pick=encloser crop=interior ink=nonbg paint=own   scale=none
  5117e062  seg=multi  pick=centred  crop=bbox     ink=piece paint=own   scale=none
  5ad4f10b  seg=mono   pick=largest  crop=bbox     ink=piece paint=other scale=shrink
  b0f4d537  seg=room   pick=marked   crop=bbox     ink=*     paint=keep  scale=stretch
"""
from collections import Counter

CARD = "concept_extract_marked_region"
CONCEPT = "extract_marked_region"
MEMBERS = ["3de23699", "5117e062", "5ad4f10b", "b0f4d537"]
READING = {
    "generator": "Single out one piece of the grid by its mark (most colours, a marked centre, largest, or a box "
                 "enclosing other content), crop its box, keep its cells or repaint its ink with its own or the "
                 "other colour, and normalise the crop: as is, shrunk one pixel per constant block, or stretched "
                 "onto the ticks of the neighbouring background piece.",
    "stop": "The output ends at the selected piece's box (or its interior); shrink stops at the coarsest block "
            "lattice whose blocks are constant, stretch at the neighbouring piece's size with every line on its tick.",
    "params": "seg ∈ {multi, mono, colour, room} · pick ∈ {encloser, centred, marked, largest} · "
              "crop ∈ {bbox, interior} · ink ∈ {piece, nonbg} · paint ∈ {keep, own, other} · "
              "scale ∈ {none, shrink, stretch:edge, stretch:interior}",
    "participants": "Background = most frequent colour (room: most frequent non-wall colour). Pieces: multi = "
                    "8-connected non-background objects; mono = 8-connected one-colour objects; colour = all cells "
                    "of one colour; room = full rectangles left when a wall colour is removed. Own colour = the "
                    "piece's most frequent colour; other colour = the most frequent non-background colour absent "
                    "from the piece; non-ink non-background cells in the box are unknown (background unless a "
                    "shrink block decides them). Stretch target = the largest other piece whose box is mostly "
                    "background; its non-background cells tick rows/columns; pattern lines = rows/columns that "
                    "differ from the most frequent one.",
    "preconditions": "Every training output is smaller than its input; on every training input the selector "
                     "singles out exactly one piece; the rendering reproduces each training output.",
}

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
SEGS = (("multi", 0), ("mono", 0), ("colour", 0), ("room", 1))
PICKS = (("encloser", 0), ("centred", 0), ("marked", 1), ("largest", 1))
CROPS = (("bbox", 0), ("interior", 1))
INKS = (("piece", 0), ("nonbg", 0))
PAINTS = (("keep", 0), ("own", 0), ("other", 1))
SCALES = (("none", 0), ("shrink", 1), ("stretch:edge", 1), ("stretch:interior", 2))


def _mode(vals):
    c = Counter(vals)
    return min(c, key=lambda k: (-c[k], k))


def _comps(g, ok, same, steps):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not ok(g[r][c]):
                continue
            seen.add((r, c))
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in steps:
                    a, b = y + dy, x + dx
                    if (0 <= a < H and 0 <= b < W and (a, b) not in seen and ok(g[a][b])
                            and (not same or g[a][b] == g[y][x])):
                        seen.add((a, b))
                        stack.append((a, b))
            out.append(cells)
    return out


def _piece(g, cells):
    ys = [y for y, _ in cells]
    xs = [x for _, x in cells]
    cnt = Counter(g[y][x] for y, x in cells)
    return {"cells": set(cells), "box": (min(ys), max(ys), min(xs), max(xs)), "cnt": cnt, "dom": _mode(cnt.elements())}


def _pieces(g, seg):
    """(bg, pieces) under segmentation seg."""
    cnt = Counter(v for row in g for v in row)
    bg = _mode(cnt.elements())
    if seg == "multi":
        groups = _comps(g, lambda v: v != bg, False, N8)
    elif seg == "mono":
        groups = _comps(g, lambda v: v != bg, True, N8)
    elif seg == "colour":
        by = {}
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != bg:
                    by.setdefault(v, []).append((r, c))
        groups = [by[k] for k in sorted(by)]
    else:
        for wall in sorted(cnt, key=lambda k: (-cnt[k], k)):
            groups = _comps(g, lambda v: v != wall, False, N4)
            ps = [_piece(g, cs) for cs in groups]
            if len(ps) >= 2 and all((p["box"][1] - p["box"][0] + 1) * (p["box"][3] - p["box"][2] + 1)
                                    == len(p["cells"]) for p in ps):
                return _mode([v for row in g for v in row if v != wall]), ps
        return bg, []
    return bg, [_piece(g, cs) for cs in groups]


def _key(g, bg, p, sel):
    r0, r1, c0, c1 = p["box"]
    if sel == "marked":
        return len(p["cnt"]) if len(p["cnt"]) >= 2 else None
    if sel == "largest":
        return len(p["cells"])
    if sel == "centred":
        mid = {(y, x) for y in {(r0 + r1) // 2, (r0 + r1 + 1) // 2} for x in {(c0 + c1) // 2, (c0 + c1 + 1) // 2}}
        return 1 if any(q in p["cells"] and g[q[0]][q[1]] != p["dom"] for q in mid) else None
    k = sum(1 for y in range(r0 + 1, r1) for x in range(c0 + 1, c1) if g[y][x] != bg and (y, x) not in p["cells"])
    return k or None                                                   # encloser: other content inside its box


def _pick(g, bg, pieces, sel, strict):
    cands = [(k, p) for p in pieces for k in [_key(g, bg, p, sel)] if k is not None]
    if not cands:
        return None
    best = max(k for k, _ in cands)
    tops = [p for k, p in cands if k == best]
    if strict and len(tops) != 1:
        return None
    return min(tops, key=lambda p: (-len(p["cells"]), p["box"]))


def _crop(g, bg, p, crop, ink, paint):
    r0, r1, c0, c1 = p["box"]
    if crop == "interior":
        r0, r1, c0, c1 = r0 + 1, r1 - 1, c0 + 1, c1 - 1
        if r0 > r1 or c0 > c1:
            return None
    if paint == "keep":
        colour = None
    elif paint == "own":
        colour = p["dom"]
    else:
        rest = Counter(v for row in g for v in row if v != bg and v not in p["cnt"])
        if not rest:
            return None
        colour = _mode(rest.elements())
    out = []
    for r in range(r0, r1 + 1):
        row = []
        for c in range(c0, c1 + 1):
            v = g[r][c]
            isink = (r, c) in p["cells"] if ink == "piece" else True
            row.append(bg if v == bg else ((v if colour is None else colour) if isink else None))
        out.append(row)
    return out


def _coarsest(rows):
    """Largest band height k dividing len(rows) whose bands are constant per column (None = unknown)."""
    n = len(rows)
    for k in range(n, 0, -1):
        if n % k == 0 and all(len({rows[y][x] for y in range(b, b + k)} - {None}) <= 1
                              for b in range(0, n, k) for x in range(len(rows[0]))):
            return k
    return 1


def _shrink(C, bg):
    kh, kw = _coarsest(C), _coarsest([list(t) for t in zip(*C)])
    out = []
    for by in range(0, len(C), kh):
        row = []
        for bx in range(0, len(C[0]), kw):
            known = [C[y][x] for y in range(by, by + kh) for x in range(bx, bx + kw) if C[y][x] is not None]
            row.append(known[0] if known else bg)
        out.append(row)
    return out


def _line_idx(vecs, bg):
    cnt = Counter(vecs)
    best = max(cnt.values())
    neutral = min((v for v in vecs if cnt[v] == best), key=lambda v: sum(1 for x in v if x != bg))
    return [i for i, v in enumerate(vecs) if v != neutral]


def _ticks(T, bg, mode):
    H, W = len(T), len(T[0])
    rows, cols = set(), set()
    for r in range(H):
        for c in range(W):
            if T[r][c] == bg:
                continue
            if mode == "edge":
                if c in (0, W - 1):
                    rows.add(r)
                if r in (0, H - 1):
                    cols.add(c)
            elif 0 < r < H - 1 and 0 < c < W - 1:
                rows.add(r)
                cols.add(c)
    return sorted(rows), sorted(cols)


def _spread(src, q):
    if (not src) != (q == 0) or q < len(src):
        return None
    base, rem = divmod(q, len(src)) if src else (0, 0)
    return [s for i, s in enumerate(src) for _ in range(base + (i < rem))]


def _axis_map(n, lines, size, ticks):
    """Monotone surjection output index -> pattern index carrying lines[i] onto ticks[i]; None if impossible."""
    if not ticks:
        plain = [i for i in range(n) if i not in lines]
        if size < n or (not plain and size != n):
            return None
        base, rem = divmod(size - len(lines), len(plain)) if plain else (0, 0)
        grow = {s: base + (j < rem) for j, s in enumerate(plain)}
        return [i for i in range(n) for _ in range(grow.get(i, 1))]
    if len(ticks) != len(lines):
        return None
    out, pl, pt = [], -1, -1
    for l, t in list(zip(lines, ticks)) + [(n, size)]:
        seg = _spread(list(range(pl + 1, l)), t - pt - 1)
        if seg is None:
            return None
        out += seg + ([l] if l < n else [])
        pl, pt = l, t
    return out if len(out) == size else None


def _stretch(g, bg, P, pieces, p, mode):
    targets = []
    for q in pieces:
        r0, r1, c0, c1 = q["box"]
        T = [list(g[r][c0:c1 + 1]) for r in range(r0, r1 + 1)]
        if q is not p and _mode([v for row in T for v in row]) == bg:
            targets.append((-(r1 - r0 + 1) * (c1 - c0 + 1), r0, c0, T))
    for _, _, _, T in sorted(targets, key=lambda t: t[:3]):
        trows, tcols = _ticks(T, bg, mode)
        rmap = _axis_map(len(P), _line_idx([tuple(r) for r in P], bg), len(T), trows)
        cmap = _axis_map(len(P[0]), _line_idx([tuple(c) for c in zip(*P)], bg), len(T[0]), tcols)
        if rmap is not None and cmap is not None:
            return [[P[i][j] for j in cmap] for i in rmap]
    return None


def _render(g, bg, pieces, p, crop, ink, paint, scale):
    C = _crop(g, bg, p, crop, ink, paint)
    if C is None:
        return None
    if scale == "shrink":
        return _shrink(C, bg)
    C = [[bg if v is None else v for v in row] for row in C]
    return C if scale == "none" else _stretch(g, bg, C, pieces, p, scale.split(":")[1])


def _program(seg, pick, crop, ink, paint, scale):
    def fn(g):
        bg, pieces = _pieces(g, seg)
        p = _pick(g, bg, pieces, pick, False)
        if p is None:
            return None
        return _render(g, bg, pieces, p, crop, ink, paint, scale)
    return fn


def fam(train):
    if not train or any(not p["input"] or not p["output"] or not p["output"][0] for p in train):
        return
    if any(len(p["output"]) * len(p["output"][0]) >= len(p["input"]) * len(p["input"][0]) for p in train):
        return                                                         # extraction: output smaller than input
    found = []
    for seg, ks in SEGS:
        segd = [_pieces(p["input"], seg) for p in train]
        if any(not ps for _, ps in segd):
            continue
        for pick, kp in PICKS:
            sel = [_pick(p["input"], bg, ps, pick, True) for p, (bg, ps) in zip(train, segd)]
            if any(s is None for s in sel):
                continue
            for crop, kc in CROPS:
                for ink, ki in INKS:
                    for paint, ka in PAINTS:
                        for scale, kz in SCALES:
                            if all(_render(p["input"], bg, ps, s, crop, ink, paint, scale) == p["output"]
                                   for p, (bg, ps), s in zip(train, segd, sel)):
                                found.append((ks + kp + kc + ki + ka + kz, seg, pick, crop, ink, paint, scale))
    found.sort(key=lambda t: t[0])
    for cost, seg, pick, crop, ink, paint, scale in found:
        yield ("extract_marked_region[seg=%s,pick=%s,crop=%s,ink=%s,paint=%s,scale=%s]"
               % (seg, pick, crop, ink, paint, scale), cost, _program(seg, pick, crop, ink, paint, scale))


FAMILIES = [fam]
