# BINDINGS (G68, priors4 / Fable v11 D38) -- every colour parameter is a declared role of colour_roles (CR) or a
# role-bound value; no literal colour number is left in a program.  Per member, the role each former literal became:
#   every member  background (old: Counter.most_common, first-seen tie) <- CR.background(g) (ties -> lower colour)
#   14754a24  evidence 4 (least frequent) <- CR.rank_colour(g, -1);  support nonbg <- all but CR.background
#             fill 2 <- CR.novel_colour(train)
#   150deff5  type colours 8 / 2 (two colours new in the outputs)  ->  LOST: needs literals 8, 2 (no single novel
#             colour; no input role names a piece-type colour)
#   1818057f  support {4} = all but CR.background;  fill 8 <- CR.novel_colour(train)
#   36fdfd69  evidence 2 <- CR.rank_colour(g, -1);  support all but 0 <- all but INERT (ROLE-BOUND VALUE defined in
#             this family: the one colour present in every training input that never changes and is neither the
#             evidence, a fill colour nor a changing colour; 0 is the background in pairs 1-2 and rank 1 in pair 0,
#             so no declared role names it);  fill 4 <- CR.novel_colour(train)
#   50846271  evidence 2 <- CR.rank_colour(g, -1);  support all but 0 <- all but INERT (0 is rank 1 / background);
#             fill 8 <- CR.novel_colour(train)
#   626c0bcc  type colours 1, 2, 3, 4  ->  LOST: needs literals 1, 2, 3, 4
#   7e02026e  support {0} (source set: 0 is rank 1 in pairs 0/2, the background in pair 1)  ->  LOST: needs literal
#             0;  fill 3 <- CR.novel_colour(train) would hold
#   896d5239  evidence 3 <- CR.rank_colour(g, -1);  support any;  fill 8 <- CR.novel_colour(train)
#   9caba7c3  evidence 2 <- CR.rank_colour(g, -1);  support all but 0 <- all but INERT (0 is also rank 1)
#             pattern centre 4 / ring 7 (two new colours)  ->  LOST: needs literals 4, 7
# Literals removed: evidence colour (literal never-changing colour and the literal tie fallback of the least-frequent
# role), support colours (literal inert / background colour, literal source set), fill colours, per-offset pattern
# colours and piece-type colours.  They are now:
#   evidence  in {CR.rank_colour(g, k), k in -1, 1, 2, 3, -2}  (a role naming, in every training input, a colour that
#             is not the background, never changes and is not a fill colour; roles selecting the same colours in every
#             training input are one option)
#   support   in {all but CR.background | all but INERT / CR.background / CR.rank_colour (the role naming the old
#             literal in every input) | whole grid | source set as roles (CR.background / CR.rank_colour)}
#   fill / pattern / type colours  <- the first of CR.novel_colour(train), CR.background, CR.rank_colour(g, k) that
#             names the induced colour in every training pair; a configuration whose colour no role names is dropped
#   piece sizes in {all | seen} (not colours; unchanged)
"""Prior family template_cover_completion, pass 4 (G68 colour roles; test-blind; specialised over FITTED BINDINGS, train pairs only).

One generator, COVER: enumerate every placement of small template pieces (the oriented shapes of one piece
class, or of several type classes) that fits the target -- lies on SUPPORT cells (optionally hanging over the
grid edge) and holds at least `minm` EVIDENCE cells -- then choose placements by one selection rule:
  * open   : every fitting translate (morphological opening; no evidence needed),
  * greedy : repeatedly take the piece holding the most still-unexplained evidence (ties: more evidence, then
             smaller/larger piece, then row-major), disjoint or overlapping, until no piece holds `minm`
             unexplained evidence cells (fewest pieces, greedily),
  * exact  : disjoint pieces explaining ALL evidence cells (backtracking with a node budget); with
             evidence = support = a blob this is an exact tiling of the blob,
and paint each chosen piece with a colour per (oriented shape, offset) induced from the training outputs:
evidence cells are kept (completion: missing cells get the fill colour, or a centre/ring pattern) or repainted
(tiling: each piece takes the colour of its shape type).
Induction (all from training pairs): changed cells, fill colours, an evidence colour that never changes, the
support, the piece class (declared elementary shapes, multi-size families whose sizes are either all or only
those seen as maximal consistent placements, shapes seen in training, or per-colour minimal output
components for typed tiling), the paint pattern, and offsets that never held evidence.
Shared steps written once: participants, placement enumeration (row bitmasks), selection loops, paint, verify.
"""
import heapq
from collections import Counter

import colour_roles as CR

CARD = "prior4_template_cover_completion"
CONCEPT = "template_cover_completion"
MEMBERS = ["14754a24", "150deff5", "1818057f", "36fdfd69", "50846271", "626c0bcc", "7e02026e",
           "896d5239", "9caba7c3"]
READING = {
    "generator": ("Enumerate placements of template pieces that lie on support cells and hold >= minm evidence "
                  "cells; keep all of them (opening), or the fewest pieces explaining the evidence (greedy most-"
                  "unexplained-evidence-first, or exact disjoint cover = exact tiling when the evidence is the blob); "
                  "paint each chosen piece by its induced per-offset colour pattern, keeping the evidence (fill the "
                  "missing cells) or repainting it (colour by piece type)."),
    "stop": ("open: all fitting translates; greedy: no remaining piece holds minm unexplained evidence cells; "
             "exact: every evidence cell explained (node budget, else greedy fallback; a blob that cannot be tiled "
             "is left unchanged); at most MAXPL placements per grid."),
    "params": ("mode ∈ {fill (keep evidence), type (repaint by piece type)} · "
               "selection ∈ {open, greedy, greedy+overlap, exact} · minm ∈ {0,1,2} · clip ∈ {0,1} · "
               "evidence ∈ {none, CR.rank_colour(g, k) naming a never-changing non-background colour, = support "
               "(type)} · "
               "support ∈ {all but CR.background, all but the inert colour (role-bound) / a declared role, any, "
               "changed-input colours as roles} (+ evidence) · "
               "piece class ∈ {plus L1|L2|L3, saltire, square 2|3, bar 2|3|4, L-tromino, plus L1-3, triangle depth "
               "1-6, rectangle up to 8x8, components seen in training} (fill) or per-colour minimal output "
               "components, as seen or under 8 symmetries (type) · sizes ∈ {all, seen} (multi-size classes) · "
               "order ∈ {small-first, large-first} · efree ∈ {0,1} · paint pattern per (shape, offset) induced, each "
               "colour bound to CR.novel_colour(train) | CR.background | CR.rank_colour (no literals, G68)"),
    "participants": ("background = CR.background(g); changed cells = cells whose colour differs in the "
                     "output; fill colours = output colours of changed cells; evidence = an input colour present in "
                     "every input whose cells never change; support = which input colours a piece may cover; in type "
                     "mode every non-background cell is both support and evidence and each output colour's minimal "
                     "components are its piece type; a consistent placement paints only fill-colour (type-colour) "
                     "cells and changes one."),
    "preconditions": ("same-size input/output in every pair, some cell changes, at most 2 fill colours (fill) or "
                      "2..6 types of 2..9 cells (type), every changed cell lies in a training-consistent placement, "
                      "the per-offset paint pattern explains every changed cell, and the program reproduces every "
                      "training pair."),
}

