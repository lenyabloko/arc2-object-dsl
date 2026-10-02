"""Prior family: PACK_OBJECTS_IN_ORDER -- extract items, sort them by a key, pack them contiguously.

One generator, ARRANGE(items; key; layout; gap; mirror; canvas):
  items    segmentation of the non-background cells into objects (same-colour 4/8-connected or reach-2,
           multicolour 4/8/reach-2 groups, one object per colour, multicolour blobs cut into congruent modal-size
           tiles) or "bracket strips" (the cells strictly between an opening k x k marker square of colour a and
           the next / farthest closing k x k square of colour b on the same k rows; optionally read in the
           transposed frame).  Background = per-grid mode | uniform border colour | mode plus the texture colour
           (second most common).  Optional filter: singletons are markers, not items.  Optional item style:
           recolour by the nearest marker | solid square of the item's cell count | solid block of the item's own
           bounding box | completion to the template shape shared by all training output items.
  key      reading order | column order | order along the layout axis | size asc/desc | colour | occlusion depth
           (completed items only); bins by colour or genus; grid slots from own position or self-indicated.
  layout   line (row | column | spread axis; cross alignment start/centre/end; gap g) | diagonal chain | per-key
           bins | slot grid.
  mirror   placements may be mirrored vertically / horizontally inside the packed block.
  canvas   crop | input-sized canvas anchored at the mirrored corner | in place (slot permutation) | container
           interior (the item with the largest box becomes a solid outline, its interior is cleared, the other
           items are removed and packed centred inside it).
Nothing task specific is stored; the template shape is induced from the training outputs.

BINDINGS (G68) -- every value induced for the members the family fits, with the role that explains it
(value seen in training  <-  role it is bound to; "literal" = no role explains it, kept as a fitted constant).
  03560426  bg 0 <- per-grid mode;  items <- same-colour 4-objects;  order <- column order (left to right)
            layout <- diagonal chain: next item starts on the previous one's far corner, overlap -1 <- literal,
            later on top <- literal;  canvas <- input frame, block anchored at the top-left corner
  1990f7a8  items <- same-colour 8-objects;  slot <- each object's own position rank;  side 2 <- sqrt(item count)
            cell size <- largest item box;  gap 1 <- literal;  canvas <- crop
  2ba387bc  items <- 4-objects;  bin <- topological genus (hollow before solid);  within <- reading order;
            column width <- widest item in its bin;  gaps 0 <- literal;  canvas <- crop
  4acc7107  items <- 4-objects;  bin <- object colour, bins in first-seen column order;  within <- column order
            stack gap 1, bin gap 1 <- literal;  anchor corner bottom-left (mirror rows) <- literal;  canvas <- input
  4e45f183  bg <- uniform border colour (mode is the panel fill);  items <- multicolour 4-blobs (panels)
            slot <- self-indicated (sign of the minority-colour centroid);  canvas <- in place
  505fff84  items <- strips between opening marker a and closing marker b (k=1 <- literal, nearest close)
            a=1, b=8 <- the colours that vanish (in every input, in no output);  order <- reading order
            layout <- column, gap 0;  canvas <- crop
  50aad11f  items <- non-singleton 4-objects;  colour <- nearest singleton marker's colour
            axis <- the axis the items are spread along;  order <- along that axis;  gap 0;  canvas <- crop
  8abad3cf  items <- one per colour;  square side <- sqrt(item cell count);  order <- size ascending
            layout <- row, gap 1 <- literal, bottom-aligned (mirror rows) <- literal;  canvas <- crop
  a8c38be5  items <- multicolour blobs cut into tiles of the modal box size;  slot <- self-indicated;  side 3;
            gap 0;  canvas <- crop
  aab50785  items <- strips between 2x2 markers (k=2 <- literal), a=b=8 <- the colour that vanishes;
            order <- reading order;  layout <- column, gap 0;  canvas <- crop
  db615bd4  (new) bg <- per-grid mode, texture <- second most common colour (dotted lattice), both background
            items <- same-colour reach-2 groups (dotted pieces);  block size <- item.h x item.w (own box)
            container <- item with the largest box (dotted frame), redrawn solid, interior cleared
            canvas <- container interior, block anchored at its centre;  axis <- spread axis of the items
            order <- along that axis;  align <- centre;  gap 1 <- literal (same value as 1990f7a8/8abad3cf)
  652646ff  (new) items <- one per colour;  shape <- the shape common to every training output item (6x6 ring),
            placed where it covers most of the colour (covering < half = noise, dropped)
            order <- occlusion depth (topmost layer first);  layout <- column, gap 0;  canvas <- crop
Specialisation menu derived from the table (no invented values):
  bg       in {mode | border | mode + texture colour}
  items    seg + same-colour reach-2;  style + own box | output template
  key      + occlusion depth (offered only for template-completed items)
  markers  bracket a, b <- vanished colours first (role-bound), literal common colours as fallback (+1)
  canvas   in {crop | input frame at corner | in place | container interior, centred}
  gap      literal 0..2 (no role explained the 1s seen)
Not widened (no role-bound parameter or shared step covers their extra step):
  d749d46f  two copies of the line (flat on top, upright at the bottom) on a canvas whose height 10 is a literal
  291dc1e1  writing mode: the origin corner and ruler colours set a dihedral reading frame and glyph rotation,
            glyphs are band-split runs; no other member shares that header-bound frame step.
"""
from collections import Counter

