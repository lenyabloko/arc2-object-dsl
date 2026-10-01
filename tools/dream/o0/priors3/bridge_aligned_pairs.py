"""Prior family: bridge_aligned_pairs (v3, test-blind, induced from training pairs only).

Concept: two items that share a colour (or, optionally, any two facing items) and lie on a common row,
column or diagonal are joined: every item between them is repainted by a learned map of the crossed colour
(their colour | the colour new in the outputs | keep | literal), and items covered by several bridges get a
learned combined colour.

One generator, written once:
  1. ABSTRACT the grid into item layers:
       pixel - every pixel is an item;
       cell  - the grid is cut by full separator lines; a lattice cell is one item whose value is its single
               marker colour (cell background if empty, mixed if several); painting fills the whole cell;
       tile  - (new) the same lattice, but a cell is one item whose pixels are its SHAPE; tiles with identical
               shapes form a class whose value is the rarest tile colour in it (a shape identical to a
               marker-coloured shape takes the marker colour); that class colour is materialised first, and
               painting recolours the shape pixels only;
       phase - equal lattice tiles; for each in-tile offset the tiles' pixels at that offset form one layer.
  2. PARTICIPANTS: items whose colour passes `sel` (not background | outside the k most frequent colours |
     colour occurring exactly twice) in the layer.
  3. PAIRS along every line of the directions `dirs`:
       span  - consecutive items of the same participant colour (whatever lies between);
       sight - consecutive non-background items with clear line of sight, both participants and of the same
               colour (`any`: any two participants, e.g. facing rectangles); with `walls` a diagonal line is
               also blocked where it slips between two diagonally touching non-background cells.
     Covered items: strictly between (plus the two endpoints when `incl`); with `margin` the bridge is eroded
     perpendicular to its direction.
  4. PAINT: crossed colour x -> {P (pair colour), N (colour new in the training outputs), K (keep), literal}.
     The map is keyed first by ROLE (x is the layer background `bg` | x is the layer's rank-2 colour `r2`), a
     role entry kept only when one value explains every singly covered item whose colour plays that role;
     literal colour keys are the fallback, unseen colours keep.  Overlaps: learned combined colour, else first /
     last bridge in direction order.  Single pass, no cascade.

BINDINGS (G68) -- every value induced for the fitted members, with the role that explains it
(value seen in training  <-  role; "literal" = no role explains it across all pairs, kept as a fitted constant).
  06df4c85  level=pixel sel=nonbg dirs=hv pair=span
            separator colour 1/8/4 (differs per pair) -> keep      <- layer background (grid mode)       [bg>K]
            crossed 0 -> pair colour                               <- 0 = rank-2 colour (empty cell colour) [r2>P]
            paint colour 2/3/8/9                                   <- endpoint (marker) colour            [P]
            other participant colours crossed -> keep              <- default (unseen colour keeps)
  7666fa5d  level=pixel sel=nonbg dirs=perp pair=sight walls=1
            direction                                              <- perpendicular to the diagonal runs of the objects
            crossed 8 -> 2                                         <- 8 = layer background; 2 = colour new in outputs [bg>N]
  a096bf4d  level=phase sel=nonbg dirs=hv pair=span
            crossed 3 / 8 / 4 (one per pair) -> pair colour        <- the phase layer's background (tile fill)  [bg>P]
            paint colour 1,6,8 / 2,4 / 7,3                          <- endpoint colour                     [P]
  b7f8a4d8  level=pixel sel=rank3 dirs=hv pair=span
            participants 8,4 / 3,1 / 3                             <- colours outside the 3 most frequent
            crossed 0 -> pair colour                               <- literal: 0 is rank-2 in pair 1 but background in
                                                                      pairs 2,3 (no single role) ; others keep (default)
  bcb3040b  level=pixel sel=twice dirs=all pair=span
            endpoints 2                                            <- the colour occurring exactly twice
            crossed 0 -> 2                                         <- background -> pair colour            [bg>P]
            crossed 1 -> 3                                         <- 1 = rank-2 colour; 3 = colour new in outputs [r2>N]
  cbded52d  level=phase sel=nonbg dirs=hv pair=span
            crossed 1 -> pair colour                               <- phase layer background               [bg>P]
  d6ad076f  level=pixel sel=nonbg dirs=hv pair=sight-any margin=1
            crossed 0 -> 8                                         <- background -> colour new in outputs  [bg>N]
            bridge width                                           <- shared face of the two rectangles minus one cell
  e760a62e  level=cell sel=nonbg dirs=hv pair=span incl=1
            crossed 0 (empty cell) -> pair colour                  <- cell background                      [bg>P]
            overlap {2,3} -> 6                                     <- colour new in the outputs            [N]
  d94c3b52  (new in v3) level=tile sel=nonbg dirs=hv pair=span
            participant tiles                                      <- shape identical to the marker-coloured shape
            their colour 8                                         <- marker colour (rarest tile colour of the class)
            crossed tiles 1 -> 7                                   <- layer background -> colour new in outputs [bg>N]
Specialisation menu derived from the table (no invented values):
  crossed-colour key in {role bg, role r2, literal colour};  paint value in {P (marker colour), N (new output
  colour), K, literal};  item level gains `tile` (lattice items identified by shape, coloured by their marker)
  -- the cell level's role "item colour <- marker colour" applied to shape classes.
Not widened (their extra step is unique to them, no role-bound parameter or shared step covers it):
  98c475bf (erase the old line and redraw a per-colour decoration library), b9630600 (minimum-spanning-tree
  corridors with walls, opening rectangle walls), f35d900a (3x3 halo of the partner colour around each endpoint
  plus dashes by parity of the distance to the nearest endpoint).
"""

