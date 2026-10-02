"""Reviewer line family for ARC card 291dc1e1 (typography: writing mode).

The input is a "page": one corner cell (the origin) sits where two uniform
ruler lines meet along two page edges.  The rest of the page (the text block)
holds lines of glyphs: bands of non-background cells separated by background
rows/columns; inside a band, glyphs are maximal runs separated by an all-
background cross-section.  The rulers declare the writing mode (which axis is
the inline axis), the origin corner declares where reading starts (inline and
block directions point away from it).  The output lists the glyphs in reading
order, one under the other, each turned so that its reading direction points
right, padded with background to a common width.
"""
from collections import Counter

CARD = "291dc1e1"
LINE = ('Family for 291dc1e1 -- typography: WRITING MODE (text direction / reading order).: The input is a page of '
        '"text": a corner cell marks where reading starts (the origin), and the two ruler lines along the page edges '
        'declare the writing mode. Glyphs (solid multi-coloured blocks) sit on lines (bands of constant thickness '
        'separated by background).')

READING = {
    "generator": "Read the glyphs of the page in writing-mode order (line by line from the origin's side, glyph by glyph "
                 "away from the origin along each line) and draw them one under the other, each turned so its reading "
                 "direction points right (vertical-mode glyphs are rotated sideways, horizontal ones stay upright), "
                 "padded with background to the widest glyph.",
    "stop": "Every glyph of every line is drawn exactly once; the output ends after the last glyph of the last line.",
    "params": "mode_axis ∈ {ruler colour c marks the inline axis, ruler colour c marks the block axis (c induced from "
              "train rulers), geometry: the axis whose bands have constant thickness} · "
              "glyph_turn ∈ {upright (horizontal kept, vertical rotated), rotate (rotation sending reading direction "
              "right), page_up (reading->right, progression->up), page (reading->right, progression->down), none} · "
              "align ∈ {centre-floor, centre-ceil, start, end} · layout ∈ {stack, stack+gap, line, line+gap}",
    "participants": "origin = the one corner cell whose edge row and edge column (without it) are each uniform and both "
                    "differ from it; rulers = that edge row and edge column; text block = the grid minus the rulers; "
                    "background = its most frequent colour; lines = maximal runs of non-background rows (or columns) "
                    "across the text block; glyphs = maximal runs of non-background cross-sections inside a line.",
    "preconditions": "Every input has exactly one such origin corner with two uniform rulers; the writing-mode rule "
                     "decides the inline axis on every training input; the text block contains at least one glyph.",
}

E, S, W, N = (0, 1), (1, 0), (0, -1), (-1, 0)
ROTS = [((1, 0), (0, 1)), ((0, -1), (1, 0)), ((-1, 0), (0, -1)), ((0, 1), (-1, 0))]  # 2x2 rows


def _mul(A, v):
    return (A[0][0] * v[0] + A[0][1] * v[1], A[1][0] * v[0] + A[1][1] * v[1])


def _mm(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(2)) for j in range(2)) for i in range(2))


def _tr(A):
    return ((A[0][0], A[1][0]), (A[0][1], A[1][1]))


def _apply(A, g):
    """Apply signed-permutation matrix A to grid coordinates (r, c) and re-anchor at 0."""
    h, w = len(g), len(g[0])
    pts = {}
    for r in range(h):
        for c in range(w):
            pts[_mul(A, (r, c))] = g[r][c]
    r0 = min(p[0] for p in pts)
    c0 = min(p[1] for p in pts)
    H = max(p[0] for p in pts) - r0 + 1
    Wd = max(p[1] for p in pts) - c0 + 1
    out = [[0] * Wd for _ in range(H)]
    for (r, c), v in pts.items():
        out[r - r0][c - c0] = v
    return out


# ---------------------------------------------------------------- page parsing
def _frame(g):
    H = len(g)
    Wd = len(g[0]) if H else 0
    if H < 3 or Wd < 3:
        return None
    found = []
    for r in (0, H - 1):
        for c in (0, Wd - 1):
            row = {g[r][j] for j in range(Wd) if j != c}
            col = {g[i][c] for i in range(H) if i != r}
            if len(row) == 1 and len(col) == 1:
                rc, cc = next(iter(row)), next(iter(col))
                if g[r][c] != rc and g[r][c] != cc:
                    found.append((r, c, rc, cc))
    if len(found) != 1:
        return None
    r, c, rc, cc = found[0]
    block = [[g[i][j] for j in range(Wd) if j != c] for i in range(H) if i != r]
    cnt = Counter(v for row in block for v in row)
    bg = min(cnt, key=lambda k: (-cnt[k], k))
    vdir = S if r == 0 else N   # away from origin, vertically
    hdir = E if c == 0 else W   # away from origin, horizontally
    return {"block": block, "bg": bg, "row_ruler": rc, "col_ruler": cc, "vdir": vdir, "hdir": hdir}


def _runs(flags):
    out, s = [], None
    for i, f in enumerate(flags + [False]):
        if f and s is None:
            s = i
        elif not f and s is not None:
            out.append((s, i - 1))
            s = None
    return out


def _bands(block, bg, horizontal):
    h, w = len(block), len(block[0])
    if horizontal:
        flags = [any(block[i][j] != bg for j in range(w)) for i in range(h)]
    else:
        flags = [any(block[i][j] != bg for i in range(h)) for j in range(w)]
    return _runs(flags)


