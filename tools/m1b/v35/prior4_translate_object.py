"""Prior family: TRANSLATE_OBJECT -- movable objects translate rigidly along an induced direction.
priors4 (Fable v11, D38 / G68): every colour parameter is a declared role of colour_roles.py (background,
rank_colour(k), novel_colour) or a role-bound value; no literal colour numbers.  Non-colour parameters, steps and the
enumeration order are those of priors3.

One generator, MOVE(objects; direction; distance; mode):
  participants  objects = segmentation of the non-background cells (seg), split into static objects (anchors that
                never move: nothing / objects whose colour is an ink rank that never changes in training / objects
                touching the leading edge ("ground") / full-length wall lines) and movers (everything else, or only
                the objects that carry a one-cell-wide tail).
  direction     fixed (one of 4, or 8 for a constant shift) | role-keyed table (ink rank of the object colour ->
                direction, induced from the training displacement of each colour; an unseen colour takes the single
                unused direction) | toward the nearest static object it can reach | along its own attached tail |
                toward or away from its own open side (the concavity of its bounding box; toward/away per ink rank).
  distance      constant k | until contact (grid edge, static object, or an already-settled mover; movers processed
                nearest-to-their-edge first so they stack; optional one-cell gap kept to the edge/static) |
                tail length (the tail is erased, the body -- or its whole bounding box with contents -- moves).
  mode          move | copy; moved cells may be recoloured by a role map (source: ink rank of the moved colour, or
                every mover; target: novel colour | background | ink rank); background may be repainted by a fill
                role (novel colour | ink rank); static rectangles may be restored (their own colour) where movers
                occluded them.
Colour roles used (all resolved on the grid, or fixed by the training pairs through the role):
  background(g)        per-grid background (CR.background)
  common               role-bound value defined here on CR.input_colours: the colour present in every training
                       input, the most frequent over them (the background the inputs share)
  rank k               CR.rank_colour(g, k, bg), k in CR.RANKS (1, 2, 3, -1, -2)
  novel                CR.novel_colour(train)
  vanishing            CR.vanishing_colours(train) minus the background (band / marker colour)
  own colour           the static object's own colour (rectify), the moved cell's own colour (default)

BINDINGS (G68) -- per member, the literal colour value priors3 induced and the role it became
("LOST: needs literal c" = no declared role explains it; the member no longer fits).
  2faf500b  band colour 6       <- vanishing (CR.vanishing_colours: in every input, in no output)      FITS
  32e9702f  fill 5              <- novel (in every output, in no input)                                 FITS
  825aa9e9  bg 7                <- common (the colour shared by every training input; pair 4's own
                                   background is 5)                                                     FITS
  98cf29f8  (no colour parameter: tail binding)                                                         FITS
  a79310a0  recolour 8>2        <- rank1 > novel                                                        FITS
  b5ca7ac4  table 2:right,8:left <- rank1:right, rank2:left (frame colours are ink ranks 1/2 in every
                                   pair)                                                                FITS
  c6e1b8da  rectify colour      <- the static rectangle's own colour (participant; unchanged)           FITS
  d255d7a7  (no colour parameter: tail + bbox carry)                                                    FITS
  f3e62deb  table 4:down,6:up,8:right  LOST: needs literal 4, 6, 8 (each grid holds one object colour, so
                                   every rank names that same colour; no role separates 4/6/8)
  1e5d6875  open-side keys 2,5  <- rank1:closed, rank2:open;  recolour 2>3, 5>4  LOST: needs literal 3, 4
                                   (two colours new in the outputs; novel_colour needs a single one)
  Unfitted in priors3 and still unfitted (no colour parameter would change that): 1efba499, 332f06d7, 4c3d4a41,
  56dc2b01, 6e453dd6, 73c3b0d8, 7d7772cc, 834ec97d, 984d8a3e, 9bbf930d, 9f669b64, fc10701f.
Literal colours removed: fixed bg (-> common), learned static colour set (-> ink ranks never changing), band set
(-> vanishing), direction-table and open-side keys (-> ink ranks), recolour map keys/values and fill (-> roles).
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_translate_object"
CONCEPT = "translate_object"
MEMBERS = ["1e5d6875", "1efba499", "2faf500b", "32e9702f", "332f06d7", "4c3d4a41", "56dc2b01", "6e453dd6",
           "73c3b0d8", "7d7772cc", "825aa9e9", "834ec97d", "984d8a3e", "98cf29f8", "9bbf930d", "9f669b64",
           "a79310a0", "b5ca7ac4", "c6e1b8da", "d255d7a7", "f3e62deb", "fc10701f"]
READING = {
    "generator": "Segment the non-background cells into objects, keep the static ones (anchors) in place and "
                 "translate every mover rigidly along a direction (fixed, ink-rank table, toward the nearest "
                 "anchor, along its own one-cell tail, or toward/away from its own open side per ink rank) by a "
                 "distance (constant, until contact with edge/anchor/"
                 "settled mover processed nearest-first, or the tail's length with the tail erased), moving or "
                 "copying it.",
    "stop": "constant k steps (cells pushed off the grid vanish) | last free position before overlapping the grid "
            "edge, an anchor or a settled mover of the same collision group, keeping `gap` empty cells before the "
            "edge/anchor | tail length",
    "params": "seg in {all, c8 multicolour, c4 same-colour, per-colour, framed rectangles} . "
              "static in {none, ink ranks that never change, ground (touching leading edge), full-length walls, largest} . "
              "dir in {fixed 4/8, ink-rank table, toward anchor, tail, open side x per-rank sign} . "
              "dist in {k in 1..3, contact, tail length} . "
              "gap in {0,1} . collide in {all, same colour} . carry in {cells, bbox} . rectify in {0,1} . "
              "mode in {move, copy} . recolour map {ink rank | mover -> novel | bg | ink rank}, fill in {novel, "
              "ink rank}, background in {per-grid background, common (shared by all training inputs)}",
    "participants": "background = role background (or role-bound 'common': the colour shared by all training inputs); "
                    "objects per seg; movers = non-static objects (or tailed objects); anchors = static objects",
    "preconditions": "input and output have equal shape in every training pair; at least one pair changes; "
                     "segmentation succeeds; table/ground/wall/tail/open-side variants only when the training "
                     "grids contain such participants",
}

DIR4 = ((-1, 0), (0, 1), (1, 0), (0, -1))
DIR8 = DIR4 + ((-1, -1), (-1, 1), (1, 1), (1, -1))
STAY = (0, 0)


# ------------------------------------------------------------------------------------------------ basic helpers
def _mode(g):
    """role background: the most frequent colour of the grid (ties -> lower colour number)."""
    return CR.background(g)


# ------------------------------------------------------------------------------------------- colour roles (G68)
RANKS = CR.RANKS


def _common_bg(train):
    """Role-bound value (defined here, built on CR.input_colours): the colour present in every training input, the
    most frequent over them -- the background shared by all training inputs.  None when no colour is shared."""
    common = CR.input_colours(train)
    if not common:
        return None
    tot = Counter(v for p in train for row in p["input"] for v in row)
    return max(sorted(common), key=lambda k: tot[k])


def _resolve_keys(g, bg, rt):
    """role-keyed table ((rank k, value), ...) -> {colour: value} on grid g (first role wins a shared colour)."""
    out = {}
    for k, v in rt:
        c = CR.rank_colour(g, k, bg)
        if c is not None and c not in out:
            out[c] = v
    return out


def _key_roles(train, bgs, lit, keys_per_pair):
    """literal {colour: value} induced from training -> role-keyed table ((rank k, value), ...): every key colour is
    replaced by the first ink rank k that names it in every training input where it occurs.  None when some key
    colour has no rank role (that member then needs a literal colour)."""
    out, used = [], {}
    for c in sorted(lit):
        idx = [i for i, ks in enumerate(keys_per_pair) if c in ks]
        hit = None
        for k in RANKS:
            if k in used and used[k] != lit[c]:
                continue
            if idx and all(CR.rank_colour(train[i]["input"], k, bgs[i]) == c for i in idx):
                hit = k
                break
        if hit is None:
            return None
        if hit not in used:
            used[hit] = lit[c]
            out.append((hit, lit[c]))
    return tuple(out)


def _target_role(train, bgs, idx, t, N):
    """the role naming colour t in every training input of idx: novel colour | background | ink rank k."""
    if N is not None and t == N:
        return ("novel",)
    if idx and all(bgs[i] == t for i in idx):
        return ("background",)
    for k in RANKS:
        if idx and all(CR.rank_colour(train[i]["input"], k, bgs[i]) == t for i in idx):
            return ("rank", k)
    return None


def _resolve_target(role, g, bg, N):
    if role[0] == "novel":
        return N
    if role[0] == "background":
        return bg
    return CR.rank_colour(g, role[1], bg)


def _rolify(train, bgs, cmap, fill, N):
    """literal recolour map / fill learned by _fit -> role specs ((source role, target role), ...), fill role.
    Source = ink rank k of the moved colour (or every mover, when all moved colours take one target role);
    target / fill = novel colour | background | ink rank k.  None when some literal has no role."""
    rc = []
    srcs = []
    for s, t in sorted(cmap.items()):
        idx = [i for i, p in enumerate(train) if any(v == s for row in p["input"] for v in row)]
        tr = _target_role(train, bgs, idx, t, N)
        if tr is None:
            return None
        srcs.append((s, idx, tr))
    for s, idx, tr in srcs:
        sr = None
        for k in RANKS:
            if idx and all(CR.rank_colour(train[i]["input"], k, bgs[i]) == s for i in idx):
                sr = ("rank", k)
                break
        if sr is None:
            break
        rc.append((sr, tr))
    else:
        srcs = None
    if srcs is not None:                     # some source colour has no rank role: try "every mover"
        if len({tr for _, _, tr in srcs}) != 1:
            return None
        rc = [(("mover",), srcs[0][2])]
    rf = None
    if fill is not None:
        rf = _target_role(train, bgs, list(range(len(train))), fill, N)
        if rf is None or rf == ("background",):
            return None
    return tuple(rc), rf


def _resolve_cmap(g, bg, rcmap, N):
    out = {}
    for sr, tr in rcmap:
        t = _resolve_target(tr, g, bg, N)
        if t is None:
            continue
        if sr[0] == "mover":
            for row in g:
                for v in row:
                    if v != bg:
                        out.setdefault(v, t)
        else:
            s = CR.rank_colour(g, sr[1], bg)
            if s is not None:
                out.setdefault(s, t)
    return out


def _role_name(r):
    return {"novel": "novel", "background": "bg", "mover": "mover"}.get(r[0]) or "rank%d" % r[1]


def _comps(g, bg, same, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
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
            out.append(sorted(cells))
    return out


def _rects(g, bg):
    """Greedy parse into rectangles with a uniform border and a uniform core (solid or framed). None on failure."""
    H, W = len(g), len(g[0])
    used = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            f = g[r][c]
            if f == bg or used[r][c]:
                continue
            wmax = 0
            while c + wmax < W and g[r][c + wmax] == f and not used[r][c + wmax]:
                wmax += 1
            hmax = 0
            while r + hmax < H and g[r + hmax][c] == f and not used[r + hmax][c]:
                hmax += 1
            best = None
            for h in range(hmax, 0, -1):
                for w in range(wmax, 0, -1):
                    if any(g[r + h - 1][c + j] != f or used[r + h - 1][c + j] for j in range(w)):
                        continue
                    if any(g[r + i][c + w - 1] != f or used[r + i][c + w - 1] for i in range(h)):
                        continue
                    core = {g[r + i][c + j] for i in range(1, h - 1) for j in range(1, w - 1)}
                    if len(core) > 1 or bg in core:
                        continue
                    if any(used[r + i][c + j] for i in range(h) for j in range(w)):
                        continue
                    best = (h, w)
                    break
                if best:
                    break
            if best is None:
                return None
            h, w = best
            cells = []
            for i in range(h):
                for j in range(w):
                    used[r + i][c + j] = True
                    cells.append((r + i, c + j))
            out.append(cells)
    return out


def _segment(g, bg, seg):
    if seg == "all":
        cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
        parts = [cells] if cells else []
    elif seg == "c8":
        parts = _comps(g, bg, False, True)
    elif seg == "c4":
        parts = _comps(g, bg, True, False)
    elif seg == "col":
        d = {}
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != bg:
                    d.setdefault(v, []).append((r, c))
        parts = [d[k] for k in sorted(d)]
    else:
        parts = _rects(g, bg)
        if parts is None:
            return None
    objs = []
    for cells in parts:
        cnt = Counter(g[r][c] for r, c in cells)
        key = max(sorted(cnt), key=lambda k: cnt[k])
        if seg == "rect":
            key = g[cells[0][0]][cells[0][1]]
        objs.append({"cells": cells, "key": key})
    return objs


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _tail(cells):
    """One-cell-wide straight tail protruding from the middle of a side.  Returns (dir, length, tail cells) or None."""
    S = set(cells)
    r0, r1, c0, c1 = _bbox(cells)
    best = None
    for side, d in (("top", (-1, 0)), ("bottom", (1, 0)), ("left", (0, -1)), ("right", (0, 1))):
        if side in ("top", "bottom"):
            lines = list(range(r0, r1 + 1))
            get = lambda L: [b for (a, b) in S if a == L]
        else:
            lines = list(range(c0, c1 + 1))
            get = lambda L: [a for (a, b) in S if b == L]
        if side in ("bottom", "right"):
            lines = lines[::-1]
        n, pos = 0, None
        for L in lines:
            ps = get(L)
            if len(ps) == 1 and (pos is None or ps[0] == pos):
                pos = ps[0]
                n += 1
            else:
                break
        if n == 0 or n >= len(lines):
            continue
        perp = [x for L in lines[n:] for x in get(L)]
        if not (min(perp) < pos < max(perp)):
            continue
        if best is None or n > best[1]:
            tl = set(lines[:n])
            if side in ("top", "bottom"):
                tail = [p for p in cells if p[0] in tl]
            else:
                tail = [p for p in cells if p[1] in tl]
            best = (d, n, tail)
    return best


def _open_vec(cells):
    """The object's open side: from the centroid of its cells toward the centroid of the background cells inside its
    bounding box (the concavity), snapped to one of 8 unit directions.  STAY when the object fills its box.
    (The complement of the tail binding: the tail is where the shape protrudes, the open side where it is hollow.)"""
    r0, r1, c0, c1 = _bbox(cells)
    S = set(cells)
    miss = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r, c) not in S]
    if not miss:
        return STAY
    mr = sum(r for r, _ in miss) / len(miss) - sum(r for r, _ in cells) / len(cells)
    mc = sum(c for _, c in miss) / len(miss) - sum(c for _, c in cells) / len(cells)
    m = max(abs(mr), abs(mc))
    if m < 0.25:
        return STAY
    dr = (1 if mr > 0 else -1) if abs(mr) >= 0.5 * m else 0
    dc = (1 if mc > 0 else -1) if abs(mc) >= 0.5 * m else 0
    return dr, dc


def _open_dir(sgn, o):
    v = _open_vec(o["cells"])
    sg = sgn.get(o["key"])
    if sg is None:
        vals = set(sgn.values())
        sg = vals.pop() if len(vals) == 1 else 1
    return sg * v[0], sg * v[1]


def _edge_dist(cells, d, H, W):
    dr, dc = d
    if d == STAY:
        return 10 ** 6
    ds = []
    if dr > 0:
        ds.append(H - 1 - max(r for r, _ in cells))
    if dr < 0:
        ds.append(min(r for r, _ in cells))
    if dc > 0:
        ds.append(W - 1 - max(c for _, c in cells))
    if dc < 0:
        ds.append(min(c for _, c in cells))
    return min(ds)


def _touches(cells, d, H, W):
    return _edge_dist(cells, d, H, W) == 0


def _is_wall(cells, H, W):
    r0, r1, c0, c1 = _bbox(cells)
    return (r0 == 0 and r1 == H - 1 and c1 - c0 < W - 1) or (c0 == 0 and c1 == W - 1 and r1 - r0 < H - 1)


# ------------------------------------------------------------------------------------------------- simulation
def _slide(cells, d, H, W, static, settled, gap, limit):
    """Number of steps the cell set can slide along d before hitting the edge, a static or a settled cell."""
    dr, dc = d
    t = 0
    while t < limit:
        n = t + 1
        ok = True
        for r, c in cells:
            y, x = r + dr * n, c + dc * n
            if not (0 <= y < H and 0 <= x < W) or (y, x) in static or (y, x) in settled:
                ok = False
                break
            for j in range(1, gap + 1):
                yy, xx = y + dr * j, x + dc * j
                if not (0 <= yy < H and 0 <= xx < W) or (yy, xx) in static:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            break
        t = n
    return t


def _toward(cells, H, W, static):
    best = None
    for d in DIR4:
        t = _slide(cells, d, H, W, static, (), 0, H + W)
        dr, dc = d
        hit = any((r + dr * (t + 1), c + dc * (t + 1)) in static for r, c in cells)
        if hit and (best is None or t < best[0]):
            best = (t, d)
    return best[1] if best else STAY


def _table_dir(table, key):
    if key in table:
        return table[key]
    used = {v for v in table.values() if v != STAY}
    free = [d for d in DIR4 if d not in used]
    return free[0] if len(free) == 1 else STAY


def _split(g, bg, objs, mk, cmap, fill):
    """Movers are the two halves of an object crossed by a full-span band of a vanishing (marker) colour: the band
    is erased and each half slides away from it by half the band's thickness."""
    H, W = len(g), len(g[0])
    out = [[bg] * W for _ in range(H)]
    dests = {}
    hit = False
    for o in objs:
        cells = o["cells"]
        band = [p for p in cells if g[p[0]][p[1]] in mk]
        body = [p for p in cells if g[p[0]][p[1]] not in mk]
        if not band:
            for r, c in body:
                out[r][c] = g[r][c]
            continue
        sr0, sr1, sc0, sc1 = _bbox(cells)
        mr0, mr1, mc0, mc1 = _bbox(band)
        full_h, full_w = (mr0, mr1) == (sr0, sr1), (mc0, mc1) == (sc0, sc1)
        if full_h and (not full_w or mc1 - mc0 <= mr1 - mr0):
            vert, b0, b1 = True, mc0, mc1
        elif full_w:
            vert, b0, b1 = False, mr0, mr1
        else:
            return None
        hit = True
        t = b1 - b0 + 1
        half = max(1, t // 2)
        cut = b0 + (t + 1) // 2
        for r, c in body:
            k = c if vert else r
            d = -half if k < cut else half
            y, x = (r, c + d) if vert else (r + d, c)
            if 0 <= y < H and 0 <= x < W:
                out[y][x] = cmap.get(g[r][c], g[r][c])
                dests[(y, x)] = g[r][c]
    if not hit:
        return None
    if fill is not None:
        out = [[fill if v == bg else v for v in row] for row in out]
    return out, dests, bg


def _sim(g, P, objs=None, cmap=None, fill=None):
    """Run the generator with parameters P.  Returns (output, {dest cell: source colour or None}) or None."""
    H, W = len(g), len(g[0])
    bg = P["bg"] if P["bg"] is not None else _mode(g)
    if objs is None:
        objs = _segment(g, bg, P["seg"])
    if objs is None:
        return None
    cmap = cmap or {}
    dirm, dist, stat = P["dir"], P["dist"], P["static"]
    lsc = {CR.rank_colour(g, k, bg) for k in P["ls"]} - {None}        # static colours <- their ink-rank roles
    table = _resolve_keys(g, bg, P["table"])
    sgn = _resolve_keys(g, bg, P["sgn"])
    movers, statics = [], []
    if dist == "split":
        return _split(g, bg, objs, P["mk"], cmap, fill)
    if dist == "tail":
        for o in objs:
            tl = _tail(o["cells"])
            if tl is None:
                statics.append(o)
            else:
                movers.append((o, tl[0], tl))
        if not movers:
            return None
    else:
        for o in objs:
            cells = o["cells"]
            if stat == "learned":
                s = o["key"] in lsc
            elif stat == "ground":
                s = _touches(cells, dirm[1], H, W)
            elif stat == "wall":
                s = _is_wall(cells, H, W)
            elif stat == "largest":
                s = False
            else:
                s = False
            if s:
                statics.append(o)
            else:
                movers.append([o, None, None])
        if stat == "largest" and movers:
            sizes = sorted((len(m[0]["cells"]) for m in movers), reverse=True)
            if len(sizes) < 2 or sizes[0] == sizes[1]:
                return None
            big = max(movers, key=lambda m: len(m[0]["cells"]))
            movers.remove(big)
            statics.append(big[0])
        if not movers:
            return None
        sset = {p for o in statics for p in o["cells"]}
        for m in movers:
            if dirm == "table":
                m[1] = _table_dir(table, m[0]["key"])
            elif dirm == "toward":
                m[1] = _toward(m[0]["cells"], H, W, sset)
            elif dirm == "open":
                m[1] = _open_dir(sgn, m[0])
            else:
                m[1] = dirm[1]
    # bodies to carry
    carried = []
    for m in movers:
        o, d, tl = m[0], m[1], m[2]
        if dist == "tail":
            tset = set(tl[2])
            body = [p for p in o["cells"] if p not in tset]
            if P["carry"] == "bbox":
                r0, r1, c0, c1 = _bbox(body)
                body = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
            carried.append((o, d, body, tl[1], o["cells"] + [p for p in body if p not in set(o["cells"])]))
        else:
            carried.append((o, d, o["cells"], None, o["cells"]))
    out = [row[:] for row in g]
    erased = set()
    if P["mode"] == "move":
        for o, d, body, n, clear in carried:
            for r, c in clear:
                out[r][c] = bg
                erased.add((r, c))
    statics = [o for o in statics if not all(p in erased for p in o["cells"])]
    if P.get("rectify"):
        for o in statics:
            r0, r1, c0, c1 = _bbox(o["cells"])
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    if out[r][c] == bg:
                        out[r][c] = o["key"]
    sset = {p for o in statics for p in o["cells"]}
    order = sorted(range(len(carried)), key=lambda i: (_edge_dist(carried[i][2], carried[i][1], H, W), i))
    settled = {}
    dests = {}
    draws = []
    for i in order:
        o, d, body, n, _ = carried[i]
        grp = o["key"] if P["collide"] == "same" else 0
        st = settled.setdefault(grp, set())
        if dist == "tail":
            t = n
        elif dist == "contact":
            t = 0 if d == STAY else _slide(body, d, H, W, sset, st, P["gap"], H + W)
        else:
            t = dist[1]
        dr, dc = d
        for r, c in body:
            y, x = r + dr * t, c + dc * t
            if 0 <= y < H and 0 <= x < W:
                st.add((y, x))
                draws.append((y, x, g[r][c]))
    for y, x, v in draws:
        if v == bg:
            out[y][x] = bg
            dests[(y, x)] = None
        else:
            out[y][x] = cmap.get(v, v)
            dests[(y, x)] = v
    if fill is not None:
        out = [[fill if v == bg else v for v in row] for row in out]
    return out, dests, bg


def _fit(train, P, segs):
    """Exact fit of P on all pairs, inducing a recolour map / background fill when needed.  (cmap, fill) or None."""
    cmap, fill, need = {}, None, False
    for p, objs in zip(train, segs):
        res = _sim(p["input"], P, objs)
        if res is None:
            return None
        out, dests, bg = res
        want = p["output"]
        if out == want:
            continue
        need = True
        for r, row in enumerate(out):
            wr = want[r]
            if row == wr:
                continue
            for c, v in enumerate(row):
                w = wr[c]
                if v == w:
                    continue
                src = dests.get((r, c))
                if src is not None:
                    if cmap.setdefault(src, w) != w:
                        return None
                elif v == bg:
                    if fill is None:
                        fill = w
                    elif fill != w:
                        return None
                else:
                    return None
    if not need:
        return {}, None
    for p, objs in zip(train, segs):
        res = _sim(p["input"], P, objs, cmap, fill)
        if res is None or res[0] != p["output"]:
            return None
    return cmap, fill


# ------------------------------------------------------------------------------------------------- induction
def _disp(train, bgs, colours=None):
    """Mean displacement (dr, dc) of each colour present with equal counts in input and output."""
    acc = {}
    for p, bg in zip(train, bgs):
        a, b = p["input"], p["output"]
        pa, pb = {}, {}
        for g, d in ((a, pa), (b, pb)):
            for r, row in enumerate(g):
                for c, v in enumerate(row):
                    if v != bg:
                        d.setdefault(v, []).append((r, c))
        for v in pa:
            if v in pb and (colours is None or v in colours):
                A, B = pa[v], pb[v]
                ar = sum(r for r, _ in A) / len(A)
                ac = sum(c for _, c in A) / len(A)
                br = sum(r for r, _ in B) / len(B)
                bc = sum(c for _, c in B) / len(B)
                s = acc.setdefault(v, [0.0, 0.0, 0])
                s[0] += br - ar
                s[1] += bc - ac
                s[2] += 1
    return acc


def _induce_side(train, segs, bgs, k):
    """Per object colour: +1 (toward its open side) or -1 (away from it), the sign whose k-step image lands on cells
    that are background in the input and painted in the output for every object of that colour.  None when no
    object has an open side or some colour fits neither sign."""
    ok = {}
    for p, objs, bg in zip(train, segs, bgs):
        a, b = p["input"], p["output"]
        H, W = len(a), len(a[0])
        for o in objs:
            v = _open_vec(o["cells"])
            if v == STAY:
                continue
            st = ok.setdefault(o["key"], {1: True, -1: True})
            for s in (1, -1):
                for r, c in o["cells"]:
                    y, x = r + s * k * v[0], c + s * k * v[1]
                    if 0 <= y < H and 0 <= x < W and a[y][x] == bg and b[y][x] == bg:
                        st[s] = False
                        break
    if not ok:
        return None
    sgn = {}
    for key, st in ok.items():
        if not (st[1] or st[-1]):
            return None
        sgn[key] = 1 if st[1] else -1
    return sgn


def _vec_dir(dr, dc):
    if abs(dr) < 0.25 and abs(dc) < 0.25:
        return STAY
    if abs(dr) >= abs(dc):
        return (1, 0) if dr > 0 else (-1, 0)
    return (0, 1) if dc > 0 else (0, -1)


def _make(P, rcmap, rfill, N):
    """colour parameters are role specs, resolved on each grid (bg, ink ranks) or fixed by the role (novel)."""
    def fn(g):
        g = [list(r) for r in g]
        try:
            bg = P["bg"] if P["bg"] is not None else _mode(g)
            cmap = _resolve_cmap(g, bg, rcmap, N)
            fill = _resolve_target(rfill, g, bg, N) if rfill is not None else None
            res = _sim(g, P, None, cmap, fill)
        except Exception:
            res = None
        return [list(r) for r in g] if res is None else res[0]
    return fn


def _name(P, cmap, fill):
    parts = ["seg=%s" % P["seg"], "static=%s" % P["static"]]
    d = P["dir"]
    parts.append("dir=%s" % (d if isinstance(d, str) else "%+d%+d" % d[1]))
    parts.append("dist=%s" % (P["dist"] if isinstance(P["dist"], str) else "k%d" % P["dist"][1]))
    for k in ("gap", "collide", "carry", "rectify", "mode"):
        if P.get(k) not in (None, 0, "all", "cells", "move"):
            parts.append("%s=%s" % (k, P[k]))
    if P["static"] == "learned":
        parts.append("ls=" + ",".join("rank%d" % k for k in P["ls"]))
    if P["dir"] == "table":
        parts.append("table=" + ",".join("rank%d:%+d%+d" % (k, v[0], v[1]) for k, v in P["table"]))
    if P["dir"] == "open":
        parts.append("side=" + ",".join("rank%d:%s" % (k, "open" if v > 0 else "closed") for k, v in P["sgn"]))
    if cmap:
        parts.append("recolour=" + ",".join("%s>%s" % (_role_name(a), _role_name(b)) for a, b in cmap))
    if fill is not None:
        parts.append("fill=%s" % _role_name(fill))
    if P["bg"] is not None:
        parts.append("bg=common")
    return "translate_object[%s]" % ",".join(parts)


def _base(**kw):
    P = {"bg": None, "seg": "c8", "static": "none", "dir": ("fix", (1, 0)), "dist": "contact", "gap": 0,
         "collide": "all", "carry": "cells", "rectify": 0, "mode": "move", "ls": (), "table": (), "mk": frozenset(),
         "sgn": ()}
    P.update(kw)
    return P


def fam(train, max_out=3):
    if not train:
        return
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
    if all(p["input"] == p["output"] for p in train):
        return
    # background candidates
    grid_bgs = [_mode(p["input"]) for p in train]
    N = CR.novel_colour(train)                       # role novel_colour, fixed by the training pairs
    bg_opts = [None]                                 # None = role background (per grid)
    gb = _common_bg(train)                           # role-bound: the colour shared by every training input
    if gb is not None and any(x != gb for x in grid_bgs):
        bg_opts.append(gb)
    found = 0
    tried = set()
    for bgfix in bg_opts:
        bgs = grid_bgs if bgfix is None else [bgfix] * len(train)
        seg_cache = {}

        def segs_for(seg):
            if seg not in seg_cache:
                ss = [_segment(p["input"], bg, seg) for p, bg in zip(train, bgs)]
                seg_cache[seg] = None if any(s is None for s in ss) else ss
            return seg_cache[seg]

        # static colours <- ink-rank roles whose colour never changes in any training pair
        chg = []
        for p, bg in zip(train, bgs):
            a, b = p["input"], p["output"]
            ch = set()
            for r, row in enumerate(a):
                for c, v in enumerate(row):
                    if v != b[r][c]:
                        ch.add(v)
                        ch.add(b[r][c])
            chg.append(ch)
        ls = tuple(k for k in RANKS
                   if all(CR.rank_colour(p["input"], k, bg) not in ch | {None} for p, bg, ch in zip(train, bgs, chg)))
        # band (marker) colours <- role-bound helper CR.vanishing_colours (in every input, in no output), minus bg
        mk = frozenset(CR.vanishing_colours(train) - set(bgs))
        disp = _disp(train, bgs)
        tw = [sum(s[0] for s in disp.values()), sum(s[1] for s in disp.values())]
        dirs4 = [d for d in DIR4 if d[0] * tw[0] + d[1] * tw[1] > 0.25] or list(DIR4)
        dirs4.sort(key=lambda d: -(d[0] * tw[0] + d[1] * tw[1]))

        def cands():
            # 1. constant shift of all non-static cells
            for static in ("none", "learned"):
                if static == "learned" and not ls:
                    continue
                for k in (1, 2, 3):
                    for d in DIR8:
                        for mode in ("move", "copy"):
                            yield 1 + k + (d not in DIR4) + (mode == "copy") + (static != "none"), \
                                _base(bg=bgfix, seg="all" if static == "none" else "c8", static=static,
                                      dir=("fix", d), dist=("k", k), mode=mode, ls=ls)
            # 2. tails
            for seg in ("c4", "col"):
                for carry in ("cells", "bbox"):
                    for rect in (0, 1):
                        yield 2 + (carry == "bbox") + rect + (seg == "col") * 0.5, \
                            _base(bg=bgfix, seg=seg, static="tail", dir="tail", dist="tail", carry=carry,
                                  rectify=rect)
            # 2a. shape-intrinsic direction (the binding tails use): toward / away from the object's open side,
            #     the side chosen per object colour (induced), constant step k from the same domain as 1.
            for seg in ("c4", "c8"):
                for k in (1, 2, 3):
                    for mode in ("move", "copy"):
                        yield 3.6 + k * 0.1 + (mode == "copy") * 0.05 + (seg == "c8") * 0.02, \
                            _base(bg=bgfix, seg=seg, static="none", dir="open", dist=("k", k), mode=mode)
            # 2b. split halves (band of a vanishing colour)
            if mk:
                yield 3, _base(bg=bgfix, seg="c8", static="split", dir="away", dist="split", mk=mk)
            # 3. contact slides
            for seg in ("c8", "c4", "col", "rect"):
                for static in ("none", "ground", "learned", "wall", "largest"):
                    if static == "learned" and not ls:
                        continue
                    for gap in (0, 1):
                        sc = 3 + gap + (static != "none") * 0.5 + ("c8", "c4", "col", "rect").index(seg) * 0.25
                        if static != "largest":
                            for d in dirs4:
                                yield sc, _base(bg=bgfix, seg=seg, static=static, dir=("fix", d), gap=gap, ls=ls)
                        if static != "ground":
                            for collide in ("all", "same"):
                                yield sc + 0.5 + (collide == "same") * 0.25, \
                                    _base(bg=bgfix, seg=seg, static=static, dir="table", gap=gap,
                                          collide=collide, ls=ls)
                        if static not in ("none", "ground"):
                            yield sc + 0.75, _base(bg=bgfix, seg=seg, static=static, dir="toward", gap=gap,
                                                   ls=ls)

        seen_sig = {}
        side_cache = {}
        clist = list(cands())
        order = sorted(range(len(clist)), key=lambda i: (clist[i][0], i))
        for cost, P in (clist[i] for i in order):
            ss = segs_for(P["seg"])
            if ss is None:
                continue
            # skip segmentations identical (on training inputs) to a cheaper one
            if P["seg"] != "all":
                sig = tuple(tuple(tuple(o["cells"]) for o in s) for s in ss)
                first = seen_sig.setdefault(sig, P["seg"])
                if first != P["seg"]:
                    P = dict(P, seg=first)
                    ss = segs_for(first)
            if P["static"] == "ground" and not all(
                    any(_touches(o["cells"], P["dir"][1], len(p["input"]), len(p["input"][0])) for o in s)
                    for p, s in zip(train, ss)):
                continue
            if P["static"] == "wall" and not all(
                    any(_is_wall(o["cells"], len(p["input"]), len(p["input"][0])) for o in s)
                    for p, s in zip(train, ss)):
                continue
            if P["dist"] == "tail" and not any(_tail(o["cells"]) for o in ss[0]):
                continue
            if P["dir"] == "open":
                sk = (P["seg"], P["dist"][1])
                if sk not in side_cache:
                    lit = _induce_side(train, ss, bgs, P["dist"][1])
                    kp = [{o["key"] for o in s if _open_vec(o["cells"]) != STAY} for s in ss]
                    side_cache[sk] = None if lit is None else _key_roles(train, bgs, lit, kp)
                sgn = side_cache[sk]
                if sgn is None:
                    continue
                P["sgn"] = sgn
            if P["dir"] == "table":
                kp = []
                for p, s, bg in zip(train, ss, bgs):
                    ks = {o["key"] for o in s}
                    if P["static"] == "learned":
                        ks -= {CR.rank_colour(p["input"], k, bg) for k in ls}
                    kp.append(ks)
                keys = set().union(*kp)
                if len(keys) < 2 and P["collide"] == "same":
                    continue
                dd = disp  # per-colour displacements do not depend on which other colours are included
                table = {k: _vec_dir(dd[k][0] / dd[k][2], dd[k][1] / dd[k][2]) for k in keys if k in dd}
                if len({v for v in table.values()}) < 2:
                    continue
                rt = _key_roles(train, bgs, table, kp)      # direction table keyed by ink-rank roles
                if rt is None:
                    continue
                P["table"] = rt
            key = repr(sorted((k, repr(v)) for k, v in P.items()))
            if key in tried:
                continue
            tried.add(key)
            try:
                r = _fit(train, P, ss)
            except Exception:
                r = None
            if r is None:
                continue
            cmap, fill = r
            rr = _rolify(train, bgs, cmap, fill, N)
            if rr is None:
                continue
            rcmap, rfill = rr
            fn = _make(P, rcmap, rfill, N)
            if not all(fn(p["input"]) == p["output"] for p in train):
                continue
            found += 1
            yield _name(P, rcmap, rfill), cost + (len(cmap) > 0) + (fill is not None), fn
            if found >= max_out:
                return


FAMILIES = [fam]
