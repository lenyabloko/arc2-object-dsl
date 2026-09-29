"""summarise.ranked_bars: colour classes are ranked by an induced key and rendered as bars.

One parametrised primitive.  Parameters, all induced from the training pairs by decoding the
outputs (never literal task constants):
  filter  : which colour classes are items   (all | no-grid: drop colours owning a full row/col |
                                               straight: only colours lying in one row or column)
  select  : all | drop-first (after sorting) | keep-max(f) (only items with the largest feature f)
  key/dir : ordering (numeric feature asc/desc, position incl. auto axis, occlusion layering)
  length  : bar length (a numeric feature | 1 | full canvas width)
  mode    : bars (one row per item) | wrap (item starts a row, wraps at width) | pour (continuous)
  canvas  : rows / cols from {#items, max length, fixed size, input H, input W}
  frame   : one of the 8 dihedral maps (bar axis, alignment side, order direction)
Zero-length bars are not drawn (their items vanish), which is how marker colours drop out.
"""
import sys
sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, D8

INV = {"id": "id", "r90": "r270", "r270": "r90", "r180": "r180", "fh": "fh", "fv": "fv", "T": "T", "aT": "aT"}

def _compose_T():
    """name of t∘T for each t (used when the ordering axis is x: canonical grid is transposed first)."""
    probe = [[1, 2, 3], [4, 5, 6]]
    imgs = {k: f(probe) for k, f in D8.items()}
    out = {}
    for k, f in D8.items():
        r = f(D8["T"](probe))
        out[k] = next(n for n, im in imgs.items() if im == r)
    return out
TCOMP = _compose_T()

NUM = ("ncells", "nobj4", "nobj8", "height", "width", "maxobj", "holes", "enclosed")
POS = ("miny", "minx", "cy", "cx", "first", "auto")
KEYS = NUM + ("value",) + POS + ("layer",)
FILTERS = ("all", "no-grid", "straight")

# ------------------------------------------------------------------ item features
def _enclosed(g, c, bg):
    """cells not of colour c that cannot reach the grid border without crossing colour c."""
    h, w = H(g), W(g); seen = [[False] * w for _ in range(h)]; st = []
    for y in range(h):
        for x in range(w):
            if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] != c:
                seen[y][x] = True; st.append((y, x))
    while st:
        y, x = st.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and g[yy][xx] != c:
                seen[yy][xx] = True; st.append((yy, xx))
    hb = sum(1 for y in range(h) for x in range(w) if not seen[y][x] and g[y][x] == bg)
    ho = sum(1 for y in range(h) for x in range(w) if not seen[y][x] and g[y][x] not in (bg, c))
    return hb, ho

def _layers(g, bg, cells):
    """Bottom-to-top occlusion order of colour classes, or None if not uniquely determined."""
    above = {c: set() for c in cells}
    for c, cs in cells.items():
        ys = [y for y, _ in cs]; xs = [x for _, x in cs]
        r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
        if all(y in (r0, r1) or x in (c0, c1) for y, x in cs):
            exp = [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if y in (r0, r1) or x in (c0, c1)]
        elif r1 - r0 == c1 - c0 and all(y - x == r0 - c0 for y, x in cs):
            exp = [(r0 + k, c0 + k) for k in range(r1 - r0 + 1)]
        elif r1 - r0 == c1 - c0 and all(y + x == r0 + c1 for y, x in cs):
            exp = [(r0 + k, c1 - k) for k in range(r1 - r0 + 1)]
        else:
            exp = [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)]
        for y, x in exp:
            d = g[y][x]
            if d != c and d != bg and d in above: above[c].add(d)
    # Kahn: bottom = colour with nothing below it
    below = {c: {d for d in cells if c in above[d]} for c in cells}
    order, left = [], set(cells)
    while left:
        free = [c for c in left if not (below[c] & left)]
        if len(free) != 1: return None
        order.append(free[0]); left.discard(free[0])
    return order

def features(g, bgspec="mode"):
    bg = bg_of(g) if bgspec == "mode" else -1 if bgspec == "none" else bgspec
    h, w = H(g), W(g)
    cells = {}
    for y in range(h):
        for x in range(w):
            if g[y][x] != bg: cells.setdefault(g[y][x], []).append((y, x))
    o4 = Counter(g[ob[0][0]][ob[0][1]] for ob in objects(g, bg, False, True))
    obs8 = objects(g, bg, True, True)
    o8 = Counter(g[ob[0][0]][ob[0][1]] for ob in obs8)
    mo = {}
    for ob in obs8:
        c = g[ob[0][0]][ob[0][1]]; mo[c] = max(mo.get(c, 0), len(ob))
    F = {}
    for c, cs in cells.items():
        ys = [y for y, _ in cs]; xs = [x for _, x in cs]
        hb, ho = _enclosed(g, c, bg)
        full = any(all(g[y][x] == c for x in range(w)) for y in set(ys)) or any(all(g[y][x] == c for y in range(h)) for x in set(xs))
        cy = sum(ys) / len(ys); cx = sum(xs) / len(xs)
        F[c] = {"ncells": len(cs), "nobj4": o4[c], "nobj8": o8[c], "height": max(ys) - min(ys) + 1,
                "width": max(xs) - min(xs) + 1, "maxobj": mo[c], "holes": hb, "enclosed": ho,
                "value": c, "miny": min(ys), "minx": min(xs), "cy": cy, "cx": cx,
                "first": min(cs), "grid": full, "straight": len(set(ys)) == 1 or len(set(xs)) == 1}
    return {"bg": bg, "F": F, "cells": cells, "h": h, "w": w, "g": g}

