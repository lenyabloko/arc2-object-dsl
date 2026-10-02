"""Line family for card e5062a87 (test-blind; induced only from train pairs).

Reviewer line (Len): "User color exemplar shape to fill as much background as possible"
(read as "Use the colour exemplar shape ...").

Reading: the exemplar is the one small shape drawn in the exemplar colour (all cells of that colour, any
connectivity).  Copies of it are stamped, in the exemplar colour, onto the background so that together they
cover as many background cells as possible: a copy is a translated (or turned -- the smallest orientation group
the training pairs need) placement whose cells are all background, copies never overlap each other, and the set
of copies is a maximum packing (most background cells covered).  Among equally large packings the one that
prefers earlier placements in reading order wins.  Optionally the copy must keep the exemplar's look: the
exemplar's enclosed holes (bbox cells it encloses) must not be background in the copy, so stamping never seals
a background cell inside a copy.
Exemplar colour = the colour that grows from input to output, background = the colour that shrinks (one
consistent pair of colours over the training pairs).
Fit note (train only): the best setting (translation, holes not background) reproduces pairs 1 and 2 but not
pair 0, where a second background run that fits the 1x4 exemplar and conflicts with no other placement is left
unfilled in the output; no maximum packing can leave it, so the line as written fits 2 of 3.  When no setting
fits every pair, only the best partial fits are yielded (name suffixed "~k/n", cost raised).
"""
from collections import Counter

CARD = "e5062a87"
LINE = "User color exemplar shape to fill as much background as possible"
READING = {
    "generator": "Stamp copies of the exemplar shape (all cells of the exemplar colour) in the exemplar colour onto "
                 "the background, choosing non-overlapping placements that lie wholly on background so that the "
                 "copies together cover as many background cells as possible (a maximum packing).",
    "stop": "When no further copy fits: the packing is maximum (no other set of non-overlapping placements covers "
            "more background); ties go to the packing that prefers earlier placements in reading order; nothing "
            "else changes and the exemplar stays.",
    "params": "orientations ∈ {translation, rotations C4, rotations+reflections D4} (smallest that fits) · "
              "holes ∈ {free, exemplar's enclosed holes must not be background} · tie ∈ {reading-order first} · "
              "exemplar / background colour induced as the colour that grows / shrinks.",
    "participants": "The exemplar = every cell of the exemplar colour in the input (one small shape, any "
                    "connectivity); the background = cells of the background colour, on which copies are placed; "
                    "holes = bbox cells of the shape it encloses.",
    "preconditions": "Input and output have the same size; every changed cell goes from the background colour to "
                     "the exemplar colour, the same pair in every training pair; the exemplar colour is present in "
                     "every input.",
}

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
ORIENTS = (("T", (0,)), ("C4", (0, 3, 5, 6)), ("D4", tuple(range(8))))  # D4 codes, see _xf
HOLES = (("holes-free", False), ("holes-nonbg", True))
COMP_CAP = 48         # exact search only on conflict components up to this many placements
NODE_BUDGET = 20000   # and within this node budget; otherwise greedy in reading order (deterministic)


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


def _placements(g, A, B, group, hole_rule):
    H, W = len(g), len(g[0])
    tmpl = [(y, x) for y in range(H) for x in range(W) if g[y][x] == A]
    if not tmpl:
        return []
    shapes, seen = [], set()
    for t in group:
        sh = _xf(tmpl, t)
        if sh not in seen:
            seen.add(sh)
            shapes.append((sh, _holes(sh)))
    cands = set()
    for sh, holes in shapes:
        h = max(y for y, _ in sh) + 1
        w = max(x for _, x in sh) + 1
        for oy in range(H - h + 1):
            for ox in range(W - w + 1):
                if any(g[oy + y][ox + x] != B for y, x in sh):
                    continue
                if hole_rule and any(g[oy + y][ox + x] == B for y, x in holes):
                    continue
                cands.add(tuple(sorted((oy + y, ox + x) for y, x in sh)))
    return sorted(cands)  # reading order of first cell, then the rest


