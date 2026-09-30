"""Group g07 "row / column tiling (periodic continuation)".

Concept: SUPERLATTICE (crystallography).
A crystal is a motif (unit cell) repeated by a lattice translation; a superlattice additionally
decorates the lattice sites with a colour (species) sequence of period p.  Here:
  * the motif is the largest single-colour object of the input (the seed);
  * it is translated along a lattice vector (primary direction, step = motif extent + gap)
    until it leaves the grid;
  * copy k (k = 1, 2, ...) is decorated with species S[(k-1) mod p], where S is either
      - 'key': the colour sequence written in the input by the remaining non-background cells
               (read along the axis perpendicular to growth), p = len(key), or
      - 'seq': a period-p sequence of roles induced from training: 'src' (the motif's own colours),
               'bg' (vacancy) or a constant colour;
  * optionally, sites of selected phases seed a secondary lattice row along the perpendicular
    direction (same step rule), carrying the same species.
Growth fills only background cells (a crystal grows into empty space).

Finite parameter domains:
  CONN    motif connectivity            (8, 4)
  DIRS    primary lattice direction     ('far', 'U', 'D', 'L', 'R', 'UD', 'LR')   'far' = side with most room
  GAPS    gap between lattice copies     (0, 1, 2)
  SOURCES species source                ('key-fwd', 'key-rev', 'seq')
  PERIODS period of an induced sequence  (1, 2, 3, 4)
  SECS    secondary direction           (None, 'far', <the two perpendicular absolute directions>)
  secondary phase flags: induced from training (subset of phases; all-or-none for 'key').
"""
from collections import Counter

CONN = (8, 4)
DIRS = ('far', 'U', 'D', 'L', 'R', 'UD', 'LR')
GAPS = (0, 1, 2)
SOURCES = ('key-fwd', 'key-rev', 'seq')
PERIODS = (1, 2, 3, 4)
VEC = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}
PERP = {'U': ('L', 'R'), 'D': ('L', 'R'), 'L': ('U', 'D'), 'R': ('U', 'D'), 'UD': ('L', 'R'), 'LR': ('U', 'D')}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _components(g, bg, conn):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and not seen[r][c]:
                col = g[r][c]
                st = [(r, c)]
                seen[r][c] = True
                cells = []
                while st:
                    y, x = st.pop()
                    cells.append((y, x))
                    for dy, dx in nb:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                            seen[ny][nx] = True
                            st.append((ny, nx))
                comps.append(cells)
    return comps


def _scene(g, conn):
    """bg, motif {cell: colour}, bbox, key cells (other non-bg cells)."""
    bg = _bg(g)
    comps = _components(g, bg, conn)
    if not comps:
        return None
    comps.sort(key=len, reverse=True)
    if len(comps) > 1 and len(comps[0]) == len(comps[1]):
        return None                                   # no unique seed
    motif = {p: g[p[0]][p[1]] for p in comps[0]}
    rs = [p[0] for p in motif]
    cs = [p[1] for p in motif]
    bbox = (min(rs), min(cs), max(rs), max(cs))
    key = [p for comp in comps[1:] for p in comp]
    return bg, motif, bbox, key


def _far(bbox, H, W, cands):
    r0, c0, r1, c1 = bbox
    room = {'U': r0, 'D': H - 1 - r1, 'L': c0, 'R': W - 1 - c1}
    best = sorted(cands, key=lambda d: -room[d])
    if len(best) > 1 and room[best[0]] == room[best[1]]:
        return None
    return best[0]


def _lattice(bbox, d, gap, H, W):
    """Offsets (k, oy, ox) of lattice copies k != 0 along direction d while the copy touches the grid."""
    r0, c0, r1, c1 = bbox
    h, w = r1 - r0 + 1, c1 - c0 + 1
    out = []
    for dd in (('U', 'D') if d == 'UD' else ('L', 'R') if d == 'LR' else (d,)):
        dy, dx = VEC[dd]
        step = (h if dy else w) + gap
        sign = 1 if (dd == d) else (1 if dd in ('D', 'R') else -1)
        k = 1
        while True:
            oy, ox = k * step * dy, k * step * dx
            if r1 + oy < 0 or r0 + oy >= H or c1 + ox < 0 or c0 + ox >= W:
                break
            out.append((sign * k, oy, ox))
            k += 1
    return out


