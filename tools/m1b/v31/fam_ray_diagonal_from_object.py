"""ray.diagonal_from_object: rays emitted from selected corners of objects.

One parametrised primitive  corner_rays(pre, sel, src, key, paint, width, stop):
  pre   : none | scale k | canvas enlarge (input pasted at an induced corner of a larger blank canvas);
          k in {fixed ratio, #colours, #non-bg cells}, canvas base (H,W) or (M,M) with M=max(H,W)
  sel   : where rays start and which way they go
            outer   - convex outer corners of cells: a diagonal direction d is emitted when the diagonal
                      neighbour and both orthogonal neighbours on that side are background
            missing - an object (single colour, 8-conn) whose bounding box lacks exactly one corner cell
                      emits from that missing corner, outward
            radial  - every cell of a multicolour object emits in sign(cell - bbox centre) (8 directions),
                      when the next cell leaves the object
  src   : which cells may emit: all | big (colour with the largest bounding box) | vanish (colours present
          in every train input and absent from every output: flags)
  key   : directions on/off induced from training either globally or per source colour
  paint : own colour | the object's / grid's other colour | a constant colour seen in all outputs
  width : 1 (single-cell ray) | object (the whole object is swept along the direction, and recoloured)
  stop  : edge (paint background cells only, pass over the rest) | block (stop at the first non-background)
Everything is induced from the training pairs and every candidate is verified on all of them before it is
yielded.
"""
import sys; sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox

DIAG = [(-1, -1), (-1, 1), (1, -1), (1, 1)]


def sgn(v): return (v > 0) - (v < 0)


def ncol(g, bg): return len({v for r in g for v in r} - {bg})
def ncell(g, bg): return sum(v != bg for r in g for v in r)


KRULES = {"ncol": ncol, "ncell": ncell}


