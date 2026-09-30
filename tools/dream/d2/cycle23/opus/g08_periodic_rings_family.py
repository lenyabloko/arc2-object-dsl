"""g08 family: ripple wavefronts (wave physics) -- concentric rings continued with the period seen in the input.

Concept: "ripple wavefronts" (waves / Huygens): a source emits a train of wavefronts at a fixed period; in grid
metrics the wavefronts are concentric squares (Chebyshev / L-inf) or diamonds (Manhattan / L1).
Mechanism: the input shows the first few wavefronts (rings, possibly clipped by the grid border, with the source
possibly off-grid); every cell whose metric distance to the source falls on the same periodic schedule
(ring width w, period P, colour sequence) is painted, i.e. the ripple train is continued to the grid border.

Read from each input (not from training): source position (half-integer, may lie off-grid), innermost radius,
ring width w >= 1, period P > w, colour sequence = optional 1-ring head + repeating cycle (length <= #rings seen).
Induced from the task's training pairs, finite domains:
  metric    in ('linf', 'l1')
  direction in ('out', 'both')        -- continue only outward from the innermost ring, or also inward
  fill      in {keep} U {colours seen in training outputs}   -- colour given to non-ring cells
Background = most frequent input colour (fallback: second most frequent).

Group coverage: f8c80d96 fits.  fd4b2b02 does NOT fit and is not a ripple: its output is a diagonal chain of
L x T bars, each bar the mirror image of the previous one across the 45-degree line through its outer corner,
with colours swapped (a glide-reflection frieze along the four diagonals).  It needs a separate concept.
"""
from collections import Counter


def _bgs(g):
    mc = Counter(v for row in g for v in row).most_common(2)
    n = len(g) * len(g[0])                    # second colour is a background candidate only if it is large
    return [mc[0][0]] + [v for v, k in mc[1:] if 3 * k >= n]


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and not seen[r][c]:
                stack = [(r, c)]; seen[r][c] = True; cells = []
                while stack:
                    y, x = stack.pop(); cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] != bg:
                            seen[yy][xx] = True; stack.append((yy, xx))
                comps.append(cells)
    return comps


def _side_options(lo, hi, n, s):
    """True extents (low, high), high-low = s, of a ring whose visible extent along one axis is [lo, hi] in 0..n-1."""
    cl_lo, cl_hi = lo == 0, hi == n - 1
    if not cl_lo and not cl_hi:
        return [(lo, hi)] if hi - lo == s else []
    if not cl_lo:
        return [(lo, lo + s)] if lo + s >= hi else []
    if not cl_hi:
        return [(hi - s, hi)] if hi - s <= lo else []
    return [(a, a + s) for a in range(n - 1 - s, 1)]


def _dist_fn(metric, R2, C2):
    if metric == 'linf':
        par = R2 % 2                                   # R2, C2 share parity (square bbox of span s)
        return lambda r, c: (max(abs(2 * r - R2), abs(2 * c - C2)) - par) // 2
    return lambda r, c: (abs(2 * r - R2) + abs(2 * c - C2)) // 2


def _fit_rings(g, metric, max_cands=3000):
    """Describe g's non-background cells as complete concentric rings: (bg, dist, start, w, P, head, cycle)."""
    H, W = len(g), len(g[0])
    for bg in _bgs(g):
        S = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
        if not S:
            continue
        comps = _components(g, bg)
        if len(comps) > 40:
            continue
        boxes = []
        for cells in comps:
            rs = [y for y, _ in cells]; cs = [x for _, x in cells]
            boxes.append((min(rs), max(rs), min(cs), max(cs)))
        boxes.sort(key=lambda b: (b[1] - b[0] + 1) * (b[3] - b[2] + 1))
        rs = [y for y, _ in S]; cs = [x for _, x in S]
        boxes = boxes[:5] + [(min(rs), max(rs), min(cs), max(cs))]
        tried = set(); n = 0
        for t, b, l, r in boxes:
            smin = max(b - t, r - l)
            for s in range(smin, smin + 2 * max(H, W) + 2):
                vo = _side_options(t, b, H, s); ho = _side_options(l, r, W, s)
                if not vo and not ho and s > smin + 1:
                    break
                for T0, B0 in vo:
                    for L0, R0 in ho:
                        key = (T0 + B0, L0 + R0)
                        if key in tried:
                            continue
                        tried.add(key); n += 1
                        if n > max_cands:
                            break
                        res = _check_source(g, bg, S, _dist_fn(metric, T0 + B0, L0 + R0))
                        if res:
                            return res
    return None


def _check_source(g, bg, S, dist):
    H, W = len(g), len(g[0])
    col = {}
    for r, c in S:
        D = dist(r, c)
        if col.setdefault(D, g[r][c]) != g[r][c]:
            return None
    Ds = sorted(col)
    runs = []
    for D in Ds:
        if runs and D == runs[-1][0] + runs[-1][1]:
            runs[-1][1] += 1
        else:
            runs.append([D, 1])
    if len(runs) < 2:
        return None
    w = runs[-1][1]
    P = runs[-1][0] - runs[-2][0]
    start = runs[1][0] - P                     # innermost ring may be cut at radius 0 (start < 0)
    if P <= w or any(k != w for _, k in runs[1:]) or runs[0] != [max(start, 0), min(w, start + w)]:
        return None
    if any(runs[i + 1][0] - runs[i][0] != P for i in range(1, len(runs) - 1)):
        return None
    if any(col[a] != col[a + i] for a, k in runs for i in range(k)):
        return None
    cols = [col[a] for a, _ in runs]
    best = None
    for h in (0, 1):
        tail = cols[h:]
        for m in range(1, len(tail) + 1):
            if all(tail[i] == tail[i - m] for i in range(m, len(tail))):
                if best is None or h + m < best[0]:
                    best = (h + m, cols[:h], tail[:m])
                break
    Dset = set(Ds); cnt = 0
    for r in range(H):
        for c in range(W):
            if dist(r, c) in Dset:
                cnt += 1
    if cnt != len(S):                          # the visible rings must be complete
        return None
    return bg, dist, start, w, P, best[1], best[2]


def _render(g, metric, direction, fill):
    fit = _fit_rings(g, metric)
    if fit is None:
        return None
    bg, dist, start, w, P, head, cyc = fit
    H, W = len(g), len(g[0])
    out = []
    for r in range(H):
        row = []
        for c in range(W):
            k = dist(r, c) - start
            if (direction == 'both' or k >= 0) and k % P < w:
                i = k // P
                row.append(head[i] if 0 <= i < len(head) else cyc[(i - len(head)) % len(cyc)])
            else:
                row.append(g[r][c] if fill is None or g[r][c] != bg else fill)
        out.append(row)
    return out


def fam_ripple_wavefronts(train):
    if not train or any(len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0])
                        for p in train):
        return
    fills = [None] + sorted({v for p in train for row in p['output'] for v in row})
    for metric in ('linf', 'l1'):
        if _fit_rings(train[0]['input'], metric) is None:
            continue
        for direction in ('out', 'both'):
            for fill in fills:
                def fn(g, metric=metric, direction=direction, fill=fill):
                    return _render(g, metric, direction, fill)
                if all(fn(p['input']) == p['output'] for p in train):
                    yield ('waves:ripple_wavefronts[metric=%s,dir=%s,fill=%s]'
                           % (metric, direction, 'keep' if fill is None else fill), 3, fn)
                    return


FAMILIES = (fam_ripple_wavefronts,)