BUDGET = 2000
MAXCONS = 400
MAXTARGETS = 400
MAXPL = 3000
MAXCELLS = 25


# ---------------------------------------------------------------- shapes
def _norm(cells):
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def _syms(shape):
    out = []
    for k in range(8):
        cells = []
        for r, c in shape:
            if k & 4:
                r, c = c, r
            if k & 1:
                r = -r
            if k & 2:
                c = -c
            cells.append((r, c))
        s = _norm(cells)
        if s not in out:
            out.append(s)
    return out


def _plus(L):
    return _norm([(0, 0)] + [(s * k, 0) for k in range(1, L + 1) for s in (1, -1)]
                 + [(0, s * k) for k in range(1, L + 1) for s in (1, -1)])


def _declared():
    """Small declared finite domain of elementary piece classes (each a list of oriented shapes)."""
    lib = []
    for L in (1, 2, 3):
        lib.append(("plus%d" % L, [_plus(L)]))
    lib.append(("saltire", [_norm([(0, 0), (1, 1), (2, 2), (0, 2), (2, 0)])]))
    for k in (2, 3):
        lib.append(("sq%d" % k, [tuple((r, c) for r in range(k) for c in range(k))]))
    for k in (2, 3, 4):
        lib.append(("bar%d" % k, _syms(tuple((0, c) for c in range(k)))))
    lib.append(("Ltri", _syms(((0, 0), (1, 0), (1, 1)))))
    lib.append(("plus*", [_plus(L) for L in (1, 2, 3)]))
    lib.append(("tri*", [t for k in range(1, 7)
                         for t in _syms(tuple((d, c) for d in range(k + 1) for c in range(k - d, k + d + 1)))]))
    lib.append(("rect*", [tuple((r, c) for r in range(h) for c in range(w))
                          for h in range(1, 9) for w in range(1, 9) if h * w > 1]))
    return lib


# ---------------------------------------------------------------- participants
def _bg(g):
    """background <- CR.background(g) (per-grid mode, ties -> lower colour)."""
    return CR.background(g)


RANKR = tuple(("rank", k) for k in CR.RANKS)
EVROLES = (("rank", -1), ("rank", 1), ("rank", 2), ("rank", 3), ("rank", -2))
COLROLES = (("novel",), ("background",)) + RANKR


def _rname(role):
    return role[0] if len(role) == 1 else "%s%d" % role


def _rcol(g, role, rc=None):
    """Resolve a colour role on grid g.  rc = role-bound constants learned from the training pairs:
    {'novel': CR.novel_colour(train), 'inert': the inert colour (see BINDINGS)}."""
    if role[0] == "rank":
        return CR.rank_colour(g, role[1], CR.background(g))
    if role[0] == "background":
        return CR.background(g)
    return (rc or {}).get(role[0])


def _role_for(grids, c, roles, rc=None):
    """The first role in `roles` naming colour c in every grid (None if none does)."""
    for role in roles:
        if all(_rcol(g, role, rc) == c for g in grids):
            return role
    return None


def _evc(g, ev):
    """Resolve the evidence binding on grid g: None or a colour role (CR.rank_colour(g, k))."""
    if ev is None:
        return None
    return _rcol(g, ev)



def _comps(cells):
    cells = set(cells)
    out = []
    while cells:
        s = cells.pop()
        comp, st = [s], [s]
        while st:
            r, c = st.pop()
            for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if n in cells:
                    cells.remove(n)
                    comp.append(n)
                    st.append(n)
        out.append(sorted(comp))
    out.sort()
    return out


def _masks(g, P):
    H, W = len(g), len(g[0])
    if P["mode"] == "type":
        bg = _bg(g)
        sup = [[g[r][c] != bg for c in range(W)] for r in range(H)]
        return sup, sup
    S, ev = P["support"], _evc(g, P["evidence"])
    if S == "nonbg":
        S = frozenset(set(v for row in g for v in row) - {_bg(g)})
    elif S is not None and S[0] == "not":     # all but the colour a role names on this grid
        S = frozenset(set(v for row in g for v in row) - {_rcol(g, S[1], P.get("rc"))})
    elif S is not None:                       # ("src", roles): the colours the roles name on this grid
        S = frozenset(_rcol(g, r, P.get("rc")) for r in S[1])
    sup = [[S is None or g[r][c] in S or g[r][c] == ev for c in range(W)] for r in range(H)]
    evm = [[g[r][c] == ev for c in range(W)] for r in range(H)]
    return sup, evm


def _rowbits(m, H, W, pad, outside):
    """Padded row bitmasks of a boolean grid; cells beyond the grid are set iff `outside`."""
    Wp = W + 2 * pad
    full = (1 << Wp) - 1
    rim = full & ~(((1 << W) - 1) << pad) if outside else 0
    rows = []
    for rp in range(H + 2 * pad):
        r = rp - pad
        if 0 <= r < H:
            v = rim
            row = m[r]
            for c in range(W):
                if row[c]:
                    v |= 1 << (c + pad)
        else:
            v = full if outside else 0
        rows.append(v)
    return rows


def _bits(memo, m, H, W, pad, outside):
    """Row bitmasks of mask `m` plus its AND/OR aggregate caches; shared through `memo` (keyed by the
    identity of a mask that the caller keeps alive) across calls."""
    if memo is None:
        return _rowbits(m, H, W, pad, outside), {}, {}, {}
    key = (id(m), pad, outside)
    v = memo.get(key)
    if v is None:
        v = memo[key] = (_rowbits(m, H, W, pad, outside), {}, {}, {})
    return v


def _popcount(x):
    return bin(x).count("1")


