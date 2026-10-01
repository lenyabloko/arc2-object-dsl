"""Prior family "conditional_line_fill", pass 3 (test-blind; specialised over FITTED BINDINGS, training pairs only).

BINDINGS (fitted members of the pass-2 family; every induced value and the role that explains it in every pair)
  member    value            literal seen          role that explains it (all train pairs)
  c1d99e64  bg               0                     bg <- minority colour of the input (the 'other' colour varies
                                                   8/1/3, so most-frequent fails; least-frequent always = 0)
            fill colour      2                     colour <- the one colour absent from every input (constant)
            predicate/axes   empty, rows+cols      line <- all in-scope cells are bg
  2bee17df  scope            inset by 1            scope <- bounding box of the background cells (the open
                                                   interior enclosed by the coloured frame); = inset here
            fill colour      3                     colour <- new colour (constant)
  da2b0fe3  scope / extent   bbox / whole line     scope <- object bbox; extent <- grid line through it
            fill colour      3                     colour <- new colour
  4612dd53  scope, pred      bbox, dense           scope <- object bbox; line <- broken side (> half inked)
            fill colour      2                     colour <- new colour
  f5b8619d  canvas           tile 2x2              factor <- output/input shape ratio (shared by all pairs)
            pred             occupied (cols)       line <- holds a coloured cell; colour 8 <- new colour
  fb791726  canvas           diag 2x2              copies <- shape ratio; pred flanked; colour 3 <- new colour
  17b80ad2  pred, side       anchored(last),       side <- the end that carries the anchor (marker row);
                             propagate(last)       colour <- nearest coloured cell met from that end
Specialisation menu derived from the table (role-bound alternatives added to the domains, cheaper than the literal
they replace; the literal stays in the domain so every old fit survives):
  bg      += minority          (c1d99e64: literal 0 -> least-frequent colour)
  scope   += bgbox             (2bee17df: inset 1 -> bbox of the background cells)
  side    += heavier           (17b80ad2 / anchored side: first|last -> the end whose end cell belongs to the
                                larger same-colour component; a bg end weighs 0; a tie selects no side)
Shared steps added (no member branches):
  region  += gap(side)         fill only the first background run met from the chosen end (after its ink)
  pred    += anchored_both, most_empty, least_empty (one extremal line, ties -> last or first)
  passes  : when the changed cells go to 2-3 colours, one FILL pass per colour (each pass fitted on the cells that
            changed to its colour), all passes read the same canvas input.
Newly fitted through these: 770cc55f (cols, anchored_both, gap(heavier) <- side of the larger end bar),
e45ef808 (two passes: most_empty -> colour A, least_empty(ties last) -> colour B, bg <- changed colour).
Still uncovered: 782b5218 (overwrites ink), 834ec97d (pixel moves), a64e4611 (maximal rectangles with margins),
c92b942c (colour-1 pass fits; colour-3 is a diagonal decoration, not a line fill).
"""

CARD = "prior3_conditional_line_fill"
CONCEPT = "conditional_line_fill"
MEMBERS = ["17b80ad2", "2bee17df", "4612dd53", "770cc55f", "782b5218", "834ec97d", "a64e4611", "c1d99e64",
           "c92b942c", "da2b0fe3", "e45ef808", "f5b8619d", "fb791726"]
