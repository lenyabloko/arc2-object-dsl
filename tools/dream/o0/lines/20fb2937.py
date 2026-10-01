"""Line family for card 20fb2937 (test-blind; written from the reviewer's line and train pairs only).

Reading: the grid is cut by one separator (a full row band or column band of a single non-background
colour). One side is a legend: entries that each pair a key object with a value object of another
colour. On the other side every object of a key colour is converted with its entry: either it is
replaced by a copy of the entry's value shape (stamped centred on it, or at the legend's key->value
offset), or it is simply recoloured to the value colour. The answer is the converted target side
(cropped) or the whole grid with only the target side converted.

In 20fb2937 the legend is above the separator: three 3x3 colour blocks, each with a single key pixel
beneath it; every key-coloured pixel below the separator becomes the 3x3 block of the mapped colour
centred on it, and the answer is the part below the separator.
"""

CARD = "20fb2937"
LINE = "use color mapping legend above separator line to convert corresponding shapes below the separator"
READING = {
    "generator": "Below (beyond) the separator line, every object of a legend key colour is replaced by the "
                 "legend's value shape in the value colour, centred on it (or recoloured to the value colour "
                 "when the legend maps colour to colour); the answer is that converted side of the grid.",
    "stop": "Each target object is converted once, from the input; objects whose colour has no legend entry and "
            "background stay as they are; stamps are clipped to the target side; later stamps (reading order) "
            "overwrite earlier ones where they overlap.",
    "params": "axis in {row, col} · legend side in {smaller, before, after} · entry in {near (each key object "
              "takes its nearest value object), mutual (mutually nearest objects), touch (two-colour connected "
              "component)} · key role in {present (colour occurs on target side), small (smallest legend "
              "objects / smaller of the pair), near_sep, far_sep (pair-wise, mutual/touch only)} · match in {colour, shape} · mode in {stamp, "
              "recolor} · anchor in {center, offset} (stamp) · key cells in {erase, keep} (stamp) · "
              "output in {crop (target side only), full}",
    "participants": "Background: most frequent colour. Separator: the single band of full uniform non-background "
                    "rows (or columns). Legend: the objects on the legend side, split into keys (by default: objects "
                    "whose colour also occurs on the target side) and values, each key paired with its nearest "
                    "value object (alternatives: mutual nearest pairs, touching two-colour pairs). Targets: 8-connected single-colour objects on the other side whose colour (and shape, "
                    "if match=shape) equals a key.",
    "preconditions": "Exactly one separator band on the chosen axis with non-empty sides; every legend entry "
                     "resolves to one key and one value of different colours; no key colour maps to two "
                     "different values; at least one target object exists.",
}


class _Fail(Exception):
    pass


# ---------------------------------------------------------------- basics

def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return min(cnt, key=lambda c: (-cnt[c], c))


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _separator(g, bg):
    """Rows-axis separator band (lo, hi) inclusive, or None. Uniform non-bg full rows grouped into
    contiguous same-colour bands; if several, keep bands whose colour occurs nowhere else; need one."""
    H = len(g)
    uni = [(g[r][0] if g[r][0] != bg and all(v == g[r][0] for v in g[r]) else None) for r in range(H)]
    bands = []
    r = 0
    while r < H:
        if uni[r] is None:
            r += 1
            continue
        s = r
        while r + 1 < H and uni[r + 1] == uni[s]:
            r += 1
        bands.append((s, r, uni[s]))
        r += 1
    if len(bands) > 1:
        keep = []
        for lo, hi, col in bands:
            elsewhere = any(g[y][x] == col for y in range(H) if not (lo <= y <= hi) for x in range(len(g[0])))
            if not elsewhere:
                keep.append((lo, hi, col))
        bands = keep
    if len(bands) != 1:
        return None
    lo, hi, _ = bands[0]
    if lo == 0 or hi == H - 1:
        return None
    return lo, hi


