"""Prior family "learned_key_table", version 3 (test-blind; specialised over the FITTED BINDINGS of version 2).

One generator, KEY -> TABLE -> EMIT: compute a discrete key for each unit of the input, look it up in a table that is
induced from the training pairs, and emit the stored value.  A unit is the whole grid, a panel of the grid (blocks
separated by empty lines) or a structural region / cell role (cell of a separator partition classified by its band
position, convex / concave corner of a 1-px outline, quadrant / inset / core of a solid rectangle, relative position
inside an object's bounding box).  The key is a whole-grid feature (binary mask, number of colours, dominant colour,
colour set, a linked-by-path predicate, containment in the stored glyph), a panel's binary mask, or the role itself.
The value is an output glyph (whole grid), a colour (panel), or a cell recolouring (keep / literal constant /
role-bound colour / per-input-colour map).  Shared steps written once: background by frequency, component extraction,
the role colours of a grid, the table induction with consistency and sharing checks (a key that changes something must
be seen at least twice), nearest-mask / containment fallback for unseen keys, and the exact-fit verification.

BINDINGS (G68) -- every value induced for the members version 2 fits, with the role that explains it
(value seen in training  <-  role; "literal" = no role explains it, kept as a fitted constant).
  15663ba9  unit=role(corner of 1-px outline); outline colour varies (8,3,1) -> convex 4, concave 2 <- literal
            (const: one output over several input colours); other cells keep <- input colour; bg 0 <- grid mode
  239be575  unit=grid, key = linked(2, 8-conn) <- "all cells of colour 2 lie in one non-bg component";
            glyph [[8]] <- the linking colour (the other non-bg colour; also literal 8 in every pair),
            glyph [[0]] <- bg (also literal 0)
  272f95fa  unit=role(partition, separator colour 8 <- the colour with most full rows+cols);
            band roles (first,inner) 2, (inner,first) 4, (inner,inner) 6, (inner,last) 3, (last,inner) 1 <- literal
  27a28665  unit=grid, key = binary mask (ink colour varies 1/8/5/4 and is ignored); glyph colour 3/6/2/1 <- literal
  639f5a19  unit=role(quad, k=2 <- literal); quadrant 0..3 -> 6,1,2,3 and inset -> 4 <- literal; rect colour 8 <- ink
  6e02f1e3  unit=grid, key = number of colours (1/2/3); glyph colours 5 and 0 <- literal (colours new in outputs)
  9110e3c5  unit=grid, key = dominant colour <- most frequent non-bg colour (1/2/3); glyph colour 8 <- literal
  941d9a10  unit=role(partition, gran 2); (first,first) 1, (centre,centre) 2, (last,last) 3 <- literal
  995c5fa3  unit=panel (bg 0 <- literal "zero"; panels split by empty columns); row colour <- panel mask table
            (literal 8/2/4/3); row width <- number of panels k (also literal 3)
  a834deea  unit=role(relpos in a 5x5 box <- object bbox); bg cells -> digit per relative position <- literal;
            box colour 8 kept <- input colour
  d4469b4b  unit=grid, key = dominant colour (the object's colour 1/2/3); glyph colour 5 <- literal
  e9c9d9a1  unit=role(partition, gran 1); corner bands 2/4/1/8, inner 7 <- literal
  ed74f2f2  unit=panel, key = left panel mask; painted shape <- the other panel's ink; colour <- mask table (literal)
Specialisation menu built from these bindings (added as alternatives; a literal is kept whenever it fits, a
role-bound value is used only where the literal varies across pairs):
  colour value  in {literal | bg <- grid mode (239be575) | dom <- most frequent non-bg colour (the 9110e3c5 /
                d4469b4b key, reused as a value) | marker <- rarest colour of the grid}
  inset depth k in {literal 0..4 (639f5a19) | k <- the rectangle's own half-size (innermost inset = core)}
  glyph         in {literal | the stored glyph with pose <- input's pose and palette <- input's colours}
  width         in {literal | k <- number of panels (995c5fa3)}
Widened (no task ids, no per-member branches):
  22806e14  role scheme "core" (quad with k bound to each rectangle, 1x1 included): core of odd squares
            -> colour <- marker (the rarest colour: the plus-shaped key 8/1/3); other roles keep; the key's own cells
            (role free & marker) keep or erase via the literal per-colour map {8:7, 1:7, 3:3} -- no role in the
            menu explains keep vs erase, so that part stays a fitted constant
  269e22fb  unit=grid, key = containment in the one stored glyph (the training outputs, equal up to the 8 poses and
            a colour bijection); emitted glyph pose <- input's registration pose, palette <- input's colours
Not widened: 9caba7c3 needs a greedy non-overlapping choice of 3x3 windows ranked by marker count; no role or shared
  step of this family selects windows, and adding it would be a per-member branch.
"""
from collections import Counter

