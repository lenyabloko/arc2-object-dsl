"""recolour.by_colour_map + recolour.by_key_position: recolour target cells from an in-grid key.

One primitive  out = paint(targets, K[corr(target)])  where the key K is read from the input grid and
indexed either by COLOUR (a colour map phi) or by POSITION (the key cell that corresponds to the target).

fam_key_position   (index by position; all parameters induced from the training pairs)
  T      : target colour role  rank0 | rank1 (by count among non-bg colours) | const c (same in every pair)
  frame  : drop the dominant non-target colour from the key (key sits inside a frame / behind lines) or not
  corr   : row | col           target cell takes the key colour found in its own row / column
           obj4 | obj8          each target component <-> one key cell, matched by normalised position
           rank-x | rank-y      target split into column (row) bands of identical profile, ordered,
                                matched to the key colours ordered the same way
           scaled               target bbox scaled onto the (rank-compressed) key matrix, per cell
           onoff                2-line key: line 0 colours target cells, line 1 colours the rest (per column/row)
  post   : keep | erase (key cells -> bg) | crop (to the target bbox; scaled/onoff)
fam_legend_map     (index by colour: phi read from legend pairs)
  source : dominoes (isolated 2-cell pairs) | rows / cols of an isolated 2-wide multicolour block
  dir    : fwd a->b | rev b->a | swap | chain (block rows applied one after another)
  scope  : whole grid outside the key | crop to the largest remaining object
fam_key_erase      phi = {k -> bg}, k = the single colour shown in a corner box cut off by a line.
fam_complement     binary complement (fg <-> bg) on scope whole | lattice blocks | object bbox,
                   the global colour-map post-step then names the new colour.
fam_variant_swap   repeated composite objects come in exactly two variants (up to integer scale);
                   every object is replaced by the other variant, aligned on their common part.
"""
import sys
sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox, crop

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _same_shape(train):
    return all((H(p["input"]), W(p["input"])) == (H(p["output"]), W(p["output"])) for p in train)


def _comps(cells, diag):
    """connected components of a set of cells"""
    cells = set(cells); out = []
    nb = N4 + (((1, 1), (1, -1), (-1, 1), (-1, -1)) if diag else ())
    while cells:
        s = cells.pop(); st = [s]; comp = [s]
        while st:
            y, x = st.pop()
            for dy, dx in nb:
                p = (y + dy, x + dx)
                if p in cells:
                    cells.remove(p); st.append(p); comp.append(p)
        out.append(comp)
    return out


# ================================================================== key by position
def _ranked(g, bg):
    cnt = Counter(v for r in g for v in r if v != bg)
    return [c for c, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))]


def _target_truth(p):
    """input colour(s) of the target: colours of changed cells (same shape) or input colours absent in output"""
    i, o = p["input"], p["output"]
    if (H(i), W(i)) == (H(o), W(o)):
        return {i[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]}
    ci = {v for r in i for v in r}; co = {v for r in o for v in r}
    return ci - co - {bg_of(i)}


def _t_roles(train):
    roles = []
    truths = [_target_truth(p) for p in train]
    for rk in (0, 1):
        ok = True
        for p, t in zip(train, truths):
            rs = _ranked(p["input"], bg_of(p["input"]))
            if len(rs) <= rk or rs[rk] not in t: ok = False; break
        if ok: roles.append(("rank%d" % rk, rk))
    common = set.intersection(*[set(t) for t in truths]) if truths else set()
    for c in sorted(common):
        roles.append(("const%d" % c, ("c", c)))
    return roles


def _target_colour(g, bg, role):
    if isinstance(role, tuple): return role[1]
    rs = _ranked(g, bg)
    return rs[role] if len(rs) > role else None


def _key(g, bg, T, frame):
    cells = {(y, x): g[y][x] for y in range(H(g)) for x in range(W(g)) if g[y][x] not in (bg, T)}
    if frame:
        cnt = Counter(cells.values())
        if len(cnt) < 2: return None
        F = cnt.most_common(1)[0][0]
        cells = {p: v for p, v in cells.items() if v != F}
    return cells or None


