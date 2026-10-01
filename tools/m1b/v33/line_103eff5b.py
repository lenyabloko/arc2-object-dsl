"""Line family for card 103eff5b (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds a small multicoloured palette (a pattern of a few colours with background
holes) and a large solid shape of one colour that is the palette's silhouette, blown up by an
integer factor and turned by one of the eight square symmetries. Each cell of the solid shape takes
the colour of the palette cell it corresponds to, i.e. the palette is transferred onto the shape.
The symmetry is the one the training pairs agree on; on a new grid the first symmetry (in that
preference order) whose scaled silhouette coincides with the shape is used.
"""

CARD = "103eff5b"
LINE = "color palette transfer to solid shape"
READING = {
    "generator": "Turn/flip the small multicoloured palette by a square symmetry, scale it up by the "
                 "integer factor that makes it the size of the solid one-colour shape, and repaint every "
                 "cell of the shape with the colour of the palette cell lying under it.",
    "stop": "Stops when every cell of the solid shape (or its bounding box in 'box' mode) has been "
            "repainted; nothing outside the shape changes except the palette itself when 'erase' is induced.",
    "params": "sym in {auto (first of the train-preferred symmetries whose scaled silhouette equals the shape), "
              "one fixed element of D4} · mode in {mask, box} · scale in {uniform, free (separate row/col factor)} · "
              "group in {union, each 8-component} · palette in {keep, erase} (induced) · "
              "out in {in_place, crop to shape} (induced) · bg = most frequent colour",
    "participants": "Shape: all cells of a non-background colour (tried by decreasing cell count) lying outside "
                    "the palette's box. Palette: bounding box of every other non-background cell (cells of the "
                    "shape colour inside that box belong to the palette).",
    "preconditions": "At least two non-background colours; the shape's bounding box is an integer multiple of "
                     "the (transformed) palette box, and in 'mask' mode each scaled palette cell is wholly shape "
                     "where the palette is coloured and wholly background where it is background.",
}

# The eight symmetries of the square, as functions on list-of-lists grids.
D4 = [
    ("id", lambda g: [list(r) for r in g]),
    ("rot90cw", lambda g: [list(r) for r in zip(*g[::-1])]),
    ("rot180", lambda g: [list(r)[::-1] for r in g[::-1]]),
    ("rot90ccw", lambda g: [list(r) for r in zip(*g)][::-1]),
    ("flip_lr", lambda g: [list(r)[::-1] for r in g]),
    ("flip_ud", lambda g: [list(r) for r in g[::-1]]),
    ("transpose", lambda g: [list(r) for r in zip(*g)]),
    ("antitranspose", lambda g: [list(r)[::-1] for r in zip(*g)][::-1]),
]


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _comps8(cells):
    cells = set(cells)
    out = []
    while cells:
        s = min(cells)
        cells.discard(s)
        stack, comp = [s], [s]
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in cells:
                        cells.discard(q)
                        stack.append(q)
                        comp.append(q)
        out.append(sorted(comp))
    return sorted(out)