def _placements(g, P, sup, evm, seeds=None, memo=None, seedmask=None, pcache=None):
    """-> list of (key, anchor, cells, evcells), key = (class rank, shape index), cells = [(y, x, offset)]
    (in-grid cells only; with clip a piece may hang over the edge).  Placements lie on support and hold
    >= minm evidence cells; with `seeds`, they must also cover a seed cell.  Fitting is tested a whole row of
    anchors at a time on bitmasks.  None when the placements explode (fast rejection)."""
    H, W = len(g), len(g[0])
    clip, need = P["clip"], P["minm"]
    shapes = P["shapes"]
    pad = max(max(max(r for r, _ in t), max(c for _, c in t)) for _, t in shapes)
    S, fitc, _, _ = _bits(memo, sup, H, W, pad, bool(clip))
    E, _, anyc, twoc = _bits(memo, evm, H, W, pad, False)
    Z = None
    if seeds is not None:
        zm = seedmask
        if zm is None:
            zm = [[False] * W for _ in range(H)]
            for r, c in seeds:
                zm[r][c] = True
        Z, _, seedc, _ = _bits(memo if seedmask is not None else None, zm, H, W, pad, False)

    def agg(cache, rows, rp, pat, conj):
        key = (rp, pat)
        v = cache.get(key)
        if v is None:
            x = rows[rp]
            v = x >> pat[0]
            for j in pat[1:]:
                v = (v & (x >> j)) if conj else (v | (x >> j))
            cache[key] = v
        return v

    def two(rp, pat):
        # (>=1, >=2) evidence masks of one row pattern
        key = (rp, pat)
        v = twoc.get(key)
        if v is None:
            x = E[rp]
            a1 = a2 = 0
            for j in pat:
                t = x >> j
                a2 |= a1 & t
                a1 |= t
            v = twoc[key] = (a1, a2)
        return v

    # pass 1: exact masks of the anchors that place a piece (support, evidence count, seed), counted so that
    # an exploding list is refused before any piece is built (the count is exact: evidence and seeds lie
    # inside the grid, and need = 0 only occurs without clipping)
    Hp = H + 2 * pad
    rows = []
    total = 0
    for si, (rank, shape) in enumerate(shapes):
        hh = max(r for r, _ in shape)
        byrow = {}
        for dr, dc in shape:
            byrow.setdefault(dr, []).append(dc)
        pats = [(dr, tuple(sorted(v))) for dr, v in sorted(byrow.items())]
        fits = []
        # anchor rows whose piece meets the grid (non-clip: lies inside it); other rows place nothing
        rlo, rhi = (max(0, pad - hh), min(Hp - hh, pad + H)) if clip else (pad, pad + H - hh)
        for rp in range(rlo, rhi):
            fit = -1
            for dr, pat in pats:
                key = (rp + dr, pat)
                v = fitc.get(key)
                if v is None:
                    v = agg(fitc, S, rp + dr, pat, True)
                fit &= v
                if not fit:
                    break
            if not fit:
                continue
            if need >= 2:
                a1 = a2 = 0
                for dr, pat in pats:
                    b1, b2 = two(rp + dr, pat)
                    a2 |= b2 | (a1 & b1)
                    a1 |= b1
                fit &= a2
            elif need:
                a = 0
                for dr, pat in pats:
                    v = anyc.get((rp + dr, pat))
                    if v is None:
                        v = agg(anyc, E, rp + dr, pat, False)
                    a |= v
                fit &= a
            if Z is not None and fit:
                a = 0
                for dr, pat in pats:
                    a |= agg(seedc, Z, rp + dr, pat, False)
                fit &= a
            if fit:
                fits.append((rp, fit))
                total += _popcount(fit)
        rows.append(fits)
    if total > MAXPL:
        return None
    # pass 2: build the pieces (an in-grid piece depends only on the grid's evidence mask, shape and anchor,
    # so it is shared through `pcache` -- keyed by the identity of an evidence mask kept alive by the caller)
    res = []
    pc = None
    if pcache is not None:
        pc = pcache.get(id(evm))
        if pc is None:
            pc = pcache[id(evm)] = ({}, {})
        sids, pc = pc
    for si, (rank, shape) in enumerate(shapes):
        hh = max(r for r, _ in shape)
        ww = max(c for _, c in shape)
        offs = [(dr, dc, k) for k, (dr, dc) in enumerate(shape)]
        if pc is not None:
            sid = sids.get(shape)
            if sid is None:
                sid = sids[shape] = len(sids)
        for rp, fit in rows[si]:
            r = rp - pad
            while fit:
                low = fit & -fit
                fit ^= low
                c = low.bit_length() - 1 - pad
                if 0 <= r and r + hh < H and 0 <= c and c + ww < W:
                    if pc is not None:
                        pk = (rank, si, sid, r, c)
                        pl = pc.get(pk)
                        if pl is None:
                            pl = pc[pk] = ((rank, si), (r, c), [(r + dr, c + dc, k) for dr, dc, k in offs],
                                           [(r + dr, c + dc) for dr, dc, k in offs if evm[r + dr][c + dc]])
                        if len(pl[3]) < need:
                            continue
                        res.append(pl)
                        if len(res) > MAXPL:
                            return None
                        continue
                    evc = [(r + dr, c + dc) for dr, dc, k in offs if evm[r + dr][c + dc]]
                    if len(evc) < need:
                        continue
                    cells = [(r + dr, c + dc, k) for dr, dc, k in offs]
                else:
                    if pc is not None:
                        # a piece over the edge (clip) keeps its in-grid cells: also shared
                        pk = (rank, si, sid, r, c)
                        pl = pc.get(pk)
                        if pl is None:
                            cl = [(r + dr, c + dc, k) for dr, dc, k in offs if 0 <= r + dr < H and 0 <= c + dc < W]
                            pl = pc[pk] = ((rank, si), (r, c), cl, [(y, x) for y, x, k in cl if evm[y][x]])
                        if not pl[2] or len(pl[3]) < need:
                            continue
                        res.append(pl)
                        if len(res) > MAXPL:
                            return None
                        continue
                    cells = [(r + dr, c + dc, k) for dr, dc, k in offs if 0 <= r + dr < H and 0 <= c + dc < W]
                    evc = [(y, x) for y, x, k in cells if evm[y][x]]
                    if not cells or len(evc) < need:
                        continue
                res.append(((rank, si), (r, c), cells, evc))
                if len(res) > MAXPL:
                    return None
    return res


# ---------------------------------------------------------------- selection
def _cellset(p, cells_of):
    cs = cells_of.get(id(p))
    if cs is None:
        cs = cells_of[id(p)] = frozenset((y, x) for y, x, k in p[2])
    return cs


def _greedy_key(order):
    sgn = -1 if order == "large" else 1
    return lambda p: (-len(p[3]), -len(p[3]), sgn * len(p[2]) if order else 0, p[0][0], p[1])


def _exact_key(order):
    sgn = -1 if order == "large" else 1
    return lambda p: (p[0][0], -len(p[3]), sgn * len(p[2]), p[1])


def _select_greedy(pls, overlap, minm, order, cells_of=None, ordered=None):
    """Repeatedly take the placement holding the most unexplained evidence (ties: more evidence, size order,
    class rank, row-major); stop when none holds max(minm,1) unexplained evidence cells."""
    sgn = -1 if order == "large" else 1
    need = max(minm, 1)

    def key(p, n):
        return (-n, -len(p[3]), sgn * len(p[2]) if order else 0, p[0][0], p[1])

    chosen = []
    if not overlap:
        # disjoint pieces never share evidence, so the static count is the dynamic one
        used = set()
        if cells_of is None:
            cells_of = {}
        if ordered is None:
            ordered = sorted((p for p in pls if len(p[3]) >= need), key=lambda p: key(p, len(p[3])))
        for p in ordered:
            if len(p[3]) < need:
                continue
            cs = _cellset(p, cells_of)
            if used.isdisjoint(cs):
                chosen.append(p)
                used.update(cs)
        return chosen
    left = set(e for p in pls for e in p[3])
    heap = [(key(p, len(p[3])), i) for i, p in enumerate(pls) if len(p[3]) >= need]
    heapq.heapify(heap)
    while heap:
        k0, i = heapq.heappop(heap)
        p = pls[i]
        n = sum(1 for e in p[3] if e in left)
        if n < need:
            continue
        k1 = key(p, n)
        if k1 != k0:
            heapq.heappush(heap, (k1, i))
            continue
        chosen.append(p)
        left.difference_update(p[3])
    return chosen


