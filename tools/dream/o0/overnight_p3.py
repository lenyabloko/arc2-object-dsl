"""OVERNIGHT-FABLE packet 3 (and the two packet-2 revisions): Fable's cell definitions
(claude/fable_cells_overnight_3.md) read literally (G83). Training pairs here; one harness check per task via
overnight_check.harness_once_fn (G87)."""
from collections import Counter
from overnight_p1 import bgc, comps, bbox, N4

FUN = {}


# ---------------------------------------------------------------- 332202d5 (revision: tie rule)
def f_332202d5(g):
    H, W = len(g), len(g[0]); bg = bgc(g)
    vcols = [x for x in range(W) if all(g[y][x] != bg for y in range(H))]
    hrows = [y for y in range(H) if all(g[y][x] != bg for x in range(W))]
    if len(vcols) != 1 or not hrows: return None
    vx = vcols[0]
    vcol = Counter(g[y][vx] for y in range(H) if y not in hrows).most_common(1)[0][0]
    cross = {g[y][vx] for y in hrows}
    if len(cross) != 1: return None
    cc = next(iter(cross))
    hcol = {y: Counter(g[y][x] for x in range(W) if x != vx).most_common(1)[0][0] for y in hrows}
    o = [list(r) for r in g]
    for y in range(H):                                            # step 1: background takes the nearest line's colour
        if y in hrows: continue
        d = sorted((abs(y - r), r) for r in hrows)
        if len(d) > 1 and d[0][0] == d[1][0]:                     # equidistant: crossing colour, unless both lines
            a, b = hcol[d[0][1]], hcol[d[1][1]]                   # have the same colour -> that colour (revision)
            col = a if a == b else cc
        else: col = hcol[d[0][1]]
        for x in range(W):
            if g[y][x] == bg: o[y][x] = col
    for y in range(H):                                            # step 2: original line cells swap by the key
        for x in range(W):
            v = g[y][x]
            if y in hrows and x != vx and v == hcol[y]: o[y][x] = cc
            elif x == vx and y not in hrows and v == vcol: o[y][x] = cc
            elif x == vx and y in hrows and v == cc: o[y][x] = vcol
    return o


FUN['332202d5'] = f_332202d5


# ---------------------------------------------------------------- 89565ca0 (revision: what counts as a line)
def f_89565ca0(g):
    H, W = len(g), len(g[0]); bg = 0
    cols = Counter(v for r in g for v in r if v != bg)

    def single_frac(c):
        cs = [(y, x) for y in range(H) for x in range(W) if g[y][x] == c]
        iso = sum(all(not (0 <= y + dy < H and 0 <= x + dx < W and g[y + dy][x + dx] == c) for dy, dx in N4) for y, x in cs)
        return iso / len(cs)
    noise = max(cols, key=single_frac)
    rows = []
    for c in sorted(cols):
        if c == noise: continue
        S = {(y, x) for y in range(H) for x in range(W) if g[y][x] == c}
        wall = set(S)
        # a line of colour c: a maximal straight run between two c cells in which no cell is background
        lines_ = [[(y, x) for x in range(W)] for y in range(H)] + [[(y, x) for y in range(H)] for x in range(W)]
        for L in lines_:
            i = 0
            while i < len(L):
                if g[L[i][0]][L[i][1]] == bg: i += 1; continue
                j = i
                while j < len(L) and g[L[j][0]][L[j][1]] != bg: j += 1   # [i, j) is a non-background run
                ks = [k for k in range(i, j) if L[k] in S]
                if len(ks) >= 2:
                    for k in range(ks[0], ks[-1] + 1): wall.add(L[k])
                i = j
        seen = set(); rooms = 0
        for y in range(H):
            for x in range(W):
                if (y, x) in wall or (y, x) in seen: continue
                st = [(y, x)]; seen.add((y, x)); border = False
                while st:
                    p = st.pop()
                    if p[0] in (0, H - 1) or p[1] in (0, W - 1): border = True
                    for dy, dx in N4:
                        q = (p[0] + dy, p[1] + dx)
                        if 0 <= q[0] < H and 0 <= q[1] < W and q not in wall and q not in seen: seen.add(q); st.append(q)
                if not border: rooms += 1
        if rooms == 0: return None
        rows.append((rooms, min(x for _, x in S), c))
    if not rows: return None
    rows.sort()                                                    # room count ascending; leftmost first on a tie
    width = max(r for r, _, _ in rows)
    return [[c] * r + [noise] * (width - r) for r, _, c in rows]


