"""transform.dihedral + transform.reflect_object: dihedral ops applied to a SOURCE that is not the whole grid.

transform.dihedral   out = D(source)
  source : framed picture crop | largest-object crop | lattice summary (cut lines / separator panels)
           | each object about its own centre (in place) | object positions only (motifs keep orientation)
  D      : constant (the harness composes crop:/downscale: programs with every D8 element)
           | chosen per grid so that marker colours inside the crop take the layout of the outside markers
           | analogy: D (and colour relabelling) mapping block A to block B, applied to block C, per lattice row

transform.reflect_object   copy = reflect(obj, axis); optionally erase obj; paint obj colour or marker colour
  axis   : line through (template cell, marker cell) pair  (marker = singleton of another colour)
           | spine of nearest anchor object (row / col / diagonal line with most anchor cells)
           | centre of the fully-symmetric anchor object (H, V and HV copies)
           | own bbox edge on side d, d = constant or read from an indicator object's shape by rotation /
             D8 equivariance with the training examples
All colours / roles are induced from the training pairs; every program is verified by the harness.
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from itertools import product
from gdsl import H, W, bg_of, objects, bbox, crop, D8, split_panels, static_colours

ROT4 = ("id", "r90", "r180", "r270")
DIR4 = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}


def same_shape(train):
    return all((H(p["input"]), W(p["input"])) == (H(p["output"]), W(p["output"])) for p in train)


def comps(g, bg, conn):
    """conn: c4 / c8 single colour, m4 / m8 multicolour."""
    return objects(g, bg, diag=conn[1] == "8", by_colour=conn[0] == "c")


def mask_of(cells):
    r0, c0, r1, c1 = bbox(cells)
    m = [[0] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for y, x in cells: m[y - r0][x - c0] = 1
    return m


def dir_under(d, D):
    """Image of a direction vector under grid transform D (applied to a 3x3 probe)."""
    p = [[0] * 3 for _ in range(3)]; p[1 + d[0]][1 + d[1]] = 1
    q = D8[D](p)
    for y in range(3):
        for x in range(3):
            if q[y][x]: return (y - 1, x - 1)


# ============================================================ transform.dihedral

def framed_picture(g, sides=None):
    """Largest multicolour component's bbox, peeling edge lines that are one colour absent from the rest."""
    bg = bg_of(g); h, w = H(g), W(g)
    obs = [ob for ob in comps(g, bg, "m8") if not any(y in (0, h - 1) or x in (0, w - 1) for y, x in ob)]
    if not obs: return None
    r0, c0, r1, c1 = bbox(max(obs, key=len)); peeled = 0
    while r1 - r0 >= 1 and c1 - c0 >= 1:
        done = False
        for side in "TBLR":
            if side == "T": line = [g[r0][x] for x in range(c0, c1 + 1)]; rest = (r0 + 1, c0, r1, c1)
            elif side == "B": line = [g[r1][x] for x in range(c0, c1 + 1)]; rest = (r0, c0, r1 - 1, c1)
            elif side == "L": line = [g[y][c0] for y in range(r0, r1 + 1)]; rest = (r0, c0 + 1, r1, c1)
            else: line = [g[y][c1] for y in range(r0, r1 + 1)]; rest = (r0, c0, r1, c1 - 1)
            cs = {v for v in line if v != bg}
            if len(cs) != 1 or sum(v != bg for v in line) * 2 < len(line): continue
            c = cs.pop()
            if any(g[y][x] == c for y in range(rest[0], rest[2] + 1) for x in range(rest[1], rest[3] + 1)): continue
            r0, c0, r1, c1 = rest; peeled += 1; done = True
            if sides is not None: sides[side] = c
            break
        if not done: break
    return crop(g, (r0, c0, r1, c1)) if peeled else None


SIDE_DIR = {"T": (-1, 0), "B": (1, 0), "L": (0, -1), "R": (0, 1)}


