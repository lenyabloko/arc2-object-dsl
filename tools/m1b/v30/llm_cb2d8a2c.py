"""Family for ARC task cb2d8a2c -- concept: CONFIGURATION SPACE (robotics: obstacles grown by a clearance radius,
then a Bug-style planner drives a point robot across the free space).

Reading of the task
-------------------
A single "robot" cell sits on one grid edge.  Barriers (straight walls) hang off the edges; each wall carries a few
hazard marks (a second colour) and the NUMBER of marks is the safety clearance that wall demands.  Planning in
configuration space: every wall is dilated by its clearance (Chebyshev / square structuring element), and the robot
travels from its edge straight toward the opposite edge.  Whenever the next step would enter a grown obstacle it
slides sideways along the obstacle's boundary toward the side where the obstacle ends (the shorter way round -- the
other side is sealed by the grid edge) until the forward cell is free, then resumes its heading (Bug-0 behaviour).
The trace is painted in the robot's colour; the hazard marks are painted over in the wall colour.

How everything is found (no task constants):
  * background B = most frequent colour of the input.
  * robot colour P, mark colour M, wall colour W are induced from the training diffs: cells that change B->P are the
    trace, cells that change M->W are painted-over marks (M disappears from the output).
  * robot = the single P cell touching a grid edge; heading = inward normal of that edge.
  * obstacles = 4-connected components of non-background, non-robot cells; clearance = a*marks + b.

Parameters (declared finite domain, induced from train; every exact fit is yielded, first fit first):
  metric    in {chebyshev, manhattan}      shape of the dilation (structuring element).
  a         in {1, 0, 2}                   clearance per hazard mark.
  b         in {0, 1, 2}                   constant clearance offset.
"""

from collections import Counter

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _induce_colours(train):
    """Return (P, M, W) from the training diffs, or None if inconsistent."""
    P = None
    MW = {}
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        B = _bg(a)
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x == y:
                    continue
                if x == B:
                    if P is not None and P != y:
                        return None
                    P = y
                else:
                    if MW.get(x, y) != y:
                        return None
                    MW[x] = y
    if P is None or len(MW) > 1:
        return None
    if MW:
        (M, W), = MW.items()
    else:
        M = W = None
    return P, M, W


def _components(g, cellset):
    """4-connected components of the given cell set."""
    seen, comps = set(), []
    for s in cellset:
        if s in seen:
            continue
        seen.add(s)
        stack, comp = [s], []
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy, dx in DIRS:
                n = (y + dy, x + dx)
                if n in cellset and n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def _plan(g, P, M, W, metric, a, b):
    H, Wd = len(g), len(g[0])
    B = _bg(g)
    robots = [(r, c) for r in range(H) for c in range(Wd) if g[r][c] == P]
    if len(robots) != 1:
        return None
    sr, sc = robots[0]
    normals = []
    if sr == 0: normals.append((1, 0))
    if sr == H - 1: normals.append((-1, 0))
    if sc == 0: normals.append((0, 1))
    if sc == Wd - 1: normals.append((0, -1))
    if len(normals) != 1:
        return None
    d = normals[0]

    # configuration-space obstacles
    solid = {(r, c) for r in range(H) for c in range(Wd) if g[r][c] not in (B, P)}
    blocked = set()
    for comp in _components(g, solid):
        marks = sum(1 for (r, c) in comp if g[r][c] == M) if M is not None else 0
        k = a * marks + b
        for (r, c) in comp:
            for dr in range(-k, k + 1):
                for dc in range(-k, k + 1):
                    if metric == "manhattan" and abs(dr) + abs(dc) > k:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < Wd:
                        blocked.add((rr, cc))
    inside = lambda y, x: 0 <= y < H and 0 <= x < Wd
    if (sr, sc) in blocked:
        return None

    # Bug-0 planner: go straight; when the next step is blocked, slide along the obstacle the short way round.
    path = [(sr, sc)]
    y, x = sr, sc
    for _ in range(4 * H * Wd):
        ny, nx = y + d[0], x + d[1]
        if not inside(ny, nx):
            break
        if (ny, nx) not in blocked:
            y, x = ny, nx
            path.append((y, x))
            continue
        best = None
        for s in ((d[1], d[0]), (-d[1], -d[0])):
            cy, cx, steps, ok = y, x, [], False
            while True:
                cy, cx = cy + s[0], cx + s[1]
                if not inside(cy, cx) or (cy, cx) in blocked:
                    break
                steps.append((cy, cx))
                fy, fx = cy + d[0], cx + d[1]
                if not inside(fy, fx) or (fy, fx) not in blocked:
                    ok = True
                    break
            if ok and (best is None or len(steps) < len(best)):
                best = steps
        if best is None:
            return None
        path.extend(best)
        y, x = best[-1]
    else:
        return None

    out = [[(W if (M is not None and v == M) else v) for v in row] for row in g]
    for (r, c) in path:
        out[r][c] = P
    return out


def fam_configuration_space(train):
    cols = _induce_colours(train)
    if cols is None:
        return
    P, M, W = cols
    for metric in ("chebyshev", "manhattan"):
        for a in (1, 0, 2):
            for b in (0, 1, 2):
                def fn(g, metric=metric, a=a, b=b):
                    return _plan(g, P, M, W, metric, a, b)
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("robotics:configuration_space[metric=%s,clearance=%d*marks+%d]" % (metric, a, b), 3, fn)


FAMILIES = (fam_configuration_space,)
