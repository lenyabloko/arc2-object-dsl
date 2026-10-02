"""fill.region_by_property: segment the grid into regions separated by walls, then paint each whole
region by a rule on one region feature.  Everything is induced from the training pairs:
  region colour r  : the input colour of (most) changed cells
  membership mode  : 'col'  region cells = colour r
                     'wall' region cells = every colour except the dominant wall colour w (most frequent non-r colour)
                     'seed' region cells = r plus isolated single-cell seeds (8-isolated, size-1 objects)
  connectivity     : 4 | 8
  feature          : border (touches edge) | size-rank | is-rect | size parity | seed majority colour |
                     adjacent-marker majority colour | adjacent-has colour c ; optionally paired with border
  table            : feature value -> action, action in {keep, constant colour, W (dominant wall colour),
                     self (the feature value is itself a colour)}.  Unseen feature values refuse (None).
"""
import sys; sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def dominant_wall(g, r):
    c = Counter(v for row in g for v in row if v != r)
    return c.most_common(1)[0][0] if c else None


def member_mask(g, r, mode):
    h, w = H(g), W(g)
    if mode == 'col':
        return [[g[y][x] == r for x in range(w)] for y in range(h)]
    if mode == 'wall':
        wc = dominant_wall(g, r)
        return [[g[y][x] != wc for x in range(w)] for y in range(h)]
    m = [[g[y][x] == r for x in range(w)] for y in range(h)]
    for y in range(h):
        for x in range(w):
            v = g[y][x]
            if v == r: continue
            if all(not (0 <= y + dy < h and 0 <= x + dx < w) or g[y + dy][x + dx] != v for dy, dx in N8):
                m[y][x] = True
    return m


def regions(g, mask, diag):
    h, w = H(g), W(g); seen = [[False] * w for _ in range(h)]; out = []
    nb = N8 if diag else N4
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0][x0] or not mask[y0][x0]: continue
            st = [(y0, x0)]; seen[y0][x0] = True; cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and mask[yy][xx]:
                        seen[yy][xx] = True; st.append((yy, xx))
            out.append(cells)
    return out


def neighbours(g, cells, mask):
    h, w = H(g), W(g); s = set(cells); nb = set()
    for y, x in cells:
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in s and not mask[yy][xx]:
                nb.add((yy, xx))
    return nb


def majority(cnt):
    if not cnt: return None
    mc = cnt.most_common(2)
    if len(mc) > 1 and mc[0][1] == mc[1][1]: return 'tie'
    return mc[0][0]


def feature_values(g, regs, mask, r, feat):
    h, w = H(g), W(g)
    if feat == 'border':
        return [any(y in (0, h - 1) or x in (0, w - 1) for y, x in c) for c in regs]
    if feat == 'size_rank':
        sizes = sorted({len(c) for c in regs}, reverse=True)
        def rk(n):
            if len(sizes) == 1: return 'only'
            if n == sizes[0]: return 'max'
            if n == sizes[-1]: return 'min'
            return '2nd' if n == sizes[1] else 'mid'
        return [rk(len(c)) for c in regs]
    if feat == 'is_rect':
        out = []
        for c in regs:
            ys = [y for y, _ in c]; xs = [x for _, x in c]
            out.append(len(c) == (max(ys) - min(ys) + 1) * (max(xs) - min(xs) + 1))
        return out
    if feat == 'parity':
        return [len(c) % 2 for c in regs]
    if feat == 'seedmaj':
        return [majority(Counter(g[y][x] for y, x in c if g[y][x] != r)) for c in regs]
    wc = dominant_wall(g, r)
    if feat == 'adjmaj':
        return [majority(Counter(g[y][x] for y, x in neighbours(g, c, mask) if g[y][x] != wc)) for c in regs]
    if feat.startswith('adjhas'):
        col = int(feat[6:])
        return [any(g[y][x] == col for y, x in neighbours(g, c, mask)) or any(g[y][x] == col for y, x in c) for c in regs]
    if feat == 'seedrank':   # region holding the most / fewest foreign (non-region-colour) cells
        cnt = [sum(g[y][x] != r for y, x in c) for c in regs]
        mx, mn = max(cnt), min(cnt)
        if mx == mn: return ['only'] * len(regs)
        return ['max' if k == mx and cnt.count(mx) == 1 else 'min' if k == mn else 'mid' for k in cnt]
    raise ValueError(feat)


SELF_FEATS = ('seedmaj', 'adjmaj')


def region_features(g, r, mode, diag, feat, with_border, scope='all'):
    if r == 'bg': r = bg_of(g)
    mask = member_mask(g, r, mode)
    regs = regions(g, mask, diag)
    if not regs or len(regs) > 200: return None
    vals = feature_values(g, regs, mask, r, feat)
    if with_border:
        bs = feature_values(g, regs, mask, r, 'border')
        vals = [(b, v) for b, v in zip(bs, vals)]
    if scope == 'r':   # only the region-colour cells are repainted; seeds/noise inside stay
        regs = [[(y, x) for y, x in c if g[y][x] == r] for c in regs]
    return regs, vals