def framed_oriented(g):
    """Framed picture turned so that each frame line's colour lands on the grid side bordered by that colour."""
    sides = {}; pic = framed_picture(g, sides)
    if pic is None or not sides: return None
    h, w = H(g), W(g); bg = bg_of(g)
    edge = {"T": g[0], "B": g[h - 1], "L": [r[0] for r in g], "R": [r[w - 1] for r in g]}
    ecol = {}
    for s, line in edge.items():
        cnt = Counter(v for v in line if v != bg)
        if cnt: ecol[s] = cnt.most_common(1)[0][0]
    inv = {v: k for k, v in SIDE_DIR.items()}; hits = []
    for D in D8:
        ok = True
        for s, c in sides.items():
            t = inv[dir_under(SIDE_DIR[s], D)]
            if ecol.get(t) != c or list(ecol.values()).count(c) != 1: ok = False; break
        if ok: hits.append(D)
    return D8[hits[0]](pic) if len(hits) == 1 else None


def fam_crop_framed(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) >= H(i) * W(i): return
    yield ("crop:framed-picture", 3, framed_picture)
    yield ("crop-oriented:framed-by-border-colour", 4, framed_oriented)


def layout_sig(pos):
    ks = sorted(pos)
    sg = lambda v: (v > 0) - (v < 0)
    return tuple((a, b, sg(pos[b][0] - pos[a][0]), sg(pos[b][1] - pos[a][1])) for a in ks for b in ks if a < b)


def crop_marker_oriented(g):
    """Crop the largest multicolour object; pick the D8 element under which the singleton colours inside
    the crop are laid out like the same colours' singletons outside it."""
    bg = bg_of(g); obs = comps(g, bg, "m8")
    if len(obs) < 3: return None
    big = max(obs, key=len); b = bbox(big)
    outside = Counter(); opos = {}
    for ob in obs:
        if ob is big: continue
        if len(ob) != 1: return None
        y, x = ob[0]; outside[g[y][x]] += 1; opos[g[y][x]] = (y, x)
    if len(opos) < 2 or any(v > 1 for v in outside.values()): return None
    pic = crop(g, b); want = layout_sig(opos); hits = []
    for k, f in D8.items():
        q = f(pic); pos = {}
        for c in opos:
            cells = [(y, x) for y in range(H(q)) for x in range(W(q)) if q[y][x] == c]
            if len(cells) != 1: return None
            pos[c] = cells[0]
        if layout_sig(pos) == want: hits.append(q)
    if not hits or any(h != hits[0] for h in hits): return None
    return hits[0]


def fam_crop_marker_oriented(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) >= H(i) * W(i): return
    yield ("crop-oriented:by-marker-layout", 4, crop_marker_oriented)


def cut_positions(g, bg, axis):
    """Lattice cuts: positions where >= 2 lines show a change between two non-bg colours."""
    h, w = H(g), W(g); cuts = []
    n = w if axis == "col" else h
    for k in range(1, n):
        cnt = 0
        for t in range(h if axis == "col" else w):
            a, b = (g[t][k - 1], g[t][k]) if axis == "col" else (g[k - 1][t], g[k][t])
            if a != bg and b != bg and a != b: cnt += 1
        if cnt >= 2: cuts.append(k)
    return cuts


def lattice_summary(g, mode):
    bg = bg_of(g)
    if mode == "panels":
        sp = split_panels(g)
        if not sp: return None
        panels, sc = sp
        h, w = H(g), W(g)
        nr = 1 + sum(1 for r in range(h) if all(v == sc for v in g[r]) and 0 < r < h - 1 and not all(v == sc for v in g[r - 1]))
        nc = len(panels) // nr if nr and len(panels) % nr == 0 else 0
        if not nc: return None
        cells = []
        for p in panels:
            cnt = Counter(v for r in p for v in r)
            top = cnt.most_common(2)
            if len(top) > 1 and top[0][1] == top[1][1]: return None
            cells.append(top[0][0])
        return [cells[r * nc:(r + 1) * nc] for r in range(nr)]
    fg = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg]
    if not fg: return None
    s = crop(g, bbox(fg))
    rc = [0] + cut_positions(s, bg, "row") + [H(s)]; cc = [0] + cut_positions(s, bg, "col") + [W(s)]
    if len(rc) * len(cc) > 100 or (len(rc) == 2 and len(cc) == 2): return None
    out = []
    for a in range(len(rc) - 1):
        row = []
        for b in range(len(cc) - 1):
            cnt = Counter(s[y][x] for y in range(rc[a], rc[a + 1]) for x in range(cc[b], cc[b + 1]) if s[y][x] != bg)
            if not cnt: return None
            row.append(cnt.most_common(1)[0][0])
        out.append(row)
    return out


