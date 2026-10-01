"""STAMP.local_stencil: every seed (cell / object) gets a fixed relative stencil painted around it.

One parametrised primitive. Everything below is induced from the training pairs:
  seg    : how seeds are segmented   cell | obj4 | obj8 | multi4 | multi8 (non-background components)
  frame  : local coordinate frame    tl (bbox top-left) | near (offset from nearest bbox side, size-free)
           | d8 (shape canonicalised up to rotation/reflection; stencil turns with it)
           | wall (frame rotated so that the nearest uniform border line is "up")
  key    : seed signature selecting the stencil: () | colour | shape | colour+shape | square
           | unique-colour | colour+inside-other-object
  stencil: learned map canonical-offset -> colour spec, spec = constant colour | colour of the seed's
           own cell at a canonical position | colour of the nearest border line.  Offsets on the seed's
           own cells express erase / recolour of the seed.
  paint  : all | bg-only | protect (never overwrite a stamping seed)
The learner aggregates, per (key, offset), what the output holds in every training instance and keeps an
offset only when one spec explains >=75% of instances and at least two of them are real changes.
Programs are yielded only when they reproduce every training output exactly.
"""
import sys; sys.path.append('/home/claude/work/widen')
from collections import Counter, defaultdict
from gdsl import H, W, bg_of, objects, bbox

R = 2          # stencil radius around the seed bbox
MAXREF = 9     # seeds larger than this cannot be used as colour references
D8T = [(sw, fy, fx) for sw in (0, 1) for fy in (0, 1) for fx in (0, 1)]
ROT = [t for t in D8T if (t[1] ^ t[2]) == t[0]]   # the four proper rotations (chirality preserved)


def fwd(t, dy, dx, h, w):
    sw, fy, fx = t
    a = h - 1 - dy if fy else dy
    b = w - 1 - dx if fx else dx
    return (b, a) if sw else (a, b)


def dims(t, h, w):
    return (w, h) if t[0] else (h, w)


def anchor(a, n, near):
    if not near: return a
    return ('t', a) if 2 * a <= n - 1 else ('b', a - (n - 1))


def walls(g, bg):
    h, w = H(g), W(g); out = {}
    for side, line in (('top', g[0]), ('bottom', g[h - 1]), ('left', [r[0] for r in g]), ('right', [r[w - 1] for r in g])):
        if len(set(line)) == 1 and line[0] != bg: out[side] = line[0]
    return out


WALL_T = {'top': (0, 0, 0), 'bottom': (0, 1, 0), 'left': (1, 0, 0), 'right': (1, 0, 1)}


def segment(g, bg, seg):
    if seg == 'rare':   # marker cells on a two-tone canvas: every colour except the two most frequent ones
        cnt = Counter(c for r in g for c in r)
        if len(cnt) < 3: return []
        top2 = {c for c, _ in cnt.most_common(2)}
        return [[(y, x)] for y in range(H(g)) for x in range(W(g)) if g[y][x] not in top2]
    if seg == 'cell':
        return [[(y, x)] for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg]
    diag = seg.endswith('8'); byc = seg.startswith('obj')
    return objects(g, bg, diag, byc)