def _observe(g, o, bg, motif, oy, ox):
    """Candidate species tokens that explain the output at a copy placed at offset (oy, ox)."""
    H, W = len(g), len(g[0])
    vals = []
    for (r, c), col in motif.items():
        y, x = r + oy, c + ox
        if 0 <= y < H and 0 <= x < W and g[y][x] == bg:
            vals.append((o[y][x], col))
    if not vals:
        return None                                   # nothing observable
    cands = set()
    if all(v == col for v, col in vals):
        cands.add('src')
    vs = {v for v, _ in vals}
    if len(vs) == 1:
        v = vs.pop()
        cands.add(v)
        if v == bg:
            cands.add('bg')
    return cands


def _paint(out, g, bg, motif, oy, ox, tok):
    if tok == 'bg':
        return
    H, W = len(g), len(g[0])
    for (r, c), col in motif.items():
        y, x = r + oy, c + ox
        if 0 <= y < H and 0 <= x < W and g[y][x] == bg:
            out[y][x] = col if tok == 'src' else tok


def _key_colours(g, key, d, rev):
    if not key:
        return None
    vertical = d in ('U', 'D', 'UD')
    ks = sorted(key, key=(lambda p: (p[1], p[0])) if vertical else (lambda p: (p[0], p[1])), reverse=rev)
    return [g[r][c] for r, c in ks]


def _setup(g, conn, dname, sname):
    sc = _scene(g, conn)
    if sc is None:
        return None
    bg, motif, bbox, key = sc
    H, W = len(g), len(g[0])
    d = _far(bbox, H, W, ('U', 'D', 'L', 'R')) if dname == 'far' else dname
    if d is None:
        return None
    if sname is None:
        sd = None
    elif sname == 'far':
        sd = _far(bbox, H, W, PERP[d])
        if sd is None:
            return None
    else:
        if sname not in PERP[d]:
            return None
        sd = sname
    return bg, motif, bbox, key, d, sd


def _species(g, setup, source, S):
    """Function k -> species token (phase = (k-1) mod p); None if not definable."""
    bg, motif, bbox, key, d, sd = setup
    if source == 'seq':
        p = len(S)
        return (lambda k: S[(k - 1) % p]), p
    kc = _key_colours(g, key, d, source == 'key-rev')
    if kc is None:
        return None
    p = len(kc)
    return (lambda k: kc[(k - 1) % p]), p


def _render(g, conn, dname, gap, source, S, sname, flags):
    H, W = len(g), len(g[0])
    st = _setup(g, conn, dname, sname)
    if st is None:
        return None
    bg, motif, bbox, key, d, sd = st
    sp = _species(g, st, source, S)
    if sp is None:
        return None
    spec, p = sp
    out = [row[:] for row in g]
    sites = [(0, 0, 0)] + _lattice(bbox, d, gap, H, W)
    for k, oy, ox in sites:
        tok = 'src' if k == 0 else spec(k)
        if k:
            _paint(out, g, bg, motif, oy, ox, tok)
        if sd is not None and flags[((k - 1) % p) if source == 'seq' else 0]:
            sb = (bbox[0] + oy, bbox[1] + ox, bbox[2] + oy, bbox[3] + ox)
            for _, sy, sx in _lattice(sb, sd, gap, H, W):
                _paint(out, g, bg, motif, oy + sy, ox + sx, tok)
    return out