def fam_lattice_summary(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) >= H(i) or W(o) >= W(i) or H(o) * W(o) > 64: return
    for mode in ("panels", "cuts"):
        yield (f"downscale:lattice-summary[{mode}]", 3, lambda g, mode=mode: lattice_summary(g, mode))


def place(out, cells_vals, h, w):
    for (y, x), v in cells_vals:
        if 0 <= y < h and 0 <= x < w: out[y][x] = v
        else: return False
    return True


def objects_dihedral_inplace(g, D, conn):
    """Every object is replaced by D(object) about its own bbox centre."""
    bg = bg_of(g); h, w = H(g), W(g); out = [[bg] * w for _ in range(h)]
    obs = comps(g, bg, conn)
    if len(obs) < 2: return None
    for ob in obs:
        r0, c0, r1, c1 = bbox(ob); hh, ww = r1 - r0 + 1, c1 - c0 + 1
        if 2 * hh * ww > h * w: return None
        sub = [[g[y][x] if (y, x) in set(ob) else None for x in range(c0, c1 + 1)] for y in range(r0, r1 + 1)]
        q = D8[D](sub); nh, nw = H(q), W(q)
        if (hh - nh) % 2 or (ww - nw) % 2: return None
        y0, x0 = r0 + (hh - nh) // 2, c0 + (ww - nw) // 2
        if not place(out, [((y0 + y, x0 + x), q[y][x]) for y in range(nh) for x in range(nw) if q[y][x] is not None], h, w):
            return None
    return out


def fam_objects_dihedral_inplace(train):
    if not same_shape(train): return
    for D, conn in product(("T", "aT", "r90", "r270", "fh", "fv", "r180"), ("c4", "c8", "m8")):
        yield (f"object-dihedral-inplace:{D}[{conn}]", 4, lambda g, D=D, conn=conn: objects_dihedral_inplace(g, D, conn))


def mirror_positions(g, D, conn):
    """Objects keep their content; only their placement is mirrored (fh / fv / r180 of the grid)."""
    bg = bg_of(g); h, w = H(g), W(g); out = [[bg] * w for _ in range(h)]
    obs = comps(g, bg, conn)
    if len(obs) < 2: return None
    for ob in obs:
        r0, c0, r1, c1 = bbox(ob)
        nr0 = h - 1 - r1 if D in ("fv", "r180") else r0
        nc0 = w - 1 - c1 if D in ("fh", "r180") else c0
        for y, x in ob: out[nr0 + y - r0][nc0 + x - c0] = g[y][x]
    return out


def fam_mirror_positions(train):
    if not same_shape(train): return
    for D, conn in product(("fh", "fv", "r180"), ("m4", "m8")):
        yield (f"mirror-positions:{D}[{conn}]", 4, lambda g, D=D, conn=conn: mirror_positions(g, D, conn))


# ============================================================ transform.reflect_object