def seed_infos(g, seg, frame):
    """Per seed: cells, bbox, transform, canonical dims, features, wall colour.  None if the frame is undefined."""
    bg = bg_of(g); h, w = H(g), W(g)
    seeds = segment(g, bg, seg)
    if not seeds or len(seeds) > 400: return None, bg
    wl = walls(g, bg) if frame == 'wall' else None
    if frame == 'wall' and not wl: return None, bg
    colsets = [tuple(sorted({g[y][x] for y, x in s})) for s in seeds]
    ccount = Counter(colsets)
    infos = []
    for s, cs in zip(seeds, colsets):
        r0, c0, r1, c1 = bbox(s); sh, sw_ = r1 - r0 + 1, c1 - c0 + 1
        rel = [(y - r0, x - c0) for y, x in s]
        wcol = None
        if frame in ('d8', 'rot'):
            t = min(D8T if frame == 'd8' else ROT, key=lambda t: sorted(fwd(t, a, b, sh, sw_) for a, b in rel))
        elif frame == 'wall':
            d = {'top': r0, 'bottom': h - 1 - r1, 'left': c0, 'right': w - 1 - c1}
            ds = sorted((d[k], k) for k in wl)
            if len(ds) > 1 and ds[0][0] == ds[1][0]: t = None
            else: t = WALL_T[ds[0][1]]; wcol = wl[ds[0][1]]
        else:
            t = (0, 0, 0)
        if t is None:
            infos.append(None); continue
        ch, cw = dims(t, sh, sw_); near = frame == 'near'
        canon = {}
        for (a, b), (y, x) in zip(rel, s):
            p = fwd(t, a, b, sh, sw_)
            canon[(anchor(p[0], ch, near), anchor(p[1], cw, near))] = g[y][x]
        shape = tuple(sorted(fwd(t, a, b, sh, sw_) for a, b in rel))
        feat = {'colour': cs, 'shape': shape, 'square': sh == sw_ and sh >= 2,
                'unique': ccount[cs] == 1}
        infos.append(dict(cells=s, box=(r0, c0, r1, c1), t=t, cd=(ch, cw), canon=canon, feat=feat, wcol=wcol,
                          cs=cs))
    # surround: the colour (background included) forming a strict majority of the in-grid 4-border of the
    # seed's 4-connected cluster of same-coloured cells (a cell seed is judged together with its cluster)
    for inf in infos:
        if inf is None: continue
        own = set(inf['cells']); stack = list(own)
        while stack:
            y, x = stack.pop()
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in own and g[yy][xx] in inf['cs']:
                    own.add((yy, xx)); stack.append((yy, xx))
        nb = Counter()
        for y, x in own:
            for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in own: nb[g[yy][xx]] += 1
        tot = sum(nb.values())
        inf['feat']['nbr'] = next((c for c, n in nb.items() if 2 * n > tot and c not in inf['cs']), None)
    return infos, bg


def window(inf, h, w, near):
    r0, c0, r1, c1 = inf['box']; sh, sw_ = r1 - r0 + 1, c1 - c0 + 1
    t = inf['t']; ch, cw = inf['cd']
    for y in range(max(0, r0 - R), min(h, r1 + R + 1)):
        for x in range(max(0, c0 - R), min(w, c1 + R + 1)):
            a, b = fwd(t, y - r0, x - c0, sh, sw_)
            yield y, x, (anchor(a, ch, near), anchor(b, cw, near))


def keyof(inf, key):
    return tuple(inf['feat'][k] for k in key)


KEYS = [(), ('colour',), ('shape',), ('colour', 'shape'), ('square',), ('unique',), ('colour', 'nbr')]


def spec_colour(inf, sp):
    if sp[0] == 'c': return sp[1]
    if sp[0] == 's': return inf['canon'].get(sp[1])
    return inf['wcol']


def finalize(stats):
    sten = {}
    for v, offs in stats.items():
        m = {}
        for off, (n, mc, cc) in offs.items():
            if not cc: continue
            sp, c = max(mc.items(), key=lambda it: (it[1], cc[it[0]], -len(it[0])))
            if c >= 0.75 * n and cc[sp] >= 2 and 2 * cc[sp] >= c:
                m[off] = sp
        sten[v] = m
    return sten


def learn(train, seg, frame, keys):
    """Two phases.  Phase 1 learns what happens to each seed's OWN cells.  Phase 2 learns the full stencil,
    ignoring cells of another seed whose output that seed's own rule already explains (so neighbouring
    seeds do not leak spurious offsets into each other's stencils)."""
    near = frame == 'near'
    seen = {k: defaultdict(set) for k in keys}   # offsets observed per key value (no extrapolation at test)
    pairs = []
    for p in train:
        g, o = p['input'], p['output']
        infos, bg = seed_infos(g, seg, frame)
        if infos is None: return None
        h, w = H(g), W(g)
        owner, rows = {}, []
        for inf in infos:
            if inf is None: continue
            own = set(inf['cells'])
            win = list(window(inf, h, w, near))
            inf['ownoff'] = {(y, x): off for y, x, off in win if (y, x) in own}
            for c in own: owner[c] = inf
            kv = [(k, keyof(inf, k)) for k in keys]
            for k, v in kv: seen[k][v].update(off for _, _, off in win)
            rows.append((inf, own, win, kv))
        pairs.append((g, o, owner, rows))

    def gather(phase, ownmaps):
        stats = {k: defaultdict(lambda: defaultdict(lambda: [0, Counter(), Counter()])) for k in keys}
        for g, o, owner, rows in pairs:
            for inf, own, win, kv in rows:
                refs = inf['canon'] if len(inf['cells']) <= MAXREF else {}
                for y, x, off in win:
                    mine = (y, x) in own
                    if phase == 1 and not mine: continue
                    ov = o[y][x]
                    other = None if mine else owner.get((y, x))
                    for k, v in kv:
                        if other is not None:
                            sp = ownmaps[k].get(keyof(other, k), {}).get(other['ownoff'][(y, x)])
                            pred = g[y][x] if sp is None else spec_colour(other, sp)
                            if pred == ov: continue
                        chg = ov != g[y][x]
                        specs = [('c', ov)] + [('s', q) for q, c in refs.items() if c == ov]
                        if inf['wcol'] is not None and inf['wcol'] == ov: specs.append(('w',))
                        st = stats[k][v][off]; st[0] += 1
                        for sp in specs:
                            st[1][sp] += 1
                            if chg: st[2][sp] += 1
        return stats

    st1 = gather(1, None)
    ownmaps = {k: finalize(st1[k]) for k in keys}
    st2 = gather(2, ownmaps)
    res = {}
    for k in keys:
        sten = finalize(st2[k])
        if any(sten.values()):
            res[k] = (sten, seen[k])
    return res