def _norm(pts):
    ys = [p[0] for p in pts]; xs = [p[1] for p in pts]
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    return [((y - y0) / (y1 - y0) if y1 > y0 else 0.0, (x - x0) / (x1 - x0) if x1 > x0 else 0.0) for y, x in pts]


def _match(a, b):
    """greedy min-distance bijection between two equal-size point lists -> list idx_a -> idx_b"""
    na, nb = _norm(a), _norm(b)
    pairs = sorted(((ya - yb) ** 2 + (xa - xb) ** 2, i, j) for i, (ya, xa) in enumerate(na) for j, (yb, xb) in enumerate(nb))
    ma, used = {}, set()
    for d, i, j in pairs:
        if i in ma or j in used: continue
        ma[i] = j; used.add(j)
    return ma


def _compress(cells):
    """rank-compress key cells into a matrix (None = hole)"""
    rows = sorted({y for y, _ in cells}); cols = sorted({x for _, x in cells})
    ri = {r: k for k, r in enumerate(rows)}; ci = {c: k for k, c in enumerate(cols)}
    M = [[None] * len(cols) for _ in rows]
    for (y, x), v in cells.items(): M[ri[y]][ci[x]] = v
    return M


def _bands(tc, axis):
    """group contiguous columns (axis=1) / rows (axis=0) holding target cells with identical profile"""
    prof = {}
    for y, x in tc:
        k, o = (x, y) if axis == 1 else (y, x)
        prof.setdefault(k, set()).add(o)
    bands = []
    for k in sorted(prof):
        if bands and bands[-1][-1] == k - 1 and prof[bands[-1][-1]] == prof[k]: bands[-1].append(k)
        else: bands.append([k])
    return bands, prof