def reflect_to_markers(g, diag, paint, keep_marker=True):
    """Templates = single-colour components (8-conn) of size >= 2; markers = singleton cells of another colour.
    Each marker is the mirror image of its nearest aligned template cell; the template is reflected with that
    mapping (row-aligned: horizontal flip, column-aligned: vertical flip, diagonal: point reflection)."""
    bg = bg_of(g); h, w = H(g), W(g)
    obs = comps(g, bg, "c8")
    temps = [ob for ob in obs if len(ob) >= 2]; marks = [ob[0] for ob in obs if len(ob) == 1]
    if not temps or not marks: return None
    out = [r[:] for r in g]; used = 0
    for my, mx in marks:
        mc = g[my][mx]; best = []
        for ti, ob in enumerate(temps):
            tc = g[ob[0][0]][ob[0][1]]
            if tc == mc: continue
            for ty, tx in ob:
                dy, dx = my - ty, mx - tx
                if dy == 0 and dx: kind = "h"
                elif dx == 0 and dy: kind = "v"
                elif diag and abs(dy) == abs(dx) and dy: kind = "p"
                else: continue
                best.append((max(abs(dy), abs(dx)), kind == "p", ti, kind, ty, tx))
        if not best: continue
        best.sort(); top = [b for b in best if b[:2] == best[0][:2]]
        maps = {(b[2], b[3], b[4] + my if b[3] != "h" else None, b[5] + mx if b[3] != "v" else None) for b in top}
        if len(maps) != 1: return None
        ti, kind, sy, sx = maps.pop(); ob = temps[ti]
        col = mc if paint == "marker" else g[ob[0][0]][ob[0][1]]
        for y, x in ob:
            ny = sy - y if kind in "vp" else y
            nx = sx - x if kind in "hp" else x
            if 0 <= ny < h and 0 <= nx < w and out[ny][nx] == bg: out[ny][nx] = col
        used += 1
    return out if used else None


def fam_reflect_to_markers(train):
    if not same_shape(train): return
    for diag, paint in product((False, True), ("marker", "template")):
        yield (f"reflect-object:to-marker[{'diag' if diag else 'orth'},{paint}]", 4,
               lambda g, diag=diag, paint=paint: reflect_to_markers(g, diag, paint))


def spine(ob):
    """Straight line (kind, k) containing the most cells of the object: row y=k, col x=k, diag y-x=k, anti y+x=k."""
    cnt = Counter()
    for y, x in ob:
        cnt[("row", y)] += 1; cnt[("col", x)] += 1; cnt[("diag", y - x)] += 1; cnt[("anti", y + x)] += 1
    (best, n), = cnt.most_common(1)
    if n < 3 or sum(1 for v in cnt.values() if v == n) > 1: return None
    return best


def refl(y, x, ax):
    kind, k = ax
    if kind == "row": return 2 * k - y, x
    if kind == "col": return y, 2 * k - x
    if kind == "diag": return x + k, y - k
    return k - x, k - y


def line_dist(y, x, ax):
    kind, k = ax
    return abs({"row": y, "col": x, "diag": y - x, "anti": y + x}[kind] - k)


def colour_select(g, bg, axis_c, how, st):
    cnt = Counter(v for r in g for v in r if v not in (bg, axis_c))
    if not cnt: return set()
    if how == "all": return set(cnt)
    if how == "nonstatic": return {c for c in cnt if c not in st}
    vals = sorted(cnt.values())
    if how == "least":
        return {c for c, n in cnt.items() if n == vals[0]} if vals.count(vals[0]) == 1 else set()
    return {c for c, n in cnt.items() if n == vals[-1]} if vals.count(vals[-1]) == 1 else set()


def reflect_across_anchor(g, axis_c, how, keep, conn, st):
    bg = bg_of(g); h, w = H(g), W(g)
    anchors = [ob for ob in comps(g, bg, "c8") if g[ob[0][0]][ob[0][1]] == axis_c]
    axes = [spine(ob) for ob in anchors]
    if not axes or any(a is None for a in axes): return None
    movc = colour_select(g, bg, axis_c, how, st)
    if not movc: return None
    movers = [ob for ob in comps(g, bg, conn) if all(g[y][x] in movc for y, x in ob)]
    if not movers: return None
    out = [r[:] for r in g]
    if not keep:
        for ob in movers:
            for y, x in ob: out[y][x] = bg
    for ob in movers:
        ds = sorted((min(line_dist(y, x, a) for y, x in ob), i) for i, a in enumerate(axes))
        if len(ds) > 1 and ds[0][0] == ds[1][0] and axes[ds[0][1]] != axes[ds[1][1]]: return None
        ax = axes[ds[0][1]]
        for y, x in ob:
            ny, nx = refl(y, x, ax)
            if not (0 <= ny < h and 0 <= nx < w): return None
            if out[ny][nx] in (bg, g[y][x]): out[ny][nx] = g[y][x]
            else: return None
    return out


