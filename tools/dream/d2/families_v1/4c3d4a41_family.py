"""Family for 4c3d4a41 -- mechanics: PIN TUMBLER (a key is inserted into a lock).

Concept: a toothed "key" (base bar + teeth of different heights) lies outside a walled "lock" (the largest
object, a rectangular frame).  The key slides straight into the lock along the axis on which it lies, to the
position where its teeth line up with the lock's pin stacks (columns of stuff hanging from the far wall).
Each tooth lifts the pin stack above it: the stack rises until it sits just on the tooth, and whatever is
pushed past the inner face of the far wall is lost.  The key leaves its original place.

Everything is found per input by roles: background = most common colour, lock = largest non-background
object (by bounding-box area), key = every non-background cell outside the lock's bounding box.  The
insertion direction and the side the teeth face are read from the geometry (the key's base is its widest end
row), by trying the 8 grid symmetries and keeping the one that puts the key left of the lock with teeth up.
Induced parameter (finite domain): whether the key is moved or copied into the lock {move, copy}.
"""
from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and not seen[r][c]:
                stack, cells = [(r, c)], []
                seen[r][c] = True
                while stack:
                    y, x = stack.pop()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                comps.append(cells)
    return comps


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


# ---- the 8 grid symmetries as (transpose, flip_rows, flip_cols) with exact inverses ----
def _fwd(g, t, fr, fc):
    if t:
        g = [list(r) for r in zip(*g)]
    if fr:
        g = g[::-1]
    if fc:
        g = [r[::-1] for r in g]
    return [list(r) for r in g]


def _inv(g, t, fr, fc):
    if fc:
        g = [r[::-1] for r in g]
    if fr:
        g = g[::-1]
    if t:
        g = [list(r) for r in zip(*g)]
    return [list(r) for r in g]


_SYMS = [(t, fr, fc) for t in (0, 1) for fr in (0, 1) for fc in (0, 1)]


def _canonical(g, bg, mode):
    """Key left of the lock, teeth pointing up, slides right.  Returns output grid or None."""
    comps = _components(g, bg)
    if len(comps) < 2:
        return None
    lock = max(comps, key=lambda cs: ((lambda b: (b[1] - b[0] + 1) * (b[3] - b[2] + 1))(_bbox(cs)), len(cs)))
    r0, r1, c0, c1 = _bbox(lock)
    if r1 - r0 < 2 or c1 - c0 < 2:
        return None
    H, W = len(g), len(g[0])
    key = [(r, c) for r in range(H) for c in range(W)
           if g[r][c] != bg and not (r0 <= r <= r1 and c0 <= c <= c1)]
    if not key:
        return None
    kr0, kr1, kc0, kc1 = _bbox(key)
    # key must lie entirely on the left, within the lock's interior rows
    if kc1 >= c0 or kr0 <= r0 or kr1 >= r1:
        return None
    # the base (widest end row) is at the bottom -> teeth point up
    top_n = sum(1 for r, _ in key if r == kr0)
    bot_n = sum(1 for r, _ in key if r == kr1)
    if kr1 > kr0 and not bot_n > top_n:
        return None
    teeth = {c for r, c in key if r < kr1} or {c for _, c in key}
    pins = {c for c in range(c0 + 1, c1) if any(g[r][c] != bg for r in range(r0 + 1, r1))}
    # slide distance: teeth line up with the pin stacks (best agreement), key stays inside the lock
    best = None
    for d in range(c0 + 1 - kc0, c1 - kc1):
        sh = {c + d for c in teeth}
        score = (len(sh & pins), -len(sh ^ pins), -d)
        if best is None or score > best[0]:
            best = (score, d)
    if best is None:
        return None
    d = best[1]
    out = [row[:] for row in g]
    if mode == 'move':
        for r, c in key:
            out[r][c] = bg
    bycol = {}
    for r, c in key:
        bycol.setdefault(c, []).append(r)
    for kc, rows in bycol.items():
        c = kc + d
        top, bottom = min(rows), max(rows)
        stack = [(r, g[r][c]) for r in range(r0 + 1, bottom + 1) if g[r][c] != bg]
        lift = max(0, max((r for r, _ in stack), default=r0) - top + 1)
        for r in range(r0 + 1, bottom + 1):
            out[r][c] = bg
        for r, v in stack:
            if r - lift >= r0 + 1:          # pushed past the far wall -> lost
                out[r - lift][c] = v
        for r in rows:
            out[r][c] = g[r][kc]
    return out


def _solve(g, mode):
    bg = _bg(g)
    for t, fr, fc in _SYMS:
        o = _canonical(_fwd(g, t, fr, fc), bg, mode)
        if o is not None:
            return _inv(o, t, fr, fc)
    return None


def fam_pin_tumbler(train):
    for mode in ('move', 'copy'):
        fn = (lambda m: (lambda g: _solve(g, m)))(mode)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("mechanics:pin_tumbler[key=%s,lift=clip]" % mode, 3, fn)
            return


FAMILIES = (fam_pin_tumbler,)
