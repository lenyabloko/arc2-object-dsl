"""Prior concept family kronecker_tiling (test-blind; anti-unified from the member one-offs and their train pairs).

One generator:  out = POST( LAYOUT (x) MOTIF ).
A layout mask L (mh x mw cells, each OFF, ON, or ON with a colour) is blown up block by block: every ON cell
receives a block painted from the motif (the motif itself, the motif recoloured to the cell's colour, a solid block
of the cell's colour, or a per-colour block learned from the training outputs); OFF cells receive a block of the
off colour; optional one-cell gaps between blocks carry a gap colour.  Unknown block or layout sizes are solved
from the output size and must be one constant over all training pairs.  An optional cell-level post-rule then
paints background cells of the tiled result (lines through coloured cells, offset neighbours of coloured cells
with or without wrap-around, rows bridged between equal cells), its colours induced from the training outputs.

Shared steps written once: background, separator split / grid lattice / block-scale unit (inverse direction:
detect the block scale and reduce), counts, the size solver, the block drawing loop, the post-rule painter and
the verify loop.

Second pass (priors3): every literal-valued parameter that a role explains is now offered as a role-bound
alternative (specialisation menu built from the BINDINGS table below, not invented values).

Third pass (priors4; Fable v11 T68 / D38 / G68 changed): every colour parameter is a declared colour role
(colour_roles: background, rank_colour(k), novel_colour) or a role-bound value (lattice colour / lattice background,
the counted colour, swatch j, the off colour, the cell's own colour); the literal-colour fallbacks are gone.
"""
# G68 BINDINGS (priors4) -- per member, the role each former literal became (training pairs only)
#   09629e4f  off lbg, gap lat (roles already)                          -> unchanged
#   10fcaaa3  post nb-diag colour 8 (induced literal)                   -> novel_colour(train)
#   15696249  off ('c', 0) (literal)                                    -> novel_colour(train)
#   2072aba6  table {5: [[1,2],[2,1]], 0: [[0,0],[0,0]]} keyed by literal colours
#                                                                       -> LOST: needs literals 1, 2 (two colours
#             new in every output; keys 5/0 swap between bg and rank 1 across pairs)
#   310f3251  post nb (-1,-1) wrap colour 2 (induced literal)           -> novel_colour(train)
#   46f33fce  off bg                                                    -> unchanged
#   4852f2fa  N <- count(colour 4) (literal count key)                  -> count(rank_colour(2))
#   91413438  N <- count(colour 0), M <- count(not 0) (literal keys); off <- counted colour
#                                                                       -> count(common colour): the one colour
#             present in every training input (CR.input_colours, a declared role-bound helper); 0 is bg in two
#             pairs and rank 1 in the others, so no per-grid role names it
#   b0039139  off sw1, gap off, ink sw0 (roles already)                 -> unchanged
#   b4a43f3b  off bg                                                    -> unchanged
#   c92b942c  post rows colour 1 + nb colour 3 (two induced literals)   -> LOST: needs literals 1, 3 (two new
#             colours, so novel_colour is not unique)
#   f5b8619d  post cols colour 8                                        -> novel_colour(train)
#   fb791726  post bridge colour 3                                      -> novel_colour(train)
# Literal slots removed (5): count-key colour c (eq/ne/cc) -> rank_colour(k) | common colour; off colour
#   ('c', v) -> novel | rank k | common; gap colour ('c', v) -> bg | novel | rank k | common; post-rule colours
#   (induced from outputs) -> novel_colour(train) only; per-colour block table (literal keys and values) -> keys =
#   the cell colour's role (bg | rank position on the grid), values = per-cell roles (own | bg | novel | rank k |
#   common).  Background is CR.background (same tie rule as before).
#
# priors3 BINDINGS (kept for reference):
# BINDINGS -- induced value <- role, per fitted member (training pairs only; old priors2 program in brackets)
#   09629e4f  layout = lattice block with fewest fg cells; block (3,3) <- lattice cell size (run length);
#             gap colour <- lattice line colour; off 0 <- LATTICE BACKGROUND (grid bg is 5, old: literal c0)
#   10fcaaa3  k (2,2) <- literal (inputs 5x3/3x4/4x4/2x4, out = 2x); post nb diag (no wrap) colour 8 <- new constant
#   15696249  layout <- uniform rows/cols of input; motif <- input; off 0 <- literal new colour (absent from input)
#   2072aba6  layout <- input cells (all ON); block (2,2) <- solved literal; block per colour <- learned table
#   310f3251  k (3,3) <- literal; post nb (-1,-1) WITH wrap colour 2 <- new constant
#   46f33fce  layout <- input sampled every 2nd cell (offset 1); block (4,4) <- solved literal (out/mask); solid
#   4852f2fa  N <- count(colour 4) (the tally colour); motif <- window anchored br of non-tally bbox, size (3,3)
#             <- solved literal (bbox is 2x3 in one pair, so not the bbox role)
#   91413438  N <- count(colour 0), M <- count(not 0); motif <- input; off 0 <- THE COUNTED COLOUR (input bg
#             varies 3/0/0/6, old: literal c0)
#   b4a43f3b  layout <- panel 1 (side of the separator line); motif <- unit(panel 0)
#   c92b942c  k (3,3) <- literal; post rows colour 1 + nb {(-1,-1),(1,1)} colour 3 <- new constants
#   f5b8619d  k (2,2) <- literal; post cols colour 8 <- new constant
#   fb791726  diag k (2,2) <- literal; post bridge colour 3 <- new constant
# Role-bound alternatives added from this table and the shared steps it exposed:
#   off colour  ∈ {bg, lattice bg, counted colour, swatch colour j, const c}       (was {bg, const c})
#   gap colour  ∈ {lattice colour, off colour, const c}                           (was {lattice, const c})
#   ink colour  ∈ {swatch colour j}  -- paint "ink": motif open cells <- ink, closed <- off
#   strip participant: a divider colour whose cells all lie on thin full lines of one axis cuts the grid into
#     panels; uniform panels are SWATCHES (sorted inner first: nearer the figure panels), the others FIGURES
#     (sorted outer first); panel background = most common colour over the figures
#   slots shape ∈ {N×N, 1×N, N×1, ALONG the strip axis}; count ∈ {..., components in figure panel j}
#   motif ∈ {..., bbox crop of figure panel j}
# Tried and dropped: a k×k block-hull post-rule for 8fbca751 -- no role explains its k = 4 (not gcd of the grid
#   dims, not gcd of the shape bbox), so it would be a literal; left out per the no-invented-values rule.
from collections import Counter

