"""g07 -- row / column tiling (periodic continuation).

Concept: FRIEZE (geometry / crystallography).  A frieze pattern is a motif repeated by translation along one axis with a
fixed period; a "coloured frieze" additionally cycles a short colour key along the repeats.

Mechanism (one operator, all parameters induced per task from its training pairs):
  * seed  = the non-background content of the input (full-span uniform lines are separators: kept, not copied);
            the seed's non-background cells are the motif, its bounding box the tile.
  * primary frieze: from the end of the existing content in the seed's band, the motif is repeated along an axis d
            (optionally also the opposite axis) until the grid edge, stride = motif extent + gap; repeat k is painted
            by key[k mod P]:
              key kind 'const'  : task constant, entries are S (= copy of the seed), a colour, or absent, P in 1..4;
              key kind 'legend' : the seed's own colour sequence in reading order (or reversed) -- the seed is a
                                  legend, P = number of seed cells.
  * secondary frieze: repeats of selected key classes (induced) are themselves repeated, identically coloured, along the
            perpendicular axis d2 (one or both senses) with stride = extent + gap2, until the grid edge.
  Only background cells are painted; existing content is preserved.

Finite parameter domains: d in {right, down, left, up} (single, or with its opposite), gap in 0..3, key kind in
{const, legend, legend_rev}, P in 1..4, key entries in {S, colour, absent}, propagating classes: subset of key
classes (+ seed), d2 in the two perpendicular senses (one or both), gap2 in 0..3.
"""
from collections import Counter

DIRS = {'right': (0, 1), 'down': (1, 0), 'left': (0, -1), 'up': (-1, 0)}
OPP = {'right': 'left', 'left': 'right', 'down': 'up', 'up': 'down'}
PERP = {'right': ('down', 'up'), 'left': ('down', 'up'), 'down': ('right', 'left'), 'up': ('right', 'left')}
MAX_GAP = 3
MAX_P = 4


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _analyse(g, bg):
    """Seed (non-bg content minus full-span uniform separator lines): bbox, mask, legend, band content ends."""
    H, W = len(g), len(g[0])
    sep = set()
    for r in range(H):
        if g[r][0] != bg and all(v == g[r][0] for v in g[r]):
            sep.update((r, c) for c in range(W))
    for c in range(W):
        if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(H)):
            sep.update((r, c) for r in range(H))
    cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg and (r, c) not in sep]
    if not cells:
        cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
        if not cells:
            return None
    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    mask = {(r - r0, c - c0): g[r][c] for r, c in cells}
    legend = [g[r][c] for r, c in cells]  # reading order
    # furthest non-bg cell (any content, separators included) inside the seed's band, per direction
    rows_band = [r for r in range(H) if any(g[r][c] != bg for c in range(c0, c1 + 1))]
    cols_band = [c for c in range(W) if any(g[r][c] != bg for r in range(r0, r1 + 1))]
    ends = {'down': max(rows_band), 'up': min(rows_band), 'right': max(cols_band), 'left': min(cols_band)}
    return dict(H=H, W=W, r0=r0, r1=r1, c0=c0, c1=c1, h=r1 - r0 + 1, w=c1 - c0 + 1,
                mask=mask, legend=legend, ends=ends)


def _positions(info, d, gap):
    """Top-left corners of the primary repeats k = 0, 1, ... along d (at least partly inside the grid)."""
    H, W, h, w = info['H'], info['W'], info['h'], info['w']
    out = []
    k = 0
    while True:
        if d == 'right':
            left = info['ends']['right'] + 1 + gap + k * (w + gap)
            if left > W - 1: break
            out.append((info['r0'], left))
        elif d == 'left':
            left = info['ends']['left'] - gap - w - k * (w + gap)
            if left + w - 1 < 0: break
            out.append((info['r0'], left))
        elif d == 'down':
            top = info['ends']['down'] + 1 + gap + k * (h + gap)
            if top > H - 1: break
            out.append((top, info['c0']))
        else:
            top = info['ends']['up'] - gap - h - k * (h + gap)
            if top + h - 1 < 0: break
            out.append((top, info['c0']))
        k += 1
    return out


def _visible(info, top, left):
    """Mask cells of a repeat placed at (top, left) that lie inside the grid: {(r, c): seed colour}."""
    H, W = info['H'], info['W']
    return {(top + dr, left + dc): col for (dr, dc), col in info['mask'].items()
            if 0 <= top + dr < H and 0 <= left + dc < W}


