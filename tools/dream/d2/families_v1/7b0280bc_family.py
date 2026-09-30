"""Family for ARC task 7b0280bc -- concept: GEODESIC (geometry / metric graph theory).

Picture: a network drawn on a background.  Square pads (all pads of a colour are solid s x s squares) are
the stations; thin strokes of another colour are the roads, each road joining two pads.  Exactly one pad
colour occurs as exactly two pads: these are the two endpoints.  The geodesic (shortest route through the
network) between the two endpoints is highlighted: every road and every intermediate station on a
shortest route is repainted, while dead ends and longer detours around loops keep their colours.

Everything is induced; nothing about sizes, positions or colour numbers is stored:
  background     = most common colour of the input
  pad colours    = colours whose 4-connected pieces are all solid squares of one side >= 2
  endpoint colour= the pad colour that has exactly two pads; other pad colours are stations
  road colours   = every other non-background colour
  elements       = 8-connected single-colour pieces; two elements are linked when they touch (8-neighbourhood)
Declared finite parameter domains, chosen by fitting the training pairs:
  metric in {"hops", "length"}      -- route length = number of elements crossed / number of cells crossed
  paint[role] in {"keep"} + colours -- per role (road, station, endpoint) the colour an on-geodesic element
                                       takes, induced from the training outputs (must be consistent)
All shortest routes are highlighted together (the geodesic interval), so ties need no arbitrary choice.
"""
from collections import Counter
import heapq

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = tuple((dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
METRICS = ("hops", "length")
ROLES = ("road", "station", "endpoint")


def _pieces(g, colour, nbrs):
    H, W = len(g), len(g[0])
    seen, out = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] != colour or (r, c) in seen:
                continue
            seen.add((r, c)); stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop(); cells.append((y, x))
                for dy, dx in nbrs:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] == colour:
                        seen.add((ny, nx)); stack.append((ny, nx))
            out.append(cells)
    return out


def _is_pad_colour(g, colour):
    sides = set()
    for cells in _pieces(g, colour, N4):
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        h, w = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
        if h != w or h < 2 or len(cells) != h * w:
            return False
        sides.add(h)
    return len(sides) == 1


def analyse(g):
    """Return (elements, roles, adjacency, endpoints) or None when the picture is not a two-endpoint network."""
    cnt = Counter(v for row in g for v in row)
    bg = cnt.most_common(1)[0][0]
    colours = [c for c in cnt if c != bg]
    pads = [c for c in colours if _is_pad_colour(g, c)]
    npads = {c: len(_pieces(g, c, N4)) for c in pads}
    ends = [c for c in pads if npads[c] == 2]
    if len(ends) != 1 or len(pads) < 2 or len(pads) == len(colours):
        return None
    end = ends[0]
    elems, role, lab = [], [], {}
    for c in colours:
        for cells in _pieces(g, c, N8):
            i = len(elems); elems.append(cells)
            role.append("endpoint" if c == end else "station" if c in pads else "road")
            for p in cells:
                lab[p] = i
    adj = [set() for _ in elems]
    for i, cells in enumerate(elems):
        for y, x in cells:
            for dy, dx in N8:
                j = lab.get((y + dy, x + dx))
                if j is not None and j != i:
                    adj[i].add(j)
    terms = [i for i in range(len(elems)) if role[i] == "endpoint"]
    if len(terms) != 2:
        return None
    return elems, role, adj, terms


def _dist(elems, adj, src, metric):
    w = (lambda j: 1) if metric == "hops" else (lambda j: len(elems[j]))
    dist = {src: 0}; pq = [(0, src)]
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist[i]:
            continue
        for j in adj[i]:
            nd = d + w(j)
            if nd < dist.get(j, float("inf")):
                dist[j] = nd; heapq.heappush(pq, (nd, j))
    return dist, w


def geodesic(g, metric):
    """Indices of elements lying on some shortest route between the two endpoints, plus the analysis."""
    a = analyse(g)
    if a is None:
        return None
    elems, role, adj, (s, t) = a
    ds, w = _dist(elems, adj, s, metric)
    dt, _ = _dist(elems, adj, t, metric)
    if t not in ds:
        return None
    full = ds[t] + w(s)                                # cost of a shortest route, both ends included
    on = set()
    for i in ds:
        if i in dt and (ds[i] + w(s)) + (dt[i] + w(t)) - w(i) == full:   # s..i and i..t, i counted once
            on.add(i)
    return elems, role, on


def paint(g, metric, colours):
    res = geodesic(g, metric)
    if res is None:
        return [row[:] for row in g]
    elems, role, on = res
    out = [row[:] for row in g]
    for i in on:
        c = colours[role[i]]
        if c == "keep":
            continue
        for y, x in elems[i]:
            out[y][x] = c
    return out


def fam_geodesic(train):
    for metric in METRICS:
        colours, ok = {}, True
        for p in train:
            a, b = p["input"], p["output"]
            if len(a) != len(b) or len(a[0]) != len(b[0]):
                return
            res = geodesic(a, metric)
            if res is None:
                ok = False; break
            elems, role, on = res
            for i in on:
                outs = {b[y][x] for y, x in elems[i]}
                ins = {a[y][x] for y, x in elems[i]}
                if len(outs) != 1:
                    ok = False; break
                o = outs.pop()
                val = "keep" if {o} == ins else o
                if colours.setdefault(role[i], val) != val:
                    ok = False; break
            if not ok:
                break
        if not ok:
            continue
        for r in ROLES:
            colours.setdefault(r, "keep")
        cols = dict(colours)

        def fn(g, metric=metric, cols=cols):
            return paint(g, metric, cols)

        if all(fn(p["input"]) == p["output"] for p in train):
            params = ",".join(f"{r}={cols[r]}" for r in ROLES)
            yield (f"geometry:geodesic[metric={metric},{params}]", 3, fn)


FAMILIES = (fam_geodesic,)