CARD = "prior3_learned_key_table"
CONCEPT = "learned_key_table"
MEMBERS = ["15663ba9", "22806e14", "239be575", "269e22fb", "272f95fa", "27a28665", "639f5a19", "6e02f1e3",
           "9110e3c5", "941d9a10", "995c5fa3", "9caba7c3", "a834deea", "d4469b4b", "e9c9d9a1", "ed74f2f2"]
READING = {
    "generator": "Compute a discrete key per unit (the whole grid: binary mask, colour count, dominant colour, colour "
                 "set or a linked-by-path predicate; each panel: its binary mask; each region/cell: its structural "
                 "role in a separator partition, a 1-px outline, a solid rectangle or an object's bounding box), look "
                 "it up in a table induced from the training pairs, and emit the stored glyph (in the input's pose "
                 "and palette when the key is containment), the stored colour "
                 "(as one row per panel or painted onto the other panel's ink), or paint each role's cells with its "
                 "stored colour.",
    "stop": "One lookup per unit; every unit is emitted once; cells without a role are left unchanged; an unseen "
            "mask key falls back to the nearest stored mask, any other unseen key keeps the cell (role) or fails.",
    "params": "unit ∈ {grid, panel, role} · key ∈ {mask, ncol, dom, colset, linked(c,conn∈{4,8}), contained"
              "(sym∈{id,D4}, palette∈{fixed,perm}), panelmask, part1, part2, corner, quad(k∈{0..4} | k←core), "
              "relpos} · value ∈ {glyph (literal | pose/palette ← input), colour, keep, const, "
              "bind(colour ← bg | dom | marker), map} · "
              "emit ∈ {glyph, rows(w∈{k,const}), paint_other(p∈{0,1}), paint_cells} · axis ∈ {v, h} · "
              "bg ∈ {mode, 0}",
    "participants": "bg = most frequent colour (grid or all training inputs); separators = full rows and full "
                    "columns of one colour; panels = maximal runs of non-empty columns (rows) cropped to the inked "
                    "rows; objects = same-colour 4-/8-connected non-background components; solid rectangles = "
                    "components filling their bounding box; outline corners = cells with exactly two same-colour "
                    "4-neighbours at a right angle, convex when the bend points into the enclosed area; "
                    "role colours of a grid: bg = most frequent, dom = most frequent other, marker = rarest; "
                    "stored glyph (containment) = the training outputs, one picture up to pose and palette.",
    "preconditions": "grid unit: outputs differ, a key is shared by two training inputs; panel unit: panel count "
                     "matches the output rows (rows) or is two (paint_other); role unit: same-size pairs, every "
                     "changed cell has a role, every role that changes cells is seen in at least two regions; "
                     "containment: outputs differ but are one picture up to pose/palette and every input is no larger; "
                     "every program reproduces all training pairs exactly.",
}

D4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
D8 = D4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


