"""ACTION prior: principle of least action and conservation laws on the grid.

Laws (the prior, stated before any task)
----------------------------------------
L1  Least action.  A curve drawn between terminals is a stationary (minimal) point of the action
        S = length  >>  turns  >>  tie terms            (lexicographic)
    length is octile (orthogonal step 1, diagonal step sqrt 2 = Euclidean step length) on the 4- or 8-lattice,
    obstacles (every non-background cell that is not an end point) have infinite potential, and among the
    shortest curves the straightest one is realised (inertia: a direction change costs).  The remaining tie
    terms are generic, induced per task: first leg along an axis at the source; turns as late as possible
    (keep going straight until forced); lateral steps to a preferred side; leave / enter a terminal that stands
    on a wall perpendicular to that wall.  A curve that passes through a terminal keeps its heading.
    If the minimum is degenerate the prior refuses (or, as an induced option, draws the union of all minimal
    curves - e.g. both one-turn king geodesics form a parallelogram).
L2  Least total length of a network.  Several terminals are joined by the network of minimal total length:
    rectilinear Steiner comb (one trunk at the median coordinate, fewest branches), minimal spanning tree of
    geodesics, minimal-total-length perfect matching (least-action assignment), or a chain / star along an
    induced order of the terminal colours.  A free end (a lone source) is joined to the far boundary.
L3  Conservation.  The cell count of every colour is invariant (checked on all training pairs).  A transformation
    is then a rearrangement whose target is fixed by the conserved quantity: the N mobile cells of a colour are
    poured into the unique container whose capacity (fluid-retaining cells, full or checkerboard lattice)
    equals N.
L4  Equilibrium.  Conserved mass settles into its minimal-potential configuration: a granular heap at the
    floor under its column with a 45-degree angle of repose (rows 1, 3, 5, ... cells, order of the cells kept);
    grains of a mobile colour fall until supported, the other colours being static supports (sand); a poured
    fluid fills the retaining cells of its container (gravity direction induced).

Search space (all parameters induced from the training pairs by internal fitting; each yielded program is
re-verified on every pair by the harness; no task constants)
  act-geodesic   preconditions: same shape, only background cells change.
                 terminals: components of one colour c (c unchanged and touching the drawn cells) | all single
                 cells | role 'pair2' (the unique colour with two components) | role 'edge' (components standing
                 on the border) | every single-colour component (4- / 8-connected with the metric), per colour.
                 curve colour: the unique new colour, or the terminal's colour.   metric N4 | N8.
                 network: pair | comb | chain / star (colour order) | emit (to the far boundary; heading away
                 from the wall the source stands on, or a fixed direction) | each colour class separately
                 (2 members -> geodesic, >2 -> spanning tree or matching, lone -> emit or keep; classes whose
                 least-action network is degenerate may be left alone, induced option).
                 tie rule: unique | union | first-h/v/d | late | late+side | perp.
  act-conserve   preconditions: same shape, colour histogram identical in every pair.
                 capacity[full|checker] x gravity (4 directions): containers = objects retaining fluid cells;
                 mobile = every other non-background cell; each mobile colour -> the container of equal capacity.
                 heap x gravity: every occupied column collapses into a 45-degree heap (count must be k^2).
                 sand[c] x gravity: grains of the mobile colour c (the colour whose cells move in every pair)
                 fall until supported; everything else is static.
Dropped / not kept: minimal-displacement assignment of dots to anchor sites (1b8318e3: the minimal total
displacement matching is degenerate and does not reproduce the outputs); hydrostatic settling of a liquid by
spill-over (28a6681f) - left to the FLUIDS prior.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import permutations, product
import heapq
from gdsl import H, W, bg_of, objects, bbox

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
DIRS = {"N4": N4, "N8": N8}


def _same(train):
    return all((H(p["input"]), W(p["input"])) == (H(p["output"]), W(p["output"])) for p in train)


def _axis(d):
    dy, dx = d
    return "v" if dx == 0 else "h" if dy == 0 else "d"


# ------------------------------------------------------------------ L1: geodesics of minimal action
ORTH = 1000000
DIAG = 1414214                      # sqrt(2) in the same units: octile (Euclidean-step) length
MAXT = 1000


def geodesics(g, free, src, dst, metric, rule=(), d0=None, final_turn=True, cap=2, d1=None):
    """Curves of minimal action from cell set src to cell set dst (dst may lie outside the grid) through
    free cells.  Action is lexicographic: (length, number of turns, tie terms) where length is octile
    (orthogonal step 1, diagonal step sqrt 2) and the tie terms come from `rule`: ('first', axis) = first step
    along axis; ('late',) = turns as late as possible (inertia: keep going straight); ('side', d) = lateral
    steps prefer direction d (N4 only).  d0 = initial heading (a first step in another direction is a turn).
    The lexicographic action is encoded in one integer.  Returns (n_optimal (capped), one optimal path,
    union of optimal paths) or None."""
    h, w = H(g), W(g); nb = DIRS[metric]; dset = set(dst)
    first_ax = next((r[1] for r in rule if r[0] == "first"), None)
    late = any(r[0] == "late" for r in rule)
    side = next((r[1] for r in rule if r[0] == "side"), None)
    F = [[free(y, x) for x in range(w)] for y in range(h)]
    if metric == "N8":
        stepc = [(ORTH if d[0] == 0 or d[1] == 0 else DIAG) << 12 for d in nb]; TC = 1 << 2; FC = 1
        late = False; side = None
    else:
        stepc = [1 << 40] * 4; TC = 1 << 30; FC = 1 << 29
    opp = None if side is None else (-side[0], -side[1])
    sidec = [1 if (opp is not None and d == opp) else 0 for d in nb]
    firstc = [0 if first_ax is None or _axis(d) == first_ax else FC for d in nb]
    K = len(nb)
    def ext(c, k, k2):
        c2 = c + stepc[k2] + sidec[k2]
        if k is not None and k2 != k:
            c2 += TC
            if late: c2 += (MAXT - (c >> 40)) << 11
        return c2
    dist = {}; pq = []; pred = {}
    k0 = None if d0 is None else nb.index(d0)
    for (y, x) in src:
        for k in range(K):
            dy, dx = nb[k]; yy, xx = y + dy, x + dx
            if (yy, xx) in dset: return None               # terminals touch: nothing to draw
            if not (0 <= yy < h and 0 <= xx < w) or not F[yy][xx]: continue
            c = ext(firstc[k], k0, k)
            st = (yy, xx, k)
            if st not in dist or c < dist[st]:
                dist[st] = c; pred[st] = [None]; heapq.heappush(pq, (c, st))
            elif c == dist[st] and None not in pred[st]:
                pred[st].append(None)
    def endcost(st):
        y, x, k = st; m = None
        for k2 in range(K):
            dy, dx = nb[k2]
            if (y + dy, x + dx) in dset:
                cc = ext(dist[st], k if final_turn else None, k2)
                if d1 is not None and nb[k2] != d1: cc += TC
                if m is None or cc < m: m = cc
        return m
    best = None; ends = []
    while pq:
        c, st = heapq.heappop(pq)
        if c != dist.get(st): continue
        if best is not None and c > best: break
        ec = endcost(st)
        if ec is not None:
            if best is None or ec < best: best = ec; ends = [st]
            elif ec == best: ends.append(st)
        y, x, k = st
        for k2 in range(K):
            dy, dx = nb[k2]; yy, xx = y + dy, x + dx
            if not (0 <= yy < h and 0 <= xx < w) or not F[yy][xx]: continue
            cc = ext(c, k, k2); s2 = (yy, xx, k2)
            o = dist.get(s2)
            if o is None or cc < o:
                dist[s2] = cc; pred[s2] = [st]; heapq.heappush(pq, (cc, s2))
            elif cc == o and st not in pred[s2]:
                pred[s2].append(st)
    if best is None: return None
    ends = [e for e in ends if endcost(e) == best]
    # number of optimal curves (capped): predecessors always have a strictly smaller action, so a pass over
    # the states in increasing action is a topological order of the predecessor DAG (no recursion)
    memo = {}
    for st in sorted(pred, key=dist.__getitem__):
        memo[st] = min(cap, sum(1 if p is None else memo.get(p, 0) for p in pred[st]))
    n = sum(memo[e] for e in ends)
    union = set(); stack = list(ends); seen = set()
    while stack:
        st = stack.pop()
        if st is None or st in seen: continue
        seen.add(st); union.add(st[:2]); stack.extend(pred[st])
    one = []; st = ends[0]
    while st is not None:
        one.append(st[:2]); st = pred[st][0]
    return min(n, cap), one, union


_GEO_CACHE = {}


def _geo(g, bg, src, dst, metric, rule=(), d0=None, final_turn=True, d1=None):
    """Cached minimal-action curves over the background cells of g (many configurations share edges)."""
    key = (tuple(map(tuple, g)), bg, tuple(src), tuple(dst), metric, rule, d0, final_turn, d1)
    if key not in _GEO_CACHE:
        if len(_GEO_CACHE) > 4000: _GEO_CACHE.clear()
        _GEO_CACHE[key] = geodesics(g, lambda y, x: g[y][x] == bg, src, dst, metric, rule, d0, final_turn, d1=d1)
    return _GEO_CACHE[key]


def _terminals(g, bg, tsel):
    """Terminal cell groups. tsel = ('col', c) | ('singles',) | ('comp',) (every single-colour component)."""
    if tsel[0] == "comp":                   # single-colour components, connectivity of the curve metric
        return objects(g, bg, tsel[1] == 8, True)
    if tsel[0] == "col":
        c = tsel[1]
        return [o for o in objects(g, bg, True, True) if g[o[0][0]][o[0][1]] == c]
    if tsel[0] == "pair2":                  # role: the unique colour class made of exactly two components
        comps = objects(g, bg, True, True); cnt = Counter(g[o[0][0]][o[0][1]] for o in comps)
        two = [c for c, n in cnt.items() if n == 2]
        return [o for o in comps if g[o[0][0]][o[0][1]] == two[0]] if len(two) == 1 else []
    if tsel[0] == "edge":                   # role: components standing on the grid border
        h, w = H(g), W(g)
        return [o for o in objects(g, bg, True, True) if any(y in (0, h - 1) or x in (0, w - 1) for y, x in o)]
    return [o for o in objects(g, bg, True, False) if len(o) == 1]


def _key(g, t):
    return g[t[0][0]][t[0][1]]


def _paint(out, cells, pcol, bg):
    for y, x in cells:
        if out[y][x] == bg: out[y][x] = pcol


def comb_steiner(pts):
    """Rectilinear Steiner comb of minimal action for points: minimal total length, then fewest branches
    (most terminals lying on the trunk).  None when the optimum is not unique."""
    cands = []
    for ax in ("v", "h"):
        a = sorted(p[1] if ax == "v" else p[0] for p in pts)      # coordinate orthogonal to trunk
        b = [p[0] if ax == "v" else p[1] for p in pts]
        n = len(a)
        for m in range(a[(n - 1) // 2], a[n // 2] + 1):
            cost = sum(abs(v - m) for v in a) + max(b) - min(b)
            cands.append((cost, -a.count(m), ax, m, min(b), max(b)))
    cands.sort()
    if len(cands) > 1 and cands[0][:2] == cands[1][:2]: return None
    cost, _, ax, m, b0, b1 = cands[0]
    cells = set()
    for t in range(b0, b1 + 1):
        cells.add((t, m) if ax == "v" else (m, t))
    for (y, x) in pts:
        if ax == "v":
            for xx in range(min(x, m), max(x, m) + 1): cells.add((y, xx))
        else:
            for yy in range(min(y, m), max(y, m) + 1): cells.add((yy, x))
    return cells


DIRV = {"down": (1, 0), "up": (-1, 0), "left": (0, -1), "right": (0, 1)}
TIES = {"unique": (), "union": (), "perp": (), "first-h": (("first", "h"),), "first-v": (("first", "v"),),
        "first-d": (("first", "d"),), "late": (("late",),)}
for _n, _d in DIRV.items():
    TIES["late-" + _n] = (("late",), ("side", _d))


def _emit_dir(g, t, emit):
    """Heading of an emitting source: fixed, or away from the single grid edge the source touches."""
    if emit in DIRV: return DIRV[emit]
    h, w = H(g), W(g)
    edges = [d for d, hit in ((DIRV["down"], any(y == 0 for y, _ in t)), (DIRV["up"], any(y == h - 1 for y, _ in t)),
                              (DIRV["right"], any(x == 0 for _, x in t)), (DIRV["left"], any(x == w - 1 for _, x in t))) if hit]
    if len(edges) > 1 and len(t) > 1:        # a bar in a corner is attached to the edge it stands on
        r0, c0, r1, c1 = bbox(t)
        if c0 == c1 and r1 > r0: edges = [d for d in edges if d[1] == 0]
        elif r0 == r1 and c1 > c0: edges = [d for d in edges if d[0] == 0]
    return edges[0] if len(edges) == 1 else None


def mst_network(g, bg, grp, metric):
    """Minimal spanning network of geodesics joining the terminals of one class (least total length).
    The spanning tree over pairwise geodesic lengths must be unique; its edges are drawn one at a time, each
    edge only when its minimal-action curve is unique given the headings inherited from curves already drawn
    (a curve passing through a single-cell terminal keeps going straight: inertia)."""
    n = len(grp); nb = DIRS[metric]
    free = lambda y, x: g[y][x] == bg
    D = {}
    for i in range(n):
        for j in range(i + 1, n):
            d = _bfs_steps(g, free, grp[i], grp[j], nb)
            if d is None: return None
            D[(i, j)] = d
    parent = list(range(n))
    def find(a):
        while parent[a] != a: a = parent[a]
        return a
    tree = []
    for (i, j), d in sorted(D.items(), key=lambda kv: (kv[1], kv[0])):
        if find(i) != find(j):
            parent[find(i)] = find(j); tree.append((i, j))
    adj = {i: [] for i in range(n)}
    for i, j in tree: adj[i].append((j, D[(i, j)])); adj[j].append((i, D[(i, j)]))
    def maxw(u, v):                        # heaviest edge on the tree path u..v
        st = [(u, -1, 0)]; seen = {u}
        while st:
            a, pa, m = st.pop()
            if a == v: return m
            for b, wgt in adj[a]:
                if b not in seen: seen.add(b); st.append((b, a, max(m, wgt)))
        return None
    for (i, j), d in D.items():
        if (i, j) not in tree and d == maxw(i, j): return None          # spanning tree not unique
    heading = {}; cells_all = set(); todo = list(tree)
    while todo:
        drawn = False
        for e in list(todo):
            i, j = e; a, b = grp[i], grp[j]
            ha = heading.get(i) if len(a) == 1 else None
            hb = heading.get(j) if len(b) == 1 else None
            r = _geo(g, bg, a, b, metric, (), d0=ha, d1=None if hb is None else (-hb[0], -hb[1]))
            if r is None or r[0] != 1: continue
            path = r[1][::-1]                 # from the cell next to a to the cell next to b
            cells_all |= set(path)
            if len(a) == 1: heading[i] = (a[0][0] - path[0][0], a[0][1] - path[0][1])
            if len(b) == 1: heading[j] = (b[0][0] - path[-1][0], b[0][1] - path[-1][1])
            todo.remove(e); drawn = True; break
        if not drawn: return None
    return cells_all


def matching_network(g, bg, grp, metric, rule):
    """Least-action assignment: the terminals of a class are paired by the perfect matching of minimal total
    geodesic length (it must be unique); each pair is joined by its minimal-action curve."""
    n = len(grp)
    if n % 2 or n > 8: return None
    free = lambda y, x: g[y][x] == bg
    D = {}
    for i in range(n):
        for j in range(i + 1, n):
            D[(i, j)] = _bfs_steps(g, free, grp[i], grp[j], DIRS[metric])
    best = []
    def rec(left, acc, cost):
        if not left:
            best.append((cost, acc)); return
        i = left[0]
        for j in left[1:]:
            d = D[(i, j)]
            if d is None: continue
            rec([k for k in left if k not in (i, j)], acc + [(i, j)], cost + d)
    rec(list(range(n)), [], 0)
    if not best: return None
    best.sort(key=lambda b: b[0])
    if len(best) > 1 and best[0][0] == best[1][0]: return None
    cells = set()
    for i, j in best[0][1]:
        r = _geo(g, bg, grp[i], grp[j], metric, rule)
        if r is None or r[0] != 1: return None
        cells |= set(r[1])
    return cells


def draw_network(g, cfg):
    """cfg = (tsel, pcol, metric, net, tie, order, emit)."""
    tsel, pcol, metric, net, tie, order, emit = cfg
    bg = bg_of(g); ts = _terminals(g, bg, tsel)
    if not ts or (len(ts) < 2 and net != "emit"): return None
    out = [r[:] for r in g]
    tcells = {c for t in ts for c in t}
    free = lambda y, x: g[y][x] == bg
    rule = TIES[tie]
    def colour(t): return pcol if pcol is not None else _key(g, t)
    def pick(r):
        if r is None: return None
        n, one, union = r
        if tie == "union": return union
        return one if n == 1 else None
    if net == "comb":
        if any(len(t) != 1 for t in ts) or len(ts) < 3: return None
        if any(v != bg and (y, x) not in tcells for y, row in enumerate(g) for x, v in enumerate(row)): return None
        cells = comb_steiner([t[0] for t in ts])
        if cells is None: return None
        _paint(out, cells, colour(ts[0]), bg)
        return out
    if net == "emit":
        h, w = H(g), W(g)
        for t in ts:
            D = _emit_dir(g, t, emit)
            if D is None: return None
            proj = max(y * D[0] + x * D[1] for y, x in t)
            tip = [(y, x) for y, x in t if y * D[0] + x * D[1] == proj]
            far = ([(h, x) for x in range(w)] if D == (1, 0) else [(-1, x) for x in range(w)] if D == (-1, 0) else
                   [(y, w) for y in range(h)] if D == (0, 1) else [(y, -1) for y in range(h)])
            if any(y in (0, h - 1) and D[0] or x in (0, w - 1) and D[1] for y, x in tip):
                if any((y + D[0], x + D[1]) in set(far) for y, x in tip): continue      # already at the far edge
            cells = pick(_geo(g, bg, tip, far, metric, rule, d0=D, final_turn=False))
            if cells is None: return None
            _paint(out, cells, colour(t), bg)
        return out
    if net == "each":
        # every colour class of terminals is its own system: two members are joined by a geodesic, a lone
        # member emits a curve away from the grid edge it touches (option), larger classes are refused
        byc = {}
        for t in ts: byc.setdefault(_key(g, t), []).append(t)
        h, w = H(g), W(g)
        for c, grp in sorted(byc.items()):
            if len(grp) == 1:
                if emit != "lone": continue
                t = grp[0]; D = _emit_dir(g, t, "away")
                if D is None: return None
                proj = max(y * D[0] + x * D[1] for y, x in t)
                tip = [(y, x) for y, x in t if y * D[0] + x * D[1] == proj]
                far = ([(h, x) for x in range(w)] if D == (1, 0) else [(-1, x) for x in range(w)] if D == (-1, 0) else
                       [(y, w) for y in range(h)] if D == (0, 1) else [(y, -1) for y in range(h)])
                cells = pick(_geo(g, bg, tip, far, metric, (("late",),), d0=D, final_turn=False))
            elif len(grp) == 2:
                a, b = sorted(grp)
                if tie == "perp":            # leave / enter each wall-attached terminal perpendicular to its wall
                    da = _emit_dir(g, a, "away"); db = _emit_dir(g, b, "away")
                    cells = pick(_geo(g, bg, a, b, metric, (), d0=da, d1=None if db is None else (-db[0], -db[1])))
                else:
                    cells = pick(_geo(g, bg, a, b, metric, rule))
            elif emit == "match":
                cells = matching_network(g, bg, sorted(grp), metric, rule)
            else:
                cells = mst_network(g, bg, sorted(grp), metric)
            if cells is None:
                if order == "skip": continue      # no unique least-action network: the class stays as it is
                return None
            _paint(out, cells, pcol if pcol is not None else c, bg)
        return out
    if net == "pair":
        if len(ts) != 2: return None
        edges = [(0, 1)]
        ks = [_key(g, t) for t in ts]
        if order is not None:
            if any(k not in order for k in ks) or ks[0] == ks[1]: return None
            if order.index(ks[0]) > order.index(ks[1]): edges = [(1, 0)]
    else:   # chain / star over distinct terminal colours in the induced order
        ks = [_key(g, t) for t in ts]
        if len(set(ks)) != len(ks) or order is None or set(ks) != set(order): return None
        idx = [ks.index(c) for c in order]
        edges = list(zip(idx, idx[1:])) if net == "chain" else [(idx[0], j) for j in idx[1:]]
    for a, b in edges:
        cells = pick(_geo(g, bg, ts[a], ts[b], metric, rule))
        if cells is None: return None
        _paint(out, cells, colour(ts[a]), bg)
    return out


def _new_colour(train):
    cs = set()
    for p in train:
        i, o = p["input"], p["output"]
        cs |= {o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]}
    return cs.pop() if len(cs) == 1 else None


def _only_bg_changes(train):
    for p in train:
        i, o = p["input"], p["output"]; bg = bg_of(i)
        if any(i[y][x] != o[y][x] and i[y][x] != bg for y in range(H(i)) for x in range(W(i))): return False
    return True


def _bfs_steps(g, free, src, dst, nb):
    """Plain BFS step count from cell set src to cell set dst (dst cells need not be free)."""
    h, w = H(g), W(g); dset = set(dst); seen = set(src); fr = list(src); d = 0
    while fr:
        d += 1; nx = []
        for y, x in fr:
            for dy, dx in nb:
                q = (y + dy, x + dx)
                if q in dset: return d
                if q in seen or not (0 <= q[0] < h and 0 <= q[1] < w) or not free(*q): continue
                seen.add(q); nx.append(q)
        fr = nx
    return None


def _changed(p):
    i, o = p["input"], p["output"]
    return {(y, x) for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]}


def _precheck(train, tsel, metric, net, emit=None):
    """Cheap necessary conditions on every training pair before any minimal-action search."""
    for p in train:
        g = p["input"]; bg = bg_of(g); ts = _terminals(g, bg, tsel); C = _changed(p)
        free = lambda y, x, g=g, bg=bg: g[y][x] == bg
        if net in ("pair", "chain", "star", "comb"):
            # every terminal is an end of some drawn curve: it touches a drawn cell
            nbm = DIRS[metric]
            if any(not any((y + dy, x + dx) in C for y, x in t for dy, dx in nbm) for t in ts): return False
        if net == "pair":
            if len(ts) != 2: return False
            d = _bfs_steps(g, free, ts[0], ts[1], DIRS[metric])
            if d is None or len(C) < d - 1: return False
        elif net in ("chain", "star"):
            ks = [_key(g, t) for t in ts]
            if len(ks) < 3 or len(set(ks)) != len(ks): return False
        elif net == "each":
            cnt = Counter(_key(g, t) for t in ts)
            if not any(v >= 2 for v in cnt.values()) or len(ts) > 24: return False
        elif net == "comb":
            if len(ts) < 3 or any(len(t) != 1 for t in ts): return False
        elif net == "emit":
            if not ts or len(ts) > 12: return False
            h, w = H(g), W(g)
            for t in ts:
                D = _emit_dir(g, t, emit)
                if D is None: return False
                # the curve leaves the source at its tip: a drawn cell must touch the tip (unless at the edge)
                proj = max(y * D[0] + x * D[1] for y, x in t)
                tip = [(y, x) for y, x in t if y * D[0] + x * D[1] == proj]
                if all(0 <= y + D[0] < h and 0 <= x + D[1] < w for y, x in tip) and \
                   not any((y + dy, x + dx) in C for y, x in tip for dy, dx in N4): return False
            if emit in DIRV:
                D = DIRV[emit]
                edge = {(h - 1, x) for x in range(w)} if D == (1, 0) else {(0, x) for x in range(w)} if D == (-1, 0) else \
                       {(y, w - 1) for y in range(h)} if D == (0, 1) else {(y, 0) for y in range(h)}
                if not (C & edge): return False
    return True


def fam_geodesic(train):
    if not _same(train) or not _only_bg_changes(train): return
    pnew = _new_colour(train)
    i0 = train[0]["input"]; bg = bg_of(i0)
    # terminal colour candidates: colours present in every input, touching the changed (drawn) cells
    cols = None
    for p in train:
        i, o = p["input"], p["output"]
        near = set()
        for y, x in _changed(p):
            for dy, dx in N8:
                yy, xx = y + dy, x + dx
                if 0 <= yy < H(i) and 0 <= xx < W(i) and i[yy][xx] != bg_of(i): near.add(i[yy][xx])
        cols = near if cols is None else cols & near
    tsels = [("col", c) for c in sorted(cols or [])] + [("singles",), ("pair2",), ("edge",), ("comp", 4), ("comp", 8)]
    pcols = [pnew] if pnew is not None else [None]
    found = 0; kinds = set()
    for tsel, pcol, metric in product(tsels, pcols, ("N4", "N8")):
        if tsel[0] == "comp" and tsel[1] != (4 if metric == "N4" else 8): continue
        if pcol is None:        # curves drawn in their terminal's colour: drawn colours must be terminal colours
            okc = True
            for p in train:
                tcols = {_key(p["input"], t) for t in _terminals(p["input"], bg_of(p["input"]), tsel)}
                if any(p["output"][y][x] not in tcols for y, x in _changed(p)): okc = False; break
            if not okc: continue
        ts0 = _terminals(i0, bg, tsel)
        ks0 = [_key(i0, t) for t in ts0]
        orders = []
        if 2 <= len(set(ks0)) <= 4 and len(set(ks0)) == len(ks0):
            orders = [list(o) for o in permutations(sorted(set(ks0)))]
        cfgs = []
        if metric == "N4" and _precheck(train, tsel, metric, "comb"):
            cfgs.append((tsel, pcol, metric, "comb", "unique", None, None))
        if _precheck(train, tsel, metric, "pair"):
            for tie in ("unique", "union", "late"):
                cfgs.append((tsel, pcol, metric, "pair", tie, None, None))
            for tie in ("first-h", "first-v", "first-d"):
                if tie == "first-d" and metric == "N4": continue
                for o in (orders if len(set(ks0)) == 2 else [None] if len(set(ks0)) == 1 else []):
                    cfgs.append((tsel, pcol, metric, "pair", tie, o, None))
        if orders and len(orders[0]) >= 3 and _precheck(train, tsel, metric, "chain"):
            for o in orders:
                for net in ("chain", "star"):
                    for tie in ("unique", "first-h", "first-v"):
                        cfgs.append((tsel, pcol, metric, net, tie, o, None))
        if tsel[0] == "comp" and _precheck(train, tsel, metric, "each"):
            for tie in ("unique", "perp", "late"):
                for lone in (None, "lone", "match"):
                    for amb in (None, "skip"):
                        cfgs.append((tsel, pcol, metric, "each", tie, amb, lone))
        if metric == "N4" and tsel[0] in ("col", "edge"):
            for emit in ("away",) + (tuple(DIRV) if tsel[0] == "col" else ()):
                if not _precheck(train, tsel, metric, "emit", emit): continue
                for tie in ("unique", "late") + tuple("late-" + d for d in DIRV):
                    cfgs.append((tsel, pcol, metric, "emit", tie, None, emit))
        for cfg in cfgs:
            if found >= 3 and tsel[0] in kinds: break          # keep a few programs, one per terminal role
            ok = True
            for p in train:
                if draw_network(p["input"], cfg) != p["output"]: ok = False; break
            if not ok: continue
            kinds.add(tsel[0])
            tsel_, pcol_, metric_, net_, tie_, o_, e_ = cfg
            name = (f"act-geodesic[{tsel_[0]}{'' if len(tsel_) == 1 else tsel_[1]},{metric_},{net_},{tie_}"
                    f"{'' if o_ is None else ',order=' + ''.join(map(str, o_)) if not isinstance(o_, str) else ',' + o_}{'' if e_ is None else ',emit=' + e_}]")
            yield (name, 4, lambda g, cfg=cfg: draw_network(g, cfg))
            found += 1
            if found >= 5: return


# ------------------------------------------------------------------ L2 + L3: conservation and equilibrium
ROT = {"down": (lambda g: [r[:] for r in g], lambda g: [r[:] for r in g]),
       "up": (lambda g: [r[:] for r in g[::-1]], lambda g: [r[:] for r in g[::-1]]),
       "right": (lambda g: [list(r) for r in zip(*g)], lambda g: [list(r) for r in zip(*g)]),
       "left": (lambda g: [list(r) for r in zip(*g)][::-1], lambda g: [list(r) for r in zip(*g[::-1])])}


def held(cells, h, w):
    """Cells of the bbox of an object that retain a fluid under gravity (down): starting there, moving
    down / left / right through non-object cells never leaves the bbox.  Closed frames retain their whole
    interior, cups their bowl."""
    cs = set(cells); r0, c0, r1, c1 = bbox(cells)
    esc = set()                          # cells from which the fluid escapes: reverse flood from outside
    st = []
    for y in range(r0, r1 + 1):
        for x in range(c0, c1 + 1):
            if (y, x) in cs: continue
            # a cell escapes if one move (down/left/right) leaves the bbox
            if y + 1 > r1 or x - 1 < c0 or x + 1 > c1: esc.add((y, x)); st.append((y, x))
    while st:
        y, x = st.pop()
        for py, px in ((y - 1, x), (y, x + 1), (y, x - 1)):     # predecessors that can move into (y, x)
            if r0 <= py <= r1 and c0 <= px <= c1 and (py, px) not in cs and (py, px) not in esc:
                esc.add((py, px)); st.append((py, px))
    return [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in cs and (y, x) not in esc]


def _pattern(cells, pat):
    if pat == "full": return list(cells)
    y0, x0 = min(cells)
    return [(y, x) for y, x in cells if (y + x - y0 - x0) % 2 == 0]


def capacity_pour(g, pat):
    """Mass conservation selects the target: every mobile colour (cells outside containers) is poured,
    count preserved, into the unique container whose capacity under the fill pattern equals its count."""
    bg = bg_of(g); h, w = H(g), W(g)
    objs = objects(g, bg, True, True)
    conts = []
    for o in objs:
        if len(o) < 3: continue
        hd = [c for c in held(o, h, w) if g[c[0]][c[1]] == bg]
        if hd: conts.append((o, _pattern(hd, pat)))
    if not conts: return None
    ccells = {c for o, _ in conts for c in o}
    mobile = {}
    for y in range(h):
        for x in range(w):
            if g[y][x] != bg and (y, x) not in ccells: mobile.setdefault(g[y][x], []).append((y, x))
    if not mobile: return None
    out = [r[:] for r in g]; used = set()
    for c, cells in mobile.items():
        hits = [k for k, (o, tgt) in enumerate(conts) if len(tgt) == len(cells)]
        if len(hits) != 1 or hits[0] in used: return None
        used.add(hits[0])
        for y, x in cells: out[y][x] = bg
        for y, x in conts[hits[0]][1]: out[y][x] = c
    return out


def heap(g):
    """Granular equilibrium with mass conservation: the cells of every occupied column collapse into a
    heap at the floor with a 45-degree angle of repose (row widths 1, 3, 5, ... centred on the column);
    cells keep their top-to-bottom order (apex first)."""
    bg = bg_of(g); h, w = H(g), W(g)
    out = [[bg] * w for _ in range(h)]
    for x in range(w):
        col = [g[y][x] for y in range(h) if g[y][x] != bg]
        if not col: continue
        k = int(round(len(col) ** 0.5))
        if k * k != len(col) or k > h: return None
        slots = []
        for j in range(k):                        # j = 0 apex row
            y = h - k + j; half = j
            if x - half < 0 or x + half >= w: return None
            slots += [(y, xx) for xx in range(x - half, x + half + 1)]
        for (y, xx), v in zip(slots, col):
            if out[y][xx] != bg: return None
            out[y][xx] = v
    return out


def sand(g, m):
    """Granular equilibrium of one mobile colour m under gravity (down): every grain falls until it rests on a
    non-background cell or the floor; all other colours are static supports.  Count is conserved."""
    bg = bg_of(g); h, w = H(g), W(g); out = [r[:] for r in g]
    if m == bg or not any(v == m for r in g for v in r): return None
    for x in range(w):
        for y in range(h - 1, -1, -1):
            if out[y][x] != m: continue
            yy = y
            while yy + 1 < h and out[yy + 1][x] == bg: yy += 1
            if yy != y: out[yy][x] = m; out[y][x] = bg
    return out


def _conserved(train):
    for p in train:
        i, o = p["input"], p["output"]
        if Counter(v for r in i for v in r) != Counter(v for r in o for v in r): return False
    return True


def fam_conserve(train):
    if not _same(train) or not _conserved(train): return
    # mobile colours: the colours of cells that move in every training pair
    mobile = None
    for p in train:
        i, o = p["input"], p["output"]; bg = bg_of(i)
        mv = {i[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x] and i[y][x] != bg}
        mobile = mv if mobile is None else mobile & mv
    mobile = mobile or set()
    for grav, (to, back) in ROT.items():
        for pat in ("full", "checker"):
            fn = lambda g, to=to, back=back, pat=pat: (lambda r: back(r) if r else None)(capacity_pour(to(g), pat))
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (f"act-conserve:capacity[{pat},gravity={grav}]", 4, fn)
        fn = lambda g, to=to, back=back: (lambda r: back(r) if r else None)(heap(to(g)))
        if all(fn(p["input"]) == p["output"] for p in train):
            yield (f"act-conserve:heap[gravity={grav}]", 4, fn)
        for m in sorted(mobile):
            fn = lambda g, to=to, back=back, m=m: (lambda r: back(r) if r else None)(sand(to(g), m))
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (f"act-conserve:sand[c{m},gravity={grav}]", 4, fn)


FAMILIES = (fam_geodesic, fam_conserve)
