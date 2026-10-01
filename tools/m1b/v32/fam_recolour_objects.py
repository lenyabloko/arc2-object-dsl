"""Recolour whole objects by an induced object feature / by shape match with exemplars.

Groups: recolour.object_by_property, recolour.by_shape_match.

fam_recolour_object_feature: objects (components 4/8, rows, cols, separator panels, uniform tiles) are
  mapped to an output behaviour (keep / literal colour / own colour / background, painted on the object
  cells or filled over the object's region) by a table over one computed feature, induced from all pairs.
fam_recolour_shape_match: candidate objects of the source colour take the colour of the exemplar object(s)
  with an equivalent shape (translation / dihedral / dihedral after collapsing repeated rows+cols);
  exemplar pool = all other objects / target-coloured objects / frame-enclosed objects; unique or majority.
  Variant: candidates are the holes of the largest object and the output is that object's crop.
fam_recolour_solid_blocks: cells covered by a monochrome TxT square (T induced) take one induced colour.
"""
import sys
from collections import Counter
from itertools import product
sys.path.append('/home/claude/work/widen')
from gdsl import H, W, bg_of, bbox

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def comps(g, pred, diag, same_colour=True):
    """Connected components of cells satisfying pred (optionally split by colour)."""
    h, w = H(g), W(g); seen = set(); out = []
    nb = N8 if diag else N4
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or not pred(g[r][c]): continue
            col = g[r][c]; st = [(r, c)]; seen.add((r, c)); cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and pred(g[yy][xx]) \
                            and (not same_colour or g[yy][xx] == col):
                        seen.add((yy, xx)); st.append((yy, xx))
            out.append(sorted(cells))
    return out


def norm(cells):
    y0 = min(y for y, _ in cells); x0 = min(x for _, x in cells)
    return tuple(sorted((y - y0, x - x0) for y, x in cells))


def d8(cells):
    res = []
    for t in range(8):
        cs = []
        for y, x in cells:
            if t & 1: y, x = x, y
            if t & 2: y = -y
            if t & 4: x = -x
            cs.append((y, x))
        res.append(norm(cs))
    return min(res)


def collapse(cells):
    """Remove repeated adjacent rows and columns of the object's mask."""
    s = set(norm(cells)); h = max(y for y, _ in s) + 1; w = max(x for _, x in s) + 1
    m = [[(y, x) in s for x in range(w)] for y in range(h)]
    m = [r for i, r in enumerate(m) if i == 0 or r != m[i - 1]]
    t = [list(c) for c in zip(*m)]
    t = [c for i, c in enumerate(t) if i == 0 or c != t[i - 1]]
    return [(y, x) for x, c in enumerate(t) for y, v in enumerate(c) if v]


CANON = {"T": norm, "D8": d8, "C8": lambda c: d8(collapse(c))}


# ---------------------------------------------------------------- object features
def full_sides(cells):
    r0, c0, r1, c1 = bbox(cells); s = set(cells)
    return (all((r0, x) in s for x in range(c0, c1 + 1)) + all((r1, x) in s for x in range(c0, c1 + 1))
            + all((y, c0) in s for y in range(r0, r1 + 1)) + all((y, c1) in s for y in range(r0, r1 + 1)))


def n_parts4(cells):
    s = set(cells); seen = set(); n = 0
    for c in cells:
        if c in seen: continue
        n += 1; st = [c]; seen.add(c)
        while st:
            y, x = st.pop()
            for dy, dx in N4:
                q = (y + dy, x + dx)
                if q in s and q not in seen: seen.add(q); st.append(q)
    return min(n, 3)


def path_turns(cells):
    """Topology of a 4-connected thin object: 'branch'/'cycle', or (n_turns, all turns same sense)."""
    s = set(cells)
    deg = {c: sum((c[0] + dy, c[1] + dx) in s for dy, dx in N4) for c in cells}
    if len(cells) == 1: return (0, True)
    ends = [c for c in cells if deg[c] == 1]
    if any(d > 2 for d in deg.values()): return "branch"
    if len(ends) != 2: return "cycle"
    path = [ends[0]]; prev = None
    while True:
        cur = path[-1]
        nx = [(cur[0] + dy, cur[1] + dx) for dy, dx in N4 if (cur[0] + dy, cur[1] + dx) in s and (cur[0] + dy, cur[1] + dx) != prev]
        if not nx: break
        prev = cur; path.append(nx[0])
    if len(path) != len(cells): return "branch"
    turns = []
    for a, b, c in zip(path, path[1:], path[2:]):
        d1 = (b[0] - a[0], b[1] - a[1]); d2 = (c[0] - b[0], c[1] - b[1])
        cr = d1[0] * d2[1] - d1[1] * d2[0]
        if cr: turns.append(cr > 0)
    return (len(turns), len(set(turns)) <= 1)