def reflect_about_centre(g, conn):
    """The one object symmetric under both flips is the centre; every other object gets its H, V and HV copies."""
    bg = bg_of(g); h, w = H(g), W(g); obs = comps(g, bg, conn)
    def sym(ob):
        s = set(ob); r0, c0, r1, c1 = bbox(ob)
        return all((r0 + r1 - y, x) in s and (y, c0 + c1 - x) in s and g[r0 + r1 - y][x] == g[y][x] and g[y][c0 + c1 - x] == g[y][x] for y, x in ob)
    cen = [ob for ob in obs if sym(ob)]
    if len(cen) != 1 or len(obs) < 2: return None
    r0, c0, r1, c1 = bbox(cen[0]); sy, sx = r0 + r1, c0 + c1
    out = [r[:] for r in g]
    for ob in obs:
        if ob is cen[0]: continue
        for y, x in ob:
            for ny, nx in ((sy - y, x), (y, sx - x), (sy - y, sx - x)):
                if not (0 <= ny < h and 0 <= nx < w): return None
                out[ny][nx] = g[y][x]
    return out


def fam_reflect_across_anchor(train):
    if not same_shape(train): return
    st = static_colours(train)
    common = None
    for p in train:
        cs = {v for r in p["input"] for v in r} - {bg_of(p["input"])}
        common = cs if common is None else common & cs
    for conn in ("c8", "m8"):
        yield (f"reflect-object:about-centre-object[{conn}]", 4, lambda g, conn=conn: reflect_about_centre(g, conn))
    for axis_c in sorted((common or set()) & st):
        for how, keep, conn in product(("nonstatic", "least", "most", "all"), (True, False), ("c8", "m8")):
            if how == "nonstatic" and keep: continue
            yield (f"reflect-object:across-anchor-spine[c{axis_c},{how},{'keep' if keep else 'move'},{conn}]", 4,
                   lambda g, a=axis_c, how=how, keep=keep, conn=conn: reflect_across_anchor(g, a, how, keep, conn, st))


def reflect_edge(g, ob, d, bg, out):
    r0, c0, r1, c1 = bbox(ob); h, w = H(g), W(g)
    for y, x in ob:
        if d == "N": ny, nx = 2 * r0 - 1 - y, x
        elif d == "S": ny, nx = 2 * r1 + 1 - y, x
        elif d == "W": ny, nx = y, 2 * c0 - 1 - x
        else: ny, nx = y, 2 * c1 + 1 - x
        if not (0 <= ny < h and 0 <= nx < w): return False
        out[ny][nx] = g[y][x]
    return True


def split_roles(g, bg, mc):
    mov = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == mc]
    ind = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] not in (bg, mc)]
    return mov, ind


def fam_reflect_own_edge(train):
    """One object of an induced colour is mirrored across its own bbox edge on side d; d is constant or is read
    from the shape of the other (indicator) object, equivariantly (rotations or all of D8) with the training pairs."""
    if not same_shape(train): return
    gain = None
    for p in train:
        i, o = p["input"], p["output"]; bg = bg_of(i)
        g_ = {o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] == bg and o[y][x] != bg}
        gain = g_ if gain is None else gain & g_
    if not gain or len(gain) != 1: return
    mc = gain.pop()
    lib = []; erase = None
    for p in train:
        i, o = p["input"], p["output"]; bg = bg_of(i)
        mov, ind = split_roles(i, bg, mc)
        if not mov or not ind: return
        er = all(o[y][x] != i[y][x] for y, x in ind)
        erase = er if erase is None else (erase if erase == er else None)
        if erase is None: return
        hit = []
        for d in DIR4:
            out = [r[:] for r in i]
            if erase:
                for y, x in ind: out[y][x] = bg
            if reflect_edge(i, mov, d, bg, out) and out == o: hit.append(d)
        if len(hit) != 1: return
        lib.append((mask_of(ind), DIR4[hit[0]]))
    inv = {v: k for k, v in DIR4.items()}

    def fn(g, mode):
        bg = bg_of(g); mov, ind = split_roles(g, bg, mc)
        if not mov or not ind: return None
        if mode == "const":
            ds = {d for _, d in lib}
        else:
            S = mask_of(ind); ds = set()
            for m, d in lib:
                for D in (ROT4 if mode == "rot" else D8):
                    if D8[D](m) == S: ds.add(dir_under(d, D))
        if len(ds) != 1: return None
        out = [r[:] for r in g]
        if erase:
            for y, x in ind: out[y][x] = bg
        return out if reflect_edge(g, mov, inv[ds.pop()], bg, out) else None
    for mode in ("const", "rot", "d8"):
        yield (f"reflect-object:own-edge[c{mc},{mode}{',erase' if erase else ''}]", 4, lambda g, mode=mode: fn(g, mode))