import colour_roles as CR

CARD = "prior4_kronecker_tiling"
CONCEPT = "kronecker_tiling"
MEMBERS = ["09629e4f", "10fcaaa3", "15696249", "2072aba6", "310f3251", "456873bc", "46f33fce", "4852f2fa",
           "5833af48", "65b59efc", "6ecd11f4", "8719f442", "8fbca751", "91413438", "b0039139", "b4a43f3b",
           "c4d067a0", "c92b942c", "eee78d87", "f5b8619d", "f931b4a8", "fb791726"]
READING = {
    "generator": "Build the output as layout mask (x) motif: every ON cell of the mask receives a block painted from "
                 "the motif (as is, recoloured to the cell colour, solid in the cell colour, or a learned per-colour "
                 "block), OFF cells a block of the off colour, with optional one-cell gap lines; then optionally "
                 "paint background cells of the tiled result by a cell-level post-rule.",
    "stop": "One block per mask cell; unknown block / layout sizes are solved from the output size and must be a "
            "single constant over the training pairs; the post-rule is applied once, reading the tiled result "
            "(later rule components override earlier ones).",
    "params": "layout ∈ {ones(ky,kx), diag(k), anti(k), self (bg OFF | all ON), uniform-lines, slots(shape ∈ {N×N, 1×N, N×1}, "
              "N×N | 1×N | N×1 | along the strip axis; N = count, first M = count; count ∈ {#=c, #≠c, #bg, #fg, "
              "components in figure panel j}, c ∈ {rank k, common colour}), panel(p ∈ {0,1}), sample(s ∈ {2,3}, o), "
              "block(sel ∈ {fewest, most})} · motif ∈ {input, unit(input), unit(panel p), window(anchor ∈ {tl, br, "
              "centre}, size solved | bbox), bbox crop of figure panel j, none} · paint ∈ {own, recolour, solid, "
              "table, ink(swatch j)} · gap ∈ {0, 1} · off ∈ {bg, lattice bg, counted colour, swatch j, novel, rank k, common} · "
              "gap colour ∈ {lattice colour, off colour, bg, novel, rank k, common} · post = line ∈ {none, rows, "
              "cols} + neighbours ∈ {none, offset set × wrap ∈ {no, yes}} + bridge ∈ {no, yes} (colour <- novel) · "
              "table = cell role (bg | rank position) -> block of roles",
    "participants": "Background: most frequent colour. Panels: the two sides of a single full line whose colour "
                    "occurs nowhere else. Strip: a divider colour whose cells all lie on thin full lines of one axis; "
                    "uniform panels are swatches (inner first), the others figures (outer first). "
                    "Lattice: a colour forming full rows and full columns; its blocks are the "
                    "runs between lines. Unit: the grid reduced by its largest row / column block factors. Window: "
                    "bbox of the cells that are neither background nor the counted colour. Counts: cells of a colour "
                    "(or not of it) in the input.",
    "preconditions": "Output dims = mask dims x block dims (+ gaps) with one constant solved size over all pairs; "
                     "every cell where the tiled result differs from the output is background in the tiled result "
                     "and is explained by one post-rule with induced colours; the program reproduces every training "
                     "pair.",
}

OFF, ON = None, -1
NB_SETS = (((-1, -1), (-1, 1), (1, -1), (1, 1)), ((-1, -1), (1, 1)), ((-1, 1), (1, -1)),
           ((-1, -1),), ((-1, 1),), ((1, -1),), ((1, 1),),
           ((-1, 0), (1, 0), (0, -1), (0, 1)))


# ---------------------------------------------------------------- shared participants
def _bg(g):
    return CR.background(g)


def _rank(c, k):
    key = ("rank", k)
    if key not in c:
        c[key] = CR.rank_colour(c["g"], k, c["bg"])
    return c[key]


def _rpos(c, v):
    """role key of a cell colour: 'bg', or its rank position among the grid's ink colours (1 = most frequent)"""
    if v == c["bg"]:
        return "bg"
    if "rpos" not in c:
        tal = Counter(x for r in c["g"] for x in r if x != c["bg"])
        c["rpos"] = {x: i + 1 for i, x in enumerate(sorted(tal, key=lambda x: (-tal[x], x)))}
    return ("rank", c["rpos"].get(v))


