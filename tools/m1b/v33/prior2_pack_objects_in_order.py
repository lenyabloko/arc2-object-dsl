"""Prior family: PACK_OBJECTS_IN_ORDER -- extract items, sort them by a key, pack them contiguously.

One generator, ARRANGE(items; key; layout; gap; mirror; canvas):
  items    segmentation of the non-background cells into objects (same-colour 4/8-connected, multicolour
           4/8/reach-2 groups, one object per colour, multicolour blobs cut into congruent modal-size tiles)
           or "bracket strips" (the cells strictly between an opening k x k marker square of colour a and the
           next / farthest closing k x k square of colour b on the same k rows; optionally read in the
           transposed frame).  Optional filter: singletons are markers, not items.  Optional item style:
           recolour by the nearest marker | redraw as a solid square of the item's cell count.
  key      reading order (r0,c0) | column order (c0,r0) | order along the layout axis | size asc/desc | colour;
           bins group by colour or topological genus (holes); grid slots come from the items' own position
           (row/column rank) or are self-indicated (sign of the centroid of the minority-colour cells).
  layout   line (row | column | the axis along which the items are spread; cross alignment start/centre/end;
           gap g) | diagonal chain (each next item starts at the previous one's far corner, overlap -1 or
           touching 0; later or earlier on top) | per-key bins (columns of stacks, gaps between stack items
           and between bins) | slot grid (side x side cells of the largest item size, gap g).
  mirror   placements (not contents) may be mirrored vertically / horizontally inside the packed block.
  canvas   crop to the packed block | input-sized background canvas, block anchored at the mirrored corner |
           in place (grid only: items permuted into the original items' slot positions).
Background = per-grid most common colour or the uniform border colour.  Nothing task specific is stored.
"""
from collections import Counter

CARD = "prior_pack_objects_in_order"
CONCEPT = "pack_objects_in_order"
MEMBERS = ["03560426", "1990f7a8", "291dc1e1", "2ba387bc", "4acc7107", "4e45f183", "505fff84", "50aad11f",
           "652646ff", "8abad3cf", "a8c38be5", "aab50785", "d749d46f", "db615bd4"]
READING = {
    "generator": "Extract items (objects, per-colour blobs, congruent tiles or marker-bracketed strips), order "
                 "them by a key (reading/column order, size, colour, genus bins, own-position or "
                 "self-indicated slot) and lay them out contiguously as a row/column, a diagonal chain, "
                 "per-key column stacks or a slot grid with gap g, on a cropped, input-sized or in-place canvas.",
    "stop": "every item is placed exactly once; the canvas is the packed block (crop), the input frame with the "
            "block anchored at the mirrored corner, or the input with items permuted among their own slots",
    "params": "bg in {mode, border} . seg in {c4, c8, m4, m8, m2, colour, cut, bracket(k in 1..3, a, b, "
              "close in {near, far}, frame in {id, T})} . filter in {all, non-singleton} . style in {keep, "
              "nearest-marker colour, area square} . layout in {line(axis in {h, v, spread}, align in {0,1,2}), "
              "chain(g in {-1,0}, top in {later, earlier}), bins(key in {colour, genus}, order in {asc, desc, "
              "first}, within in {rc, cr}, gaps 0..2), grid(slot in {pos, self})} . key in {rc, cr, axis, size+, "
              "size-, colour} . gap in {0,1,2} . mirror in {0,1}^2 . canvas in {crop, input, inplace}",
    "participants": "background = per-grid mode or uniform border colour; items per seg (singletons are markers "
                    "under the non-singleton filter); marker colours a,b range over colours present in every "
                    "training input",
    "preconditions": "every training input yields 1..40 items; outputs either all keep the input shape "
                     "(input/inplace canvas, at least one pair changes) or are cropped packed blocks; non-bg "
                     "cell count of the output equals the items' cell count unless the chain overlaps",
}

MAX_ITEMS = 40
MAX_YIELD = 3