def _apply_pos(g, role, frame, corr, post, diag=False, fill=None):
    bg = bg_of(g); T = _target_colour(g, bg, role)
    if T is None: return None
    if T == bg:
        cnt = Counter(v for r in g for v in r if v != T)
        if not cnt: return None
        bg = cnt.most_common(1)[0][0]
    tc = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == T]
    if not tc: return None
    K = _key(g, bg, T, frame)
    if not K: return None
    out = [r[:] for r in g]
    if corr in ("row", "col"):
        ax = 0 if corr == "row" else 1
        line = {}
        for p, v in K.items(): line.setdefault(p[ax], set()).add(v)
        for p in tc:
            s = line.get(p[ax])
            if not s or len(s) != 1: return None
            out[p[0]][p[1]] = next(iter(s))
    elif corr == "obj":
        comps = _comps(tc, diag)
        kp = sorted(K)
        if len(comps) != len(kp) or len(kp) < 2: return None
        cen = [(sum(y for y, _ in c) / len(c), sum(x for _, x in c) / len(c)) for c in comps]
        m = _match(cen, kp)
        for i, c in enumerate(comps):
            for y, x in c: out[y][x] = K[kp[m[i]]]
    elif corr in ("rank-x", "rank-y"):
        axis = 1 if corr == "rank-x" else 0
        bands, _ = _bands(tc, axis)
        first = {}
        for (y, x), v in K.items():
            k = x if axis == 1 else y
            first[v] = min(first.get(v, k), k)
        order = sorted(first, key=lambda v: first[v])
        if len(order) != len(bands) or len(order) < 2: return None
        for b, v in zip(bands, order):
            bs = set(b)
            for y, x in tc:
                if (x if axis == 1 else y) in bs: out[y][x] = v
    elif corr in ("scaled", "onoff"):
        r0, c0, r1, c1 = bbox(tc); h, w = r1 - r0 + 1, c1 - c0 + 1
        M = _compress(K)
        if any(v is None for r in M for v in r): return None
        if corr == "scaled":
            kh, kw = len(M), len(M[0])
            if (kh, kw) == (1, 1) or h % kh or w % kw: return None
            for y, x in tc: out[y][x] = M[(y - r0) * kh // h][(x - c0) * kw // w]
        else:
            rows = [r for k, r in enumerate(M) if k == 0 or r != M[k - 1]]
            if len(rows) == 2 and len(set(map(tuple, rows))) == 2:
                lines, vert = rows, False
            else:
                Mt = [list(c) for c in zip(*M)]
                cols = [r for k, r in enumerate(Mt) if k == 0 or r != Mt[k - 1]]
                if len(cols) != 2: return None
                lines, vert = cols, True
            n = len(lines[0]); span = h if vert else w
            if span % n: return None
            for y in range(r0, r1 + 1):
                for x in range(c0, c1 + 1):
                    k = ((y - r0) if vert else (x - c0)) * n // span
                    out[y][x] = lines[0 if g[y][x] == T else 1][k]
    else:
        return None
    if post == "erase":
        for y, x in K: out[y][x] = bg
    elif post == "crop":
        r0, c0, r1, c1 = bbox(tc)
        res = crop(out, (r0, c0, r1, c1))
        if corr == "scaled":
            f = bg if fill is None else fill
            res = [[v if g[r0 + y][c0 + x] == T else f for x, v in enumerate(r)] for y, r in enumerate(res)]
        return res
    return out


def fam_key_position(train):
    same = _same_shape(train)
    i0, o0 = train[0]["input"], train[0]["output"]
    if not same and (H(o0) > H(i0) or W(o0) > W(i0)): return
    roles = _t_roles(train)
    if not roles: return
    if same:
        combos = [(c, p) for c in ("row", "col", "obj4", "obj8", "rank-x", "rank-y") for p in ("keep", "erase")]
        combos += [("scaled", "keep"), ("onoff", "keep")]
    else:
        combos = [("scaled", "crop"), ("onoff", "crop")]
    fills = [None] + sorted(set.intersection(*[{v for r in p["output"] for v in r} & {v for r in p["input"] for v in r} for p in train]))[:2]
    if same: fills = [None]
    for rn, role in roles:
      for fill in fills:
        for frame in (False, True):
            for corr, post in combos:
                c = corr[:3] if corr.startswith("obj") else corr
                diag = corr == "obj8"
                if fill is not None and corr != "scaled": continue
                def fn(g, role=role, frame=frame, c=c, post=post, diag=diag, fill=fill):
                    return _apply_pos(g, role, frame, c, post, diag, fill)
                fs = "" if fill is None else f",fill={fill}"
                yield (f"key-position:{corr}[T={rn},frame={int(frame)},{post}{fs}]", 4, fn)


# ================================================================== key by colour (legend)
def _legend_sources(g, bg, how):
    """list of (pairs [(a,b)...], keycells set) for the chosen legend source"""
    res = []
    for ob in objects(g, bg, False, False):
        r0, c0, r1, c1 = bbox(ob); h, w = r1 - r0 + 1, c1 - c0 + 1
        if len(ob) != h * w: continue
        if how == "dominoes":
            if len(ob) != 2: continue
            (y1, x1), (y2, x2) = sorted(ob)
            prs = [(g[y1][x1], g[y2][x2])]
        elif how == "rows":
            if w != 2 or h > 10: continue
            prs = [(g[y][c0], g[y][c0 + 1]) for y in range(r0, r1 + 1)]
        else:
            if h != 2 or w > 10: continue
            prs = [(g[r0][x], g[r0 + 1][x]) for x in range(c0, c1 + 1)]
        if any(a == b for a, b in prs): continue
        res.append((prs, set(ob)))
    return res


def _phi(prs, d):
    m = {}
    for a, b in prs:
        if d == "rev": a, b = b, a
        if d == "swap":
            if m.get(b, a) != a: return None
            m[b] = a
        if m.get(a, b) != b: return None
        m[a] = b
    return m


def _apply_legend(g, how, d, scope):
    bg = bg_of(g)
    src = _legend_sources(g, bg, how)
    if not src: return None
    if how != "dominoes" and len(src) != 1: return None
    prs = [p for s, _ in src for p in s]; kc = set().union(*[k for _, k in src])
    if d == "chain":
        f = lambda v: _chain(v, prs)
    else:
        m = _phi(prs, d)
        if not m: return None
        f = lambda v: m.get(v, v)
    if scope == "all":
        return [[f(v) if (y, x) not in kc else v for x, v in enumerate(r)] for y, r in enumerate(g)]
    obs = [ob for ob in objects(g, bg, True, False) if not set(ob) & kc]
    if not obs: return None
    big = max(obs, key=len)
    if sum(1 for o in obs if len(o) == len(big)) > 1: return None
    return [[f(v) for v in r] for r in crop(g, bbox(big))]


def _chain(v, prs):
    for a, b in prs:
        if v == a: v = b
    return v


def fam_legend_map(train):
    i0, o0 = train[0]["input"], train[0]["output"]
    same = _same_shape(train)
    scopes = ("all",) if same else ("crop",)
    if not same and (H(o0) >= H(i0) and W(o0) >= W(i0)): return
    for how in ("dominoes", "rows", "cols"):
        if not any(_legend_sources(p["input"], bg_of(p["input"]), how) for p in train[:1]): continue
        for d in ("fwd", "rev", "swap") + (("chain",) if how != "dominoes" else ()):
            for sc in scopes:
                def fn(g, how=how, d=d, sc=sc): return _apply_legend(g, how, d, sc)
                yield (f"legend-map:{how}[{d},{sc}]", 4, fn)


# ================================================================== erase the colour shown in a corner box
_D4 = [(lambda g: g, lambda g: g),
       (lambda g: [r[::-1] for r in g], lambda g: [r[::-1] for r in g]),
       (lambda g: g[::-1], lambda g: g[::-1]),
       (lambda g: [r[::-1] for r in g[::-1]], lambda g: [r[::-1] for r in g[::-1]])]


def _corner_box(g, bg):
    """top-left box: row r0 (cols 0..c0) and column c0 (rows 0..r0) all colour L; returns (r0,c0,L)"""
    for r0 in range(1, H(g) - 1):
        for c0 in range(1, W(g) - 1):
            L = g[r0][c0]
            if L == bg: continue
            if all(g[r0][x] == L for x in range(c0 + 1)) and all(g[y][c0] == L for y in range(r0 + 1)):
                inner = {g[y][x] for y in range(r0) for x in range(c0)} - {bg}
                if L not in inner: return r0, c0, L
    return None


def _apply_erase(g, how):
    bg = bg_of(g)
    for k, (f, fi) in enumerate(_D4):
        gg = f(g); cb = _corner_box(gg, bg)
        if not cb: continue
        r0, c0, L = cb
        inner = {gg[y][x] for y in range(r0) for x in range(c0)} - {bg}
        if len(inner) != 1: return None
        kcol = next(iter(inner))
        out = [[(bg if (v == kcol and not (y < r0 and x < c0)) else v) for x, v in enumerate(r)] for y, r in enumerate(gg)]
        return fi(out)
    return None


def fam_key_erase(train):
    if not _same_shape(train): return
    yield ("key-erase:corner-box", 4, lambda g: _apply_erase(g, "erase"))


# ================================================================== binary complement
def _lattice(g, bg):
    """smallest period p>=3 such that rows (cols) at one offset mod p are all background"""
    def per(lines):
        n = len(lines)
        for p in range(3, n):
            for off in range(p):
                if all(all(v == bg for v in lines[i]) for i in range(off, n, p)):
                    return p, off
        return None
    pr = per(g); pc = per([list(c) for c in zip(*g)])
    if not pr or not pc: return None
    def spans(n, p, off):
        cuts = list(range(off, n, p))
        edges = [-1] + cuts + [n]
        return [(a + 1, b - 1) for a, b in zip(edges, edges[1:]) if b - 1 >= a + 1]
    return [(a, b, c, d) for a, b in spans(H(g), *pr) for c, d in spans(W(g), *pc)]


def _complement(g, scope):
    bg = bg_of(g); out = [r[:] for r in g]
    if scope == "whole":
        regions = [(0, H(g) - 1, 0, W(g) - 1)]
    elif scope == "lattice":
        regions = _lattice(g, bg)
        if not regions: return None
    else:
        regions = [(b[0], b[2], b[1], b[3]) for b in (bbox(o) for o in objects(g, bg, True, False))]
    done = False
    for r0, r1, c0, c1 in regions:
        cs = {g[y][x] for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)} - {bg}
        if not cs: continue
        if len(cs) != 1: return None
        c = next(iter(cs)); done = True
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                out[y][x] = bg if g[y][x] == c else c
    return out if done else None


