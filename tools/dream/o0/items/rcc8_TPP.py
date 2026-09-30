"""RCC-8 TPP (tangential proper part) on filled cell regions.
x TPP y iff region(x) is a proper subset of region(y) and some cell of region(x) is 4-adjacent to a cell outside
region(y) or lies on the grid border.
Randell, Cui & Cohn (1992), "A spatial logic based on regions and connection" (KR'92): region connection calculus,
base relations DC, EC, PO, TPP, NTPP, TPPi, NTPPi, EQ (jointly exhaustive, pairwise disjoint); PP = TPP | NTPP and
PPi = TPPi | NTPPi are the usual proper-part unions.

Grounding (shared by rcc8_DC, rcc8_PO, rcc8_EQ, rcc8_TPP, rcc8_NTPP, rcc8_TPPi, rcc8_NTPPi, rcc8_PP, rcc8_PPi):
  region(x)  = cells(x) plus the cells x encloses: the cells outside x (of any colour) that are not 4-connected to the
               grid border through cells outside x. So a background cell, or an object, lying in the hole of a hollow
               object is part of that object's region (the flood never enters x, so walls count as closed).
  C(a, b)    = region(a) and region(b) share a cell or have a 4-adjacent pair of cells (connection).
  boundary   = the cells of region(y) that are 4-adjacent to a cell outside region(y) or lie on the grid border.
The first argument ranges over all individuals (objects and background cells), the second over objects only (README);
x != y. A hole cell is never 4-adjacent to the exterior, so a background cell inside a hollow object is always NTPP
(never TPP) of it; TPP / TPPi / EQ need lattice objects that share cells. rcc8_EC keeps its own grounding on raw cells
(so EC can co-occur with NTPP / NTPPi / PO: e.g. a hole cell touching its frame); the relations here are pairwise
disjoint.
Subsumption (every grid): rcc8_TPP ⊑ rcc8_PP."""


def _cells(m, Wp):
    """cells of a padded-grid bitmask"""
    s = bin(m)[:1:-1]; k = s.find("1")
    while k >= 0:
        yield (k // Wp - 1, k % Wp - 1)
        k = s.find("1", k + 1)


def _region(pix, H, W, Wp, full):
    """(region(pix) as a cell set, region(pix) as a bitmask). Bitmask layout: the grid padded by one empty ring, bit
    (y + 1) * Wp + x + 1 for cell (y, x), Wp = W + 2. Fewer than 4 cells, or a bbox thinner than 3, cannot enclose a
    cell. Enclosed cells: bitset flood of the exterior through cells outside pix; every cell outside bbox(pix) reaches
    the border by a straight line, so it seeds the exterior and the flood only has to cross the bbox."""
    m = 0
    for (y, x) in pix: m |= 1 << ((y + 1) * Wp + x + 1)
    if len(pix) < 4: return pix, m
    ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    if y1 - y0 < 2 or x1 - x0 < 2: return pix, m
    row = ((1 << (x1 - x0 + 1)) - 1) << (x0 + 1)
    box = 0
    for y in range(y0, y1 + 1): box |= row << ((y + 1) * Wp)
    free = full & ~m
    e = full & ~box
    while True:
        e2 = (e | (e << 1) | (e >> 1) | (e << Wp) | (e >> Wp)) & free
        if e2 == e: break
        e = e2
    h = box & ~e & ~m
    if not h: return pix, m
    return set(pix).union(_cells(h, Wp)), m | h


def rcc8(grid, inds, want):
    """{i: set(j)} for relation `want` in DC PO EQ TPP NTPP TPPi NTPPi PP PPi; j ranges over objects, i != j.
    Regions (sets and bitmasks) and the cell -> object map are built once per call. Pairs with a multi-cell first
    argument are decided on bitmasks; single-cell individuals (background cells) through the cell -> object map."""
    H, W = len(grid), len(grid[0]); Wp = W + 2; full = (1 << ((H + 2) * Wp)) - 1
    objs = [j for j, x in enumerate(inds) if x.get("kind") == "object" and x["pix"]]
    out = {}
    if not objs: return out
    R, M = {}, {}
    for j in objs: R[j], M[j] = _region(inds[j]["pix"], H, W, Wp, full)
    one, big = {}, []  # single-cell non-object individuals by cell; every other non-empty individual
    for i, x in enumerate(inds):
        if i in M: big.append(i)
        elif len(x["pix"]) == 1: one.setdefault(next(iter(x["pix"])), []).append(i)
        elif x["pix"]:
            R[i], M[i] = _region(x["pix"], H, W, Wp, full); big.append(i)
    Bm = {}

    def bnd(j):  # cells of region(j) with a 4-neighbour outside region(j); padding bits are 0, so border cells count
        b = Bm.get(j)
        if b is None:
            m = M[j]; b = Bm[j] = m & ~(m & (m << 1) & (m >> 1) & (m << Wp) & (m >> Wp))
        return b

    if want == "DC":
        D = {j: M[j] | (M[j] << 1) | (M[j] >> 1) | (M[j] << Wp) | (M[j] >> Wp) for j in objs}
        for i in big:
            mi = M[i]
            dc = {j for j in objs if j != i and not (mi & D[j])}
            if dc: out[i] = dc
        if one:
            own = {}  # cell -> objects whose region contains it
            for j in objs:
                for p in R[j]:
                    s = own.get(p)
                    if s is None: own[p] = [j]
                    else: s.append(j)
            allobj = set(objs)
            for (y, x), its in one.items():
                t = set()
                for q in ((y, x), (y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    s = own.get(q)
                    if s: t.update(s)
                for i in its:
                    dc = allobj - t; dc.discard(i)
                    if dc: out[i] = dc
        return out
    for i in big:
        mi = M[i]; hit = set()
        for j in objs:
            if j == i: continue
            mj = M[j]; c = mi & mj
            if not c: continue
            if c == mi:
                if c == mj: lab = "EQ"
                elif want == "PP": lab = "PP"
                else: lab = "TPP" if mi & bnd(j) else "NTPP"
            elif c == mj: lab = "PPi" if want == "PPi" else ("TPPi" if mj & bnd(i) else "NTPPi")
            else: lab = "PO"
            if lab == want: hit.add(j)
        if hit: out[i] = hit
    if one and want in ("EQ", "TPP", "NTPP", "PP"):  # a single cell can only be EQ to, or a proper part of, y
        for j in objs:
            rj = R[j]; n = len(rj); bs = None
            for p in rj:
                its = one.get(p)
                if not its: continue
                if n == 1: lab = "EQ"
                elif want == "PP": lab = "PP"
                else:
                    if bs is None: bs = set(_cells(bnd(j), Wp))
                    lab = "TPP" if p in bs else "NTPP"
                if lab == want:
                    for i in its:
                        if i != j: out.setdefault(i, set()).add(j)
    return out


def rcc8_TPP(grid, inds, bg):
    return rcc8(grid, inds, "TPP")


ITEM = {"name": "rcc8_TPP", "layer": 1, "iri": "qsr:TPP", "kind": "role", "params": {}, "subsumes": ["rcc8_PP"],
        "definition": "x is a tangential proper part of y: region(x) is a proper subset of region(y) and some cell of "
                      "region(x) is 4-adjacent to a cell outside region(y) or on the grid border. Grounding: region(x) "
                      "= cells of x plus the cells x encloses (cells outside x not 4-connected to the grid border "
                      "through cells outside x); the second argument is an object; x != y. Randell, Cui & Cohn 1992 "
                      "(RCC-8).",
        "fn": rcc8_TPP}