def _classify(cells, out, bg):
    """What a repeat looks like in the output: 'S' (copy of seed), a colour (uniform), None (absent) or False."""
    if not cells:
        return False
    vals = [(col, out[r][c]) for (r, c), col in cells.items()]
    if all(o == bg for _, o in vals):
        return None
    if all(o == col for col, o in vals):
        return 'S'
    outs = {o for _, o in vals}
    if len(outs) == 1:
        return outs.pop()
    return False


def _shift(cells, dr, dc, H, W):
    return {(r + dr, c + dc): v for (r, c), v in cells.items() if 0 <= r + dr < H and 0 <= c + dc < W}


def _entry(kind, key, P, k, info):
    """(class label, key entry) of primary repeat k."""
    if kind == 'const':
        return ('K', k % P), key[k % P]
    leg = info['legend'] if kind == 'legend' else info['legend'][::-1]
    n = len(leg)
    return ('L', k % n), leg[k % n]


def _elements(g, bg, info, dirs, gap, kind, key, P, seed_label):
    """[(label, {(r, c): colour})] -- the seed, then every primary repeat (absent ones skipped)."""
    elems = [(seed_label, _visible(info, info['r0'], info['c0']))]
    for d in dirs:
        for k, (top, left) in enumerate(_positions(info, d, gap)):
            label, e = _entry(kind, key, P, k, info)
            if e is None:
                continue
            cells = _visible(info, top, left)
            if e != 'S':
                cells = {rc: e for rc in cells}
            elems.append((label, cells))
    return elems


def _secondary_copies(cells, info, d2, gap2):
    """Perpendicular repeats m = 1, 2, ... of one element along d2 (clipped)."""
    H, W = info['H'], info['W']
    dr0, dc0 = DIRS[d2]
    stride2 = (info['h'] if d2 in ('down', 'up') else info['w']) + gap2
    m = 1
    while True:
        sh = _shift(cells, dr0 * m * stride2, dc0 * m * stride2, H, W)
        if not sh:
            return
        yield sh
        m += 1


def _build(dirs, gap, kind, key, P, seed_label, prop, d2s, gap2):
    """The program: a function grid -> grid."""
    def fn(g):
        bg = _bg(g)
        info = _analyse(g, bg)
        if info is None:
            return [row[:] for row in g]
        out = [row[:] for row in g]
        elems = _elements(g, bg, info, dirs, gap, kind, key, P, seed_label)
        for label, cells in elems[1:]:
            for (r, c), v in cells.items():
                if out[r][c] == bg:
                    out[r][c] = v
        for label, cells in elems:
            if label not in prop or not cells:
                continue
            for d2 in d2s:
                for sh in _secondary_copies(cells, info, d2, gap2):
                    for (r, c), v in sh.items():
                        if out[r][c] == bg:
                            out[r][c] = v
        return out
    return fn


def _induce_secondary(train, pairs_info, dirs, gap, kind, key, P, seed_label):
    """Residual after the primary frieze must be explained by perpendicular repeats of some element classes."""
    base = _build(dirs, gap, kind, key, P, seed_label, set(), (), 0)
    residuals = []
    for p, (bg, info) in zip(train, pairs_info):
        pri = base(p['input'])
        res = {(r, c): p['output'][r][c] for r in range(info['H']) for c in range(info['W'])
               if pri[r][c] != p['output'][r][c]}
        if any(p['input'][r][c] != bg or pri[r][c] != bg for (r, c) in res):
            return None  # the primary frieze painted something wrong: unfixable
        residuals.append(res)
    if not any(residuals):
        return set(), (), 0
    p0, p1 = PERP[dirs[0]]
    for d2s in ((p0,), (p1,), (p0, p1)):
        for gap2 in range(MAX_GAP + 1):
            per_class = {}
            for pi, (p, (bg, info)) in enumerate(zip(train, pairs_info)):
                for label, cells in _elements(p['input'], bg, info, dirs, gap, kind, key, P, seed_label):
                    for d2 in d2s:
                        for sh in _secondary_copies(cells, info, d2, gap2):
                            sh = {rc: v for rc, v in sh.items() if p['input'][rc[0]][rc[1]] == bg}
                            per_class.setdefault(label, []).append((pi, sh))
            prop = set()
            for label, lst in per_class.items():
                if any(sh for _, sh in lst) and \
                        all(all(residuals[pi].get(rc) == v for rc, v in sh.items()) for pi, sh in lst):
                    prop.add(label)
            if not prop:
                continue
            explained = [dict() for _ in train]
            for label in prop:
                for pi, sh in per_class[label]:
                    explained[pi].update(sh)
            if all(explained[pi] == residuals[pi] for pi in range(len(train))):
                return prop, d2s, gap2
    return None