# ----------------------------------------------------------------------------------------------- shared steps
def _mode(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _train_bg(train):
    c = Counter(v for p in train for r in p['input'] for v in r)
    best = max(c.values())
    return min(k for k in c if c[k] == best)


def _comps(g, bg, nb):
    """Same-colour connected components of non-background cells: list of (colour, cells)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            st = [(r, c)]
            seen[r][c] = True
            cells = []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] == col:
                        seen[yy][xx] = True
                        st.append((yy, xx))
            out.append((col, cells))
    return out


def _mask(g, bg):
    return tuple(tuple(0 if v == bg else 1 for v in r) for r in g)


def _nearest(table, k):
    """Unseen binary-mask key: the stored key of the same shape with the fewest differing cells."""
    best, bd = None, None
    for t in sorted(table):
        if len(t) != len(k) or len(t[0]) != len(k[0]):
            continue
        d = sum(a != b for ra, rb in zip(t, k) for a, b in zip(ra, rb))
        if bd is None or d < bd:
            best, bd = t, d
    return best


def _induce(items):
    """items: (key, value) pairs -> table, or None when a key maps to two values or no key is shared."""
    table = {}
    for k, v in items:
        if k is None:
            return None
        if k in table and table[k] != v:
            return None
        table[k] = v
    if not table or len(table) >= len(items):
        return None
    return table


def _lookup(table, k, is_mask):
    if k in table:
        return table[k]
    if is_mask and k is not None:
        n = _nearest(table, k)
        if n is not None:
            return table[n]
    return None


# ----------------------------------------------------------------------------------------- unit = whole grid
def _linked(g, bg, c, nb):
    """Are all cells of colour c inside one connected component of non-background cells?"""
    H, W = len(g), len(g[0])
    cs = [(r, x) for r in range(H) for x in range(W) if g[r][x] == c]
    if not cs:
        return None
    seen = {cs[0]}
    st = [cs[0]]
    while st:
        y, x = st.pop()
        for dy, dx in nb:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] != bg:
                seen.add((yy, xx))
                st.append((yy, xx))
    return all(p in seen for p in cs)


def _grid_keys(train, bg):
    keys = [("ncol", 1.0, False, lambda g: len({v for r in g for v in r}))]

    def dom(g):
        c = Counter(v for r in g for v in r if v != bg)
        if not c:
            return None
        top = c.most_common()
        if len(top) > 1 and top[1][1] == top[0][1]:
            return None
        return top[0][0]
    keys.append(("dom", 1.0, False, dom))
    keys.append(("colset", 1.1, False, lambda g: tuple(sorted({v for r in g for v in r} - {bg}))))
    common = None
    for p in train:
        s = {v for r in p['input'] for v in r} - {bg}
        common = s if common is None else common & s
    for c in sorted(common or ()):
        for cn, nb in (("8", D8), ("4", D4)):
            keys.append(("linked%d_%s" % (c, cn), 1.3, False,
                         lambda g, c=c, nb=nb: _linked(g, bg, c, nb)))
    keys.append(("mask", 1.5, True, lambda g: _mask(g, bg)))
    return keys


def _grid_programs(train):
    bg = _train_bg(train)
    outs = {tuple(map(tuple, p['output'])) for p in train}
    if len(outs) < 2:
        return
    for name, cost, is_mask, key in _grid_keys(train, bg):
        try:
            table = _induce([(key(p['input']), tuple(map(tuple, p['output']))) for p in train])
        except Exception:
            table = None
        if table is None or len(set(table.values())) < 2:
            continue

        def fn(g, key=key, table=table, is_mask=is_mask):
            o = _lookup(table, key(g), is_mask)
            return None if o is None else [list(r) for r in o]
        yield ("grid_%s->glyph" % name, cost, fn)


def _poses(g, sym):
    """Distinct poses of g: identity only, or the 8 symmetries of the square (fixed order, identity first)."""
    h = [list(r) for r in g]
    if sym == "id":
        return [h]
    out = []
    for _ in range(4):
        for q in (h, [r[::-1] for r in h]):
            if q not in out:
                out.append(q)
        h = [list(r) for r in zip(*h[::-1])]
    return out


def _canon(g, pal):
    if pal == "fixed":
        return tuple(map(tuple, g))
    m = {}
    return tuple(tuple(m.setdefault(v, len(m)) for v in r) for r in g)


def _register(atlas, frag, sym, pal):
    """Containment lookup: the stored glyph in the first pose (and colour bijection) under which `frag` is a window
    of it, emitted in that pose and palette -- pose <- the input's pose, palette <- the input's colours."""
    H, W = len(frag), len(frag[0])
    for q in _poses(atlas, sym):
        R, C = len(q), len(q[0])
        if H > R or W > C:
            continue
        for top in range(R - H + 1):
            for left in range(C - W + 1):
                fwd, bwd, ok = {}, {}, True
                for i in range(H):
                    qr, fr = q[top + i], frag[i]
                    for j in range(W):
                        a, b = qr[left + j], fr[j]
                        if pal == "fixed":
                            if a != b:
                                ok = False
                                break
                        elif fwd.setdefault(a, b) != b or bwd.setdefault(b, a) != a:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    return [[fwd.get(v, v) for v in r] for r in q]
    return None


def _registration_programs(train):
    """unit = grid, key = 'the input is contained in the stored glyph' (one stored glyph shared by every pair, the
    training outputs up to pose / palette), value = that glyph with pose and palette bound to the input's."""
    outs = [p['output'] for p in train]
    if len({tuple(map(tuple, o)) for o in outs}) < 2:
        return
    atlas = outs[0]
    for sym in ("id", "D4"):
        for pal in ("fixed", "perm"):
            if sym == "id" and pal == "fixed":
                continue
            ks = {_canon(q, pal) for q in _poses(atlas, sym)}
            if not all(_canon(o, pal) in ks for o in outs):
                continue
            if any(len(p['input']) * len(p['input'][0]) > len(atlas) * len(atlas[0]) for p in train):
                return

            def fn(g, sym=sym, pal=pal):
                return _register(atlas, g, sym, pal)
            yield ("grid_contained->glyph_%s_%s" % (sym, pal), 1.6, fn)
            return


# ---------------------------------------------------------------------------------------------- unit = panel
def _T(g):
    return [list(r) for r in zip(*g)]


def _panels(g, bg, axis):
    if axis == 'h':
        return [_T(p) for p in _panels(_T(g), bg, 'v')]
    H, W = len(g), len(g[0])
    occ = [any(g[i][j] != bg for i in range(H)) for j in range(W)]
    rows = [i for i in range(H) if any(v != bg for v in g[i])]
    if not rows:
        return []
    r0, r1 = rows[0], rows[-1]
    out, j = [], 0
    while j < W:
        if occ[j]:
            k = j
            while k < W and occ[k]:
                k += 1
            out.append([g[i][j:k] for i in range(r0, r1 + 1)])
            j = k
        else:
            j += 1
    return out


def _panel_programs(train):
    tbg = _train_bg(train)
    for bgname, bgf in (("mode", lambda g: tbg), ("zero", lambda g: 0)):
        if bgname == "zero" and tbg == 0:
            continue
        for axis in ('v', 'h'):
            try:
                P = [_panels(p['input'], bgf(p['input']), axis) for p in train]
            except Exception:
                continue
            if any(len(ps) < 2 for ps in P):
                continue
            # emit = rows: one uniform row per panel, in panel order
            items, ok = [], True
            for p, ps in zip(train, P):
                o = p['output']
                if len(o) != len(ps) or any(len(set(r)) != 1 for r in o):
                    ok = False
                    break
                bg = bgf(p['input'])
                items += [(_mask(q, bg), r[0]) for q, r in zip(ps, o)]
            table = _induce(items) if ok else None
            if table is not None and len(set(table.values())) >= 2:
                wc = {len(p['output'][0]) for p in train}
                modes = []
                if all(len(p['output'][0]) == len(p['output']) for p in train):
                    modes.append('k')
                if len(wc) == 1:
                    modes.append(wc.pop())
                for wm in modes:
                    def fn(g, table=table, wm=wm, axis=axis, bgf=bgf):
                        bg = bgf(g)
                        ps = _panels(g, bg, axis)
                        cols = [_lookup(table, _mask(q, bg), True) for q in ps]
                        if not cols or None in cols:
                            return None
                        w = len(cols) if wm == 'k' else wm
                        return [[c] * w for c in cols]
                    yield ("panel_mask->colour_rows_%s_%s_%s" % (axis, bgname, wm), 1.2, fn)
            # emit = paint_other: key panel p selects the colour of the other panel's ink
            if any(len(ps) != 2 for ps in P):
                continue
            for kp in (0, 1):
                items, ok = [], True
                for p, ps in zip(train, P):
                    o, t, bg = p['output'], ps[1 - kp], bgf(p['input'])
                    if len(o) != len(t) or len(o[0]) != len(t[0]):
                        ok = False
                        break
                    cs = set()
                    for i in range(len(o)):
                        for j in range(len(o[0])):
                            if (t[i][j] == bg) != (o[i][j] == bg):
                                ok = False
                            elif o[i][j] != bg:
                                cs.add(o[i][j])
                    if not ok or len(cs) != 1:
                        ok = False
                        break
                    items.append((_mask(ps[kp], bg), cs.pop()))
                table = _induce(items) if ok else None
                if table is None or len(set(table.values())) < 2:
                    continue

                def fn(g, table=table, kp=kp, axis=axis, bgf=bgf):
                    bg = bgf(g)
                    ps = _panels(g, bg, axis)
                    if len(ps) != 2:
                        return None
                    c = _lookup(table, _mask(ps[kp], bg), True)
                    if c is None:
                        return None
                    return [[c if v != bg else bg for v in r] for r in ps[1 - kp]]
                yield ("panel%d_mask->colour_paint_other_%s_%s" % (kp, axis, bgname), 1.25, fn)


# ------------------------------------------------------------------------------------- unit = region / cell role
# every role scheme returns regions: list of (instance, role key, cells)
def _bands(lines, n):
    out, cur = [], []
    for i in range(n):
        if i in lines:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _band_class(i, n, gran):
    if i == 0:
        return 'first'
    if i == n - 1:
        return 'last'
    if gran == 2 and n % 2 == 1 and i == n // 2:
        return 'centre'
    return 'inner'


def _roles_partition(g, gran):
    H, W = len(g), len(g[0])
    best = None
    for c in sorted({v for r in g for v in r}):
        rows = {i for i in range(H) if all(v == c for v in g[i])}
        cols = {j for j in range(W) if all(g[i][j] == c for i in range(H))}
        if rows and cols and len(rows) < H and len(cols) < W:
            if best is None or len(rows) + len(cols) > best[0]:
                best = (len(rows) + len(cols), rows, cols)
    if best is None:
        return None
    R, C = _bands(best[1], H), _bands(best[2], W)
    regs = []
    for bi, rb in enumerate(R):
        for bj, cb in enumerate(C):
            key = (_band_class(bi, len(R), gran), _band_class(bj, len(C), gran))
            regs.append(((bi, bj), key, [(r, c) for r in rb for c in cb]))
    return regs


def _roles_corner(g):
    H, W = len(g), len(g[0])
    bg = _mode(g)
    out = [[False] * W for _ in range(H)]
    st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == bg]
    for r, c in st:
        out[r][c] = True
    while st:
        r, c = st.pop()
        for dr, dc in D4:
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and not out[rr][cc] and g[rr][cc] == bg:
                out[rr][cc] = True
                st.append((rr, cc))
    regs = []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == bg:
                continue
            nb = [(dr, dc) for dr, dc in D4 if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == v]
            if len(nb) != 2 or (nb[0][0] + nb[1][0] == 0 and nb[0][1] + nb[1][1] == 0):
                continue
            rr, cc = r + nb[0][0] + nb[1][0], c + nb[0][1] + nb[1][1]
            inside = 0 <= rr < H and 0 <= cc < W and not out[rr][cc]
            regs.append(((r, c), 'convex' if inside else 'concave', [(r, c)]))
    return regs