FUN['89565ca0'] = f_89565ca0


# ---------------------------------------------------------------- 6e453dd6
def f_6e453dd6(g):
    H, W = len(g), len(g[0]); bg = bgc(g)
    lc = [x for x in range(W) if len({g[y][x] for y in range(H)}) == 1 and g[0][x] != bg]   # the full-height line
    if len(lc) != 1: return None
    lx = lc[0]; line_col = g[0][lx]
    shape_cols = {v for r in g for v in r} - {bg, line_col}
    if len(shape_cols) != 1: return None
    sc = next(iter(shape_cols))
    o = [[(line_col if x == lx else bg) for x in range(W)] for y in range(H)]
    moved = []
    for c, cells in comps([[v if v == sc else -1 for v in r] for r in g], -1, conn8=True):   # black shapes
        y0, x0, y1, x1 = bbox(cells)
        if x1 < lx: d = (lx - 1) - x1                              # slide right until it touches the line
        elif x0 > lx: d = (lx + 1) - x0                            # slide left until it touches the line
        else: return None
        moved.append([(y, x + d) for y, x in cells])
    for cells in moved:
        for y, x in cells: o[y][x] = sc
    red_rows = set()
    for cells in moved:                                            # enclosed hole: background not reachable from the
        S = set(cells)                                             # grid border without crossing this shape
        seen = set(); st = [(y, x) for y in range(H) for x in range(W) if (y in (0, H - 1) or x in (0, W - 1)) and (y, x) not in S]
        seen.update(st)
        while st:
            p = st.pop()
            for dy, dx in N4:
                q = (p[0] + dy, p[1] + dx)
                if 0 <= q[0] < H and 0 <= q[1] < W and q not in S and q not in seen: seen.add(q); st.append(q)
        y0, x0, y1, x1 = bbox(cells)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (y, x) not in S and (y, x) not in seen and o[y][x] == bg: red_rows.add(y)
    side = range(lx + 1, W) if all(x < lx for cells in moved for _, x in cells) else None
    if side is None: return None                                   # "right of the line": shapes must be on the left
    for y in red_rows:
        for x in side: o[y][x] = 2
    return o


FUN['6e453dd6'] = f_6e453dd6


# ---------------------------------------------------------------- 782b5218
def _comps4(H, W, free):
    """4-connected components of the cells for which free(y, x) holds"""
    seen = set(); out = []
    for y in range(H):
        for x in range(W):
            if not free(y, x) or (y, x) in seen: continue
            st = [(y, x)]; seen.add((y, x)); cs = []
            while st:
                p = st.pop(); cs.append(p)
                for dy, dx in N4:
                    q = (p[0] + dy, p[1] + dx)
                    if 0 <= q[0] < H and 0 <= q[1] < W and free(*q) and q not in seen: seen.add(q); st.append(q)
            out.append(set(cs))
    return out


def f_782b5218(g, red=2, bg=0):
    H, W = len(g), len(g[0])
    B = {(y, x) for y in range(H) for x in range(W) if g[y][x] == red}           # boundary: the red cells
    if not B: return None
    others = {v for r in g for v in r} - {red, bg}
    if len(others) != 1: return None
    noise = next(iter(others))
    sides = _comps4(H, W, lambda y, x: (y, x) not in B)
    if len(sides) != 2: return None                                              # WHY: the curve splits the grid in two
    low = [s for s in sides if (H - 1, 0) in s]
    if not low: return None                                                      # the bottom-left corner is on the curve
    o = [[bg] * W for _ in range(H)]
    for y, x in B: o[y][x] = red
    for y, x in low[0]: o[y][x] = noise
    return o


FUN['782b5218'] = f_782b5218


# ---------------------------------------------------------------- 3a25b0d8
def _enclosed(H, W, S):
    """cells not in S that cannot reach the grid border through cells not in S (4-connected)"""
    seen = {(y, x) for y in range(H) for x in range(W) if (y in (0, H - 1) or x in (0, W - 1)) and (y, x) not in S}
    st = list(seen)
    while st:
        p = st.pop()
        for dy, dx in N4:
            q = (p[0] + dy, p[1] + dx)
            if 0 <= q[0] < H and 0 <= q[1] < W and q not in S and q not in seen: seen.add(q); st.append(q)
    return {(y, x) for y in range(H) for x in range(W) if (y, x) not in S and (y, x) not in seen}


