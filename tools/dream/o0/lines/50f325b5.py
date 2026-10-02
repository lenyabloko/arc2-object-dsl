"""Line family for card 50f325b5 (test-blind; induced only from train pairs).

Reviewer line (Len): "find exemplar monochrome shape and recolor all matching foreground mono-chrome shapes into
the color of the exemplar".

Reading: the exemplar is the one small monochrome shape drawn in the exemplar colour (all cells of that colour,
any connectivity).  Every matching monochrome shape drawn in a foreground (source) colour -- the same shape,
moved and possibly turned (the smallest orientation group the training pairs need) -- is recoloured to the
exemplar colour.  A "matching shape" is, most literally, a whole single-colour connected component congruent to
the exemplar; where the source colour is noisy and touches itself, it is a placement of the shape whose cells
are all source colour (its enclosed holes not source colour).  Every match is painted; overlapping matches are
either all painted or taken first come, first served in reading order.
Exemplar colour = the colour every changed cell becomes (or the rarest colour of the grid); source colour = the
colour every changed cell comes from (or every colour other than the exemplar and the background).
"""
from collections import Counter

CARD = "50f325b5"
LINE = ("find exemplar monochrome shape and recolor all matching foreground mono-chrome shapes into the color "
        "of the exemplar")
READING = {
    "generator": "Take the exemplar (all cells of the exemplar colour) as a shape and repaint, in the exemplar "
                 "colour, every monochrome shape of a foreground colour that matches it: the same shape, translated "
                 "and turned within the smallest orientation group the training pairs need, found either as a whole "
                 "single-colour component or as a placement whose cells are all that colour.",
    "stop": "One pass over all matches of the shape in the input; each match is painted once (overlaps: all "
            "painted, or skipped once a cell is taken, in reading order) and no other cell changes; the exemplar "
            "itself stays.",
    "params": "match ∈ {whole component 4-conn, whole component 8-conn, placement inside colour} · "
              "orientations ∈ {translation, rotations C4, rotations+reflections D4} · "
              "holes ∈ {must not be source colour, free} (placement only) · overlap ∈ {paint all, reading-order "
              "greedy} (placement only) · exemplar colour ∈ {induced colour every change goes to, rarest colour "
              "of the grid} · source ∈ {induced colour every change comes from, every non-background non-exemplar "
              "colour (background = most frequent)}",
    "participants": "The exemplar = all cells of the exemplar colour in the input (one small shape, any "
                    "connectivity); candidate shapes = single-colour components or placements of the shape on cells "
                    "of a source colour; holes = bbox cells of the shape it encloses.",
    "preconditions": "Input and output have the same size; every changed cell turns into the exemplar colour (one "
                     "colour per grid, present in the input) from a non-exemplar colour; at least one cell changes; "
                     "the induced setting reproduces every training pair.",
}

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
ORIENTS = (("T", (0,)), ("C4", (0, 3, 5, 6)), ("D4", tuple(range(8))))  # D4 codes, see _xf
MATCHES = (("comp4", 4), ("comp8", 8), ("place", 0))
HOLES = (("holes-not-source", True), ("holes-free", False))
OVERLAP = (("paint-all", 0), ("greedy", 1))


def _xf(cells, t):
    """Apply D4 element t (bit2 = transpose, bit0 = flip rows, bit1 = flip cols); normalise to origin."""
    out = []
    for y, x in cells:
        if t & 4:
            y, x = x, y
        if t & 1:
            y = -y
        if t & 2:
            x = -x
        out.append((y, x))
    my = min(y for y, _ in out)
    mx = min(x for _, x in out)
    return tuple(sorted((y - my, x - mx) for y, x in out))


def _holes(shape):
    """Bbox cells not in the shape and not 4-connected to outside the bbox through non-shape cells."""
    s = set(shape)
    h = max(y for y, _ in shape) + 1
    w = max(x for _, x in shape) + 1
    st = [(y, x) for y in range(-1, h + 1) for x in range(-1, w + 1) if y in (-1, h) or x in (-1, w)]
    seen = set(st)
    while st:
        a, b = st.pop()
        for dy, dx in N4:
            p, q = a + dy, b + dx
            if -1 <= p <= h and -1 <= q <= w and (p, q) not in seen and (p, q) not in s:
                seen.add((p, q))
                st.append((p, q))
    return tuple((y, x) for y in range(h) for x in range(w) if (y, x) not in s and (y, x) not in seen)


def _shapes(tmpl, group):
    res, seen = [], set()
    for t in group:
        sh = _xf(tmpl, t)
        if sh not in seen:
            seen.add(sh)
            res.append((sh, _holes(sh)))
    return res