def _greedy_overlap_heap(entries, base, pls, minm, good=None):
    """Overlapping greedy (as in _select_greedy) from heap entries (initial key, index into `base`) that
    are already sorted; `pls` (a subsequence of `base`) supplies the evidence still to explain."""
    need = max(minm, 1)
    left = set(e for p in pls for e in p[3])
    heap = list(entries)
    chosen = []
    while heap:
        k0, j = heapq.heappop(heap)
        p = base[j]
        n = sum(1 for e in p[3] if e in left)
        if n < need:
            continue
        k1 = (-n,) + k0[1:]
        if k1 != k0:
            heapq.heappush(heap, (k1, j))
            continue
        if good is not None and not good(p):
            return None  # a chosen piece paints a wrong colour: the output cannot match
        chosen.append(p)
        left.difference_update(p[3])
    return chosen


def _select_exact(pls, targets, order, cells_of=None, ordered=None, byget=None):
    """Non-overlapping placements covering all targets; None if impossible or not found within budget.
    `byget` (optional) gives, per target cell, the candidate pieces holding it in trial order (None when
    there is none), replacing the index built here."""
    sgn = -1 if order == "large" else 1
    targets = sorted(targets)
    if len(targets) > MAXTARGETS:
        return None
    if byget is not None:
        byget, has = byget
        if not all(has(t) for t in targets):
            return None
        by = _LazyIndex(byget)
    else:
        cover = set()
        for p in pls:
            cover.update(p[3])
        if any(t not in cover for t in targets):
            return None
        by = {}
        for p in (sorted(pls, key=lambda p: (p[0][0], -len(p[3]), sgn * len(p[2]), p[1])) if ordered is None
                  else ordered):
            for e in p[3]:
                by.setdefault(e, []).append(p)
    if cells_of is None:
        cells_of = {}
    used = set()
    chosen = []
    cnt = [BUDGET]

    def rec(i):
        cnt[0] -= 1
        if cnt[0] < 0:
            return None
        while i < len(targets) and targets[i] in used:
            i += 1
        if i == len(targets):
            return True
        for p in by[targets[i]]:
            cs = cells_of.get(id(p))
            if cs is None:
                cs = cells_of[id(p)] = frozenset((y, x) for y, x, k in p[2])
            if not cs.isdisjoint(used):
                continue
            used.update(cs)
            chosen.append(p)
            r = rec(i + 1)
            if r:
                return True
            chosen.pop()
            used.difference_update(cs)
            if r is None:
                return None
        return False

    return list(chosen) if rec(0) else None


def _filter(pls, P, evoff_of=None):
    """Keep placements of the allowed shape sizes whose evidence-free offsets hold no evidence.
    (`evoff_of`: optional cache id(placement) -> offsets holding evidence.)"""
    allowed, efree = P.get("allowed"), P.get("efree")
    if allowed is None and not efree:
        return pls
    out = []
    for p in pls:
        si = p[0][1]
        if allowed is not None and si not in allowed:
            continue
        free = efree.get(si) if efree else None
        if free and p[3]:
            if evoff_of is None:
                evs = set(p[3])
                if any(k in free and (y, x) in evs for y, x, k in p[2]):
                    continue
            else:
                eo = evoff_of.get(id(p))
                if eo is None:
                    evs = set(p[3])
                    eo = evoff_of[id(p)] = frozenset(k for y, x, k in p[2] if (y, x) in evs)
                if not free.isdisjoint(eo):
                    continue
        out.append(p)
    return out


def _choose(g, P, sup, evm, pls):
    sel = P["sel"]
    if sel == "open":
        return pls
    if sel == "greedy":
        return _select_greedy(pls, P["overlap"], P["minm"], P["order"])
    H, W = len(g), len(g[0])
    if P["mode"] == "type":
        cid = {}
        comps = _comps([(r, c) for r in range(H) for c in range(W) if sup[r][c]])
        for i, comp in enumerate(comps):
            for cell in comp:
                cid[cell] = i
        by = {}
        for p in pls:
            i = cid[p[2][0][:2]]
            if all(cid[(y, x)] == i for y, x, k in p[2]):
                by.setdefault(i, []).append(p)
        chosen = []
        for i, comp in enumerate(comps):
            res = _select_exact(by.get(i, []), comp, P["order"])
            if res:
                chosen.extend(res)
        return chosen
    targets = [(r, c) for r in range(H) for c in range(W) if evm[r][c]]
    res = _select_exact(pls, targets, P["order"])
    if res is None:
        res = _select_greedy(pls, False, P["minm"], P["order"])
    return res


# ---------------------------------------------------------------- painting
def _paint(g, P, evm, chosen):
    """Paint the chosen pieces.  Pattern values are colours during induction (training pairs) and colour roles in
    a program (resolved on the grid being painted)."""
    out = [row[:] for row in g]
    keep = P["mode"] == "fill"
    pat = P["pattern"]
    res = {}
    for key, rc, cells, evc in chosen:
        pt = pat.get(key[1])
        if pt is None:
            continue
        for y, x, k in cells:
            if keep and evm[y][x]:
                continue
            v = pt.get(k)
            if type(v) is tuple:
                if v not in res:
                    res[v] = _rcol(g, v, P.get("rc"))
                v = res[v]
            if v is not None:
                out[y][x] = v
    return out


def _render(g, P):
    sup, evm = _masks(g, P)
    pls = _placements(g, P, sup, evm)
    if pls is None:
        return [row[:] for row in g]
    return _paint(g, P, evm, _choose(g, P, sup, evm, _filter(pls, P)))


def _make(P, known=None):
    """Program for P.  `known` maps training inputs to their outputs, which the program was verified to
    reproduce, so those are returned (as copies) without recomputation."""
    P = dict(P)
    if not known:
        return lambda g: _render(g, P)

    def fn(g):
        out = known.get(tuple(map(tuple, g)))
        if out is not None:
            return [list(r) for r in out]
        return _render(g, P)
    return fn