CARD = "prior3_bridge_aligned_pairs"
CONCEPT = "bridge_aligned_pairs"
MEMBERS = ["06df4c85", "7666fa5d", "98c475bf", "a096bf4d", "b7f8a4d8", "b9630600", "bcb3040b",
           "cbded52d", "d6ad076f", "d94c3b52", "e760a62e", "f35d900a"]
READING = {
    "generator": ("Abstract the grid into items (pixels, separator-lattice cells, lattice shapes coloured by their "
                  "marker-coloured twin, or same-offset pixels of equal tiles); along each chosen row/column/diagonal pair consecutive participant items of one colour "
                  "(any span, or clear line of sight, optionally any two facing items) and repaint the items "
                  "between them by a learned map of the crossed colour, combining overlaps by a learned rule."),
    "stop": "single pass: every pair present in the input is bridged once; nothing drawn is re-used as an endpoint.",
    "params": ("level in {pixel, cell, tile, phase} . sel in {nonbg, rank2, rank3, twice} . dirs in {hv, h, v, all, "
               "x, x1, x2, perp} . pairing in {span, sight, sight-any} . incl in {0,1} . margin in {0,1} . walls in "
               "{0,1} . paint map key in {role bg, role r2, literal colour} -> {P, N, K, colour} (role entry first, "
               "then literal, unseen colour keeps) . overlap = learned set->colour, fallback in {first, last}"),
    "participants": ("items of a layer whose colour is not the layer background (mode), or lies outside the 2/3 "
                     "most frequent colours, or occurs exactly twice; mixed lattice cells never participate."),
    "preconditions": ("every training output has its input's shape; at least one pair changes; cell/phase "
                      "/tile levels need full separator rows and columns of one colour (phase: equal tile sizes); every "
                      "changed item is covered by some bridge; the learned paint map is consistent."),
}