# ------------------------------------------------------------------------------------------------ helpers
def _mode(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _bg(g, how):
    if how == "mode":
        return _mode(g)
    ring = set(g[0]) | set(g[-1]) | {r[0] for r in g} | {r[-1] for r in g}
    if len(ring) != 1:
        raise ValueError("no uniform border")
    return ring.pop()


def _tr(g):
    return [list(r) for r in zip(*g)]


def _isqrt(n):
    s = int(n ** 0.5)
    while s * s > n:
        s -= 1
    while (s + 1) * (s + 1) <= n:
        s += 1
    return s


def _comps(g, bg, same, reach):
    """reach 0 = 4-connected, 1 = 8-connected, 2 = Chebyshev distance <= 2."""
    H, W = len(g), len(g[0])
    if reach == 0:
        nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    else:
        nb = tuple((a, b) for a in range(-reach, reach + 1) for b in range(-reach, reach + 1) if a or b)
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            st, cells = [(r, c)], []
            seen[r][c] = True
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg \
                            and (not same or g[ny][nx] == col):
                        seen[ny][nx] = True
                        st.append((ny, nx))
            out.append(cells)
    return out


def _item(g, cells):
    r0 = min(a for a, _ in cells)
    c0 = min(b for _, b in cells)
    r1 = max(a for a, _ in cells)
    c1 = max(b for _, b in cells)
    rel = sorted((a - r0, b - c0, g[a][b]) for a, b in cells)
    return {"r0": r0, "c0": c0, "h": r1 - r0 + 1, "w": c1 - c0 + 1, "cells": rel, "n": len(rel)}


def _col(it):
    """The item's dominant colour (computed lazily)."""
    if "col" not in it:
        cnt = Counter(v for _, _, v in it["cells"])
        it["col"] = max(sorted(cnt), key=lambda k: cnt[k])
    return it["col"]


def _rect_item(g, r0, r1, c0, c1):
    return _item(g, [(a, b) for a in range(r0, r1 + 1) for b in range(c0, c1 + 1)])


def _genus(it):
    if "genus" in it:
        return it["genus"]
    h, w = it["h"] + 2, it["w"] + 2
    body = {(a + 1, b + 1) for a, b, _ in it["cells"]}
    seen, regions = set(), 0
    for r in range(h):
        for c in range(w):
            if (r, c) in body or (r, c) in seen:
                continue
            regions += 1
            st = [(r, c)]
            seen.add((r, c))
            while st:
                y, x = st.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (y + dy, x + dx)
                    if 0 <= q[0] < h and 0 <= q[1] < w and q not in body and q not in seen:
                        seen.add(q)
                        st.append(q)
    it["genus"] = regions - 1
    return regions - 1


# ------------------------------------------------------------------------------------------------ items
def _cut(g, comps):
    """Cut multicolour blobs into congruent tiles of the modal bounding-box size (greedy, row-major)."""
    sizes = Counter()
    for cells in comps:
        sizes[(max(a for a, _ in cells) - min(a for a, _ in cells) + 1,
               max(b for _, b in cells) - min(b for _, b in cells) + 1)] += 1
    ph, pw = max(sorted(sizes), key=lambda k: sizes[k])
    out = []
    for cells in comps:
        left = set(cells)
        while left:
            a, b = min(left)
            block = [(a + i, b + j) for i in range(ph) for j in range(pw)]
            if any(x not in left for x in block):
                raise ValueError("blob does not cut into modal tiles")
            left.difference_update(block)
            out.append(_rect_item(g, a, a + ph - 1, b, b + pw - 1))
    return out


def _squares(g, k):
    """For every row r: {colour: [c, ...]} of the uniform k x k squares whose top-left corner is (r, c)."""
    H, W = len(g), len(g[0])
    out = []
    for r in range(H - k + 1):
        d = {}
        for c in range(W - k + 1):
            v = g[r][c]
            if all(g[r + i][c + j] == v for i in range(k) for j in range(k)):
                d.setdefault(v, []).append(c)
        out.append(d)
    return out


def _spans(g, k, a, b, close, sqs=None):
    """Strips strictly between an opening k x k square of colour a and a closing k x k square of colour b,
    as (r0, r1, c0, c1) rectangles."""
    if sqs is None:
        sqs = _squares(g, k)
    out = []
    r = 0
    while r < len(sqs):
        opens = sqs[r].get(a)
        done = False
        if opens:
            c0 = opens[0]
            closes = [c for c in sqs[r].get(b, ()) if c >= c0 + k]
            if closes:
                c1 = closes[0] if close == "near" else closes[-1]
                if c1 > c0 + k:
                    out.append((r, r + k - 1, c0 + k, c1 - 1))
                    done = True
        r += k if done else 1
    return out


def _items(g, cfg, spans=None):
    """cfg = (bgmode, seg, filt, style) or ("bracket", k, a, b, close).  Returns (bg, items)."""
    if cfg[0] == "bracket":
        if spans is None:
            spans = _spans(g, *cfg[1:])
        return _mode(g), [_rect_item(g, *sp) for sp in spans]
    bgm, seg, filt, style = cfg
    bg = _bg(g, bgm)
    if seg == "colour":
        pos = {}
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != bg:
                    pos.setdefault(v, []).append((r, c))
        comps = [pos[v] for v in sorted(pos)]
    else:
        same, reach = {"c4": (True, 0), "c8": (True, 1), "m4": (False, 0), "m8": (False, 1),
                       "m2": (False, 2), "cut": (False, 0)}[seg]
        comps = _comps(g, bg, same, reach)
    if not comps or len(comps) > 4 * MAX_ITEMS:
        raise ValueError("no participants")
    markers = []
    if filt == "big":
        markers = [c[0] for c in comps if len(c) == 1]
        comps = [c for c in comps if len(c) > 1]
    items = _cut(g, comps) if seg == "cut" else [_item(g, c) for c in comps]
    if style == "mark":
        if not markers:
            raise ValueError("no markers")
        for it in items:
            best, cols = None, set()
            for (mr, mc) in markers:
                d = min(max(abs(mr - it["r0"] - a), abs(mc - it["c0"] - b)) for a, b, _ in it["cells"])
                if best is None or d < best:
                    best, cols = d, {g[mr][mc]}
                elif d == best:
                    cols.add(g[mr][mc])
            if len(cols) != 1:
                raise ValueError("ambiguous marker")
            v = cols.pop()
            it["cells"] = [(a, b, v) for a, b, _ in it["cells"]]
            it["col"] = v
    elif style == "square":
        for it in items:
            s = _isqrt(it["n"])
            if s * s != it["n"]:
                raise ValueError("area is not a square")
            it["cells"] = [(a, b, _col(it)) for a in range(s) for b in range(s)]
            it["h"] = it["w"] = s
    return bg, items


# ------------------------------------------------------------------------------------------------ layouts
def _order(items, key, horiz=None):
    if key == "rc" or (key == "axis" and not horiz):
        return sorted(items, key=lambda o: (o["r0"], o["c0"]))
    if key == "cr" or key == "axis":
        return sorted(items, key=lambda o: (o["c0"], o["r0"]))
    if key == "size+":
        return sorted(items, key=lambda o: (o["n"], o["r0"], o["c0"]))
    if key == "size-":
        return sorted(items, key=lambda o: (-o["n"], o["r0"], o["c0"]))
    return sorted(items, key=lambda o: (_col(o), o["r0"], o["c0"]))


def _disjoint(items, horiz):
    lo, ln = ("c0", "w") if horiz else ("r0", "h")
    s = sorted(items, key=lambda o: o[lo])
    return all(s[i][lo] + s[i][ln] <= s[i + 1][lo] for i in range(len(s) - 1))


def _pos_slots(items):
    n = len(items)
    side = _isqrt(n)
    if side * side != n:
        raise ValueError("not a square number of items")
    s = sorted(items, key=lambda o: (2 * o["r0"] + o["h"], 2 * o["c0"] + o["w"]))
    slots = []
    for i in range(side):
        row = sorted(s[i * side:(i + 1) * side], key=lambda o: 2 * o["c0"] + o["w"])
        for j, o in enumerate(row):
            slots.append((o, i, j))
    return side, slots


def _self_slots(items):
    cnt = Counter(v for it in items for _, _, v in it["cells"])
    filler = max(sorted(cnt), key=lambda k: cnt[k])
    slots, used = [], set()
    for it in items:
        mk = [(a, b) for a, b, v in it["cells"] if v != filler]
        m = len(mk)
        if m:
            sr, sc = 2 * sum(a for a, _ in mk), 2 * sum(b for _, b in mk)
            i = 0 if sr < m * (it["h"] - 1) else (1 if sr == m * (it["h"] - 1) else 2)
            j = 0 if sc < m * (it["w"] - 1) else (1 if sc == m * (it["w"] - 1) else 2)
        else:
            i = j = 1
        if (i, j) in used:
            raise ValueError("slot clash")
        used.add((i, j))
        slots.append((it, i, j))
    return 3, slots


def _place(items, lay):
    """Returns (Hp, Wp, [(item, y, x)]) in drawing order, canonical (unmirrored)."""
    kind = lay[0]
    if kind == "line":
        _, axis, key, align, gap = lay
        if axis == "spread":
            if _disjoint(items, True):
                horiz = True
            elif _disjoint(items, False):
                horiz = False
            else:
                raise ValueError("items not spread along an axis")
        else:
            horiz = axis == "h"
        seq = _order(items, key, horiz)
        cross = max((o["h"] if horiz else o["w"]) for o in seq)
        pl, t = [], 0
        for o in seq:
            ln, cw = (o["w"], o["h"]) if horiz else (o["h"], o["w"])
            off = (0, (cross - cw) // 2, cross - cw)[align]
            pl.append((o, off, t) if horiz else (o, t, off))
            t += ln + gap
        t -= gap
        return (cross, t, pl) if horiz else (t, cross, pl)
    if kind == "chain":
        _, key, gap, top = lay
        seq = _order(items, key)
        pl, y, x = [], 0, 0
        for o in seq:
            pl.append((o, y, x))
            y += o["h"] + gap
            x += o["w"] + gap
        Hp = max(y0 + o["h"] for o, y0, _ in pl)
        Wp = max(x0 + o["w"] for o, _, x0 in pl)
        return Hp, Wp, (pl if top == "later" else pl[::-1])
    if kind == "bins":
        _, bkey, border, within, gs, gb = lay
        seq = _order(items, within)
        val = _col if bkey == "colour" else _genus
        groups, first = {}, []
        for o in seq:
            v = val(o)
            if v not in groups:
                groups[v] = []
                first.append(v)
            groups[v].append(o)
        keys = first if border == "first" else sorted(groups, reverse=(border == "desc"))
        pl, x, Hp = [], 0, 0
        for v in keys:
            y = 0
            for o in groups[v]:
                pl.append((o, y, x))
                y += o["h"] + gs
            Hp = max(Hp, y - gs)
            x += max(o["w"] for o in groups[v]) + gb
        return Hp, x - gb, pl
    # grid
    _, slot, gap = lay
    side, slots = _pos_slots(items) if slot == "pos" else _self_slots(items)
    ch = max(o["h"] for o in items)
    cw = max(o["w"] for o in items)
    pl = [(o, i * (ch + gap), j * (cw + gap)) for o, i, j in slots]
    return side * ch + (side - 1) * gap, side * cw + (side - 1) * gap, pl


def _inplace(g, bg, items, lay):
    side, slots = (_self_slots(items) if lay[1] == "self" else _pos_slots(items))
    side2, home = _pos_slots(items)
    if side != side2:
        raise ValueError("slot grid mismatch")
    at = {(i, j): (o["r0"], o["c0"]) for o, i, j in home}
    out = [list(r) for r in g]
    for o in items:
        for a, b, _ in o["cells"]:
            out[o["r0"] + a][o["c0"] + b] = bg
    H, W = len(g), len(g[0])
    for o, i, j in slots:
        y, x = at[(i, j)]
        for a, b, v in o["cells"]:
            if 0 <= y + a < H and 0 <= x + b < W:
                out[y + a][x + b] = v
    return out


def _paint(g, bg, placed, mirror, canvas):
    Hp, Wp, pl = placed
    mr, mc = mirror
    if canvas == "crop":
        H, W, oy, ox = Hp, Wp, 0, 0
    else:
        H, W = len(g), len(g[0])
        oy = H - Hp if mr else 0
        ox = W - Wp if mc else 0
    out = [[bg] * W for _ in range(H)]
    for o, y, x in pl:
        if mr:
            y = Hp - y - o["h"]
        if mc:
            x = Wp - x - o["w"]
        y += oy
        x += ox
        for a, b, v in o["cells"]:
            if 0 <= y + a < H and 0 <= x + b < W:
                out[y + a][x + b] = v
    return out


def _render(g, bg, items, lay, mirror, canvas):
    if canvas == "inplace":
        return _inplace(g, bg, items, lay)
    return _paint(g, bg, _place(items, lay), mirror, canvas)


def _layouts(exact):
    """Yields (cost, lay) in preference order; only chain overlap can lose cells (exact=False)."""
    keys = ("rc", "cr", "axis", "size+", "size-", "colour")
    if exact:
        for gap in (0, 1, 2):
            for axis in ("v", "h", "spread"):
                for key in keys:
                    for align in (0, 1, 2):
                        yield 1 + gap + (axis == "spread") + (align > 0), ("line", axis, key, align, gap)
        for slot in ("pos", "self"):
            for gap in (0, 1):
                yield 2 + gap, ("grid", slot, gap)
        for bkey in ("colour", "genus"):
            for border in ("asc", "desc", "first"):
                for within in ("rc", "cr"):
                    for gs in (0, 1, 2):
                        for gb in (0, 1, 2):
                            yield 3 + gs + gb, ("bins", bkey, border, within, gs, gb)
    for gap in ((0, -1) if exact else (-1,)):
        for key in keys:
            for top in ("later", "earlier"):
                yield 2 + (top != "later"), ("chain", key, gap, top)


def _seg_configs(colours):
    for bgm in ("mode", "border"):
        for seg in ("c4", "c8", "m4", "m8", "m2", "colour", "cut"):
            for filt in ("all", "big"):
                for style in ("keep", "mark", "square"):
                    if style == "mark" and filt != "big":
                        continue
                    if style == "square" and seg not in ("c4", "c8", "colour"):
                        continue
                    yield (bgm == "border") + (filt == "big") + (style != "keep") + (seg == "cut"), \
                        (bgm, seg, filt, style)
    for k in (1, 2, 3):
        for a in colours:
            for b in colours:
                for close in ("near", "far"):
                    yield 2 + (close == "far") + (a != b), ("bracket", k, a, b, close)


def _make(frame, cfg, lay, mirror, canvas):
    def fn(g):
        h = _tr(g) if frame == "T" else [list(r) for r in g]
        bg, items = _items(h, cfg)
        if not items or len(items) > MAX_ITEMS:
            raise ValueError("bad item count")
        out = _render(h, bg, items, lay, mirror, canvas)
        return _tr(out) if frame == "T" else out
    return fn


def _sig(items):
    return tuple((o["r0"], o["c0"], tuple(o["cells"])) for o in items)


# ------------------------------------------------------------------------------------------------ family
def fam(train):
    try:
        pairs = [(p["input"], p["output"]) for p in train]
        if not pairs or any(not I or not I[0] or not O or not O[0] for I, O in pairs):
            return
    except Exception:
        return
    same = all(len(I) == len(O) and len(I[0]) == len(O[0]) for I, O in pairs)
    if same and all(I == O for I, O in pairs):
        return
    canvases = ("input", "inplace") if same else ("crop",)
    common = None
    for I, _ in pairs:
        cs = {v for r in I for v in r}
        common = cs if common is None else common & cs
    colours = sorted(common)
    fits = []
    for frame in ("id", "T"):
        fp = [(_tr(I), _tr(O)) if frame == "T" else (I, O) for I, O in pairs]
        seen = set()
        sqc = {}
        for ccost, cfg in _seg_configs(colours):
            if frame == "T" and cfg[0] != "bracket":
                continue
            try:
                if cfg[0] == "bracket":
                    k, a, b = cfg[1], cfg[2], cfg[3]
                    if k not in sqc:
                        sqc[k] = [_squares(I, k) for I, _ in fp]
                        sqc[k, "c"] = [{v for d in sq for v in d} for sq in sqc[k]]
                    if any(a not in cs or b not in cs for cs in sqc[k, "c"]):
                        continue
                    sps = []
                    for (I, _), sq in zip(fp, sqc[k]):
                        sp = _spans(I, k, a, b, cfg[4], sq)
                        if not sp or len(sp) > MAX_ITEMS:
                            break
                        sps.append(sp)
                    if len(sps) != len(fp):
                        continue
                    ext = [_items(I, cfg, sp) for (I, _), sp in zip(fp, sps)]
                else:
                    ext = [_items(I, cfg) for I, _ in fp]
            except Exception:
                continue
            if any(not it or len(it) > MAX_ITEMS for _, it in ext):
                continue
            sig = tuple((bg, _sig(it)) for bg, it in ext)
            if sig in seen:
                continue
            seen.add(sig)
            # cell-count / colour preconditions (per pair) for the packing canvases
            exact = True
            ok = True
            for (bg, it), (I, O) in zip(ext, fp):
                n_items = sum(1 for o in it for _, _, v in o["cells"] if v != bg)
                n_out = sum(1 for r in O for v in r if v != bg)
                cols_items = {v for o in it for _, _, v in o["cells"]}
                if not {v for r in O for v in r if v != bg} <= cols_items:
                    ok = False
                    break
                if n_out > n_items:
                    ok = False
                    break
                if n_out != n_items:
                    exact = False
            tight = all(v != bg for bg, it in ext for o in it for _, _, v in o["cells"])
            boxes = []
            for (bg, it), (I, O) in zip(ext, fp):
                rows = [r for r, row in enumerate(O) if any(v != bg for v in row)]
                cols = [c for c in range(len(O[0])) if any(row[c] != bg for row in O)]
                boxes.append((rows[0], rows[-1], cols[0], cols[-1]) if rows else None)
            for canvas in canvases:
                if canvas == "inplace":
                    for slot in ("pos", "self"):
                        lay = ("grid", slot, 0)
                        try:
                            good = all(_inplace(I, bg, it, lay) == O for (bg, it), (I, O) in zip(ext, fp))
                        except Exception:
                            good = False
                        if good:
                            fits.append((ccost + 3 + (frame == "T"), len(fits), frame, cfg, lay, (0, 0), canvas))
                    continue
                if not ok:
                    continue
                for lcost, lay in _layouts(exact):
                    placed = []
                    for (bg, it), (I, O), bb in zip(ext, fp, boxes):
                        try:
                            P = _place(it, lay)
                        except Exception:
                            break
                        Hp, Wp = P[0], P[1]
                        if canvas == "crop":
                            if (Hp, Wp) != (len(O), len(O[0])):
                                break
                        elif tight and lay[0] != "grid" and Hp <= len(O) and Wp <= len(O[0]) and \
                                (bb is None or (Hp, Wp) != (bb[1] - bb[0] + 1, bb[3] - bb[2] + 1)):
                            break
                        placed.append(P)
                    if len(placed) != len(fp):
                        continue
                    for mirror in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        if canvas == "input" and tight and lay[0] != "grid":
                            if any(bb is None or (bb[0] != 0 if not mirror[0] else bb[1] != len(O) - 1) or
                                   (bb[2] != 0 if not mirror[1] else bb[3] != len(O[0]) - 1)
                                   for bb, (I, O) in zip(boxes, fp)):
                                continue
                        if all(_paint(I, bg, P, mirror, canvas) == O
                               for P, (bg, it), (I, O) in zip(placed, ext, fp)):
                            cost = ccost + lcost + sum(mirror) + (frame == "T")
                            fits.append((cost, len(fits), frame, cfg, lay, mirror, canvas))
                            break
                    if len(fits) >= 12:
                        break
            if len(fits) >= 12:
                break
        if len(fits) >= 12:
            break
    fits.sort(key=lambda t: (t[0], t[1]))
    for cost, _, frame, cfg, lay, mirror, canvas in fits[:MAX_YIELD]:
        name = "pack[%s|%s|%s|m%d%d|%s]" % (frame, ",".join(map(str, cfg)), ",".join(map(str, lay)),
                                           mirror[0], mirror[1], canvas)
        yield name, cost, _make(frame, cfg, lay, mirror, canvas)


FAMILIES = [fam]
