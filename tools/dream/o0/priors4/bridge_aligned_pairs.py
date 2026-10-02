"""Prior family: bridge_aligned_pairs (v4, test-blind, induced from training pairs only).
priors4 (Fable v11, D38 / G68): every colour parameter is a declared role of colour_roles.py (background,
rank_colour(k), novel_colour) or a role-bound value; no literal colour numbers.  Non-colour parameters, steps and
the enumeration order are those of priors3.

Concept: two items that share a colour (or, optionally, any two facing items) and lie on a common row, column or
diagonal are joined: every item between them is repainted by a role-keyed map of the crossed colour, and items
covered by bridges of different paint get one learned role.

One generator, written once:
  1. ABSTRACT the grid into item layers: pixel | cell (separator lattice, item value = its single marker colour) |
     tile (lattice shapes coloured by their marker-coloured twin) | phase (same-offset pixels of equal tiles).
  2. PARTICIPANTS: items whose colour passes `sel` (not background | outside the k most frequent colours | colour
     occurring exactly twice) in the layer.
  3. PAIRS along every line of the directions `dirs`: span (consecutive same-colour participants) | sight (clear line
     of sight; `any`: any two participants), with incl / margin / walls as before.
  4. PAINT: crossed colour x -> value.  Keys are ROLES of the item layer only: bg (its background, CR.background)
     and rank k (CR.rank_colour of the layer, k in 1, 2, 3, -1, -2); the first role x plays that has an entry
     decides; a colour playing no keyed role keeps.  Values: P (the pair's own colour, participant), N (novel colour),
     K (keep), or a layer role.  A role entry is kept only when one value explains every singly covered item whose
     crossed colour plays that role.  Overlaps of bridges with different paint: one role (K | N | layer role) for
     every crossing, else first / last bridge in direction order.  Single pass, no cascade.
  N = CR.novel_colour(train); when undefined, the role-bound value new_any(train) DEFINED HERE (the single colour
  that appears in some training output and in no training input; CR.novel_colour also needs it in EVERY output).

BINDINGS (G68) -- per member, the literal colour values priors3 induced and the role each became
("LOST: needs literal c" = no declared role explains it; the member no longer fits).
  06df4c85  separator 1/8/4 -> keep <- bg>K ; crossed 0 -> pair colour <- rank1>P (0 is ink rank 1 in every pair) ;
            literal keys 0>P,1>K,2>K,3>K,4>K,8>K,9>K removed (redundant: rank roles / default keep)        FITS
  7666fa5d  crossed 8 -> 2 <- bg>N, N <- novel ; literal key 8>N removed (8 = layer background)            FITS
  a096bf4d  crossed 3/8/4 -> pair colour <- bg>P ; literal keys 3,4,8>P removed (each phase layer's
            background)                                                                                     FITS
  bcb3040b  crossed 0 -> 2 <- bg>P ; crossed 1 -> 3 <- rank1>N, N <- novel ; literal keys 0>P,1>N removed   FITS
  cbded52d  crossed 1 -> pair colour <- bg>P ; literal key 1>P removed                                      FITS
  d6ad076f  crossed 0 -> 8 <- bg>N, N <- novel ; literal key 0>N removed                                    FITS
  d94c3b52  crossed tiles 1 -> 7 <- bg>N, N <- novel ; marker colour <- rarest tile colour (participant) ;
            literal key 1>N removed                                                                         FITS
  e760a62e  crossed 0 -> pair colour <- bg>P ; overlap {2,3} -> 6 <- cross>N with N <- new_any (6 is absent
            from output 3, so CR.novel_colour is None) ; literal keys 0,2,3>P and overlap key {2,3} removed    FITS
  b7f8a4d8  crossed 0 -> pair colour  LOST: needs literal 0 (0 is ink rank 1 in pair 1 but the background in
            pairs 2 and 3, where crossed background must keep in pair 1; no single role names it)
  Unfitted in priors3 and still unfitted: 98c475bf, b9630600, f35d900a.
Literal colours removed: literal crossed-colour keys of the paint map, literal paint values, literal overlap table
(set of colours -> colour), N printed as a colour (now the role name).
"""

import colour_roles as CR

CARD = "prior4_bridge_aligned_pairs"
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
               "{0,1} . paint map key in {layer bg, layer ink rank 1,2,3,-1,-2} -> {P, N, K, layer role} (first "
               "role with an entry, otherwise keep) . overlap = one role {K, N, layer role}, else {first, last}"),
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
# crossed-colour keys and paint values are roles of the item layer (G68): its background and its ink ranks
ROLE_KEYS = ("bg",) + tuple("rank%d" % k for k in CR.RANKS)


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
    """(layer background, participant colours, layer roles {role name: colour}).  Roles: bg = most frequent item value
    (CR.background of the layer), rank k = CR.rank_colour of the layer."""
    cnt = {}
    for r in V:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    order = sorted(cnt, key=lambda k: (-cnt[k], k))
    bg = CR.background(V)
    rl = {"bg": bg}
    for k in CR.RANKS:
        c = CR.rank_colour(V, k, bg)
        if c is not None:
            rl["rank%d" % k] = c
    if sel == "nonbg":
        S = set(order[1:])
    elif sel == "twice":
        S = {c for c in cnt if cnt[c] == 2 and c != bg}
    else:
        k = 2 if sel == "rank2" else 3
        S = set(order[k:])
    S.discard(MIXED)
    return bg, S, rl


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


def _res(v, P, N, rl):
    """paint value -> colour: K keep, P the pair (endpoint) colour, N the novel colour, or a layer role."""
    if v == "K":
        return KEEP
    if v == "P":
        return P
    if v == "N":
        return N
    return rl.get(v)