DIRSETS = {
    "hv": ((0, 1), (1, 0)),
    "h": ((0, 1),),
    "v": ((1, 0),),
    "all": ((0, 1), (1, 0), (1, 1), (1, -1)),
    "x": ((1, 1), (1, -1)),
    "x1": ((1, 1),),
    "x2": ((1, -1),),
    "perp": None,   # per grid: perpendicular to the direction along which non-background items form fewest runs
}
DIRCOST = {"hv": 0.0, "h": 0.4, "v": 0.4, "all": 0.5, "x": 0.8, "x1": 1.2, "x2": 1.2, "perp": 1.1}
SELS = ("nonbg", "twice", "rank2", "rank3")
SELCOST = {"nonbg": 0.0, "twice": 0.6, "rank2": 0.8, "rank3": 1.0}
LEVELCOST = {"pixel": 0.0, "cell": 0.5, "tile": 0.8, "phase": 1.0}
MIXED = -1
KEEP = None


# ----------------------------------------------------------------------------------------------- abstraction
def _mode(vals):
    cnt = {}
    for v in vals:
        cnt[v] = cnt.get(v, 0) + 1
    if not cnt:
        return None
    return min(cnt, key=lambda k: (-cnt[k], k))


def _bands(n, seps):
    out, cur = [], []
    for i in range(n):
        if i in seps:
            if cur:
                out.append(cur)
                cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _lattice(g):
    H, W = len(g), len(g[0])
    best = None
    for s in sorted({x for r in g for x in r}):
        rows = [i for i in range(H) if all(x == s for x in g[i])]
        if not rows:
            continue
        cols = [j for j in range(W) if all(g[i][j] == s for i in range(H))]
        if not cols:
            continue
        n = len(rows) + len(cols)
        if best is None or n > best[0]:
            best = (n, s, set(rows), set(cols))
    if best is None:
        return None
    _, s, rows, cols = best
    rb, cb = _bands(H, rows), _bands(W, cols)
    if not rb or not cb or len(rb) * len(cb) < 2:
        return None
    return s, rb, cb


def _layers(g, level):
    """list of (V, pix): V item values (R x C), pix[i][j] = list of pixel positions of the item."""
    if level == "pixel":
        H, W = len(g), len(g[0])
        return [([list(r) for r in g], [[((i, j),) for j in range(W)] for i in range(H)])]
    lat = _lattice(g)
    if lat is None:
        return None
    s, rb, cb = lat
    if level == "tile":
        return [_tiles(g, s, rb, cb)]
    if level == "cell":
        cbg = _mode([g[i][j] for R in rb for i in R for C in cb for j in C])
        V, P = [], []
        for R in rb:
            vr, pr = [], []
            for C in cb:
                pos = tuple((i, j) for i in R for j in C)
                cs = {g[i][j] for i, j in pos} - {cbg}
                vr.append(cbg if not cs else (cs.pop() if len(cs) == 1 else MIXED))
                pr.append(pos)
            V.append(vr)
            P.append(pr)
        return [(V, P)]
    # phase
    if len({len(R) for R in rb}) != 1 or len({len(C) for C in cb}) != 1:
        return None
    out = []
    for a in range(len(rb[0])):
        for b in range(len(cb[0])):
            V = [[g[R[a]][C[b]] for C in cb] for R in rb]
            P = [[((R[a], C[b]),) for C in cb] for R in rb]
            out.append((V, P))
    return out


def _tiles(g, s, rb, cb):
    """tile level: each lattice cell is an item whose pixels are its shape (non-separator pixels); its value is the
    colour of its shape class -- every tile with the same shape takes the globally rarest tile colour present in
    that class (shapes identical to a marker-coloured shape take the marker colour; a class of one colour keeps
    it); an empty tile takes the separator colour, a multicoloured one is mixed."""
    keys, cols = [], []
    for R in rb:
        kr, cr = [], []
        for C in cb:
            pos = tuple((i, j) for i in R for j in C if g[i][j] != s)
            cs = {g[i][j] for i, j in pos}
            kr.append((len(R), len(C), frozenset((i - R[0], j - C[0]) for i, j in pos), pos))
            cr.append(s if not cs else (cs.pop() if len(cs) == 1 else MIXED))
        keys.append(kr)
        cols.append(cr)
    tot, cls = {}, {}
    for kr, cr in zip(keys, cols):
        for k, c in zip(kr, cr):
            if c in (s, MIXED):
                continue
            tot[c] = tot.get(c, 0) + 1
            cls.setdefault(k[:3], set()).add(c)
    V, P = [], []
    for kr, cr in zip(keys, cols):
        V.append([c if c in (s, MIXED) else min(cls[k[:3]], key=lambda x: (tot[x], x)) for k, c in zip(kr, cr)])
        P.append([k[3] for k in kr])
    return V, P