def base_val(v, with_border):
    return v[1] if with_border else v


def is_col(v):
    return isinstance(v, int) and not isinstance(v, bool)


def skey(v, with_border):
    """In self mode every colour-valued feature shares one table key (its action is 'self' or a constant)."""
    bv = base_val(v, with_border)
    if not is_col(bv): return v
    return (v[0], '*') if with_border else '*'


def candidate_actions(gi, go, cells, wc):
    acts = set()
    if all(gi[y][x] == go[y][x] for y, x in cells): acts.add('keep')
    cs = {go[y][x] for y, x in cells}
    if len(cs) == 1:
        c = cs.pop(); acts.add(c)
        if c == wc: acts.add('W')
    return acts


def induce(train, r, mode, diag, feat, with_border, selfmode, scope):
    table = {}; any_change = False
    for p in train:
        gi, go = p['input'], p['output']
        rf = region_features(gi, r, mode, diag, feat, with_border, scope)
        if rf is None: return None
        regs, vals = rf
        cover = set()
        wc = dominant_wall(gi, bg_of(gi) if r == 'bg' else r)
        for c, v in zip(regs, vals):
            if not c: continue
            cover.update(c)
            acts = candidate_actions(gi, go, c, wc)
            if not acts: return None
            if selfmode:
                bv = base_val(v, with_border)
                if is_col(bv) and bv in acts: acts = acts | {'self'}
                v = skey(v, with_border)
            prev = table.get(v)
            table[v] = acts if prev is None else prev & acts
            if not table[v]: return None
        # every changed cell must lie in some region
        for y in range(H(gi)):
            for x in range(W(gi)):
                if gi[y][x] != go[y][x] and (y, x) not in cover: return None
    fixed = {}
    for v, acts in table.items():
        # prefer keep; else self; else the single consistent constant colour; else the dominant-wall-colour role
        ints = [k for k in acts if isinstance(k, int)]
        a = 'keep' if 'keep' in acts else 'self' if 'self' in acts else ints[0] if len(ints) == 1 else 'W'
        fixed[v] = a
        if a != 'keep': any_change = True
    if not any_change: return None
    return fixed


def apply(g, r, mode, diag, feat, with_border, selfmode, scope, table):
    rf = region_features(g, r, mode, diag, feat, with_border, scope)
    if rf is None: return None
    regs, vals = rf
    wc = dominant_wall(g, bg_of(g) if r == 'bg' else r)
    out = [row[:] for row in g]
    for c, v in zip(regs, vals):
        bv = base_val(v, with_border)
        k = skey(v, with_border) if selfmode else v
        if k not in table: return None
        a = table[k]
        if a == 'keep': continue
        col = wc if a == 'W' else bv if a == 'self' else a
        if not is_col(col): return None
        for y, x in c: out[y][x] = col
    return out


def fam_region_by_property(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    ch = Counter()
    for p in train:
        gi, go = p['input'], p['output']
        for y in range(H(gi)):
            for x in range(W(gi)):
                if gi[y][x] != go[y][x]: ch[gi[y][x]] += 1
    if not ch: return
    rs = [ch.most_common(1)[0][0]]
    if bg_of(i0) not in rs: rs.append(bg_of(i0))
    if len({bg_of(p['input']) for p in train}) > 1: rs.append('bg')   # region colour as a per-grid role
    # colours relevant for adjhas: colours painted in outputs
    painted = set()
    for p in train:
        gi, go = p['input'], p['output']
        painted |= {go[y][x] for y in range(H(gi)) for x in range(W(gi)) if gi[y][x] != go[y][x]}
    feats = ['border', 'size_rank', 'is_rect', 'parity', 'seedrank', 'seedmaj', 'adjmaj'] + ['adjhas%d' % c for c in sorted(painted)][:3]
    from itertools import product
    n = 0
    for r, mode, diag, feat in product(rs, ('col', 'seed', 'wall'), (False, True), feats):
        if mode == 'col' and feat == 'seedmaj': continue
        sm = feat in SELF_FEATS
        for wb, scope in product((False,) if feat == 'border' else (False, True), ('all',) if mode == 'col' else ('all', 'r')):
            t = induce(train, r, mode, diag, feat, wb, sm, scope)
            if t is None: continue
            n += 1
            if n > 40: return
            name = f"region-fill:{feat}{'+border' if wb else ''}[r{r},{mode},{'8' if diag else '4'}{',r-only' if scope == 'r' else ''}]"
            yield (name, 4 + wb, lambda g, a=(r, mode, diag, feat, wb, sm, scope, t): apply(g, *a))

FAMILIES = (fam_region_by_property,)