def _look(x, rl, m):
    """paint value for crossed colour x: the learned entry of the first role x plays in this layer (background, then
    ink ranks 1, 2, 3, -1, -2), else keep"""
    for rn in ROLE_KEYS:
        if rn in m and rl.get(rn) == x:
            return m[rn]
    return "K"


def _decide(x, rl, Ps, m, comb, fb, N):
    res = list(dict.fromkeys(_res(_look(x, rl, m), P, N, rl) for P in Ps))
    if len(res) == 1:
        return res[0]
    if comb is not None:                      # bridges painting different colours cross: the learned role
        return _res(comb, None, N, rl)
    return res[-1] if fb == "last" else res[0]


def _run(g, cfg, m, comb, fb, N):
    level, sel, dname, pairing, incl, margin, walls = cfg
    L = _layers(g, level)
    if L is None:
        return None
    out = _base(g, level, L)
    for V, pix in L:
        bg, S, rl = _participants(V, sel)
        if not S:
            continue
        dirs = _dirs(dname, V, bg)
        merged = _merge([_cover_dir(V, bg, S, d, pairing, walls) for d in dirs], dirs, incl, margin)
        for (i, j), Ps in merged.items():
            r = _decide(V[i][j], rl, list(dict.fromkeys(Ps)), m, comb, fb, N)
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


def _interps(g, o, pos, P, N, rl):
    """paint values consistent with what the output shows on this item: 'K', 'P' (pair colour), 'N' (the novel
    colour), or a layer role (bg, rank k) -- never a literal colour."""
    s = set()
    if all(g[a][b] == o[a][b] for a, b in pos):
        s.add("K")
    ys = {o[a][b] for a, b in pos}
    if len(ys) == 1:
        y = ys.pop()
        if P is not None and y == P:
            s.add("P")
        if N is not None and y == N:
            s.add("N")
        s |= {rn for rn, c in rl.items() if c == y}
    return s


def _comb_interps(ob, N, rl):
    """roles explaining an item where bridges of different paint cross: K | N | layer role."""
    s = set()
    if KEEP in ob:
        s.add("K")
    if N is not None and N in ob:
        s.add("N")
    s |= {rn for rn, c in rl.items() if c in ob}
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
    for v in ("P", "K", "N") + ROLE_KEYS:
        if v in cs:
            return v
    return None


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
            bg, S, rl = ctx.part(pi, level, li, sel)
            if not S:
                return None
            u = set()
            for d in _dirs(dname, ctx.layers(pi, level)[li][0], bg):
                mid, allk = ctx.cov(pi, level, li, sel, d, pairing, walls)[1]
                u |= allk if incl else mid
            if not ch <= u:
                return None
    # pass 2: learn the role-keyed paint map from singly covered items, collect overlaps
    orole, multi, singles = {}, [], []
    for pi in order:
        g, o = ctx.base(pi, level), ctx.pairs[pi][1]
        for li, (V, pix) in enumerate(ctx.layers(pi, level)):
            bg, S, rl = ctx.part(pi, level, li, sel)
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
                    c = _interps(g, o, pos, dist[0], N, rl)
                    plays = [rn for rn in ROLE_KEYS if rl.get(rn) == x]
                    if "K" not in c and not plays:
                        return None              # a repainted item whose colour plays no role: needs a literal key
                    for rn in plays:
                        orole[rn] = c if rn not in orole else (orole[rn] & c)
                    singles.append((x, rl, dist[0], pos, g, o))
                else:
                    multi.append((x, rl, dist, _observed(g, o, pos)))
    # a role entry is kept only when one paint value explains every item whose crossed colour plays that role
    m = {rn: _pick(c) for rn, c in orole.items() if c}
    # cheap necessary check before the full run: every singly covered item gets the colour the output shows
    for x, rl, P, pos, g, o in singles:
        if _res(_look(x, rl, m), P, N, rl) not in _observed(g, o, pos):
            return None
    comb_c, agree, conflicts = None, {"first": 0, "last": 0}, 0
    for x, rl, dist, ob in multi:
        res = list(dict.fromkeys(_res(_look(x, rl, m), P, N, rl) for P in dist))
        if len(res) == 1:
            continue
        conflicts += 1
        c = _comb_interps(ob, N, rl)
        comb_c = c if comb_c is None else comb_c & c
        agree["first"] += res[0] in ob
        agree["last"] += res[-1] in ob
    comb = _pick(comb_c) if comb_c else None
    if comb is not None:
        fbs = ("last",)
    elif agree["first"] > agree["last"]:
        fbs = ("first",)
    elif agree["last"] > agree["first"]:
        fbs = ("last",)
    elif conflicts:
        fbs = ("last", "first")
    else:
        fbs = ("last",)
    return m, comb, fbs


def _fmt_map(m):
    return ",".join("%s>%s" % (rn, m[rn]) for rn in ROLE_KEYS if rn in m)


def _new_any(pairs):
    """Role-bound value defined here (CR.novel_colour is stricter: it needs the colour in EVERY output): the single
    colour that appears in some training output and in no training input (else None)."""
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
    N, nrole = CR.novel_colour(train), "novel"       # role novel_colour, fixed by the training pairs
    if N is None:
        N, nrole = _new_any(pairs), "new_any"
    if N is None:
        nrole = None
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
            ov = "cross>%s" % comb if comb is not None else ""
            name = ("bridge_aligned_pairs[level=%s,sel=%s,dirs=%s,pair=%s,incl=%d,margin=%d,walls=%d,map={%s},"
                    "N=%s,overlap={%s}+%s]" % (level, sel, dname, pairing, incl, margin, walls, _fmt_map(m),
                                               nrole, ov, fb))
            yield (name, cost + 0.05 * n + 0.01 * len(m), fn)
            found += 1
            if found >= limit:
                return


FAMILIES = [fam]