def _base(g, level, L):
    """the grid the bridges are painted on: at tile level the shape-class colour is materialised first (every tile
    whose shape matches a marker-coloured shape is recoloured to the marker colour); other levels: the input."""
    out = [list(r) for r in g]
    if level == "tile" and L:
        V, pix = L[0]
        for i in range(len(V)):
            for j in range(len(V[0])):
                if V[i][j] != MIXED:
                    for a, b in pix[i][j]:
                        out[a][b] = V[i][j]
    return out


def _participants(V, sel):
    cnt = {}
    for r in V:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    order = sorted(cnt, key=lambda k: (-cnt[k], k))
    bg = order[0]
    r2 = order[1] if len(order) > 1 else None
    if sel == "nonbg":
        S = set(order[1:])
    elif sel == "twice":
        S = {c for c in cnt if cnt[c] == 2 and c != bg}
    else:
        k = 2 if sel == "rank2" else 3
        S = set(order[k:])
    S.discard(MIXED)
    return bg, S, r2


# ----------------------------------------------------------------------------------------------- bridges
def _lines(R, C, d):
    dr, dc = d
    for i in range(R):
        for j in range(C):
            pi, pj = i - dr, j - dc
            if 0 <= pi < R and 0 <= pj < C:
                continue
            line = []
            a, b = i, j
            while 0 <= a < R and 0 <= b < C:
                line.append((a, b))
                a += dr
                b += dc
            if len(line) >= 3:
                yield line




def _dirs(dname, V, bg):
    ds = DIRSETS[dname]
    if ds is not None:
        return ds
    R, C = len(V), len(V[0])
    best = None
    for d in ((0, 1), (1, 0), (1, 1), (1, -1)):
        dr, dc = d
        n = 0
        for i in range(R):
            for j in range(C):
                if V[i][j] != bg:
                    pi, pj = i - dr, j - dc
                    if not (0 <= pi < R and 0 <= pj < C) or V[pi][pj] == bg:
                        n += 1
        if best is None or n < best[0]:
            best = (n, d)
    d = best[1]
    p = (d[1], -d[0])
    if p[0] < 0 or (p[0] == 0 and p[1] < 0):
        p = (-p[0], -p[1])
    return (p,)


