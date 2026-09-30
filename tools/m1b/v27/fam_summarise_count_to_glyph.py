"""summarise.count_to_glyph: count N items of an induced class, render N marks into a canvas.

One parametrised primitive, induced by decoding the training outputs first:
  canvas : fixed shape (all outputs equal) | 1xN / Nx1 bar | NxN diagonal | input-shaped canvas with
           a bar centred on the middle row/column
  slots  : for a fixed canvas, the fill order is one of the generic orders (reading / snake /
           diagonal / checkerboard-reading, under the 8 dihedral frames) or, failing that, the
           nested painted sets learned from the outputs (usable only for counts seen in training)
  cbg    : canvas background (0, input bg, or an output colour)
  target : the per-pair counts (and run colours) read off the outputs
Only then the item selector is searched (all of it must reproduce every target):
  role   : colour c | all fg (one group) | most/least frequent fg | each fg colour (sequential pour,
           ordered by colour value asc/desc)
  unit   : cells | 4/8-components | solid kxk squares (k>=2) | components of size>=2 | singletons |
           rows / columns of the item bbox that contain background
  scope  : whole grid | interior of the bbox of the largest object of another colour
  paint  : item colour | induced constant;  offset (size canvases only): N or N+1
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox

# ------------------------------------------------------------------ slot orders
def _walks(hh, ww):
    read = [(y, x) for y in range(hh) for x in range(ww)]
    snake = [(y, x if y % 2 == 0 else ww - 1 - x) for y in range(hh) for x in range(ww)]
    diag = [(i, i) for i in range(min(hh, ww))]
    cheq = [(y, x) for y in range(hh) for x in range(ww) if (y + x) % 2 == 0]
    return {"read": read, "snake": snake, "diag": diag, "cheq": cheq}

def slot_orders(h, w):
    out = {}; seen = set()
    for tname, tr, hh, ww in (
            ("id", lambda y, x: (y, x), h, w), ("fh", lambda y, x: (y, w - 1 - x), h, w),
            ("fv", lambda y, x: (h - 1 - y, x), h, w), ("r180", lambda y, x: (h - 1 - y, w - 1 - x), h, w),
            ("T", lambda y, x: (x, y), w, h), ("Tfh", lambda y, x: (x, h - 1 - y), w, h),
            ("Tfv", lambda y, x: (w - 1 - x, y), w, h), ("Tr180", lambda y, x: (w - 1 - x, h - 1 - y), w, h)):
        for wname, walk in _walks(hh, ww).items():
            o = tuple(tr(y, x) for y, x in walk)
            if o in seen: continue
            seen.add(o); out[wname + "/" + tname] = list(o)
    return out

# ------------------------------------------------------------------ item selectors
def _comps(mask, diag):
    h, w = len(mask), len(mask[0]); seen = set(); out = []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if diag else [])
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or (y, x) in seen: continue
            st = [(y, x)]; seen.add((y, x)); cs = []
            while st:
                a, b = st.pop(); cs.append((a, b))
                for dy, dx in nb:
                    p = (a + dy, b + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and mask[p[0]][p[1]] and p not in seen:
                        seen.add(p); st.append(p)
            out.append(cs)
    return out

def _is_square(cs):
    y0, x0, y1, x1 = bbox(cs)
    return y1 - y0 == x1 - x0 and y1 > y0 and len(cs) == (y1 - y0 + 1) ** 2

UNITS = ("cells", "comp4", "comp8", "square", "big4", "single8", "bgrows", "bgcols")

def count_unit(g, c, unit, bg, region):
    h, w = H(g), W(g)
    inr = (lambda y, x: True) if region is None else (lambda y, x: region[0] < y < region[2] and region[1] < x < region[3])
    mask = [[g[y][x] == c and inr(y, x) for x in range(w)] for y in range(h)]
    if unit == "cells": return sum(map(sum, mask))
    if unit in ("bgrows", "bgcols"):
        cs = [(y, x) for y in range(h) for x in range(w) if mask[y][x]]
        if not cs: return 0
        y0, x0, y1, x1 = bbox(cs)
        if unit == "bgrows": return sum(1 for y in range(y0, y1 + 1) if any(g[y][x] == bg for x in range(x0, x1 + 1)))
        return sum(1 for x in range(x0, x1 + 1) if any(g[y][x] == bg for y in range(y0, y1 + 1)))
    comps = _comps(mask, unit in ("comp8", "single8"))
    if unit in ("comp4", "comp8"): return len(comps)
    if unit == "square": return sum(1 for cs in comps if _is_square(cs))
    if unit == "big4": return sum(1 for cs in comps if len(cs) > 1)
    if unit == "single8": return sum(1 for cs in comps if len(cs) == 1)

def _region(g, bg, scope):
    """None (whole grid) or (y0,x0,y1,x1, frame colour) of the largest single-colour 8-object."""
    if scope == "all": return None, None
    obs = objects(g, bg, True, True)
    if not obs: return False, None
    big = max(obs, key=len)
    if sum(1 for o in obs if len(o) == len(big)) > 1: return False, None
    return bbox(big), g[big[0][0]][big[0][1]]

def grid_bg(g, fbg):
    """induced background: the colour that is the background of every training input (if present), else per grid."""
    return fbg if fbg is not None and any(fbg in r for r in g) else bg_of(g)

def groups(g, role, unit, scope, fbg=None):
    """list of (colour, count) for the selected item colours; None if the selector is undefined."""
    bg = grid_bg(g, fbg)
    region, frame = _region(g, bg, scope)
    if region is False: return None
    cnt = Counter(v for r in g for v in r if v != bg and v != frame)
    if role[0] == "c":
        cols = [role[1]]
    elif role[0] in ("fg", "each+", "each-"):
        cols = sorted(cnt, reverse=role[0] == "each-")
    elif role[0] in ("max", "min"):
        if not cnt: return None
        mc = cnt.most_common()
        v = mc[0][1] if role[0] == "max" else mc[-1][1]
        cs = [c for c, n in mc if n == v]
        if len(cs) != 1: return None
        cols = cs
    if role[0] == "fg":
        n = sum(count_unit(g, c, unit, bg, region) for c in cols) if unit in ("cells", "square", "big4", "single8") \
            else None
        if n is None:  # multi-colour components / rows: count on the union mask
            gg = [[1 if (v != bg and v != frame) else 0 for v in r] for r in g]
            n = count_unit(gg, 1, unit, 0, region)
        return [(cols[0] if len(cols) == 1 else None, n)]
    return [(c, count_unit(g, c, unit, bg, region)) for c in cols]

# ------------------------------------------------------------------ canvas decoding
def runs_along(o, order, cbg):
    """painted cells of o must be exactly a prefix of `order`; returns run-length colour list."""
    painted = {(y, x) for y in range(H(o)) for x in range(W(o)) if o[y][x] != cbg}
    n = len(painted)
    if n > len(order) or set(order[:n]) != painted: return None
    runs = []
    for y, x in order[:n]:
        v = o[y][x]
        if runs and runs[-1][0] == v: runs[-1][1] += 1
        else: runs.append([v, 1])
    return [tuple(r) for r in runs]

def learned_order(outs, cbg):
    """nested painted sets -> (dict n -> set). None if not nested."""
    sets = {}
    for o in outs:
        s = frozenset((y, x) for y in range(H(o)) for x in range(W(o)) if o[y][x] != cbg)
        if len(s) in sets and sets[len(s)] != s: return None
        sets[len(s)] = s
    ks = sorted(sets)
    for a, b in zip(ks, ks[1:]):
        if not sets[a] <= sets[b]: return None
    return sets

def decode(train):
    """yield (canvas_name, targets, render) where targets[i] = list of (colour, n) runs and
    render(runs, g) -> grid.  A run colour of None means 'unspecified'."""
    ins = [p["input"] for p in train]; outs = [p["output"] for p in train]
    shapes = {(H(o), W(o)) for o in outs}
    # (a) fixed canvas
    if len(shapes) == 1:
        h, w = shapes.pop()
        if h * w <= 36:
            cands = []
            for c in [0] + sorted({v for o in outs for v in (x for r in o for x in r)}):
                if c not in cands: cands.append(c)
            orders = slot_orders(h, w)
            for cbg in cands:
                got = 0
                for oname, order in orders.items():
                    tg = [runs_along(o, order, cbg) for o in outs]
                    if any(t is None for t in tg): continue
                    if all(len(t) == 0 for t in tg): continue
                    def render(runs, g, order=order, cbg=cbg, h=h, w=w):
                        out = [[cbg] * w for _ in range(h)]; k = 0
                        for col, n in runs:
                            if k + n > len(order): return None
                            for y, x in order[k:k + n]: out[y][x] = col
                            k += n
                        return out
                    yield ("fixed%dx%d:%s:bg%d" % (h, w, oname, cbg), tg, render)
                    got += 1
                    if got >= 2: break
                if got: continue
                sets = learned_order(outs, cbg)
                if sets and len(sets) >= 2:
                    tg = []
                    for o in outs:
                        cs = {o[y][x] for y in range(H(o)) for x in range(W(o)) if o[y][x] != cbg}
                        n = sum(1 for r in o for v in r if v != cbg)
                        if len(cs) > 1: tg = None; break
                        tg.append([(cs.pop(), n)] if n else [])
                    if tg is None: continue
                    def render(runs, g, sets=sets, cbg=cbg, h=h, w=w):
                        if len(runs) > 1: return None
                        n = runs[0][1] if runs else 0
                        if n not in sets: return None
                        out = [[cbg] * w for _ in range(h)]
                        for y, x in sets[n]: out[y][x] = runs[0][0]
                        return out
                    yield ("learned%dx%d:bg%d" % (h, w, cbg), tg, render)
        return
    # (b) uniform bar 1xN / Nx1
    for ax in ("row", "col"):
        if all((H(o) == 1 if ax == "row" else W(o) == 1) and len({v for r in o for v in r}) == 1 for o in outs):
            tg = [[(o[0][0], W(o) if ax == "row" else H(o))] for o in outs]
            def render(runs, g, ax=ax):
                if len(runs) != 1 or runs[0][1] < 1: return None
                c, n = runs[0]
                return [[c] * n] if ax == "row" else [[c] for _ in range(n)]
            yield ("bar-" + ax, tg, render)
            return
    # (c) NxN with diagonal painted
    if all(H(o) == W(o) for o in outs):
        for anti in (False, True):
            tg = []
            for o in outs:
                n = H(o); d = {(i, n - 1 - i if anti else i) for i in range(n)}
                dc = {o[y][x] for y, x in d}
                rest = {o[y][x] for y in range(n) for x in range(n) if (y, x) not in d}
                if len(dc) != 1 or len(rest) > 1 or dc == rest: tg = None; break
                tg.append((dc.pop(), n, rest.pop() if rest else None))
            if tg is None: continue
            cb = {t[2] for t in tg if t[2] is not None}
            if len(cb) != 1: continue
            cbg = cb.pop()
            def render(runs, g, anti=anti, cbg=cbg):
                if len(runs) != 1 or runs[0][1] < 1: return None
                c, n = runs[0]; out = [[cbg] * n for _ in range(n)]
                for i in range(n): out[i][n - 1 - i if anti else i] = c
                return out
            yield ("diag" + ("-anti" if anti else ""), [[(c, n)] for c, n, _ in tg], render)
            return
    # (d) input-shaped canvas, bar centred on the middle row / column
    if all((H(i), W(i)) == (H(o), W(o)) for i, o in zip(ins, outs)):
        for ax in ("row", "col"):
            tg = []
            for i, o in zip(ins, outs):
                bg = bg_of(i); h, w = H(o), W(o)
                cells = [(y, x) for y in range(h) for x in range(w) if o[y][x] != bg]
                cs = {o[y][x] for y, x in cells}
                if len(cs) != 1: tg = None; break
                n = len(cells); L = w if ax == "row" else h
                if ax == "row": want = {(h // 2, x) for x in range((L - n) // 2, (L - n) // 2 + n)}
                else: want = {(y, w // 2) for y in range((L - n) // 2, (L - n) // 2 + n)}
                if set(cells) != want: tg = None; break
                tg.append([(cs.pop(), n)])
            if tg is None: continue
            def render(runs, g, ax=ax):
                if len(runs) != 1: return None
                c, n = runs[0]; bg = bg_of(g); h, w = H(g), W(g)
                L = w if ax == "row" else h
                if n > L: return None
                out = [[bg] * w for _ in range(h)]
                for k in range((L - n) // 2, (L - n) // 2 + n):
                    if ax == "row": out[h // 2][k] = c
                    else: out[k][w // 2] = c
                return out
            yield ("centred-" + ax, tg, render)

# ------------------------------------------------------------------ the family
def fam_count_to_glyph(train):
    ins = [p["input"] for p in train]
    if len(train) < 2: return
    decs = list(decode(train))
    if not decs: return
    bgs = {bg_of(i) for i in ins}
    fbg = bgs.pop() if len(bgs) == 1 else None
    fgcols = sorted({v for i in ins for r in i for v in r} - {bg_of(i) for i in ins})
    roles = [("fg",), ("max",), ("min",)] + [("c", c) for c in fgcols]
    multi_roles = [("each-",), ("each+",)]
    cache = {}
    def G(k, role, unit, scope):
        key = (k, role, unit, scope)
        if key not in cache: cache[key] = groups(ins[k], role, unit, scope, fbg)
        return cache[key]
    n_yield = 0
    for cname, tg, render in decs:
        single = all(len(t) <= 1 for t in tg)
        offsets = (0, 1) if cname.startswith("bar") else (0,)
        if single:
            tcol = {t[0][0] for t in tg if t}
            for scope in ("all", "inbox"):
                for unit in UNITS:
                    for role in roles:
                        for off in offsets:
                            ok_item = True; ok = True
                            for k, t in enumerate(tg):
                                gs = G(k, role, unit, scope)
                                if gs is None: ok = False; break
                                col, n = gs[0]
                                tn = t[0][1] if t else 0
                                if n + off != tn: ok = False; break
                                if t and col != t[0][0]: ok_item = False
                            if not ok: continue
                            paints = []
                            if ok_item and any(tg): paints.append(("item", None))
                            if len(tcol) == 1: paints.append(("const", next(iter(tcol))))
                            for pmode, pc in paints:
                                def fn(g, role=role, unit=unit, scope=scope, off=off, pmode=pmode, pc=pc, render=render, fbg=fbg):
                                    gs = groups(g, role, unit, scope, fbg)
                                    if gs is None: return None
                                    col, n = gs[0]; n += off
                                    if pmode == "item" and col is None and n: return None
                                    c = col if pmode == "item" else pc
                                    return render([(c, n)] if n else [], g)
                                rn = role[0] + (str(role[1]) if len(role) > 1 else "")
                                yield ("count_to_glyph:%s[%s,%s,%s,+%d,%s]" % (cname, rn, unit, scope, off, pmode), 4, fn)
                                n_yield += 1
                                if n_yield >= 12: return
        else:
            for scope in ("all", "inbox"):
                for unit in UNITS:
                    for role in multi_roles:
                        ok = True
                        for k, t in enumerate(tg):
                            gs = G(k, role, unit, scope)
                            if gs is None or [(c, n) for c, n in gs if n] != list(t): ok = False; break
                        if not ok: continue
                        def fn(g, role=role, unit=unit, scope=scope, render=render, fbg=fbg):
                            gs = groups(g, role, unit, scope, fbg)
                            if gs is None: return None
                            return render([(c, n) for c, n in gs if n], g)
                        yield ("count_to_glyph:%s[%s,%s,%s,pour]" % (cname, role[0], unit, scope), 5, fn)
                        n_yield += 1
                        if n_yield >= 12: return

# ------------------------------------------------------------------ legend-box canvas
def find_legend(g):
    """a solid single-colour rectangle (colour != grid bg) whose interior holds isolated single-cell
    glyphs, one per row (or per column).  Returns (y0,x0,y1,x1, boxcol, [(y,x,colour)...]) or None."""
    bg = bg_of(g); h, w = H(g), W(g); found = []
    for c in sorted({v for r in g for v in r} - {bg}):
        cs = [(y, x) for y in range(h) for x in range(w) if g[y][x] == c]
        y0, x0, y1, x1 = bbox(cs)
        if (y1 - y0 + 1) * (x1 - x0 + 1) < 9: continue
        glyphs = []; ok = True
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                v = g[y][x]
                if v == c: continue
                if not (y0 < y < y1 and x0 < x < x1): ok = False; break
                if any(g[y + dy][x + dx] != c for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx): ok = False; break
                glyphs.append((y, x, v))
            if not ok: break
        if ok and len(glyphs) >= 1 and len({v for _, _, v in glyphs}) == len(glyphs):
            found.append((y0, x0, y1, x1, c, glyphs))
    return found[0] if len(found) == 1 else None

def _legend_render(g, counts, stride, axis):
    L = find_legend(g)
    if L is None: return None
    y0, x0, y1, x1, c, glyphs = L
    out = [r[x0:x1 + 1] for r in g[y0:y1 + 1]]
    for y, x, v in glyphs:
        n = counts.get(v)
        if n is None: return None
        for k in range(max(n, 0)):
            yy, xx = (y - y0, x - x0 + k * stride) if axis == "row" else (y - y0 + k * stride, x - x0)
            if not (0 <= yy < len(out) and 0 <= xx < len(out[0])): return None
            if k and out[yy][xx] != c: return None
            out[yy][xx] = v if n else c
    return out

def legend_counts(g, unit, scope):
    """count, for each legend colour, its items (unit) outside (or everywhere) the legend box."""
    L = find_legend(g)
    if L is None: return None
    y0, x0, y1, x1, c, glyphs = L
    gg = [list(r) for r in g]
    if scope == "outside":
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): gg[y][x] = c
    return {v: count_unit(gg, v, unit, bg_of(g), None) for _, _, v in glyphs}

def fam_legend_count(train):
    """canvas = the legend box itself; every glyph in it is repeated N times along its row/column
    (stride induced), N = number of items of the glyph's colour elsewhere in the grid."""
    if len(train) < 2: return
    ins = [p["input"] for p in train]; outs = [p["output"] for p in train]
    Ls = [find_legend(g) for g in ins]
    if any(L is None for L in Ls): return
    if any((L[2] - L[0] + 1, L[3] - L[1] + 1) != (H(o), W(o)) for L, o in zip(Ls, outs)): return
    n = 0
    for unit in ("comp8", "comp4", "cells", "big4", "single8"):
        for scope in ("outside", "all"):
            for axis in ("row", "col"):
                for stride in (2, 1):
                    def fn(g, unit=unit, scope=scope, axis=axis, stride=stride):
                        cnt = legend_counts(g, unit, scope)
                        return None if cnt is None else _legend_render(g, cnt, stride, axis)
                    if all(fn(i) == o for i, o in zip(ins, outs)):
                        yield ("count_to_glyph:legend[%s,%s,%s,s%d]" % (unit, scope, axis, stride), 5, fn)
                        n += 1
                        if n >= 2: return

FAMILIES = (fam_count_to_glyph, fam_legend_count)
