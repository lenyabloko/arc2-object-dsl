"""Prior family stamp_stencil_at_anchors (test-blind; anti-unified from the member one-offs and train pairs).

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

CARD = "prior_stamp_stencil_at_anchors"
CONCEPT = "stamp_stencil_at_anchors"
MEMBERS = ["10fcaaa3", "11e1fe23", "140c817e", "264363fd", "310f3251", "396d80d7", "3f23242b", "58f5dbd5",
           "67a423a3", "ac3e2b04", "ac605cbb", "dfadab01", "e9614598", "ecdecbb3", "f35d900a"]
READING = {
    "generator": "Find anchor points (every coloured cell, crossings of full lines, the centre of the marker "
                 "bounding box, or points where a dot's ray meets a full line) and paste on each a small stencil "
                 "induced from training, whose cells take role colours (constant, anchor colour, other colour, "
                 "hit-line colour, quadrant participant colour), optionally with full lines through stencil "
                 "rows/columns and the ray trail, painting only where the guard allows.",
    "stop": "One stencil per anchor, clipped at the edge (or wrapped on a tiled canvas); lines run edge to edge; "
            "trails run from the dot to the hit line; nothing else changes.",
    "params": "canvas ∈ {same, tile, tile+wrap} · anchor ∈ {cell, cross, centre, rayhit} · "
              "key ∈ {none, anchor colour} · guard ∈ {bg, free bg, all} · R ∈ {1,2,3} · lines ∈ {0,1} · "
              "trail ∈ {0,1} · role preference ∈ {relational, constant} · stencil offsets/roles (induced)",
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

ROLES_REL = ("own", "other", "line", "quad")
DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
RMAX = 3


# ---------------------------------------------------------------- shared participants
def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _sgn(x):
    return (x > 0) - (x < 0)


def _canvas(g, mode, ratio):
    if mode == "same":
        return [list(r) for r in g]
    ky, kx = ratio
    h, w = len(g), len(g[0])
    return [[g[y % h][x % w] for x in range(w * kx)] for y in range(h * ky)]


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
                        a, b, path = y + dy, x + dx, []
                        while 0 <= a < H and 0 <= b < W:
                            if (dy and a in rl) or (dx and b in cl):
                                res.append((a, b, {"own": v, "line": rl[a] if dy else cl[b], "trail": path}))
                                break
                            path.append((a, b))
                            a += dy
                            b += dx
    return res


def _value(role, ctx, dy, dx):
    if isinstance(role, int):
        return role
    if role == "quad":
        q = ctx.get("quad")
        return None if q is None else q.get((_sgn(dy), _sgn(dx)))
    return ctx.get(role)


def _prep(g, P):
    cv = _canvas(g, P["canvas"], P["ratio"])
    bg = _bg(g)
    return cv, bg, _anchors(cv, bg, P["anchor"]), _guard_mask(cv, bg, P["guard"])


# ---------------------------------------------------------------- induction
def _learn_stencil(data, P):
    """Per (key, offset) role statistics over all anchors of all pairs."""
    wrap, keyed = P["wrap"], P["key"] == "colour"
    st = {}
    for cv, bg, anc, gm, out in data:
        H, W = len(cv), len(cv[0])
        for r, c, ctx in anc:
            k = ctx.get("own") if keyed else None
            for dy in range(-RMAX, RMAX + 1):
                for dx in range(-RMAX, RMAX + 1):
                    y, x = r + dy, c + dx
                    if wrap:
                        y, x = y % H, x % W
                    elif not (0 <= y < H and 0 <= x < W):
                        continue
                    if not gm[y][x]:
                        continue
                    ov, iv = out[y][x], cv[y][x]
                    s = st.get((k, dy, dx))
                    if s is None:
                        s = st[(k, dy, dx)] = {"alive": set(ROLES_REL), "consts": set(), "chg": False}
                    s["consts"].add(ov)
                    if ov != iv:
                        s["chg"] = True
                    for role in tuple(s["alive"]):
                        v = _value(role, ctx, dy, dx)
                        if not ((v is None and ov == iv) or v == ov):
                            s["alive"].discard(role)
    return st


def _choose(st, R, pref):
    sten = {}
    for (k, dy, dx), s in sorted(st.items(), key=lambda t: (str(t[0][0]), t[0][1], t[0][2])):
        if max(abs(dy), abs(dx)) > R or not s["chg"]:
            continue
        rel = [r for r in ROLES_REL if r in s["alive"]]
        con = [min(s["consts"])] if len(s["consts"]) == 1 else []
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
            for role in ("own", "other", "line", "const"):
                ok, cval, chg = True, None, False
                for cv, bg, anc, gm, out in data:
                    H, W = len(cv), len(cv[0])
                    for r, c, ctx in anc:
                        y0 = r + d if axis == "row" else c + d
                        if not (0 <= y0 < (H if axis == "row" else W)):
                            continue
                        cells = ([(y0, x) for x in range(W) if abs(x - c) > R] if axis == "row"
                                 else [(y, y0) for y in range(H) if abs(y - r) > R])
                        if not cells:
                            continue
                        if role == "const":
                            cnt = Counter(out[y][x] for y, x in cells)
                            v, n = cnt.most_common(1)[0]
                            if cval is None:
                                cval = v
                            elif v != cval:
                                ok = False
                                break
                        else:
                            v = ctx.get(role)
                            if v is None:
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
                    best = cval if role == "const" else role
                    break
            if best is not None:
                found[axis].append((d, best))
    return found


# ---------------------------------------------------------------- drawing
def _render(g, P):
    cv, bg, anc, gm = _prep(g, P)
    H, W = len(cv), len(cv[0])
    out = [r[:] for r in cv]
    keyed = P["key"] == "colour"
    lines = P["lines"]
    if lines:
        lg = gm if P["guard"] != "free" else _guard_mask(cv, bg, "bg")
        for r, c, ctx in anc:
            for d, role in lines["row"]:
                y = r + d
                v = _value(role, ctx, 0, 0)
                if v is not None and 0 <= y < H:
                    for x in range(W):
                        if lg[y][x]:
                            out[y][x] = v
            for d, role in lines["col"]:
                x = c + d
                v = _value(role, ctx, 0, 0)
                if v is not None and 0 <= x < W:
                    for y in range(H):
                        if lg[y][x]:
                            out[y][x] = v
    if P["trail"]:
        for r, c, ctx in anc:
            for y, x in ctx.get("trail", ()):
                if cv[y][x] == bg:
                    out[y][x] = ctx["own"]
    sten, wrap = P["stencil"], P["wrap"]
    for r, c, ctx in anc:
        for dy, dx, role in sten.get(ctx.get("own") if keyed else None, ()):
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
        return [("same", None, False)]
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
    for canvas, ratio, wrap in _canvases(train):
        for kind in ("cell", "cross", "centre", "rayhit"):
            pre = []
            for p in train:
                cv = _canvas(p["input"], canvas, ratio)
                bg = _bg(p["input"])
                anc = _anchors(cv, bg, kind)
                if not anc or len(anc) > 1000:
                    break
                pre.append((cv, bg, anc, p["output"]))
            if len(pre) != len(train):
                continue
            for key in ("none", "colour"):
                for guard in ("bg", "free", "all"):
                    P = {"canvas": canvas, "ratio": ratio, "wrap": wrap, "anchor": kind, "key": key, "guard": guard}
                    data = [(cv, bg, anc, _guard_mask(cv, bg, guard), out) for cv, bg, anc, out in pre]
                    learned.append((P, data, _learn_stencil(data, P)))
    if not learned:
        return
    cands = []
    for R in range(1, RMAX + 1):
        for i, (P, data, st) in enumerate(learned):
            for pref in ("rel", "const"):
                sten = _choose(st, R, pref)
                if not sten:
                    continue
                for trail in ((False, True) if P["anchor"] == "rayhit" else (False,)):
                    for use_lines in (False, True):
                        cost = R + (P["key"] != "none") + use_lines + trail + 0.5 * (pref != "rel")
                        cands.append((cost, len(cands), i, R, pref, sten, trail, use_lines))
    cands.sort(key=lambda t: (t[0], t[1]))
    found, seen = 0, set()
    for cost, _, i, R, pref, sten, trail, use_lines in cands:
        P, data, st = learned[i]
        lines = _learn_lines(data, R, P["key"] == "colour") if use_lines else None
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
            name = ("stamp[canvas=%s%s,anchor=%s,key=%s,guard=%s,R=%d,pref=%s,trail=%d,lines=%d]"
                    % (P["canvas"], "+wrap" if P["wrap"] else "", P["anchor"], P["key"], P["guard"], R, pref,
                       trail, bool(lines)))
            yield (name, 1 + cost, fn)
            found += 1
            if found >= 3:
                return


FAMILIES = [fam]