def _geometry_axis(fr):
    """'h' if lines are horizontal bands, 'v' if vertical, None if undecided."""
    block, bg = fr["block"], fr["bg"]
    ok = {}
    for ax, horiz in (("h", True), ("v", False)):
        b = _bands(block, bg, horiz)
        if b and len({e - s for s, e in b}) == 1:
            ok[ax] = (len(b), b[0][1] - b[0][0])
    if len(ok) == 1:
        return next(iter(ok))
    if len(ok) == 2:
        (a1, (n1, t1)), (a2, (n2, t2)) = sorted(ok.items())
        if n1 != n2:
            return a1 if n1 > n2 else a2
        if t1 != t2:
            return a1 if t1 < t2 else a2
    return None


def _colour_axis(fr, colour, role):
    rc, cc = fr["row_ruler"], fr["col_ruler"]
    if rc == cc or colour not in (rc, cc):
        return None
    ruler_axis = "h" if rc == colour else "v"   # orientation of the ruler with that colour
    if role == "inline":
        return ruler_axis
    return "v" if ruler_axis == "h" else "h"


# ---------------------------------------------------------------- glyph turns
def _turn(mode, vi, vb):
    """D4 matrix applied to an input-frame glyph so that it is drawn in the output frame."""
    if mode == "none":
        return ROTS[0]
    if mode == "upright" and vi[0] == 0:
        return ROTS[0]
    if mode in ("upright", "rotate"):
        for R in ROTS:
            if _mul(R, vi) == E:
                return R
    if mode == "page":
        return (vb, vi)
    if mode == "page_up":
        return ((-vb[0], -vb[1]), vi)
    return None


def _glyphs(fr, axis, mode):
    block, bg = fr["block"], fr["bg"]
    if axis == "h":
        vi, vb = fr["hdir"], fr["vdir"]
    else:
        vi, vb = fr["vdir"], fr["hdir"]
    M = (vb, vi)                       # canonical frame: inline -> E, block -> S
    T = _turn(mode, vi, vb)
    K = _mm(T, _tr(M))                 # canonical glyph -> output glyph
    C = _apply(M, block)
    out = []
    for a, b in _bands(C, bg, True):
        rows = C[a:b + 1]
        for x, y in _runs([any(r[j] != bg for r in rows) for j in range(len(C[0]))]):
            out.append(_apply(K, [r[x:y + 1] for r in rows]))
    return out


def _assemble(glyphs, bg, align, layout):
    if not glyphs:
        return None
    gap = 1 if layout.endswith("gap") else 0
    if layout.startswith("line"):
        glyphs = [_apply(((0, 1), (1, 0)), gl) for gl in glyphs]   # build as a stack of transposes
    width = max(len(gl[0]) for gl in glyphs)
    out = []
    for k, gl in enumerate(glyphs):
        if k and gap:
            out.append([bg] * width)
        d = width - len(gl[0])
        off = {"centre_floor": d // 2, "centre_ceil": (d + 1) // 2, "start": 0, "end": d}[align]
        for r in gl:
            out.append([bg] * off + list(r) + [bg] * (d - off))
    if layout.startswith("line"):
        out = _apply(((0, 1), (1, 0)), out)
    return out


# ---------------------------------------------------------------- family
def _axis(fr, rule):
    if rule[0] == "colour":
        return _colour_axis(fr, rule[1], rule[2])
    return _geometry_axis(fr)


def _make(rule, mode, align, layout):
    def fn(g):
        fr = _frame(g)
        if fr is None:
            return [list(r) for r in g]
        ax = _axis(fr, rule)
        if ax is None and rule[0] != "geometry":
            ax = _geometry_axis(fr)
        if ax is None:
            ax = "h"
        out = _assemble(_glyphs(fr, ax, mode), fr["bg"], align, layout)
        return out if out is not None else [list(r) for r in g]
    return fn


def fam(train):
    if not train:
        return
    frames = []
    for p in train:
        g = p["input"]
        if not g or not g[0]:
            return
        fr = _frame(g)
        if fr is None:
            return
        frames.append(fr)
    colours = sorted({fr["row_ruler"] for fr in frames} | {fr["col_ruler"] for fr in frames})
    rules = []
    for c in colours:
        rules.append((("colour", c, "inline"), 0))
    for c in colours:
        rules.append((("colour", c, "block"), 1))
    rules.append((("geometry",), 2))
    modes = [("upright", 0), ("rotate", 1), ("page_up", 2), ("page", 3), ("none", 4)]
    aligns = [("centre_floor", 0), ("centre_ceil", 1), ("start", 1), ("end", 1)]
    layouts = [("stack", 0), ("stack_gap", 1), ("line", 2), ("line_gap", 3)]
    targets = [[list(r) for r in p["output"]] for p in train]
    found = []
    for rule, rk in rules:
        # the rule must decide the writing mode on every training page by itself
        axes = [_axis(fr, rule) for fr in frames]
        if any(a is None for a in axes):
            continue
        for mode, mk in modes:
            for align, ak in aligns:
                for layout, lk in layouts:
                    ok = True
                    for fr, ax, tgt in zip(frames, axes, targets):
                        try:
                            out = _assemble(_glyphs(fr, ax, mode), fr["bg"], align, layout)
                        except Exception:
                            out = None
                        if out != tgt:
                            ok = False
                            break
                    if ok:
                        rname = "geometry" if rule[0] == "geometry" else f"ruler{rule[1]}={rule[2]}"
                        name = f"writing_mode[axis={rname},turn={mode},align={align},layout={layout}]"
                        found.append((10 + rk + 2 * mk + ak + lk, len(found), name, (rule, mode, align, layout)))
    found.sort()
    for cost, _, name, cfg in found:
        yield name, cost, _make(*cfg)


FAMILIES = [fam]
