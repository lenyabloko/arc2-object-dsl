CARD = "ba1aa698"
READING = ("The grid is a strip of framed panels showing one shape stepping by a constant offset from "
           "panel to panel; the output is the next panel, with the shape moved one more step.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _panels(g):
    """Split along full columns of the frame colour. Returns (frame, [(c0, c1)]) where c0..c1 is a
    panel interior column span, or None."""
    H, W = len(g), len(g[0])
    frame = g[0][0]
    if not all(x == frame for x in g[0]) or not all(x == frame for x in g[-1]):
        return None
    seps = [j for j in range(W) if all(g[i][j] == frame for i in range(H))]
    if len(seps) < 3 or seps[0] != 0 or seps[-1] != W - 1:
        return None
    spans = [(a + 1, b - 1) for a, b in zip(seps, seps[1:]) if b - a > 1]
    if len(spans) < 2:
        return None
    return frame, spans


def _bg(cells):
    cnt = {}
    for x in cells:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _shape(g, c0, c1, bg):
    H = len(g)
    pts = [(i - 1, j - c0, g[i][j]) for i in range(1, H - 1) for j in range(c0, c1 + 1) if g[i][j] != bg]
    if not pts:
        return None
    r0 = min(p[0] for p in pts)
    q0 = min(p[1] for p in pts)
    return (r0, q0), frozenset((a - r0, b - q0, v) for a, b, v in pts)


def _solve_h(g, extra):
    P = _panels(g)
    if P is None:
        return None
    frame, spans = P
    widths = {c1 - c0 for c0, c1 in spans}
    if len(widths) != 1:
        return None
    c0, c1 = spans[0]
    H = len(g)
    bg = _bg([g[i][j] for i in range(1, H - 1) for c0_, c1_ in spans for j in range(c0_, c1_ + 1)])
    shapes = [_shape(g, a, b, bg) for a, b in spans]
    if any(s is None for s in shapes):
        return None
    offs = [s[0] for s in shapes]
    steps = {(b[0] - a[0], b[1] - a[1]) for a, b in zip(offs, offs[1:])}
    if len(steps) != 1:
        return None
    dr, dc = steps.pop()
    dr += extra * (1 if dr > 0 else -1 if dr < 0 else 0)
    dc += extra * (1 if dc > 0 else -1 if dc < 0 else 0)
    (lr, lc), cells = offs[-1], shapes[-1][1]
    w = c1 - c0 + 1
    out = [[frame] * (w + 2) for _ in range(H)]
    for i in range(1, H - 1):
        for j in range(1, w + 1):
            out[i][j] = bg
    for a, b, v in cells:
        i, j = lr + dr + a + 1, lc + dc + b + 1
        if 1 <= i < H - 1 and 1 <= j <= w:
            out[i][j] = v
    return out


def _solve(g, extra=0):
    r = _solve_h(g, extra)
    if r is not None:
        return r
    r = _solve_h(_T(g), extra)
    return None if r is None else _T(r)


def _fits(fn, p):
    try:
        return fn(p["input"]) == p["output"]
    except Exception:
        return False


def fam(train):
    fn = lambda g: _solve(g, 0)
    nfit = sum(_fits(fn, p) for p in train)
    if nfit == len(train):
        yield ("next_panel_constant_step", 1, fn)
    elif nfit >= len(train) - 1 and len(train) >= 3:
        # Best attempt: one training pair (train[1]: steps 3,3 then an output step of 4) is not
        # explained by constant-step extrapolation; yield the rule as an explicitly approximate program.
        yield ("next_panel_constant_step_approx", 9, fn)


FAMILIES = [fam]
