"""summarise.panel_to_pixel: the grid is partitioned into panels; the output has one pixel per panel.

One parametrised primitive  out[i][j] = reduce(P[i][j])  followed by an optional layout post-step.
All parameters are induced from the training pairs (programs are pre-checked on every pair):
  partition : sep      - full uniform lines of one colour s split the grid into bands
                         (options: strip = peel uniform border layers first,
                                   seps  = separator runs are themselves output bands)
              lattice  - like sep, but the lines may carry marks (a line is a separator when it holds
                         no panel-background cell and is mostly s); panels know their 4 lattice corners
              blocks   - R x C equal blocks, (R,C) = constant output shape or input/k;
                         optional pre-crop to the bbox of the largest object
              layout   - solid rectangles (large, dense components) clustered into rows/columns
  reduce    : major | major_ex (majority ignoring bg and s) | second[fill] (most frequent colour other
              than the panel majority; fill = panel majority or global bg when absent) |
              uniform (active only when the panel is one colour) |
              corners (active when all 4 lattice corners are marked; colour when they agree, else bg) |
              table:<feature> (count feature -> colour, learnt from the pairs; threshold for unseen)
  post      : plain | crop (bbox of active panels) | frame (1-cell ring of s / bg around the result)
"""
import sys
sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox, crop, fit_cmap, apply_cmap


# ------------------------------------------------------------------ partitions
# A partition is (matrix of panels, s) where a panel is dict(cells=[values], corners=[values|None]).

def _runs(idx_is_sep, n, with_seps):
    bands, cur, kind = [], [], None
    for i in range(n):
        k = idx_is_sep[i]
        if cur and k != kind:
            bands.append((kind, cur)); cur = []
        cur.append(i); kind = k
    if cur: bands.append((kind, cur))
    return [b for k, b in bands if with_seps or not k]


def _strip(g):
    r0, r1, c0, c1 = 0, H(g) - 1, 0, W(g) - 1
    changed = True
    while changed and r1 - r0 >= 2 and c1 - c0 >= 2:
        changed = False
        for side in range(4):
            if side == 0: vals = g[r0][c0:c1 + 1]
            elif side == 1: vals = g[r1][c0:c1 + 1]
            elif side == 2: vals = [g[r][c0] for r in range(r0, r1 + 1)]
            else: vals = [g[r][c1] for r in range(r0, r1 + 1)]
            if len(set(vals)) == 1:
                if side == 0: r0 += 1
                elif side == 1: r1 -= 1
                elif side == 2: c0 += 1
                else: c1 -= 1
                changed = True
                break
    if (r0, c0) == (0, 0) and (r1, c1) == (H(g) - 1, W(g) - 1): return None
    return crop(g, (r0, c0, r1, c1))


def _matrix(g, rb, cb, rsep, csep):
    h, w = H(g), W(g)
    M = []
    for rows in rb:
        line = []
        for cols in cb:
            cells = [g[r][c] for r in rows for c in cols]
            ys = (rows[0] - 1, rows[-1] + 1); xs = (cols[0] - 1, cols[-1] + 1)
            corners = [g[y][x] if 0 <= y < h and 0 <= x < w and rsep[y] and csep[x] else None
                       for y in ys for x in xs]
            line.append({"cells": cells, "corners": corners})
        M.append(line)
    return M


def part_sep(g, strip, with_seps, loose):
    gb0 = bg_of(g)
    if strip:
        g = _strip(g)
        if g is None: return None
    h, w = H(g), W(g)
    if h < 3 or w < 3: return None
    uni = Counter()
    for r in range(h):
        if len(set(g[r])) == 1: uni[g[r][0]] += 1
    for c in range(w):
        col = {g[r][c] for r in range(h)}
        if len(col) == 1: uni[g[0][c]] += 1
    if len(uni) != 1: return None
    s = next(iter(uni))
    if loose:
        rest = Counter(v for row in g for v in row if v != s)
        if not rest: return None
        pb = rest.most_common(1)[0][0]
        rsep = [pb not in g[r] and 2 * g[r].count(s) >= w for r in range(h)]
        colv = [[g[r][c] for r in range(h)] for c in range(w)]
        csep = [pb not in colv[c] and 2 * colv[c].count(s) >= h for c in range(w)]
    else:
        rsep = [len(set(g[r])) == 1 and g[r][0] == s for r in range(h)]
        csep = [all(g[r][c] == s for r in range(h)) for c in range(w)]
    if all(rsep) or all(csep): return None
    rb = _runs(rsep, h, with_seps); cb = _runs(csep, w, with_seps)
    if len(rb) * len(cb) < 2: return None
    return _matrix(g, rb, cb, rsep, csep), s, gb0