def rank_vals(vals, key):
    """Per-object label max/min/mid of a numeric value (ties allowed only at non-extremes)."""
    mx, mn = max(vals), min(vals)
    if mx == mn: return ["all"] * len(vals)
    return ["max" if v == mx else "min" if v == mn else "mid" for v in vals]


def feat_values(fname, objs, g):
    """objs: list of (fg_cells, region_cells, origin). Returns one hashable per object or None."""
    fg = [o[0] for o in objs]
    if fname == "size": return [len(c) for c in fg]
    if fname == "size_ext": return rank_vals([len(c) for c in fg], None)
    if fname == "size_rank":
        s = sorted({len(c) for c in fg}, reverse=True); return [s.index(len(c)) for c in fg]
    if fname == "shape": return [norm(c) if c else () for c in fg]
    if fname == "shape_d8": return [d8(c) if c else () for c in fg]
    if fname == "pattern":
        return [tuple(sorted(((y - o[2][0], x - o[2][1]), g[y][x]) for y, x in c)) for c, o in zip(fg, objs)]
    if fname == "full_sides": return [full_sides(c) if c else -1 for c in fg]
    if fname == "turns": return [path_turns(c) if c else None for c in fg]
    if fname == "parts4": return [n_parts4(c) if c else 0 for c in fg]
    if fname == "marker_pos":
        out = []
        for c, o in zip(fg, objs):
            if len(c) != 1: out.append(None); continue
            y, x = c[0]; out.append((y - o[2][0], x - o[2][1]))
        return out
    if fname == "colour_count_ext":
        return rank_vals([len(c) for c in fg], None)
    raise KeyError(fname)


NUMERIC = {"size", "full_sides", "parts4"}