# ---------------------------------------------------------------- induction
def _consistent(cache, P, quick=False, votepls=None, known=False, codes_of=None):
    """Training-consistent placements: every painted cell holds a fill colour (fill) / its type colour (type)
    and one of them changes.  They must cover all changed cells.  Induces the per-offset paint pattern, the
    observed sizes of a multi-size class and the evidence-free offsets.  -> list of variants or None."""
    keep = P["mode"] == "fill"
    multi = keep and len({len(s) for _, s in P["shapes"]}) > 1
    fills = set().union(*[c[3] for c in cache])
    vote = keep and len(fills) > 1
    votes = {}
    evseen = {}
    observed = set()
    if known and multi and any(len(c[6]) > MAXCONS for c in cache):
        multi = False  # (all listed placements are consistent: some pair has too many to compare)
    koff = [{rc: k for k, rc in enumerate(shape)} for _, shape in P["shapes"]]
    for g, o, D, dst, sup, evm, pls in cache:
        covered = set()
        cons = []
        if known and not quick:
            # listed placements are consistent by construction and cover every changed cell (checked by
            # the caller): only the pattern votes, evidence offsets and maximality are collected
            flat = {}
            for key, rc, cells, evc in pls:
                si = key[1]
                if vote:
                    fl = flat.get(si)
                    if fl is None:
                        fl = flat[si] = []
                    if codes_of is None:
                        fl.extend([k * 16 + o[y][x] for y, x, k in cells if not evm[y][x]])
                    else:
                        cd = codes_of.get(id(cells))
                        if cd is None:
                            cd = codes_of[id(cells)] = [k * 16 + o[y][x] for y, x, k in cells if not evm[y][x]]
                        fl.extend(cd)
                else:
                    votes[si] = None
                if evc:
                    s = evseen.setdefault(si, set())
                    r, c = rc
                    ko = koff[si]
                    for y, x in evc:
                        s.add(ko[(y - r, x - c)])
                if multi:
                    cons.append((si, frozenset((y, x) for y, x, k in cells)))
            for si, fl in flat.items():
                vs = votes.setdefault(si, {})
                for code, m in Counter(fl).items():
                    vk = (code >> 4, code & 15)
                    vs[vk] = vs.get(vk, 0) + m
            covered = D
        for key, rc, cells, evc in (() if known and not quick else pls):
            si = key[1]
            paint = [(y, x, k) for y, x, k in cells if not evm[y][x]] if keep else cells
            if known:
                pass  # listed placements are consistent by construction
            elif not paint or not any((y, x) in D for y, x, k in paint):
                continue
            elif keep:
                if any(o[y][x] not in dst for y, x, k in paint):
                    continue
            else:
                tc = P["typecol"][key[0]]
                if any(o[y][x] != tc for y, x, k in paint):
                    continue
            covered.update((y, x) for y, x, k in paint)
            if quick:
                continue
            if vote:
                vs = votes.setdefault(si, {})
                for y, x, k in paint:
                    vk = (k, o[y][x])
                    vs[vk] = vs.get(vk, 0) + 1
            elif keep:
                votes[si] = None
            if evc:
                s = evseen.setdefault(si, set())
                for y, x, k in cells:
                    if evm[y][x]:
                        s.add(k)
            if multi:
                cons.append((si, frozenset((y, x) for y, x, k in cells)))
        if not D <= covered:
            return None
        if quick:
            continue
        if multi and len(cons) > MAXCONS:
            multi = False
            observed = set()
        if multi:
            # a shape size is observed when one of its consistent placements is maximal
            idx = {}
            for j, (si, cs) in enumerate(cons):
                for cell in cs:
                    idx.setdefault(cell, []).append(j)
            for si, cs in cons:
                if si in observed:
                    continue
                first = min(cs)
                if not any(len(cons[j][1]) > len(cs) and cs < cons[j][1] for j in idx[first]):
                    observed.add(si)
    if quick:
        return True
    pattern = {}
    if keep and not vote:
        # one fill colour: every piece fills its missing cells with it
        f = next(iter(fills))
        votes = {si: None for si in range(len(P["shapes"]))}
    for si, d in votes.items():
        if d is None:
            pattern[si] = {k: f for k in range(len(P["shapes"][si][1]))}
            continue
        best = {}
        for (k, v), n in sorted(d.items()):
            if k not in best or n > best[k][0]:
                best[k] = (n, v)
        pattern[si] = {k: v for k, (n, v) in best.items()}
    if vote:
        # several fill colours: the per-offset pattern itself must explain every changed cell
        okcodes = {si: frozenset(k * 16 + v for k, v in d.items()) for si, d in pattern.items()}
        empty = frozenset()
        for i, (g, o, D, dst, sup, evm, pls) in enumerate(cache):
            if votepls is not None:
                pls = votepls(i, pattern)
                if pls is None:
                    return None
            # a piece explains its painted cells when each one's (offset, output colour) is in the pattern;
            # changed cells are never evidence, so discarding all of a piece's cells is the same
            left = set(D)
            for key, rc, cells, evc in pls:
                if not left:
                    break
                cd = codes_of.get(id(cells)) if codes_of is not None else None
                if cd is None:
                    cd = [k * 16 + o[y][x] for y, x, k in cells if not evm[y][x]]
                if cd and okcodes.get(key[1], empty).issuperset(cd):
                    left.difference_update([(y, x) for y, x, k in cells])
            if left:
                return None
    if not keep:
        for si, (rank, shape) in enumerate(P["shapes"]):
            pattern[si] = {k: P["typecol"][rank] for k in range(len(shape))}
    else:
        # offsets of a shape never seen in a consistent placement take the shape's (unique) colour
        for si, (rank, shape) in enumerate(P["shapes"]):
            d = pattern.get(si)
            if d is None:
                continue
            vals = set(d.values())
            if len(vals) == 1 and len(d) < len(shape):
                v = vals.pop()
                for k in range(len(shape)):
                    d.setdefault(k, v)
        # an orientation never seen consistently borrows a constant colour from its class
        cls = {}
        for si, (rank, shape) in enumerate(P["shapes"]):
            if si in pattern:
                cls.setdefault(rank, set()).update(pattern[si].values())
        for si, (rank, shape) in enumerate(P["shapes"]):
            if si not in pattern and len(cls.get(rank, ())) == 1:
                v = next(iter(cls[rank]))
                pattern[si] = {k: v for k in range(len(shape))}
    efree = {}
    for si, (rank, shape) in enumerate(P["shapes"]):
        if si in evseen:
            efree[si] = frozenset(k for k in range(len(shape)) if k not in evseen[si])
    variants = [("all", None, pattern, efree)]
    if multi and observed and len(observed) < len(P["shapes"]):
        variants.append(("seen", frozenset(observed), pattern, efree))
    return variants


def _observed_shapes(train_info, evs):
    """evs: the evidence colour of each training pair (None: no evidence)."""
    seen = []
    for (g, o, D, dst), ev in zip(train_info, evs):
        H, W = len(g), len(g[0])
        sets = [set(D)]
        if ev is not None:
            sets.append(set(D) | {(r, c) for r in range(H) for c in range(W) if g[r][c] == ev})
        for cells in sets:
            for comp in _comps(cells):
                if 2 <= len(comp) <= MAXCELLS:
                    s = _norm(comp)
                    if s not in seen:
                        seen.append(s)
    seen.sort(key=lambda s: (len(s), s))
    return seen[:6]