def _decl(c, spec):
    """a declared role: ('rank', k) on the grid; ('novel', v) / ('common', v) fixed by the training pairs
    (v = CR.novel_colour(train) / the single colour of CR.input_colours(train))"""
    if spec[0] == "rank":
        return _rank(c, spec[1])
    return spec[1]


def _decl_roles(train):
    nov = CR.novel_colour(train)
    com = CR.input_colours(train)
    return ([("novel", nov)] if nov is not None else []) + [("rank", k) for k in CR.RANKS] + \
        ([("common", next(iter(com)))] if len(com) == 1 else [])


_MEMO = {}


def _ctx(g):
    key = tuple(tuple(r) for r in g)
    c = _MEMO.get(key)
    if c is None:
        if len(_MEMO) > 512:
            _MEMO.clear()
        c = _MEMO[key] = {"g": g, "bg": _bg(g), "cnt": Counter(v for r in g for v in r)}
    return c


def _lazy(c, name, f):
    if name not in c:
        try:
            c[name] = f(c["g"])
        except Exception:
            c[name] = None
    return c[name]


def _unit(g):
    """Inverse direction: reduce by the largest row / column block factors."""
    H, W = len(g), len(g[0])
    fr = max(f for f in range(1, H + 1) if H % f == 0 and all(g[i] == g[i - i % f] for i in range(H)))
    fc = max(f for f in range(1, W + 1) if W % f == 0 and
             all(r[j] == r[j - j % f] for r in g for j in range(W)))
    return [r[::fc] for r in g[::fr]]


def _panels(g):
    """Two sides of the single full line whose colour occurs nowhere else."""
    H, W = len(g), len(g[0])
    cnt = Counter(v for r in g for v in r)
    rows = [i for i in range(1, H - 1) if len(set(g[i])) == 1 and cnt[g[i][0]] == W]
    cols = [j for j in range(1, W - 1) if len({g[i][j] for i in range(H)}) == 1 and cnt[g[0][j]] == H]
    if len(rows) + len(cols) != 1:
        return None
    if rows:
        k = rows[0]
        return [r[:] for r in g[:k]], [r[:] for r in g[k + 1:]]
    k = cols[0]
    return [r[:k] for r in g], [r[k + 1:] for r in g]


def _strip(g):
    """Divider colour whose cells all lie on thin full lines of one axis (most panels wins).  Returns
    {axis, figs (outer first), sw (swatch colours, inner first), pbg} or None."""
    H, W = len(g), len(g[0])
    T = [list(r) for r in zip(*g)]
    best = None
    for axis, G in (("rows", g), ("cols", T)):
        n = len(G)
        full = {}
        for i, r in enumerate(G):
            if len(set(r)) == 1:
                full.setdefault(r[0], set()).add(i)
        for c, rows in full.items():
            if any(i + 1 in rows for i in rows) or any(v == c and i not in rows for i, r in enumerate(G) for v in r):
                continue
            other = T if axis == "rows" else g                # no full line of c across the other axis
            if any(all(v == c for v in r) for r in other):
                continue
            pans = [[G[i] for i in run] for run in _runs(n, rows)]
            if len(pans) >= 2 and (best is None or len(pans) > len(best[1])):
                best = (axis, pans)
    if best is None:
        return None
    axis, pans = best
    if axis == "cols":
        pans = [[list(r) for r in zip(*p)] for p in pans]
    uni = [k for k, p in enumerate(pans) if len({v for r in p for v in r}) == 1]
    fig = [k for k, p in enumerate(pans) if k not in uni]
    if not uni or not fig:
        return None
    cu, cf = sum(uni) / len(uni), sum(fig) / len(fig)
    fig.sort(key=lambda k: (-abs(k - cu), k))               # outer figure first (reading-direction free)
    uni.sort(key=lambda k: (abs(k - cf), k))                # inner swatch first
    cnt = Counter(v for k in fig for r in pans[k] for v in r)
    return {"axis": axis, "figs": [pans[k] for k in fig], "sw": [pans[k][0][0] for k in uni],
            "pbg": max(cnt, key=lambda k: (cnt[k], -k))}


def _fig_crop(c, j):
    S = _lazy(c, "strip", _strip)
    if S is None or j >= len(S["figs"]):
        return None
    p, pb = S["figs"][j], S["pbg"]
    cells = [(a, b) for a, r in enumerate(p) for b, v in enumerate(r) if v != pb]
    if not cells:
        return None
    r0, r1 = min(a for a, _ in cells), max(a for a, _ in cells)
    c0, c1 = min(b for _, b in cells), max(b for _, b in cells)
    return [r[c0:c1 + 1] for r in p[r0:r1 + 1]]


def _fig_count(g, j):
    """Connected (8-neighbour) groups of non-panel-background cells in figure panel j."""
    S = _strip(g)
    if S is None or j >= len(S["figs"]):
        return None
    p, pb = S["figs"][j], S["pbg"]
    return _comps_count([[1 if v != pb else 0 for v in r] for r in p], 1)


def _runs(n, lines):
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


def _lattice(g):
    """(line colour, row runs, col runs, bg) for a colour forming full rows and full columns."""
    H, W = len(g), len(g[0])
    for c in sorted({v for r in g for v in r}):
        rs = {i for i in range(H) if all(v == c for v in g[i])}
        cs = {j for j in range(W) if all(g[i][j] == c for i in range(H))}
        if rs and cs:
            R, C = _runs(H, rs), _runs(W, cs)
            cnt = Counter(v for r in g for v in r if v != c)
            if not cnt or len(R) * len(C) < 2:
                continue
            return c, R, C, max(cnt, key=lambda k: (cnt[k], -k))
    return None