def _components(g, rows, bg, multi=False):
    """8-connected components of non-bg cells restricted to the given rows.
    multi=False: single-colour components; multi=True: any non-bg colours together."""
    W = len(g[0])
    rows = set(rows)
    seen = set()
    comps = []
    for r in sorted(rows):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            col = g[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if (yy, xx) in seen or yy not in rows or not (0 <= xx < W):
                            continue
                        v = g[yy][xx]
                        if v == bg or (not multi and v != col):
                            continue
                        seen.add((yy, xx))
                        stack.append((yy, xx))
            comps.append(sorted(cells))
    return comps


def _bbox(cells):
    ys = [y for y, _ in cells]
    xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


def _norm(cells):
    r0, c0, _, _ = _bbox(cells)
    return tuple(sorted((y - r0, x - c0) for y, x in cells))


def _dist(a, b):
    return min(abs(y1 - y2) + abs(x1 - x2) for y1, x1 in a for y2, x2 in b)


# ---------------------------------------------------------------- legend

def _colour(g, cells):
    return g[cells[0][0]][cells[0][1]]


def _entries(g, bg, leg_rows, tgt_colours, sep, entry, role):
    """List of (key_cells, value_cells) read from the legend rows.
    entry=near:   legend objects are split into keys / values by the role (present: colour occurs on the
                  target side; small: objects of the smallest legend size), then each key takes its unique
                  nearest value object (a value serves one key).
    entry=mutual: mutually nearest single-colour objects of different colours form an entry.
    entry=touch:  a two-colour connected legend component forms an entry.
    For mutual / touch the role picks the key inside the entry (present, small, near_sep, far_sep)."""
    lo, hi = sep
    if entry == "near":
        objs = _components(g, leg_rows, bg)
        if role == "present":
            keys = [o for o in objs if _colour(g, o) in tgt_colours]
            vals = [o for o in objs if _colour(g, o) not in tgt_colours]
        elif role == "small":
            m = min(len(o) for o in objs) if objs else 0
            keys = [o for o in objs if len(o) == m]
            vals = [o for o in objs if len(o) > m]
        else:
            raise _Fail
        if not keys or not vals:
            raise _Fail
        out, used = [], set()
        for k in keys:
            ds = sorted((_dist(k, v), i) for i, v in enumerate(vals) if _colour(g, v) != _colour(g, k))
            if not ds or (len(ds) > 1 and ds[0][0] == ds[1][0]) or ds[0][1] in used:
                raise _Fail
            used.add(ds[0][1])
            out.append((k, vals[ds[0][1]]))
        return out

    pairs = []
    if entry == "touch":
        for comp in _components(g, leg_rows, bg, multi=True):
            cols = sorted({g[y][x] for y, x in comp})
            if len(cols) != 2:
                continue
            a = [p for p in comp if g[p[0]][p[1]] == cols[0]]
            b = [p for p in comp if g[p[0]][p[1]] == cols[1]]
            pairs.append((a, b))
    else:
        objs = _components(g, leg_rows, bg)
        n = len(objs)
        nn = []
        for i in range(n):
            best, bi, tie = None, None, False
            for j in range(n):
                if j == i or _colour(g, objs[j]) == _colour(g, objs[i]):
                    continue
                d = _dist(objs[i], objs[j])
                if best is None or d < best:
                    best, bi, tie = d, j, False
                elif d == best:
                    tie = True
            nn.append(None if tie else bi)
        for i in range(n):
            j = nn[i]
            if j is not None and j > i and nn[j] == i:
                pairs.append((objs[i], objs[j]))
    if not pairs:
        raise _Fail
    out = []
    for a, b in pairs:
        ca, cb = _colour(g, a), _colour(g, b)
        if role == "present":
            pa, pb = ca in tgt_colours, cb in tgt_colours
            if pa == pb:
                raise _Fail
            key_first = pa
        elif role == "small":
            if len(a) == len(b):
                raise _Fail
            key_first = len(a) < len(b)
        else:
            def sd(cells):
                return min(min(abs(y - lo), abs(y - hi)) for y, _ in cells)
            da, db = sd(a), sd(b)
            if da == db:
                raise _Fail
            key_first = (da < db) if role == "near_sep" else (da > db)
        out.append((a, b) if key_first else (b, a))
    return out


# ---------------------------------------------------------------- program

def _apply_rows(g, side, entry, role, match, mode, anchor, keep, out_mode):
    bg = _bg(g)
    sep = _separator(g, bg)
    if sep is None:
        raise _Fail
    lo, hi = sep
    H, W = len(g), len(g[0])
    before, after = list(range(0, lo)), list(range(hi + 1, H))
    if side == "smaller":
        leg_first = len(before) <= len(after)
    else:
        leg_first = side == "before"
    leg_rows, tgt_rows = (before, after) if leg_first else (after, before)
    tgt_set = set(tgt_rows)
    tgt_colours = {g[y][x] for y in tgt_rows for x in range(W)} - {bg}
    ents = _entries(g, bg, leg_rows, tgt_colours, sep, entry, role)

    # key lookup: colour (and shape) -> entry; conflicting values are a failure
    table = {}
    for k, v in ents:
        kc = g[k[0][0]][k[0][1]]
        tag = (kc, _norm(k)) if match == "shape" else kc
        val = (tuple((y, x, g[y][x]) for y, x in v), tuple(_bbox(k)))
        sig = (_norm(v), g[v[0][0]][v[0][1]])
        if tag in table and table[tag][0] != sig:
            raise _Fail
        table.setdefault(tag, (sig, val, k))

    res = [list(r) for r in g]
    targets = _components(g, tgt_rows, bg)
    hits = 0
    for t in targets:
        tc = g[t[0][0]][t[0][1]]
        tag = (tc, _norm(t)) if match == "shape" else tc
        if tag not in table:
            continue
        hits += 1
        _, (vcells, kbox), kcells = table[tag]
        vcol = vcells[0][2]
        if mode == "recolor":
            for y, x in t:
                res[y][x] = vcol
            continue
        if keep == "erase":
            for y, x in t:
                res[y][x] = bg
        vr0, vc0, vr1, vc1 = _bbox([(y, x) for y, x, _ in vcells])
        tr0, tc0, tr1, tc1 = _bbox(t)
        if anchor == "center":
            top = tr0 + ((tr1 - tr0 + 1) - (vr1 - vr0 + 1)) // 2
            left = tc0 + ((tc1 - tc0 + 1) - (vc1 - vc0 + 1)) // 2
        else:
            top = tr0 + (vr0 - kbox[0])
            left = tc0 + (vc0 - kbox[1])
        for y, x, col in vcells:
            yy, xx = top + y - vr0, left + x - vc0
            if yy in tgt_set and 0 <= xx < W:
                res[yy][xx] = col
    if hits == 0:
        raise _Fail
    if out_mode == "crop":
        return [res[y] for y in tgt_rows]
    return res


def _make(axis, side, entry, role, match, mode, anchor, keep, out_mode):
    def fn(g):
        g = [list(r) for r in g]
        if axis == "col":
            s = {"before": "before", "after": "after", "smaller": "smaller"}[side]
            return _transpose(_apply_rows(_transpose(g), s, entry, role, match, mode, anchor, keep, out_mode))
        return _apply_rows(g, side, entry, role, match, mode, anchor, keep, out_mode)
    return fn


def _specs():
    specs = []
    for ia, axis in enumerate(("row", "col")):
        for io, out_mode in enumerate(("crop", "full")):
            for isd, side in enumerate(("smaller", "before", "after")):
                for ie, entry in enumerate(("near", "mutual", "touch")):
                    roles = ("present", "small") if entry == "near" else ("present", "small", "near_sep", "far_sep")
                    for ir, role in enumerate(roles):
                        for im, match in enumerate(("colour", "shape")):
                            modes = [("stamp", "center", "erase", 0), ("stamp", "center", "keep", 1),
                                     ("stamp", "offset", "erase", 2), ("stamp", "offset", "keep", 3),
                                     ("recolor", None, None, 1)]
                            for mode, anchor, keep, mc in modes:
                                cost = 1 + ia + io + isd + ie + ir + im + mc
                                name = ("legend_convert[axis=%s,side=%s,entry=%s,key=%s,match=%s,mode=%s,"
                                        "anchor=%s,key_cells=%s,out=%s]"
                                        % (axis, side, entry, role, match, mode, anchor, keep, out_mode))
                                specs.append((cost, name, (axis, side, entry, role, match, mode, anchor, keep,
                                                           out_mode)))
    specs.sort(key=lambda t: (t[0], t[1]))
    return specs


def fam(train):
    if not train:
        return
    # precondition: some axis has a single separator band in every training input
    axes_ok = set()
    for axis in ("row", "col"):
        ok = True
        for p in train:
            g = p["input"] if axis == "row" else _transpose(p["input"])
            if not g or not g[0] or _separator(g, _bg(g)) is None:
                ok = False
                break
        if ok:
            axes_ok.add(axis)
    if not axes_ok:
        return
    seen = set()
    for cost, name, args in _specs():
        if args[0] not in axes_ok:
            continue
        fn = _make(*args)
        good = True
        outs = []
        for p in train:
            try:
                o = fn(p["input"])
            except Exception:
                good = False
                break
            if o != p["output"]:
                good = False
                break
            outs.append(o)
        if not good:
            continue
        # one program per conversion class (axis, match, mode, anchor, output); the cheapest parse wins
        key = (args[0], args[4], args[5], args[6] if args[5] == "stamp" else None, args[8])
        if key in seen:
            continue
        seen.add(key)
        yield name, cost, fn


FAMILIES = [fam]