def _roles(g):
    """Yield (bg, shape colour, palette crop, palette box, shape cells) for each candidate shape colour."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    cnt = {}
    for row in g:
        for v in row:
            if v != bg:
                cnt[v] = cnt.get(v, 0) + 1
    if len(cnt) < 2:
        return
    for c in sorted(cnt, key=lambda k: (-cnt[k], k)):
        pal = [(r, x) for r in range(H) for x in range(W) if g[r][x] != bg and g[r][x] != c]
        if not pal:
            continue
        r0 = min(p[0] for p in pal); r1 = max(p[0] for p in pal)
        c0 = min(p[1] for p in pal); c1 = max(p[1] for p in pal)
        crop = [g[r][c0:c1 + 1] for r in range(r0, r1 + 1)]
        shape = [(r, x) for r in range(H) for x in range(W)
                 if g[r][x] == c and not (r0 <= r <= r1 and c0 <= x <= c1)]
        if not shape:
            continue
        yield bg, c, crop, (r0, c0, r1, c1), shape


def _paint(Q, cells, bg, mode, scale):
    """Map transformed palette Q onto the shape given by `cells`. Returns {cell: colour} or None."""
    h, w = len(Q), len(Q[0])
    r0 = min(p[0] for p in cells); r1 = max(p[0] for p in cells)
    c0 = min(p[1] for p in cells); c1 = max(p[1] for p in cells)
    Hs, Ws = r1 - r0 + 1, c1 - c0 + 1
    if Hs % h or Ws % w:
        return None
    sy, sx = Hs // h, Ws // w
    if scale == "uniform" and sy != sx:
        return None
    filled = set(cells)
    out = {}
    for r in range(r0, r1 + 1):
        for x in range(c0, c1 + 1):
            v = Q[(r - r0) // sy][(x - c0) // sx]
            on = (r, x) in filled
            if mode == "mask":
                if on != (v != bg):
                    return None
                if on:
                    out[(r, x)] = v
            else:
                out[(r, x)] = v
    return out


def _make(sym, pref, mode, scale, group, palette, outm):
    def fn(g):
        for bg, c, crop, pbox, shape in _roles(g):
            groups = [shape] if group == "union" else _comps8(shape)
            paints = []
            for cells in groups:
                got = None
                order = pref if sym == "auto" else [sym]
                for ti in order:
                    got = _paint(D4[ti][1](crop), cells, bg, mode, scale)
                    if got is not None:
                        break
                if got is None:
                    break
                paints.append(got)
            if len(paints) != len(groups):
                continue
            res = [list(r) for r in g]
            if palette == "erase":
                r0, c0, r1, c1 = pbox
                for r in range(r0, r1 + 1):
                    for x in range(c0, c1 + 1):
                        res[r][x] = bg
            for p in paints:
                for (r, x), v in p.items():
                    res[r][x] = v
            if outm == "crop":
                rs = [p[0] for p in shape]; xs = [p[1] for p in shape]
                res = [row[min(xs):max(xs) + 1] for row in res[min(rs):max(rs) + 1]]
            return res
        return None
    return fn


def _ok(fn, train):
    try:
        return all(fn(p["input"]) == p["output"] for p in train)
    except Exception:
        return False


def fam(train):
    for p in train:
        if next(_roles(p["input"]), None) is None:
            return
    # Induced output form and palette fate (both from the training outputs).
    same = all(len(p["output"]) == len(p["input"]) and len(p["output"][0]) == len(p["input"][0])
               for p in train)
    outms = ["in_place"] if same else ["crop"]
    palettes = ["keep", "erase"]
    # Preference order for 'auto': symmetries ranked by how many training pairs they reproduce.
    score = []
    for ti in range(len(D4)):
        fns = [_make(ti, None, "mask", sc, "union", pal, outms[0])
               for pal in palettes for sc in ("uniform", "free")]
        score.append(sum(1 for p in train if any(_ok(f, [p]) for f in fns)))
    pref = sorted(range(len(D4)), key=lambda t: (-score[t], t))
    progs = []
    for pi, pal in enumerate(palettes):
        for si, sc in enumerate(("uniform", "free")):
            for gi, grp in enumerate(("union", "each")):
                base = pi + si + 2 * gi
                progs.append(("palette_to_shape[sym=auto,mode=mask,scale=%s,group=%s,palette=%s,out=%s]"
                              % (sc, grp, pal, outms[0]), 1 + base,
                              _make("auto", pref, "mask", sc, grp, pal, outms[0])))
                for ti in pref:
                    if score[ti] < len(train):
                        continue
                    for mi, md in enumerate(("mask", "box")):
                        progs.append(("palette_to_shape[sym=%s,mode=%s,scale=%s,group=%s,palette=%s,out=%s]"
                                      % (D4[ti][0], md, sc, grp, pal, outms[0]), 2 + base + mi,
                                      _make(ti, None, md, sc, grp, pal, outms[0])))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = (repr(outs), name.split("[")[1].split(",")[0])
        if sig in seen:
            continue  # same symmetry choice and same train behaviour as a cheaper program
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
