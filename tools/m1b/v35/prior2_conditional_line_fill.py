"""Prior family "conditional_line_fill" (test-blind; anti-unified from the member one-offs and their train pairs only).

One generator, FILL: optionally rebuild the canvas (tile the input, or place copies on the main diagonal), then
iterate over the rows and/or columns inside a scope (the grid, the grid's interior inset by one, or the bounding
box of the non-background cells), evaluate one line predicate on the line's cells inside the scope, and fill the
background cells of every qualifying line -- inside the scope or along the whole grid line -- with a learned
colour, or with the nearest coloured cell met when scanning the line from one end.
Shared steps written once: canvas, background, scope, the line loop, predicates and fills, and the induction of
canvas / fill colour from the training diffs.  Members differ only in parameter values:
  c1d99e64  bg=literal (the changed colour), axes=both, scope=grid,  pred=empty,    fill=literal
  2bee17df  axes=both, scope=inset, pred=empty,    fill=literal
  da2b0fe3  axes=both, scope=bbox,  pred=empty,    fill=literal, extent=grid
  4612dd53  axes=both, scope=bbox,  pred=dense,    fill=literal
  f5b8619d  canvas=tile, axes=cols, scope=grid, pred=occupied, fill=literal
  fb791726  canvas=diag, axes=rows, scope=grid, pred=flanked,  fill=literal
  17b80ad2  axes=cols, scope=grid, pred=anchored(last), fill=propagate(last)
Uncovered (would need member-specific steps): 770cc55f (fill only the gap between divider and the larger bar),
782b5218 (clears the segment before the wall and overwrites colours), 834ec97d (pixel moves, parity columns),
a64e4611 (maximal empty rectangles with margins), c92b942c (extra diagonal decoration), e45ef808 (two extremal
profile columns with two colours).
"""

CARD = "prior_conditional_line_fill"
CONCEPT = "conditional_line_fill"
MEMBERS = ["17b80ad2", "2bee17df", "4612dd53", "770cc55f", "782b5218", "834ec97d", "a64e4611", "c1d99e64",
           "c92b942c", "da2b0fe3", "e45ef808", "f5b8619d", "fb791726"]
READING = {
    "generator": "After an optional canvas step (tile the input, or copy it along the main diagonal), every row "
                 "and/or column inside the scope (grid, interior inset by one, or bounding box of the non-background "
                 "cells) whose in-scope cells satisfy the line predicate has its background cells -- in the scope or "
                 "along the whole grid line -- filled with a learned colour, or with the nearest coloured cell met "
                 "when scanning the line from one end.",
    "stop": "One pass over the lines; predicates are evaluated on the (canvas) input, never on partially filled "
            "output; a propagated fill stops at nothing (it runs to the far end of the line, restarting at every "
            "coloured cell).",
    "params": "canvas ∈ {same, tile, diag} · bg ∈ {most frequent, literal (the changed cells' input colour)} · "
              "axes ∈ {rows, cols, both} · scope ∈ {grid, inset, bbox} · predicate ∈ {empty, occupied, dense, "
              "flanked, anchored(first|last)} · fill ∈ {literal c, propagate(first|last)} · extent ∈ {scope, grid}",
    "participants": "bg = most frequent colour of the (canvas) input, or the literal colour every changed cell had. "
                    "empty = all in-scope cells bg; occupied = some non-bg cell; dense = more than half non-bg "
                    "(a broken line); flanked = empty and the two neighbouring lines hold the same colour at some "
                    "common position; anchored(s) = the in-scope end cell at side s is non-bg. literal c = the "
                    "single output colour of all changed cells; propagate(s) = scanning from side s, each bg cell "
                    "takes the colour of the last non-bg cell passed.",
    "preconditions": "Output size = input size times (ky, kx) with the same factors in every pair (canvas), some "
                     "cell changes, every changed cell is bg in the canvas input (a fill never overwrites colour), "
                     "literal fills need one changed-to colour, and the whole program reproduces every pair.",
}


