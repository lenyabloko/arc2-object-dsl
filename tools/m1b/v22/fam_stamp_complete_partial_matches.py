"""STAMP.complete_partial_matches: complete every partial copy of a reference template.

One parametrised primitive.  A complete reference template (a multi-colour cluster, or the largest
shape) is present in the input; every other configuration that equals a part of the template, under a
transform group G and a block scale s, is completed in place by painting the template's missing cells.

Parameters, all induced from the training pairs (the family fits them internally and yields only
programs that reproduce every training output exactly):
  dom     : grid | lattice (grid-lines compress the picture to a cell grid; completion runs on cells)
  tsel    : which clusters are templates
            P      clusters containing a colour that training outputs add (optionally cropped to the
                   bbox of those colours, trimming touching noise)
            maxcol clusters with the maximal number of distinct colours (>= 2)
            big    the single cluster with the most (colours, scaled units)
            (clusters = non-bg cells linked at Chebyshev distance <= d, d in {1,2})
  krole   : which template colours form the key K that a fragment must contain completely
            fixed (template minus added colours) | least (least frequent colours) |
            nonmajor (all but the most frequent) | free (any present subset of cells; optionally
            colour-closed: each present colour complete) | none (with sigma=free, pure shape match)
  sigma   : id | free  (non-key colours may be recoloured by the fragment's own colour)
  G       : id | D4 ;  scale: 1 | 1..5 (each fragment block-scaled);  clip: template may leave the grid
  other   : bg  (non-key template cells must be bg or already the template colour; paint bg only)
            notK (non-key cells must merely not hold a key colour; paint over them)
  closure : none | comp (matched cells are whole 8-components) | class (matched colour classes whole)
Matches whose matched-cell set is strictly contained in another match are discarded; conflicting paints
reject the program.
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
import time
from collections import Counter
from gdsl import H, W, bg_of

MAXC, MAXT = 64, 8   # a reference template is a small object; many/huge candidates -> no template
TRANS = [(sw, fy, fx) for sw in (0, 1) for fy in (0, 1) for fx in (0, 1)]


# ------------------------------------------------------------------ lattice domain
def lattice(g):
    """Return (line colour, row runs, col runs, compressed grid) or None."""
    h, w = H(g), W(g)
    for L in {v for r in g for v in r}:
        rows = [y for y in range(h) if all(v == L for v in g[y])]
        cols = [x for x in range(w) if all(g[y][x] == L for y in range(h))]
        if not rows or not cols or len(rows) == h or len(cols) == w: continue
        rr = runs([y for y in range(h) if y not in set(rows)])
        cc = runs([x for x in range(w) if x not in set(cols)])
        if len(rr) < 2 or len(cc) < 2: continue
        comp = []
        for a, b in rr:
            row = []
            for c, d in cc:
                vs = {g[y][x] for y in range(a, b + 1) for x in range(c, d + 1)}
                if len(vs) != 1: return None
                row.append(vs.pop())
            comp.append(row)
        return L, rr, cc, comp
    return None


def runs(idx):
    out = []
    for i in idx:
        if out and out[-1][1] == i - 1: out[-1][1] = i
        else: out.append([i, i])
    return [tuple(r) for r in out]


def expand(g, lat, comp):
    L, rr, cc, _ = lat
    out = [r[:] for r in g]
    for i, (a, b) in enumerate(rr):
        for j, (c, d) in enumerate(cc):
            for y in range(a, b + 1):
                for x in range(c, d + 1): out[y][x] = comp[i][j]
    return out


# ------------------------------------------------------------------ templates
def clusters(g, bg, d):
    h, w = H(g), W(g); seen = set(); out = []
    for r in range(h):
        for c in range(w):
            if g[r][c] == bg or (r, c) in seen: continue
            st = [(r, c)]; seen.add((r, c)); cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy in range(-d, d + 1):
                    for dx in range(-d, d + 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and g[yy][xx] != bg:
                            seen.add((yy, xx)); st.append((yy, xx))
            out.append(cells)
    return out


def block_scale(g, cells):
    """Largest s such that the cells are a union of aligned s x s uniform blocks."""
    cs = set(cells); y0 = min(y for y, _ in cells); x0 = min(x for _, x in cells)
    for s in (5, 4, 3, 2):
        ok = True
        for y, x in cells:
            by, bx = y0 + (y - y0) // s * s, x0 + (x - x0) // s * s
            if any((by + i, bx + j) not in cs or g[by + i][bx + j] != g[y][x] for i in range(s) for j in range(s)):
                ok = False; break
        if ok: return s
    return 1


def templates(g, bg, tsel, d, crop, pfix):
    cl = clusters(g, bg, d)
    if tsel == 'P':
        T = []
        for c in cl:
            pc = [(y, x) for y, x in c if g[y][x] in pfix]
            if not pc: continue
            if crop:
                y0 = min(y for y, _ in pc); y1 = max(y for y, _ in pc)
                x0 = min(x for _, x in pc); x1 = max(x for _, x in pc)
                c = [(y, x) for y, x in c if y0 <= y <= y1 and x0 <= x <= x1]
            T.append(c)
    elif tsel == 'maxcol':
        nc = [len({g[y][x] for y, x in c}) for c in cl]
        m = max(nc, default=0)
        if m < 2: return []
        T = [c for c, n in zip(cl, nc) if n == m]
    else:  # big
        key = lambda c: (len({g[y][x] for y, x in c}), len(c) / block_scale(g, c) ** 2)
        if not cl: return []
        ks = [key(c) for c in cl]; m = max(ks)
        if ks.count(m) != 1: return []
        T = [cl[ks.index(m)]]
    out = []; seen = set()
    if len(T) > MAXT: return []
    for c in T:
        if len(c) > MAXC: return []
        y0 = min(y for y, _ in c); x0 = min(x for _, x in c)
        t = tuple(sorted((y - y0, x - x0, g[y][x]) for y, x in c))
        if t not in seen: seen.add(t); out.append(t)
    return out


def key_colours(t, krole, pfix):
    cnt = Counter(c for _, _, c in t)
    if krole == 'fixed': K = set(cnt) - pfix
    elif krole == 'least':
        m = min(cnt.values()); K = {c for c in cnt if cnt[c] == m}
        if len(K) == len(cnt): return None
    elif krole == 'nonmajor':
        m = max(cnt.values()); top = [c for c in cnt if cnt[c] == m]
        if len(top) != 1: return None
        K = set(cnt) - set(top)
    else: K = set()
    if krole in ('fixed', 'least', 'nonmajor') and (not K or K == set(cnt)): return None
    return K


def variants(t, G):
    out = []; seen = set()
    for tr in (TRANS if G == 'D4' else TRANS[:1]):
        sw, fy, fx = tr
        h = max(a for a, _, _ in t) + 1; w = max(b for _, b, _ in t) + 1
        v = []
        for a, b, c in t:
            a2 = h - 1 - a if fy else a; b2 = w - 1 - b if fx else b
            v.append((b2, a2, c) if sw else (a2, b2, c))
        v = tuple(sorted(v))
        if v not in seen: seen.add(v); out.append(v)
    return out


# ------------------------------------------------------------------ matching
def block_tls(g, bg, s):
    h, w = H(g), W(g)
    if s == 1: return [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg]
    return [(y, x) for y in range(h - s + 1) for x in range(w - s + 1) if g[y][x] != bg
            and all(g[y + i][x + j] == g[y][x] for i in range(s) for j in range(s))]


def raw_matches(g, bg, T, B):
    """All placements of all templates (every scale, clipping allowed); filters are applied later.
    Record = (M, foot, paints, s, offgrid, missing colours, present colours)."""
    h, w = H(g), W(g); res = []
    tls = {s: block_tls(g, bg, s) for s in SCALES}
    for t in T:
        K = key_colours(t, B['krole'], B['pfix'])
        if K is None: continue
        for v in variants(t, B['G']):
            kc = [x for x in v if x[2] in K]
            for s in SCALES:
                if not tls[s]: continue
                if kc:
                    a0, b0, c0 = kc[0]
                    origins = {(y - a0 * s, x - b0 * s) for y, x in tls[s] if g[y][x] == c0}
                elif B['sigma'] == 'id':
                    origins = {(y - a * s, x - b * s) for y, x in tls[s] for a, b, c in v if g[y][x] == c}
                else:
                    origins = {(y - a * s, x - b * s) for y, x in tls[s] for a, b, _ in v}
                for oy, ox in origins:
                    r = place(g, bg, v, K, s, oy, ox, B, h, w)
                    if r: res.append(r)
    return res


def place(g, bg, v, K, s, oy, ox, B, h, w):
    other, sigma = B['other'], B['sigma']
    M = set(); miss = []; present = set(); sig = {}; foot = set(); off = False
    for a, b, c in v:
        vals = set()
        for i in range(s):
            for j in range(s):
                y, x = oy + a * s + i, ox + b * s + j
                if 0 <= y < h and 0 <= x < w: vals.add(g[y][x]); foot.add((y, x))
                elif c in K: return None
                else: off = True
        if c in K:
            if vals != {c}: return None
            M.update((oy + a * s + i, ox + b * s + j) for i in range(s) for j in range(s)); continue
        if not vals: continue
        if other == 'notK':
            if vals & K: return None
            miss.append((a, b, c)); continue
        if len(vals) != 1: return None
        u = next(iter(vals))
        if u == bg: miss.append((a, b, c)); continue
        if sigma == 'id':
            if u != c: return None
        elif u in K or sig.setdefault(c, u) != u: return None
        present.add(c)
        M.update((y, x) for y in range(oy + a * s, oy + a * s + s) for x in range(ox + b * s, ox + b * s + s)
                 if 0 <= y < h and 0 <= x < w)
    if not miss or not M: return None
    if len(set(sig.values())) != len(sig): return None
    paints = {}
    for a, b, c in miss:
        col = sig.get(c, c)
        for i in range(s):
            for j in range(s):
                y, x = oy + a * s + i, ox + b * s + j
                if 0 <= y < h and 0 <= x < w and g[y][x] != col: paints[(y, x)] = col
    if not paints: return None
    return (frozenset(M), frozenset(foot), tuple(sorted(paints.items())), s, off,
            frozenset(c for _, _, c in miss), frozenset(present))


def closed(g, bg, M, foot, closure):
    h, w = H(g), W(g)
    if closure == 'comp':
        for y, x in M:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and g[yy][xx] != bg and (yy, xx) not in foot: return False
    elif closure == 'class':
        cols = {g[y][x] for y, x in M}
        if any(g[y][x] in cols and (y, x) not in M for y in range(h) for x in range(w)): return False
    return True


def finalize(g, bg, recs, F):
    byM = {}
    for M, foot, pt, s, off, missc, presc in recs:
        if s > F['maxs'] or (off and not F['clip']): continue
        if F['colclosed'] and missc & presc: continue
        if not closed(g, bg, M, foot, F['closure']): continue
        byM.setdefault(M, set()).add(pt)
    keys = [M for M in byM if len(byM[M]) == 1]          # ambiguous fragments are left alone
    keys = [M for M in keys if not any(M < N for N in keys)]
    if not keys: return None
    out = [r[:] for r in g]; done = {}
    for M in keys:
        for (y, x), c in next(iter(byM[M])):
            if done.setdefault((y, x), c) != c: return None
            out[y][x] = c
    return out


def prepare(g, B):
    """-> (work grid, lattice info, bg, raw records) or None."""
    lat = None; work = g
    if B['dom'] == 'lattice':
        lat = lattice(g)
        if lat is None: return None
        work = lat[3]
    bg = bg_of(work)
    T = templates(work, bg, B['tsel'], B['d'], B['crop'], B['pfix'])
    if not T: return None
    return work, lat, bg, raw_matches(work, bg, T, B)


def apply(prep, F):
    if prep is None: return None
    work, lat, bg, recs = prep[:4]
    out = finalize(work, bg, recs, F)
    if out is None or out == work: return None
    return expand(prep[4], lat, out) if lat else out


def run_cfg(g, B, F):
    prep = prepare(g, B)
    if prep is None: return None
    prep = prep + (g,)
    return apply(prep, F)


# ------------------------------------------------------------------ family
SCALES = (1, 2, 3, 4, 5)
SEL = (('P', 1, True), ('P', 1, False), ('maxcol', 1, False), ('big', 1, False),
       ('P', 2, False), ('maxcol', 2, False), ('big', 2, False))


def bases(pfix, allbg, has_lat):
    others = ['bg'] if allbg else ['notK']
    for dom in ['grid'] + (['lattice'] if has_lat else []):
        for tsel, d, crop in SEL:
            if tsel == 'P' and not pfix: continue
            for krole, sigma in (('fixed', 'id'), ('least', 'id'), ('nonmajor', 'id'), ('least', 'free'),
                                 ('nonmajor', 'free'), ('free', 'id'), ('none', 'free')):
                if (krole == 'fixed') != (tsel == 'P'): continue
                for other in others:
                    if other == 'notK' and krole in ('free', 'none'): continue
                    for G in ('id', 'D4'):
                        yield dict(dom=dom, tsel=tsel, d=d, crop=crop, krole=krole, sigma=sigma, other=other,
                                   G=G, pfix=pfix)


def filters(B):
    anchorless = B['krole'] in ('free', 'none')
    for closure in ('none', 'comp', 'class'):
        if anchorless and closure == 'none': continue
        if B['other'] == 'notK' and closure != 'none': continue
        for colclosed in ((True, False) if B['krole'] == 'free' else (False,)):
            for maxs, clip in ((1, False), (1, True), (5, False), (5, True)):
                yield dict(closure=closure, colclosed=colclosed, maxs=maxs, clip=clip)


def fam_complete_partial(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    pfix = set(); allbg = True; has_lat = True
    for p in train:
        i, o = p['input'], p['output']
        if (H(i), W(i)) != (H(o), W(o)): return
        bg = bg_of(i); ch = 0
        for y in range(H(i)):
            for x in range(W(i)):
                if i[y][x] != o[y][x]:
                    ch += 1; pfix.add(o[y][x])
                    if i[y][x] != bg: allbg = False
        if ch == 0: return
        if lattice(i) is None: has_lat = False
    pfix = frozenset(pfix)
    t0 = time.time(); found = 0
    for B in bases(pfix, allbg, has_lat):
        if time.time() - t0 > BUDGET: return
        preps = []
        for p in train:
            try: pr = prepare(p['input'], B)
            except Exception: pr = None
            if pr is None or not pr[3]: preps = None; break
            preps.append(pr + (p['input'],))
            if time.time() - t0 > BUDGET: return
        if not preps: continue
        for F in filters(B):
            if all(apply(pr, F) == p['output'] for pr, p in zip(preps, train)):
                name = ("complete-partial[{dom},{tsel}{d}{c},K={krole},sig={sigma},{other},G={G},"
                        "{closure}{cc},s<={maxs},clip={clip}]").format(c='crop' if B['crop'] else '',
                        cc='+colclosed' if F['colclosed'] else '', **B, **F)
                yield (name, 4, lambda g, B=B, F=F: run_cfg(g, B, F))
                found += 1
                break
        if found >= 3: return


BUDGET = 1e9  # deterministic: wall-clock budget removed (Kaggle parity)


# ------------------------------------------------------------------ variant A: divided canvas, mirrored + scaled
def dividers(g):
    """a single full row and a single full column of one colour L -> (L, row, col)."""
    h, w = H(g), W(g)
    for L in {v for r in g for v in r}:
        rows = [y for y in range(h) if all(v == L for v in g[y])]
        cols = [x for x in range(w) if all(g[y][x] == L for y in range(h))]
        if len(rows) == 1 and len(cols) == 1: return L, rows[0], cols[0]
    return None


def _solid_rect(cells):
    y0 = min(y for y, _ in cells); y1 = max(y for y, _ in cells)
    x0 = min(x for _, x in cells); x1 = max(x for _, x in cells)
    return (y0, x0, y1, x1) if len(set(cells)) == (y1 - y0 + 1) * (x1 - x0 + 1) else None


def mirror_stamp(g, mirror, clip=False):
    """Quadrants split by a divider cross.  One quadrant holds the template: a solid single-colour core
    with decorations; every other object is a bare core (same colour, any size).  The decorations are
    re-drawn around each bare core, scaled by (core size / template core size) and, with mirror=True,
    reflected across each divider that separates the core from the template."""
    dv = dividers(g)
    if dv is None: return None
    L, ry, cx = dv
    bg = bg_of(g)
    # the divider cross would join everything: cluster with the divider row/column blanked out
    gg = [[bg if (y == ry or x == cx) else g[y][x] for x in range(W(g))] for y in range(H(g))]
    obs = clusters(gg, bg, 1)
    multi = [c for c in obs if len({g[y][x] for y, x in c}) > 1]
    if len(multi) != 1: return None
    tpl = multi[0]; bare = [c for c in obs if c is not tpl]
    kc = {g[y][x] for c in bare for y, x in c}
    if len(kc) != 1 or not bare: return None
    K = kc.pop()
    core = [(y, x) for y, x in tpl if g[y][x] == K]
    cr = _solid_rect(core)
    if cr is None: return None
    cy0, cx0, cy1, cx1 = cr; ch, cw = cy1 - cy0 + 1, cx1 - cx0 + 1
    sb = block_scale(g, tpl)
    while sb > 1 and (ch % sb or cw % sb or (cy0 - min(y for y, _ in tpl)) % sb
                      or (cx0 - min(x for _, x in tpl)) % sb): sb -= 1
    bh, bw = ch // sb, cw // sb
    deco = {}
    for y, x in tpl:
        if g[y][x] == K: continue
        a, b = (y - cy0), (x - cx0)
        deco[(a // sb if a >= 0 else -((-a + sb - 1) // sb), b // sb if b >= 0 else -((-b + sb - 1) // sb))] = g[y][x]
    tside = (cy0 < ry, cx0 < cx)
    out = [r[:] for r in g]; n = 0
    for c in bare:
        r = _solid_rect(c)
        if r is None: return None
        y0, x0, y1, x1 = r; hh, ww = y1 - y0 + 1, x1 - x0 + 1
        if hh % bh or ww % bw or hh // bh != ww // bw: return None
        u = hh // bh
        fy = mirror and (y0 < ry) != tside[0]; fx = mirror and (x0 < cx) != tside[1]
        for (a, b), col in deco.items():
            a2 = bh - 1 - a if fy else a; b2 = bw - 1 - b if fx else b
            for i in range(u):
                for j in range(u):
                    yy, xx = y0 + a2 * u + i, x0 + b2 * u + j
                    if not (0 <= yy < H(g) and 0 <= xx < W(g)):
                        if clip: continue
                        return None
                    if g[yy][xx] != bg: return None
                    out[yy][xx] = col; n += 1
    return out if n else None


def fam_mirror_scaled_stamp(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)) or dividers(i0) is None: return
    for mirror in (True, False):
        for clip in (False, True):
            yield ("complete-partial:divided[G=%s,scale=core,clip=%s]" % ("mirror" if mirror else "id", clip), 5,
                   lambda g, mirror=mirror, clip=clip: mirror_stamp(g, mirror, clip))


# ------------------------------------------------------------------ variant B: tile lattice, self template
def tile_lattice(g):
    """grid of equal k x k tiles separated by 1-wide lines of colour L -> (L, k, rows, cols, tiles)."""
    h, w = H(g), W(g)
    L = g[0][0]
    rows = [y for y in range(h) if all(v == L for v in g[y])]
    cols = [x for x in range(w) if all(g[y][x] == L for y in range(h))]
    if len(rows) < 3 or len(cols) < 3: return None
    k = rows[1] - rows[0] - 1
    if k < 2 or any(b - a - 1 != k for a, b in zip(rows, rows[1:])) or any(b - a - 1 != k for a, b in zip(cols, cols[1:])):
        return None
    tiles = [[tuple(tuple(g[y][x] for x in range(c + 1, c + 1 + k)) for y in range(r + 1, r + 1 + k))
              for c in cols[:-1]] for r in rows[:-1]]
    return L, k, rows, cols, tiles


def lattice_self_complete(g, mrole):
    """Tiles are all one common pattern except a few 'alt' tiles of one other pattern.  The alt tile's
    own mask (cells of its majority colour, or of the colour absent from the common tile) is the meta
    template: alt tiles are added so that the set of alt positions becomes that mask, placed at the
    unique offset that contains every existing alt tile."""
    lt = tile_lattice(g)
    if lt is None: return None
    L, k, rows, cols, tiles = lt
    cnt = Counter(t for r in tiles for t in r)
    if len(cnt) != 2: return None
    (common, _), (alt, na) = cnt.most_common()
    if na == 0: return None
    ac = Counter(v for r in alt for v in r)
    if mrole == 'major':
        m = ac.most_common()
        if len(m) < 2 or m[0][1] == m[1][1]: return None
        mc = m[0][0]
    else:
        new = set(ac) - {v for r in common for v in r}
        if len(new) != 1: return None
        mc = new.pop()
    mask = [(a, b) for a in range(k) for b in range(k) if alt[a][b] == mc]
    pos = {(i, j) for i, r in enumerate(tiles) for j, t in enumerate(r) if t == alt}
    R, C = len(tiles), len(tiles[0])
    fits = []
    for oy in range(-k + 1, R):
        for ox in range(-k + 1, C):
            ms = {(oy + a, ox + b) for a, b in mask}
            if pos <= ms and all(0 <= y < R and 0 <= x < C for y, x in ms): fits.append(ms)
    if len(fits) != 1 or fits[0] == pos: return None
    out = [r[:] for r in g]
    for i, j in fits[0]:
        for a in range(k):
            for b in range(k): out[rows[i] + 1 + a][cols[j] + 1 + b] = alt[a][b]
    return out


def fam_lattice_self_template(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if (H(i0), W(i0)) != (H(o0), W(o0)) or tile_lattice(i0) is None: return
    for mrole in ('major', 'new'):
        yield ("complete-partial:lattice-self[mask=%s]" % mrole, 5,
               lambda g, mrole=mrole: lattice_self_complete(g, mrole))


FAMILIES = (fam_complete_partial, fam_mirror_scaled_stamp, fam_lattice_self_template)
