"""Family for ARC task b9e38dc0 -- concept: SPOTLIGHT (optics: a lamp inside a reflector housing).

A lamp (the fill colour) sits at the closed end of a housing drawn as an open 8-connected wall curve (the vessel).
Its light fills the housing and leaves through the mouth as a beam:

  * the beam's edges continue the housing's flare -- each wall end (a "tip": a wall cell with exactly one wall
    neighbour) is extrapolated outward to the grid border by repeating its last wall step pattern (the smallest
    period p <= P whose last 2p steps are p-periodic; otherwise the last step), exactly like the rim of a
    reflector defines the cone of its beam;
  * the lit area is everything 4-reachable from the lamp through background inside the housing + extended rim;
  * light travels straight along the beam axis (the mean direction of the two extrapolated rims), so every foreign
    object touched by the light casts a straight shadow forward along the axis -- shadowed cells stay unlit.

Roles (no fixed colours): background = most common colour; housing = most common non-background colour; lamp /
fill = the other colour with most cells inside the housing's bounding box; obstacles = every remaining colour.
Induced parameter (small finite domain): P in {1, 2, 3} -- the longest rim-step period recognised.
"""
from collections import Counter

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
N8 = N4 + DIAG


def _trace(tip, wall, n):
    """Walk along the wall curve from its tip (orthogonal neighbours preferred), at most n cells."""
    path, seen = [tip], {tip}
    while len(path) < n:
        r, c = path[-1]
        nxt = [(r + dr, c + dc) for dr, dc in N8 if (r + dr, c + dc) in wall and (r + dr, c + dc) not in seen]
        if not nxt:
            break
        path.append(nxt[0])
        seen.add(nxt[0])
    return path


def _rim_steps(tip, wall, P):
    """The step pattern (one period) by which the rim keeps going beyond the tip."""
    path = _trace(tip, wall, 2 * P + 1)[::-1]            # far end ... tip
    steps = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(path, path[1:])]
    if not steps:
        return None
    for p in range(1, P + 1):
        if len(steps) >= 2 * p and all(steps[-i] == steps[-i - p] for i in range(1, p + 1)):
            return steps[-p:]
    return steps[-1:]


def _spotlight(g, P):
    H, W = len(g), len(g[0])
    cnt = Counter(v for row in g for v in row)
    bg = cnt.most_common(1)[0][0]
    others = [c for c, _ in cnt.most_common() if c != bg]
    if len(others) < 2:
        return None
    wallc = others[0]
    wall = {(r, c) for r in range(H) for c in range(W) if g[r][c] == wallc}
    rs = [r for r, _ in wall]
    cs = [c for _, c in wall]
    inside = Counter(g[r][c] for r in range(min(rs), max(rs) + 1) for c in range(min(cs), max(cs) + 1)
                     if g[r][c] not in (bg, wallc))
    if not inside:
        return None
    top = inside.most_common(2)
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    lamp = top[0][0]

    tips = [p for p in wall if sum((p[0] + dr, p[1] + dc) in wall for dr, dc in N8) == 1]
    if len(tips) != 2:
        return None
    virtual, axis = set(), [0, 0]
    for tip in tips:
        pat = _rim_steps(tip, wall, P)
        if pat is None:
            return None
        axis[0] += sum(s[0] for s in pat) / len(pat)
        axis[1] += sum(s[1] for s in pat) / len(pat)
        r, c, k = tip[0], tip[1], 0
        while True:
            dr, dc = pat[k % len(pat)]
            r, c, k = r + dr, c + dc, k + 1
            if not (0 <= r < H and 0 <= c < W):
                break
            virtual.add((r, c))
    if abs(axis[0]) == abs(axis[1]):
        return None
    d = (1 if axis[0] > 0 else -1, 0) if abs(axis[0]) > abs(axis[1]) else (0, 1 if axis[1] > 0 else -1)

    # light: flood from the lamp through background, bounded by housing, extended rim and objects
    lit = {(r, c) for r in range(H) for c in range(W) if g[r][c] == lamp}
    stack = list(lit)
    while stack:
        r, c = stack.pop()
        for dr, dc in N4:
            q = (r + dr, c + dc)
            if 0 <= q[0] < H and 0 <= q[1] < W and q not in lit and q not in virtual and g[q[0]][q[1]] == bg:
                lit.add(q)
                stack.append(q)

    # shadows: every obstacle touched by the light shades the cells straight behind it along the axis
    obst = {(r, c) for r in range(H) for c in range(W) if g[r][c] not in (bg, wallc, lamp)}
    shade = set()
    for (r, c) in obst:
        if not any((r + dr, c + dc) in lit for dr, dc in N4):
            continue
        q = (r + d[0], c + d[1])
        while q in lit or q in obst:
            if q in lit:
                shade.add(q)
            q = (q[0] + d[0], q[1] + d[1])

    out = [row[:] for row in g]
    for (r, c) in lit - shade:
        out[r][c] = lamp
    return out


def fam_spotlight(train):
    for P in (1, 2, 3):
        fn = (lambda P: lambda g: _spotlight(g, P))(P)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("optics:spotlight[P=%d]" % P, 3, fn)
            return


FAMILIES = (fam_spotlight,)
