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
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter, defaultdict
from gdsl import H, W, bg_of, objects, bbox

R = 2          # stencil radius around the seed bbox
MAXREF = 9     # seeds larger than this cannot be used as colour references
D8T = [(sw, fy, fx) for sw in (0, 1) for fy in (0, 1) for fx in (0, 1)]


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
    big = None
    infos = []
    for s, cs in zip(seeds, colsets):
        r0, c0, r1, c1 = bbox(s); sh, sw_ = r1 - r0 + 1, c1 - c0 + 1
        rel = [(y - r0, x - c0) for y, x in s]
        wcol = None
        if frame == 'd8':
            t = min(D8T, key=lambda t: sorted(fwd(t, a, b, sh, sw_) for a, b in rel))
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
    # inside the bbox of a (>=4 cell) object of another colour
    if any(i is not None for i in infos):
        if big is None:
            big = [(bbox(o), g[o[0][0]][o[0][1]]) for o in objects(g, bg, False, True) if len(o) >= 4]
        for inf in infos:
            if inf is None: continue
            r0, c0, r1, c1 = inf['box']
            inf['feat']['inbox'] = any(b[0] <= r0 and r1 <= b[2] and b[1] <= c0 and c1 <= b[3] and col not in inf['cs']
                                       for b, col in big)
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


KEYS = [(), ('colour',), ('shape',), ('colour', 'shape'), ('square',), ('unique',), ('colour', 'inbox')]


def learn(train, seg, frame, keys):
    near = frame == 'near'
    # stats[key][keyval][off] = [n, Counter(spec->match), Counter(spec->change-match)]
    stats = {k: defaultdict(lambda: defaultdict(lambda: [0, Counter(), Counter()])) for k in keys}
    for p in train:
        g, o = p['input'], p['output']
        infos, bg = seed_infos(g, seg, frame)
        if infos is None: return None
        h, w = H(g), W(g)
        for inf in infos:
            if inf is None: continue
            refs = inf['canon'] if len(inf['cells']) <= MAXREF else {}
            kv = [(k, keyof(inf, k)) for k in keys]
            for y, x, off in window(inf, h, w, near):
                ov = o[y][x]; chg = ov != g[y][x]
                specs = [('c', ov)] + [('s', q) for q, v in refs.items() if v == ov]
                if inf['wcol'] is not None and inf['wcol'] == ov: specs.append(('w',))
                for k, v in kv:
                    st = stats[k][v][off]; st[0] += 1
                    for sp in specs:
                        st[1][sp] += 1
                        if chg: st[2][sp] += 1
    res = {}
    for k in keys:
        sten = {}
        for v, offs in stats[k].items():
            m = {}
            for off, (n, mc, cc) in offs.items():
                if not cc: continue
                sp, c = max(mc.items(), key=lambda it: (it[1], cc[it[0]], -len(it[0])))
                if c >= 0.75 * n and cc[sp] >= 2 and 2 * cc[sp] >= c:
                    m[off] = sp
            sten[v] = m
        if any(sten.values()):
            res[k] = sten
    return res


def apply(g, seg, frame, key, sten, mode):
    infos, bg = seed_infos(g, seg, frame)
    if infos is None or any(i is None for i in infos): return None
    h, w = H(g), W(g); near = frame == 'near'
    out = [r[:] for r in g]
    plan = []
    for inf in infos:
        kv = keyof(inf, key)
        if kv not in sten: return None
        m = sten[kv]
        if m: plan.append((inf, m))
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
    for seg in ('cell', 'obj4', 'obj8', 'multi4', 'multi8'):
        for frame in ('tl', 'wall', 'near', 'd8'):
            if seg == 'cell' and frame in ('near', 'd8'): continue
            if frame == 'd8': keys = [('shape',), ('colour', 'shape')]
            elif seg == 'cell': keys = [k for k in KEYS if 'shape' not in k and 'square' not in k]
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
                    cost = 4 + (len(key) > 1) + (frame in ('d8', 'wall', 'near'))
                    yield (f"stencil[{seg},{frame},key={nk},{mode}]", cost,
                           lambda g, seg=seg, frame=frame, key=key, sten=sten, mode=mode: apply(g, seg, frame, key, sten, mode))
                    found += 1
                    break
                if found >= 6: return


FAMILIES = (fam_local_stencil,)
