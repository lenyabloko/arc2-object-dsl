"""g08 "periodic rings" -- periodic continuation of a seed to the grid edge.

Two members, two generators (they do NOT share one mechanism, see FINAL notes):

  fam_wavefront  (physics: wave propagation / ripples, Chebyshev or Manhattan metric)
      The input shows the first few wavefronts of a wave radiating from a point source
      (which may lie on or outside the grid).  A wavefront is the set of cells at distance d
      from the source; the colour depends only on d and is periodic with wavelength p.
      The source, the wavelength and the colour-per-phase are induced from the INPUT itself
      (they vary from pair to pair); the output propagates the wave to every cell of the grid.
      Cells whose phase carries no wavefront are painted with a fill colour induced from the
      training outputs (identity/background allowed).

  fam_mirror_images  (optics: images in parallel mirrors / "hall of mirrors")
      The seed object sits between two parallel mirrors placed on opposite sides of its
      bounding box (mirror axis in {H, V, D, A}; any subset of axes, each an independent
      image chain, or the 2-D image lattice for a perpendicular pair).  Images alternate
      handedness; odd images take an induced colour map (identity or a colour swap).

Both: stdlib only, no hard-coded sizes/coordinates/colours, parameters from finite domains,
training pairs verified exactly before yielding, quick rejection.
"""
from collections import Counter

# ----------------------------------------------------------------------------- helpers

def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _same_shape(a, b):
    return len(a) == len(b) and len(a[0]) == len(b[0])


# =========================================================================== wavefront

_METRICS = ('cheb', 'manh')


def _dist(metric, r, c, cr, cc):
    dr = r - cr if r >= cr else cr - r
    dc = c - cc if c >= cc else cc - c
    if metric == 'cheb':
        return dr if dr >= dc else dc
    return dr + dc


def _probes(metric, cr, cc, d):
    """A few O(1) sample points on the wavefront at distance d (used to reject centres fast)."""
    if d == 0:
        return ((cr, cc),)
    pts = [(cr - d, cc), (cr + d, cc), (cr, cc - d), (cr, cc + d)]
    if metric == 'cheb':
        pts += [(cr - d, cc - d), (cr - d, cc + d), (cr + d, cc - d), (cr + d, cc + d)]
    else:
        h = d // 2
        pts += [(cr - h, cc + d - h), (cr - h, cc - d + h), (cr + h, cc + d - h), (cr + h, cc - d + h)]
    return pts


def _uniform_on_S(g, metric, cr, cc, S):
    """Cheap filter: the coloured cells must be uniformly coloured per wavefront."""
    seq = {}
    for (r, c) in S:
        d = _dist(metric, r, c, cr, cc)
        v = g[r][c]
        prev = seq.get(d)
        if prev is None:
            seq[d] = v
        elif prev != v:
            return None
    return seq


def _verify_centre(g, metric, bg, cr, cc, seq):
    """Every wavefront (d <= dmax) must be uniformly coloured.  Returns (dmax, p, phase->colour)."""
    H, W = len(g), len(g[0])
    seq = dict(seq)
    dmax = max(seq)
    # full pass over the grid
    for r in range(H):
        for c in range(W):
            d = _dist(metric, r, c, cr, cc)
            v = g[r][c]
            prev = seq.get(d)
            if prev is None:
                seq[d] = v
            elif prev != v:
                return None
    # smallest wavelength consistent with the observed phases 0..dmax (unobserved d = wildcard)
    for p in range(1, dmax + 2):
        phase = {}
        ok = True
        for d in range(dmax + 1):
            v = seq.get(d)
            if v is None:
                continue
            k = d % p
            if k in phase:
                if phase[k] != v:
                    ok = False
                    break
            else:
                phase[k] = v
        if ok:
            return dmax, p, phase
    return None


def _candidate_centres(H, W):
    """Grid cells first (row-major), then the off-grid margin ring by ring (up to max(H, W) away)."""
    for r in range(H):
        for c in range(W):
            yield r, c
    for m in range(1, max(H, W) + 1):
        for r in range(-m, H + m):
            for c in range(-m, W + m):
                if r == -m or r == H + m - 1 or c == -m or c == W + m - 1:
                    yield r, c


