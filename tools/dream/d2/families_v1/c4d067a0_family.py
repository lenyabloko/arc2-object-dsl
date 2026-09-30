"""c4d067a0 -- drafting:pantograph.

A pantograph copies a small drawing at a larger scale.  The grid holds a small key (a lattice of 1-cell
squares at some pitch q) and a partially traced enlargement of it (a lattice of s x s squares at pitch p).
The traced squares fix the registration of the copy (which key cell they reproduce); the pantograph then
finishes the enlargement: every non-background key cell (i, j) becomes an s x s square at
origin + (i*p, j*p).  Scale s, pitch p, key pitch q and registration are all read off the input grid.
"""
from collections import Counter
from math import gcd


def _background(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    """4-connected monochrome components as (color, r0, c0, h, w, solid)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            stack = [(r, c)]
            seen[r][c] = True
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            ys = [y for y, _ in cells]
            xs = [x for _, x in cells]
            r0, c0 = min(ys), min(xs)
            h, w = max(ys) - r0 + 1, max(xs) - c0 + 1
            out.append((col, r0, c0, h, w, len(cells) == h * w))
    return out


def _lattice_pitch(items):
    """gcd of all positive coordinate differences (both axes) of the squares' top-left corners."""
    g = 0
    for axis in (1, 2):
        vals = sorted({it[axis] for it in items})
        for a, b in zip(vals, vals[1:]):
            g = gcd(g, b - a)
    return g


def _pantograph(g, tie):
    bg = _background(g)
    comps = _components(g, bg)
    if not comps or not all(solid and h == w for _, _, _, h, w, solid in comps):
        return None
    sizes = sorted({h for _, _, _, h, _, _ in comps})
    if len(sizes) != 2:
        return None
    a, s = sizes                                   # key square size, enlargement square size
    key = [cmp for cmp in comps if cmp[3] == a]
    big = [cmp for cmp in comps if cmp[3] == s]
    q = _lattice_pitch(key)
    p = _lattice_pitch(big)
    if q <= 0 or p < s:
        return None
    kr0 = min(k[1] for k in key)
    kc0 = min(k[2] for k in key)
    cells = {}
    for col, r, c, _, _, _ in key:
        if (r - kr0) % q or (c - kc0) % q:
            return None
        cells[((r - kr0) // q, (c - kc0) // q)] = col
    H, W = len(g), len(g[0])
    col0, R, C = big[0][0], big[0][1], big[0][2]
    results = []
    for (i, j), kc in sorted(cells.items()):      # registration: which key cell the first traced square copies
        if kc != col0:
            continue
        R0, C0 = R - i * p, C - j * p
        ok = True
        for col, rb, cb, _, _, _ in big:
            if (rb - R0) % p or (cb - C0) % p or cells.get(((rb - R0) // p, (cb - C0) // p)) != col:
                ok = False
                break
        if not ok:
            continue
        out = [row[:] for row in g]
        for (ii, jj), kcol in cells.items():
            top, left = R0 + ii * p, C0 + jj * p
            if top < 0 or left < 0 or top + s > H or left + s > W:
                ok = False
                break
            for y in range(top, top + s):
                for x in range(left, left + s):
                    if out[y][x] not in (bg, kcol):
                        ok = False
                    out[y][x] = kcol
        if ok:
            results.append(out)
    if not results or (tie == "unique" and len(results) != 1):
        return None
    return results[0]


def fam_pantograph(train):
    for tie in ("unique", "first"):               # declared finite domain: registration tie-break
        fn = (lambda t: (lambda grid: _pantograph(grid, t)))(tie)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("drafting:pantograph[registration=%s]" % tie, 3, fn)
                return
        except Exception:
            continue


FAMILIES = (fam_pantograph,)