def bg_runs(n, is_sep):
    runs, cur = [], None
    for k in range(n):
        if is_sep(k):
            if cur is not None: runs.append(cur); cur = None
        else:
            cur = [k, k] if cur is None else [cur[0], k]
    if cur is not None: runs.append(cur)
    return runs


def analogy_map(A, B, C):
    """A : B :: C : ?  with ? = cmap(D(C)); (D, cmap) is the simplest pair (fewest recolourings, then D8 order)
    mapping A exactly onto B; None when C holds a colour the map does not know."""
    best = None
    for rank, k in enumerate(("id", "fh", "fv", "T", "aT", "r180", "r90", "r270")):
        f = D8[k]; q = f(A)
        if (H(q), W(q)) != (H(B), W(B)): continue
        m = {}; ok = True
        for ra, rb in zip(q, B):
            for a, b in zip(ra, rb):
                if m.setdefault(a, b) != b: ok = False
        if not ok: continue
        key = (sum(a != b for a, b in m.items()), rank)
        if best is None or key < best[0]: best = (key, f, m)
    if best is None: return None
    _, f, m = best; r = f(C)
    if best[0][0] and any(v not in m for row in r for v in row): return None
    return [[m.get(v, v) for v in row] for row in r]


def lattice_analogy(g, orient):
    """Blocks separated by background lines; each lattice row (or column) holds A, B, C; the output keeps the
    separator layout and replaces each row (column) by the analogy answer for C."""
    if orient == "col": g = [list(r) for r in zip(*g)]
    bg = bg_of(g); h, w = H(g), W(g)
    rr = bg_runs(h, lambda y: all(v == bg for v in g[y])); cr = bg_runs(w, lambda x: all(g[y][x] == bg for y in range(h)))
    if len(cr) != 3 or len(rr) < 1: return None
    out = []; prev = -1
    for a, b in rr:
        out += [None] * (a - prev - 1)
        A, B, C = (crop(g, (a, c0, b, c1)) for c0, c1 in cr)
        r = analogy_map(A, B, C)
        if r is None or H(r) != b - a + 1: return None
        out += r; prev = b
    out += [None] * (h - 1 - prev)
    wd = max(len(r) for r in out if r is not None)
    if any(r is not None and len(r) != wd for r in out): return None
    out = [r if r is not None else [bg] * wd for r in out]
    return [list(r) for r in zip(*out)] if orient == "col" else out


def fam_lattice_analogy(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) >= H(i) * W(i): return
    for orient in ("row", "col"):
        yield (f"lattice-analogy:{orient}", 4, lambda g, orient=orient: lattice_analogy(g, orient))