READING = {
    "generator": "After an optional canvas step (tile the input, or copy it along the main diagonal), every row "
                 "and/or column inside the scope (grid, interior inset by one, bounding box of the non-background "
                 "cells, or bounding box of the background cells) whose in-scope cells satisfy the line predicate "
                 "has its background cells -- all of them in the scope or along the whole grid line, or only the "
                 "first background run met from one end -- filled with a learned colour, or with the nearest "
                 "coloured cell met when scanning from one end. When changed cells take several colours, one such "
                 "pass per colour.",
    "stop": "One pass over the lines per colour; predicates are evaluated on the (canvas) input, never on partially "
            "filled output; a propagated fill runs to the far end of the line, restarting at every coloured cell; "
            "a gap fill stops at the first coloured cell after the run.",
    "params": "canvas ∈ {same, tile, diag} · bg ∈ {most frequent, minority (least frequent), literal} · "
              "axes ∈ {rows, cols, both} · scope ∈ {grid, bbox, bgbox, inset} · predicate ∈ {empty, occupied, "
              "dense, flanked, anchored(first|last|both), most_empty(last|first), least_empty(last|first)} · "
              "fill ∈ {literal c, propagate(side), gap(side, c)} · side ∈ {heavier, first, last} · "
              "extent ∈ {scope, grid} · passes = one per changed-to colour",
    "participants": "bg = most frequent / least frequent colour of the (canvas) input, or the literal colour every "
                    "changed cell had. empty = all in-scope cells bg; occupied = some non-bg cell; dense = more "
                    "than half non-bg; flanked = empty and the two neighbouring lines hold the same colour at some "
                    "common position; anchored(s) = the in-scope end cell(s) non-bg; most/least_empty = the one "
                    "line with the most / fewest bg cells (ties broken by position). heavier = the end whose end "
                    "cell lies in the larger same-colour 4-connected component (bg end weighs 0, tie = no side). "
                    "literal c = the single output colour of the pass's changed cells; propagate(s) = scanning from "
                    "s each bg cell takes the colour of the last non-bg cell passed; gap(s, c) = skip the ink at "
                    "end s, colour the following bg run c.",
    "preconditions": "Output size = input size times (ky, kx) with the same factors in every pair (canvas), some "
                     "cell changes, every changed cell is bg in the canvas input (a fill never overwrites colour), "
                     "each pass writes one colour (or propagates), and the whole program reproduces every pair.",
}