def _induce_seq(train, conn, dname, gap, p):
    """Induce the period-p species roles from the primary copies of every training pair."""
    cand = [None] * p
    for pr in train:
        g, o = pr['input'], pr['output']
        st = _setup(g, conn, dname, None)
        if st is None:
            return None
        bg, motif, bbox, key, d, _ = st
        for k, oy, ox in _lattice(bbox, d, gap, len(g), len(g[0])):
            obs = _observe(g, o, bg, motif, oy, ox)
            if obs is None:
                continue
            j = (k - 1) % p
            cand[j] = obs if cand[j] is None else (cand[j] & obs)
            if not cand[j]:
                return None
    if any(c is None for c in cand):
        return None
    S = []
    for c in cand:
        S.append('src' if 'src' in c else 'bg' if 'bg' in c else min(x for x in c if isinstance(x, int)))
    return tuple(S)


def _induce_flags(train, conn, dname, gap, source, S, sname):
    """Which phases seed a secondary lattice row (evidence from the first secondary site)."""
    nflag = len(S) if source == 'seq' else 1
    ev = [None] * nflag
    for pr in train:
        g, o = pr['input'], pr['output']
        H, W = len(g), len(g[0])
        st = _setup(g, conn, dname, sname)
        if st is None:
            return None
        bg, motif, bbox, key, d, sd = st
        sp = _species(g, st, source, S)
        if sp is None:
            return None
        spec, p = sp
        for k, oy, ox in [(0, 0, 0)] + _lattice(bbox, d, gap, H, W):
            tok = 'src' if k == 0 else spec(k)
            if tok == 'bg':
                continue
            sb = (bbox[0] + oy, bbox[1] + ox, bbox[2] + oy, bbox[3] + ox)
            sec = _lattice(sb, sd, gap, H, W)
            if not sec:
                continue
            _, sy, sx = sec[0]
            obs = _observe(g, o, bg, motif, oy + sy, ox + sx)
            if obs is None:
                continue
            grown = tok in obs
            empty = 'bg' in obs
            if grown == empty:                        # ambiguous or foreign evidence
                continue
            j = ((k - 1) % p) if source == 'seq' else 0
            if ev[j] is None:
                ev[j] = grown
            elif ev[j] != grown:
                return None
    return tuple(bool(e) for e in ev)


def fam_superlattice(train):
    # quick rejections: same shape, growth only into background, something grows
    for pr in train:
        g, o = pr['input'], pr['output']
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return
        bg = _bg(g)
        changed = False
        for rg, ro in zip(g, o):
            for a, b in zip(rg, ro):
                if a != b:
                    if a != bg:
                        return
                    changed = True
        if not changed:
            return
    seen = set()
    for conn in CONN:
        for dname in DIRS:
            for gap in GAPS:
                for source in SOURCES:
                    Ss = [None] if source != 'seq' else [_induce_seq(train, conn, dname, gap, p) for p in PERIODS]
                    for S in Ss:
                        if source == 'seq' and S is None:
                            continue
                        for sname in (None, 'far', 'U', 'D', 'L', 'R'):
                            if sname is None:
                                flags = (False,) * (len(S) if S else 1)
                            else:
                                flags = _induce_flags(train, conn, dname, gap, source, S, sname)
                                if flags is None or not any(flags):
                                    continue
                            outs = []
                            for pr in train:
                                r = _render(pr['input'], conn, dname, gap, source, S, sname, flags)
                                if r is None or r != pr['output']:
                                    break
                                outs.append(r)
                            else:
                                sig = (source, S, sname, flags)
                                if sig in seen:
                                    continue
                                seen.add(sig)
                                name = (f"crystallography:superlattice[conn={conn},dir={dname},gap={gap},"
                                        f"species={source}{'' if S is None else list(S)},"
                                        f"secondary={sname},sec_phases={''.join('1' if f else '0' for f in flags)}]")

                                def fn(x, conn=conn, dname=dname, gap=gap, source=source, S=S, sname=sname, flags=flags):
                                    r = _render(x, conn, dname, gap, source, S, sname, flags)
                                    return r if r is not None else [row[:] for row in x]
                                yield (name, 3, fn)
                                return


FAMILIES = (fam_superlattice,)