def _components(g, cols, conn):
    H, W = len(g), len(g[0])
    nb = N4 if conn == 4 else N8
    seen = [[False] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] not in cols:
                continue
            c = g[y][x]
            seen[y][x] = True
            st, cells = [(y, x)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c:
                        seen[p][q] = True
                        st.append((p, q))
            comps.append(cells)
    return comps


def _exemplar_colour(g, emode, A):
    if emode == 0:
        return A
    cnt = Counter(v for r in g for v in r)
    lo = min(cnt.values())
    rare = [c for c in cnt if cnt[c] == lo]
    return rare[0] if len(rare) == 1 else None


def _source_colours(g, smode, B, a):
    if smode == 0:
        return {B} - {a}
    cnt = Counter(v for r in g for v in r)
    bg = max(sorted(cnt), key=lambda c: cnt[c])
    return set(cnt) - {a, bg}


def _apply(g, spec):
    emode, A, smode, B, group, match, hole_rule, overlap = spec
    H, W = len(g), len(g[0])
    out = [r[:] for r in g]
    a = _exemplar_colour(g, emode, A)
    if a is None:
        return out
    tmpl = [(y, x) for y in range(H) for x in range(W) if g[y][x] == a]
    if not tmpl:
        return out
    src = _source_colours(g, smode, B, a)
    if not src:
        return out
    shapes = _shapes(tmpl, group)
    if match:  # whole single-colour components congruent to the exemplar
        forms = {sh for sh, _ in shapes}
        n = len(tmpl)
        for cells in _components(g, src, match):
            if len(cells) == n and _xf(cells, 0) in forms:
                for y, x in cells:
                    out[y][x] = a
        return out
    cands = []
    for sh, holes in shapes:
        h = max(y for y, _ in sh) + 1
        w = max(x for _, x in sh) + 1
        for oy in range(H - h + 1):
            for ox in range(W - w + 1):
                c = g[oy + sh[0][0]][ox + sh[0][1]]
                if c not in src or any(g[oy + y][ox + x] != c for y, x in sh):
                    continue
                if hole_rule and any(g[oy + y][ox + x] == c for y, x in holes):
                    continue
                cands.append(tuple(sorted((oy + y, ox + x) for y, x in sh)))
    cands.sort()
    taken = set()
    for cells in cands:
        if overlap and any(p in taken for p in cells):
            continue
        taken.update(cells)
        for y, x in cells:
            out[y][x] = a
    return out


def _induce(train):
    """Per pair: the single colour all changes go to (exemplar) and the set they come from.  Returns
    (fixed exemplar colour or None, fixed source colour or None) or None when preconditions fail."""
    to_all, from_all, changed = set(), [], False
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if not gi or not gi[0] or len(gi) != len(go) or any(len(r) != len(s) for r, s in zip(gi, go)):
            return None
        to_c, from_c = set(), set()
        for ra, rb in zip(gi, go):
            for u, v in zip(ra, rb):
                if u != v:
                    to_c.add(v)
                    from_c.add(u)
        if not to_c:
            continue
        changed = True
        if len(to_c) != 1:
            return None
        t = next(iter(to_c))
        if t in from_c or not any(t in r for r in gi):
            return None
        to_all.add(t)
        from_all.append(from_c)
    if not changed:
        return None
    A = next(iter(to_all)) if len(to_all) == 1 else None
    fr = set().union(*from_all)
    B = next(iter(fr)) if len(fr) == 1 else None
    return A, B


def fam(train):
    if not train:
        return
    ind = _induce(train)
    if ind is None:
        return
    A, B = ind
    emodes = [(0, "exemplar=induced")] if A is not None else []
    emodes.append((1, "exemplar=rarest"))
    smodes = [(0, "source=induced")] if B is not None else []
    smodes.append((1, "source=all-foreground"))
    found = []
    for ei, ename in emodes:
        for si, sname in smodes:
            for oi, (oname, group) in enumerate(ORIENTS):
                for mi, (mname, match) in enumerate(MATCHES):
                    hl = HOLES if not match else HOLES[:1]
                    ol = OVERLAP if not match else OVERLAP[:1]
                    for hi, (hname, hole_rule) in enumerate(hl):
                        for vi, (vname, overlap) in enumerate(ol):
                            spec = (ei, A, si, B, group, match, hole_rule, overlap)
                            if all(_apply(pr["input"], spec) == pr["output"] for pr in train):
                                cost = 10 + 2 * oi + mi + hi + vi + ei + si
                                parts = [mname, oname] + ([] if match else [hname, vname]) + [ename, sname]
                                name = "recolour-matches[%s]" % ",".join(parts)
                                found.append((cost, len(found), name, spec))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(spec)


def _make(spec):
    def fn(grid):
        return _apply(grid, spec)
    return fn


FAMILIES = [fam]
