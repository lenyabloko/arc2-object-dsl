"""Prior family "learned_key_table", version 4 (test-blind; version 3 with every colour parameter re-parameterised over
the declared colour roles of colour_roles.py -- Fable v11 D38 / G68).

One generator, KEY -> TABLE -> EMIT: compute a discrete key for each unit of the input, look it up in a table that is
induced from the training pairs, and emit the stored value.  A unit is the whole grid, a panel of the grid (blocks
separated by empty lines) or a structural region / cell role (cell of a separator partition classified by its band
position, convex / concave corner of a 1-px outline, quadrant / inset / core of a solid rectangle, relative position
inside an object's bounding box).  The key is a whole-grid feature (binary mask, number of colours, a linked-by-path
predicate on a role colour, containment in the stored glyph), a panel's binary mask, or the role itself.  The value
is an output glyph whose every cell is a colour ROLE (resolved on the input it is emitted for), a role colour
(panel), or a cell recolouring (keep / role colour / role-to-role map).  No program stores a colour number.
Shared steps written once: background by role, component extraction, the role colours of a grid, the table
induction with consistency and sharing checks (a key that changes something must be seen at least twice),
nearest-mask / containment fallback for unseen keys, and the exact-fit verification.

Colour roles used (colour_roles.py, plus two role-bound values defined here and flagged):
  background(g, train), rank_colour(g, k) (k in 1, 2, 3, -1, -2), novel_colour(train);
  train_bg      = background() of the training inputs taken as one participant (the family's bg since v2; it is
                  the declared role applied to the training inputs -- defined in this family);
  vanish        = the single colour of colour_roles.vanishing_colours(train) (declared helper; None unless unique).

BINDINGS (G68) -- per member fitted by version 3: each former literal -> the role it became, or LOST.
  15663ba9  corner roles: convex 4, concave 2 -> LOST: needs literal 4 and 2 (two colours new in every output,
            novel_colour undefined; no input role equals either)
  22806e14  core -> rank_colour(g, -1) (marker, was bind 'marker');  free&marker cells keep-or-erase via literal map
            {8:7, 1:7, 3:3} -> LOST: needs literal map keys 8/1 vs 3 (the marker role erases in two pairs and keeps
            in the third)
  239be575  key linked(2) -> linked(vanish) (2 is the vanishing colour);  glyph [[8]] -> [[rank_colour(g, 1)]],
            glyph [[0]] -> [[background(g)]]
  269e22fb  glyph pose / palette <- the input's (participants);  literal fallback for atlas colours outside the
            bijection removed (every emitted colour is an input colour)
  272f95fa  band colours 2/4/6/3/1 -> LOST: needs literal 2, 4, 6, 3, 1 (separator 8 <- participant)
  27a28665  mask -> glyph colour 3/6/2/1 -> LOST: needs literal 3, 6, 2, 1 (output colour varies with the key)
  639f5a19  quadrant colours 6/1/2/3, inset 4 -> LOST: needs literal 6, 1, 2, 3, 4
  6e02f1e3  glyph colours 5 and 0 -> LOST: needs literal 5 and 0 (both new in every output: novel_colour undefined)
  9110e3c5  key dom (literal key colours 1/2/3) and glyph colour 8 -> LOST: needs literal key colours 1, 2, 3 and
            literal 8 (8 occurs in some inputs, so it is not novel_colour)
  941d9a10  band colours 1/2/3 -> LOST: needs literal 1, 2, 3
  995c5fa3  bg 'zero' -> rank_colour(g, 1);  row colours 8/2/4/3 by panel mask -> LOST: needs literal 8, 4, 3
            (only 2 is novel_colour)
  a834deea  digit per relative position -> LOST: needs literal 1..7, 9
  d4469b4b  key dom (literal key colours 1/2/3) -> LOST: needs literal key colours 1, 2, 3 (glyph 5 <- novel_colour,
            0 <- train_bg would be expressible)
  e9c9d9a1  band colours 2/4/1/8, inner 7 -> LOST: needs literal 2, 4, 1, 8, 7
  ed74f2f2  panel mask -> colour 1/3/2 -> LOST: needs literal 1, 3, 2
  Not fitted in version 3 either: 9caba7c3.
Removed literal paths (G68): the 'dom' and 'colset' grid keys (tables keyed by stored colour numbers); linked(c)
over literal common input colours (now c in {vanish, rank_colour(g, k)}); literal output glyphs (now role templates);
the literal panel background 'zero' (now background(g) | rank_colour(g, 1)); literal panel / paint colours (now
roles); literal const and per-colour maps (now role and role-to-role maps); the atlas colour fallback.
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_learned_key_table"
CONCEPT = "learned_key_table"
MEMBERS = ["15663ba9", "22806e14", "239be575", "269e22fb", "272f95fa", "27a28665", "639f5a19", "6e02f1e3",
           "9110e3c5", "941d9a10", "995c5fa3", "9caba7c3", "a834deea", "d4469b4b", "e9c9d9a1", "ed74f2f2"]
READING = {
    "generator": "Compute a discrete key per unit (the whole grid: binary mask, colour count or a linked-by-path "
                 "predicate on a role colour; each panel: its binary mask; each region/cell: its structural "
                 "role in a separator partition, a 1-px outline, a solid rectangle or an object's bounding box), look "
                 "it up in a table induced from the training pairs, and emit the stored role glyph resolved on the "
                 "input (in the input's pose and palette when the key is containment), the stored role colour "
                 "(as one row per panel or painted onto the other panel's ink), or paint each role's cells with its "
                 "stored role colour.",
    "stop": "One lookup per unit; every unit is emitted once; cells without a role are left unchanged; an unseen "
            "mask key falls back to the nearest stored mask, any other unseen key keeps the cell (role) or fails.",
    "params": "unit ∈ {grid, panel, role} · key ∈ {mask, ncol, linked(c ∈ {vanish, rank_k}, conn∈{4,8}), "
              "contained(sym∈{id,D4}, palette∈{fixed,perm}), panelmask, part1, part2, corner, quad(k∈{0..4} | "
              "k←core), relpos} · value ∈ {glyph (role template | pose/palette ← input), role colour, keep, "
              "role, role map} · role ∈ {background, train_bg, novel, rank_k (k ∈ 1,2,3,-1,-2)} · "
              "emit ∈ {glyph, rows(w∈{k,const}), paint_other(p∈{0,1}), paint_cells} · axis ∈ {v, h} · "
              "bg ∈ {train_bg, background, rank1}",
    "participants": "bg = most frequent colour (grid or all training inputs); separators = full rows and full "
                    "columns of one colour; panels = maximal runs of non-empty columns (rows) cropped to the inked "
                    "rows; objects = same-colour 4-/8-connected non-background components; solid rectangles = "
                    "components filling their bounding box; outline corners = cells with exactly two same-colour "
                    "4-neighbours at a right angle, convex when the bend points into the enclosed area; "
                    "role colours of a grid: background, rank_colour(k) (k = 1 dom, k = -1 marker), novel, train_bg, vanish; "
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
    return CR.background(g)


def _train_bg(train):
    """train_bg: the declared background role applied to the training inputs taken as one participant."""
    return CR.background([r for p in train for r in p['input']])


# ------------------------------------------------------------------------------------- colour roles (G68)
EMIT_ROLES = (("background",), ("train_bg",), ("novel",), ("rank", 1), ("rank", 2), ("rank", 3), ("rank", -1),
              ("rank", -2))
VALUE_ROLES = (("novel",), ("rank", -1), ("rank", 1), ("background",), ("rank", 2), ("rank", 3), ("rank", -2),
               ("train_bg",))
KEY_ROLES = (("background",), ("rank", 1), ("rank", 2), ("rank", 3), ("rank", -1), ("rank", -2))
LINK_ROLES = (("vanish",), ("rank", 1), ("rank", 2), ("rank", 3), ("rank", -1), ("rank", -2))


def _rname(role):
    return role[0] if len(role) == 1 else "%s%d" % role


def _consts(train):
    """Role colours fixed by the training pairs (constants at prediction time, each named by its role)."""
    van = CR.vanishing_colours(train)
    return {"train": train, "train_bg": _train_bg(train), "novel": CR.novel_colour(train),
            "vanish": next(iter(van)) if len(van) == 1 else None}


def _rc(g, C, bg=None):
    """Role colours of grid g: {role: colour or None}; ranks are counted against bg (default background(g))."""
    if bg is None:
        bg = CR.background(g, C["train"])
    d = {("background",): bg, ("train_bg",): C["train_bg"], ("novel",): C["novel"], ("vanish",): C["vanish"]}
    for k in CR.RANKS:
        d[("rank", k)] = CR.rank_colour(g, k, bg)
    return d


def _first_role(roles, obs):
    """obs: [(role colours of a grid, observed colour)] -> the first role naming the observed colour every time."""
    for r in roles:
        if all(R[r] is not None and R[r] == c for R, c in obs):
            return r
    return None


def _template(outs, Rs):
    """Output glyphs sharing a key -> the glyph as a grid of roles (each cell: the first EMIT role whose colour is
    the cell's colour in every one of them), or None."""
    h, w = len(outs[0]), len(outs[0][0])
    if any(len(o) != h or len(o[0]) != w for o in outs):
        return None
    memo, rows = {}, []
    for i in range(h):
        row = []
        for j in range(w):
            cs = tuple(o[i][j] for o in outs)
            if cs not in memo:
                memo[cs] = _first_role(EMIT_ROLES, list(zip(Rs, cs)))
            if memo[cs] is None:
                return None
            row.append(memo[cs])
        rows.append(tuple(row))
    return tuple(rows)


def _emit(tpl, R):
    out = []
    for row in tpl:
        r = [R[x] for x in row]
        if None in r:
            return None
        out.append(r)
    return out


def _groups(items):
    """items: (key, payload) -> {key: [payloads]}, or None when a key is undefined or no key is shared."""
    g = {}
    for k, v in items:
        if k is None:
            return None
        g.setdefault(k, []).append(v)
    if not g or len(g) >= len(items):
        return None
    return g


def _induce_roles(items, Rs, roles=EMIT_ROLES):
    """items: (key, pair index, colour) -> {key: role} (the first role naming the colour of every item of the key),
    or None."""
    g = _groups([(k, (pi, c)) for k, pi, c in items])
    if g is None:
        return None
    table = {}
    for k, lst in g.items():
        r = _first_role(roles, [(Rs[pi], c) for pi, c in lst])
        if r is None:
            return None
        table[k] = r
    return table


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


def _grid_keys(train, bg, C):
    """Whole-grid keys.  Version 3's 'dom' and 'colset' keys looked stored colour numbers up in the table; they are
    removed (G68).  linked(c): c is a role colour (vanish, rank_colour(g, k) against bg), defined on every
    training input; roles naming the same colours on every training input are tried once."""
    keys = [("ncol", 1.0, False, lambda g: len({v for r in g for v in r}))]
    seen = set()
    for role in LINK_ROLES:
        sig = tuple(_rc(p['input'], C, bg)[role] for p in train)
        if None in sig or bg in sig or sig in seen:
            continue
        seen.add(sig)
        for cn, nb in (("8", D8), ("4", D4)):
            keys.append(("linked_%s_%s" % (_rname(role), cn), 1.3, False,
                         lambda g, role=role, nb=nb: _linked(g, bg, _rc(g, C, bg)[role], nb)))
    keys.append(("mask", 1.5, True, lambda g: _mask(g, bg)))
    return keys


def _grid_programs(train, C):
    bg = C["train_bg"]
    outs = {tuple(map(tuple, p['output'])) for p in train}
    if len(outs) < 2:
        return
    Rs = [_rc(p['input'], C) for p in train]
    for name, cost, is_mask, key in _grid_keys(train, bg, C):
        try:
            groups = _groups([(key(p['input']), pi) for pi, p in enumerate(train)])
        except Exception:
            groups = None
        if groups is None:
            continue
        table = {}
        for k, pis in groups.items():
            t = _template([train[pi]['output'] for pi in pis], [Rs[pi] for pi in pis])
            if t is None:
                table = None
                break
            table[k] = t
        if table is None or len(set(table.values())) < 2:
            continue

        def fn(g, key=key, table=table, is_mask=is_mask):
            t = _lookup(table, key(g), is_mask)
            return None if t is None else _emit(t, _rc(g, C))
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
    of it, emitted in that pose and palette -- pose <- the input's pose, palette <- the input's colours.  Every
    colour of the emitted glyph must be an input colour (bound through the window); version 3's fallback that
    emitted an unbound atlas colour literally is removed."""
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
                            fwd[a] = b
                        elif fwd.setdefault(a, b) != b or bwd.setdefault(b, a) != a:
                            ok = False
                            break
                    if not ok:
                        break
                if ok and all(v in fwd for r in q for v in r):
                    return [[fwd[v] for v in r] for r in q]
    return None


def _registration_programs(train, C):
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


def _panel_programs(train, C):
    tbg = C["train_bg"]
    Rs = [_rc(p['input'], C) for p in train]
    # panel background: train_bg (version 3 'mode'), then the roles that replace the literal 'zero'
    opts, seen = [("mode", lambda g: tbg)], {tuple(tbg for _ in train)}
    for role in (("background",), ("rank", 1)):
        bgr = (lambda g, role=role: _rc(g, C)[role])
        sig = tuple(R[role] for R in Rs)
        if None in sig or sig in seen:
            continue
        seen.add(sig)
        opts.append((_rname(role), bgr))
    for bgname, bgf in opts:
        for axis in ('v', 'h'):
            try:
                P = [_panels(p['input'], bgf(p['input']), axis) for p in train]
            except Exception:
                continue
            if any(len(ps) < 2 for ps in P):
                continue
            # emit = rows: one uniform row per panel, in panel order; row colour <- the role stored for the mask
            items, ok = [], True
            for pi, (p, ps) in enumerate(zip(train, P)):
                o = p['output']
                if len(o) != len(ps) or any(len(set(r)) != 1 for r in o):
                    ok = False
                    break
                bg = bgf(p['input'])
                items += [(_mask(q, bg), pi, r[0]) for q, r in zip(ps, o)]
            table = _induce_roles(items, Rs) if ok else None
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
                        R = _rc(g, C)
                        roles = [_lookup(table, _mask(q, bg), True) for q in ps]
                        if not roles or None in roles:
                            return None
                        cols = [R[r] for r in roles]
                        if None in cols:
                            return None
                        w = len(cols) if wm == 'k' else wm
                        return [[c] * w for c in cols]
                    yield ("panel_mask->colour_rows_%s_%s_%s" % (axis, bgname, wm), 1.2, fn)
            # emit = paint_other: key panel p selects the role colour of the other panel's ink
            if any(len(ps) != 2 for ps in P):
                continue
            for kp in (0, 1):
                items, ok = [], True
                for pi, (p, ps) in enumerate(zip(train, P)):
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
                    items.append((_mask(ps[kp], bg), pi, cs.pop()))
                table = _induce_roles(items, Rs) if ok else None
                if table is None or len(set(table.values())) < 2:
                    continue

                def fn(g, table=table, kp=kp, axis=axis, bgf=bgf):
                    bg = bgf(g)
                    ps = _panels(g, bg, axis)
                    if len(ps) != 2:
                        return None
                    rl = _lookup(table, _mask(ps[kp], bg), True)
                    c = None if rl is None else _rc(g, C)[rl]
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
    role ('free', colour is the grid's marker colour = rank_colour(g, -1))."""
    bg = _mode(g)
    mk = CR.rank_colour(g, -1, bg)
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


def _role_value(pairs, Rs):
    """pairs: (input colour, output colour, pair index); Rs: role colours of each training input.
    keep | role (the first VALUE role whose colour is the output colour of every cell of the role, in its pair;
    replaces version 3's literal const and bind) | role map (key = the first KEY role naming the cell's input colour
    in its pair, value = keep or a VALUE role; replaces version 3's literal per-colour map)."""
    if all(a == b for a, b, _ in pairs):
        return ('keep',)
    r = _first_role(VALUE_ROLES, [(Rs[pi], b) for _, b, pi in pairs])
    if r is not None:
        return ('role', r)
    groups = {}
    for a, b, pi in pairs:
        kr = next((k for k in KEY_ROLES if Rs[pi][k] == a), None)
        if kr is None:
            return None
        groups.setdefault(kr, []).append((a, b, pi))
    m = []
    for kr in KEY_ROLES:
        if kr not in groups:
            continue
        lst = groups[kr]
        if all(a == b for a, b, _ in lst):
            m.append((kr, ('keep',)))
            continue
        vr = _first_role(VALUE_ROLES, [(Rs[pi], b) for _, b, pi in lst])
        if vr is None:
            return None
        m.append((kr, ('role', vr)))
    return ('map', tuple(m))


def _paint(g, regs, table, C):
    out = [list(r) for r in g]
    R = None
    for inst, key, cells in regs:
        v = table.get(key)
        if v is None or v[0] == 'keep':
            continue
        R = R or _rc(g, C)
        if v[0] == 'role':
            c = R[v[1]]
            if c is None:
                return None
            for y, x in cells:
                out[y][x] = c
            continue
        m = dict(v[1])
        for y, x in cells:
            a = g[y][x]
            kr = next((k for k in KEY_ROLES if R[k] == a), None)
            w = m.get(kr)
            if w is None or w[0] == 'keep':
                continue
            c = R[w[1]]
            if c is None:
                return None
            out[y][x] = c
    return out


def _role_programs(train, C):
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
        B = [_rc(p['input'], C) for p in train]
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
            return _paint(g, regs, table, C)
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
    C = _consts(train)
    for gen in (_grid_programs, _registration_programs, _panel_programs, _role_programs):
        try:
            for name, cost, fn in gen(train, C):
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
