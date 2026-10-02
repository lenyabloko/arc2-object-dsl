"""Prior family stamp_stencil_at_anchors, v4 (test-blind; Fable v11 T68 / D38 / G68 changed): every colour parameter
is a declared colour role (colour_roles: background, rank_colour(k), novel_colour) or a role-bound participant colour
(own, other, line, quad, tmpl); no literal colour numbers.

G68 BINDINGS (priors4) -- per member, the role each former literal became (training pairs only)
  member    former literal (priors3 first program)                 role now
  10fcaaa3  none (4 diagonals <- fresh 8)                          fresh = CR.novel_colour(train)
  11e1fe23  none (centre <- fresh 5, diagonals <- quad)            fresh = CR.novel_colour(train)
  140c817e  stencil constants 2 (centre), 3 (corners)              LOST: needs literal 2, 3 (both new in every
                                                                   output, so novel_colour is not unique)
  264363fd  none (tmpl)                                            -
  310f3251  none (fresh 2)                                         fresh
  396d80d7  none (other)                                           -
  3f23242b  stencil constants 5, 2, 8 and row-line constant 2      LOST: needs literal 5, 2, 8 (three new colours)
  67a423a3  none (fresh 4)                                         fresh
  dfadab01  table keyed by the dot's literal colour 2/3/5/8,       LOST: needs literal keys 2,3,5,8 and values
            glyph colours 4/1/6/7 (constants)                      4,1,6,7 (rank keys vary per pair; values unnamed)
  e9614598  none (fresh 3)                                         fresh
  ecdecbb3  none (line, own)                                       -
  f35d900a  none (other; trail fresh 5)                            fresh
  Literal slots removed (3): the stencil-offset constant and the line constant (now: the declared roles
  background / rank_colour(k) of the canvas, tried after the participant roles, or before them under
  pref=decl); the stencil key 'anchor colour' (a literal colour used as a table key) -> key 'rank' (the anchor
  colour's rank position among the canvas ink colours, 1 = most frequent).
  FRESH is CR.novel_colour; background is CR.background.

Earlier pass (priors3):

BINDINGS (what each induced value of the first fitting program is bound to, per fitted member; train pairs only)
  member    canvas     anchor           stencil cell colours (offset <- role)                       extra
  10fcaaa3  tile 2x2   every cell       4 diagonals <- FRESH colour (8: new in every output)         R=1 <- diagonal reach 1
  11e1fe23  same       bbox centre      centre <- FRESH (5); 4 diagonals <- quadrant participant    R=1
  140c817e  same       every cell       centre, corners <- two fresh colours (2,3: literal, 2 fresh  lines row/col 0 <- own
                                        so no unique FRESH); 4 sides <- own                          colour (anchor's own)
  310f3251  tile+wrap  every cell       up-left diagonal <- FRESH (2)                                wrap <- tiled canvas
  396d80d7  same       every cell       4 diagonals <- OTHER participant; guard free-bg              -
  3f23242b  same       every cell       5x5 frame <- three fresh colours (5,2,8 literal, by row)    row line d=+2 <- stencil
                                                                                                     edge row (= R) colour 2
  67a423a3  same       line crossings   8-ring <- FRESH (4)                                          guard all
  e9614598  same       bbox centre      plus <- FRESH (3)                                            -
  ecdecbb3  same       ray hits on line 8-ring <- LINE colour; centre <- OWN (dot)                   trail <- dot colour,
                                                                                                     period 1, dot -> line
  Specialisation menu built from these bindings (step 2): colour role FRESH (the colour absent from every training
  input and present in every training output, when it is unique) is tried before the literal constant; the trail
  colour domain is {own, FRESH}; the trail period domain is {1, 2} (period 1 observed, 2 = alternate cells); the trail
  target is {ray hits a full line, ray meets an aligned partner anchor (stop at the midpoint)}; the canvas domain gets
  'blank' (paint on background only, input objects wiped) and the anchor domain 'dot' (cells of colours whose
  components are all single pixels, minus label dots attached outside a sign's bounding box).  Shared step
  "stencil read from the grid": anchor 'tmpl' (markers inside host objects; the in-grid template is consumed),
  stencil role TMPL (colour <- template cell at the same offset) and line role TMPL (line colour <- template arm
  colour two cells out), lines bounded by the anchor's host object instead of running edge to edge.
  Newly fitted through these: f35d900a (cell anchors, 8-ring <- OTHER, partner trail colour FRESH period 2),
  dfadab01 (blank canvas, dot anchors keyed by own colour, R=3 glyph induced per key from training outputs),
  264363fd (tmpl anchors, 3x3 core <- TMPL, row/col lines through the anchor <- TMPL arm, inside the host).
  Not fitted: 58f5dbd5 (output is a crop), ac3e2b04 (secondary anchors where a drawn line crosses), ac605cbb
  (per-colour direction/length trails with crossing rays).

Prior family stamp_stencil_at_anchors (test-blind; anti-unified from the member one-offs and train pairs).

One generator: build the canvas (the input, or the input tiled to the output size), find the anchor points,
then at every anchor paste a small stencil whose cells carry colour ROLES (a constant, the anchor's own colour,
the other participant colour, the colour of the line the anchor sits on, or the colour of the participant
lying in the cell's quadrant), optionally preceded by full row/column lines through stencil rows/columns and
by the ray trail that produced the anchor.  The stencil, its roles and its lines are induced offset by offset
from the training outputs (an offset joins the stencil when one role explains every observation of it and it
changes at least one cell); painting is guarded (background only, free background only, or anywhere).
Shared steps written once: background, canvas, anchors and their role contexts, the per-offset role
induction, line induction, the drawing loop (lines -> trails -> stencil, clipped or wrapped), and verify.
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_stamp_stencil_at_anchors"
CONCEPT = "stamp_stencil_at_anchors"
MEMBERS = ["10fcaaa3", "11e1fe23", "140c817e", "264363fd", "310f3251", "396d80d7", "3f23242b", "58f5dbd5",
           "67a423a3", "ac3e2b04", "ac605cbb", "dfadab01", "e9614598", "ecdecbb3", "f35d900a"]
READING = {
    "generator": "Find anchor points (every coloured cell, single-pixel dots, crossings of full lines, the centre "
                 "of the marker bounding box, points where a dot's ray meets a full line, or markers inside host "
                 "objects matching an in-grid template) and paste on each a small stencil induced from training, "
                 "whose cells take role colours (background, a rank colour, fresh colour, anchor colour, other colour, "
                 "hit-line colour, quadrant participant colour, template colour), optionally with lines through stencil "
                 "rows/columns (edge to edge or within the host object) and a (dashed) trail toward the hit line "
                 "or an aligned partner, painting on the input or a blank canvas where the guard allows.",
    "stop": "One stencil per anchor, clipped at the edge (or wrapped on a tiled canvas); lines run edge to edge; "
            "trails run from the dot to the hit line; nothing else changes.",
    "params": "canvas ∈ {same, blank, tile, tile+wrap} · anchor ∈ {cell, dot, cross, centre, rayhit} · "
              "key ∈ {none, rank position of the anchor colour} · guard ∈ {bg, free bg, all} · R ∈ {1,2,3} · lines ∈ {0,1} · "
              "trail ∈ {none, (own|fresh) x period (1|2)} toward {hit line | aligned partner, to the midpoint} · "
              "role preference ∈ {relational, declared} · stencil offsets/roles (induced; roles own, other, "
              "line, quad, fresh, tmpl, bg, rank k)",
    "participants": "Background = most frequent canvas colour. cell: every non-background cell. cross: cells "
                    "where a fully coloured row meets a fully coloured column. centre: integer centre of the "
                    "bounding box of all non-background cells (quadrant participants = those cells). rayhit: "
                    "dots off the uniform full lines cast 4 rays; where a ray reaches a perpendicular full line "
                    "the hit cell is the anchor (own = dot colour, line = line colour, trail = ray path). "
                    "other = the second non-background colour when the grid has exactly two.",
    "preconditions": "Output size equals the canvas size in every pair, anchors exist in every training "
                     "input, every stencil offset is explained by one role, and the induced program "
                     "reproduces every training pair.",
}

ROLES_REL = ("own", "other", "line", "quad", "fresh", "tmpl")
ROLES_DECL = ("bg",) + tuple(("rank", k) for k in CR.RANKS)     # declared roles (colour_roles), per canvas
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
RMAX = 3
# trail menu from the bindings: (colour role, period); None = no trail
TRAILS = (None, ("own", 1), ("fresh", 1), ("own", 2), ("fresh", 2))


# ---------------------------------------------------------------- shared participants
def _bg(g):
    return CR.background(g)


def _bind_roles(src, bg, anc, fresh):
    """Role colours every anchor context carries: fresh (CR.novel_colour of the training pairs), the canvas
    background and rank colours, and the anchor colour's rank position (the stencil key)."""
    tal = Counter(v for r in src for v in r if v != bg)
    order = sorted(tal, key=lambda x: (-tal[x], x))
    pos = {v: i for i, v in enumerate(order)}
    ranks = {("rank", k): CR.rank_colour(src, k, bg) for k in CR.RANKS}
    for _, _, ctx in anc:
        ctx["fresh"] = fresh
        ctx["bg"] = bg
        ctx.update(ranks)
        i = pos.get(ctx.get("own"))
        ctx["krank"] = None if i is None else i + 1