def pre_candidates(train, bgc):
    """Yield (name, fn(g, bg) -> grid) consistent with all training shapes."""
    i0, o0 = train[0]["input"], train[0]["output"]
    shp = [((H(p["input"]), W(p["input"])), (H(p["output"]), W(p["output"]))) for p in train]
    if all(a == b for a, b in shp):
        yield "none", lambda g, bg: [r[:] for r in g]
        return
    def kfix(g, bg, k): return k
    rules = []
    if H(o0) % H(i0) == 0 and W(o0) % W(i0) == 0 and H(o0) // H(i0) == W(o0) // W(i0):
        rules.append(("k%d" % (H(o0) // H(i0)), lambda g, bg, k=H(o0) // H(i0): k))
    M0 = max(H(i0), W(i0))
    if H(o0) == W(o0) and H(o0) % M0 == 0 and ("k%d" % (H(o0) // M0)) not in [r[0] for r in rules]:
        rules.append(("k%d" % (H(o0) // M0), lambda g, bg, k=H(o0) // M0: k))
    for kn, kf in KRULES.items():
        rules.append((kn, kf))
    for kname, kf in rules:
        # scale
        def scale(g, bg, kf=kf):
            k = kf(g, bg)
            if k < 1 or k * max(H(g), W(g)) > 30: return None
            return [[v for v in r for _ in range(k)] for r in g for _ in range(k)]
        # canvas
        for base in ("hw", "mm"):
            for ay in (0, 1):
                for ax in (0, 1):
                    def canvas(g, bg, kf=kf, base=base, ay=ay, ax=ax):
                        k = kf(g, bg)
                        bh, bw = (H(g), W(g)) if base == "hw" else (max(H(g), W(g)),) * 2
                        oh, ow = bh * k, bw * k
                        if k < 1 or oh > 30 or ow > 30 or oh < H(g) or ow < W(g): return None
                        out = [[bg] * ow for _ in range(oh)]
                        y0 = 0 if ay == 0 else oh - H(g); x0 = 0 if ax == 0 else ow - W(g)
                        for y in range(H(g)):
                            for x in range(W(g)): out[y0 + y][x0 + x] = g[y][x]
                        return out
                    yield f"canvas[{base},{kname},{'tb'[ay]}{'lr'[ax]}]", canvas
        yield f"scale[{kname}]", scale


def grid_other(g, bg, own):
    cnt = Counter(v for r in g for v in r if v != bg and v != own)
    return cnt.most_common(1)[0][0] if cnt else None


def emissions(g, bg, sel, srcset):
    """List of (oy, ox, dy, dx, own, other, cells)."""
    h, w = H(g), W(g); em = []
    comps = objects(g, bg, diag=True, by_colour=False)
    comp_of = {}
    for ci, ob in enumerate(comps):
        for c in ob: comp_of[c] = ci
    def other_of(ci, own):
        cnt = Counter(g[y][x] for y, x in comps[ci] if g[y][x] != own)
        return cnt.most_common(1)[0][0] if cnt else grid_other(g, bg, own)
    def nb(y, x): return not (0 <= y < h and 0 <= x < w) or g[y][x] == bg
    if sel == "outer":
        for y in range(h):
            for x in range(w):
                v = g[y][x]
                if v == bg or (srcset is not None and v not in srcset): continue
                for dy, dx in DIAG:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and g[yy][xx] == bg and nb(yy, x) and nb(y, xx):
                        ci = comp_of[(y, x)]
                        em.append((y, x, dy, dx, v, other_of(ci, v), comps[ci]))
    elif sel == "cell":
        for y in range(h):
            for x in range(w):
                v = g[y][x]
                if v == bg or (srcset is not None and v not in srcset): continue
                ci = comp_of[(y, x)]
                for dy, dx in DIAG:
                    em.append((y, x, dy, dx, v, other_of(ci, v), comps[ci]))
    elif sel == "missing":
        for ob in objects(g, bg, diag=True, by_colour=True):
            v = g[ob[0][0]][ob[0][1]]
            if len(ob) < 2 or (srcset is not None and v not in srcset): continue
            r0, c0, r1, c1 = bbox(ob)
            if r0 == r1 or c0 == c1: continue
            s = set(ob)
            miss = [(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if (y, x) not in s]
            if len(miss) != 1: continue
            y, x = miss[0]
            if y not in (r0, r1) or x not in (c0, c1) or g[y][x] != bg: continue
            dy = -1 if y == r0 else 1; dx = -1 if x == c0 else 1
            ci = comp_of[ob[0]]
            em.append((y, x, dy, dx, v, other_of(ci, v), ob))
    elif sel == "radial":
        for ci, ob in enumerate(comps):
            if len(ob) < 2: continue
            r0, c0, r1, c1 = bbox(ob); s = set(ob)
            for y, x in ob:
                v = g[y][x]
                if srcset is not None and v not in srcset: continue
                dy, dx = sgn(2 * y - r0 - r1), sgn(2 * x - c0 - c1)
                if (dy, dx) == (0, 0) or (y + dy, x + dx) in s: continue
                em.append((y, x, dy, dx, v, other_of(ci, v), ob))
    return em


def paint_of(e, paint):
    if paint == "own": return e[4]
    if paint == "other": return e[5]
    return paint


def cast(g, bg, ems, on, keymode, paint, width, stop):
    h, w = H(g), W(g); out = [r[:] for r in g]
    for e in ems:
        oy, ox, dy, dx, own = e[:5]
        key = (dy, dx) if keymode == "global" else (own, dy, dx)
        if keymode != "global" and own not in {k[0] for k in on}: return None  # unseen source colour
        if not on.get(key, True): continue
        col = paint_of(e, paint)
        if col is None: return None
        if width == 1:
            y, x = oy + dy, ox + dx
            while 0 <= y < h and 0 <= x < w:
                if g[y][x] != bg:
                    if stop == "block": break
                else: out[y][x] = col
                y += dy; x += dx
        else:
            cells = e[6]; s = set(cells)
            for y, x in cells: out[y][x] = col
            k = 1
            while True:
                pts = [(y + k * dy, x + k * dx) for y, x in cells]
                pts = [(y, x) for y, x in pts if 0 <= y < h and 0 <= x < w]
                if not pts: break
                if stop == "block" and any(g[y][x] != bg and (y, x) not in s for y, x in pts): break
                for y, x in pts:
                    if g[y][x] == bg: out[y][x] = col
                k += 1
    return out


def induce_on(pairs, bgs, sel, srcsets, keymode, paint):
    """Vote directions on/off from the first ray cell. None if contradictory or nothing fires."""
    votes = {}
    for (g, o), bg, ss in zip(pairs, bgs, srcsets):
        for e in emissions(g, bg, sel, ss):
            oy, ox, dy, dx, own = e[:5]
            y, x = oy + dy, ox + dx
            if not (0 <= y < H(g) and 0 <= x < W(g)) or g[y][x] != bg: continue
            col = paint_of(e, paint)
            if col is None: return None
            key = (dy, dx) if keymode == "global" else (own, dy, dx)
            votes.setdefault(key, set()).add(o[y][x] == col)
    if any(len(v) > 1 for v in votes.values()): return None
    on = {k: True in v for k, v in votes.items()}
    if not any(on.values()): return None
    return on


def fam_corner_rays(train):
    i0, o0 = train[0]["input"], train[0]["output"]
    bgs_in = [bg_of(p["input"]) for p in train]
    fixed_bg = bgs_in[0] if len(set(bgs_in)) == 1 else None
    def bgf(g):
        return fixed_bg if fixed_bg is not None and any(fixed_bg in r for r in g) else bg_of(g)
    ci_all = [{v for r in p["input"] for v in r} for p in train]
    co_all = [{v for r in p["output"] for v in r} for p in train]
    vanish = set.intersection(*ci_all) - set.union(*co_all)
    consts = set.intersection(*co_all) - {fixed_bg}
    found = 0
    for pname, pf in pre_candidates(train, fixed_bg):
        pairs = []
        for p in train:
            g = pf(p["input"], bgf(p["input"]))
            if g is None or (H(g), W(g)) != (H(p["output"]), W(p["output"])): pairs = None; break
            pairs.append((g, p["output"]))
        if not pairs: continue
        bgs = [bgf(p["input"]) for p in train]
        # cells that change must change from background (rays add, never erase) except sweep recolour
        for src in ("all", "big", "vanish"):
            if src == "vanish" and not vanish: continue
            def srcset_of(g, bg, src=src):
                if src == "all": return None
                if src == "vanish": return vanish
                cols = {v for r in g for v in r} - {bg}
                if not cols: return set()
                def area(c):
                    cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == c]
                    r0, c0, r1, c1 = bbox(cells); return (r1 - r0 + 1) * (c1 - c0 + 1)
                ar = sorted(((area(c), c) for c in cols), reverse=True)
                if len(ar) > 1 and ar[0][0] == ar[1][0]: return set()
                return {ar[0][1]}
            srcsets = [srcset_of(g, bg) for (g, _), bg in zip(pairs, bgs)]
            for sel in ("outer", "cell", "missing", "radial"):
                for paint in ["own", "other"] + sorted(consts):
                    for keymode in ("global", "colour"):
                        on = induce_on(pairs, bgs, sel, srcsets, keymode, paint)
                        if on is None: continue
                        for width in (1, "obj"):
                            for stop in ("edge", "block"):
                                def fn(g, pf=pf, sel=sel, srcset_of=srcset_of, on=on, keymode=keymode,
                                       paint=paint, width=width, stop=stop):
                                    bg = bgf(g); gg = pf(g, bg)
                                    if gg is None: return None
                                    ems = emissions(gg, bg, sel, srcset_of(gg, bg))
                                    if not ems: return None
                                    return cast(gg, bg, ems, on, keymode, paint, width, stop)
                                ok = True
                                for (g, o), p in zip(pairs, train):
                                    r = fn(p["input"])
                                    if r != o: ok = False; break
                                if not ok: continue
                                cost = 3 + (pname != "none") + (src != "all") + 2 * (keymode != "global") + (width != 1)
                                yield (f"diag-rays[{pname};{sel};{src};{keymode};{paint};w{width};{stop}]", cost, fn)
                                found += 1
                                if found >= 6: return
                                break  # one stop mode suffices when both fit


# ---------------------------------------------------------------- side segments of objects on a patterned bg
def bg_model(g):
    """background as a function (y,x)->colour: a 2-colour checkerboard covering most of the grid,
    else the plain majority colour."""
    h, w = H(g), W(g)
    cnt = [Counter(), Counter()]
    for y in range(h):
        for x in range(w): cnt[(y + x) % 2][g[y][x]] += 1
    a, na = cnt[0].most_common(1)[0]; b, nb = cnt[1].most_common(1)[0]
    if a != b and na + nb >= 0.8 * h * w:
        return lambda y, x: a if (y + x) % 2 == 0 else b
    c = bg_of(g)
    return lambda y, x: c

def side_segments(g, bgf):
    """per object (8-conn cells deviating from the background), each non-body colour must form straight
    diagonal runs on the object's boundary; yields (cells sorted along the run, outward direction)."""
    h, w = H(g), W(g)
    dev = {(y, x) for y in range(h) for x in range(w) if g[y][x] != bgf(y, x)}
    seen = set(); segs = []
    for st in sorted(dev):
        if st in seen: continue
        comp = []; stack = [st]; seen.add(st)
        while stack:
            y, x = stack.pop(); comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    p = (y + dy, x + dx)
                    if p in dev and p not in seen: seen.add(p); stack.append(p)
        if len(comp) < 3: return None
        cols = Counter(g[y][x] for y, x in comp)
        body = cols.most_common(1)[0][0]
        cy = sum(y for y, _ in comp) / len(comp); cx = sum(x for _, x in comp) / len(comp)
        for c in cols:
            if c == body: continue
            cells = [p for p in comp if g[p[0]][p[1]] == c]
            # split into diagonal runs
            left = set(cells)
            while left:
                p0 = min(left); run = None
                for d in ((1, 1), (1, -1)):
                    r = [p0]
                    while (r[-1][0] + d[0], r[-1][1] + d[1]) in left: r.append((r[-1][0] + d[0], r[-1][1] + d[1]))
                    if len(r) >= 2 and (run is None or len(r) > len(run[0])): run = (r, d)
                if run is None: return None
                r, d = run
                left -= set(r)
                # outward: the perpendicular diagonal pointing away from the object's centre
                my = sum(y for y, _ in r) / len(r); mx = sum(x for _, x in r) / len(r)
                best = None
                for o in ((d[0], -d[1]), (-d[0], d[1])):
                    dot = o[0] * (my - cy) + o[1] * (mx - cx)
                    if best is None or dot > best[0]: best = (dot, o)
                if best[0] <= 0: return None
                segs.append((c, r, best[1]))
    return segs

def seg_rays(g, emit, stop):
    bgf = bg_model(g)
    segs = side_segments(g, bgf)
    if not segs: return None
    out = [r[:] for r in g]
    for c, r, (dy, dx) in segs:
        src = r if emit == "all" else [r[0], r[-1]]
        for y, x in src:
            yy, xx = y + dy, x + dx
            while 0 <= yy < H(g) and 0 <= xx < W(g):
                if g[yy][xx] != bgf(yy, xx):
                    if stop: break
                else: out[yy][xx] = c
                yy += dy; xx += dx
    return out

def fam_side_segment_rays(train):
    """objects on a (possibly checkerboard) background carry coloured straight diagonal side segments;
    each segment is swept outward (perpendicular, away from the object) to the edge.  Induced: which
    segment cells emit (the two ends, i.e. the band's outline, or all of them) and edge/block stop."""
    i0, o0 = train[0]["input"], train[0]["output"]
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if not side_segments(i0, bg_model(i0)): return
    for emit in ("ends", "all"):
        for stop in (False, True):
            yield ("diag-rays:side-segments[%s,%s]" % (emit, "block" if stop else "edge"), 5,
                   lambda g, emit=emit, stop=stop: seg_rays(g, emit, stop))

FAMILIES = (fam_corner_rays, fam_side_segment_rays)
