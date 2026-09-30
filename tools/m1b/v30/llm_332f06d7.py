"""Family for ARC task 332f06d7 -- concept: PIPELINE PIG (mechanics / pipeline engineering),
equivalently the PIANO MOVER'S problem (robotics motion planning).

A pipeline "pig" is a rigid plug pushed through a pipe toward the receiver; it travels as far as the
pipe's bore lets it and lodges at the first restriction narrower than itself.  In the grid:
  * pipe    = the colour the pig's old footprint turns into (the bore),
  * pig     = the one colour whose cells are translated between input and output (a rigid body),
  * receiver= a third colour: the sink the flow drives the pig toward,
  * every other colour is wall.
Mechanism: free space = pipe | pig | receiver cells.  The pig's configuration space is the set of
translations of its exact shape that lie wholly in free space (a morphological erosion); flood-fill
it from the pig's start pose (4-neighbour unit shifts).  Potential = geodesic (BFS, 4-connected)
distance of free cells to the receiver; the pig settles at the reachable pose of least potential
(it reaches and caps the receiver when the bore is wide enough all the way, otherwise it jams just
before the first too-narrow section).  The vacated footprint becomes pipe; the pig is drawn at the
new pose (over the receiver if it got there).

Induced from training: pig colour (the translated colour), pipe colour (what vacated pig cells
become), receiver colour (chosen from the remaining input colours, must fit).
Declared finite parameter:
  potential in ('nose', 'mass') -- rank poses by (min, sum) or (sum, min) of cell potentials.
"""
from collections import deque

INF = float('inf')


def _cells(g, c):
    return [(r, k) for r, row in enumerate(g) for k, v in enumerate(row) if v == c]


def _colours(g):
    return {v for row in g for v in row}


def _induce_roles(train):
    """Return (pig, pipe, candidate receiver colours) or None.
    pig  = colour translated (same count, different cells) in every pair;
    pipe = the single colour its vacated cells turn into, the same in every pair."""
    roles = None
    for p in train:
        a, b = p['input'], p['output']
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        here = set()
        for c in _colours(a) & _colours(b):
            ca, cb = set(_cells(a, c)), set(_cells(b, c))
            if ca != cb and len(ca) == len(cb):
                vc = {b[r][k] for r, k in ca - cb}
                if len(vc) == 1:
                    here.add((c, vc.pop()))
        roles = here if roles is None else roles & here
    if not roles or len(roles) != 1:
        return None
    pig, pipe = roles.pop()
    common = set.intersection(*[_colours(p['input']) for p in train])
    return pig, pipe, sorted(common - {pig, pipe})


def make_pig(pig, pipe, recv, potential):
    def fn(g):
        H, W = len(g), len(g[0])
        body = _cells(g, pig)
        goal = _cells(g, recv)
        if not body or not goal:
            return [row[:] for row in g]
        free = [[g[r][k] in (pig, pipe, recv) for k in range(W)] for r in range(H)]
        # geodesic potential: BFS distance from the receiver through free cells
        dist = [[INF] * W for _ in range(H)]
        q = deque()
        for r, k in goal:
            dist[r][k] = 0
            q.append((r, k))
        while q:
            r, k = q.popleft()
            for dr, dk in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nk = r + dr, k + dk
                if 0 <= nr < H and 0 <= nk < W and free[nr][nk] and dist[nr][nk] == INF:
                    dist[nr][nk] = dist[r][k] + 1
                    q.append((nr, nk))
        r0 = min(r for r, _ in body)
        k0 = min(k for _, k in body)
        shape = [(r - r0, k - k0) for r, k in body]

        def fits(t):
            tr, tk = t
            for dr, dk in shape:
                r, k = tr + dr, tk + dk
                if not (0 <= r < H and 0 <= k < W and free[r][k]):
                    return False
            return True

        def score(t):
            ds = [dist[t[0] + dr][t[1] + dk] for dr, dk in shape]
            lo, s = min(ds), sum(ds)
            return (lo, s) if potential == 'nose' else (s, lo)

        start = (r0, k0)
        seen = {start}
        q = deque([start])
        best, best_s = start, score(start)
        while q:
            t = q.popleft()
            sc = score(t)
            if sc < best_s:
                best, best_s = t, sc
            for dr, dk in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (t[0] + dr, t[1] + dk)
                if n not in seen and fits(n):
                    seen.add(n)
                    q.append(n)
        out = [row[:] for row in g]
        for r, k in body:
            out[r][k] = pipe
        for dr, dk in shape:
            out[best[0] + dr][best[1] + dk] = pig
        return out
    return fn


def fam_pipeline_pig(train):
    roles = _induce_roles(train)
    if roles is None:
        return
    pig, pipe, receivers = roles
    for recv in receivers:
        for potential in ('nose', 'mass'):
            fn = make_pig(pig, pipe, recv, potential)
            try:
                if all(fn(p['input']) == p['output'] for p in train):
                    yield ('mechanics:pipeline_pig[pig=%d,pipe=%d,receiver=%d,potential=%s]'
                           % (pig, pipe, recv, potential), 3, fn)
                    return
            except Exception:
                continue


FAMILIES = (fam_pipeline_pig,)
