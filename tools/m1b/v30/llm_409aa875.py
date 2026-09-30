"""Family for 409aa875 -- ballistics: fixed-range fire.

Every small object that is an *arrowhead* (a shape mirror-symmetric about an axis through a unique extreme
cell, the tip) fires a shot along its heading (one of the 8 compass directions); the shot lands exactly R
cells beyond the tip (R induced).  Landing on empty ground leaves a crater of the shot colour; a point hit
by several shots at once (crossfire) gets the crossfire colour; a shot landing on an object paints the
whole object (a hit).  Shots are fired simultaneously from the input state; off-grid shots vanish.
Parameters: background = most common colour; R in 1..max(H,W); shot colour and crossfire colour are
constants induced from the training outputs.
"""
from collections import Counter

DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _objects(g, bg):
    H, W = len(g), len(g[0])
    seen, objs = set(), []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or (i, j) in seen:
                continue
            comp, st = [], [(i, j)]
            seen.add((i, j))
            while st:
                a, b = st.pop()
                comp.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] != bg:
                            seen.add((x, y))
                            st.append((x, y))
            objs.append(comp)
    return objs


def _reflect(cell, tip, d):
    """Mirror `cell` across the line through `tip` with direction d (8-direction lines only)."""
    r, c = cell[0] - tip[0], cell[1] - tip[1]
    if d[1] == 0:            # vertical axis
        return (tip[0] + r, tip[1] - c)
    if d[0] == 0:            # horizontal axis
        return (tip[0] - r, tip[1] + c)
    if d[0] == d[1]:         # main diagonal
        return (tip[0] + c, tip[1] + r)
    return (tip[0] - c, tip[1] - r)  # anti-diagonal


def _heading(comp):
    """Return (tip, direction) if the object is an arrowhead with exactly one heading, else None."""
    if len(comp) < 2:
        return None
    s = set(comp)
    found = []
    for d in DIRS:
        proj = [p[0] * d[0] + p[1] * d[1] for p in comp]
        m = max(proj)
        tips = [p for p, v in zip(comp, proj) if v == m]
        if len(tips) != 1:
            continue
        tip = tips[0]
        if all(_reflect(p, tip, d) in s for p in comp):
            found.append((tip, d))
    return found[0] if len(found) == 1 else None


def _shots(g, R):
    """Landing counts per cell and the object map of the input."""
    H, W = len(g), len(g[0])
    bg = _bg(g)
    objs = _objects(g, bg)
    owner = {}
    for k, comp in enumerate(objs):
        for p in comp:
            owner[p] = k
    land = Counter()
    for comp in objs:
        h = _heading(comp)
        if h is None:
            continue
        (tr, tc), (dr, dc) = h
        x, y = tr + R * dr, tc + R * dc
        if 0 <= x < H and 0 <= y < W:
            land[(x, y)] += 1
    return bg, objs, owner, land


def _fire(g, R, shot, cross):
    bg, objs, owner, land = _shots(g, R)
    out = [row[:] for row in g]
    for (x, y), n in land.items():
        col = shot if n == 1 else cross
        if (x, y) in owner:
            for p in objs[owner[(x, y)]]:
                out[p[0]][p[1]] = col
        else:
            out[x][y] = col
    return out


def fam_fixed_range_fire(train):
    maxR = max(max(len(p["input"]), len(p["input"][0])) for p in train)
    for R in range(1, maxR + 1):
        shot_cols, cross_cols, ok = set(), set(), True
        for p in train:
            gi, go = p["input"], p["output"]
            if len(gi) != len(go) or len(gi[0]) != len(go[0]):
                return
            _, _, _, land = _shots(gi, R)
            if not land:
                ok = False
                break
            for (x, y), n in land.items():
                (shot_cols if n == 1 else cross_cols).add(go[x][y])
        if not ok or len(shot_cols) != 1 or len(cross_cols) > 1:
            continue
        shot = next(iter(shot_cols))
        cross = next(iter(cross_cols)) if cross_cols else shot
        fn = lambda g, R=R, s=shot, c=cross: _fire(g, R, s, c)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("ballistics:fixed_range_fire[range=%d,shot=%d,crossfire=%d]" % (R, shot, cross), 3, fn)
            return


FAMILIES = (fam_fixed_range_fire,)