def _band_groups(regions):
    """regions (sets of cells) grouped so that regions sharing rows form one group; groups ordered top to bottom"""
    rs = sorted(regions, key=lambda r: (min(y for y, _ in r), min(x for _, x in r)))
    groups = []
    for r in rs:
        ys = {y for y, _ in r}
        hit = [G for G in groups if ys & {y for R in G for y, _ in R}]
        for G in hit: groups.remove(G)
        groups.append(sum(hit, []) + [r])
    return sorted(groups, key=lambda G: min(y for R in G for y, _ in R))


def f_3a25b0d8(g):
    H, W = len(g), len(g[0]); bg = bgc(g)
    objs = [set(cells) for _, cells in comps(g, bg, conn8=True, by_colour=False)]
    objs = [o for o in objs if len(o) > 1]
    if len(objs) != 2: return None
    outline = {Counter(g[y][x] for y, x in o).most_common(1)[0][0] for o in objs}
    if len(outline) != 1: return None                                            # same outline colour
    oc = next(iter(outline))
    has_colour = [any(g[y][x] != oc for y, x in o) for o in objs]
    if sorted(has_colour) != [False, True]: return None
    mask = objs[has_colour.index(False)]; col = objs[has_colour.index(True)]
    hole_cells = {p for p in _enclosed(H, W, mask) if g[p[0]][p[1]] == bg}
    holes = _comps4(H, W, lambda y, x: (y, x) in hole_cells)
    groups = _band_groups(holes)
    # colour regions of the coloured shape: one-colour 4-connected regions of non-outline colour, top to bottom
    regs = []
    for c in sorted({g[y][x] for y, x in col} - {oc}):
        regs += [(min(y for y, _ in r), min(x for _, x in r), c) for r in _comps4(H, W, lambda y, x, c=c: (y, x) in col and g[y][x] == c)]
    regs.sort()
    if len(regs) < len(groups): return None
    y0, x0, y1, x1 = bbox(list(mask))
    o = [[g[y][x] if (y, x) in mask else bg for x in range(x0, x1 + 1)] for y in range(y0, y1 + 1)]
    for i, G in enumerate(groups):                                               # i-th hole group <- i-th colour region
        for R in G:
            for y, x in R: o[y - y0][x - x0] = regs[i][2]
    return o


FUN['3a25b0d8'] = f_3a25b0d8


# ---------------------------------------------------------------- e87109e9
def legend(g):
    """the top strip of framed boxes: rows down to the first all-frame row after row 0; each box (a run of non-frame
    cells between frame cells) holds one coloured cell at its left or right end -> {colour: 'left' | 'right'}"""
    W = len(g[0]); fc = g[0][0]
    if any(v != fc for v in g[0]): return None, None
    end = next((y for y in range(1, len(g)) if all(v == fc for v in g[y])), None)
    if end is None: return None, None
    L = {}
    for y in range(1, end):
        x = 0
        while x < W:
            if g[y][x] == fc: x += 1; continue
            j = x
            while j < W and g[y][j] != fc: j += 1
            box = g[y][x:j]; cnt = Counter(box)
            if len(cnt) == 2:
                bgb = cnt.most_common(1)[0][0]
                ks = [i for i, v in enumerate(box) if v != bgb]
                if len(ks) == 1:
                    c = box[ks[0]]; side = 'left' if ks[0] == 0 else ('right' if ks[0] == len(box) - 1 else None)
                    if side is None or L.get(c, side) != side: return None, None
                    L[c] = side
            x = j
    return L, end


def f_e87109e9(g):
    L, end = legend(g)
    if not L: return None
    M = [list(r) for r in g[end + 1:]]
    H, W = len(M), len(M[0]); bg = bgc(M)
    seeds = [(c, cells) for c, cells in comps(M, bg, conn8=False) if len(cells) == 4 and
             (lambda b: b[2] - b[0] == 1 and b[3] - b[1] == 1)(bbox(cells))]
    if len(seeds) != 1: return None
    rc, cells = seeds[0]
    if sum(v == rc for r in M for v in r) != 4: return None                      # the only cells of the ray colour
    sy, sx, _, _ = bbox(cells)
    o = [list(r) for r in M]
    left = lambda d: (-d[1], d[0]); right = lambda d: (d[1], -d[0])
    for d0 in ((-1, 0), (1, 0), (0, -1), (0, 1)):                                # all four directions
        y, x, d = sy, sx, d0; steps = 0
        while steps < 4 * (H + W):
            steps += 1
            ny, nx = y + d[0], x + d[1]
            lead = [(ny + a, nx + b) for a in (0, 1) for b in (0, 1)]
            lead = [p for p in lead if p not in {(y + a, x + b) for a in (0, 1) for b in (0, 1)}]
            if any(not (0 <= p[0] < H and 0 <= p[1] < W) for p in lead): break   # ends at the grid edge
            hit = {M[p[0]][p[1]] for p in lead} - {bg, rc}
            if hit:
                if len(hit) != 1: return None
                c = next(iter(hit))
                if c not in L: return None
                d = left(d) if L[c] == 'left' else right(d); continue
            y, x = ny, nx
            for p in lead: o[p[0]][p[1]] = rc
        else:
            return None
    return o