def _roles_quad(g, k):
    regs = []
    for col, cells in _comps(g, _mode(g), D4):
        r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
        c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if len(cells) != h * w or h < 2 or w < 2:
            continue
        groups = {}
        for y, x in cells:
            i, j = y - r0, x - c0
            if k and k <= i < h - k and k <= j < w - k:
                role = 'inset'
            else:
                role = (0 if 2 * i < h else 2) + (0 if 2 * j < w else 1)
            groups.setdefault(role, []).append((y, x))
        regs += [((r0, c0), role, cs) for role, cs in groups.items()]
    return regs


def _roles_core(g):
    """quad with the inset depth bound to each rectangle (k <- (min(h,w)-1)//2, the innermost inset; 1x1 included):
    core role keyed by (h odd, w odd, square), other cells by quadrant; cells of non-rectangular components get the
    role ('free', colour is the grid's marker colour)."""
    bg = _mode(g)
    mk = _binds(g)["marker"]
    regs = []
    for col, cells in _comps(g, bg, D4):
        r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
        c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if len(cells) != h * w:
            regs.append(((r0, c0), ('free', col == mk), cells))
            continue
        d = (min(h, w) - 1) // 2
        groups = {}
        for y, x in cells:
            i, j = y - r0, x - c0
            if d <= i < h - d and d <= j < w - d:
                role = ('core', h % 2, w % 2, h == w)
            else:
                role = (0 if 2 * i < h else 2) + (0 if 2 * j < w else 1)
            groups.setdefault(role, []).append((y, x))
        regs += [((r0, c0), role, cs) for role, cs in groups.items()]
    return regs