def _mode(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


# ------------------------------------------------------------------ canvas
def _canvas(g, kind, ky, kx):
    if kind == "same":
        return [list(r) for r in g]
    if kind == "tile":
        return [list(r) * kx for _ in range(ky) for r in g]
    # diag: copies of g on the main diagonal of a ky x ky block canvas, background elsewhere
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
    rs = [r for r in range(H) if any(v != bg for v in g[r])]
    if not rs:
        return None
    cs = [c for c in range(W) if any(g[r][c] != bg for r in range(H))]
    return rs[0], rs[-1], cs[0], cs[-1]


# ------------------------------------------------------------------ predicates on in-scope line values
def _pred(name, vals, prev, nxt, bg):
    if name == "empty":
        return all(v == bg for v in vals)
    if name == "occupied":
        return any(v != bg for v in vals)
    if name == "dense":
        return 2 * sum(1 for v in vals if v != bg) > len(vals)
    if name == "flanked":
        if prev is None or nxt is None or any(v != bg for v in vals):
            return False
        return any(a != bg and a == b for a, b in zip(prev, nxt))
    if name == "anchored_first":
        return vals[0] != bg
    if name == "anchored_last":
        return vals[-1] != bg
    return False


PREDS = ("empty", "occupied", "dense", "flanked", "anchored_first", "anchored_last")
PRED_COST = {"empty": 0.0, "occupied": 0.1, "dense": 0.2, "anchored_first": 0.2, "anchored_last": 0.2,
             "flanked": 0.4}                    # flanked is compound (empty AND matching neighbours)


def _apply(g, bg, axes, scope, pred, fill, extent):
    """g is the canvas input; returns the filled grid, or None when the scope is undefined."""
    H, W = len(g), len(g[0])
    box = _scope(g, bg, scope)
    if box is None:
        return None
    r0, r1, c0, c1 = box
    out = [list(r) for r in g]
    for axis in axes:
        if axis == "rows":
            idxs = range(r0, r1 + 1)
            seg = [[(i, c) for c in range(c0, c1 + 1)] for i in idxs]
            full = [[(i, c) for c in range(W)] for i in idxs]
        else:
            idxs = range(c0, c1 + 1)
            seg = [[(r, j) for r in range(r0, r1 + 1)] for j in idxs]
            full = [[(r, j) for r in range(H)] for j in idxs]
        vals = [[g[r][c] for r, c in s] for s in seg]
        n = len(seg)
        for k in range(n):
            if not _pred(pred, vals[k], vals[k - 1] if k > 0 else None, vals[k + 1] if k + 1 < n else None, bg):
                continue
            cells = seg[k] if extent == "scope" else full[k]
            if fill[0] == "literal":
                for r, c in cells:
                    if g[r][c] == bg:
                        out[r][c] = fill[1]
            else:
                order = cells if fill[1] == "first" else cells[::-1]
                cur = None
                for r, c in order:
                    v = g[r][c]
                    if v != bg:
                        cur = v
                    elif cur is not None:
                        out[r][c] = cur
    return out


def _make(canvas, ky, kx, bgopt, axes, scope, pred, fill, extent):
    def fn(grid):
        g = _canvas(grid, canvas, ky, kx)
        bg = _mode(g) if bgopt is None else bgopt
        out = _apply(g, bg, axes, scope, pred, fill, extent)
        return g if out is None else out
    return fn


AXES = (("rows", "cols"), ("rows",), ("cols",))
SCOPES = ("grid", "bbox", "inset")


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs:
        return
    # canvas factors, shared by every pair
    fac = None
    for I, O in pairs:
        H, W, h, w = len(I), len(I[0]), len(O), len(O[0])
        if not H or not W or h % H or w % W:
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
        # diffs: changed cells, their input and output colours
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
        else:
            bgopts.append((src, 0.5))           # literal background: the colour every changed cell had
        fills = []
        if len(dsts) == 1:
            fills.append((("literal", next(iter(dsts))), 0.0))
        fills += [(("prop", "first"), 0.3), (("prop", "last"), 0.3)]
        for bgopt, bc in bgopts:
            for ai, axes in enumerate(AXES):
                for si, scope in enumerate(SCOPES):
                    for pred in PREDS:
                        for fill, fc in fills:
                            for ei, extent in enumerate(("scope", "grid")):
                                if scope == "grid" and extent == "grid":
                                    continue
                                cost = 1 + ci + bc + 0.1 * ai + 0.2 * si + PRED_COST[pred] + fc + 0.1 * ei
                                fn = _make(canvas, ky, kx, bgopt, axes, scope, pred, fill, extent)
                                ok = True
                                for (I, O), (G, _) in zip(pairs, cps):
                                    bg = _mode(G) if bgopt is None else bgopt
                                    try:
                                        res = _apply(G, bg, axes, scope, pred, fill, extent)
                                    except Exception:
                                        res = None
                                    if res != O:
                                        ok = False
                                        break
                                if ok:
                                    name = "fill_%s_%s_%s_%s_%s_%s%s" % (
                                        canvas, "+".join(axes), scope, pred,
                                        fill[0] + str(fill[1]), extent,
                                        "" if bgopt is None else "_bg%d" % bgopt)
                                    found.append((name, round(cost, 3), fn))
    found.sort(key=lambda t: t[1])
    for f in found[:3]:
        yield f


FAMILIES = [fam]