def _count(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return cnt


def _mode(g):
    cnt = _count(g)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _minority(g):
    cnt = _count(g)
    return min(sorted(cnt), key=lambda k: cnt[k])


def _bg_of(g, bgopt):
    if bgopt is None:
        return _mode(g)
    if bgopt == "minority":
        return _minority(g)
    return bgopt


# ------------------------------------------------------------------ canvas
def _canvas(g, kind, ky, kx):
    if kind == "same":
        return [list(r) for r in g]
    if kind == "tile":
        return [list(r) * kx for _ in range(ky) for r in g]
    H, W = len(g), len(g[0])
    bg = _mode(g)
    out = [[bg] * (W * kx) for _ in range(H * ky)]
    for t in range(ky):
        for r in range(H):
            row = out[t * H + r]
            for c in range(W):
                row[t * W + c] = g[r][c]
    return out


# ------------------------------------------------------------------ scope box (r0, r1, c0, c1) or None
def _scope(g, bg, kind):
    H, W = len(g), len(g[0])
    if kind == "grid":
        return 0, H - 1, 0, W - 1
    if kind == "inset":
        if H < 3 or W < 3:
            return None
        return 1, H - 2, 1, W - 2
    if kind == "bbox":
        rs = [r for r in range(H) if any(v != bg for v in g[r])]
        if not rs:
            return None
        cs = [c for c in range(W) if any(g[r][c] != bg for r in range(H))]
        return rs[0], rs[-1], cs[0], cs[-1]
    # bgbox: bounding box of the background cells
    rs = [r for r in range(H) if any(v == bg for v in g[r])]
    if not rs:
        return None
    cs = [c for c in range(W) if any(g[r][c] == bg for r in range(H))]
    return rs[0], rs[-1], cs[0], cs[-1]


# ------------------------------------------------------------------ line predicates (select indices of lines)
def _select(name, vals, bg):
    n = len(vals)
    if name in ("most_empty", "least_empty", "most_empty_first", "least_empty_first"):
        if not n:
            return []
        cnts = [sum(1 for v in vs if v == bg) for vs in vals]
        tgt = max(cnts) if name.startswith("most") else min(cnts)
        ks = [k for k in range(n) if cnts[k] == tgt]
        return [ks[0]] if name.endswith("_first") else [ks[-1]]
    out = []
    for k in range(n):
        vs = vals[k]
        if name == "empty":
            ok = all(v == bg for v in vs)
        elif name == "occupied":
            ok = any(v != bg for v in vs)
        elif name == "dense":
            ok = 2 * sum(1 for v in vs if v != bg) > len(vs)
        elif name == "flanked":
            if k == 0 or k + 1 >= n or any(v != bg for v in vs):
                ok = False
            else:
                ok = any(a != bg and a == b for a, b in zip(vals[k - 1], vals[k + 1]))
        elif name == "anchored_first":
            ok = vs[0] != bg
        elif name == "anchored_last":
            ok = vs[-1] != bg
        elif name == "anchored_both":
            ok = vs[0] != bg and vs[-1] != bg
        else:
            ok = False
        if ok:
            out.append(k)
    return out


PREDS = ("empty", "occupied", "dense", "anchored_first", "anchored_last", "anchored_both", "flanked",
         "most_empty", "least_empty", "most_empty_first", "least_empty_first")
PRED_COST = {"empty": 0.0, "occupied": 0.1, "dense": 0.2, "anchored_first": 0.2, "anchored_last": 0.2,
             "anchored_both": 0.25, "flanked": 0.4, "most_empty": 0.3, "least_empty": 0.3,
             "most_empty_first": 0.35, "least_empty_first": 0.35}


# ------------------------------------------------------------------ components (for the 'heavier' side role)
def _components(g, bg):
    H, W = len(g), len(g[0])
    size = [[0] * W for _ in range(H)]
    seen = [[False] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] == col:
                        seen[yy][xx] = True
                        stack.append((yy, xx))
            for y, x in cells:
                size[y][x] = len(cells)
    return size


def _side(side, seg, comp):
    """'first' / 'last', or the role 'heavier' resolved on this line (None when undecided)."""
    if side != "heavier":
        return side
    a, b = seg[0], seg[-1]
    sa, sb = comp[a[0]][a[1]], comp[b[0]][b[1]]
    if sa == sb:
        return None
    return "first" if sa > sb else "last"


# ------------------------------------------------------------------ one fill pass
class _Ctx:
    """Per-grid cache of scope boxes, line cells/values, selections and components."""

    def __init__(self, g, bg):
        self.g, self.bg = g, bg
        self.H, self.W = len(g), len(g[0])
        self.boxes, self.lines, self.sels, self.comp = {}, {}, {}, None

    def box(self, scope):
        if scope not in self.boxes:
            self.boxes[scope] = _scope(self.g, self.bg, scope)
        return self.boxes[scope]

    def line(self, axis, scope):
        key = (axis, scope)
        if key not in self.lines:
            box = self.box(scope)
            if box is None:
                self.lines[key] = None
            else:
                r0, r1, c0, c1 = box
                g, H, W = self.g, self.H, self.W
                if axis == "rows":
                    idxs = range(r0, r1 + 1)
                    seg = [[(i, c) for c in range(c0, c1 + 1)] for i in idxs]
                    full = [[(i, c) for c in range(W)] for i in idxs]
                else:
                    idxs = range(c0, c1 + 1)
                    seg = [[(r, j) for r in range(r0, r1 + 1)] for j in idxs]
                    full = [[(r, j) for r in range(H)] for j in idxs]
                vals = [[g[r][c] for r, c in s] for s in seg]
                self.lines[key] = (list(idxs), seg, full, vals)
        return self.lines[key]

    def sel(self, axis, scope, pred):
        key = (axis, scope, pred)
        if key not in self.sels:
            ln = self.line(axis, scope)
            self.sels[key] = None if ln is None else _select(pred, ln[3], self.bg)
        return self.sels[key]

    def components(self):
        if self.comp is None:
            self.comp = _components(self.g, self.bg)
        return self.comp


def _pass(ctx, out, axes, scope, pred, fill, extent):
    """Writes one pass into out (cells are read from ctx.g); False when the scope is undefined."""
    g, bg = ctx.g, ctx.bg
    for axis in axes:
        ln = ctx.line(axis, scope)
        if ln is None:
            return False
        _, seg, full, _ = ln
        for k in ctx.sel(axis, scope, pred):
            cells = seg[k] if extent == "scope" else full[k]
            kind = fill[0]
            if kind == "literal":
                c = fill[1]
                for r, cc in cells:
                    if g[r][cc] == bg:
                        out[r][cc] = c
                continue
            side = _side(fill[1], seg[k], ctx.components() if fill[1] == "heavier" else None)
            if side is None:
                continue
            order = cells if side == "first" else cells[::-1]
            if kind == "prop":
                cur = None
                for r, cc in order:
                    v = g[r][cc]
                    if v != bg:
                        cur = v
                    elif cur is not None:
                        out[r][cc] = cur
            else:                               # gap: skip the ink at that end, colour the following bg run
                i, n = 0, len(order)
                while i < n and g[order[i][0]][order[i][1]] != bg:
                    i += 1
                while i < n and g[order[i][0]][order[i][1]] == bg:
                    out[order[i][0]][order[i][1]] = fill[2]
                    i += 1
    return True


def _run(G, bgopt, passes, ctx=None):
    bg = _bg_of(G, bgopt)
    if ctx is None:
        ctx = _Ctx(G, bg)
    out = [list(r) for r in G]
    for axes, scope, pred, fill, extent in passes:
        if not _pass(ctx, out, axes, scope, pred, fill, extent):
            return None
    return out


def _make(canvas, ky, kx, bgopt, passes):
    def fn(grid):
        g = _canvas(grid, canvas, ky, kx)
        out = _run(g, bgopt, passes)
        return g if out is None else out
    return fn


AXES = (("rows", "cols"), ("rows",), ("cols",))
SCOPES = ("grid", "bbox", "bgbox", "inset")
SCOPE_COST = {"grid": 0.0, "bbox": 0.2, "bgbox": 0.3, "inset": 0.4}
SIDES = (("heavier", 0.28), ("first", 0.3), ("last", 0.3))


def _search(ctxs, targets, colours):
    """All single-pass configs reproducing every target (target = canvas input with this pass's cells changed).
    Fast rejection: a pass along a single axis must select every line that holds a changed cell."""
    fills = []
    if len(colours) == 1:
        c = next(iter(colours))
        fills.append((("literal", c), 0.0))
        for s, sc in SIDES:
            fills.append((("gap", s, c), 0.1 + sc))
    for s, sc in SIDES:
        fills.append((("prop", s), sc))
    chg = []
    for ctx, O in zip(ctxs, targets):
        g = ctx.g
        rows, cols = set(), set()
        for r in range(ctx.H):
            gr, orow = g[r], O[r]
            for c in range(ctx.W):
                if gr[c] != orow[c]:
                    rows.add(r)
                    cols.add(c)
        chg.append({"rows": rows, "cols": cols})
    found = []
    for ai, axes in enumerate(AXES):
        for scope in SCOPES:
            for pred in PREDS:
                viable = True
                for ctx, ch in zip(ctxs, chg):
                    for axis in axes:
                        ln = ctx.line(axis, scope)
                        if ln is None:
                            viable = False
                            break
                        if len(axes) == 1:
                            idxs = ln[0]
                            sel = set(idxs[k] for k in ctx.sel(axis, scope, pred))
                            if not ch[axis] <= sel:
                                viable = False
                                break
                    if not viable:
                        break
                if not viable:
                    continue
                for fill, fc in fills:
                    for ei, extent in enumerate(("scope", "grid")):
                        if scope == "grid" and extent == "grid":
                            continue
                        p = (axes, scope, pred, fill, extent)
                        ok = True
                        for ctx, O in zip(ctxs, targets):
                            out = [list(r) for r in ctx.g]
                            try:
                                if not _pass(ctx, out, axes, scope, pred, fill, extent) or out != O:
                                    ok = False
                            except Exception:
                                ok = False
                            if not ok:
                                break
                        if ok:
                            cost = 0.1 * ai + SCOPE_COST[scope] + PRED_COST[pred] + fc + 0.1 * ei
                            if len(axes) == 2 and pred.startswith(("most", "least")):
                                cost += 0.3             # an extremal line is one line of one axis
                            found.append((round(cost, 3), p))
    found.sort(key=lambda t: t[0])
    return found


def _pname(p):
    axes, scope, pred, fill, extent = p
    return "%s_%s_%s_%s_%s" % ("+".join(axes), scope, pred, "".join(str(x) for x in fill), extent)


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs:
        return
    fac = None
    for I, O in pairs:
        if not I or not I[0] or not O or not O[0]:
            return
        H, W, h, w = len(I), len(I[0]), len(O), len(O[0])
        if h % H or w % W:
            return
        f = (h // H, w // W)
        if fac is None:
            fac = f
        elif fac != f:
            return
    ky, kx = fac
    if ky > 5 or kx > 5:
        return
    canvases = ["same"] if (ky, kx) == (1, 1) else (["tile", "diag"] if ky == kx else ["tile"])
    found = []
    for ci, canvas in enumerate(canvases):
        cps = [(_canvas(I, canvas, ky, kx), O) for I, O in pairs]
        srcs, dsts, any_change = set(), set(), False
        for G, O in cps:
            for rg, ro in zip(G, O):
                for a, b in zip(rg, ro):
                    if a != b:
                        any_change = True
                        srcs.add(a)
                        dsts.add(b)
        if not any_change or len(srcs) != 1:
            continue                            # a fill only writes background cells: one source colour
        src = next(iter(srcs))
        bgopts = []
        if all(_mode(G) == src for G, _ in cps):
            bgopts.append((None, 0.0))
        elif all(_minority(G) == src for G, _ in cps):
            bgopts.append(("minority", 0.3))    # role-bound: the least frequent colour (c1d99e64)
        if not bgopts or bgopts[0][0] is not None:
            bgopts.append((src, 0.5))           # literal background: the colour every changed cell had
        for bgopt, bc in bgopts:
            ctxs = [_Ctx(G, _bg_of(G, bgopt)) for G, _ in cps]
            if any(ctx.bg != src for ctx in ctxs):
                continue
            base = 1 + ci + bc
            if len(dsts) == 1:
                for cost, p in _search(ctxs, [O for _, O in cps], dsts)[:3]:
                    name = "fill_%s_%s%s" % (canvas, _pname(p), "" if bgopt is None else "_bg%s" % bgopt)
                    found.append((name, round(base + cost, 3), _make(canvas, ky, kx, bgopt, [p])))
            # one pass per changed-to colour (also tried for one colour only via the plain search above)
            if 2 <= len(dsts) <= 3:
                passes, total = [], base + 0.5 * (len(dsts) - 1)
                for c in sorted(dsts):
                    tg = []
                    for G, O in cps:
                        T = [list(r) for r in G]
                        for r in range(len(G)):
                            for x in range(len(G[0])):
                                if O[r][x] == c and G[r][x] != c:
                                    T[r][x] = c
                        tg.append(T)
                    res = _search(ctxs, tg, {c})
                    if not res:
                        passes = None
                        break
                    total += res[0][0]
                    passes.append(res[0][1])
                if passes:
                    if all(_run(G, bgopt, passes) == O for G, O in cps):
                        name = "fill_%s_%s%s" % (canvas, "|".join(_pname(p) for p in passes),
                                                  "" if bgopt is None else "_bg%s" % bgopt)
                        found.append((name, round(total, 3), _make(canvas, ky, kx, bgopt, passes)))
            if len(dsts) >= 2:                  # propagated fills write several colours in one pass
                for cost, p in _search(ctxs, [O for _, O in cps], dsts)[:3]:
                    name = "fill_%s_%s%s" % (canvas, _pname(p), "" if bgopt is None else "_bg%s" % bgopt)
                    found.append((name, round(base + cost, 3), _make(canvas, ky, kx, bgopt, [p])))
    found.sort(key=lambda t: t[1])
    for f in found[:3]:
        yield f


FAMILIES = [fam]
