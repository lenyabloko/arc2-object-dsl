"""Family for ARC task f560132c -- concept: JIGSAW ASSEMBLY (recreational geometry: a dissection puzzle).

Reading of the task
-------------------
The input scatters the loose pieces of a rectangular jigsaw on the table (background).  One piece carries the
"box-lid picture": a small kh x kw block of colours embedded in it (the key), a thumbnail of the finished puzzle
with one cell per piece.  Solving the puzzle means fitting all pieces (the key-carrying piece included, key cells
and any hole it encloses counted as part of it) into one gap-free rectangle, and painting every piece with the
colour the thumbnail shows at the piece's place in the picture.  Pieces may be turned on the table (rotations,
optionally flips); the key-carrying piece is the reference and keeps its orientation, which fixes the orientation
of the finished picture.

How everything is found (no task constants):
  * background = most frequent colour; pieces = 4-connected components of non-background cells (any colours),
                 background pockets fully enclosed by a piece belong to that piece (pieces are hole-free).
  * key        = the only multicolour piece; its non-body cells (body = its commonest colour) must fill their
                 bounding box exactly -> a kh x kw thumbnail; #pieces must equal kh*kw.
  * rectangle  = every H x W with H*W = total piece area; exact-cover backtracking (first empty cell in reading
                 order, every unused piece/orientation whose first cell lands there).
  * painting   = the thumbnail is a kh x kw downsampling of the finished picture: among all tilings and all
                 bijections pieces <-> key cells, keep the one whose painted picture agrees on the most cells with
                 the key upscaled (nearest neighbour) to H x W -- the assembly that best resembles the box-lid
                 picture (bijection optimised by a DP over subsets; ties keep the first in search order).

Parameters (declared finite domain, induced from train; first fit wins):
  group    in {rot, dih}           orientations a piece may take (4 rotations, or all 8 dihedral images).
  anchor   in {fixed, free}        whether the key-carrying piece keeps its input orientation.
"""

from collections import Counter


def _components(H, W, inside):
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or not inside(r, c):
                continue
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and inside(ny, nx):
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            out.append(cells)
    return out


def _pieces(g, bg):
    H, W = len(g), len(g[0])
    solid = [[v != bg for v in row] for row in g]
    for comp in _components(H, W, lambda r, c: g[r][c] == bg):          # enclosed pockets -> part of the piece
        if not any(y in (0, H - 1) or x in (0, W - 1) for y, x in comp):
            for y, x in comp:
                solid[y][x] = True
    return _components(H, W, lambda r, c: solid[r][c])


def _norm(cells):
    y0 = min(y for y, _ in cells)
    x0 = min(x for _, x in cells)
    return tuple(sorted((y - y0, x - x0) for y, x in cells))


def _orients(shape, group):
    res, cur = [], shape
    for _ in range(4):
        cur = _norm([(x, -y) for y, x in cur])                           # rotate 90 degrees
        for s in ((cur,) if group == "rot" else (cur, _norm([(y, -x) for y, x in cur]))):
            if s not in res:
                res.append(s)
    return res


def _key(g, piece):
    cnt = Counter(g[y][x] for y, x in piece)
    if len(cnt) < 2:
        return None
    body = cnt.most_common(1)[0][0]
    kc = [(y, x) for y, x in piece if g[y][x] != body]
    ys, xs = [y for y, _ in kc], [x for _, x in kc]
    h, w = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
    if h * w != len(kc) or h * w < 2:
        return None
    return [[g[y][x] for x in range(min(xs), max(xs) + 1)] for y in range(min(ys), max(ys) + 1)]


def _tilings(opts, H, W, limit=256):
    """Exact covers of an H x W rectangle, one orientation of every piece; yields placements (piece -> cells)."""
    n = len(opts)
    grid = [[-1] * W for _ in range(H)]
    # anchor offset: first cell in reading order of each orientation
    prep = [[(s, s[0]) for s in o] for o in opts]
    used = [False] * n
    found = []

    def first_empty(start):
        for i in range(start, H * W):
            if grid[i // W][i % W] < 0:
                return i
        return -1

    def rec(start, left):
        if len(found) >= limit:
            return
        if left == 0:
            found.append([row[:] for row in grid])
            return
        i = first_empty(start)
        r, c = divmod(i, W)
        for p in range(n):
            if used[p]:
                continue
            for s, (ay, ax) in prep[p]:
                oy, ox = r - ay, c - ax
                ok = True
                for y, x in s:
                    Y, X = y + oy, x + ox
                    if not (0 <= Y < H and 0 <= X < W) or grid[Y][X] >= 0:
                        ok = False
                        break
                if not ok:
                    continue
                for y, x in s:
                    grid[y + oy][x + ox] = p
                used[p] = True
                rec(i + 1, left - 1)
                used[p] = False
                for y, x in s:
                    grid[y + oy][x + ox] = -1

    rec(0, n)
    return found


def _assign(til, key, n):
    """Best bijection pieces -> key cells: maximise agreement of the painted picture with the key upscaled
    (nearest neighbour) to the rectangle.  Returns (score, colour_of_piece)."""
    H, W = len(til), len(til[0])
    kh, kw = len(key), len(key[0])
    ov = [[0] * (kh * kw) for _ in range(n)]
    for r in range(H):
        for c in range(W):
            ov[til[r][c]][(r * kh // H) * kw + c * kw // W] += 1
    best = {0: (0, ())}                                  # DP over pieces in order, mask of key cells used
    for p in range(n):
        nxt = {}
        for mask, (s, ch) in best.items():
            for k in range(kh * kw):
                if not mask >> k & 1:
                    m2, s2 = mask | 1 << k, s + ov[p][k]
                    if m2 not in nxt or s2 > nxt[m2][0]:
                        nxt[m2] = (s2, ch + (k,))
        best = nxt
    s, ch = best[(1 << (kh * kw)) - 1]
    return s, [key[k // kw][k % kw] for k in ch]


def _solve(g, group, anchor):
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]
    pieces = _pieces(g, bg)
    keyed = [(i, k) for i, k in ((i, _key(g, p)) for i, p in enumerate(pieces)) if k is not None]
    if len(keyed) != 1:
        return None
    ki, key = keyed[0]
    kh, kw = len(key), len(key[0])
    n = len(pieces)
    if n != kh * kw:
        return None
    shapes = [_norm(p) for p in pieces]
    opts = [([s] if (anchor == "fixed" and i == ki) else _orients(s, group)) for i, s in enumerate(shapes)]
    area = sum(len(s) for s in shapes)
    best, out = -1, None
    for H in range(1, area + 1):
        if area % H:
            continue
        W = area // H
        if any(all(max(y for y, _ in s) >= H or max(x for _, x in s) >= W for s in o) for o in opts):
            continue
        for til in _tilings(opts, H, W):
            score, colour = _assign(til, key, n)
            if score > best:
                best, out = score, [[colour[p] for p in row] for row in til]
    return out


def fam_jigsaw(train):
    for anchor in ("fixed", "free"):
        for group in ("rot", "dih"):
            def fn(g, group=group, anchor=anchor):
                return _solve(g, group, anchor)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("geometry:jigsaw[group=%s,anchor=%s]" % (group, anchor), 3, fn)
                return


FAMILIES = (fam_jigsaw,)
