"""Prior family (priors3, Fable v10b T65 / G68): LEGEND_LOOKUP_SUBSTITUTION -- read a key->value table from an
in-grid legend, apply it to the field.  Second pass: parameters specialised over FITTED BINDINGS (test-blind).

BINDINGS (fitted members of the priors2 version; every induced value with the role that explains it)
  58743b76  corner          key image    <- grid cells outside the field rectangle (field = bbox of bg cells)
                            block count  <- key image cell count;  block size <- field size / key size
                            colour       <- key[cell's block index];  objects <- non-bg field cells
  5a5a2103  lattice[rows]   separator    <- colour of the full lines;  panel size <- lattice period
                            key colour   <- the band's KEY PANEL colour; key panel = column 0 (literal index) --
                                            role: the only panel column whose panels each hold exactly one colour
                            glyph        <- union of the masks in the other panels
  5adee1b2  entries halo    key colour   <- legend part whose colour also occurs in the field
                            value colour <- the partner part's colour;  halo <- bg reachable in object bbox + 1
  9356391f  header rings    separator    <- first full uniform row;  list <- header cells in reading order
                            ring k colour<- list[k];  layer index k <- Chebyshev distance to the seed
                            seed         <- field cells of colour list[0];  strike colour <- separator colour
  a406ac07  cross           key row/col  <- the full non-bg lines on two meeting borders (role, not H-1 / W-1)
                            colour       <- row label when row label == column label
  c64f1187  entries glyph   glyph        <- the legend partner's shape;  ink <- key colour
                            anchor       <- glyph corner opposite the marker side;  crop <- field bbox
  d59b0160  fenced erase    key set      <- colours inside the L-fenced corner box;  bg <- largest region colour
                            erased docs  <- documents whose colour set contains the key set
  dfadab01  entries glyph   glyph        <- training-output patch at the training legends' frame (learn=1)
                            ink          <- the glyph's own colours
Specialisation menu built from these bindings (alternatives added to the parameter domains, originals kept first):
  lattice key panel  in {first (literal index 0), mono (the panel column whose panels each hold one colour)}
  key line           in {border (cross), framed (the line beside a full uniform frame line)}: label <- position
  act on positional match  in {recolour (cross), route (keyline): match -> line next to the frame, else far edge}
  list source        in {header (above the separator), loose (cells of colours other than bg and the object's)}
  layer index        in {ring (Chebyshev distance to the seed), L (depth of the nested L from the object's lead
                         corner, arm = the object's top width)};  cycle in {0 (header), 1 (list repeats)}

One generator, SUBSTITUTE(objects; table; act):
  legend   where the table is written, and what its keys are:
             entries  -- colour pairs / marker+glyph entries: 8-connected components made of exactly two colours whose
                         two colour parts lie side by side (disjoint bounding boxes).  Key = the part whose colour also
                         occurs in the field (else the smaller part); value = the other part (its colour, or its
                         shape = a glyph, placed relative to the key cell).
             corner   -- a key image in the corner left over by the field rectangle (field = bounding box of the
                         background cells); key = position, the field is cut into as many equal blocks as the key has
                         cells.
             cross    -- a key row and a key column on two meeting grid borders; key = (row label, column label).
             lattice  -- a lattice of separator lines cuts the grid into equal panels; the first panel of every band
                         carries the band's key colour; key = band index; the shared glyph = union of the other
                         panels' masks.
             fenced   -- a corner box closed off by an edge-to-edge L of one colour; key = the set of colours in it.
             header   -- a header list above (or left of) a full separator line; key = list index k, value = the
                         colour of ring k (Chebyshev distance k) around each seed.
  objects  per legend: field cells / same-colour components / key cells / panels / background-separated documents.
  act      recolour (object -> value colour) | halo (background reachable from the object's 1-padded box -> value
           colour) | glyph (object -> value glyph, ink = its own colours or the key colour, anchored with the key cell
           at the glyph corner opposite the legend's marker side, or at the legend's own offset) | erase (object ->
           background when its colours match the key set) | rings (header list drawn as concentric rings; entries
           whose ring is clipped may be struck out with the separator colour).
  The shared loop: parse legend -> table; for each field object: key -> lookup -> paint value; optionally clear the
  canvas, drop the legend, crop to the field.  Keys absent from a grid's legend may come from a table induced from the
  training outputs (same glyph frame as the training legends).
"""
from collections import Counter