def _cover_dir(V, bg, S, d, pairing, walls):
    """{item: [(P, endpoint)]} for one direction; P = pair colour, or None for an `any` pair of two colours.
    Positions along a line are half-steps: cell k -> 2k, the crossing between cells k-1 and k -> 2k-1."""
    R, C = len(V), len(V[0])
    cov = {}
    diag = d[0] != 0 and d[1] != 0
    for line in _lines(R, C, d):
        if pairing == "span":
            last = {}
            for k, (a, b) in enumerate(line):
                x = V[a][b]
                if x in S:
                    if x in last and k - last[x] > 1:
                        for t in range(last[x] + 1, k):
                            cov.setdefault(line[t], []).append((x, False))
                        cov.setdefault(line[last[x]], []).append((x, True))
                        cov.setdefault(line[k], []).append((x, True))
                    last[x] = k
            continue
        ev = []  # blockers along the line: (half position, value)
        for k, (a, b) in enumerate(line):
            if k and walls and diag:
                p, q = line[k - 1]
                u, w = V[a][q], V[p][b]
                if u != bg and w != bg:
                    ev.append((2 * k - 1, u if u == w else MIXED))
            x = V[a][b]
            if x != bg:
                ev.append((2 * k, x))
        for t in range(1, len(ev)):
            h1, x1 = ev[t - 1]
            h2, x2 = ev[t]
            lo, hi = h1 // 2 + 1, (h2 + 1) // 2
            if hi <= lo or x1 not in S or x2 not in S:
                continue
            if x1 == x2:
                P = x1
            elif pairing == "sight-any":
                P = None
            else:
                continue
            for k in range(lo, hi):
                cov.setdefault(line[k], []).append((P, False))
            if h1 % 2 == 0:
                cov.setdefault(line[h1 // 2], []).append((P, True))
            if h2 % 2 == 0:
                cov.setdefault(line[h2 // 2], []).append((P, True))
    return cov


def _merge(covs, dirs, incl, margin):
    """item -> [P, ...] in direction order, keeping endpoints only when `incl`, eroding by `margin`."""
    out = {}
    for d, cov in zip(dirs, covs):
        pr, pc = d[1], -d[0]
        mid = None
        if margin:
            mid = {q for q, l in cov.items() if any(not e for _, e in l)}
        for q, l in cov.items():
            for P, e in l:
                if e:
                    if not incl:
                        continue
                elif margin:
                    i, j = q
                    if not all((i + s * pr, j + s * pc) in mid and (i - s * pr, j - s * pc) in mid
                               for s in range(1, margin + 1)):
                        continue
                out.setdefault(q, []).append(P)
    return out


def _res(v, P, N):
    if v == "K":
        return KEEP
    if v == "P":
        return P
    if v == "N":
        return N
    return v


def _look(x, bg, r2, m):
    """paint value for crossed colour x: the learned role entry when x plays a role (layer background, then rank-2
    colour), else the learned literal entry, else keep"""
    lit, roles = m
    if x == bg and "bg" in roles:
        return roles["bg"]
    if x == r2 and "r2" in roles:
        return roles["r2"]
    if x in lit:
        return lit[x]
    return "K"


def _decide(x, bg, r2, Ps, m, comb, fb, N):
    res = list(dict.fromkeys(_res(_look(x, bg, r2, m), P, N) for P in Ps))
    if len(res) == 1:
        return res[0]
    key = frozenset(res)
    if key in comb:
        return comb[key]
    return res[-1] if fb == "last" else res[0]


def _run(g, cfg, m, comb, fb, N):
    level, sel, dname, pairing, incl, margin, walls = cfg
    L = _layers(g, level)
    if L is None:
        return None
    out = _base(g, level, L)
    for V, pix in L:
        bg, S, r2 = _participants(V, sel)
        if not S:
            continue
        dirs = _dirs(dname, V, bg)
        merged = _merge([_cover_dir(V, bg, S, d, pairing, walls) for d in dirs], dirs, incl, margin)
        for (i, j), Ps in merged.items():
            r = _decide(V[i][j], bg, r2, list(dict.fromkeys(Ps)), m, comb, fb, N)
            if r is None:
                continue
            for a, b in pix[i][j]:
                out[a][b] = r
    return out


# ----------------------------------------------------------------------------------------------- induction
def _configs():
    out = []
    for level in ("pixel", "cell", "tile", "phase"):
        for sel in SELS:
            for dname in DIRSETS:
                diag = DIRSETS[dname] is None or any(a and b for a, b in DIRSETS[dname])
                for pairing in ("span", "sight", "sight-any"):
                    for incl in (0, 1):
                        for margin in ((0, 1) if pairing != "span" and not incl else (0,)):
                            for walls in ((0, 1) if pairing != "span" and diag else (0,)):
                                cost = (1.0 + LEVELCOST[level] + SELCOST[sel] + DIRCOST[dname] +
                                        {"span": 0.0, "sight": 0.2, "sight-any": 0.7}[pairing] +
                                        0.3 * incl + 0.8 * margin + 0.5 * walls)
                                out.append((round(cost, 3), (level, sel, dname, pairing, incl, margin, walls)))
    out.sort()
    return out


CONFIGS = _configs()


class _Ctx:
    def __init__(self, pairs):
        self.pairs = pairs
        self._lay, self._part, self._cov, self._ch, self._keys, self._base = {}, {}, {}, {}, {}, {}

    def base(self, pi, level):
        k = (pi, level)
        if k not in self._base:
            self._base[k] = (_base(self.pairs[pi][0], level, self.layers(pi, level)) if level == "tile"
                             else self.pairs[pi][0])
        return self._base[k]

    def layers(self, pi, level):
        k = (pi, level)
        if k not in self._lay:
            self._lay[k] = _layers(self.pairs[pi][0], level)
        return self._lay[k]

    def part(self, pi, level, li, sel):
        k = (pi, level, li, sel)
        if k not in self._part:
            self._part[k] = _participants(self.layers(pi, level)[li][0], sel)
        return self._part[k]

    def changed(self, pi, level, li):
        k = (pi, level, li)
        if k not in self._ch:
            g, o = self.base(pi, level), self.pairs[pi][1]
            V, pix = self.layers(pi, level)[li]
            self._ch[k] = {(i, j) for i in range(len(V)) for j in range(len(V[0]))
                           if any(g[a][b] != o[a][b] for a, b in pix[i][j])}
        return self._ch[k]

    def cov(self, pi, level, li, sel, d, pairing, walls):
        k = (pi, level, li, sel, d, pairing, walls if (d[0] and d[1]) else 0)
        if k not in self._cov:
            V = self.layers(pi, level)[li][0]
            bg, S, _ = self.part(pi, level, li, sel)
            c = _cover_dir(V, bg, S, d, pairing, walls)
            self._cov[k] = c
            self._keys[k] = ({q for q, l in c.items() if any(not e for _, e in l)}, set(c))
        return self._cov[k], self._keys[k]


def _interps(g, o, pos, P, N):
    """paint values consistent with what the output shows on this item: 'K', 'P' (pair colour), 'N' (the colour new
    in the training outputs), literal colour."""
    s = set()
    if all(g[a][b] == o[a][b] for a, b in pos):
        s.add("K")
    ys = {o[a][b] for a, b in pos}
    if len(ys) == 1:
        y = ys.pop()
        s.add(y)
        if P is not None and y == P:
            s.add("P")
        if N is not None and y == N:
            s.add("N")
    return s


def _observed(g, o, pos):
    s = set()
    if all(g[a][b] == o[a][b] for a, b in pos):
        s.add(KEEP)
    ys = {o[a][b] for a, b in pos}
    if len(ys) == 1:
        s.add(ys.pop())
    return s


def _pick(cs):
    if "P" in cs:
        return "P"
    if "K" in cs:
        return "K"
    if "N" in cs:
        return "N"
    return min(c for c in cs if isinstance(c, int))


def _learn(ctx, cfg, order, N):
    level, sel, dname, pairing, incl, margin, walls = cfg
    # pass 1: fast necessary check -- every changed item lies on some bridge of this configuration
    for pi in order:
        L = ctx.layers(pi, level)
        if L is None:
            return None
        for li in range(len(L)):
            ch = ctx.changed(pi, level, li)
            if not ch:
                continue
            bg, S, r2 = ctx.part(pi, level, li, sel)
            if not S:
                return None
            u = set()
            for d in _dirs(dname, ctx.layers(pi, level)[li][0], bg):
                mid, allk = ctx.cov(pi, level, li, sel, d, pairing, walls)[1]
                u |= allk if incl else mid
            if not ch <= u:
                return None
    # pass 2: learn the paint map from singly covered items, collect overlaps
    obs, orole, multi = {}, {}, []
    for pi in order:
        g, o = ctx.base(pi, level), ctx.pairs[pi][1]
        for li, (V, pix) in enumerate(ctx.layers(pi, level)):
            bg, S, r2 = ctx.part(pi, level, li, sel)
            if not S:
                continue
            dirs = _dirs(dname, V, bg)
            covs = [ctx.cov(pi, level, li, sel, d, pairing, walls)[0] for d in dirs]
            merged = _merge(covs, dirs, incl, margin)
            if not ctx.changed(pi, level, li) <= merged.keys():
                return None
            for (i, j), Ps in merged.items():
                x = V[i][j]
                pos = pix[i][j]
                dist = list(dict.fromkeys(Ps))
                if len(dist) == 1:
                    c = _interps(g, o, pos, dist[0], N)
                    cx = obs[x] & c if x in obs else c
                    if not cx:
                        return None
                    obs[x] = cx
                    for rn, rv in (("bg", bg), ("r2", r2)):
                        if x == rv:
                            orole[rn] = c if rn not in orole else (orole[rn] & c)
                else:
                    multi.append((x, bg, r2, dist, _observed(g, o, pos)))
    # a role entry is kept only when one paint value explains every item whose crossed colour plays that role
    m = ({x: _pick(c) for x, c in obs.items()}, {rn: _pick(c) for rn, c in orole.items() if c})
    comb, agree = {}, {"first": 0, "last": 0}
    for x, bg, r2, dist, ob in multi:
        res = list(dict.fromkeys(_res(_look(x, bg, r2, m), P, N) for P in dist))
        if len(res) == 1:
            continue
        key = frozenset(res)
        c = comb[key] & ob if key in comb else ob
        if not c:
            return None
        comb[key] = c
        agree["first"] += res[0] in ob
        agree["last"] += res[-1] in ob
    comb = {k: (KEEP if KEEP in c else min(c)) for k, c in comb.items()}
    if agree["first"] > agree["last"]:
        fbs = ("first",)
    elif agree["last"] > agree["first"]:
        fbs = ("last",)
    elif multi and comb:
        fbs = ("last", "first")
    else:
        fbs = ("last",)
    return m, comb, fbs


def _fmt_map(m):
    lit, roles = m
    s = ["%s>%s" % (r, roles[r]) for r in ("bg", "r2") if r in roles]
    return ",".join(s + ["%s>%s" % (x, v) for x, v in sorted(lit.items())])


def _new_colour(pairs):
    """N: the single colour that appears in some training output and in no training input (else None)."""
    ci = {x for g, _ in pairs for r in g for x in r}
    co = {x for _, o in pairs for r in o for x in r} - ci
    return co.pop() if len(co) == 1 else None


def fam(train, limit=3):
    try:
        pairs = [(p["input"], p["output"]) for p in train]
    except Exception:
        return
    if not pairs:
        return
    for g, o in pairs:
        if not g or not g[0] or len(g) != len(o) or any(len(a) != len(b) for a, b in zip(g, o)):
            return
    if all(g == o for g, o in pairs):
        return
    order = sorted(range(len(pairs)), key=lambda k: len(pairs[k][0]) * len(pairs[k][0][0]))
    ctx = _Ctx(pairs)
    N = _new_colour(pairs)
    found = 0
    for cost, cfg in CONFIGS:
        try:
            r = _learn(ctx, cfg, order, N)
        except Exception:
            r = None
        if r is None:
            continue
        m, comb, fbs = r
        for n, fb in enumerate(fbs):
            fn = (lambda g, c=cfg, mm=m, cb=comb, f=fb: _run(g, c, mm, cb, f, N))
            try:
                ok = all(fn(g) == o for g, o in pairs)
            except Exception:
                ok = False
            if not ok:
                break
            level, sel, dname, pairing, incl, margin, walls = cfg
            ov = ";".join("%s>%s" % ("+".join(str(v) for v in sorted(k, key=str)),
                                      "N" if (N is not None and c == N) else c) for k, c in sorted(comb.items(), key=str))
            name = ("bridge_aligned_pairs[level=%s,sel=%s,dirs=%s,pair=%s,incl=%d,margin=%d,walls=%d,map={%s},"
                    "N=%s,overlap={%s}+%s]" % (level, sel, dname, pairing, incl, margin, walls, _fmt_map(m),
                                               N, ov, fb))
            yield (name, cost + 0.05 * n + 0.01 * len(m[0]), fn)
            found += 1
            if found >= limit:
                return


FAMILIES = [fam]