def _comps_count(g, col):
    H, W = len(g), len(g[0])
    seen, n = set(), 0
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or (i, j) in seen:
                continue
            n += 1
            st = [(i, j)]
            seen.add((i, j))
            while st:
                a, b = st.pop()
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                            seen.add((x, y))
                            st.append((x, y))
    return n


def _count(c, key):
    kind, col = key
    g, cnt = c["g"], c["cnt"]
    if kind in ("eq", "ne", "cc"):
        col = _decl(c, col)
        if col is None:
            return None
    tot = len(g) * len(g[0])
    if kind == "eq":
        return cnt.get(col, 0)
    if kind == "ne":
        return tot - cnt.get(col, 0)
    if kind == "bg":
        return cnt[c["bg"]]
    if kind == "fg":
        return tot - cnt[c["bg"]]
    if kind == "cc":
        return _lazy(c, ("cc", col), lambda gg: _comps_count(gg, col))
    if kind == "scc":
        return _lazy(c, ("scc", col), lambda gg: _fig_count(gg, col))
    return None


def _slot_dims(c, shape, N):
    if shape == "along":
        S = _lazy(c, "strip", _strip)
        if S is None:
            return None
        shape = "col" if S["axis"] == "rows" else "row"
    return {"sq": (N, N), "row": (1, N), "col": (N, 1)}[shape]


# ---------------------------------------------------------------- layouts: grid of OFF / ON / colour
def _layout(c, lay, kk):
    kind, arg = lay
    g, bg = c["g"], c["bg"]
    if kind == "ones":
        return [[ON] * kk[1] for _ in range(kk[0])]
    if kind in ("diag", "anti"):
        ky, kx = kk
        if kind == "diag":
            return [[ON if i == j else OFF for j in range(kx)] for i in range(ky)]
        return [[ON if i + j == kx - 1 else OFF for j in range(kx)] for i in range(ky)]
    if kind == "self":
        return [[OFF if (v == bg and arg != "all") else v for v in r] for r in g]
    if kind == "lines":
        H, W = len(g), len(g[0])
        ur = {i for i in range(H) if len(set(g[i])) == 1}
        uc = {j for j in range(W) if len({g[i][j] for i in range(H)}) == 1}
        if not ur and not uc:
            return None
        return [[ON if (i in ur or j in uc) else OFF for j in range(W)] for i in range(H)]
    if kind == "slots":
        shape, nkey, mkey = arg
        N = _count(c, nkey)
        M = N if mkey is None else _count(c, mkey)
        if not N or N < 1 or N > 30 or M is None:
            return None
        sd = _slot_dims(c, shape, N)
        if sd is None:
            return None
        mh, mw = sd
        return [[ON if i * mw + j < M else OFF for j in range(mw)] for i in range(mh)]
    if kind == "panel":
        P = _lazy(c, "panels", _panels)
        if P is None:
            return None
        p = P[arg]
        pb = _bg(p)
        return [[OFF if v == pb else v for v in r] for r in p]
    if kind == "sample":
        s, o = arg
        sm = [r[o::s] for r in g[o::s]]
        if not sm or not sm[0]:
            return None
        return [[OFF if v == bg else v for v in r] for r in sm]
    if kind == "block":
        lat = _lazy(c, "lattice", _lattice)
        if lat is None:
            return None
        lc, R, C, lbg = lat
        blocks = []
        for bi in range(len(R)):
            for bj in range(len(C)):
                n = sum(1 for a in R[bi] for b in C[bj] if g[a][b] != lbg)
                blocks.append((n, bi, bj))
        ns = [b[0] for b in blocks]
        pick = min(blocks) if arg == "fewest" else max(blocks)
        if ns.count(pick[0]) != 1:
            return None
        _, bi, bj = pick
        return [[OFF if g[a][b] == lbg else g[a][b] for b in C[bj]] for a in R[bi]]
    return None


def _layout_dims(c, lay):
    """Mask dims, or None when they are free (solved from the output size)."""
    if lay[0] in ("ones", "diag", "anti"):
        return None
    key = ("dims", lay)
    if key not in c:
        if lay[0] == "slots":
            N = _count(c, lay[1][1])
            M = N if lay[1][2] is None else _count(c, lay[1][2])
            ok = N and 1 <= N <= 30 and M is not None
            sd = _slot_dims(c, lay[1][0], N) if ok else None
            c[key] = False if sd is None else sd
        else:
            L = _layout(c, lay, None)
            c[key] = False if not L or not L[0] else (len(L), len(L[0]))
    return c[key]


def _excluded(lay):
    """The counted colour (a role spec) is a tally, not part of a motif window."""
    if lay[0] == "slots":
        ks = [k for k in lay[1][1:] if k] + [lay[1][1]]
        for k in ks:
            if k[0] in ("eq", "cc"):
                return k[1]
    return None


# ---------------------------------------------------------------- motifs
def _bbox(g, bg, ex):
    cells = [(i, j) for i, r in enumerate(g) for j, v in enumerate(r) if v != bg and v != ex]
    if not cells:
        return None
    return (min(i for i, _ in cells), max(i for i, _ in cells), min(j for _, j in cells), max(j for _, j in cells))