def _max_packing(cands):
    """Indices of a maximum set of pairwise disjoint placements; ties -> prefer earlier placements."""
    n = len(cands)
    owner = {}
    for i, c in enumerate(cands):
        for cell in c:
            owner.setdefault(cell, []).append(i)
    nb = [set() for _ in range(n)]
    for lst in owner.values():
        for i in lst:
            nb[i].update(lst)
    for i in range(n):
        nb[i].discard(i)
    # conflict components are independent sub-problems
    comp_of = [-1] * n
    comps = []
    for i in range(n):
        if comp_of[i] >= 0:
            continue
        comp_of[i] = len(comps)
        st, cur = [i], [i]
        while st:
            u = st.pop()
            for v in nb[u]:
                if comp_of[v] < 0:
                    comp_of[v] = len(comps)
                    st.append(v)
                    cur.append(v)
        comps.append(sorted(cur))
    chosen = []
    for comp in comps:
        chosen.extend(_mis(comp, nb, cands))
    return sorted(chosen)


def _greedy(comp, nb):
    taken, blocked = [], set()
    for i in comp:
        if i not in blocked:
            taken.append(i)
            blocked.update(nb[i])
            blocked.add(i)
    return taken


def _mis(comp, nb, cands):
    if len(comp) == 1:
        return list(comp)
    best = _greedy(comp, nb)
    if len(comp) > COMP_CAP:
        return best
    best_n = [len(best)]
    best_set = [list(best)]
    found_exact = [False]
    budget = [NODE_BUDGET]
    m = len(comp)
    size = len(cands[comp[0]])

    def rec(k, chosen, blocked):
        budget[0] -= 1
        if budget[0] < 0:
            return
        # upper bound: chosen + min(#still-free placements, free cells they cover // shape size)
        free, cells = 0, set()
        for j in range(k, m):
            if comp[j] not in blocked:
                free += 1
                cells.update(cands[comp[j]])
        ub = len(chosen) + min(free, len(cells) // size)
        if ub < best_n[0] or (ub == best_n[0] and found_exact[0]):
            return
        if k == m:
            if len(chosen) > best_n[0] or not found_exact[0]:
                best_n[0] = len(chosen)
                best_set[0] = list(chosen)
                found_exact[0] = True
            return
        i = comp[k]
        if i in blocked:
            rec(k + 1, chosen, blocked)
            return
        chosen.append(i)
        rec(k + 1, chosen, blocked | nb[i])
        chosen.pop()
        rec(k + 1, chosen, blocked)

    rec(0, [], frozenset())
    return best_set[0]


def _apply(g, A, B, group, hole_rule):
    out = [r[:] for r in g]
    cands = _placements(g, A, B, group, hole_rule)
    for i in _max_packing(cands):
        for y, x in cands[i]:
            out[y][x] = A
    return out


def _colours(train):
    pair = None
    changed = False
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if not gi or not gi[0] or len(gi) != len(go) or any(len(a) != len(b) for a, b in zip(gi, go)):
            return None
        ci = Counter(v for r in gi for v in r)
        co = Counter(v for r in go for v in r)
        cols = sorted(set(ci) | set(co))
        A = max(cols, key=lambda c: co[c] - ci[c])
        B = min(cols, key=lambda c: co[c] - ci[c])
        if A == B or ci[A] == 0:
            return None
        for ra, rb in zip(gi, go):
            for a, b in zip(ra, rb):
                if a != b:
                    changed = True
                    if (a, b) != (B, A):
                        return None
        if pair is None:
            pair = (A, B)
        elif pair != (A, B):
            return None
    return pair if changed else None


def _make(A, B, group, hole_rule):
    def fn(grid):
        return _apply(grid, A, B, group, hole_rule)
    return fn


def fam(train):
    if not train:
        return
    ab = _colours(train)
    if ab is None:
        return
    A, B = ab
    n = len(train)
    scored = []
    for oi, (oname, group) in enumerate(ORIENTS):
        for hi, (hname, hole_rule) in enumerate(HOLES):
            fit = sum(1 for pr in train if _apply(pr["input"], A, B, group, hole_rule) == pr["output"])
            cost = 10 + 2 * oi + hi
            scored.append((fit, cost, oname, hname, group, hole_rule))
    best_fit = max(s[0] for s in scored)
    if best_fit == 0:
        return
    # programs reproducing every pair first; if none does, only the best partial fits (the line's best reading)
    keep = [s for s in scored if s[0] == best_fit]
    keep.sort(key=lambda s: s[1])
    for fit, cost, oname, hname, group, hole_rule in keep:
        name = "max-packing[%s,%s,reading-tie]" % (oname, hname)
        if fit < n:
            name += "~%d/%d" % (fit, n)
            cost += 10 * (n - fit)
        yield name, cost, _make(A, B, group, hole_rule)


FAMILIES = [fam]