def _key(ctx, key):
    return None if key == "none" else ctx.get("krank")


def _sgn(x):
    return (x > 0) - (x < 0)


def _canvas(g, mode, ratio):
    """The source the anchors are read from (blank shares the input as source)."""
    if mode in ("same", "blank"):
        return [list(r) for r in g]
    ky, kx = ratio
    h, w = len(g), len(g[0])
    return [[g[y % h][x % w] for x in range(w * kx)] for y in range(h * ky)]


def _base(src, bg, mode, anc=()):
    """The canvas painting starts from: the source, or (blank) background everywhere; cells an anchor
    consumed (its template) are erased."""
    if mode == "blank":
        return [[bg] * len(src[0]) for _ in src]
    gone = anc[0][2].get("consume") if anc else None
    if gone:
        src = [r[:] for r in src]
        for y, x in gone:
            src[y][x] = bg
    return src


def _fresh(train):
    """Training-wide FRESH colour = the declared role CR.novel_colour(train)."""
    return CR.novel_colour(train)


def _dots(cv, bg):
    """Cells of colours whose 8-components are all single pixels, minus label dots (a dot 8-touching a
    non-dot object while lying outside that object's bounding box)."""
    H, W = len(cv), len(cv[0])
    nb8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    multi = set()
    for y in range(H):
        for x in range(W):
            v = cv[y][x]
            if v != bg and v not in multi:
                for a, b in nb8:
                    if 0 <= y + a < H and 0 <= x + b < W and cv[y + a][x + b] == v:
                        multi.add(v)
                        break
    comp = [[-1] * W for _ in range(H)]
    boxes = []
    for y in range(H):
        for x in range(W):
            if cv[y][x] in multi and comp[y][x] < 0:
                k = len(boxes)
                st, box = [(y, x)], [y, x, y, x]
                comp[y][x] = k
                while st:
                    i, j = st.pop()
                    box = [min(box[0], i), min(box[1], j), max(box[2], i), max(box[3], j)]
                    for a, b in nb8:
                        u, w = i + a, j + b
                        if 0 <= u < H and 0 <= w < W and comp[u][w] < 0 and cv[u][w] in multi:
                            comp[u][w] = k
                            st.append((u, w))
                boxes.append(box)
    res = []
    for y in range(H):
        for x in range(W):
            v = cv[y][x]
            if v == bg or v in multi:
                continue
            label = False
            for a, b in nb8:
                u, w = y + a, x + b
                if 0 <= u < H and 0 <= w < W and comp[u][w] >= 0:
                    r0, c0, r1, c1 = boxes[comp[u][w]]
                    if not (r0 <= y <= r1 and c0 <= x <= c1):
                        label = True
                        break
            if not label:
                res.append((y, x))
    return res