def _type_classes(train_info, sym):
    """Per output colour: the minimal 4-components of that colour on the support -> oriented shapes."""
    best = {}
    for g, o, D, dst in train_info:
        H, W = len(g), len(g[0])
        bg = _bg(g)
        bycol = {}
        for r in range(H):
            for c in range(W):
                if g[r][c] != bg:
                    bycol.setdefault(o[r][c], []).append((r, c))
        for col, cells in bycol.items():
            for comp in _comps(cells):
                s = _norm(comp)
                cur = best.get(col)
                if cur is None or len(s) < cur[0]:
                    best[col] = (len(s), [s])
                elif len(s) == cur[0] and s not in cur[1]:
                    cur[1].append(s)
    classes = []
    for col in sorted(best):
        n, shapes = best[col]
        if n > 9 or n < 2:
            return None  # a piece type is a small template of 2..9 cells
        if sym:
            allv = []
            for s in shapes:
                for t in _syms(s):
                    if t not in allv:
                        allv.append(t)
            shapes = allv
        classes.append((col, shapes))
    return classes


def _info(train):
    info = []
    for p in train:
        g, o = p["input"], p["output"]
        if not g or len(g) != len(o) or any(len(a) != len(b) for a, b in zip(g, o)):
            return None
        D = set()
        dst = set()
        for r, (ra, rb) in enumerate(zip(g, o)):
            for c, (a, b) in enumerate(zip(ra, rb)):
                if a != b:
                    D.add((r, c))
                    dst.add(b)
        info.append((g, o, D, dst))
    if not any(D for _, _, D, _ in info):
        return None
    return info


def _configs(info, novel=None):
    """Yield (cost, P) base configurations (without pattern) in preference order.  Every colour is a role (G68)."""
    dst = set().union(*[d for _, _, _, d in info])
    srcs = set()
    for g, o, D, _ in info:
        for r, c in D:
            srcs.add(g[r][c])
    incols = set.intersection(*[set(v for r in g for v in r) for g, _, _, _ in info])
    grids = [g for g, _, _, _ in info]
    rc0 = {"novel": novel}
    # ---- fill mode (keep evidence, paint missing cells)
    # the fill colours must be named by a role in every training pair (else the pattern needs a literal)
    if len(dst) <= 2 and all(_role_for(grids, f, COLROLES, rc0) is not None for f in dst):
        changing = srcs
        bgs = {_bg(g) for g in grids}
        # evidence roles: CR.rank_colour(g, k) naming, in every training input, a colour that is not that grid's
        # background, never changes and is not a fill colour; roles selecting the same colours are one option
        evs, evsig = [None], {None: [None] * len(info)}
        seen_sig = set()
        for role in EVROLES:
            cols = [_rcol(g, role) for g in grids]
            if any(c is None or c == _bg(g) or c in dst or c in changing for c, g in zip(cols, grids)):
                continue
            if tuple(cols) in seen_sig:
                continue
            seen_sig.add(tuple(cols))
            evs.append(role)
            evsig[role] = cols
        for ev in evs:
            evcols = evsig[ev]
            evset = set(c for c in evcols if c is not None)
            lib = list(_declared())
            for i, s in enumerate(_observed_shapes(info, evcols)):
                if all(s not in shapes for _, shapes in lib):
                    lib.append(("seen%d" % i, [s]))
            # supports in preference order: role-bound (all but CR.background; all but the inert colour = the one
            # colour present in every input, never changing, neither evidence nor fill nor source (role-bound value
            # defined here); the whole grid) before the source-colour set; each priors3 literal is replaced by the
            # role naming it in every training input, or dropped when none does
            cand = sorted(x for x in incols if x not in dst and x not in srcs and x not in evset)
            inert = cand[0] if len(cand) == 1 else None
            rc = {"novel": novel, "inert": inert}
            nots = sorted(set(cand) | {x for x in bgs if x not in srcs and x not in evset})
            notroles = []
            for x in nots:
                role = ("inert",) if x == inert else _role_for(grids, x, (("background",),) + RANKR)
                if role is not None and role not in notroles:
                    notroles.append(role)
            srcroles = tuple(_role_for(grids, x, (("background",),) + RANKR) for x in sorted(srcs))
            srcopt = ("src", srcroles) if srcroles and None not in srcroles else "drop"
            supports, sigs = [], set()
            opts = (("nonbg", srcopt) if ev is None else
                    ("nonbg",) + tuple(("not", r) for r in notroles) + (None, srcopt))
            for S in opts:
                if S == "drop":
                    continue
                sig = []
                for g, e in zip(grids, evcols):
                    cols = set(v for r in g for v in r)
                    if S == "nonbg":
                        sel = cols - {_bg(g)}
                    elif S is None:
                        sel = cols
                    elif S[0] == "not":
                        sel = cols - {_rcol(g, S[1], rc)}
                    else:
                        sel = cols & {_rcol(g, r, rc) for r in S[1]}
                    sig.append(tuple(sorted(sel | ({e} & cols))))
                sig = tuple(sig)
                if sig not in sigs:
                    sigs.add(sig)
                    supports.append(S)
            for si_, S in enumerate(supports):
                for ci, (cname, shapes) in enumerate(lib):
                    if ev is None and len({len(t) for t in shapes}) > 1:
                        continue  # the opening by a multi-size class is the opening by its smallest piece
                    rects = all(len(t) == (t[-1][0] + 1) * (t[-1][1] + 1) for t in shapes)
                    for clip in ((0,) if ev is None or (rects and len(shapes) > 1) else (0, 1)):
                        P = {"mode": "fill", "evidence": ev, "support": S, "clip": clip,
                             "shapes": [(0, s) for s in shapes], "cname": cname, "rc": rc}
                        base = (ev is not None) + si_ + clip + 0.05 * ci
                        yield base, P
    # ---- type mode (evidence = support = non-background, repaint each piece by its type colour)
    if 2 <= len(dst) <= 6:
        for sym in (0, 1):
            classes = _type_classes(info, sym)
            if not classes or len(classes) < 2:
                continue
            shapes = []
            typecol = {}
            for rank, (col, shs) in enumerate(classes):
                typecol[rank] = col
                for s in shs:
                    shapes.append((rank, s))
            if len(shapes) > 24:
                continue
            # every piece-type colour must be named by a role in every training pair (G68), else no program
            if any(_role_for(grids, col, COLROLES, rc0) is None for col in typecol.values()):
                continue
            P = {"mode": "type", "evidence": None, "support": None, "clip": 0, "shapes": shapes,
                 "typecol": typecol, "cname": "types%d" % sym, "rc": rc0}
            yield 1.5 + sym, P


def _supname(S):
    if S is None or S == "nonbg":
        return "any" if S is None else S
    if S[0] == "not":
        return "not:" + _rname(S[1])
    return "src:" + "+".join(_rname(r) for r in S[1])