CARD = "prior3_legend_lookup_substitution"
CONCEPT = "legend_lookup_substitution"
MEMBERS = ["15660dd6", "3e6067c3", "58743b76", "5a5a2103", "5adee1b2", "65b59efc", "7d7772cc", "9356391f",
           "a406ac07", "b0039139", "b20f7c8b", "b457fec5", "c64f1187", "d59b0160", "dfadab01", "e87109e9"]
READING = {
    "generator": "Locate the legend (side-by-side colour pairs / marker+glyph entries, a corner key image beside the "
                 "field rectangle, a key row and key column on meeting borders, the first panel of each band of a "
                 "separator lattice, an L-fenced corner box, or a header list above a separator line), parse it into a key->value table (key = colour, "
                 "position, band or colour set; value = colour, glyph or ring order), and substitute every field "
                 "object by the value of its key (recolour, halo-fill, stamp the glyph, erase, or draw rings), dropping the legend / cropping "
                 "to the field when the outputs do.",
    "stop": "single pass over the field objects; objects whose key is not in the table stay (or vanish on a cleared "
            "canvas)",
    "params": "legend in {entries, corner, cross, lattice, fenced, header} . "
              "act in {recolour, halo, glyph, erase, rings} . strike in {0,1} . "
              "ink in {own, key} . anchor in {opposite, same} . canvas in {keep, clear} . drop_legend in {0,1} . "
              "crop in {0,1} . learn in {0,1} . axis in {rows, cols} . match in {any, all, none, notall}",
    "participants": "background = most common colour (fenced: colour of the largest single-colour region); legend "
                    "and table per `legend`; objects = field cells / mono 8-components / key cells / panels / "
                    "4-connected documents",
    "preconditions": "a legend of the chosen kind parses in every training input with a non-empty table; corner: "
                     "field size divisible by key size; output shape equals input shape, except crop (field bbox)",
}

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