FUN['e87109e9'] = f_e87109e9


# ---------------------------------------------------------------- 522fdd07
def f_522fdd07(g):
    H, W = len(g), len(g[0]); bg = bgc(g)
    sq = []
    for c, cells in comps(g, bg, conn8=False):
        y0, x0, y1, x1 = bbox(cells); s = y1 - y0 + 1
        if x1 - x0 + 1 != s or len(cells) != s * s or s not in (1, 3, 5, 7, 9): return None   # solid odd squares only
        sq.append((c, (y0 + y1) // 2, (x0 + x1) // 2, s))
    if not sq: return None
    o = [[bg] * W for _ in range(H)]
    for c, cy, cx, s in sq:
        t = 9 if s == 1 else s - 2                                   # 9 -> 7 -> 5 -> 3 -> 1 -> 9
        r = t // 2
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if 0 <= y < H and 0 <= x < W: o[y][x] = c
    return o


FUN['522fdd07'] = f_522fdd07


# ---------------------------------------------------------------- 8719f442
def f_8719f442(g):
    n = len(g)
    if n != 3 or len(g[0]) != 3: return None
    bg = 0
    cells = [(r, c) for r in range(3) for c in range(3) if g[r][c] != bg]
    cols = {g[r][c] for r, c in cells}
    if len(cols) != 1: return None
    col = next(iter(cols))
    o = [[bg] * 15 for _ in range(15)]
    skel = {(1 + r, 1 + c) for r, c in cells}                                    # skeleton: pattern at block offset (1,1)
    def block(B, solid):
        for a in range(3):
            for b in range(3):
                if solid or g[a][b] != bg: o[3 * B[0] + a][3 * B[1] + b] = col
    for B in skel: block(B, True)
    N8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
    for B in skel:
        nb = [(B[0] + a, B[1] + b) for a, b in N8 if (B[0] + a, B[1] + b) in skel]
        if len(nb) != 1: continue                                                # tip: exactly one skeleton neighbour (8-conn)
        dy, dx = B[0] - nb[0][0], B[1] - nb[0][1]                                # direction away from the neighbour
        outs = [(B[0] + dy, B[1] + dx)] if dy == 0 or dx == 0 else [(B[0] + dy, B[1]), (B[0], B[1] + dx)]
        for P_ in outs:
            if 0 <= P_[0] < 5 and 0 <= P_[1] < 5 and P_ not in skel: block(P_, False)
    return o


FUN['8719f442'] = f_8719f442


# ---------------------------------------------------------------- 5ecac7f7
def f_5ecac7f7(g):
    H, W = len(g), len(g[0])
    uni = [x for x in range(W) if len({g[y][x] for y in range(H)}) == 1]
    cands = []
    for sc in sorted({g[0][x] for x in uni}):                                    # separator colour: the one whose full
        seps = [x for x in uni if g[0][x] == sc]                                 # columns cut equal-width panels
        bounds = [-1] + seps + [W]
        pn = [(a + 1, b) for a, b in zip(bounds, bounds[1:]) if b - a > 1]
        if len(pn) >= 2 and len({b - a for a, b in pn}) == 1 and all(b - a > 1 for a, b in zip(bounds, bounds[1:])):
            cands.append(pn)
    if len(cands) != 1: return None
    panels = cands[0]; w = panels[0][1] - panels[0][0]; n = len(panels)
    o = [[None] * w for _ in range(H)]
    for j in range(w):
        dist = [abs(j / (w - 1) - k / (n - 1)) for k in range(n)]
        m = min(dist); ks = [k for k in range(n) if abs(dist[k] - m) < 1e-9]
        k = min(ks, key=lambda k: min(k, n - 1 - k))                             # tie: the panel nearer the grid edge
        if len(ks) > 1 and len({min(k, n - 1 - k) for k in ks}) == 1: return None
        x = panels[k][0] + j
        for y in range(H): o[y][j] = g[y][x]
    return o


FUN['5ecac7f7'] = f_5ecac7f7


# ---------------------------------------------------------------- 4c7dc4dd
def framed_boxes(g, min_side=3):
    """rectangles whose border is one colour (a frame), at least min_side on each side; returns
    [(colour, (y0, x0, y1, x1))], frames whose border lies inside a larger frame of the same colour dropped"""
    H, W = len(g), len(g[0]); out = []
    for y0 in range(H):
        for x0 in range(W):
            c = g[y0][x0]
            x1max = x0
            while x1max + 1 < W and g[y0][x1max + 1] == c: x1max += 1
            y1max = y0
            while y1max + 1 < H and g[y1max + 1][x0] == c: y1max += 1
            for x1 in range(x0 + min_side - 1, x1max + 1):
                for y1 in range(y0 + min_side - 1, y1max + 1):
                    if all(g[y1][x] == c for x in range(x0, x1 + 1)) and all(g[y][x1] == c for y in range(y0, y1 + 1)):
                        inner = [g[y][x] for y in range(y0 + 1, y1) for x in range(x0 + 1, x1)]
                        if inner and any(v != c for v in inner): out.append((c, (y0, x0, y1, x1)))
    # a frame is kept if no other same-colour frame shares its border cells (keeps the tightest of nested duplicates)
    keep = []
    for c, b in out:
        dup = [b2 for c2, b2 in out if c2 == c and b2 != b and b2[0] <= b[0] and b2[1] <= b[1] and b2[2] >= b[2] and b2[3] >= b[3]
               and (b2[0] == b[0] or b2[1] == b[1] or b2[2] == b[2] or b2[3] == b[3])]
        if not dup: keep.append((c, b))
    return keep


def interior(g, b): return [row[b[1] + 1:b[3]] for row in g[b[0] + 1:b[2]]]


def boxes_on_pattern(g):
    """framed boxes whose outside ring (one cell beyond the frame, inside the grid) is not all one colour"""
    H, W = len(g), len(g[0]); out = []
    for c, (y0, x0, y1, x1) in framed_boxes(g):
        ring = [g[y][x] for y in range(y0 - 1, y1 + 2) for x in range(x0 - 1, x1 + 2)
                if 0 <= y < H and 0 <= x < W and not (y0 <= y <= y1 and x0 <= x <= x1)]
        if len(set(ring)) > 1: out.append((c, (y0, x0, y1, x1)))
    return out


def _inside(b, B): return B[0] < b[0] and B[1] < b[1] and b[2] < B[2] and b[3] < B[3]


def f_4c7dc4dd(g, verbose=False):
    import scale_free as SF
    fr = boxes_on_pattern(g)
    encl = [(c, b) for c, b in fr if any(_inside(b2, b) for _, b2 in fr)]           # enclosing frames
    boxes_ = [(c, b) for c, b in fr if (c, b) not in encl]
    def home(b):
        E = [B for _, B in encl if _inside(b, B)]
        return min(E, key=lambda B: (B[2] - B[0]) * (B[3] - B[1])) if E else None
    groups = {}
    for c, b in boxes_: groups.setdefault((c, home(b)), []).append(b)
    pairs = [v for v in groups.values() if len(v) == 2]
    empty = lambda b: len({v for r in interior(g, b) for v in r}) == 1
    ex = [p for p in pairs if not empty(p[0]) and not empty(p[1])]
    qu = [p for p in pairs if empty(p[0]) != empty(p[1])]
    if verbose: print('pairs', pairs, 'example', ex, 'query', qu)
    if len(ex) != 1 or len(qu) != 1: return None
    a, b = [interior(g, x) for x in sorted(ex[0])]
    q_in = interior(g, [x for x in qu[0] if not empty(x)][0]); q_out = interior(g, [x for x in qu[0] if empty(x)][0])
    preds = []
    for src, dst in ((a, b), (b, a)):                                                # the relation, either direction
        fits = SF.fit([{'input': src, 'output': dst}], max_depth=2, budget=60)
        for S in fits:
            r = SF.apply(S, q_in)
            if r is not None and len(r) == len(q_out) and len(r[0]) == len(q_out[0]): preds.append((SF.key(S), r)); break
        if verbose: print('direction', 'a->b' if src is a else 'b->a', 'fits', len(fits), [SF.key(S) for S in fits[:3]])
    if len(preds) != 1: return None                                                 # one direction only
    return preds[0][1]


FUN['4c7dc4dd'] = f_4c7dc4dd