def _role_pattern(pattern, grids, rc):
    """Bind every pattern colour to the first of CR.novel_colour(train), CR.background, CR.rank_colour that names it
    in every training input (G68).  None when some colour has no role (the program would need a literal)."""
    out, memo = {}, {}
    for si, d in pattern.items():
        nd = {}
        for k, v in d.items():
            if v not in memo:
                memo[v] = _role_for(grids, v, COLROLES, rc)
            if memo[v] is None:
                return None
            nd[k] = memo[v]
        out[si] = nd
    return out


def _minms(P):
    if P["mode"] == "type":
        return (1,)
    return (0,) if P["evidence"] is None else (1, 2)


def _selections(P):
    """Selection rules for a configuration whose minm is fixed: (extra cost, P)."""
    if P["mode"] == "type":
        for order in ("large", "small"):
            yield 0.0, dict(P, sel="exact", overlap=0, order=order)
        return
    if P["evidence"] is None:
        yield 0.0, dict(P, sel="open", overlap=1, order=None)
        return
    sizes = len({len(s) for _, s in P["shapes"]})
    orders = ("small", "large") if sizes > 1 else (None,)
    for oi, order in enumerate(orders):
        yield 0.0 + 0.1 * oi, dict(P, sel="greedy", overlap=0, order=order)
        yield 0.3 + 0.1 * oi, dict(P, sel="greedy", overlap=1, order=order)
        yield 0.5 + 0.1 * oi, dict(P, sel="exact", overlap=0, order=order)
    yield 0.6, dict(P, sel="open", overlap=1, order=None)


class _Lazy:
    """A sequence computed on first iteration."""

    def __init__(self, make):
        self.make = make

    def __iter__(self):
        return iter(self.make())


class _Dead(Exception):
    """A training grid's placements explode: the configuration yields nothing."""


def _derive(store, key, minm, compute):
    """Placement lists for minm=2 are the minm=1 lists filtered (same order; the cap cannot bite)."""
    if key + (minm,) in store:
        return store[key + (minm,)]
    base = store.get(key + (1,), False) if minm == 2 else False
    if base is not False and base is not None:
        res = [p for p in base if len(p[3]) >= 2]
    else:
        res = compute()
    store[key + (minm,)] = res
    return res


def _covers(pls, D):
    """Do the listed placements (all holding a changed, hence non-evidence, cell) cover every changed cell?"""
    left = set(D)
    for p in pls:
        for y, x, k in p[2]:
            left.discard((y, x))
        if not left:
            return True
    return not left


def _lazy_filter(full, R1, evoff_of=None):
    got = {}

    def fpl(i):
        v = got.get(i)
        if v is None:
            v = got[i] = _filter(full(i), R1, evoff_of)
        return v
    return fpl


def _ordered(presort, full, fpl, i, which, order):
    """fpl(i) sorted by a selection key: the full list sorted once (stable), restricted to fpl(i)."""
    k = (i, which, order)
    base = presort.get(k)
    if base is None:
        base = presort[k] = sorted(full(i), key=(_greedy_key if which == "g" else _exact_key)(order))
    fl = fpl(i)
    if fl is full(i):
        return base
    ids = set(map(id, fl))
    return [p for p in base if id(p) in ids]


def _overlap_entries(presort, full, fpl, i, order, need):
    k = (i, "h", order)
    allent = presort.get(k)
    if allent is None:
        key = _greedy_key(order)
        allent = presort[k] = sorted((key(p), j) for j, p in enumerate(full(i)))
    base = full(i)
    fl = fpl(i)
    if fl is base:
        return [e for e in allent if len(base[e[1]][3]) >= need]
    ids = set(map(id, fl))
    return [e for e in allent if id(base[e[1]]) in ids and len(base[e[1]][3]) >= need]


class _LazyIndex(dict):
    def __init__(self, get):
        dict.__init__(self)
        self.get_ = get

    def __missing__(self, t):
        v = self[t] = self.get_(t)
        return v


def _exact_index(presort, full, fpl, i, order):
    """(byget, has) for _select_exact: the candidates of a target in trial order, restricted to fpl(i),
    and whether there is one."""
    k = (i, "E", order)
    by_full = presort.get(k)
    if by_full is None:
        by_full = {}
        for p in sorted(full(i), key=_exact_key(order)):
            for e in p[3]:
                by_full.setdefault(e, []).append(p)
        presort[k] = by_full
    fl = fpl(i)
    if fl is full(i):
        return (lambda t: by_full[t]), (lambda t: t in by_full)
    ids = set(map(id, fl))

    def byget(t):
        return [p for p in by_full.get(t, ()) if id(p) in ids]

    def has(t):
        return any(id(p) in ids for p in by_full.get(t, ()))
    return byget, has


def _goodness(cache, pattern):
    """good(i, p): painting piece p alone leaves every cell it touches as in the output (fill mode).  A chosen
    piece that is not good makes the output differ when no other chosen piece touches its cells (disjoint
    selections), or when every piece paints the same single colour."""
    got = {}

    def good(i, p):
        k = (i, id(p))
        v = got.get(k)
        if v is None:
            g, o, D, dst, sup, evm = cache[i][:6]
            pt = pattern.get(p[0][1])
            v = True
            if pt is not None:
                for y, x, kk in p[2]:
                    if evm[y][x]:
                        continue
                    c = pt.get(kk)
                    if o[y][x] != (g[y][x] if c is None else c):
                        v = False
                        break
            got[k] = v
        return v
    return good


def _greedy_verdicts(cache, fpl, cells_of, presort, full, good):
    """Per pair and order: does disjoint greedy selection reproduce the output?  (Exact selection falls back
    to exactly this when no exact cover exists.)  Stops at the first chosen piece that is not good."""
    got = {}

    def verdict(i, R):
        k = (i, R["order"])
        v = got.get(k)
        if v is None:
            c = cache[i]
            need = max(R["minm"], 1)
            used = set()
            chosen = []
            v = None
            for p in _ordered(presort, full, fpl, i, "g", R["order"]):
                if len(p[3]) < need:
                    continue
                cs = _cellset(p, cells_of)
                if used.isdisjoint(cs):
                    if good is not None and not good(i, p):
                        v = False
                        break
                    chosen.append(p)
                    used.update(cs)
            if v is None:
                v = _paint(c[0], R, c[5], chosen) == c[1]
            got[k] = v
        return v
    return verdict