def fam_complement(train):
    if not _same_shape(train): return
    for sc in ("whole", "lattice", "objbox"):
        yield (f"complement:{sc}", 3, lambda g, sc=sc: _complement(g, sc))


# ================================================================== two-variant swap
def _unit(g, ob, bg):
    """object -> (unit pattern dict (y,x)->colour, scale, top-left)"""
    r0, c0, r1, c1 = bbox(ob); h, w = r1 - r0 + 1, c1 - c0 + 1
    cells = {(y - r0, x - c0): g[y][x] for y, x in ob}
    for s in range(min(h, w), 0, -1):
        if h % s or w % s: continue
        ok = True
        for y in range(h):
            for x in range(w):
                if cells.get((y, x)) != cells.get((y - y % s, x - x % s)): ok = False; break
            if not ok: break
        if ok:
            return {(y // s, x // s): v for (y, x), v in cells.items() if y % s == 0 and x % s == 0}, s, (r0, c0)
    return None


def _align(A, B):
    """offset (dy,dx) to place B relative to A maximising shared equal-colour cells"""
    best = (0, None)
    for (ay, ax) in A:
        for (by, bx) in B:
            dy, dx = ay - by, ax - bx
            n = sum(1 for (y, x), v in B.items() if A.get((y + dy, x + dx)) == v)
            if n > best[0]: best = (n, (dy, dx))
    return best


def _variant_swap(g, diag):
    bg = bg_of(g)
    obs = objects(g, bg, diag, False)
    if len(obs) < 2 or len(obs) > 30: return None
    units = []
    for ob in obs:
        u = _unit(g, ob, bg)
        if u is None: return None
        units.append(u)
    keys = []
    for u, _, _ in units:
        k = frozenset(u.items())
        if k not in keys: keys.append(k)
    if len(keys) != 2: return None
    A, B = dict(keys[0]), dict(keys[1])
    n, off = _align(A, B)
    if not off or n < 2 or n >= min(len(A), len(B)): return None
    out = [r[:] for r in g]
    for ob in obs:
        for y, x in ob: out[y][x] = bg
    for u, s, (r0, c0) in units:
        if frozenset(u.items()) == keys[0]: new, (dy, dx) = B, off
        else: new, (dy, dx) = A, (-off[0], -off[1])
        for (y, x), v in new.items():
            for a in range(s):
                for b in range(s):
                    yy, xx = r0 + (y + dy) * s + a, c0 + (x + dx) * s + b
                    if not (0 <= yy < H(g) and 0 <= xx < W(g)): return None
                    out[yy][xx] = v
    return out


def fam_variant_swap(train):
    if not _same_shape(train): return
    for diag in (True, False):
        yield (f"variant-swap[{8 if diag else 4}]", 5, lambda g, diag=diag: _variant_swap(g, diag))


FAMILIES = (fam_key_position, fam_legend_map, fam_key_erase, fam_complement, fam_variant_swap)
