"""Line family for card d6542281 (test-blind; induced only from train pairs).

Reading: the input holds a few multi-coloured connected shapes (exemplars) and scattered
single-colour fragments.  Each fragment is a piece of one exemplar: its pixels coincide, colour for
colour, with the pixels of one colour of an exemplar under some translation (optionally also a
rotation/reflection).  Completing the fragment means stamping the whole exemplar at that placement.
Placements are chosen greedily by how many fragment pixels they explain, and must agree with the
grid everywhere they land.
"""
from collections import Counter

CARD = "d6542281"
LINE = "complete mono-colored shapes using matching multi-colored exemplars"
READING = {
    "generator": "Every multi-coloured connected shape is an exemplar; each group of single-colour fragment "
                 "pixels that matches, colour for colour, the pixels of some colour(s) of an exemplar under a "
                 "translation (optionally a rotation/reflection) is completed by stamping the whole exemplar there.",
    "stop": "One stamp per placement; placements are taken greedily (most uncovered fragment pixels explained "
            "first) until every fragment pixel is explained or no consistent placement explains one more; a stamp "
            "never overwrites a different colour or an exemplar, and must touch only whole fragments.",
    "params": "connectivity ∈ {8, 4} · orientation ∈ {translation only, any of the 8 rotations/reflections} · "
              "border ∈ {stamp must lie inside the grid, clip at the border}",
    "participants": "Background = most frequent colour; exemplars = connected components (non-background) with "
                    "two or more colours; fragments = connected components with a single colour; a fragment pixel "
                    "is matched to an exemplar pixel of the same colour, which fixes the placement.",
    "preconditions": "Input and output have the same size, the output only adds paint, there is at least one "
                     "multi-coloured exemplar and at least one single-colour fragment whose colour occurs in an "
                     "exemplar, and the induced setting reproduces every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
D8 = D4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
# the 8 rotations/reflections as (y, x) -> new (y, x); identity first
DIH = (
    lambda y, x: (y, x), lambda y, x: (x, -y), lambda y, x: (-y, -x), lambda y, x: (-x, y),
    lambda y, x: (y, -x), lambda y, x: (-y, x), lambda y, x: (x, y), lambda y, x: (-x, -y),
)


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _components(g, bg, conn):
    """Connected components of non-background cells (any colours mixed)."""
    H, W = len(g), len(g[0])
    nb = D4 if conn == 4 else D8
    seen = [[False] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            seen[y][x] = True
            st, pix = [(y, x)], []
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] != bg:
                        seen[p][q] = True
                        st.append((p, q))
            comps.append(sorted(pix))
    comps.sort()
    return comps


def _parse(g, conn):
    bg = _bg(g)
    exemplars, fragments = [], []
    for pix in _components(g, bg, conn):
        cols = {g[a][b] for a, b in pix}
        if len(cols) >= 2:
            exemplars.append({(a, b): g[a][b] for a, b in pix})
        else:
            fragments.append(pix)
    return bg, exemplars, fragments


def _orient(ex, k):
    """Exemplar cells under dihedral transform k, normalised to min corner (0, 0)."""
    f = DIH[k]
    cells = {f(a, b): c for (a, b), c in ex.items()}
    y0 = min(p[0] for p in cells); x0 = min(p[1] for p in cells)
    return tuple(sorted(((a - y0, b - x0), c) for (a, b), c in cells.items()))


def _complete(g, conn, orient, border):
    H, W = len(g), len(g[0])
    bg, exemplars, fragments = _parse(g, conn)
    out = [r[:] for r in g]
    if not exemplars or not fragments:
        return out
    ex_cells = set()
    for ex in exemplars:
        ex_cells |= set(ex)
    frag_of = {}
    for i, pix in enumerate(fragments):
        for p in pix:
            frag_of[p] = i
    ks = range(len(DIH)) if orient == "d8" else (0,)
    shapes = []                                   # deduplicated oriented exemplars, in order
    for ex in exemplars:
        for k in ks:
            s = _orient(ex, k)
            if s not in shapes:
                shapes.append(s)
    by_col = []
    for s in shapes:
        d = {}
        for p, c in s:
            d.setdefault(c, []).append(p)
        by_col.append(d)
    # candidate placements: a fragment pixel sits on an exemplar pixel of the same colour
    cands = []
    seen = set()
    for (a, b) in sorted(frag_of):
        c = g[a][b]
        for si, d in enumerate(by_col):
            for (y, x) in d.get(c, ()):
                key = (si, a - y, b - x)
                if key not in seen:
                    seen.add(key)
                    cands.append(key)
    remaining = set(frag_of)
    while remaining:
        best = None
        for si, ty, tx in cands:
            covered, ok, touched = set(), True, set()
            for (y, x), c in shapes[si]:
                p, q = y + ty, x + tx
                if not (0 <= p < H and 0 <= q < W):
                    if border == "inside":
                        ok = False
                        break
                    continue
                if (p, q) in ex_cells:
                    ok = False
                    break
                v = out[p][q]
                if v != bg and v != c:
                    ok = False
                    break
                if (p, q) in frag_of:
                    covered.add((p, q))
                    touched.add(frag_of[(p, q)])
            if not ok:
                continue
            # a stamp must contain every fragment it touches entirely
            if any(not all(p in covered for p in fragments[i]) for i in touched):
                continue
            gain = len(covered & remaining)
            if gain == 0:
                continue
            key = (-gain, si, ty, tx)
            if best is None or key < best[0]:
                best = (key, si, ty, tx, covered)
        if best is None:
            break
        _, si, ty, tx, covered = best
        for (y, x), c in shapes[si]:
            p, q = y + ty, x + tx
            if 0 <= p < H and 0 <= q < W:
                out[p][q] = c
        remaining -= covered
    return out


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        bg = _bg(gi)
        if not any(a == bg and b != bg for ri, ro in zip(gi, go) for a, b in zip(ri, ro)):
            return                                # completion must add paint on background
    parsed = {cn: [_parse(p["input"], cn) for p in train] for cn in (8, 4)}
    conns = [8] if parsed[8] == parsed[4] else [8, 4]
    usable = False
    for cn in conns:
        for (bg, exs, frs), pr in zip(parsed[cn], train):
            excols = {c for ex in exs for c in ex.values()}
            if any(pr["input"][pix[0][0]][pix[0][1]] in excols for pix in frs):
                usable = True
    if not usable:
        return
    n = len(train)
    found = []
    for cn in conns:
        for orient, oc in (("id", 0), ("d8", 2)):
            for border, bc in (("inside", 0), ("clip", 1)):
                k = sum(_complete(pr["input"], cn, orient, border) == pr["output"] for pr in train)
                cost = 10 + (cn == 4) + oc + bc
                name = "complete_from_exemplar[c%d,%s,%s]" % (cn, orient, border)
                found.append((k, cost, len(found), name, (cn, orient, border)))
    full = [f for f in found if f[0] == n]
    if full:
        chosen = full
    else:
        # no setting reproduces every pair: offer the settings that fit a strict majority, marked partial
        best = max(f[0] for f in found)
        if 2 * best <= n:
            return
        chosen = [(k, cost + 10 * (n - k), i, "%s(partial %d/%d)" % (name, k, n), spec)
                  for k, cost, i, name, spec in found if k == best]
    chosen.sort(key=lambda t: (t[1], t[2]))
    for _, cost, _, name, spec in chosen:
        yield name, cost, _make(*spec)


def _make(conn, orient, border):
    def fn(grid):
        return _complete(grid, conn, orient, border)
    return fn


FAMILIES = [fam]