def _partner_trails(cv, bg, anc):
    """For cell/dot anchors: toward each aligned partner anchor reached over background, the cells up to the
    midpoint, as (y, x, distance)."""
    H, W = len(cv), len(cv[0])
    pos = {(r, c) for r, c, _ in anc}
    for r, c, ctx in anc:
        tr = []
        for dy, dx in DIRS4:
            a, b, k = r + dy, c + dx, 1
            while 0 <= a < H and 0 <= b < W and cv[a][b] == bg:
                a, b, k = a + dy, b + dx, k + 1
            if (a, b) in pos:
                tr.extend((r + dy * d, c + dx * d, d) for d in range(1, k // 2 + 1))
        ctx["trail"] = tr


def _comps8(cv, bg):
    H, W = len(cv), len(cv[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            if cv[y][x] != bg and not seen[y][x]:
                st, cells = [(y, x)], []
                seen[y][x] = True
                while st:
                    i, j = st.pop()
                    cells.append((i, j))
                    for a in (-1, 0, 1):
                        for b in (-1, 0, 1):
                            u, w = i + a, j + b
                            if 0 <= u < H and 0 <= w < W and not seen[u][w] and cv[u][w] != bg:
                                seen[u][w] = True
                                st.append((u, w))
                comps.append(cells)
    return comps


def _template_anchors(cv, bg):
    """Stencil read from the grid: host = most frequent non-background colour; objects without host colour are
    templates (the largest is used and consumed); marker colour = most frequent non-host colour inside host
    objects; the template's marker cell nearest its centroid is its centre.  Anchors = marker cells in host
    objects; ctx tmpl = template colours by offset from its centre; host = the anchor's host object (minus
    marker cells), which bounds its lines; consume = template cells (erased)."""
    cnt = Counter(v for r in cv for v in r if v != bg)
    if len(cnt) < 2:
        return []
    host = cnt.most_common(1)[0][0]
    comps = _comps8(cv, bg)
    hosts = [cs for cs in comps if any(cv[y][x] == host for y, x in cs)]
    temps = [cs for cs in comps if not any(cv[y][x] == host for y, x in cs)]
    mc = Counter(cv[y][x] for cs in hosts for y, x in cs if cv[y][x] != host)
    if not temps or not mc:
        return []
    mcol = mc.most_common(1)[0][0]
    temp = max(temps, key=lambda cs: (len(cs), [(-y, -x) for y, x in sorted(cs)]))
    cen = [(y, x) for y, x in temp if cv[y][x] == mcol]
    if not cen or len(temp) < 2:
        return []
    ty = sum(y for y, _ in temp) / len(temp)
    tx = sum(x for _, x in temp) / len(temp)
    cy, cx = min(cen, key=lambda p: ((p[0] - ty) ** 2 + (p[1] - tx) ** 2, p))
    T = {(y - cy, x - cx): cv[y][x] for y, x in temp}
    res = []
    for cs in hosts:
        hs = frozenset((y, x) for y, x in cs if cv[y][x] == host)
        for y, x in cs:
            if cv[y][x] == mcol:
                res.append((y, x, {"own": mcol, "tmpl": T, "host": hs, "consume": temp}))
    return res


def _line_cells(axis, k, r, c, ctx, H, W, R):
    """Cells of the row/column k through an anchor beyond its stencil window (R) -- bounded by its host object
    when the anchor has one."""
    cells = ([(k, x) for x in range(W) if abs(x - c) > R] if axis == "row"
             else [(y, k) for y in range(H) if abs(y - r) > R])
    hs = ctx.get("host")
    return cells if hs is None else [p for p in cells if p in hs]


def _line_value(role, ctx, axis, d):
    """Line colour: a role colour, or (tmpl) the template's arm colour two cells out along the line."""
    if role == "tmpl":
        t = ctx.get("tmpl")
        if t is None:
            return None
        offs = ((d, 2), (d, -2)) if axis == "row" else ((2, d), (-2, d))
        vs = [t[o] for o in offs if o in t]
        return vs[0] if vs else None
    return _value(role, ctx, 0, 0)


def _guard_mask(cv, bg, guard):
    H, W = len(cv), len(cv[0])
    if guard == "all":
        return [[True] * W for _ in range(H)]
    m = [[cv[y][x] == bg for x in range(W)] for y in range(H)]
    if guard == "free":
        m = [[m[y][x] and all(not (0 <= y + a < H and 0 <= x + b < W) or cv[y + a][x + b] == bg
                              for a, b in DIRS4) for x in range(W)] for y in range(H)]
    return m


def _other_map(cv, bg):
    cols = sorted({v for r in cv for v in r} - {bg})
    if len(cols) == 2:
        return {cols[0]: cols[1], cols[1]: cols[0]}
    return {}


def _anchors(cv, bg, kind):
    """-> list of (r, c, ctx); ctx = {own, other, line, quad, trail}."""
    H, W = len(cv), len(cv[0])
    oth = _other_map(cv, bg)
    res = []
    if kind == "cell":
        for y in range(H):
            for x in range(W):
                v = cv[y][x]
                if v != bg:
                    res.append((y, x, {"own": v, "other": oth.get(v)}))
    elif kind == "dot":
        for y, x in _dots(cv, bg):
            res.append((y, x, {"own": cv[y][x], "other": oth.get(cv[y][x])}))
    elif kind == "cross":
        rows = [y for y in range(H) if all(v != bg for v in cv[y])]
        cols = [x for x in range(W) if all(cv[y][x] != bg for y in range(H))]
        if len(rows) < H and len(cols) < W:
            for y in rows:
                for x in cols:
                    res.append((y, x, {"own": cv[y][x], "other": oth.get(cv[y][x])}))
    elif kind == "centre":
        pts = [(y, x, cv[y][x]) for y in range(H) for x in range(W) if cv[y][x] != bg]
        if 2 <= len(pts) <= 8:
            ys = [p[0] for p in pts]
            xs = [p[1] for p in pts]
            if (min(ys) + max(ys)) % 2 == 0 and (min(xs) + max(xs)) % 2 == 0:
                cy, cx = (min(ys) + max(ys)) // 2, (min(xs) + max(xs)) // 2
                q = {}
                for y, x, v in pts:
                    q.setdefault((_sgn(y - cy), _sgn(x - cx)), set()).add(v)
                quad = {s: min(cs) for s, cs in q.items() if len(cs) == 1}
                res.append((cy, cx, {"own": cv[cy][cx], "quad": quad}))
    elif kind == "tmpl":
        res = _template_anchors(cv, bg)
    elif kind == "rayhit":
        rl = {y: cv[y][0] for y in range(H) if cv[y][0] != bg and all(v == cv[y][0] for v in cv[y])}
        cl = {x: cv[0][x] for x in range(W) if cv[0][x] != bg and all(cv[y][x] == cv[0][x] for y in range(H))}
        if (rl or cl) and len(rl) < H and len(cl) < W:
            for y in range(H):
                if y in rl:
                    continue
                for x in range(W):
                    v = cv[y][x]
                    if v == bg or x in cl:
                        continue
                    for dy, dx in DIRS4:
                        a, b, path, d = y + dy, x + dx, [], 1
                        while 0 <= a < H and 0 <= b < W:
                            if (dy and a in rl) or (dx and b in cl):
                                res.append((a, b, {"own": v, "line": rl[a] if dy else cl[b], "trail": path}))
                                break
                            path.append((a, b, d))
                            a += dy
                            b += dx
                            d += 1
    return res


def _value(role, ctx, dy, dx):
    if role == "tmpl":
        t = ctx.get("tmpl")
        return None if t is None else t.get((dy, dx))
    if role == "quad":
        q = ctx.get("quad")
        return None if q is None else q.get((_sgn(dy), _sgn(dx)))
    return ctx.get(role)


def _prep(g, P):
    src = _canvas(g, P["canvas"], P["ratio"])
    bg = _bg(g)
    anc = _anchors(src, bg, P["anchor"])
    _bind_roles(src, bg, anc, P["fresh"])
    if P.get("trail") and P["anchor"] in ("cell", "dot"):
        _partner_trails(src, bg, anc)
    cv = _base(src, bg, P["canvas"], anc)
    return cv, bg, anc, _guard_mask(cv, bg, P["guard"])


# ---------------------------------------------------------------- induction
def _learn_stencil(data, P):
    """Per (key, offset) role statistics over all anchors of all pairs: [alive roles, unused, changed?].  An
    entry with no alive role is dead and skipped (fast reject).  Roles: participant roles, then declared roles."""
    wrap, key = P["wrap"], P["key"]
    offs = [(dy, dx) for dy in range(-RMAX, RMAX + 1) for dx in range(-RMAX, RMAX + 1)]
    st = {}
    for cv, bg, anc, gm, out in data:
        H, W = len(cv), len(cv[0])
        for r, c, ctx in anc:
            k = _key(ctx, key)
            for dy, dx in offs:
                y, x = r + dy, c + dx
                if wrap:
                    y, x = y % H, x % W
                elif not (0 <= y < H and 0 <= x < W):
                    continue
                if not gm[y][x]:
                    continue
                s = st.get((k, dy, dx))
                if s is None:
                    s = st[(k, dy, dx)] = [list(ROLES_REL + ROLES_DECL), None, False]
                elif not s[0]:
                    continue
                ov, iv = out[y][x], cv[y][x]
                if ov != iv:
                    s[2] = True
                if s[0]:
                    keep = []
                    for role in s[0]:
                        v = _value(role, ctx, dy, dx)
                        if v == ov or (v is None and ov == iv):
                            keep.append(role)
                    s[0] = keep
    return st


def _choose(st, R, pref):
    sten = {}
    for (k, dy, dx), s in sorted(st.items(), key=lambda t: (str(t[0][0]), t[0][1], t[0][2])):
        if max(abs(dy), abs(dx)) > R or not s[2]:
            continue
        rel = [r for r in s[0] if r in ROLES_REL]
        con = [r for r in s[0] if r not in ROLES_REL]           # declared roles replace the literal constant
        opts = rel + con if pref == "rel" else con + rel
        if opts:
            sten.setdefault(k, []).append((dy, dx, opts[0]))
    return sten


def _learn_lines(data, R, keyed):
    """Rows/columns through stencil offsets that are (mostly) one role colour beyond the stencil window."""
    found = {"row": [], "col": []}
    for axis in ("row", "col"):
        for d in range(-R, R + 1):
            best = None
            for role in ("own", "other", "line", "fresh", "tmpl") + ROLES_DECL[1:]:
                ok, chg = True, False
                for cv, bg, anc, gm, out in data:
                    H, W = len(cv), len(cv[0])
                    for r, c, ctx in anc:
                        y0 = r + d if axis == "row" else c + d
                        if not (0 <= y0 < (H if axis == "row" else W)):
                            continue
                        cells = _line_cells(axis, y0, r, c, ctx, H, W, R)
                        if not cells:
                            continue
                        v = _line_value(role, ctx, axis, d)
                        if v is None:
                            if role == "tmpl":
                                continue
                            ok = False
                            break
                        n = sum(1 for y, x in cells if out[y][x] == v)
                        if v == bg or 2 * n < len(cells) + 1:
                            ok = False
                            break
                        chg = chg or any(out[y][x] == v != cv[y][x] for y, x in cells)
                    if not ok:
                        break
                if ok and chg:
                    best = role
                    break
            if best is not None:
                found[axis].append((d, best))
    return found


# ---------------------------------------------------------------- drawing
def _render(g, P):
    cv, bg, anc, gm = _prep(g, P)
    H, W = len(cv), len(cv[0])
    out = [r[:] for r in cv]
    key = P["key"]
    lines = P["lines"]
    if lines:
        lg = gm if P["guard"] != "free" else _guard_mask(cv, bg, "bg")
        for r, c, ctx in anc:
            for axis in ("row", "col"):
                for d, role in lines[axis]:
                    k = (r if axis == "row" else c) + d
                    v = _line_value(role, ctx, axis, d)
                    if v is not None and 0 <= k < (H if axis == "row" else W):
                        for y, x in _line_cells(axis, k, r, c, ctx, H, W, -1):
                            if lg[y][x]:
                                out[y][x] = v
    if P["trail"]:
        trole, period = P["trail"]
        for r, c, ctx in anc:
            v = ctx.get(trole)
            if v is None:
                continue
            for y, x, d in ctx.get("trail", ()):
                if d % period == 0 and cv[y][x] == bg:
                    out[y][x] = v
    sten, wrap = P["stencil"], P["wrap"]
    for r, c, ctx in anc:
        for dy, dx, role in sten.get(_key(ctx, key), ()):
            y, x = r + dy, c + dx
            if wrap:
                y, x = y % H, x % W
            elif not (0 <= y < H and 0 <= x < W):
                continue
            if gm[y][x]:
                v = _value(role, ctx, dy, dx)
                if v is not None:
                    out[y][x] = v
    return out


def _make(P):
    P = dict(P)
    return lambda g: _render(g, P)


def _canvases(train):
    shapes = [(len(p["input"]), len(p["input"][0]), len(p["output"]), len(p["output"][0])) for p in train]
    if all(a == c and b == d for a, b, c, d in shapes):
        res = [("same", None, False)]
        # blank (input objects wiped) only when every pair wipes some input cell to background
        bgs = [_bg(p["input"]) for p in train]
        if all(any(v != bg and p["output"][y][x] == bg for y, r in enumerate(p["input"]) for x, v in enumerate(r))
               for p, bg in zip(train, bgs)):
            res.append(("blank", None, False))
        return res
    if all(c % a == 0 and d % b == 0 for a, b, c, d in shapes):
        rs = {(c // a, d // b) for a, b, c, d in shapes}
        if len(rs) == 1:
            ratio = rs.pop()
            return [("tile", ratio, False), ("tile", ratio, True)]
    return []


# ---------------------------------------------------------------- family
def fam(train):
    if not train:
        return
    learned = []
    fresh = _fresh(train)
    for canvas, ratio, wrap in _canvases(train):
        for kind in ("cell", "dot", "cross", "centre", "rayhit", "tmpl"):
            pre = []
            for p in train:
                src = _canvas(p["input"], canvas, ratio)
                bg = _bg(p["input"])
                anc = _anchors(src, bg, kind)
                # fast reject: a stamp has sparse anchors (fitted members: at most 1/4 of the canvas)
                if not anc or len(anc) > 1000 or (len(anc) > 16 and 3 * len(anc) > len(src) * len(src[0])):
                    break
                _bind_roles(src, bg, anc, fresh)
                pre.append((_base(src, bg, canvas, anc), bg, anc, p["output"]))
            if len(pre) != len(train):
                continue
            keyed_ok = len({ctx.get("own") for _, _, anc, _ in pre for _, _, ctx in anc}) > 1
            for key in (("none", "rank") if keyed_ok else ("none",)):
                for guard in (("all",) if canvas == "blank" else ("bg", "free", "all")):
                    P = {"canvas": canvas, "ratio": ratio, "wrap": wrap, "anchor": kind, "key": key, "guard": guard,
                         "fresh": fresh}
                    data = [(cv, bg, anc, _guard_mask(cv, bg, guard), out) for cv, bg, anc, out in pre]
                    learned.append((P, data, _learn_stencil(data, P)))
    if not learned:
        return
    cands = []
    for R in range(1, RMAX + 1):
        for i, (P, data, st) in enumerate(learned):
            for pref in ("rel", "decl"):
                sten = _choose(st, R, pref)
                if not sten:
                    continue
                for trail in TRAILS:
                    if trail and (P["anchor"] not in ("rayhit", "cell", "dot")
                                  or (trail[0] == "fresh" and P["fresh"] is None)):
                        continue
                    for use_lines in (False, True):
                        cost = (R + (P["key"] != "none") + use_lines + 0.5 * (pref != "rel")
                                + (P["canvas"] == "blank") + (trail is not None) + 0.5 * bool(trail and trail[1] > 1))
                        cands.append((cost, len(cands), i, R, pref, sten, trail, use_lines))
    cands.sort(key=lambda t: (t[0], t[1]))
    found, seen = 0, set()
    for cost, _, i, R, pref, sten, trail, use_lines in cands:
        P, data, st = learned[i]
        lines = _learn_lines(data, R, P["key"] != "none") if use_lines else None
        if use_lines and not (lines["row"] or lines["col"]):
            continue
        Q = dict(P, stencil=sten, trail=trail, lines=lines)
        sig = repr(sorted((k, v) for k, v in Q.items() if k not in ("stencil", "lines"))) + repr(
            sorted(sten.items(), key=lambda t: str(t[0]))) + repr(lines)
        if sig in seen:
            continue
        seen.add(sig)
        fn = _make(Q)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            name = ("stamp[canvas=%s%s,anchor=%s,key=%s,guard=%s,R=%d,pref=%s,trail=%s,lines=%d]"
                    % (P["canvas"], "+wrap" if P["wrap"] else "", P["anchor"], P["key"], P["guard"], R, pref,
                       "%s/%d" % trail if trail else "0", bool(lines)))
            yield (name, 1 + cost, fn)
            found += 1
            if found >= 3:
                return


FAMILIES = [fam]