def part_blocks(g, R, C, precrop):
    gb = bg_of(g)
    if precrop:
        gb = g[0][0]
        if any(g[0][0] != v for v in (g[0][-1], g[-1][0], g[-1][-1])): return None
        cells = [(r, c) for r in range(H(g)) for c in range(W(g)) if g[r][c] != gb]
        if not cells: return None
        g = crop(g, bbox(cells))
    h, w = H(g), W(g)
    if R * C < 2 or h < 2 * R or w < 2 * C: return None   # >=2 blocks, each at least 2x2
    rb = [list(range(i * h // R, (i + 1) * h // R)) for i in range(R)]
    cb = [list(range(j * w // C, (j + 1) * w // C)) for j in range(C)]
    return _matrix(g, rb, cb, [False] * h, [False] * w), None, gb


def part_layout(g):
    bg = bg_of(g)
    objs = objects(g, bg, diag=False, by_colour=True)
    rects = []
    for o in objs:
        y0, x0, y1, x1 = bbox(o)
        if y1 - y0 < 1 or x1 - x0 < 1: continue
        if len(o) < 0.7 * (y1 - y0 + 1) * (x1 - x0 + 1): continue
        rects.append((len(o), y0, x0, y1, x1, g[o[0][0]][o[0][1]]))
    if len(rects) < 2: return None
    big = max(r[0] for r in rects)
    rects = [r for r in rects if r[0] >= 0.25 * big and r[0] >= 4]
    if len(rects) < 2: return None
    rects.sort(key=lambda r: r[1])
    rows = []
    for r in rects:
        if rows and r[1] <= max(q[3] for q in rows[-1]):
            rows[-1].append(r)
        else:
            rows.append([r])
    n = len(rows[0])
    if any(len(rw) != n for rw in rows): return None
    M = [[{"cells": [r[5]], "corners": [None] * 4} for r in sorted(rw, key=lambda q: q[2])] for rw in rows]
    return M, None, bg


# ------------------------------------------------------------------ reduces: panel -> (colour, active)

def _major(cells):
    return Counter(cells).most_common(1)[0][0]


def red_major(p, gb, s):
    return _major(p["cells"]), True


def red_major_ex(p, gb, s):
    cnt = Counter(v for v in p["cells"] if v != gb and v != s)
    return (cnt.most_common(1)[0][0] if cnt else gb), True


def _second(p, fill_gb, gb):
    cnt = Counter(p["cells"]).most_common()
    if len(cnt) >= 2:
        if len(cnt) >= 3 and cnt[1][1] == cnt[2][1]: return None, True
        return cnt[1][0], True
    return (gb if fill_gb else cnt[0][0]), True


def red_second_pb(p, gb, s): return _second(p, False, gb)
def red_second_gb(p, gb, s): return _second(p, True, gb)


def red_uniform(p, gb, s):
    st = set(p["cells"])
    return (next(iter(st)), True) if len(st) == 1 else (gb, False)


def red_corners(p, gb, s):
    cs = p["corners"]
    pb = _major(p["cells"])
    if any(c is None or c == s for c in cs): return pb, False
    return (cs[0] if len(set(cs)) == 1 else pb), True


REDUCES = {"major": red_major, "major_ex": red_major_ex, "second[fill=panel]": red_second_pb,
           "second[fill=bg]": red_second_gb, "uniform": red_uniform, "corners": red_corners}

FEATS = {"n_fg": lambda p, gb: sum(v != gb for v in p["cells"]),
         "n_minor": lambda p, gb: len(p["cells"]) - Counter(p["cells"]).most_common(1)[0][1],
         "n_colours": lambda p, gb: len(set(p["cells"]))}


# ------------------------------------------------------------------ post

def assemble(M, post, s, gb):
    """M: matrix of (colour, active). Returns output grid or None."""
    if post == "crop":
        act = [(i, j) for i, row in enumerate(M) for j, (c, a) in enumerate(row) if a]
        if not act: return None
        i0 = min(i for i, _ in act); i1 = max(i for i, _ in act)
        j0 = min(j for _, j in act); j1 = max(j for _, j in act)
        M = [row[j0:j1 + 1] for row in M[i0:i1 + 1]]
    out = [[c for c, a in row] for row in M]
    if any(c is None for row in out for c in row): return None
    if post == "frame":
        f = s if s is not None else gb
        w = len(out[0]) + 2
        out = [[f] * w] + [[f] + row + [f] for row in out] + [[f] * w]
    return out


# ------------------------------------------------------------------ family

def _partitioners(train):
    P = []
    for strip in (False, True):
        for ws in (False, True):
            P.append((f"sep[strip={int(strip)},seps={int(ws)}]", 0 + strip + ws,
                      lambda g, a=strip, b=ws: part_sep(g, a, b, False)))
    P.append(("lattice", 1, lambda g: part_sep(g, False, False, True)))
    shapes = {(H(p["output"]), W(p["output"])) for p in train}
    ks = set()
    for pc in (False, True):
        if len(shapes) == 1:
            R, C = next(iter(shapes))
            P.append((f"blocks[{R}x{C},crop={int(pc)}]", 1 + pc, lambda g, R=R, C=C, pc=pc: part_blocks(g, R, C, pc)))
    kk = {(H(p["input"]) / H(p["output"]), W(p["input"]) / W(p["output"])) for p in train}
    if len(kk) == 1:
        a, b = next(iter(kk))
        if a == int(a) and b == int(b) and a * b > 1:
            a, b = int(a), int(b)
            P.append((f"blocks[/{a}x{b}]", 1, lambda g, a=a, b=b: part_blocks(g, H(g) // a, W(g) // b, False)
                      if H(g) % a == 0 and W(g) % b == 0 else None))
    P.append(("layout", 2, part_layout))
    return P


def _fits(preds, outs):
    if any(p is None or H(p) != H(o) or W(p) != W(o) for p, o in zip(preds, outs)): return False
    if preds == outs: return True
    m = fit_cmap(preds, outs)
    return bool(m) and all(apply_cmap(a, m) == b for a, b in zip(preds, outs))


def _table_fn(table):
    keys = sorted(table)
    vals = [table[k] for k in keys]
    thr = None
    if len(set(vals)) == 2:
        cut = [i for i in range(1, len(vals)) if vals[i] != vals[i - 1]]
        if len(cut) == 1: thr = (keys[cut[0] - 1], keys[cut[0]], vals[0], vals[-1])

    def f(v):
        if v in table: return table[v]
        if thr: return thr[2] if v <= thr[0] else thr[3] if v >= thr[1] else None
        return None
    return f


def fam_panel_to_pixel(train):
    """Exact fits shadow fits that need the harness colour map (those extrapolate worse)."""
    outs = [p["output"] for p in train]
    progs = list(_programs(train))
    exact = [x for x in progs if [x[2](p["input"]) for p in train] == outs]
    for x in (exact or progs)[:40]:
        yield x


def _programs(train):
    outs = [p["output"] for p in train]
    ins = [p["input"] for p in train]
    if any(H(o) * W(o) >= H(i) * W(i) for i, o in zip(ins, outs)): return
    if max(H(o) * W(o) for o in outs) > 100: return
    n = 0
    for pname, pcost, part in _partitioners(train):
        parts = []
        for g in ins:
            r = part(g)
            if r is None: break
            parts.append(r)
        if len(parts) != len(ins): continue
        for post in ("plain", "crop", "frame"):
            # quick shape pre-check for plain/frame
            if post != "crop":
                d = 2 if post == "frame" else 0
                if any((len(M) + d, len(M[0]) + d) != (H(o), W(o)) for (M, s, gb), o in zip(parts, outs)): continue
            for rname, red in REDUCES.items():
                if post == "crop" and rname not in ("uniform", "corners"): continue
                if rname == "corners" and not pname.startswith("lattice"): continue
                preds = [assemble([[red(p, gb, s) for p in row] for row in M], post, s, gb)
                         for M, s, gb in parts]
                if not _fits(preds, outs): continue

                def fn(g, part=part, red=red, post=post):
                    r = part(g)
                    if r is None: return None
                    M, s, gb = r
                    return assemble([[red(p, gb, s) for p in row] for row in M], post, s, gb)
                n += 1
                yield (f"panel2px:{pname}:{rname}:{post}", min(6, 3 + pcost + (post != 'plain')), fn)
            if post == "crop": continue
            d = 1 if post == "frame" else 0
            for fname, feat in (FEATS.items() if pname.startswith(("sep", "lattice")) else ()):
                table = {}; ok = True
                for (M, s, gb), o in zip(parts, outs):
                    for i, row in enumerate(M):
                        for j, p in enumerate(row):
                            v = feat(p, gb); c = o[i + d][j + d]
                            if table.setdefault(v, c) != c: ok = False; break
                        if not ok: break
                    if not ok: break
                if not ok or len(set(table.values())) < 2: continue
                tf = _table_fn(table)
                if post == "frame":
                    f0 = {o[0][0] for o in outs}
                    if len(f0) != 1: continue
                    fc = f0.pop()
                    if any(set(o[0]) != {fc} or set(o[-1]) != {fc} or {r[0] for r in o} != {fc} or {r[-1] for r in o} != {fc}
                           for o in outs): continue
                else:
                    fc = None

                def fn(g, part=part, feat=feat, tf=tf, post=post, fc=fc):
                    r = part(g)
                    if r is None: return None
                    M, s, gb = r
                    out = [[tf(feat(p, gb)) for p in row] for row in M]
                    if any(c is None for row in out for c in row): return None
                    if post == "frame":
                        w = len(out[0]) + 2
                        out = [[fc] * w] + [[fc] + row + [fc] for row in out] + [[fc] * w]
                    return out
                if not _fits([fn(g) for g in ins], outs): continue
                n += 1
                yield (f"panel2px:{pname}:table[{fname}]:{post}", min(6, 4 + pcost + (post != 'plain')), fn)


FAMILIES = (fam_panel_to_pixel,)