def _motif(c, mot, lay, size):
    kind, arg = mot
    g, bg = c["g"], c["bg"]
    if kind == "input":
        return g
    if kind == "unit":
        return _lazy(c, "unit", _unit)
    if kind == "panel":
        P = _lazy(c, "panels", _panels)
        return None if P is None else _unit(P[arg])
    if kind == "fig":
        return _fig_crop(c, arg)
    if kind == "window":
        ex = _excluded(lay)
        ex = None if ex is None else _decl(c, ex)
        H, W = len(g), len(g[0])
        bb = _lazy(c, ("bbox", ex), lambda gg: _bbox(gg, bg, ex))
        if bb is None:
            return None
        r0, r1, c0, c1 = bb
        if size is None:
            h, w, a, b = r1 - r0 + 1, c1 - c0 + 1, r0, c0
        else:
            h, w = size
            if arg == "tl":
                a, b = r0, c0
            elif arg == "br":
                a, b = r1 - h + 1, c1 - w + 1
            else:
                a, b = (r0 + r1 + 1 - h) // 2, (c0 + c1 + 1 - w) // 2
        out = []
        for i in range(a, a + h):
            row = []
            for j in range(b, b + w):
                v = g[i][j] if 0 <= i < H and 0 <= j < W else bg
                row.append(bg if v == ex else v)
            out.append(row)
        return out
    return None


def _motif_dims(c, mot, lay, paint):
    """Block dims, or None when free (solid / table paint, or a window whose size is solved)."""
    if paint in ("solid", "table") or (mot[0] == "window" and mot[1] != "bbox"):
        return None
    key = ("mdims", mot, _excluded(lay) if mot[0] == "window" else None)
    if key not in c:
        T = _motif(c, mot, lay, None)
        c[key] = False if not T or not T[0] else (len(T), len(T[0]))
    return c[key]


# ---------------------------------------------------------------- the drawing loop
def _assemble(L, T, paint, bh, bw, gap, offc, gapc, table, tbg):
    mh, mw = len(L), len(L[0])
    OH, OW = mh * bh + (mh - 1) * gap, mw * bw + (mw - 1) * gap
    if OH > 60 or OW > 60 or OH < 1 or OW < 1:
        return None
    out = [[gapc] * OW for _ in range(OH)]
    for i in range(mh):
        for j in range(mw):
            v = L[i][j]
            r0, c0 = i * (bh + gap), j * (bw + gap)
            for a in range(bh):
                row = out[r0 + a]
                for b in range(bw):
                    if v is OFF:
                        x = offc
                    elif paint == "own":
                        x = T[a][b]
                    elif paint == "recolour":
                        x = offc if T[a][b] == tbg else v
                    elif paint == "solid":
                        x = v
                    elif paint[0] == "ink":                  # open motif cells <- ink, closed <- off
                        x = offc if T[a][b] == tbg else table
                    else:
                        blk = table.get(v)
                        if blk is None:
                            return None
                        x = blk[a][b]
                    row[c0 + b] = x
    return out


# ---------------------------------------------------------------- post-rule
def _paint_sets(t, bg):
    """Background cells each post-rule component would paint, reading the tiled result t."""
    H, W = len(t), len(t[0])
    fg = [(i, j) for i in range(H) for j in range(W) if t[i][j] != bg]
    rows = {i for i, _ in fg}
    cols = {j for _, j in fg}
    S = {("line", "rows"): {(i, j) for i in rows for j in range(W) if t[i][j] == bg},
         ("line", "cols"): {(i, j) for j in cols for i in range(H) if t[i][j] == bg}}
    shift = {}                                               # one pass per single offset, shared by the sets
    for wrap in (False, True):
        for ds in NB_SETS:
            for di, dj in ds:
                if (di, dj, wrap) in shift:
                    continue
                if wrap:
                    s = {((i + di) % H, (j + dj) % W) for i, j in fg if t[(i + di) % H][(j + dj) % W] == bg}
                else:
                    s = {(i + di, j + dj) for i, j in fg
                         if 0 <= i + di < H and 0 <= j + dj < W and t[i + di][j + dj] == bg}
                shift[(di, dj, wrap)] = s
    for k, ds in enumerate(NB_SETS):
        for wrap in (False, True):
            S[("nb", (k, wrap))] = set().union(*[shift[(di, dj, wrap)] for di, dj in ds])
    s = set()
    for i in range(1, H - 1):
        if all(v == bg for v in t[i]) and any(t[i - 1][j] != bg and t[i - 1][j] == t[i + 1][j] for j in range(W)):
            s.update((i, j) for j in range(W))
    S[("bridge", None)] = s
    return S


POST_COMBOS = [(ln, nb, br) for br in (None, ("bridge", None)) for ln in (None, ("line", "rows"), ("line", "cols"))
               for nb in [None] + [("nb", (k, w)) for w in (False, True) for k in range(len(NB_SETS))]
               if ln or nb or br]


def _pair_info(t, o, g, nov):
    """Per-pair post-rule facts: [t, bg, D, paint sets (lazy), single-pair feasibility (lazy)] or None when some
    cell differs where t is not background or the output colour is not the novel colour (the only role that names
    a colour absent from the input)."""
    bg = _bg(t)
    if nov is None:
        old = None
    else:
        old = {v for r in g for v in r}
    D = {}
    for i in range(len(t)):
        ti, oi = t[i], o[i]
        if ti == oi:
            continue
        for j in range(len(ti)):
            if ti[j] != oi[j]:
                if old is None or ti[j] != bg or oi[j] in old or oi[j] != nov:
                    return None
                D[(i, j)] = oi[j]
    return [t, bg, D, None, None]