def order_items(info, flt, key, desc, sel):
    """Returns (ordered colours, transposed?) or None."""
    F = info["F"]
    items = [c for c in F if flt == "all" or (flt == "no-grid" and not F[c]["grid"]) or (flt == "straight" and F[c]["straight"])]
    if not items: return None
    tr = False
    if key == "layer":
        lay = _layers_cached(info, tuple(sorted(items)))
        if lay is None: return None
        seq = lay[::-1] if desc else lay
    else:
        k = key
        if key == "auto":
            sy = max(F[c]["cy"] for c in items) - min(F[c]["cy"] for c in items)
            sx = max(F[c]["cx"] for c in items) - min(F[c]["cx"] for c in items)
            if sx == sy: return None
            tr = sx > sy; k = "cx" if tr else "cy"
        vals = [F[c][k] for c in items]
        if len(set(vals)) != len(vals): return None      # ambiguous ranking
        seq = sorted(items, key=lambda c: F[c][k], reverse=desc)
    if sel == "drop-first":
        seq = seq[1:]
    elif sel.startswith("max:"):
        f = sel[4:]; m = max(F[c][f] for c in seq); seq = [c for c in seq if F[c][f] == m]
    return seq, tr

def _layers_cached(info, items):
    ck = ("layer", items)
    if ck not in info:
        info[ck] = _layers(info["g"], info["bg"], {c: info["cells"][c] for c in items})
    return info[ck]

# ------------------------------------------------------------------ decode / render
def decode(C, bg, mode):
    """Canonical grid -> list of (colour, length) or None."""
    h, w = H(C), W(C)
    if mode == "pour":
        flat = [v for r in C for v in r]
        while flat and flat[-1] == bg: flat.pop()
        seq = []
        for v in flat:
            if v == bg: return None
            if seq and seq[-1][0] == v: seq[-1][1] += 1
            else: seq.append([v, 1])
        return [tuple(s) for s in seq]
    rows = []
    for r in C:
        L = 0
        while L < w and r[L] != bg: L += 1
        if L and any(v != r[0] for v in r[:L]): return None
        if any(v != bg for v in r[L:]): return None
        rows.append((r[0] if L else None, L))
    while rows and rows[-1][1] == 0: rows.pop()
    if any(L == 0 for _, L in rows): return None
    if mode == "bars": return rows
    seq = []
    for i, (c, L) in enumerate(rows):
        if seq and seq[-1][0] == c and rows[i - 1][1] == w: seq[-1][1] += L
        else: seq.append([c, L])
    return [tuple(s) for s in seq]