def _roles_relpos(g):
    H, W = len(g), len(g[0])
    taken = set()
    regs = []
    for col, cells in _comps(g, _mode(g), D8):
        r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
        c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if h * w < 4:
            continue
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                if (y, x) not in taken:
                    taken.add((y, x))
                    regs.append(((r0, c0), (h, w, y - r0, x - c0), [(y, x)]))
    return regs


ROLE_SCHEMES = ([("part1", 1.0, lambda g: _roles_partition(g, 1)), ("part2", 1.05, lambda g: _roles_partition(g, 2)),
                 ("corner", 1.1, _roles_corner)]
                + [("quad%d" % k, 1.15 + 0.01 * k, (lambda g, k=k: _roles_quad(g, k))) for k in range(5)]
                + [("core", 1.2, _roles_core), ("relpos", 1.4, _roles_relpos)])


BIND_ORDER = ("marker", "dom", "bg")


def _binds(g):
    """Role colours of one grid -- the specialisation menu for colour values (see BINDINGS): bg = most frequent
    colour, dom = most frequent other colour, marker = rarest colour (None when the rank is tied)."""
    c = Counter(v for r in g for v in r)
    order = sorted(c.items(), key=lambda t: (-t[1], t[0]))
    rest = order[1:]
    dom = rest[0][0] if rest and (len(rest) == 1 or rest[1][1] != rest[0][1]) else None
    marker = rest[-1][0] if rest and (len(rest) == 1 or rest[-2][1] != rest[-1][1]) else None
    return {"bg": order[0][0], "dom": dom, "marker": marker}


