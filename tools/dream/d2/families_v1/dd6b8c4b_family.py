"""Family for ARC task dd6b8c4b -- concept: CATCHMENT (hydrology: a drainage basin feeding one reservoir).

Reading of the task
-------------------
A small reservoir (a block of "container" colours, here a framed cell) sits in a landscape of background ground
crossed by impermeable walls.  Droplets (single cells of the "mover" colour) lie scattered around.  The reservoir
drains its catchment: only droplets that can flow to it -- along a 4-connected path of ground/droplet cells that
never crosses a wall -- are drawn in, the ones with the shortest flow path first, until the reservoir is full
(capacity = its number of cells).  Each captured droplet leaves ground behind; the reservoir's cells are filled with
the mover colour in raster order.  Droplets outside the catchment (behind walls) or beyond capacity stay put.

Roles (no task constants):
  * mover      = the one colour the training outputs both remove and write (from the changed cells).
  * ground     = the colour a captured droplet leaves behind (from train; not assumed to be the majority colour,
                 walls may outnumber it).
  * container  = the input colours of the cells overwritten by the mover (from train); the reservoir is every cell
                 of those colours in the grid being solved.
  * walls      = every other colour (impassable).
Note: train fixes conn=4 but cannot separate the two fill orders (they differ only when 5..8 droplets are caught),
so both are yielded, raster first as the simpler hypothesis.

Parameters (small declared finite domains, induced from train; every fitting combination is yielded, preferred
first):
  conn  in (4, 8)                    connectivity of flow paths (8 lets water slip through diagonal gaps).
  order in ('raster', 'rim_first')   fill order of the reservoir: plain raster, or rim-colour cells before the core.
Ties in flow distance are broken by raster order of the droplets.
"""

from collections import Counter, deque


def _roles(train):
    """Induce (mover, ground, container colour set) from the cells the training pairs change; None if inconsistent.
    Every changed cell is either a captured droplet (mover -> ground) or a reservoir cell (container -> mover), so
    the mover is the one colour that is both removed and written."""
    changes = set()
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        changes |= {(v, go[r][c]) for r, row in enumerate(gi) for c, v in enumerate(row) if go[r][c] != v}
    movers = {w for _, w in changes} & {v for v, _ in changes}
    if len(movers) != 1:
        return None
    mover = movers.pop()
    grounds = {w for v, w in changes if v == mover}
    containers = frozenset(v for v, w in changes if w == mover)
    if len(grounds) != 1 or not containers or len(changes) != len(containers) + 1:
        return None
    return mover, grounds.pop(), containers


def _flow_distance(g, sources, passable, conn):
    """Multi-source BFS from the reservoir through passable cells; returns {cell: steps}."""
    H, W = len(g), len(g[0])
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1))
    if conn == 8:
        steps += ((1, 1), (1, -1), (-1, 1), (-1, -1))
    dist = {s: 0 for s in sources}
    dq = deque(sources)
    while dq:
        y, x = dq.popleft()
        for dy, dx in steps:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in dist and g[ny][nx] in passable:
                dist[(ny, nx)] = dist[(y, x)] + 1
                dq.append((ny, nx))
    return dist


def _make(mover, bg, containers, conn, order):
    def fn(g):
        H, W = len(g), len(g[0])
        res = [(r, c) for r in range(H) for c in range(W) if g[r][c] in containers]
        if not res:
            return [row[:] for row in g]
        if order == "rim_first":
            rim = Counter(g[r][c] for r, c in res).most_common(1)[0][0]
            res.sort(key=lambda rc: (g[rc[0]][rc[1]] != rim, rc))
        dist = _flow_distance(g, res, {bg, mover}, conn)
        drops = sorted((d, rc) for rc, d in dist.items() if g[rc[0]][rc[1]] == mover)
        caught = [rc for _, rc in drops[:len(res)]]
        out = [row[:] for row in g]
        for r, c in caught:
            out[r][c] = bg
        for r, c in res[:len(caught)]:
            out[r][c] = mover
        return out
    return fn


def fam_catchment(train):
    roles = _roles(train)
    if roles is None:
        return
    mover, bg, containers = roles
    for conn in (4, 8):
        for order in ("raster", "rim_first"):
            fn = _make(mover, bg, containers, conn, order)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("hydrology:catchment[conn=%d,order=%s]" % (conn, order), 3, fn)


FAMILIES = (fam_catchment,)