def _role_based(key):
    return all(e is None or e == 'S' for e in key)


def fam_frieze(train):
    # quick rejection: same size, only background cells change, something changes
    pairs_info = []
    for p in train:
        I, O = p['input'], p['output']
        if len(I) != len(O) or any(len(a) != len(b) for a, b in zip(I, O)):
            return
        bg = _bg(I)
        if any(I[r][c] != bg and I[r][c] != O[r][c] for r in range(len(I)) for c in range(len(I[0]))):
            return
        if all(I[r][c] == O[r][c] for r in range(len(I)) for c in range(len(I[0]))):
            return
        info = _analyse(I, bg)
        if info is None:
            return
        pairs_info.append((bg, info))

    seen = set()
    dir_sets = [(d,) for d in DIRS] + [(d, OPP[d]) for d in ('right', 'down')]
    for dirs in dir_sets:
        for gap in range(MAX_GAP + 1):
            # observed repeat sequence per pair and direction
            obs_all, good = [], True
            for p, (bg, info) in zip(train, pairs_info):
                per_dir = []
                for dd in dirs:
                    seq = []
                    for top, left in _positions(info, dd, gap):
                        e = _classify(_visible(info, top, left), p['output'], bg)
                        if e is False:
                            good = False; break
                        seq.append(e)
                    if not good: break
                    per_dir.append(seq)
                if not good: break
                obs_all.append(per_dir)
            if not good:
                continue
            # every used direction must show at least one repeat in some pair
            if any(not any(per_dir[i] for per_dir in obs_all) for i in range(len(dirs))):
                continue
            # key hypotheses
            hyps = []
            for P in range(1, MAX_P + 1):
                key, known, ok = [None] * P, [False] * P, True
                for per_dir in obs_all:
                    for seq in per_dir:
                        for k, e in enumerate(seq):
                            j = k % P
                            if known[j] and key[j] != e:
                                ok = False; break
                            key[j], known[j] = e, True
                        if not ok: break
                    if not ok: break
                if ok and all(known):
                    hyps.append(('const', tuple(key), P))
            for kind in ('legend', 'legend_rev'):
                leg_ok = True
                for (bg, info), per_dir in zip(pairs_info, obs_all):
                    for seq in per_dir:
                        for k, e in enumerate(seq):
                            _, want = _entry(kind, (), 0, k, info)
                            if e != want and not (e == 'S' and len(set(info['legend'])) == 1):
                                leg_ok = False; break
                        if not leg_ok: break
                    if not leg_ok: break
                if leg_ok:
                    hyps.append((kind, (), 0))
            # most general first: role-based constant keys, legends, colour-specific keys
            order = ([h for h in hyps if h[0] == 'const' and _role_based(h[1])]
                     + [h for h in hyps if h[0] != 'const']
                     + [h for h in hyps if h[0] == 'const' and not _role_based(h[1])])
            for kind, key, P in order:
                seed_labels = [('seed',)]
                if kind == 'const' and key[P - 1] == 'S':
                    seed_labels.insert(0, ('K', P - 1))  # the seed is repeat -1 of the same frieze
                for seed_label in seed_labels:
                    sec = _induce_secondary(train, pairs_info, dirs, gap, kind, key, P, seed_label)
                    if sec is None:
                        continue
                    prop, d2s, gap2 = sec
                    fn = _build(dirs, gap, kind, key, P, seed_label, prop, d2s, gap2)
                    if not all(fn(p['input']) == p['output'] for p in train):
                        continue
                    kd = kind if kind != 'const' else 'key=' + ''.join(
                        'S' if e == 'S' else ('_' if e is None else str(e)) for e in key)
                    name = 'geometry:frieze[d=%s gap=%d %s' % ('+'.join(dirs), gap, kd)
                    if prop:
                        name += ' prop=%s d2=%s gap2=%d' % (
                            '/'.join(sorted(str(l[-1]) for l in prop)), '+'.join(d2s), gap2)
                    name += ']'
                    if name not in seen:
                        seen.add(name)
                        yield (name, 3, fn)
                    break


FAMILIES = (fam_frieze,)