CARD = "prior3_pack_objects_in_order"
CONCEPT = "pack_objects_in_order"
MEMBERS = ["03560426", "1990f7a8", "291dc1e1", "2ba387bc", "4acc7107", "4e45f183", "505fff84", "50aad11f",
           "652646ff", "8abad3cf", "a8c38be5", "aab50785", "d749d46f", "db615bd4"]
READING = {
    "generator": "Extract items (objects, per-colour blobs, congruent tiles or marker-bracketed strips; optionally "
                 "redrawn as own-box blocks or completed to the shape shared by the output items), order them "
                 "by a key (reading/column order, size, colour, occlusion depth, genus bins, own-position or "
                 "self-indicated slot) and lay them out contiguously as a row/column, a diagonal chain, "
                 "per-key column stacks or a slot grid with gap g, on a cropped, input-sized, in-place or "
                 "container-interior canvas.",
    "stop": "every item is placed exactly once; the canvas is the packed block (crop), the input frame with the "
            "block anchored at the mirrored corner, the input with items permuted among their own slots, or "
            "the largest item's interior with the block centred in it",
    "params": "bg in {mode, border, mode+texture} . seg in {c4, c8, c2, m4, m8, m2, colour, cut, bracket(k in "
              "1..3, a, b <- vanished colours (else common colours), close in {near, far}, frame in {id, T})} . "
              "filter in {all, non-singleton} . style in {keep, nearest-marker colour, area square, own box, "
              "output template} . layout in {line(axis in {h, v, spread}, align in {0,1,2}), "
              "chain(g in {-1,0}, top in {later, earlier}), bins(key in {colour, genus}, order in {asc, desc, "
              "first}, within in {rc, cr}, gaps 0..2), grid(slot in {pos, self})} . key in {rc, cr, axis, size+, "
              "size-, colour, depth} . gap in {0,1,2} . mirror in {0,1}^2 . canvas in {crop, input, inplace, frame}",
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
    return {"r0": r0, "c0": c0, "h": r1 - r0 + 1, "w": c1 - c0 + 1, "cells": rel, "n": len(rel), "src": cells}


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
    if bgm == "tex":
        # background <- per-grid mode; texture <- the second most common colour, read as background too
        cnt = Counter(v for row in g for v in row)
        if len(cnt) < 3:
            raise ValueError("no texture")
        bg, tex = sorted(cnt, key=lambda k: (-cnt[k], k))[:2]
        g = [[bg if v == tex else v for v in row] for row in g]
    else:
        bg = _bg(g, bgm)
    if seg == "colour":
        pos = {}
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != bg:
                    pos.setdefault(v, []).append((r, c))
        comps = [pos[v] for v in sorted(pos)]
    else:
        same, reach = {"c4": (True, 0), "c8": (True, 1), "c2": (True, 2), "m4": (False, 0), "m8": (False, 1),
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
    elif style == "box":
        # solid block of the item's own bounding box (width <- item.w, height <- item.h)
        for it in items:
            it["cells"] = [(a, b, _col(it)) for a in range(it["h"]) for b in range(it["w"])]
            it["n"] = it["h"] * it["w"]
    elif style[0] == "tmpl":
        items = _complete(g, items, style)
    return bg, items


def _complete(g, items, style):
    """Template style: each item is completed to the shape common to all training output items (template
    <- output item shape), fitted where it covers most of the item's own colour; an item covering less
    than half of the template is noise and dropped.  Keeps cover/shown cells for the occlusion-depth key."""
    _, th, tw, tcells = style
    H, W = len(g), len(g[0])
    out = []
    for it in items:
        v = _col(it)
        votes = Counter()
        for y, x in it["src"]:
            if g[y][x] != v:
                continue
            for a, b in tcells:
                votes[(y - a, x - b)] += 1
        if not votes:
            continue
        best = max(votes.values())
        if 2 * best < len(tcells):
            continue
        r0, c0 = min(k for k, n in votes.items() if n == best)
        cover = {(r0 + a, c0 + b) for a, b in tcells}
        shown = {(y, x) for y, x in cover if 0 <= y < H and 0 <= x < W and g[y][x] == v}
        out.append({"r0": r0, "c0": c0, "h": th, "w": tw, "cells": [(a, b, v) for a, b in tcells],
                    "n": len(tcells), "src": it["src"], "col": v, "cover": cover, "shown": shown, "fit": best})
    if not out:
        raise ValueError("no item fits the template")
    return out


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
    if key == "depth":
        return _by_depth(items)
    return sorted(items, key=lambda o: (_col(o), o["r0"], o["c0"]))


def _by_depth(items):
    """Occlusion depth: item i is above item j when a cell of both completed shapes shows i's colour.
    Topmost first (most items transitively below), then larger visible fit, then reading order."""
    n = len(items)
    below = [set() for _ in range(n)]
    for i in range(n):
        ci = items[i].get("cover")
        if ci is None:
            continue
        for j in range(n):
            if i != j and items[j].get("cover") is not None and (ci & items[j]["cover"]) & items[i]["shown"]:
                below[i].add(j)
    changed = True
    while changed:
        changed = False
        for i in range(n):
            add = set()
            for j in below[i]:
                add |= below[j]
            add -= below[i]
            add.discard(i)
            if add:
                below[i] |= add
                changed = True
    idx = sorted(range(n), key=lambda i: (-len(below[i]), -items[i].get("fit", items[i]["n"]),
                                          items[i]["r0"], items[i]["c0"]))
    return [items[i] for i in idx]


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


def _split_container(items):
    """container <- the item with the largest bounding box (unique, at least 3x3); the rest are packed."""
    areas = [o["h"] * o["w"] for o in items]
    m = max(areas)
    if areas.count(m) != 1 or len(items) < 2:
        raise ValueError("no unique container")
    k = areas.index(m)
    box = items[k]
    if box["h"] < 3 or box["w"] < 3:
        raise ValueError("container too small")
    return box, items[:k] + items[k + 1:]


def _frame_base(g, bg, items):
    """The frame canvas without its contents: packed items erased from where they were, the container
    redrawn as a solid outline of its own colour with its interior cleared.  Returns (out, box, rest)."""
    box, rest = _split_container(items)
    out = [list(r) for r in g]
    for o in rest:
        for y, x in o["src"]:
            out[y][x] = bg
    R0, C0, R1, C1 = box["r0"], box["c0"], box["r0"] + box["h"] - 1, box["c0"] + box["w"] - 1
    v = _col(box)
    for r in range(R0, R1 + 1):
        for c in range(C0, C1 + 1):
            out[r][c] = v if r in (R0, R1) or c in (C0, C1) else bg
    return out, box, rest


def _framed(g, bg, items, lay, base=None):
    out, box, rest = base if base is not None else _frame_base(g, bg, items)
    out = [list(r) for r in out]
    Hp, Wp, pl = _place(rest, lay)
    IH, IW = box["h"] - 2, box["w"] - 2
    if Hp > IH or Wp > IW:
        raise ValueError("block does not fit the container")
    oy = box["r0"] + 1 + (IH - Hp) // 2          # anchored at the container interior's centre
    ox = box["c0"] + 1 + (IW - Wp) // 2
    for o, y, x in pl:
        for a, b, v in o["cells"]:
            out[oy + y + a][ox + x + b] = v
    return out


def _render(g, bg, items, lay, mirror, canvas):
    if canvas == "inplace":
        return _inplace(g, bg, items, lay)
    if canvas == "frame":
        return _framed(g, bg, items, lay)
    return _paint(g, bg, _place(items, lay), mirror, canvas)


def _layouts(exact, depth=False):
    """Yields (cost, lay) in preference order; only chain overlap can lose cells (exact=False).
    The occlusion-depth key is offered only for completed (template) items, where it differs from size-."""
    keys = ("rc", "cr", "axis", "size+", "size-", "colour") + (("depth",) if depth else ())
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


def _frame_layouts():
    """Layouts offered inside a container (frame canvas): lines and slot grids, contents centred."""
    for gap in (0, 1, 2):
        for axis in ("v", "h", "spread"):
            for key in ("rc", "cr", "axis", "size+", "size-", "colour"):
                for align in (0, 1, 2):
                    yield 1 + gap + (axis == "spread") + (align != 1), ("line", axis, key, align, gap)
    for slot in ("pos", "self"):
        for gap in (0, 1):
            yield 2 + gap, ("grid", slot, gap)


def _seg_configs(colours, vanished=(), tmpl=None):
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
    # bracket marker colours: role-bound first (a, b <- colours that vanish: in every input, in no output),
    # then the literal colours common to all inputs (fallback, +1)
    menu = [c for c in colours if c in vanished] + [c for c in colours if c not in vanished]
    for k in (1, 2, 3):
        for a in menu:
            for b in menu:
                for close in ("near", "far"):
                    yield 2 + (close == "far") + (a != b) + (a not in vanished or b not in vanished), \
                        ("bracket", k, a, b, close)
    # specialisations added in prior3 (after the old menu so old tie-breaks are unchanged)
    for bgm in ("mode", "border", "tex"):
        for seg in ("c4", "c8", "c2", "colour"):
            for style in ("keep", "box"):
                if bgm != "tex" and seg != "c2" and style == "keep":
                    continue                       # already in the old menu
                if bgm == "tex" and seg == "colour":
                    continue
                yield 1 + (bgm != "mode") + (seg == "c2") + (style == "box"), (bgm, seg, "all", style)
    if tmpl is not None:
        yield 1, ("mode", "colour", "all", tmpl)


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


def _template(pairs):
    """template <- the shape shared by every output item (same-colour 8-connected, output mode as
    background) across all training outputs; at least two such items and four cells, else None."""
    shapes = set()
    n = 0
    for _, O in pairs:
        bg = _mode(O)
        for cells in _comps(O, bg, True, 1):
            r0 = min(a for a, _ in cells)
            c0 = min(b for _, b in cells)
            shapes.add(tuple(sorted((a - r0, b - c0) for a, b in cells)))
            n += 1
            if len(shapes) > 1:
                return None
    if n < 2 or not shapes:
        return None
    sh = shapes.pop()
    if len(sh) < 4:
        return None
    return ("tmpl", max(a for a, _ in sh) + 1, max(b for _, b in sh) + 1, sh)


def _outside_ok(base, O):
    """The frame canvas outside the container interior must already equal the output."""
    out, box, _ = base
    ri = range(box["r0"] + 1, box["r0"] + box["h"] - 1)
    ci = range(box["c0"] + 1, box["c0"] + box["w"] - 1)
    for r, (ro, rO) in enumerate(zip(out, O)):
        if r in ri:
            if ro[:ci.start] != rO[:ci.start] or ro[ci.stop:] != rO[ci.stop:]:
                return False
        elif ro != rO:
            return False
    return True


# ------------------------------------------------------------------------------------------------ family
def fam(train):
    try:
        pairs = [(p["input"], p["output"]) for p in train]
        if not pairs or any(not I or not I[0] or not O or not O[0] for I, O in pairs):
            return
        if any(len({len(r) for r in G}) != 1 for I, O in pairs for G in (I, O)):
            return
    except Exception:
        return
    same = all(len(I) == len(O) and len(I[0]) == len(O[0]) for I, O in pairs)
    if same and all(I == O for I, O in pairs):
        return
    canvases = ("input", "inplace", "frame") if same else ("crop",)
    common = None
    for I, _ in pairs:
        cs = {v for r in I for v in r}
        common = cs if common is None else common & cs
    colours = sorted(common)
    out_cols = {v for _, O in pairs for r in O for v in r}
    vanished = {c for c in colours if c not in out_cols}
    tmpl = None if same else _template(pairs)
    fits = []
    for frame in ("id", "T"):
        fp = [(_tr(I), _tr(O)) if frame == "T" else (I, O) for I, O in pairs]
        seen = set()
        sqc = {}
        for ccost, cfg in _seg_configs(colours, vanished, tmpl):
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
                if canvas == "frame":
                    if cfg[0] == "bracket" or cfg[3] not in ("keep", "box"):
                        continue
                    try:
                        bases = [_frame_base(I, bg, it) for (bg, it), (I, O) in zip(ext, fp)]
                    except Exception:
                        continue
                    if not all(_outside_ok(b, O) for b, (I, O) in zip(bases, fp)):
                        continue
                    best = None
                    for lcost, lay in _frame_layouts():
                        if best is not None and lcost >= best[0]:
                            continue
                        try:
                            good = all(_framed(I, bg, it, lay, b) == O
                                       for b, (bg, it), (I, O) in zip(bases, ext, fp))
                        except Exception:
                            good = False
                        if good:
                            best = (lcost, lay)
                    if best is not None:
                        fits.append((ccost + best[0] + 2, len(fits), frame, cfg, best[1], (0, 0), canvas))
                    continue
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
                for lcost, lay in _layouts(exact, cfg[0] != "bracket" and cfg[3][0] == "tmpl"):
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
        cname = cfg if cfg[0] == "bracket" or cfg[3][0] != "tmpl" else \
            cfg[:3] + ("tmpl%dx%d/%d" % (cfg[3][1], cfg[3][2], len(cfg[3][3])),)
        name = "pack[%s|%s|%s|m%d%d|%s]" % (frame, ",".join(map(str, cname)), ",".join(map(str, lay)),
                                           mirror[0], mirror[1], canvas)
        yield name, cost, _make(frame, cfg, lay, mirror, canvas)


FAMILIES = [fam]