def _role_value(pairs, B):
    """pairs: (input colour, output colour, pair index).  keep | const (the role overrides several input colours) |
    bind (the output colour varies across pairs and is the grid's role colour B[pi][name] every time) |
    map (input colour -> output colour per role, literal)."""
    if all(a == b for a, b, _ in pairs):
        return ('keep',)
    outs = {b for _, b, _ in pairs}
    if len(outs) == 1 and len({a for a, _, _ in pairs}) > 1:
        return ('const', outs.pop())
    if len(outs) > 1:
        for nm in BIND_ORDER:
            if all(b == B[pi][nm] for _, b, pi in pairs):
                return ('bind', nm)
    m = {}
    for a, b, _ in pairs:
        if m.setdefault(a, b) != b:
            return None
    return ('map', m)


def _paint(g, regs, table):
    out = [list(r) for r in g]
    B = None
    for inst, key, cells in regs:
        v = table.get(key)
        if v is None or v[0] == 'keep':
            continue
        if v[0] == 'bind':
            B = B or _binds(g)
            c = B[v[1]]
            if c is None:
                return None
        for y, x in cells:
            if v[0] == 'const':
                out[y][x] = v[1]
            elif v[0] == 'bind':
                out[y][x] = c
            else:
                out[y][x] = v[1].get(g[y][x], g[y][x])
    return out


def _role_programs(train):
    for p in train:
        if len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0]):
            return
    if all(p['input'] == p['output'] for p in train):
        return
    for name, cost, scheme in ROLE_SCHEMES:
        pairs, inst = {}, {}
        ok = True
        for pi, p in enumerate(train):
            I, O = p['input'], p['output']
            try:
                regs = scheme(I)
            except Exception:
                regs = None
            if not regs:
                ok = False
                break
            covered = set()
            for ins, key, cells in regs:
                for y, x in cells:
                    covered.add((y, x))
                    pairs.setdefault(key, []).append((I[y][x], O[y][x], pi))
                inst.setdefault(key, set()).add((pi, ins))
            if any(I[y][x] != O[y][x] and (y, x) not in covered
                   for y in range(len(I)) for x in range(len(I[0]))):
                ok = False
                break
        if not ok:
            continue
        table = {}
        B = [_binds(p['input']) for p in train]
        for key, pr in pairs.items():
            v = _role_value(pr, B)
            if v is None:
                ok = False
                break
            if v[0] != 'keep' and len(inst[key]) < 2:
                ok = False
                break
            table[key] = v
        if not ok or all(v[0] == 'keep' for v in table.values()):
            continue

        def fn(g, scheme=scheme, table=table):
            regs = scheme(g)
            if not regs:
                return None
            return _paint(g, regs, table)
        nmap = sum(1 for v in table.values() if v[0] == 'map' and len(v[1]) > 1)
        yield ("role_%s->paint" % name, cost + 0.05 * nmap, fn)


# ------------------------------------------------------------------------------------------------------ family
def fam(train):
    try:
        if not train or any(not p['input'] or not p['input'][0] for p in train):
            return
    except Exception:
        return
    cands = []
    for gen in (_grid_programs, _registration_programs, _panel_programs, _role_programs):
        try:
            for name, cost, fn in gen(train):
                cands.append((cost, len(cands), name, fn))
        except Exception:
            continue
    cands.sort(key=lambda t: (t[0], t[1]))
    n = 0
    for cost, _, name, fn in cands:
        try:
            if all(fn(p['input']) == p['output'] for p in train):
                yield (name, cost, fn)
                n += 1
                if n >= 3:
                    return
        except Exception:
            continue


FAMILIES = [fam]