def fam(train):
    info = _info(train)
    if info is None:
        return
    info.sort(key=lambda t: len(t[0]) * len(t[0][0]))  # small pairs first: cheap rejection
    n = len(info)
    memo = {}      # row bitmasks / aggregates of masks kept alive in `masks`
    masks = {}     # (pair, mode, support, evidence) -> (sup, evm, sup2)
    seedm = []     # per pair: changed-cell mask
    for g, o, D, dst in info:
        zm = [[False] * len(g[0]) for _ in g]
        for r, c in D:
            zm[r][c] = True
        seedm.append(zm)
    store = {}     # placement lists: (kind, config, pair, minm); kept alive for the id-keyed caches
    cells_of = {}  # id(placement) -> frozenset of its cells
    pcache = {}    # id(evidence mask) -> shared in-grid pieces
    codes_of = {}  # id(cells of a piece) -> its (offset, output colour) vote codes (pieces are per pair)
    evoff_of = {}  # id(placement) -> offsets of its evidence cells
    keep_alive = []

    evms = {}      # (pair, mode, evidence) -> one evidence mask object (shared placement cache key)

    def getmasks(i, P1):
        k = (i, P1["mode"], P1["support"], P1["evidence"])
        v = masks.get(k)
        if v is None:
            g, o, D, dst = info[i]
            sup, evm = _masks(g, P1)
            if P1["mode"] == "fill":
                evm = evms.setdefault((i, P1["evidence"]), evm)
            sup2 = None
            if P1["mode"] == "fill":
                sup2 = [[sup[r][c] and (evm[r][c] or o[r][c] in dst) for c in range(len(g[0]))]
                        for r in range(len(g))]
            v = masks[k] = (sup, evm, sup2)
        return v

    found = 0
    grids = [g for g, _, _, _ in info]
    for ci, (base, P0) in enumerate(_configs(info, CR.novel_colour(train))):
        for minm in _minms(P0):
            P1 = dict(P0, minm=minm, sel=None)
            cache = []
            for i, (g, o, D, dst) in enumerate(info):
                sup, evm, sup2 = getmasks(i, P1)
                if not all(sup[r][c] for r, c in D):
                    break
                if P1["mode"] == "fill":
                    # consistent placements lie on cells that are evidence or end in a fill colour
                    near = _derive(store, ("near", ci, i), minm,
                                   lambda: _placements(g, P1, sup2, evm, seeds=D, memo=memo, seedmask=seedm[i],
                                                       pcache=pcache))
                    if near is None or not _covers(near, D):
                        break
                else:
                    near = _derive(store, ("near", ci, i), minm,
                                   lambda: _placements(g, P1, sup, evm, seeds=D, memo=memo, seedmask=seedm[i],
                                                       pcache=pcache))
                    if near is None or not _consistent([(g, o, D, dst, sup, evm, near)], P1, quick=True):
                        break
                cache.append((g, o, D, dst, sup, evm, near))
            if len(cache) < n:
                continue

            presort = {}

            def full(i):
                g, o, D, dst, sup, evm, near = cache[i]
                res = _derive(store, ("full", ci, i), minm, lambda: _placements(g, P1, sup, evm, memo=memo, pcache=pcache))
                if res is None:
                    raise _Dead()
                return res

            def votepls(i, pattern):
                # placements whose painted cells all match the pattern and explain a changed cell lie on
                # support cells that are evidence or end in a pattern colour, and cover a changed cell
                g, o, D, dst, sup, evm, near = cache[i]
                vals = set(v for d in pattern.values() for v in d.values())
                if P1["mode"] == "fill" and vals <= dst:
                    return near  # every such placement is already listed (pattern colours are fill colours)
                sup3 = [[sup[r][c] and (evm[r][c] or o[r][c] in vals) for c in range(len(g[0]))]
                        for r in range(len(g))]
                return _placements(g, P1, sup3, evm, seeds=D, memo=None)

            # consistent placements are exactly the support placements covering a changed cell
            variants = _consistent(cache, P1, votepls=votepls, known=P1["mode"] == "fill", codes_of=codes_of)
            uniform = False
            if variants:
                pat0 = variants[0][2]
                good = _goodness(cache, pat0)
                vals = set(v for d in pat0.values() for v in d.values())
                uniform = (P1["mode"] == "fill" and len(vals) == 1 and
                           all(len(pat0.get(si, ())) == len(sh) for si, (_, sh) in enumerate(P1["shapes"])))
            try:
                for vi, (sizes, allowed, pattern, efree) in enumerate(variants or ()):
                    rpat = _role_pattern(pattern, grids, P1.get("rc"))
                    if rpat is None:
                        continue      # a pattern colour no role names: LOST (needs a literal)
                    for ef in ((0, 1) if P1["mode"] == "fill" and P1["evidence"] is not None else (0,)):
                        R1 = dict(P1, allowed=allowed, pattern=pattern, efree=efree if ef else None)
                        fpl = _lazy_filter(full, R1, evoff_of)
                        if ef:
                            if all(len(fpl(i)) == len(prev(i)) for i in range(n)):
                                continue  # the evidence-free offsets remove nothing: same as efree=0
                        prev = fpl
                        greedy_verdict = _greedy_verdicts(cache, fpl, cells_of, presort, full,
                                                          good if P1["mode"] == "fill" else None)

                        for extra, R in _selections(R1):
                            ok = True
                            for i in range(n):
                                fp = fpl(i)
                                c = cache[i]
                                try:
                                    if R["sel"] == "greedy" and not R["overlap"]:
                                        good_ = greedy_verdict(i, R)
                                    elif R["sel"] == "greedy":
                                        ent = _overlap_entries(presort, full, fpl, i, R["order"],
                                                               max(R["minm"], 1))
                                        chosen = _greedy_overlap_heap(ent, full(i), fp, R["minm"],
                                                                      (lambda p: good(i, p)) if uniform else None)
                                        good_ = chosen is not None and _paint(c[0], R, c[5], chosen) == c[1]
                                    elif R["sel"] == "open" and uniform:
                                        good_ = (all(good(i, p) for p in fp)
                                                 and _paint(c[0], R, c[5], fp) == c[1])
                                    elif R["sel"] == "exact" and R["mode"] == "fill":
                                        H, W = len(c[0]), len(c[0][0])
                                        evm = c[5]
                                        tg = [(r, q) for r in range(H) for q in range(W) if evm[r][q]]
                                        res = _select_exact(fp, tg, R["order"], cells_of,
                                                            byget=_exact_index(presort, full, fpl, i, R["order"]))
                                        good_ = (greedy_verdict(i, R) if res is None
                                                 else _paint(c[0], R, evm, res) == c[1])
                                    else:
                                        good_ = _paint(c[0], R, c[5], _choose(c[0], R, c[4], c[5], fp)) == c[1]
                                except _Dead:
                                    raise
                                except Exception:
                                    good_ = False
                                if not good_:
                                    ok = False
                                    break
                            if not ok:
                                continue
                            name = ("cover[mode=%s,piece=%s%s,ev=%s,sup=%s,sel=%s%s,minm=%d,clip=%d,order=%s,"
                                    "efree=%d]"
                                    % (R["mode"], R["cname"], ":" + sizes if len(P0["shapes"]) > 1 else "",
                                       (_rname(R["evidence"]) if R["evidence"] is not None else None),
                                       _supname(R["support"]),
                                       R["sel"], "+ov" if R["overlap"] and R["sel"] == "greedy" else "",
                                       R["minm"], R["clip"], R["order"], ef))
                            known = {tuple(map(tuple, c[0])): c[1] for c in cache}
                            yield name, 1 + base + extra + 0.5 * ef + 0.3 * vi, _make(dict(R, pattern=rpat), known)
                            found += 1
                            if found >= 3:
                                return
                            break
            except _Dead:
                continue


FAMILIES = [fam]