def _find_source(g, metric, bg, budget=60):
    """Induce (cr, cc, p, phase) from the input alone.  Centre may lie outside the grid."""
    H, W = len(g), len(g[0])
    S = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    if not S:
        return None
    samples = [S[0], S[-1], S[len(S) // 2], S[len(S) // 4], S[(3 * len(S)) // 4]]
    samples = [(r, c, g[r][c]) for (r, c) in samples]
    best = None
    checks = 0
    for cr, cc in _candidate_centres(H, W):
        ok = True
        for (rr, ccc, col) in samples:
            d = _dist(metric, rr, ccc, cr, cc)
            for (pr, pc) in _probes(metric, cr, cc, d):
                if 0 <= pr < H and 0 <= pc < W and g[pr][pc] != col:
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            continue
        seq = _uniform_on_S(g, metric, cr, cc, S)
        if seq is None:
            continue
        checks += 1
        if checks > budget:
            break
        res = _verify_centre(g, metric, bg, cr, cc, seq)
        if res is None:
            continue
        dmax, p, phase = res
        inside = 0 if (0 <= cr < H and 0 <= cc < W) else 1
        key = (dmax, p, inside, cr, cc)
        if best is None or key < best[0]:
            best = (key, (cr, cc, p, phase))
    return None if best is None else best[1]


def _propagate(g, metric, bg, fill):
    src = _find_source(g, metric, bg)
    if src is None:
        return None
    cr, cc, p, phase = src
    H, W = len(g), len(g[0])
    out = []
    for r in range(H):
        row = []
        for c in range(W):
            v = phase.get(_dist(metric, r, c, cr, cc) % p, bg)
            row.append(fill if v == bg else v)
        out.append(row)
    return out


def fam_wavefront(train):
    """physics:wavefront -- concentric wavefronts of wavelength p from a source, continued to the edge."""
    for metric in _METRICS:
        fill = None
        ok = True
        for pr in train:
            g, o = pr['input'], pr['output']
            if not _same_shape(g, o):
                ok = False
                break
            bg = _bg(g)
            pred = _propagate(g, metric, bg, -1)
            if pred is None:
                ok = False
                break
            for r in range(len(o)):
                for c in range(len(o[0])):
                    v = pred[r][c]
                    if v == -1:
                        if fill is None:
                            fill = o[r][c]
                        elif fill != o[r][c]:
                            ok = False
                    elif v != o[r][c]:
                        ok = False
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        fill_mode = 'bg' if fill is None else fill

        def fn(g, metric=metric, fill_mode=fill_mode):
            bg = _bg(g)
            out = _propagate(g, metric, bg, bg if fill_mode == 'bg' else fill_mode)
            if out is None:
                raise ValueError('no wave source found')
            return out

        if all(fn(p['input']) == p['output'] for p in train):
            yield ('physics:wavefront[metric=%s,fill=%s]' % (metric, fill_mode), 3, fn)
            return


# ====================================================================== mirror images

_AXES = ('H', 'V', 'D', 'A')


def _mirror_pair(kind, r0, r1, c0, c1):
    """Two parallel mirrors on opposite sides of the bounding box [r0,r1]x[c0,c1] (cell maps)."""
    if kind == 'H':      # mirrors along the bottom / top edges -> vertical chain
        return (lambda r, c: (2 * r1 + 1 - r, c)), (lambda r, c: (2 * r0 - 1 - r, c))
    if kind == 'V':      # mirrors along the right / left edges -> horizontal chain
        return (lambda r, c: (r, 2 * c1 + 1 - c)), (lambda r, c: (r, 2 * c0 - 1 - c))
    if kind == 'D':      # main-diagonal mirrors through the TR / BL corner points
        return (lambda r, c: (c - c1 - 1 + r0, r - r0 + c1 + 1)), (lambda r, c: (c - c0 + r1 + 1, r - r1 - 1 + c0))
    # 'A'                # anti-diagonal mirrors through the TL / BR corner points
    return (lambda r, c: (r0 + c0 - c - 1, r0 + c0 - r - 1)), (lambda r, c: (r1 + c1 + 1 - c, r1 + c1 + 1 - r))


def _chain(kind, S, r0, r1, c0, c1, H, W):
    """All images of S in one pair of parallel mirrors: list of (|k|, parity, cells)."""
    M1, M2 = _mirror_pair(kind, r0, r1, c0, c1)
    a, b = M1(*M2(r0, c0))
    t = (a - r0, b - c0)                      # two reflections = one translation
    step = max(abs(t[0]), abs(t[1]))
    if step == 0:
        return []
    K = (H + W) // step + 2
    S1 = [M1(r, c) for (r, c) in S]
    imgs = []
    for k in range(-K, K + 1):
        dr, dc = k * t[0], k * t[1]
        imgs.append((abs(k), 0, [(r + dr, c + dc) for (r, c) in S]))
        imgs.append((abs(k), 1, [(r + dr, c + dc) for (r, c) in S1]))
    return imgs


def _images(g, bg, axes, mode):
    H, W = len(g), len(g[0])
    S = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    if not S:
        return None
    r0 = min(r for r, c in S); r1 = max(r for r, c in S)
    c0 = min(c for r, c in S); c1 = max(c for r, c in S)
    cols = [g[r][c] for (r, c) in S]
    if mode == 'chains':
        imgs = []
        for kind in axes:
            imgs += _chain(kind, S, r0, r1, c0, c1, H, W)
    else:                                       # 'lattice': product of two perpendicular chains
        k1, k2 = axes
        A = _chain(k1, S, r0, r1, c0, c1, H, W)
        M1, M2 = _mirror_pair(k2, r0, r1, c0, c1)
        a, b = M1(*M2(r0, c0))
        t = (a - r0, b - c0)
        step = max(abs(t[0]), abs(t[1]))
        if step == 0:
            return None
        K = (H + W) // step + 2
        imgs = []
        for (n, par, cells) in A:
            cells1 = [M1(r, c) for (r, c) in cells]
            for k in range(-K, K + 1):
                dr, dc = k * t[0], k * t[1]
                imgs.append((n + abs(k), par, [(r + dr, c + dc) for (r, c) in cells]))
                imgs.append((n + abs(k), 1 - par, [(r + dr, c + dc) for (r, c) in cells1]))
    imgs.sort(key=lambda x: -x[0])              # far images first, the seed itself last
    return imgs, cols


def _paint(g, bg, axes, mode, cmap):
    res = _images(g, bg, axes, mode)
    if res is None:
        return None
    imgs, cols = res
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    for (_, par, cells) in imgs:
        for (r, c), v in zip(cells, cols):
            if 0 <= r < H and 0 <= c < W:
                out[r][c] = cmap.get(v, v) if par else v
    return out


def _axis_subsets():
    subs = []
    for m in range(1, 1 << len(_AXES)):
        subs.append(tuple(a for i, a in enumerate(_AXES) if m >> i & 1))
    subs.sort(key=len)
    return subs


def fam_mirror_images(train):
    """optics:parallel_mirrors -- seed between parallel mirrors; chain of alternating images."""
    configs = [(s, 'chains') for s in _axis_subsets()] + [(('H', 'V'), 'lattice'), (('D', 'A'), 'lattice')]
    for axes, mode in configs:
        cmap = {}
        ok = True
        for pr in train:
            g, o = pr['input'], pr['output']
            if not _same_shape(g, o):
                ok = False
                break
            bg = _bg(g)
            res = _images(g, bg, axes, mode)
            if res is None:
                ok = False
                break
            imgs, cols = res
            H, W = len(g), len(g[0])
            for (_, par, cells) in imgs:
                for (r, c), v in zip(cells, cols):
                    if not (0 <= r < H and 0 <= c < W):
                        continue
                    w = o[r][c]
                    if par:
                        if w == bg or cmap.setdefault(v, w) != w:   # odd images must stay visible
                            ok = False
                            break
                    elif w != v:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        cm = dict(cmap)

        def fn(g, axes=axes, mode=mode, cm=cm):
            out = _paint(g, _bg(g), axes, mode, cm)
            if out is None:
                raise ValueError('no seed')
            return out

        if all(fn(p['input']) == p['output'] for p in train):
            desc = 'identity' if all(k == v for k, v in cm.items()) else ','.join('%d>%d' % kv for kv in sorted(cm.items()))
            yield ('optics:parallel_mirrors[axes=%s,mode=%s,odd_colours=%s]' % (''.join(axes), mode, desc), 3, fn)
            return


FAMILIES = (fam_wavefront, fam_mirror_images)