def _search_post(infos):
    """First post-rule combo (in POST_COMBOS order) explaining every pair, with induced colours, or None."""
    if not any(info[2] for info in infos):
        return ()
    valid = None
    for info in infos:
        if info[3] is None:
            info[3] = _paint_sets(info[0], info[1])
        Dset = info[2].keys()
        ok = {x for x, s in info[3].items() if s <= Dset}   # a component painting outside D can never fit
        valid = ok if valid is None else valid & ok
    for info in infos:                                       # the usable components must cover every D
        if info[2] and not info[2].keys() <= set().union(*[info[3][x] for x in valid]):
            return None
    for info in infos:
        if len(info) < 7:
            by = {}
            for q, v in info[2].items():
                by.setdefault(v, set()).add(q)
            info.extend([set(info[2]), by])                  # D as a set, D cells by colour
    for combo in POST_COMBOS:
        comps = [x for x in combo if x]
        if any(x not in valid for x in comps):
            continue
        cols = [None] * len(comps)
        ok = True
        for info in infos:
            D, S, Dset, by = info[2], info[3], info[5], info[6]
            sets = [S[x] for x in comps]
            if set().union(*sets) != Dset:
                ok = False
                break
            later = set()
            for k in range(len(sets) - 1, -1, -1):           # cells where component k is the last painter
                region = sets[k] - later
                later |= sets[k]
                if not region:
                    continue
                v = D[next(iter(region))]
                if not region <= by[v] or cols[k] not in (None, v):
                    ok = False
                    break
                cols[k] = v
            if not ok:
                break
        if ok and all(x is not None for x in cols):
            return tuple(zip(comps, cols))
    return None


def _induce_post(bases, outs, ins, nov):
    """Find a post-rule (components + colours) mapping each tiled result onto its output, or None.
    Post-rule colours are the novel colour (absent from every input, present in every output)."""
    infos = []
    for t, o, g in zip(bases, outs, ins):
        info = _pair_info(t, o, g, nov)
        if info is None:
            return None
        infos.append(info)
    return _search_post(infos)


def _apply_post(t, post):
    if not post:
        return t
    bg = _bg(t)
    S = _paint_sets(t, bg)
    out = [r[:] for r in t]
    for comp, col in post:
        col = col[1] if isinstance(col, tuple) else col     # ('novel', v): fixed by the training pairs
        for i, j in S[comp]:
            out[i][j] = col
    return out


# ---------------------------------------------------------------- the generator
def _layouts(train):
    roles = [s for s in _decl_roles(train) if s[0] != "novel"]   # a novel colour has no input count
    keys = [("bg", None), ("fg", None)] + [(k, s) for s in roles for k in ("eq", "ne", "cc")]
    yield ("ones", None), 1
    yield ("self", None), 1
    yield ("self", "all"), 2
    yield ("diag", None), 2
    yield ("anti", None), 2
    yield ("lines", None), 2
    yield ("panel", 0), 2
    yield ("panel", 1), 2
    yield ("block", "fewest"), 3
    yield ("block", "most"), 3
    for s in (2, 3):
        for o in range(s):
            yield ("sample", (s, o)), 3
    for shape in ("row", "col", "sq"):
        for nk in keys:
            for mk in [None] + keys:
                yield ("slots", (shape, nk, mk)), 3
    if all(_lazy(_ctx(p["input"]), "strip", _strip) for p in train):
        for shape in ("along", "row", "col"):                 # strip roles: tally = components of a figure
            for j in (0, 1):
                yield ("slots", (shape, ("scc", j), None)), 3


MOTIFS = (("input", None), ("unit", None), ("panel", 0), ("panel", 1),
          ("window", "bbox"), ("window", "br"), ("window", "tl"), ("window", "centre"), ("fig", 0), ("fig", 1),
          (None, None))
PAINTS = ("own", "recolour", "solid", "table", ("ink", 0), ("ink", 1))
NO_COLOUR = ("ones", "diag", "anti", "lines", "slots")         # layouts whose ON cells carry no colour


def _is_ink(paint):
    return isinstance(paint, tuple) and paint[0] == "ink"


def _count_colour(lay):
    """Role: the colour a slots layout counts (eq / ne / cc key)."""
    if lay[0] == "slots":
        for k in lay[1][1:]:
            if k and k[0] in ("eq", "ne", "cc"):
                return k[1]
    return None


def _role_colour(c, spec, lay, offc=None):
    """Resolve a colour parameter: a role of the input (or of the off colour) or a constant."""
    if spec == "bg":
        return c["bg"]
    if spec == "lbg":
        lat = _lazy(c, "lattice", _lattice)
        return lat[3] if lat else None
    if spec == "lat":
        lat = _lazy(c, "lattice", _lattice)
        return lat[0] if lat else None
    if spec == "cnt":
        s = _count_colour(lay)
        return None if s is None else _decl(c, s)
    if spec == "off":
        return offc
    if spec[0] == "sw":
        S = _lazy(c, "strip", _strip)
        return S["sw"][spec[1]] if S and spec[1] < len(S["sw"]) else None
    return _decl(c, spec)                                    # declared role (no literal colours)


def _solve(dims_m, dims_b, out, gap):
    """Per axis: solve the free one of (mask size, block size) from out = m*b + (m-1)*gap."""
    res = []
    for m, b, O in zip(dims_m or (None, None), dims_b or (None, None), out):
        if m is None and b is None:
            return None
        if m is None:
            if (O + gap) % (b + gap):
                return None
            m = (O + gap) // (b + gap)
        elif b is None:
            if (O - (m - 1) * gap) % m:
                return None
            b = (O - (m - 1) * gap) // m
        if m < 1 or b < 1 or m * b + (m - 1) * gap != O:
            return None
        res.append((m, b))
    return res


