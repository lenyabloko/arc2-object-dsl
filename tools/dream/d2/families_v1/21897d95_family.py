"""Family for 21897d95 -- graphics: FLOOD FILL (paint-bucket), plus a turn-arrow orientation mark.

Picture: the grid is a map of solid colour regions.  Each region holds a small T-shaped paint-bucket nozzle
drawn in the marker colour (three arms around a centre cell).  The nozzle's stem (the arm opposite the missing
arm) touches a neighbouring region; that neighbour is flood-filled with the nozzle's paint.  The paint is the
colour loaded in the nozzle centre, or -- if the centre is plain marker colour -- the colour of the region the
nozzle stands in (all fills read the ORIGINAL colours, i.e. they happen simultaneously).  Nozzles are then wiped
(painted with their own region's colour).  An optional one-cell-thick L-shaped mark of a foreign colour is a bent
turn-arrow (like the glyphs "up-then-left" / "up-then-right"): it is wiped too and the whole picture is turned a
quarter turn in the arrow's sense.  No mark -> no turn.

Parameters (all induced from training, finite domains):
  marker  in 0..9        the nozzle colour (role: present in every training input, absent from every output)
  sense   in {+1, -1}    whether the L reads vertical-arm -> corner -> horizontal-arm (+1) or the reverse (-1)
"""

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _rot_ccw(g):
    return [list(r) for r in zip(*g)][::-1]


def _rot_cw(g):
    return [list(r)[::-1] for r in zip(*g)]


def _components(g):
    H, W = len(g), len(g[0])
    lab = [[-1] * W for _ in range(H)]
    comps = []
    for i in range(H):
        for j in range(W):
            if lab[i][j] >= 0:
                continue
            c = g[i][j]
            k = len(comps)
            lab[i][j] = k
            st, cells = [(i, j)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in D4:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and lab[x][y] < 0 and g[x][y] == c:
                        lab[x][y] = k
                        st.append((x, y))
            comps.append((c, cells))
    return lab, comps


def _nozzles(g, m):
    """Cells with exactly three marker-coloured orthogonal neighbours are nozzle centres."""
    H, W = len(g), len(g[0])
    out = []
    for i in range(H):
        for j in range(W):
            arms = [(da, db) for da, db in D4
                    if 0 <= i + da < H and 0 <= j + db < W and g[i + da][j + db] == m]
            if len(arms) != 3:
                continue
            # a real nozzle is an isolated T: no arm touches marker colour except through the centre
            if any(0 <= i + a + da < H and 0 <= j + b + db < W and g[i + a + da][j + b + db] == m
                   and (a + da, b + db) != (0, 0) for a, b in arms for da, db in D4):
                continue
            miss = [d for d in D4 if d not in arms][0]
            stem = (-miss[0], -miss[1])
            out.append(((i, j), [(i + a, j + b) for a, b in arms], stem))
    return out


def _mode(vals):
    best, bc = None, 0
    for v in vals:
        c = vals.count(v)
        if c > bc:
            best, bc = v, c
    return best


def _l_mark(cells):
    """If the cell set is a one-cell-thick L filling one outer row and one outer column of its bounding box
    (both arms >= 2 cells beyond the corner), return (corner, vertical_free_end, horizontal_free_end)."""
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    if r1 - r0 < 2 or c1 - c0 < 2 or len(cells) != (r1 - r0) + (c1 - c0) + 1:
        return None
    S = set(cells)
    for rr in (r0, r1):
        for cc in (c0, c1):
            if all((rr, y) in S for y in range(c0, c1 + 1)) and all((x, cc) in S for x in range(r0, r1 + 1)):
                vend = (r1 if rr == r0 else r0, cc)
                hend = (rr, c1 if cc == c0 else c0)
                return (rr, cc), vend, hend
    return None


def _solve(g, m, sense):
    H, W = len(g), len(g[0])
    g = [list(r) for r in g]
    fills = []
    clean = [list(r) for r in g]
    for (ci, cj), arms, (di, dj) in _nozzles(g, m):
        si, sj = ci + di, cj + dj                       # stem cell
        flank = [g[si + a][sj + b] for a, b in ((dj, di), (-dj, -di))
                 if 0 <= si + a < H and 0 <= sj + b < W and g[si + a][sj + b] != m]
        if not flank:
            mi, mj = ci - di, cj - dj
            flank = [g[mi][mj]] if 0 <= mi < H and 0 <= mj < W else []
        if not flank:
            continue
        home = _mode(flank)
        paint = g[ci][cj] if g[ci][cj] != m else home
        for a, b in arms + [(ci, cj)]:
            clean[a][b] = home
        ti, tj = ci + 2 * di, cj + 2 * dj
        if 0 <= ti < H and 0 <= tj < W:
            fills.append(((ti, tj), paint))
    # orientation mark: a foreign one-cell-thick L component; wipe it with its surroundings' colour
    turn = 0
    lab, comps = _components(clean)
    for k, (c, cells) in enumerate(comps):
        if c == m:
            continue
        L = _l_mark(cells)
        if L is None:
            continue
        S = set(cells)
        around = [clean[a + da][b + db] for a, b in cells for da, db in D4
                  if 0 <= a + da < H and 0 <= b + db < W and (a + da, b + db) not in S]
        if not around:
            continue
        sur = _mode(around)
        if sur == c or around.count(sur) * 2 <= len(around):
            continue
        for a, b in cells:
            clean[a][b] = sur
        (cr, cc), (vr, vc), (hr, hc) = L
        v1 = (0, vr - cr)                               # math coords: x = col, y = -row
        v2 = (hc - cc, 0)
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        turn = 1 if cross * sense > 0 else -1           # +1 = counter-clockwise
    # simultaneous flood fills on the cleaned map, using original region colours
    lab, comps = _components(clean)
    newc = {}
    for (ti, tj), paint in fills:
        newc[lab[ti][tj]] = paint
    out = [[newc.get(lab[i][j], clean[i][j]) for j in range(W)] for i in range(H)]
    if turn == 1:
        out = _rot_ccw(out)
    elif turn == -1:
        out = _rot_cw(out)
    return out


def fam_flood_fill(train):
    ins = [p["input"] for p in train]
    outs = [p["output"] for p in train]
    cin = set.intersection(*[set(v for r in g for v in r) for g in ins])
    cout = set().union(*[set(v for r in g for v in r) for g in outs])
    roles = sorted(cin - cout) or list(range(10))
    for m in roles:
        for sense in (1, -1):
            fn = (lambda mm, ss: (lambda g: _solve(g, mm, ss)))(m, sense)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("graphics:flood_fill[marker=%d,turn_sense=%+d]" % (m, sense), 3, fn)
                return


FAMILIES = (fam_flood_fill,)