def segment(g, mode, bg):
    """Returns (objs, sep) where objs = [(fg_cells, region_cells, origin)], or None."""
    h, w = H(g), W(g)
    if mode in ("c4", "c8", "m4", "m8"):
        cs = comps(g, lambda v: v != bg, mode[1] == "8", mode[0] == "c")
        return [(c, c, bbox(c)[:2]) for c in cs]
    if mode == "rows":
        return [([(y, x) for x in range(w) if g[y][x] != bg], [(y, x) for x in range(w)], (y, 0)) for y in range(h)]
    if mode == "cols":
        return [([(y, x) for y in range(h) if g[y][x] != bg], [(y, x) for y in range(h)], (0, x)) for x in range(w)]
    if mode == "panels":
        pr = panel_rects(g)
        if not pr: return None
        rects, sc = pr
        return [([(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if g[y][x] not in (bg, sc)],
                 [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)], (r0, c0)) for r0, c0, r1, c1 in rects]
    if mode.startswith("tile"):
        th, tw = map(int, mode[4:].split("x"))
        if h % th or w % tw or (h // th) * (w // tw) < 2: return None
        return [([(y, x) for y in range(r, r + th) for x in range(c, c + tw) if g[y][x] != bg],
                 [(y, x) for y in range(r, r + th) for x in range(c, c + tw)], (r, c))
                for r in range(0, h, th) for c in range(0, w, tw)]
    return None


def panel_rects(g):
    h, w = H(g), W(g)
    for sc in sorted({v for r in g for v in r}):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols or len(rows) == h or len(cols) == w: continue
        rb = [-1] + rows + [h]; cb = [-1] + cols + [w]; rects = []
        for a in range(len(rb) - 1):
            for b in range(len(cb) - 1):
                if rb[a + 1] - rb[a] > 1 and cb[b + 1] - cb[b] > 1:
                    rects.append((rb[a] + 1, cb[b] + 1, rb[a + 1] - 1, cb[b + 1] - 1))
        if len(rects) >= 2: return rects, sc
    return None


def outcome_roles(g, o, ob, paint, bg):
    """Candidate roles explaining the output over one object; [] if not explainable."""
    fg, reg, _ = ob
    cells = fg if paint else reg
    if not cells: return [("keep",)]
    vs = {o[y][x] for y, x in cells}
    roles = [("keep",)] if all(o[y][x] == g[y][x] for y, x in cells) else []
    if len(vs) != 1: return roles
    X = vs.pop(); roles.append(("lit", X))
    own = Counter(g[y][x] for y, x in fg).most_common(1)[0][0] if fg else None
    if X == own: roles.append(("own",))
    if X == bg: roles.append(("bg",))
    return roles


def induce_table(train, mode, fname, paint):
    obs_by_val = {}
    for p in train:
        g, o = p["input"], p["output"]; bg = bg_of(g)
        objs = segment(g, mode, bg)
        if not objs: return None
        vals = feat_values(fname, objs, g)
        for ob, v in zip(objs, vals):
            rs = outcome_roles(g, o, ob, paint, bg)
            if not rs: return None
            obs_by_val.setdefault(v, []).append(rs)
    table = {}
    for v, lst in obs_by_val.items():
        common = set(lst[0])
        for rs in lst[1:]: common &= set(rs)
        if not common: return None
        for pref in (("keep",), None, ("own",), ("bg",)):
            if pref is None:
                lits = [r for r in common if r[0] == "lit"]
                if lits: table[v] = lits[0]; break
            elif pref in common: table[v] = pref; break
    if all(r == ("keep",) for r in table.values()): return None
    return table


def apply_table(g, mode, fname, paint, table, nearest):
    bg = bg_of(g); objs = segment(g, mode, bg)
    if not objs: return None
    vals = feat_values(fname, objs, g); out = [r[:] for r in g]
    keys = [k for k in table if isinstance(k, int)]
    for ob, v in zip(objs, vals):
        if v not in table:
            if not nearest or not isinstance(v, int) or not keys: return None
            d = sorted(keys, key=lambda k: abs(k - v))
            if len(d) > 1 and abs(d[0] - v) == abs(d[1] - v) and table[d[0]] != table[d[1]]: return None
            v = d[0]
        r = table[v]
        if r == ("keep",): continue
        fg, reg, _ = ob
        if r[0] == "lit": c = r[1]
        elif r == ("bg",): c = bg
        else:
            if not fg: return None
            c = Counter(g[y][x] for y, x in fg).most_common(1)[0][0]
        for y, x in (fg if paint else reg): out[y][x] = c
    return out


def uniform_tile(train):
    """Smallest tile (th,tw), >=2 tiles, such that every training output is constant on each tile."""
    o0 = train[0]["output"]; h, w = H(o0), W(o0); res = []
    for th in range(1, h + 1):
        for tw in range(1, w + 1):
            if h % th or w % tw or th * tw < 2 or (h // th) * (w // tw) < 2: continue
            if all(H(p["output"]) % th == 0 and W(p["output"]) % tw == 0 and
                   all(len({p["output"][y][x] for y in range(r, r + th) for x in range(c, c + tw)}) == 1
                       for r in range(0, H(p["output"]), th) for c in range(0, W(p["output"]), tw)) for p in train):
                res.append((th * tw, th, tw))
    return sorted(res, reverse=True)[:3]


def fam_recolour_object_feature(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(i), W(i)) != (H(o), W(o)) or i == o: return
    if any((H(p["input"]), W(p["input"])) != (H(p["output"]), W(p["output"])) for p in train): return
    modes = [("c4", True), ("c8", True), ("m4", True), ("m8", True), ("rows", False), ("cols", False), ("panels", False)]
    for _, th, tw in uniform_tile(train): modes.append((f"tile{th}x{tw}", False))
    feats = ("size", "size_ext", "size_rank", "shape", "shape_d8", "pattern", "full_sides", "parts4", "turns", "marker_pos")
    n = 0
    for (mode, paint), fname in product(modes, feats):
        if mode in ("c4", "c8") and fname in ("size", "size_rank", "shape"): continue   # covered by gdsl
        t = induce_table(train, mode, fname, paint)
        if not t: continue
        for nearest in ((False, True) if fname in NUMERIC else (False,)):
            def fn(g, mode=mode, fname=fname, paint=paint, t=t, nearest=nearest):
                return apply_table(g, mode, fname, paint, t, nearest)
            yield (f"recolour-objects:{mode}[{fname}{',nearest' if nearest else ''}]", 4 + nearest, fn)
            n += 1
        if n >= 40: return


# ---------------------------------------------------------------- shape match
def change_colours(train):
    src, tgt = set(), set()
    for p in train:
        g, o = p["input"], p["output"]
        for y in range(H(g)):
            for x in range(W(g)):
                if g[y][x] != o[y][x]: src.add(g[y][x]); tgt.add(o[y][x])
    return src, tgt


def enclosed(g, cells, bg):
    """True if some colour F (not the object's, not bg) walls the object off from the grid border."""
    oc = g[cells[0][0]][cells[0][1]]
    for F in {v for r in g for v in r} - {oc, bg}:
        seen = set(cells); st = list(cells); ok = True
        while st and ok:
            y, x = st.pop()
            for dy, dx in N4:
                yy, xx = y + dy, x + dx
                if not (0 <= yy < H(g) and 0 <= xx < W(g)): ok = False; break
                if (yy, xx) not in seen and g[yy][xx] != F: seen.add((yy, xx)); st.append((yy, xx))
        if ok: return True
    return False


def vote(key, exemplars, resolve):
    cs = [c for k, c in exemplars if k == key]
    if not cs: return None
    cnt = Counter(cs).most_common()
    if resolve == "unique": return cnt[0][0] if len(cnt) == 1 else "amb"
    if len(cnt) > 1 and cnt[0][1] == cnt[1][1]: return "amb"
    return cnt[0][0]


def shape_match(g, s, diag, pool, equiv, resolve, tgt):
    cnt = Counter(v for r in g for v in r)
    bg = max((c for c in cnt if c != s), key=lambda c: cnt[c], default=None)
    can = CANON[equiv]
    cands = comps(g, lambda v: v == s, diag)
    if not cands: return None
    ex = []
    for e in comps(g, lambda v: v not in (s, bg), diag):
        c = g[e[0][0]][e[0][1]]
        if pool == "targets" and c not in tgt: continue
        if pool == "enclosed" and not enclosed(g, e, bg): continue
        ex.append((can(e), c))
    if not ex: return None
    out = [r[:] for r in g]
    for cd in cands:
        c = vote(can(cd), ex, resolve)
        if c == "amb": return None
        if c is not None:
            for y, x in cd: out[y][x] = c
    return out


def holes_crop(g, diag, equiv):
    """Largest single-colour object; its holes (other-coloured components inside its bbox) take the
    majority colour of equal-shape objects outside the bbox; return the crop."""
    cnt = Counter(v for r in g for v in r); bg = cnt.most_common(1)[0][0]
    objs = comps(g, lambda v: True, False)
    big = max(objs, key=len); cc = g[big[0][0]][big[0][1]]
    if cc == bg and len(objs) > 1:
        big = max((o for o in objs if g[o[0][0]][o[0][1]] != bg), key=len); cc = g[big[0][0]][big[0][1]]
    r0, c0, r1, c1 = bbox(big)
    if r1 - r0 < 2 or c1 - c0 < 2: return None
    sub = [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
    can = CANON[equiv]
    ex = [(can(e), g[e[0][0]][e[0][1]]) for e in comps(g, lambda v: v not in (bg, cc), diag)
          if all(not (r0 <= y <= r1 and c0 <= x <= c1) for y, x in e)]
    if not ex: return None
    out = [r[:] for r in sub]; hit = False
    for hcells in comps(sub, lambda v: v != cc, False):
        c = vote(can(hcells), ex, "majority")
        if c == "amb" or c is None: return None
        hit = True
        for y, x in hcells: out[y][x] = c
    return out if hit else None


def fam_recolour_shape_match(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(i), W(i)) != (H(o), W(o)):
        if H(o) < H(i) and W(o) < W(i):
            for diag, equiv in product((False, True), ("D8", "T")):
                yield (f"shape-vote-holes-crop[{'8' if diag else '4'},{equiv}]", 5,
                       lambda g, diag=diag, equiv=equiv: holes_crop(g, diag, equiv))
        return
    if any((H(p["input"]), W(p["input"])) != (H(p["output"]), W(p["output"])) for p in train): return
    src, tgt = change_colours(train)
    if len(src) != 1 or not tgt: return
    s = src.pop()
    # changed cells must be whole source components (checked by verification); enumerate the rest
    for diag, pool, equiv, resolve in product((False, True), ("all", "targets", "enclosed"), ("T", "D8", "C8"),
                                              ("unique", "majority")):
        def fn(g, diag=diag, pool=pool, equiv=equiv, resolve=resolve):
            return shape_match(g, s, diag, pool, equiv, resolve, tgt)
        yield (f"recolour-shape-match[{'8' if diag else '4'},{pool},{equiv},{resolve}]",
               4 + (equiv != "T") + (resolve != "unique"), fn)



# ---------------------------------------------------------------- solid blocks
def solid_cover(g, T):
    h, w = H(g), W(g); cov = set()
    for r in range(h - T + 1):
        for c in range(w - T + 1):
            v = g[r][c]
            if all(g[y][x] == v for y in range(r, r + T) for x in range(c, c + T)):
                cov.update((y, x) for y in range(r, r + T) for x in range(c, c + T))
    return cov


def fam_recolour_solid_blocks(train):
    """Cells covered by a monochrome TxT square are recoloured to one induced colour (noise grids)."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(i), W(i)) != (H(o), W(o)) or i == o: return
    src, tgt = change_colours(train)
    if len(tgt) != 1: return
    c = next(iter(tgt))
    for T in range(2, 7):
        ok = True
        for p in train:
            g, out = p["input"], p["output"]
            if (H(g), W(g)) != (H(out), W(out)): return
            cov = solid_cover(g, T)
            exp = [[c if (y, x) in cov else g[y][x] for x in range(W(g))] for y in range(H(g))]
            if exp != out: ok = False; break
        if ok:
            def fn(g, T=T):
                cov = solid_cover(g, T)
                return [[c if (y, x) in cov else g[y][x] for x in range(W(g))] for y in range(H(g))]
            yield (f"recolour-solid-blocks[{T}]", 4, fn)
            return


# ---------------------------------------------------------------- capped bars selected by key count
def capped_bars(g, bg, vert):
    """Maximal straight runs of non-bg cells (>=3, along columns if vert else rows) whose two end cells share
    colour a that does not occur in the interior."""
    bars = []
    lines = ([[(y, x) for y in range(H(g))] for x in range(W(g))] if vert else
             [[(y, x) for x in range(W(g))] for y in range(H(g))])
    for ln in lines:
        run = []
        for q in ln + [None]:
            if q is not None and g[q[0]][q[1]] != bg: run.append(q); continue
            if len(run) >= 3:
                a = g[run[0][0]][run[0][1]]
                if g[run[-1][0]][run[-1][1]] == a and a not in {g[y][x] for y, x in run[1:-1]}:
                    bars.append((a, run))
            run = []
    return bars


def key_rank_fill(g, desc, vert):
    bg = bg_of(g); bars = capped_bars(g, bg, vert)
    if not bars: return None
    inbar = {c for _, ob in bars for c in ob}
    out = [r[:] for r in g]; hit = False
    for a in {a for a, _ in bars}:
        k = sum(1 for y in range(H(g)) for x in range(W(g)) if g[y][x] == a and (y, x) not in inbar)
        grp = sorted((ob for c, ob in bars if c == a), key=len, reverse=desc)
        if k < 1 or k > len(grp): continue
        if k < len(grp) and len(grp[k - 1]) == len(grp[k]) or k > 1 and len(grp[k - 1]) == len(grp[k - 2]): return None
        for y, x in grp[k - 1]: out[y][x] = a
        hit = True
    return out if hit else None


def fam_recolour_bar_by_key_rank(train):
    """Per cap colour a: the k-th longest (or shortest) capped bar is filled with a, k = number of loose
    a-cells (the key)."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(i), W(i)) != (H(o), W(o)) or i == o: return
    for vert, desc in product((True, False), (True, False)):
        if not capped_bars(i, bg_of(i), vert): continue
        yield (f"recolour-bar-by-key-rank[{'v' if vert else 'h'},{'desc' if desc else 'asc'}]", 5,
               lambda g, desc=desc, vert=vert: key_rank_fill(g, desc, vert))


FAMILIES = (fam_recolour_object_feature, fam_recolour_shape_match, fam_recolour_solid_blocks, fam_recolour_bar_by_key_rank)
