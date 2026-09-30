"""Family for 7ed72f31: optics:mirror_reflection.

Each object is a shape glued to a "mirror" (cells of one role colour).  The mirror's fixed-point set
decides the isometry: a single mirror cell is a point mirror (central inversion through it), a straight
mirror segment (row, column or diagonal) is a plane mirror (axial reflection across its line).  The
mirror image of the shape is painted onto the background; everything in the input stays.

Induced parameters:
  bg      - most frequent colour of each grid (role).
  mirror  - the colour shared by every multi-colour object in the training inputs (role, induced).
  conn    - object connectivity, from the finite domain {8, 4}.
"""
from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg, conn):
    H, W = len(g), len(g[0])
    if conn == 8:
        nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
    else:
        nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            stack, comp = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] != bg:
                        seen[yy][xx] = True
                        stack.append((yy, xx))
            comps.append(comp)
    return comps


# The candidate involutions of the square lattice, written on doubled coordinates about a centre
# (cy2, cx2) = 2*centre.  Each maps (y, x) -> (y', x').  Ordered by the size of their fixed set:
# the point mirror fixes one point, axial mirrors fix a line.
def _reflector(M):
    """Return the lattice isometry whose fixed-point set is the affine hull of mirror cells M."""
    if len(M) == 1:
        (y0, x0), = M
        return lambda y, x: (2 * y0 - y, 2 * x0 - x)          # point mirror (central inversion)
    ys = {y for y, _ in M}
    xs = {x for _, x in M}
    if len(ys) == 1:
        y0 = next(iter(ys))
        return lambda y, x: (2 * y0 - y, x)                    # horizontal plane mirror
    if len(xs) == 1:
        x0 = next(iter(xs))
        return lambda y, x: (y, 2 * x0 - x)                    # vertical plane mirror
    d = {y - x for y, x in M}
    if len(d) == 1:
        k = next(iter(d))
        return lambda y, x: (x + k, y - k)                     # main-diagonal plane mirror
    s = {y + x for y, x in M}
    if len(s) == 1:
        k = next(iter(s))
        return lambda y, x: (k - x, k - y)                     # anti-diagonal plane mirror
    return None                                                # not a flat mirror


def _make(mirror, conn):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        for comp in _components(g, bg, conn):
            M = [p for p in comp if g[p[0]][p[1]] == mirror]
            S = [p for p in comp if g[p[0]][p[1]] != mirror]
            if not M or not S:
                continue
            f = _reflector(M)
            if f is None:
                continue
            for y, x in S:
                yy, xx = f(y, x)
                if 0 <= yy < H and 0 <= xx < W and out[yy][xx] == bg:
                    out[yy][xx] = g[y][x]
        return out
    return fn


def _mirror_colour(train, conn):
    shared = None
    for p in train:
        g = p["input"]
        bg = _bg(g)
        for comp in _components(g, bg, conn):
            cols = {g[y][x] for y, x in comp}
            if len(cols) < 2:
                continue
            shared = cols if shared is None else shared & cols
    return shared or set()


def fam_mirror_reflection(train):
    for conn in (8, 4):
        for mirror in sorted(_mirror_colour(train, conn)):
            fn = _make(mirror, conn)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("optics:mirror_reflection[mirror=role-shared colour,conn=%d]" % conn, 3, fn)
                return


FAMILIES = (fam_mirror_reflection,)
