"""connect.aligned_pair (+ ray.full_line): straight-line drawing between / through items.

fam_connect_pairs
  Items = same-colour 8-connected objects.  Two items are a pair when their centres lie on a
  common row / column / diagonal (align set induced), they match on an induced key (same shape,
  same colour, or any), and no other item of the same class lies on the segment between them
  (nearest facing partner).  The segment is the run of line cells strictly between the last cell
  of item A and the first cell of item B.  Induced options:
     clear    - segment must be all background (otherwise the pair is not joined)
     paint    - own colour | constant k | halves (A-colour half, k at the midpoint, B-colour half)
     over     - paint background only | paint over everything
     filter   - all items | items on opposite grid borders (line spans the grid)
     base     - keep the input | blank canvas (only joined pairs + segments survive)
     emit     - foreign cells lying on a segment emit a full perpendicular line of their colour
fam_full_lines
  Seeds (objects filtered by an induced shape class) paint their full row and/or column through
  their centre.  Axis: both | row | col | orientation of the seed (horizontal/vertical segment) |
  per-colour table induced from training.  Line colour own | constant.  Crossings of a row line and
  a column line from different seeds: row wins | column wins | constant colour.  Layer: paint
  background only | everything but seeds | everything.  Clip: whole grid | the region (enclosing
  component) around the seed, line across its short side | crop to the largest one-colour
  component's bbox first.
Every parameter combination is verified internally on all training pairs; only exact fits are
yielded (bounded)."""
import sys; sys.path.append('/home/claude/work/widen')
from itertools import product
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox


def _same_shape_io(train):
    return all((H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)


def _changed_colours(train, n=4):
    """Colours painted onto changed cells, most widely used first (pairs containing it, then count)."""
    cs = Counter(); npair = Counter()
    for p in train:
        i, o = p['input'], p['output']
        if (H(i), W(i)) != (H(o), W(o)): continue
        here = set()
        for y in range(H(i)):
            for x in range(W(i)):
                if i[y][x] != o[y][x]: cs[o[y][x]] += 1; here.add(o[y][x])
        for c in here: npair[c] += 1
    incol = {v for p in train for r in p['input'] for v in r}
    return sorted(cs, key=lambda c: (-npair[c], c in incol, -cs[c]))[:n]


# ------------------------------------------------------------------ connect pairs
class _Item:
    __slots__ = ('col', 'cells', 'r2', 'c2', 'shape', 'bb')

    def __init__(self, g, cells):
        self.cells = set(cells); self.col = g[cells[0][0]][cells[0][1]]
        self.bb = bbox(cells); r0, c0, r1, c1 = self.bb
        self.r2, self.c2 = r0 + r1, c0 + c1
        self.shape = tuple(sorted((y - r0, x - c0) for y, x in cells))


def _line_cells(a, b):
    """Integer cells on the line through the two centres, ordered from a to b, strictly between centres
    (endpoints included when integer).  None when not aligned."""
    dr, dc = b.r2 - a.r2, b.c2 - a.c2
    if dr == 0 and dc == 0: return None
    if dr == 0:
        if a.r2 % 2: return None
        y = a.r2 // 2; s = 1 if dc > 0 else -1
        xs = range(-(-a.c2 // 2) if s > 0 else a.c2 // 2, (b.c2 // 2) + s if s > 0 else -(-b.c2 // 2) + s, s)
        return 'orth', [(y, x) for x in xs]
    if dc == 0:
        if a.c2 % 2: return None
        x = a.c2 // 2; s = 1 if dr > 0 else -1
        ys = range(-(-a.r2 // 2) if s > 0 else a.r2 // 2, (b.r2 // 2) + s if s > 0 else -(-b.r2 // 2) + s, s)
        return 'orth', [(y, x) for y in ys]
    if abs(dr) != abs(dc): return None
    if (a.r2 - a.c2) % 2 and (a.r2 + a.c2) % 2: return None
    sr = 1 if dr > 0 else -1; sc = 1 if dc > 0 else -1
    out = []
    y = -(-a.r2 // 2) if sr > 0 else a.r2 // 2
    while (2 * y - b.r2) * sr <= 0:
        x2 = a.c2 + sc * sr * (2 * y - a.r2)
        if x2 % 2 == 0: out.append((y, x2 // 2))
        y += sr
    return 'diag', out


_IC = {}


def _items(g):
    kk = tuple(map(tuple, g))
    if kk not in _IC:
        if len(_IC) > 64: _IC.clear()
        bg = bg_of(g); _IC[kk] = (bg, [_Item(g, cs) for cs in objects(g, bg, True, True)])
    return _IC[kk]


def _pairs(g, key, align, clear, filt, ic=None):
    h, w = H(g), W(g)
    bg, items = _items(g)
    if ic is not None and not any(it.col == ic for it in items): return None
    if len(items) > 80: return None
    owner = {}
    for k, it in enumerate(items):
        for c in it.cells: owner[c] = k
    kf = {'shape': lambda it: (it.col, it.shape), 'colour': lambda it: it.col, 'any': lambda it: 0}[key]
    if filt == 'border':
        def onb(it):
            return {e for y, x in it.cells for e, t in (('t', y == 0), ('b', y == h - 1), ('l', x == 0), ('r', x == w - 1)) if t}
        eb = [onb(it) for it in items]
    res = []
    for ia in range(len(items)):
        for ib in range(ia + 1, len(items)):
            a, b = items[ia], items[ib]
            if ic is not None and (a.col != ic or b.col != ic): continue
            if kf(a) != kf(b): continue
            if filt == 'border':
                ea, ebb = eb[ia], eb[ib]
                if not (('t' in ea and 'b' in ebb) or ('b' in ea and 't' in ebb) or ('l' in ea and 'r' in ebb) or ('r' in ea and 'l' in ebb)):
                    continue
            lc = _line_cells(a, b)
            if lc is None: continue
            kind, cells = lc
            if align == 'row' and a.r2 != b.r2 or align == 'col' and a.c2 != b.c2: continue
            if align in ('orth', 'diag') and kind != align: continue
            ia_last = max([k for k, c in enumerate(cells) if c in a.cells], default=-1)
            ib_first = min([k for k, c in enumerate(cells) if c in b.cells], default=len(cells))
            seg = cells[ia_last + 1:ib_first]
            if not seg: continue
            if any(c in a.cells or c in b.cells for c in seg): continue
            blocked = False
            for c in seg:
                o = owner.get(c)
                if o is not None and o not in (ia, ib) and kf(items[o]) == kf(a): blocked = True; break
                if clear and g[c[0]][c[1]] != bg: blocked = True; break
            if blocked: continue
            res.append((a, b, kind, seg))
    return bg, res


def _render(g, pr, paint, k, over, base, emit):
    bg, prs = pr
    out = [r[:] for r in g] if base == 'keep' else [[bg] * W(g) for _ in range(H(g))]
    if base == 'blank':
        for a, b, _, _ in prs:
            for it in (a, b):
                for y, x in it.cells: out[y][x] = it.col
    emitters = []
    for a, b, kind, seg in prs:
        n = len(seg)
        for j, (y, x) in enumerate(seg):
            if paint == 'own': col = a.col
            elif paint == 'const': col = k
            else:
                if n % 2 == 0: return None
                col = a.col if j < n // 2 else (b.col if j > n // 2 else k)
            if g[y][x] != bg and g[y][x] not in (a.col,):
                emitters.append((y, x, kind, a, b))
            if over == 'bg' and g[y][x] != bg: continue
            out[y][x] = col
    if emit != 'none':
        for y, x, kind, a, b in emitters:
            if kind == 'orth':
                dirs = [(0, 1), (0, -1)] if a.r2 != b.r2 else [(1, 0), (-1, 0)]
            else:
                sr = 1 if b.r2 > a.r2 else -1; sc = 1 if b.c2 > a.c2 else -1
                dirs = [(sr, -sc), (-sr, sc)]
            col = g[y][x]
            for dy, dx in dirs:
                yy, xx = y + dy, x + dx
                while 0 <= yy < H(g) and 0 <= xx < W(g):
                    if emit == 'all' or out[yy][xx] == bg: out[yy][xx] = col
                    yy += dy; xx += dx
    return out


def fam_connect_pairs(train):
    if not _same_shape_io(train): return
    if any(p['input'] == p['output'] for p in train): return
    ks = _changed_colours(train)
    ins = [p['input'] for p in train]; outs = [p['output'] for p in train]
    found = 0
    common = set.intersection(*[{v for r in g for v in r} - {bg_of(g)} for g in ins])
    for ic, key, align, clear, filt in product(sorted(common) + [None], ('shape', 'colour', 'any'), ('orth', 'diag', 'both', 'row', 'col'), (True, False), ('all', 'border')):
        if ic is not None and key == 'any': continue
        prs = []
        for g in ins:
            pr = _pairs(g, key, align, clear, filt, ic)
            if pr is None or not pr[1]: prs = None; break
            prs.append(pr)
        if prs is None: continue
        fgseg = any(g[y][x] != pr[0] for g, pr in zip(ins, prs) for *_, seg in pr[1] for y, x in seg)
        paints = [('own', None)] + [('const', k) for k in ks] + [('halves', k) for k in ks]
        for (paint, k), over, base, emit in product(paints, ('bg', 'all'), ('keep', 'blank'), ('none', 'bg', 'all')):
            if base == 'blank' and filt != 'border': continue
            if not fgseg and (over == 'all' or emit != 'none'): continue
            if all(_render(g, pr, paint, k, over, base, emit) == o for g, pr, o in zip(ins, prs, outs)):
                def fn(g, key=key, align=align, clear=clear, filt=filt, paint=paint, k=k, over=over, base=base, emit=emit, ic=ic):
                    pr = _pairs(g, key, align, clear, filt, ic)
                    if pr is None or not pr[1]: return None
                    return _render(g, pr, paint, k, over, base, emit)
                yield (f"connect-pairs[items={ic},key={key},align={align},clear={int(clear)},filt={filt},paint={paint}{'' if k is None else k},"
                       f"over={over},base={base},emit={emit}]", 4, fn)
                found += 1
                if found >= 6: return


# ------------------------------------------------------------------ full lines
def _seed_ok(cls, cells):
    r0, c0, r1, c1 = bbox(cells); hh, ww = r1 - r0 + 1, c1 - c0 + 1; n = len(cells)
    if cls == 'all': return True
    if cls == 'single': return n == 1
    if cls == 'segment': return n >= 2 and (hh == 1 or ww == 1)
    if cls == 'block': return hh >= 2 and ww >= 2 and n == hh * ww
    if cls == 'nonblock': return not (hh >= 2 and ww >= 2 and n == hh * ww) and n < 0.2 * 900
    return False


def _crop_main(g):
    """Bbox of the largest one-colour component, trimmed of edge rows/cols that are mostly another colour."""
    obs = objects(g, -1, False, True)
    big = max(obs, key=len); c = g[big[0][0]][big[0][1]]
    r0, c0, r1, c1 = bbox(big)
    frac = lambda cells: sum(g[y][x] == c for y, x in cells) / len(cells)
    while r1 > r0 and c1 > c0:
        e = [(frac([(r0, x) for x in range(c0, c1 + 1)]), 't'), (frac([(r1, x) for x in range(c0, c1 + 1)]), 'b'),
             (frac([(y, c0) for y in range(r0, r1 + 1)]), 'l'), (frac([(y, c1) for y in range(r0, r1 + 1)]), 'r')]
        f, side = min(e)
        if f >= 0.5: break
        if side == 't': r0 += 1
        elif side == 'b': r1 -= 1
        elif side == 'l': c0 += 1
        else: c1 -= 1
    if r1 - r0 < 1 or c1 - c0 < 1: return None
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _seeds(g, cls, clip):
    bg = bg_of(g)
    obs = objects(g, bg, False, True)
    if len(obs) > 60: return None
    seeds = []
    for cs in obs:
        if not _seed_ok(cls, cs): continue
        r0, c0, r1, c1 = bbox(cs)
        col = g[cs[0][0]][cs[0][1]]
        hh, ww = r1 - r0 + 1, c1 - c0 + 1
        orient = 'row' if hh == 1 and ww > 1 else 'col' if ww == 1 and hh > 1 else 'both'
        ry = (r0 + r1) / 2; cx = (c0 + c1) / 2
        region = (0, 0, H(g) - 1, W(g) - 1)
        if clip == 'region':
            if len(cs) != 1: continue
            y, x = cs[0]
            nb = Counter(g[yy][xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1))
                         if 0 <= yy < H(g) and 0 <= xx < W(g) and g[yy][xx] != col)
            if not nb: return None
            rc = nb.most_common(1)[0][0]
            comp = [o for o in objects(g, -1, False, True) if g[o[0][0]][o[0][1]] == rc and any(abs(a - y) + abs(b - x) == 1 for a, b in o)]
            if not comp: return None
            region = bbox(max(comp, key=len))
        seeds.append({'cells': set(cs), 'col': col, 'orient': orient, 'r': ry, 'c': cx, 'region': region})
    return bg, seeds


def _axes(s, amode, table):
    if amode in ('row', 'col'): return {amode}
    if amode == 'both': return {'row', 'col'}
    if amode == 'orient': return {s['orient']} if s['orient'] != 'both' else {'row', 'col'}
    if amode == 'short':
        r0, c0, r1, c1 = s['region']
        return {'col'} if (r1 - r0) < (c1 - c0) else {'row'} if (r1 - r0) > (c1 - c0) else set()
    if amode == 'table':
        return table.get(s['col'])


def _draw_lines(g, sd, amode, table, lcol, cross, layer):
    bg, seeds = sd
    h, w = H(g), W(g)
    rowc, colc = {}, {}
    seedcells = {}
    for k, s in enumerate(seeds):
        for c in s['cells']: seedcells[c] = k
    for k, s in enumerate(seeds):
        ax = _axes(s, amode, table)
        if ax is None: return None
        col = s['col'] if lcol is None else lcol
        r0, c0, r1, c1 = s['region']
        if 'row' in ax:
            if s['r'] != int(s['r']): return None
            y = int(s['r'])
            for x in range(c0, c1 + 1): rowc.setdefault((y, x), (k, col))
        if 'col' in ax:
            if s['c'] != int(s['c']): return None
            x = int(s['c'])
            for y in range(r0, r1 + 1): colc.setdefault((y, x), (k, col))
    out = [r[:] for r in g]
    for cell in set(rowc) | set(colc):
        y, x = cell
        if layer == 'bg' and g[y][x] != bg: continue
        if layer == 'nonseed' and cell in seedcells: continue
        a, b = rowc.get(cell), colc.get(cell)
        if a and b and a[0] != b[0]:
            if cross == 'row': v = a[1]
            elif cross == 'col': v = b[1]
            elif cross == 'bg': v = bg
            else: v = cross
        else: v = (a or b)[1]
        out[y][x] = v
    return out


def _induce_table(ins, sds, outs, lcol):
    table = {}
    for g, sd, o in zip(ins, sds, outs):
        for s in sd[1]:
            col = s['col'] if lcol is None else lcol
            ax = set()
            r0, c0, r1, c1 = s['region']
            if s['r'] == int(s['r']):
                y = int(s['r']); n = c1 - c0 + 1
                if sum(o[y][x] == col for x in range(c0, c1 + 1)) * 2 > n: ax.add('row')
            if s['c'] == int(s['c']):
                x = int(s['c']); n = r1 - r0 + 1
                if sum(o[y][x] == col for y in range(r0, r1 + 1)) * 2 > n: ax.add('col')
            if table.setdefault(s['col'], ax) != ax: return None
    if len(set(map(frozenset, table.values()))) < 2: return None
    return table


def fam_full_lines(train):
    ins = [p['input'] for p in train]; outs = [p['output'] for p in train]
    if any(i == o for i, o in zip(ins, outs)): return
    crops = [False]
    if not _same_shape_io(train):
        cr = [_crop_main(g) for g in ins]
        if any(c is None or (H(c), W(c)) != (H(o), W(o)) for c, o in zip(cr, outs)): return
        crops = [True]; ins = cr
    ks = _changed_colours([{'input': i, 'output': o} for i, o in zip(ins, outs)])
    found = 0
    for crop in crops:
        for cls, clip in product(('all', 'single', 'segment', 'block', 'nonblock'), ('none', 'region')):
            sds = [_seeds(g, cls, clip) for g in ins]
            if any(sd is None or not sd[1] for sd in sds): continue
            amodes = ('both', 'row', 'col', 'orient', 'table') if clip == 'none' else ('short',)
            for amode, lcol in product(amodes, [None] + ks):
                table = None
                if amode == 'table':
                    table = _induce_table(ins, sds, outs, lcol)
                    if table is None: continue
                for cross, layer in product(['row', 'col', 'bg'] + ks, ('bg', 'nonseed', 'all')):
                    ok = True
                    for g, sd, o in zip(ins, sds, outs):
                        if _draw_lines(g, sd, amode, table, lcol, cross, layer) != o: ok = False; break
                    if not ok: continue
                    def fn(g, crop=crop, cls=cls, clip=clip, amode=amode, table=table, lcol=lcol, cross=cross, layer=layer):
                        if crop:
                            g = _crop_main(g)
                            if g is None: return None
                        sd = _seeds(g, cls, clip)
                        if sd is None or not sd[1]: return None
                        return _draw_lines(g, sd, amode, table, lcol, cross, layer)
                    yield (f"full-lines[crop={int(crop)},seed={cls},clip={clip},axis={amode},col={lcol},cross={cross},layer={layer}]", 4, fn)
                    found += 1
                    if found >= 6: return


FAMILIES = (fam_connect_pairs, fam_full_lines)