def _slots_sig(c, lay):
    """The slots mask is fixed by (mask dims, number of ON slots clipped to the mask)."""
    key = ("sig", lay)
    if key not in c:
        c[key] = _slots_sig0(c, lay)
    return c[key]


def _slots_sig0(c, lay):
    N = _count(c, lay[1][1])
    M = N if lay[1][2] is None else _count(c, lay[1][2])
    if not N or N < 1 or N > 30 or M is None:
        return None
    sd = _slot_dims(c, lay[1][0], N)
    if sd is None:
        return None
    mh, mw = sd
    return mh, mw, max(0, min(M, mh * mw))


_EXC = object()


def _static_ok(kind, mot, paint):
    """The setting-only preconditions of _fit_one (checked there too)."""
    if paint in ("own", "recolour") and mot[0] is None:
        return False
    if paint in ("solid", "table") and mot[0] is not None:
        return False
    if paint != "own" and not _is_ink(paint) and kind in NO_COLOUR:
        return False
    if _is_ink(paint) != (mot[0] == "fig") and paint != "own":
        return False
    if mot[0] == "window" and kind in ("self", "panel", "block", "sample"):
        return False
    return True


def _fit_one(train, ctxs, lay, mot, paint, gap, pc=None):
    if pc is None:
        pc = {}
    if "_decl" not in pc:
        pc["_decl"] = _decl_roles(train)
        pc["_nov"] = CR.novel_colour(train)
    decl, nov = pc["_decl"], pc["_nov"]
    if paint in ("own", "recolour") and mot[0] is None:
        return None
    if paint in ("solid", "table") and mot[0] is not None:
        return None
    if not _static_ok(lay[0], mot, paint):
        return None                                          # e.g. cells carry no colour
    if mot[0] == "window" and lay[0] in ("self", "panel", "block", "sample"):
        return None
    free_m = lay[0] in ("ones", "diag", "anti")
    free_b = paint in ("solid", "table") or (mot[0] == "window" and mot[1] != "bbox")
    const_m = const_b = None
    for c, p in zip(ctxs, train):
        dm = None if free_m else _layout_dims(c, lay)
        if dm is False:
            return None
        db = None if free_b else _motif_dims(c, mot, lay, paint)
        if db is False:
            return None
        o = p["output"]
        sv = _solve(dm, db, (len(o), len(o[0])), gap)
        if sv is None:
            return None
        if free_m:
            k = (sv[0][0], sv[1][0])
            if const_m not in (None, k):
                return None
            const_m = k
        if free_b:
            k = (sv[0][1], sv[1][1])
            if const_b not in (None, k):
                return None
            const_b = k
    # learned per-role blocks: key = the cell colour's role (bg | rank position), each block cell = the first role
    # (own, bg, declared roles) explaining every observation; no literal keys or values
    table = None
    order = ["own", "bg"] + decl
    if paint == "table":
        cand = {}
        bh, bw = const_b
        for c, p in zip(ctxs, train):
            L = _layout(c, lay, const_m)
            o = p["output"]
            for i, r in enumerate(L):
                for j, v in enumerate(r):
                    if v is OFF:
                        continue
                    key = _rpos(c, v)
                    vals = {"own": v, "bg": c["bg"]}
                    for s in decl:
                        vals[s] = _decl(c, s)
                    blk = cand.get(key)
                    if blk is None:
                        blk = cand[key] = [[set(order) for _ in range(bw)] for _ in range(bh)]
                    for a in range(bh):
                        orow = o[i * (bh + gap) + a]
                        for b in range(bw):
                            want = orow[j * (bw + gap) + b]
                            s0 = blk[a][b]
                            s0 &= {s for s in s0 if vals[s] == want}
                            if not s0:
                                return None
        if not cand:
            return None
        table = {k: tuple(tuple(next(s for s in order if s in cell) for cell in row) for row in blk)
                 for k, blk in cand.items()}
    o0, c0 = train[0]["output"], ctxs[0]
    # colour menus: roles first (from the BINDINGS table), then constants; a choice that resolves to the same
    # colour on every training input as an earlier one is dropped (the role replaces the literal)
    offs = ["bg", "lbg", "cnt", ("sw", 0), ("sw", 1)] + decl
    gaps = ["lat"]
    if gap:
        gaps, gseen = [], set()
        for g_ in ["lat", "off", "bg"] + decl:
            if g_ == "off":
                gaps.append(g_)
                continue
            vec = tuple(_role_colour(c, g_, lay) for c in ctxs)
            if None not in vec and vec not in gseen:
                gseen.add(vec)
                gaps.append(g_)
    seen, keep = set(), []
    for o_ in offs:
        vec = tuple(_role_colour(c, o_, lay) for c in ctxs)
        if None not in vec and vec not in seen:
            seen.add(vec)
            keep.append(o_)
    offs = keep

    def build(g, offc_s, gapc_s, post):
        c = _ctx(g)
        L = _layout(c, lay, const_m)
        if L is None or not L or not L[0]:
            return None
        T = None
        if mot[0] is not None:
            T = _motif(c, mot, lay, const_b if free_b else None)
            if not T or not T[0]:
                return None
            bh, bw = len(T), len(T[0])
        else:
            bh, bw = const_b
        offc = _role_colour(c, offc_s, lay)
        gapc = _role_colour(c, gapc_s, lay, offc)
        if offc is None or (gap and gapc is None):
            return None
        tbg, tab = (_bg(T) if T else None), table
        if paint == "table":                                 # resolve the role table on this grid
            tab = {}
            for r in L:
                for v in r:
                    if v is OFF or v in tab:
                        continue
                    blk = table.get(_rpos(c, v))
                    if blk is None:
                        return None
                    vals = {"own": v, "bg": c["bg"]}
                    rb = []
                    for row in blk:
                        rr = []
                        for s in row:
                            x = vals[s] if s in vals else _decl(c, s)
                            if x is None:
                                return None
                            rr.append(x)
                        rb.append(rr)
                    tab[v] = rb
        if _is_ink(paint):                                   # ink <- swatch colour; closed cells = panel bg
            S = _lazy(c, "strip", _strip)
            tab = _role_colour(c, ("sw", paint[1]), lay)
            if S is None or tab is None:
                return None
            tbg = S["pbg"]
        t = _assemble(L, T, paint, bh, bw, gap, offc, gapc, tab, tbg)
        if t is None:
            return None
        return _apply_post(t, post)

    tkey = (mot, _excluded(lay) if mot[0] == "window" else None, const_b if free_b else None)
    for offc_s in offs:
        for gapc_s in gaps:
            infos = []
            for k, (c, p) in enumerate(zip(ctxs, train)):
                lkey = ("S", _slots_sig(c, lay)) if lay[0] == "slots" else (lay, const_m)
                key = (k, lkey, tkey, paint, gap, const_b, offc_s, gapc_s)   # same key -> same tiled base
                hit = pc.get(key)
                if hit is None:
                    try:
                        b = build(p["input"], offc_s, gapc_s, ())
                    except Exception:
                        pc[key] = _EXC
                        raise
                    info = None
                    if b is not None and len(b) == len(p["output"]) and len(b[0]) == len(p["output"][0]):
                        bkey = ("base", k, tuple(map(tuple, b)))     # identical bases share their facts
                        if bkey in pc:
                            info = pc[bkey]
                        else:
                            info = _pair_info(b, p["output"], p["input"], nov)
                            if info is not None:
                                info[4] = _search_post([info]) is not None
                            pc[bkey] = info
                    hit = pc[key] = (info,)
                elif hit is _EXC:
                    raise ValueError("build failed")
                info = hit[0]
                if info is None or not info[4]:
                    infos = None                             # fast per-pair rejection
                    break
                infos.append(info)
            if infos is None:
                continue
            pkey = ("post",) + tuple(id(i) for i in infos)
            if pkey not in pc:
                pc[pkey] = _search_post(infos)
            post = pc[pkey]
            if post is None:
                continue
            post = tuple((comp, ("novel", col)) for comp, col in post)   # every post colour is the novel colour
            fn = (lambda o_, g_, q_: (lambda grid: build(grid, o_, g_, q_)))(offc_s, gapc_s, post)
            name = "kronecker_tiling[layout=%s,motif=%s,paint=%s,gap=%d,off=%s,gapc=%s,k=%s,b=%s,post=%s]" % (
                _fmt(lay), _fmt(mot), _fmt(paint), gap, _fmt(offc_s), _fmt(gapc_s) if gap else "-", const_m, const_b,
                _fmt(post))
            return name, len(post), fn
    return None


