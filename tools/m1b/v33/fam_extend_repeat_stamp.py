"""extend.repeat_stamp: a template is copied repeatedly along a translation vector.

One primitive  REPEAT(template T, vector v, stop, colour)  -- paint T + k*v for k = 1, 2, ... until the
copy leaves the grid (or, with stop=hit, until the copy overlaps its target, inclusive).
Every parameter is induced per task; the *inducer* says where T, v, stop and colour come from:

  fragment  T = the unique largest object; every other object M is a fragment of a copy: v is the one
            direction d (8 dirs) whose step-shift of T contains M; step in {bbox+g, minfree+g}, g in {0,1}
            (minfree = smallest shift with no overlap).  Copies take M's colour, M is erased first.
  toward    T = template object, aligned target object (perpendicular spans overlap) lies in direction d;
            copies of T step size+g until one overlaps the target.  Target role: 'share' (single-colour
            object whose colour occurs in the multi-colour T) or 'vanish' (colour that disappears in all
            training outputs).  Targets optionally erased.
  self      every object repeats itself along (sy*(h+g), sx*(w+g)); the sign set is induced from the first
            training pair (directions whose first copy agrees with the output).
  stub      stub = component of non-anchor colours touching an anchor-colour object on one side;
            v = away from the anchor, |v| = stub extent (the stub's own period) -> continued to the edge.
  legend    identical shapes stacked with pitch = shape extent; a striped legend object gives the colour
            order; the stack is completed (both ways) to the full legend sequence, legend erased.
  motif     single-cell seeds; motif M (cells in the box between seed and seed+v, colours as roles
            seed/constant) and the set of vectors v are learned from the first pair's difference.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox

D8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
D4 = D8[:4]


def same_size(train):
    return all((H(p["input"]), W(p["input"])) == (H(p["output"]), W(p["output"])) for p in train)


def chain(out, cells, v, stop=None, kmax=40):
    """cells: list of (y,x,c). Paint cells+k*v, k=1.. while any cell is inside; stop(inside) ends it."""
    h, w = H(out), W(out); vy, vx = v
    if v == (0, 0): return
    for k in range(1, kmax):
        ins = [(y + k * vy, x + k * vx, c) for y, x, c in cells
               if 0 <= y + k * vy < h and 0 <= x + k * vx < w]
        if not ins: return
        for y, x, c in ins: out[y][x] = c
        if stop and stop(ins): return


def comps(g, keep, diag=False):
    """Multicolour components of cells where keep(y,x)."""
    h, w = H(g), W(g); seen = set(); res = []
    nb = D8 if diag else D4
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or not keep(y, x): continue
            st = [(y, x)]; seen.add((y, x)); cs = []
            while st:
                a, b = st.pop(); cs.append((a, b))
                for dy, dx in nb:
                    q = (a + dy, b + dx)
                    if 0 <= q[0] < h and 0 <= q[1] < w and q not in seen and keep(*q):
                        seen.add(q); st.append(q)
            res.append(cs)
    return res


def step_vec(cells, d, mode):
    dy, dx = d
    y0, x0, y1, x1 = bbox(cells)
    kind, g = mode[:-1], int(mode[-1])
    if kind == "bbox":
        return (dy * (y1 - y0 + 1 + g), dx * (x1 - x0 + 1 + g))
    s = set(cells)
    for k in range(1, 31):
        if not any((y + k * dy, x + k * dx) in s for y, x in cells):
            return (dy * (k + g), dx * (k + g))
    return None


# ------------------------------------------------------------------ fragment
def fam_fragment(train):
    if not same_size(train): return
    for diag in (True, False):
        for mode in ("minfree0", "bbox1", "bbox0", "minfree1"):
            def fn(g, diag=diag, mode=mode):
                bg = bg_of(g); obs = objects(g, bg, diag, True)
                if len(obs) < 2: return None
                obs.sort(key=len, reverse=True)
                if len(obs[0]) == len(obs[1]) or len(obs[0]) < 3: return None
                T = obs[0]; out = [r[:] for r in g]
                for M in obs[1:]:
                    for y, x in M: out[y][x] = bg
                for M in obs[1:]:
                    ms = set(M); hits = []
                    for d in D8:
                        v = step_vec(T, d, mode)
                        if v and ms <= {(y + v[0], x + v[1]) for y, x in T}: hits.append(v)
                    if len(hits) != 1: return None
                    c = g[M[0][0]][M[0][1]]
                    chain(out, [(y, x, c) for y, x in T], hits[0])
                return out
            yield (f"repeat:fragment[{mode},{'8' if diag else '4'}]", 4, fn)


# ------------------------------------------------------------------ toward
def vanish_colours(train):
    v = None
    for p in train:
        ci = {c for r in p["input"] for c in r}; co = {c for r in p["output"] for c in r}
        v = (ci - co) if v is None else v & (ci - co)
    return v or set()


def fam_toward(train):
    if not same_size(train): return
    van = vanish_colours(train)
    roles = ["share"] + (["vanish"] if van else [])
    for role in roles:
        for erase in (False, True):
            for gap in (0, 1):
                def fn(g, role=role, erase=erase, gap=gap):
                    bg = bg_of(g); obs = comps(g, lambda y, x: g[y][x] != bg)
                    col = lambda o: {g[y][x] for y, x in o}
                    if role == "share":
                        tps = [o for o in obs if len(col(o)) >= 2]
                        tgs = [o for o in obs if len(col(o)) == 1]
                    else:
                        tps = [o for o in obs if not col(o) & van]
                        tgs = [o for o in obs if col(o) <= van]
                    if not tps or not tgs: return None
                    out = [r[:] for r in g]
                    if erase:
                        for o in tgs:
                            for y, x in o: out[y][x] = bg
                    n = 0
                    for T in tps:
                        y0, x0, y1, x1 = bbox(T); ct = col(T)
                        for dy, dx in D4:
                            best = None
                            for M in tgs:
                                a0, b0, a1, b1 = bbox(M)
                                if dy:
                                    if b1 < x0 or b0 > x1: continue
                                    dist = a0 - y1 if dy > 0 else y0 - a1
                                else:
                                    if a1 < y0 or a0 > y1: continue
                                    dist = b0 - x1 if dx > 0 else x0 - b1
                                if dist <= 0: continue
                                if best is None or dist < best[0]: best = (dist, M)
                            if best is None: continue
                            M = best[1]
                            if role == "share" and not col(M) <= ct: continue
                            ms = set(M)
                            v = (dy * (y1 - y0 + 1 + gap), dx * (x1 - x0 + 1 + gap))
                            chain(out, [(y, x, g[y][x]) for y, x in T], v,
                                  stop=lambda ins, ms=ms: any((y, x) in ms for y, x, _ in ins))
                            n += 1
                    return out if n else None
                yield (f"repeat:toward[{role},{'erase' if erase else 'keep'},g{gap}]", 5, fn)


# ------------------------------------------------------------------ self
def fam_self(train):
    if not same_size(train): return
    i0, o0 = train[0]["input"], train[0]["output"]
    signs = [d for d in D8]
    for diag in (False, True):
        for gap in (0, 1):
            bg = bg_of(i0); obs = objects(i0, bg, diag, False)
            if not obs or len(obs) > 12: continue
            ok = []
            for sy, sx in signs:
                new = False; good = True
                for T in obs:
                    y0, x0, y1, x1 = bbox(T)
                    v = (sy * (y1 - y0 + 1 + gap), sx * (x1 - x0 + 1 + gap))
                    for y, x in T:
                        yy, xx = y + v[0], x + v[1]
                        if 0 <= yy < H(i0) and 0 <= xx < W(i0):
                            if o0[yy][xx] != i0[y][x]: good = False; break
                            if i0[yy][xx] != i0[y][x]: new = True
                    if not good: break
                if good and new: ok.append((sy, sx))
            if not ok: continue
            def fn(g, diag=diag, gap=gap, ok=tuple(ok)):
                bg = bg_of(g); obs = objects(g, bg, diag, False)
                if not obs: return None
                out = [r[:] for r in g]
                for T in obs:
                    y0, x0, y1, x1 = bbox(T)
                    for sy, sx in ok:
                        chain(out, [(y, x, g[y][x]) for y, x in T],
                              (sy * (y1 - y0 + 1 + gap), sx * (x1 - x0 + 1 + gap)))
                return out
            yield (f"repeat:self[{','.join('%d%d' % d for d in ok)},g{gap},{'8' if diag else '4'}]", 4, fn)


# ------------------------------------------------------------------ stub
def fam_stub(train):
    if not same_size(train): return
    cs = None
    for p in train:
        c = {v for r in p["input"] for v in r}
        cs = c if cs is None else cs & c
    for a in sorted(cs or ()):
        def fn(g, a=a):
            bg = bg_of(g)
            if a == bg: return None
            h, w = H(g), W(g)
            stubs = comps(g, lambda y, x: g[y][x] not in (bg, a))
            out = [r[:] for r in g]; n = 0
            for C in stubs:
                dirs = set()
                for y, x in C:
                    for dy, dx in D4:
                        yy, xx = y - dy, x - dx
                        if 0 <= yy < h and 0 <= xx < w and g[yy][xx] == a: dirs.add((dy, dx))
                if not dirs: continue
                if len(dirs) != 1: return None
                dy, dx = dirs.pop(); y0, x0, y1, x1 = bbox(C)
                chain(out, [(y, x, g[y][x]) for y, x in C], (dy * (y1 - y0 + 1), dx * (x1 - x0 + 1)))
                n += 1
            return out if n else None
        yield (f"repeat:stub[anchor={a}]", 4, fn)


# ------------------------------------------------------------------ legend
def legend_of(g, bg):
    """Multicolour rectangle whose colour is constant along one axis: returns (cells, colour order, axis)."""
    found = []
    for C in comps(g, lambda y, x: g[y][x] != bg):
        cols = {g[y][x] for y, x in C}
        if len(cols) < 2: continue
        y0, x0, y1, x1 = bbox(C)
        if len(C) != (y1 - y0 + 1) * (x1 - x0 + 1): continue
        if all(g[y][x] == g[y0][x] for y, x in C):
            seq = [g[y0][x] for x in range(x0, x1 + 1)]
        elif all(g[y][x] == g[y][x0] for y, x in C):
            seq = [g[y][x0] for y in range(y0, y1 + 1)]
        else: continue
        if len(set(seq)) != len(seq): continue
        found.append((C, seq))
    return found[0] if len(found) == 1 else None


def fam_legend(train):
    if not same_size(train): return
    for axis in (0, 1):
        for rev in (False, True):
            def fn(g, axis=axis, rev=rev):
                bg = bg_of(g); L = legend_of(g, bg)
                if not L: return None
                LC, seq = L
                if rev: seq = seq[::-1]
                lset = set(LC)
                obs = [o for o in objects(g, bg, True, True) if not set(o) & lset]
                if not obs: return None
                norm = lambda o: sorted((y - bbox(o)[0], x - bbox(o)[1]) for y, x in o)
                shape = norm(obs[0])
                if any(norm(o) != shape for o in obs): return None
                cols = [g[o[0][0]][o[0][1]] for o in obs]
                if len(set(cols)) != len(cols) or not set(cols) <= set(seq): return None
                obs = sorted(obs, key=lambda o: bbox(o)[axis])
                y0, x0, y1, x1 = bbox(obs[0])
                pitch = (y1 - y0 + 1) if axis == 0 else (x1 - x0 + 1)
                for j, o in enumerate(obs):
                    b = bbox(o)
                    if b[axis] != bbox(obs[0])[axis] + j * pitch or b[1 - axis] != bbox(obs[0])[1 - axis]: return None
                idx = [seq.index(c) for c in cols]
                if idx != list(range(idx[0], idx[0] + len(idx))): return None
                out = [r[:] for r in g]
                for y, x in LC: out[y][x] = bg
                base = obs[0]; bi = idx[0]; h, w = H(g), W(g)
                for j, c in enumerate(seq):
                    k = j - bi
                    off = (k * pitch, 0) if axis == 0 else (0, k * pitch)
                    for y, x in base:
                        yy, xx = y + off[0], x + off[1]
                        if not (0 <= yy < h and 0 <= xx < w): return None
                        out[yy][xx] = c
                return out
            yield (f"repeat:legend[{'rows' if axis == 0 else 'cols'},{'rev' if rev else 'fwd'}]", 5, fn)


# ------------------------------------------------------------------ motif
def _seeds(g, bg):
    """Seeds = multicolour 4-connected objects; (cells, bbox, colour or None if multicolour)."""
    res = []
    for C in comps(g, lambda y, x: g[y][x] != bg):
        cs = {g[y][x] for y, x in C}
        res.append((set(C), bbox(C), cs.pop() if len(cs) == 1 else None))
    return res


def _ref(bb, v):
    y0, x0, y1, x1 = bb
    ry = y0 if v[0] < 0 else y1 if v[0] > 0 else (y0 + y1) / 2
    rx = x0 if v[1] < 0 else x1 if v[1] > 0 else (x0 + x1) / 2
    if ry != int(ry) or rx != int(rx): return None
    return (int(ry), int(rx))


def _motif_paint(g, seeds, motifs):
    out = [r[:] for r in g]
    for C, bb, sc in seeds:
        for v, M in motifs:
            ref = _ref(bb, v)
            if ref is None: return None
            if any(r == "S" for r in M.values()) and sc is None: return None
            cells = [(ref[0] + a - v[0], ref[1] + b - v[1], sc if r == "S" else r) for (a, b), r in M.items()]
            chain(out, cells, v)
    return out


def fam_motif(train):
    """Seeds emit a periodic motif along learned vectors to the border (motif learned from all pairs)."""
    if not same_size(train): return
    data = []
    for p in train:
        i, o = p["input"], p["output"]; bg = bg_of(i); h, w = H(i), W(i)
        sd = _seeds(i, bg)
        if not sd or len(sd) > 10 or any(len(C) > 9 for C, _, _ in sd): return
        D = {(y, x): o[y][x] for y in range(h) for x in range(w) if o[y][x] != i[y][x]}
        if not D or any(i[y][x] != bg for y, x in D): return
        data.append((i, o, sd, D))
    newc = {c for _, _, _, D in data for c in D.values()}

    def motif_for(v):
        vy, vx = v; M = {}
        for i, o, sd, D in data:
            for C, bb, sc in sd:
                ref = _ref(bb, v)
                if ref is None: return None
                for a in range(min(0, vy), max(0, vy) + 1):
                    for b in range(min(0, vx), max(0, vx) + 1):
                        q = (ref[0] + a, ref[1] + b)
                        if q in C or q not in D: continue
                        r = "S" if sc is not None and D[q] == sc else D[q]
                        if M.setdefault((a, b), r) != r: return None
        return M

    cand = sorted({(a, b) for a in range(-4, 5) for b in range(-4, 5) if (a, b) != (0, 0)},
                  key=lambda v: (max(abs(v[0]), abs(v[1])), abs(v[0]) + abs(v[1])))
    active = []; covered = [set() for _ in data]
    for v in cand:
        M = motif_for(v)
        if not M or any(r != "S" and r not in newc for r in M.values()): continue
        diffs = []; good = True
        for (i, o, sd, D) in data:
            p = _motif_paint(i, sd, [(v, M)])
            if p is None: good = False; break
            diff = {(y, x) for y in range(H(i)) for x in range(W(i)) if p[y][x] != i[y][x]}
            if any(p[y][x] != o[y][x] for y, x in diff): good = False; break
            diffs.append(diff)
        if not good or all(d <= c for d, c in zip(diffs, covered)): continue
        active.append((v, M))
        for c, d in zip(covered, diffs): c |= d
        if len(active) > 12: return
    if any(c != set(D) for c, (_, _, _, D) in zip(covered, data)): return

    def fn(g, active=tuple(active)):
        bgc = bg_of(g); sd = _seeds(g, bgc)
        if not sd or len(sd) > 10 or any(len(C) > 9 for C, _, _ in sd): return None
        return _motif_paint(g, sd, active)
    yield (f"repeat:motif[{';'.join('%d,%d' % v for v, _ in active)}]", 5, fn)


FAMILIES = (fam_fragment, fam_toward, fam_self, fam_stub, fam_legend, fam_motif)