# ------------------------------------------------------------------------------------------------ helpers
def _bg(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _comps(g, ok, nb):
    """Connected components of cells with ok(r, c); `ok` may be colour-sensitive through `link`."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or not ok(i, j):
                continue
            seen[i][j] = True
            st, cells = [(i, j)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and ok(x, y):
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _mono(g, bg, nb=N8):
    """Same-colour components of non-background cells."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            c = g[i][j]
            seen[i][j] = True
            st, cells = [(i, j)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == c:
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _bbox(cells):
    rs = [a for a, _ in cells]
    cs = [b for _, b in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _T(g):
    return [list(r) for r in zip(*g)]


# ------------------------------------------------------------------------------------------------ legend: entries
def _entries(g, bg):
    """Side-by-side two-colour entries.  -> (legend cells, {key colour: entry}) or None.
    entry = (key cells, value colour, value cells [(r, c, colour)], value bbox)."""
    comps = _comps(g, lambda a, b: g[a][b] != bg, N8)
    cand = []
    for cells in comps:
        parts = {}
        for a, b in cells:
            parts.setdefault(g[a][b], []).append((a, b))
        if len(parts) != 2:
            continue
        (c1, p1), (c2, p2) = sorted(parts.items())
        b1, b2 = _bbox(p1), _bbox(p2)
        if not (b1[1] < b2[0] or b2[1] < b1[0] or b1[3] < b2[2] or b2[3] < b1[2]):
            continue
        cand.append((cells, (c1, p1, b1), (c2, p2, b2)))
    if not cand:
        return None
    leg = set()
    for cells, _, _ in cand:
        leg.update(cells)
    H, W = len(g), len(g[0])
    field_cols = Counter(g[i][j] for i in range(H) for j in range(W) if g[i][j] != bg and (i, j) not in leg)
    table = {}
    for cells, A, B in cand:
        ina, inb = A[0] in field_cols, B[0] in field_cols
        if ina != inb:
            key, val = (A, B) if ina else (B, A)
        elif len(A[1]) != len(B[1]):
            key, val = (A, B) if len(A[1]) < len(B[1]) else (B, A)
        else:
            continue
        ent = (key[1], val[0], [(a, b, g[a][b]) for a, b in val[1]], val[2])
        if key[0] in table:
            old = table[key[0]]
            if old[1] != ent[1] or len(old[2]) != len(ent[2]):
                return None
            continue
        table[key[0]] = ent
    if not table:
        return None
    return leg, table


def _glyph_of(ent, anchor):
    """Entry -> glyph placement rule: (dr0, dc0, cells [(dr, dc, colour)]) relative to the key cell, or None."""
    kc, _, vcells, (r0, r1, c0, c1) = ent
    if len(kc) != 1:
        return None
    mr, mc = kc[0]
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if anchor == 'same':
        top, left = r0 - mr, c0 - mc
    else:
        if mr < r0:
            top = -(h - 1)
        elif mr > r1:
            top = 0
        else:
            top = r0 - mr
        if mc < c0:
            left = -(w - 1)
        elif mc > c1:
            left = 0
        else:
            left = c0 - mc
    return (top, left, [(a - r0, b - c0, v) for a, b, v in vcells], h, w)


def _frames(train, anchor):
    """Unique glyph frame (top, left, h, w) of the training legends' glyph entries, or None."""
    fr = set()
    for p in train:
        e = _entries(p["input"], _bg(p["input"]))
        if e is None:
            continue
        for ent in e[1].values():
            gl = _glyph_of(ent, anchor)
            if gl is not None:
                fr.add((gl[0], gl[1], gl[3], gl[4]))
    return fr.pop() if len(fr) == 1 else None


def _marker_colours(g, bg):
    sizes = {}
    for cells in _mono(g, bg):
        sizes.setdefault(g[cells[0][0]][cells[0][1]], set()).add(len(cells))
    return {c for c, s in sizes.items() if s == {1}}


def _learn(train, anchor, frame):
    """Glyphs for key colours missing from a grid's legend, read off the training outputs at the training frame."""
    top, left, h, w = frame
    key = {}
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        bg = _bg(gi)
        e = _entries(gi, bg)
        leg, table = e if e is not None else (set(), {})
        H, W = len(gi), len(gi[0])
        for col in _marker_colours(gi, bg) - set(table):
            for i in range(H):
                for j in range(W):
                    if gi[i][j] != col or (i, j) in leg:
                        continue
                    r0, c0 = i + top, j + left
                    if r0 < 0 or c0 < 0 or r0 + h > H or c0 + w > W:
                        continue
                    patch = tuple((a, b, go[r0 + a][c0 + b]) for a in range(h) for b in range(w)
                                  if go[r0 + a][c0 + b] != bg)
                    if key.get(col, patch) != patch:
                        return None
                    key[col] = patch
    return {c: (top, left, list(v), h, w) for c, v in key.items()}


def _run_entries(g, act, ink, anchor, canvas, drop, crop, learned):
    bg = _bg(g)
    e = _entries(g, bg)
    if e is None:
        if not learned:
            return None
        leg, table = set(), {}
    else:
        leg, table = e
    H, W = len(g), len(g[0])
    out = [[bg] * W for _ in range(H)] if canvas == 'clear' else [row[:] for row in g]
    if drop and canvas != 'clear':
        for a, b in leg:
            out[a][b] = bg
    if act == 'glyph':
        glyphs = dict(learned or {})
        for col, ent in table.items():
            gl = _glyph_of(ent, anchor)
            if gl is None:
                return None
            if ink == 'key':
                gl = (gl[0], gl[1], [(a, b, col) for a, b, _ in gl[2]], gl[3], gl[4])
            glyphs[col] = gl
        if not glyphs:
            return None
        for i in range(H):
            for j in range(W):
                col = g[i][j]
                if (i, j) in leg or col not in glyphs:
                    continue
                top, left, cells, _, _ = glyphs[col]
                if canvas != 'clear':
                    out[i][j] = bg
                for a, b, v in cells:
                    x, y = i + top + a, j + left + b
                    if 0 <= x < H and 0 <= y < W:
                        out[x][y] = v
    else:
        objs = [c for c in _mono(g, bg) if not leg.intersection(c) and g[c[0][0]][c[0][1]] in table]
        if not objs:
            return None
        for cells in objs:
            v = table[g[cells[0][0]][cells[0][1]]][1]
            if act == 'recolour':
                for a, b in cells:
                    out[a][b] = v
            else:  # halo
                r0, r1, c0, c1 = _bbox(cells)
                r0, r1, c0, c1 = max(0, r0 - 1), min(H - 1, r1 + 1), max(0, c0 - 1), min(W - 1, c1 + 1)
                st = [(a, b) for a in range(r0, r1 + 1) for b in range(c0, c1 + 1)
                      if (a in (r0, r1) or b in (c0, c1)) and g[a][b] == bg]
                seen = set(st)
                while st:
                    a, b = st.pop()
                    out[a][b] = v
                    for da, db in N4:
                        x, y = a + da, b + db
                        if r0 <= x <= r1 and c0 <= y <= c1 and (x, y) not in seen and g[x][y] == bg:
                            seen.add((x, y))
                            st.append((x, y))
    if crop:
        fc = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg and (i, j) not in leg]
        if not fc:
            return None
        r0, r1, c0, c1 = _bbox(fc)
        out = [row[c0:c1 + 1] for row in out[r0:r1 + 1]]
    return out


# ------------------------------------------------------------------------------------------------ legend: corner
def _run_corner(g):
    """Key image in the corner beside the field rectangle; field cells recoloured by their block's key colour."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    rows = [i for i in range(H) if bg in g[i]]
    cols = [j for j in range(W) if any(g[i][j] == bg for i in range(H))]
    r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]
    kr = list(range(0, r0)) or list(range(r1 + 1, H))
    kc = list(range(0, c0)) or list(range(c1 + 1, W))
    if not kr or not kc or (r0 and r1 < H - 1) or (c0 and c1 < W - 1):
        return None
    key = [[g[i][j] for j in kc] for i in kr]
    kh, kw = len(key), len(key[0])
    fh, fw = r1 - r0 + 1, c1 - c0 + 1
    if fh % kh or fw % kw or any(v == bg for row in key for v in row):
        return None
    out = [row[:] for row in g]
    for i in range(r0, r1 + 1):
        for j in range(c0, c1 + 1):
            if g[i][j] != bg:
                out[i][j] = key[(i - r0) * kh // fh][(j - c0) * kw // fw]
    return out


# ------------------------------------------------------------------------------------------------ legend: cross
def _run_cross(g):
    """Key row and key column on meeting borders; a field cell takes the label shared by its row and column."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    for kr in (H - 1, 0):
        for kc in (W - 1, 0):
            if bg in g[kr] or any(g[i][kc] == bg for i in range(H)):
                continue
            out = [row[:] for row in g]
            for r in range(H):
                if r == kr:
                    continue
                for c in range(W):
                    if c != kc and g[r][kc] == g[kr][c]:
                        out[r][c] = g[r][kc]
            return out
    return None


# ------------------------------------------------------------------------------------------------ legend: lattice
def _spans(idx, n):
    out, prev = [], -1
    for k in idx + [n]:
        if k - prev > 1:
            out.append((prev + 1, k))
        prev = k
    return out


def _run_lattice(g, key='first'):
    """Separator lattice; key panel of each band = band key colour; every panel := shared glyph in the key colour.
    key: 'first' = panel column 0; 'mono' = the unique panel column whose panels each hold exactly one colour."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    rows = [i for i in range(H) if g[i][0] != bg and all(v == g[i][0] for v in g[i])]
    cols = [j for j in range(W) if g[0][j] != bg and all(g[i][j] == g[0][j] for i in range(H))]
    if not cols:
        return None
    s = g[0][cols[0]]
    if any(g[i][0] != s for i in rows) or any(g[0][j] != s for j in cols):
        return None
    rs, cs = _spans(rows, H), _spans(cols, W)
    if len(cs) < 2:
        return None
    ch, cw = rs[0][1] - rs[0][0], cs[0][1] - cs[0][0]
    if any(b - a != ch for a, b in rs) or any(b - a != cw for a, b in cs):
        return None
    def pcol(a0, a1, b0, b1):
        return {g[i][j] for i in range(a0, a1) for j in range(b0, b1)} - {bg}
    if key == 'first':
        kj = 0
    else:
        ks = [j for j, (b0, b1) in enumerate(cs) if all(len(pcol(a0, a1, b0, b1)) == 1 for a0, a1 in rs)]
        if len(ks) != 1:
            return None
        kj = ks[0]
    table = {}
    for k, (a0, a1) in enumerate(rs):
        cl = pcol(a0, a1, cs[kj][0], cs[kj][1])
        if len(cl) != 1:
            return None
        table[k] = cl.pop()
    glyph = set()
    for a0, a1 in rs:
        for pj, (b0, b1) in enumerate(cs):
            if pj == kj:
                continue
            for i in range(a0, a1):
                for j in range(b0, b1):
                    if g[i][j] != bg:
                        glyph.add((i - a0, j - b0))
    if not glyph:
        return None
    out = [row[:] for row in g]
    for k, (a0, a1) in enumerate(rs):
        for b0, b1 in cs:
            for i in range(a0, a1):
                for j in range(b0, b1):
                    out[i][j] = table[k] if (i - a0, j - b0) in glyph else bg
    return out


def _run_lattice_cols(g, key='first'):
    r = _run_lattice(_T(g), key)
    return None if r is None else _T(r)


# ------------------------------------------------------------------------------------------------ legend: keyline
def _orient(g, k):
    """k in 0..3: identity, flip rows, transpose, transpose+flip; returns (grid, inverse map)."""
    if k == 0:
        return g, lambda o: o
    if k == 1:
        return g[::-1], lambda o: o[::-1]
    if k == 2:
        return _T(g), _T
    return _T(g)[::-1], lambda o: _T(o[::-1])


def _keyline_rows(g, near_on_match):
    """Key line = the line just below a full uniform frame row L whose colour is absent above it (the open region).
    Label of an open-region cell <- the key line at its column (position key, as in `cross`).  act route: a cell
    moves along its column to the line next to the frame when (colour == label) == near_on_match, else to the far
    edge of the open region."""
    H, W = len(g), len(g[0])
    for L in range(1, H - 1):
        fc = g[L][0]
        if any(v != fc for v in g[L]):
            continue
        if any(fc in g[r] for r in range(L)) or not any(fc in g[r] for r in range(L + 1, H)):
            continue
        cnt = Counter(v for r in range(L) for v in g[r])
        bg = max(sorted(cnt), key=lambda c: cnt[c])
        key = g[L + 1]
        movers = [(r, c, g[r][c]) for r in range(L) for c in range(W) if g[r][c] != bg]
        if not movers:
            continue
        out = [row[:] for row in g]
        for r in range(L):
            out[r] = [bg] * W
        for r, c, v in movers:
            out[L - 1 if (v == key[c]) == near_on_match else 0][c] = v
        return out
    return None


def _run_keyline(g, near_on_match):
    for k in range(4):
        h, back = _orient([list(r) for r in g], k)
        o = _keyline_rows(h, near_on_match)
        if o is not None:
            return back(o)
    return None


# ------------------------------------------------------------------------------------------------ legend: list layers
def _loose_list(g, bg, obj_col):
    """List source 'loose': cells whose colour is neither bg nor the object colour, read in reading order."""
    return [v for row in g for v in row if v != bg and v != obj_col]


def _L_layers(cells, lst):
    """Layer index <- depth of the nested L from the object's lead corner (top row's first cell, the object leaning
    down-right); arm = the object's top width.  Colour of layer k = lst[k mod n]; cells past the last complete L
    keep that L's colour."""
    top = min(r for r, _ in cells)
    toprow = sorted(c for r, c in cells if r == top)
    r0, c0, T = top, toprow[0], len(toprow)
    col, last, k = {}, None, 0
    while True:
        L = [(r0 + k, c0 + k + j) for j in range(T)] + [(r0 + k + i, c0 + k) for i in range(1, T)]
        if not all(p in cells for p in L):
            break
        last = lst[k % len(lst)]
        for p in L:
            col[p] = last
        k += 1
    if last is None:
        return None
    for p in cells:
        if p not in col:
            col[p] = last
    return col


def _run_list_L(g):
    """Legend = loose list; objects = same-colour 4-components of the dominant non-bg colour; layer = L depth (the
    lead corner is mirrored when the object leans down-left); cycle = 1."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    cnt = Counter(v for row in g for v in row if v != bg)
    if len(cnt) < 2:
        return None
    oc = max(sorted(cnt), key=lambda c: cnt[c])
    lst = _loose_list(g, bg, oc)
    if not lst:
        return None
    out = [row[:] for row in g]
    objs = [c for c in _mono(g, bg, N4) if g[c[0][0]][c[0][1]] == oc]
    for cells in objs:
        top, bot = min(r for r, _ in cells), max(r for r, _ in cells)
        tm = sum(c for r, c in cells if r == top) / float(sum(1 for r, _ in cells if r == top))
        bm = sum(c for r, c in cells if r == bot) / float(sum(1 for r, _ in cells if r == bot))
        mir = bm < tm
        norm = set((r, W - 1 - c) if mir else (r, c) for r, c in cells)
        col = _L_layers(norm, lst)
        if col is None:
            return None
        for (r, c), v in col.items():
            out[r][W - 1 - c if mir else c] = v
    return out


# ------------------------------------------------------------------------------------------------ legend: fenced
def _region_bg(g):
    H, W = len(g), len(g[0])
    best, bg = -1, None
    for cells in _mono(g, None, N4):
        if len(cells) > best:
            best, bg = len(cells), g[cells[0][0]][cells[0][1]]
    return bg


def _fenced(g, bg):
    """Unique corner box closed by an edge-to-edge L of one colour -> (box cells, key colours)."""
    H, W = len(g), len(g[0])
    found = set()
    for fr in (0, 1):
        for fc in (0, 1):
            R = (lambda i: H - 1 - i) if fr else (lambda i: i)
            C = (lambda j: W - 1 - j) if fc else (lambda j: j)
            for r in range(1, H - 1):
                for s in range(1, W - 1):
                    col = g[R(r)][C(s)]
                    if col == bg:
                        continue
                    L = {(R(r), C(j)) for j in range(s + 1)} | {(R(i), C(s)) for i in range(r + 1)}
                    if any(g[a][b] != col for a, b in L):
                        continue
                    if any(0 <= R(r) + da < H and 0 <= C(s) + db < W and g[R(r) + da][C(s) + db] == col and
                           (R(r) + da, C(s) + db) not in L for da, db in ((1 - 2 * fr, 0), (0, 1 - 2 * fc))):
                        continue
                    inner = {(R(i), C(j)) for i in range(r) for j in range(s)}
                    if any(g[a][b] == col for a, b in inner):
                        continue
                    keys = {g[a][b] for a, b in inner} - {bg, col}
                    if keys:
                        found.add((frozenset(L | inner), frozenset(keys)))
    return found.pop() if len(found) == 1 else None


_MATCH = {
    'all': lambda K, P: K <= P,
    'any': lambda K, P: bool(K & P),
    'none': lambda K, P: not (K & P),
    'notall': lambda K, P: not (K <= P),
}


def _run_fenced(g, match):
    bg = _region_bg(g)
    leg = _fenced(g, bg)
    if leg is None:
        return None
    box, keys = leg
    pred = _MATCH[match]
    out = [row[:] for row in g]
    for doc in _comps(g, lambda a, b: g[a][b] != bg and (a, b) not in box, N4):
        if pred(keys, {g[a][b] for a, b in doc}):
            for a, b in doc:
                out[a][b] = bg
    return out


# ------------------------------------------------------------------------------------------------ legend: header
def _run_header(g, strike):
    """Header list above the first full separator row: entry k = colour of ring k (Chebyshev distance k) around
    every seed of the field; strike: entries whose ring does not fit in the field are overwritten by the separator."""
    H, W = len(g), len(g[0])
    gb = _bg(g)
    s = next((r for r in range(1, H - 1) if g[r][0] != gb and all(v == g[r][0] for v in g[r])), None)
    if s is None:
        return None
    sc = g[s][0]
    bg = _bg(g[s + 1:])
    hdr = [v for row in g[:s] for v in row]
    last = max([i for i, v in enumerate(hdr) if v != bg], default=-1)
    seq = hdr[:last + 1]
    seeds = [(i, j) for i in range(s + 1, H) for j in range(W) if g[i][j] != bg]
    if len(seq) < 2 or not seeds or sc in seq or any(g[i][j] != seq[0] for i, j in seeds):
        return None
    out = [row[:] for row in g]
    for si, sj in seeds:
        for k, col in enumerate(seq):
            ring = {(si - k, sj + d) for d in range(-k, k + 1)} | {(si + k, sj + d) for d in range(-k, k + 1)} | \
                   {(si + d, sj - k) for d in range(-k, k + 1)} | {(si + d, sj + k) for d in range(-k, k + 1)}
            for i, j in ring:
                if s < i < H and 0 <= j < W:
                    out[i][j] = col
            if strike and not (si - k > s and si + k < H and sj - k >= 0 and sj + k < W):
                out[k // W][k % W] = sc
    return out


def _header_cols(strike):
    def fn(g):
        r = _run_header(_T(g), strike)
        return None if r is None else _T(r)
    return fn


# ------------------------------------------------------------------------------------------------ family
def _fits(fn, train):
    try:
        for p in train:
            if fn(p["input"]) != p["output"]:
                return False
        return True
    except Exception:
        return False


def _cands(train):
    same = all(len(p["input"]) == len(p["output"]) and len(p["input"][0]) == len(p["output"][0]) for p in train)
    smaller = all(len(p["output"]) <= len(p["input"]) and len(p["output"][0]) <= len(p["input"][0]) for p in train)
    if same:
        yield "corner", 1, _run_corner
        yield "cross", 1, _run_cross
        yield "lattice[rows]", 2, _run_lattice
        yield "lattice[cols]", 2, _run_lattice_cols
        for strike in (0, 1):
            yield "header[act=rings,axis=rows,strike=%d]" % strike, 2 + strike, \
                (lambda st: lambda g: _run_header(g, st))(strike)
            yield "header[act=rings,axis=cols,strike=%d]" % strike, 3 + strike, _header_cols(strike)
        # role-bound specialisations (menu from the BINDINGS table)
        yield "lattice[rows,key=mono]", 3, lambda g: _run_lattice(g, 'mono')
        yield "lattice[cols,key=mono]", 3, lambda g: _run_lattice_cols(g, 'mono')
        for near in (True, False):
            yield ("keyline[act=route,match=%s]" % ('near' if near else 'far'), 3 + (not near),
                   (lambda nm: lambda g: _run_keyline(g, nm))(near))
        yield "list[source=loose,layer=L,cycle=1]", 4, _run_list_L
    have_entries = any(_entries(p["input"], _bg(p["input"])) is not None for p in train)
    if have_entries and same:
        for act in ('recolour', 'halo'):
            for drop in (0, 1):
                yield ("entries[act=%s,drop=%d]" % (act, drop), 2 + drop,
                       (lambda act, drop: lambda g: _run_entries(g, act, 'own', 'opposite', 'keep', drop, 0, None))
                       (act, drop))
    if have_entries and (same or smaller):
        for anchor in ('opposite', 'same'):
            learned_opts = [None]
            if same:
                fr = _frames(train, anchor)
                if fr is not None:
                    lt = _learn(train, anchor, fr)
                    if lt:
                        learned_opts.append(lt)
            for crop in ((0, 1) if not same else (0,)):
                for ink in ('own', 'key'):
                    for canvas in ('clear', 'keep'):
                        for lt in learned_opts:
                            name = "entries[act=glyph,ink=%s,anchor=%s,canvas=%s,crop=%d,learn=%d]" % (
                                ink, anchor, canvas, crop, lt is not None)
                            yield (name, 3 + (anchor == 'same') + (lt is not None),
                                   (lambda ink, anchor, canvas, crop, lt:
                                    lambda g: _run_entries(g, 'glyph', ink, anchor, canvas, 1, crop, lt))
                                   (ink, anchor, canvas, crop, lt))
    if same and any(_fenced(p["input"], _region_bg(p["input"])) is not None for p in train[:1]):
        for match in ('all', 'any', 'none', 'notall'):
            yield "fenced[act=erase,match=%s]" % match, 3, (lambda m: lambda g: _run_fenced(g, m))(match)


def fam(train):
    if not train or any(p["input"] == p["output"] for p in train):
        return
    found = []
    for name, cost, fn in _cands(train):
        if _fits(fn, train):
            found.append((cost, len(found), name, fn))
            if len(found) >= 3:
                break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found:
        yield name, cost, fn


FAMILIES = [fam]
