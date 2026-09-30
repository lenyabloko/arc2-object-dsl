"""Group family for g06 "paths between two points".

Concept: line-of-sight homing navigation (robotics, the "Bug"/TangentBug family of planners).
A walker leaves the SOURCE object and navigates to GOAL objects, painting the cells its body sweeps:
  1. line of sight: whenever an unvisited goal is visible along a clear straight ray (in the move set),
     travel straight to the nearest one until contact, and step onto it;
  2. after reaching a goal the walker continues only to further goals in line of sight (a waypoint tour),
     otherwise it stops;
  3. while no goal is in sight it wanders: an elongated source launches it along its own axis and it keeps
     that heading until blocked (inertia); otherwise it steps greedily toward the goal's contact zone
     (per-axis sign of the gap, keeping its current heading while that still makes progress, never reversing).
Body = k x k square, k = thickness of the source. Everything (roles, colours, move set) is induced per task.
"""
from collections import Counter

DIRS4 = ((-1, 0), (0, 1), (1, 0), (0, -1))
DIRS8 = DIRS4 + ((-1, 1), (1, 1), (1, -1), (-1, -1))


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, colour):
    H, W = len(g), len(g[0])
    seen, comps = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == colour and (r, c) not in seen:
                stack, comp = [(r, c)], []
                seen.add((r, c))
                while stack:
                    x, y = stack.pop()
                    comp.append((x, y))
                    for dx, dy in DIRS4:
                        a, b = x + dx, y + dy
                        if 0 <= a < H and 0 <= b < W and (a, b) not in seen and g[a][b] == colour:
                            seen.add((a, b))
                            stack.append((a, b))
                comps.append(comp)
    return comps


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def _gap(lo, hi, g0, g1):
    """signed distance from span [lo,hi] to span [g0,g1] (0 if they overlap)"""
    if hi < g0:
        return g0 - hi
    if lo > g1:
        return g1 - lo
    return 0


def _sgn(x):
    return (x > 0) - (x < 0)