def _fmt(x):
    if isinstance(x, tuple) and len(x) == 2 and x[0] in ("novel", "common") and isinstance(x[1], int):
        return x[0]                                          # name the role, not the value it is bound to
    if isinstance(x, tuple):
        return "(" + ",".join(_fmt(y) for y in x) + ")"
    return str(x).replace(" ", "")


def fam(train):
    if not train or any(not p["input"] or not p["output"] for p in train):
        return
    if any(len(p["output"]) > 60 or len(p["output"][0]) > 60 for p in train):
        return
    ctxs = [_ctx(p["input"]) for p in train]
    cache = {}                                               # per-call cache of tiled bases and post-rules
    has_strip = all(_lazy(c, "strip", _strip) for c in ctxs)
    found = []
    for lay, lc in _layouts(train):
        if lay[0] not in ("ones", "diag", "anti"):
            try:                                             # mask dims undefined on a pair: no setting can fit
                bad = any(_layout_dims(c, lay) is False for c in ctxs)
            except Exception:
                bad = True
            if bad:
                continue
        for mot in MOTIFS:
            if mot[0] == "fig" and not has_strip:
                continue
            for paint in PAINTS:
                if not _static_ok(lay[0], mot, paint):
                    continue
                for gap in (0, 1):
                    try:
                        r = _fit_one(train, ctxs, lay, mot, paint, gap, cache)
                    except Exception:
                        r = None
                    if r is None:
                        continue
                    name, pc, fn = r
                    try:
                        if not all(fn(p["input"]) == p["output"] for p in train):
                            continue
                    except Exception:
                        continue
                    found.append((name, lc + gap + pc + (paint != "own") + (mot[0] not in ("input", None)), fn))
                    if len(found) >= 3:
                        break
                if len(found) >= 3:
                    break
            if len(found) >= 3:
                break
        if len(found) >= 3:
            break
    found.sort(key=lambda x: x[1])                           # best (cheapest) first
    for f in found:
        yield f


FAMILIES = [fam]