def slide_mirror_into_anchor(g, mc, ac):
    """The mover (colour mc) slides straight toward the anchor (colour ac) until they touch; the anchor is
    replaced by the mover's mirror image across the contact edge, painted in the anchor colour."""
    bg = bg_of(g); h, w = H(g), W(g)
    mov = [(y, x) for y in range(h) for x in range(w) if g[y][x] == mc]
    anc = [(y, x) for y in range(h) for x in range(w) if g[y][x] == ac]
    if not mov or not anc: return None
    m0, n0, m1, n1 = bbox(mov); a0, b0, a1, b1 = bbox(anc)
    if n0 <= b1 and b0 <= n1 and not (m0 <= a1 and a0 <= m1):
        d = "S" if a0 > m1 else "N"; k = (a0 - m1 - 1) if d == "S" else (m0 - a1 - 1); dy, dx = (k, 0) if d == "S" else (-k, 0)
    elif m0 <= a1 and a0 <= m1 and not (n0 <= b1 and b0 <= n1):
        d = "E" if b0 > n1 else "W"; k = (b0 - n1 - 1) if d == "E" else (n0 - b1 - 1); dy, dx = (0, k) if d == "E" else (0, -k)
    else:
        return None
    out = [r[:] for r in g]
    for y, x in mov + anc: out[y][x] = bg
    moved = [(y + dy, x + dx) for y, x in mov]
    for y, x in moved: out[y][x] = mc
    ok = reflect_edge([[mc if (y, x) in set(moved) else bg for x in range(w)] for y in range(h)], moved, d, bg, out)
    if not ok: return None
    for y in range(h):
        for x in range(w):
            if out[y][x] == mc and (y, x) not in set(moved): out[y][x] = ac
    return out


def fam_slide_mirror_into_anchor(train):
    if not same_shape(train): return
    cs = None
    for p in train:
        c = {v for r in p["input"] for v in r} - {bg_of(p["input"])}
        cs = c if cs is None else cs & c
    if not cs or len(cs) != 2: return
    for mc in cs:
        ac = (cs - {mc}).pop()
        yield (f"reflect-object:slide-mirror-into-anchor[c{mc}->c{ac}]", 5,
               lambda g, mc=mc, ac=ac: slide_mirror_into_anchor(g, mc, ac))


def orient_to_marker(g, head, mk):
    """Every straight run (row or column segment of >= 2 non-background, non-marker cells containing colour
    `head`) that shares its line with a marker (colour mk) is reversed in place if that brings its head cells
    closer to the marker."""
    bg = bg_of(g); h, w = H(g), W(g)
    out = [r[:] for r in g]; touched = set(); acted = 0
    for axis in ("row", "col"):
        for k in range(h if axis == "row" else w):
            line = [(k, x) for x in range(w)] if axis == "row" else [(y, k) for y in range(h)]
            vals = [g[y][x] for y, x in line]
            marks = [t for t, v in enumerate(vals) if v == mk]
            if not marks: continue
            t = 0
            while t < len(vals):
                if vals[t] in (bg, mk): t += 1; continue
                u = t
                while u + 1 < len(vals) and vals[u + 1] not in (bg, mk): u += 1
                seg = vals[t:u + 1]
                if len(seg) >= 2 and head in seg:
                    rev = seg[::-1]
                    d0 = min(abs(t + j - m) for j, v in enumerate(seg) if v == head for m in marks)
                    d1 = min(abs(t + j - m) for j, v in enumerate(rev) if v == head for m in marks)
                    if d1 < d0:
                        for j, v in enumerate(rev):
                            y, x = line[t + j]
                            if (y, x) in touched: return None
                            out[y][x] = v
                        acted += 1
                    for j in range(len(seg)): touched.add(line[t + j])
                u += 1; t = u
    return out if acted else None


def fam_orient_to_marker(train):
    if not same_shape(train): return
    i, o = train[0]["input"], train[0]["output"]; bg = bg_of(i)
    diff = {i[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]}
    if not diff or bg in diff or len(diff) > 3: return
    cs = {v for r in i for v in r} - {bg}
    for head, mk in product(sorted(diff), sorted(cs - diff)):
        yield (f"reflect-object:orient-to-marker[head=c{head},marker=c{mk}]", 5,
               lambda g, head=head, mk=mk: orient_to_marker(g, head, mk))


FAMILIES = (fam_crop_framed, fam_crop_marker_oriented, fam_lattice_summary, fam_objects_dihedral_inplace,
            fam_mirror_positions, fam_reflect_to_markers, fam_reflect_across_anchor, fam_reflect_own_edge,
            fam_lattice_analogy, fam_slide_mirror_into_anchor, fam_orient_to_marker)