def _walk(g, bg, src, goals, M, paint):
    """Run the homing walker; return painted grid or None if it never reaches a goal."""
    H, W = len(g), len(g[0])
    lab = [[None if v == bg else -1 for v in row] for row in g]
    gboxes = []
    for i, comp in enumerate(goals):
        for r, c in comp:
            lab[r][c] = i
        gboxes.append(_bbox(comp))
    r0, c0, r1, c1 = _bbox(src)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if len(src) != h * w:
        return None
    k = min(h, w)
    dirs = DIRS4 if M == 4 else DIRS8
    slack = 1 if M == 8 else 0
    if h == w:
        starts = [((r0, c0), None)]
    elif h > w:   # vertical source: launch from either end along its axis
        starts = [((r0, c0), (-1, 0)), ((r1 - k + 1, c0), (1, 0))]
    else:
        starts = [((r0, c0), (0, -1)), ((r0, c1 - k + 1), (0, 1))]

    def fp(br, bc):
        return [(br + i, bc + j) for i in range(k) for j in range(k)]

    def free(br, bc, own=()):
        return all(0 <= x < H and 0 <= y < W and (lab[x][y] is None or (x, y) in own) for x, y in fp(br, bc))

    best = None
    for body, heading in starts:
        launched = heading is not None
        trail, visited, seen_states = [], set(), set()
        for _ in range(4 * H * W + 8):
            if body is None:
                break
            br, bc = body
            own = set(fp(br, bc))   # the walker's own current footprint never blocks it
            # 1. line of sight to an unvisited goal
            sight = None
            for oi, (dr, dc) in enumerate(dirs):
                s = 1
                while True:
                    cells = fp(br + s * dr, bc + s * dc)
                    if any(not (0 <= x < H and 0 <= y < W) for x, y in cells):
                        break
                    hits = {lab[x][y] for x, y in cells if lab[x][y] is not None and (x, y) not in own}
                    if hits:
                        if len(hits) == 1:
                            gi = hits.pop()
                            if gi >= 0 and gi not in visited:
                                if sight is None or s - 1 < sight[0]:
                                    sight = (s - 1, oi, (dr, dc), gi)
                        break
                    s += 1
            if sight is not None:
                dist, _, (dr, dc), gi = sight
                for s in range(1, dist + 1):
                    trail.extend(fp(br + s * dr, bc + s * dc))
                visited.add(gi)
                gr0, gc0, gr1, gc1 = gboxes[gi]
                body = (gr0, gc0) if (gr1 - gr0 + 1 == k and gc1 - gc0 + 1 == k) else None
                heading, launched = (dr, dc), False
                if len(visited) == len(goals):
                    body = None
                continue
            if visited:          # tour ends when no further goal is in sight
                break
            # 3. wander
            if launched and free(br + heading[0], bc + heading[1], own):
                body = (br + heading[0], bc + heading[1])
                trail.extend(fp(*body))
                continue
            launched = False
            gi = min((i for i in range(len(goals)) if i not in visited),
                     key=lambda i: abs(_gap(br, br + k - 1, gboxes[i][0], gboxes[i][2]))
                     + abs(_gap(bc, bc + k - 1, gboxes[i][1], gboxes[i][3])))
            gr = _gap(br, br + k - 1, gboxes[gi][0], gboxes[gi][2])
            gc = _gap(bc, bc + k - 1, gboxes[gi][1], gboxes[gi][3])
            des = (_sgn(gr) if abs(gr) > slack else 0, _sgn(gc) if abs(gc) > slack else 0)
            gaps = (abs(gr), abs(gc))
            rev = (-heading[0], -heading[1]) if heading else None
            cands = []
            for m in dirs:
                if m == rev:
                    continue
                if not all(m[i] == 0 or m[i] == des[i] for i in (0, 1)):
                    continue
                matched = sum(1 for i in (0, 1) if m[i] != 0)
                if matched == 0 or not free(br + m[0], bc + m[1], own):
                    continue
                cands.append((-matched, m != heading, -sum(gaps[i] for i in (0, 1) if m[i]), m))
            if not cands:
                break
            m = min(cands)[3]
            state = (body, m)
            if state in seen_states:
                break
            seen_states.add(state)
            heading = m
            body = (br + m[0], bc + m[1])
            trail.extend(fp(*body))
        if visited and (best is None or len(set(trail)) < len(best)):
            best = set(trail)
    if best is None:
        return None
    out = [row[:] for row in g]
    for x, y in best:
        if g[x][y] == bg:
            out[x][y] = paint
    return out


def fam_homing(train):
    # quick shape / diff checks: output = input with some background cells painted one colour
    paint = None
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
        bg = _bg(a)
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    if x != bg or (paint is not None and y != paint):
                        return
                    paint = y
    if paint is None:
        return
    infos = []
    for p in train:
        a = p["input"]
        bg = _bg(a)
        cols = {v for row in a for v in row} - {bg}
        infos.append((a, bg, cols, {c: _components(a, c) for c in cols}))
    common = set.intersection(*(i[2] for i in infos))
    srcs = [c for c in sorted(common) if all(len(i[3][c]) == 1 for i in infos)]
    for M in (4, 8):
        for sc in srcs:
            for gc in sorted(common - {sc}):
                pc = sc if paint == sc else paint

                def fn(grid, sc=sc, gc=gc, M=M, pc=pc):
                    bg = _bg(grid)
                    s = _components(grid, sc)
                    goals = _components(grid, gc)
                    if len(s) != 1 or not goals:
                        return None
                    return _walk(grid, bg, s[0], goals, M, pc)

                if all(fn(p["input"]) == p["output"] for p in train):
                    role = "src" if paint == sc else "const"
                    yield (f"robotics:line_of_sight_homing[src={sc},goal={gc},moves={M},paint={role}:{paint}]", 3, fn)
                    return


FAMILIES = (fam_homing,)