def render(seq, R, Cn, bg, mode):
    if R <= 0 or Cn <= 0 or R > 30 or Cn > 30: return None
    out = [[bg] * Cn for _ in range(R)]
    if mode == "bars":
        if len(seq) > R: return None
        for i, (c, L) in enumerate(seq):
            if L > Cn: return None
            for x in range(L): out[i][x] = c
    elif mode == "wrap":
        y = 0
        for c, L in seq:
            while L > 0:
                if y >= R: return None
                k = min(L, Cn)
                for x in range(k): out[y][x] = c
                L -= k; y += 1
    else:
        pos = 0
        for c, L in seq:
            for _ in range(L):
                if pos >= R * Cn: return None
                out[pos // Cn][pos % Cn] = c; pos += 1
    return out

def dim(rule, g, n, lens):
    if rule == "n": return n
    if rule == "maxlen": return max(lens) if lens else 0
    if rule == "inH": return H(g)
    if rule == "inW": return W(g)
    return rule  # fixed int

def program(bgs, flt, key, desc, sel, length, mode, rrule, crule, t):
    def fn(g):
        info = features(g, bgs)
        r = order_items(info, flt, key, desc, sel)
        if r is None: return None
        seq, tr = r
        F = info["F"]
        n = len(seq)
        if length == "full":
            Cn = dim(crule, g, n, [])
            lens = [Cn] * n
        else:
            lens = [1 if length == "one" else F[c][length] for c in seq]
            Cn = dim(crule, g, n, lens)
        items = [(c, L) for c, L in zip(seq, lens) if L > 0]
        if not items: return None
        R = dim(rrule, g, len(items), lens)
        out = render(items, R, Cn, info["bg"], mode)
        if out is None: return None
        tt = TCOMP[t] if tr else t
        return D8[tt](out)
    return fn

# ------------------------------------------------------------------ induction
def _score(sig):
    bgs, mode, t, flt, key, desc, sel, length, rr, cr = sig
    s = (sel != "all") + (flt != "all") + (bgs != "mode") + isinstance(rr, int) + isinstance(cr, int)
    if key == length: pass
    elif key in ("layer", "auto", "value", "first"): s += 0.5
    elif key in POS: s += 1
    else: s += 2
    return s

def fam_ranked_bars(train):
    o0 = train[0]["output"]
    if H(o0) * W(o0) > 400: return
    common = set.intersection(*[{v for r in p["input"] for v in r} for p in train])
    bgspecs = ["mode", "none"] + sorted(c for c in common if any(bg_of(p["input"]) != c for p in train))
    found = []
    for bgs in bgspecs:
        infos = []
        for p in train:
            info = features(p["input"], bgs)
            if len(info["F"]) < 1 or len(info["F"]) > 12: infos = None; break
            infos.append(info)
        if not infos: continue
        dec = {}
        for mode in ("bars", "wrap", "pour"):
            for t in D8:
                ds = []
                for p, info in zip(train, infos):
                    C = D8[INV[t]](p["output"])
                    d = decode(C, info["bg"], mode)
                    if not d: ds = None; break
                    ds.append((d, H(C), W(C)))
                dec[(mode, t)] = ds
        if not any(dec.values()): continue
        sels = ["all", "drop-first"] + ["max:" + f for f in NUM]
        for mode in ("bars", "wrap", "pour"):
            for t in D8:
                if dec[(mode, t)] is None and dec[(mode, TCOMP[t])] is None: continue
                for flt in FILTERS:
                    for key in KEYS:
                        for desc in (False, True):
                            for sel in sels:
                                res = _match(train, infos, dec, mode, t, flt, key, desc, sel)
                                if not res: continue
                                for length, rr, cr in res:
                                    sig = (bgs, mode, t, flt, key, desc, sel, length, rr, cr)
                                    fn = program(bgs, flt, key, desc, sel, length, mode, rr, cr, t)
                                    if all(fn(p["input"]) == p["output"] for p in train):
                                        found.append((_score(sig), len(found), sig, fn))
                                if len(found) > 300: break
    found.sort(key=lambda x: (x[0], x[1]))
    for sc, _, sig, fn in found[:4]:
        bgs, mode, t, flt, key, desc, sel, length, rr, cr = sig
        name = f"ranked-bars:{mode}[bg={bgs},{flt},{sel},key={key}{'-' if desc else '+'},len={length},rows={rr},cols={cr},{t}]"
        yield (name, 5, fn)

def _match(train, infos, dec, mode, t, flt, key, desc, sel):
    per = []
    multi = False
    for p, info in zip(train, infos):
        r = order_items(info, flt, key, desc, sel)
        if r is None: return None
        seq, tr = r
        tt = TCOMP[t] if tr else t
        ds = dec.get((mode, tt))
        if ds is None: return None
        d, R, Cn = ds[len(per)]
        cols = [c for c, _ in d]
        if not set(cols) <= set(seq): return None
        if len(cols) >= 2: multi = True
        per.append((info, seq, d, R, Cn))
    if not multi: return None
    # lengths: items missing from the decoded sequence must have length 0 under the feature
    lens_ok = []
    for length in NUM + ("one", "full"):
        ok = True
        for info, seq, d, R, Cn in per:
            dd = dict(d)
            kept = [c for c in seq if c in dd]
            if [c for c, _ in d] != kept: ok = False; break
            for c in seq:
                if length == "one": L = 1
                elif length == "full": L = Cn
                else: L = info["F"][c][length]
                if dd.get(c, 0) != L: ok = False; break
            if not ok: break
        if ok: lens_ok.append(length)
    if not lens_ok: return None
    out = []
    for length in lens_ok:
        rrs = []; crs = []
        for rule in ("n", "maxlen", "inH", "inW"):
            if all(R == _dimv(rule, info, len(d), [L for _, L in d]) for info, seq, d, R, Cn in per):
                rrs.append(rule)
            if length != "full" and all(Cn == _dimv(rule, info, len(d), [L for _, L in d]) for info, seq, d, R, Cn in per):
                crs.append(rule)
        if len({R for _, _, _, R, _ in per}) == 1: rrs.append(per[0][3])
        if len({Cn for _, _, _, _, Cn in per}) == 1: crs.append(per[0][4])
        if length == "full":
            for rule in ("n", "inH", "inW"):
                if all(Cn == _dimv(rule, info, len(d), []) for info, seq, d, R, Cn in per): crs.append(rule)
        if rrs and crs: out.append((length, rrs[0], crs[0]))
    return out

def _dimv(rule, info, n, lens):
    if rule == "n": return n
    if rule == "maxlen": return max(lens) if lens else -1
    if rule == "inH": return info["h"]
    if rule == "inW": return info["w"]

FAMILIES = (fam_ranked_bars,)