def apply(g, seg, frame, key, learned, mode):
    sten, seen = learned
    infos, bg = seed_infos(g, seg, frame)
    if infos is None or any(i is None for i in infos): return None
    h, w = H(g), W(g); near = frame == 'near'
    out = [r[:] for r in g]
    plan = []
    for inf in infos:
        kv = keyof(inf, key)
        if kv not in sten: return None
        m = sten[kv]
        if m:
            if any(off not in seen[kv] for _, _, off in window(inf, h, w, near)): return None
            plan.append((inf, m))
    protect = {c for inf, _ in plan for c in inf['cells']}
    ext = []
    for inf, m in plan:
        own = set(inf['cells'])
        for y, x, off in window(inf, h, w, near):
            sp = m.get(off)
            if sp is None: continue
            if sp[0] == 'c': col = sp[1]
            elif sp[0] == 's':
                col = inf['canon'].get(sp[1])
                if col is None: return None
            else: col = inf['wcol']
            if (y, x) in own: out[y][x] = col
            else: ext.append((y, x, col))
    for y, x, col in ext:
        if mode == 'bg' and g[y][x] != bg: continue
        if mode == 'protect' and (y, x) in protect: continue
        out[y][x] = col
    return out


def fam_local_stencil(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    if all(p['input'] == p['output'] for p in train): return
    # every changed cell must lie within Chebyshev R of a non-background input cell
    for p in train:
        g, o = p['input'], p['output']; bg = bg_of(g); h, w = H(g), W(g)
        for y in range(h):
            for x in range(w):
                if g[y][x] != o[y][x] and not any(g[yy][xx] != bg for yy in range(max(0, y - R), min(h, y + R + 1))
                                                  for xx in range(max(0, x - R), min(w, x + R + 1))):
                    return
    outs = [p['output'] for p in train]
    found = 0
    for seg in ('cell', 'rare', 'obj4', 'obj8', 'multi4', 'multi8'):
        for frame in ('tl', 'wall', 'near', 'd8', 'rot'):
            if seg in ('cell', 'rare') and frame in ('near', 'd8', 'rot'): continue
            if frame in ('d8', 'rot'): keys = [('shape',), ('colour', 'shape')]
            elif seg in ('cell', 'rare'): keys = [k for k in KEYS if 'shape' not in k and 'square' not in k]
            else: keys = KEYS
            if frame == 'near': keys = [k for k in keys if 'shape' not in k]
            try:
                learned = learn(train, seg, frame, keys)
            except Exception:
                learned = None
            if not learned: continue
            for key, sten in learned.items():
                for mode in ('all', 'bg', 'protect'):
                    ok = all(apply(p['input'], seg, frame, key, sten, mode) == p['output'] for p in train)
                    if not ok: continue
                    nk = '+'.join(key) or 'any'
                    cost = 4 + (len(key) > 1) + (frame in ('d8', 'rot', 'wall', 'near'))
                    yield (f"stencil[{seg},{frame},key={nk},{mode}]", cost,
                           lambda g, seg=seg, frame=frame, key=key, sten=sten, mode=mode: apply(g, seg, frame, key, sten, mode))
                    found += 1
                    break
                if found >= 40: return


FAMILIES = (fam_local_stencil,)
