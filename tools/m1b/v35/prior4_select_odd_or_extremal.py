"""Prior family "select_odd_or_extremal", pass 4 (test-blind; colour roles per Fable v11 D38 / G68; train pairs only).

One generator, SELECT: enumerate comparable candidates of one kind (lattice tiles, framed panels, colour classes,
single-colour objects, denoised regions, or maximal straight runs of a colour), give every candidate one score
(cell count, foreign-cell count, odd-one-out dissimilarity, growth across a separator, or exact template match with
a reference object), pick the winner of each group by max / min with an induced tie rule, and render it: crop it,
emit a block of its colour, paint it in place with a mark colour (one mark for the max and optionally one for the
min), enlarge it over the lattice, or assemble one winner per lattice rank into a strip.
Pass 4 = pass 3 with every colour parameter bound to a declared colour role of colour_roles.py (background,
rank_colour(k), novel_colour) or a participant's colour; the literal source-colour and literal mark-colour values
of pass 3 are gone (no program stores a colour number).

BINDINGS (G68) -- per fitted member of pass 3: each former literal -> the role it became, or LOST.
  09629e4f  lattice 5 <- colour owning full rows+cols (participant); tile bg <- background of the non-line cells;
            block colours <- the winner tile's own cells (participant).  No literal.
  38007db0  lattice <- participant; winners' cells (participant).  No literal.
  8597cfd7  separator <- participant; output colour <- winner.colour (participant).  No literal.
  aa300dc3  source colour 0 <- rank_colour(g, 1) (pass 3: role 'rank2', literal fallback removed)
            mark colour 8   <- novel_colour(train)   (was literal 8)
  aee291af  panel frame <- participant; crop.  No literal.
  ce602527  reference / winner <- participants; crop.  No literal.
  de1cd16c  output colour <- winner.colour (participant).  No literal.
  e45ef808  source colour 1 <- background(g) (pass 3: role 'mode')
            mark colours 9 (max), 4 (min) -> LOST: needs literal 9 and 4 (two colours new in every output, so
            novel_colour is undefined; no input role equals either)
Colour-role menus (role order = enumeration order):
  source colour (runs)  in {background(g) | rank_colour(g, k), k in 1, 2, 3, -1, -2 | any non-background colour
                        (the slot of pass 3's literal, offered when one colour changes overall)}; roles checked per
                        pair (the colour that changes in each pair is the role's colour there)
  mark colour(s)        in {novel_colour(train) | background(g) | rank_colour(g, k), k in 1, 2, 3, -1, -2}; for two
                        marks the first role pair whose colours are, in every pair, the changed-to colours, both
                        max/min assignments tried
  output colour         <- winner.colour (always a participant);  background <- background(g) | non-line mode (tiles)
Not widened: no shared step was added in pass 4.
"""
from collections import Counter
from itertools import combinations

import colour_roles as CR

CARD = "prior4_select_odd_or_extremal"
CONCEPT = "select_odd_or_extremal"
MEMBERS = ["09629e4f", "38007db0", "8597cfd7", "aa300dc3", "aee291af", "ce602527", "de1cd16c", "e45ef808"]
READING = {
    "generator": "Enumerate candidates of one kind (lattice tiles, framed panels, colour classes, objects, denoised "
                 "regions or straight runs), score each (cell count, foreign-cell count, odd-one-out "
                 "dissimilarity, growth across a separator, template match with the edge-cut reference), select the "
                 "max or min of every group with an induced tie rule, and output the winner cropped, as a block of "
                 "its colour, painted in place with a role mark colour, enlarged over the lattice, or one winner per "
                 "lattice rank assembled into a strip.",
    "stop": "One winner per group (per selector for marks); a program is rejected when a tie remains under tie=unique "
            "or the kind's precondition (lattice, separator, reference, enough candidates) fails.",
    "params": "kind ∈ {tiles/all, tiles/row, tiles/col, panels/solid, panels/open, colours, objects, regions, "
              "runs/V, runs/H, runs/VH, runs/D} · score ∈ {size, ink, odd, growth, match} · sel ∈ {max, min} · "
              "tie ∈ {unique, first, last, centre} · out ∈ {crop, colour(h×w), mark(max→m1[, min→m2]), enlarge, "
              "strip} · src (runs/mark) ∈ {background, rank_colour(k)} · m1, m2 ∈ {novel, background, "
              "rank_colour(k)}",
    "participants": "bg = most frequent colour (for tiles: of the non-line cells); lattice = the colour owning full "
                    "rows and full columns (most lines); separator = a full line of a non-bg colour; panels = "
                    "maximal rectangles with a uniform non-bg border holding another colour; objects = 8-connected "
                    "single-colour non-bg components; regions = 4-components after singletons are replaced by their "
                    "neighbours' majority; runs = maximal straight runs of the mark's source colour, bound by role "
                    "(background or rank_colour(k), checked per pair; else of any non-bg colour); mark colours = "
                    "novel_colour(train), background or rank_colour(k) of the grid; reference for match = the unique edge-touching candidate, else the largest.",
    "preconditions": "out=mark/enlarge: same shape and only one source colour changes per pair (mark) or a lattice with as "
                     "many blocks as a tile has cells (enlarge); out=colour: every output is one colour and all "
                     "outputs share one size; out=crop/strip: smaller output equal to the winner's clean patch / the "
                     "lattice strip; every parameter is chosen by exact fit on all training pairs.",
}

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
RUN_DIRS = {'V': ((1, 0),), 'H': ((0, 1),), 'VH': ((1, 0), (0, 1)), 'D': ((1, 1), (1, -1))}
MAX_CANDS = 400


# ----------------------------------------------------------------------------------------------- shared steps
def _mode(vals, default=None):
    c = Counter(vals)
    if not c:
        return default
    return max(c, key=lambda k: (c[k], -k))


def _segments(n, lines):
    s, segs, cur = set(lines), [], []
    for i in range(n):
        if i in s:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        segs.append(cur)
    return segs


class _Ctx(object):
    """Per-grid roles: grid mode, lattice (colour, rows, cols), tile background, separator split."""

    def __init__(self, g):
        H, W = len(g), len(g[0])
        self.g, self.H, self.W = g, H, W
        self.m = CR.background(g)                            # role: background
        self.rc = {}
        rows, cols = {}, {}
        for i in range(H):
            if len(set(g[i])) == 1:
                rows.setdefault(g[i][0], []).append(i)
        for j in range(W):
            if len({g[i][j] for i in range(H)}) == 1:
                cols.setdefault(g[0][j], []).append(j)
        both = [k for k in rows if k in cols]
        self.lat = None
        if both:
            k = max(both, key=lambda k: (k != self.m, len(rows[k]) + len(cols[k]), -k))
            self.lat = (k, rows[k], cols[k])
        if self.lat:
            L, lr, lc = self.lat
            sr, sc = set(lr), set(lc)
            self.bg_t = _mode([g[i][j] for i in range(H) if i not in sr for j in range(W) if j not in sc], self.m)
        else:
            self.bg_t = self.m
        # separator: first full line (row, else column) whose colour is not the grid mode
        self.split = None
        for i in range(H):
            if len(set(g[i])) == 1 and g[i][0] != self.m:
                self.split = ('r', i, g[i][0])
                break
        if self.split is None:
            for j in range(W):
                col = {g[i][j] for i in range(H)}
                if len(col) == 1 and g[0][j] != self.m:
                    self.split = ('c', j, g[0][j])
                    break


SRC_ROLES = (('background',), ('rank', 1), ('rank', 2), ('rank', 3), ('rank', -1), ('rank', -2))
MARK_ROLES = (('novel',), ('background',), ('rank', 1), ('rank', 2), ('rank', 3), ('rank', -1), ('rank', -2))


def _rname(role):
    return role[0] if len(role) == 1 else '%s%d' % role


def _role_colour(X, role, nov=None):
    """Colour bound to a declared role in this grid: background(g), rank_colour(g, k) or novel_colour(train) (a
    constant fixed by the training pairs, passed in as nov)."""
    if role[0] == 'novel':
        return nov
    if role[0] == 'background':
        return X.m
    if role not in X.rc:
        X.rc[role] = CR.rank_colour(X.g, role[1], X.m)
    return X.rc[role]


class _Cand(object):
    __slots__ = ('cells', 'colour', 'ground', 'patch', 'group', 'order')

    def __init__(self, g, cells, colour, ground, bg, group, order):
        self.cells, self.colour, self.ground, self.group, self.order = cells, colour, ground, group, order
        r0 = min(a for a, _ in cells)
        r1 = max(a for a, _ in cells)
        c0 = min(b for _, b in cells)
        c1 = max(b for _, b in cells)
        S = set(cells)
        self.patch = tuple(tuple(g[a][b] if (a, b) in S else bg for b in range(c0, c1 + 1))
                           for a in range(r0, r1 + 1))


def _components(g, pred, nb, same=True):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or not pred(g[i][j]):
                continue
            c = g[i][j]
            seen[i][j] = True
            st, cells = [(i, j)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and pred(g[x][y]) and (not same or g[x][y] == c):
                        seen[x][y] = True
                        st.append((x, y))
            out.append((c, sorted(cells)))
    return out


# ----------------------------------------------------------------------------------------------- candidate kinds
def _tiles(g, X, group):
    if X.lat is None:
        return None
    L, lr, lc = X.lat
    R, C = _segments(X.H, lr), _segments(X.W, lc)
    if len(R) * len(C) < 2:
        return None
    bg = X.bg_t
    out = []
    for i, rs in enumerate(R):
        for j, cs in enumerate(C):
            cells = [(a, b) for a in rs for b in cs]
            col = _mode([g[a][b] for a, b in cells if g[a][b] != bg], bg)
            grp = 0 if group == 'all' else (i if group == 'row' else j)
            out.append(_Cand(g, cells, col, bg, bg, grp, (i, j)))
    return out


def _panels(g, X, interior):
    H, W, bg = X.H, X.W, X.m
    right = [[1] * W for _ in range(H)]
    down = [[1] * W for _ in range(H)]
    for i in range(H - 1, -1, -1):
        for j in range(W - 1, -1, -1):
            if j + 1 < W and g[i][j + 1] == g[i][j]:
                right[i][j] = right[i][j + 1] + 1
            if i + 1 < H and g[i + 1][j] == g[i][j]:
                down[i][j] = down[i + 1][j] + 1
    pre = {}  # per-colour 2D prefix counts, for O(1) interior tests

    def table(v):
        if v not in pre:
            t = [[0] * (W + 1) for _ in range(H + 1)]
            for i in range(H):
                acc = 0
                for j in range(W):
                    acc += g[i][j] == v
                    t[i + 1][j + 1] = t[i][j + 1] + acc
            pre[v] = t
        return pre[v]

    def count(t, a0, b0, a1, b1):  # inclusive-exclusive box
        return t[a1][b1] - t[a0][b1] - t[a1][b0] + t[a0][b0]

    tb = table(bg)
    rects = []
    for r in range(H):
        for c in range(W):
            F = g[r][c]
            if F == bg or right[r][c] < 3 or down[r][c] < 3:
                continue
            tf = table(F)
            for h in range(3, down[r][c] + 1):
                for w in range(3, right[r][c] + 1):
                    if right[r + h - 1][c] < w or down[r][c + w - 1] < h:
                        continue
                    if count(tf, r + 1, c + 1, r + h - 1, c + w - 1) == (h - 2) * (w - 2):
                        continue
                    if interior == 'solid' and count(tb, r + 1, c + 1, r + h - 1, c + w - 1):
                        continue
                    rects.append((r, c, h, w))
                    if len(rects) > MAX_CANDS:
                        return None
    keep = [q for q in rects if not any(p != q and p[0] <= q[0] and p[1] <= q[1] and q[0] + q[2] <= p[0] + p[2]
                                        and q[1] + q[3] <= p[1] + p[3] for p in rects)]
    out = []
    for r, c, h, w in keep:
        cells = [(a, b) for a in range(r, r + h) for b in range(c, c + w)]
        col = _mode([g[a][b] for a, b in cells if g[a][b] != bg], bg)
        out.append(_Cand(g, cells, col, bg, bg, 0, (r, c)))
    return out


def _colours(g, X):
    bg = X.m
    sep = X.split[2] if X.split else None
    by = {}
    for i in range(X.H):
        for j in range(X.W):
            v = g[i][j]
            if v != bg and v != sep:
                by.setdefault(v, []).append((i, j))
    return [_Cand(g, cells, v, bg, bg, 0, cells[0]) for v, cells in sorted(by.items(), key=lambda t: t[1][0])]


def _objects(g, X):
    bg = X.m
    comps = _components(g, lambda v: v != bg, DIRS8)
    if len(comps) > MAX_CANDS:
        return None
    return [_Cand(g, cells, c, bg, bg, 0, cells[0]) for c, cells in comps]


def _regions(g, X):
    H, W = X.H, X.W
    clean = [list(r) for r in g]
    for c, cells in _components(g, lambda v: True, DIRS4):
        if len(cells) == 1:
            a, b = cells[0]
            nb = [g[x][y] for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)) if 0 <= x < H and 0 <= y < W]
            clean[a][b] = _mode(nb, c)
    comps = _components(clean, lambda v: True, DIRS4)
    if len(comps) > MAX_CANDS:
        return None
    return [_Cand(g, cells, c, c, X.m, 0, cells[0]) for c, cells in comps]


def _runs(g, X, dirs, src):
    H, W = X.H, X.W
    out = []
    for dr, dc in RUN_DIRS[dirs]:
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if (v != src) if src is not None else (v == X.m):
                    continue
                pr, pc = r - dr, c - dc
                if 0 <= pr < H and 0 <= pc < W and g[pr][pc] == v:
                    continue
                cells, a, b = [], r, c
                while 0 <= a < H and 0 <= b < W and g[a][b] == v:
                    cells.append((a, b))
                    a += dr
                    b += dc
                out.append(_Cand(g, cells, v, X.m, X.m, 0, (r, c)))
                if len(out) > 4 * MAX_CANDS:
                    return None
    out.sort(key=lambda q: q.order)
    return out


def _cands(g, X, kind, src):
    k, _, p = kind.partition('/')
    if k == 'tiles':
        return _tiles(g, X, p)
    if k == 'panels':
        return _panels(g, X, p)
    if k == 'colours':
        return _colours(g, X)
    if k == 'objects':
        return _objects(g, X)
    if k == 'regions':
        return _regions(g, X)
    return _runs(g, X, p, src)


# ----------------------------------------------------------------------------------------------- scores
def _scale_matches(mask, h, w, ref, H, W, k):
    r0 = min(a for a, _ in ref)
    r1 = max(a for a, _ in ref)
    c0 = min(b for _, b in ref)
    c1 = max(b for _, b in ref)
    for oy in range(r1 - k * h + 1, r0 + 1):
        for ox in range(c1 - k * w + 1, c0 + 1):
            ok = True
            for i in range(max(0, oy), min(H, oy + k * h)):
                for j in range(max(0, ox), min(W, ox + k * w)):
                    if mask[(i - oy) // k][(j - ox) // k] != ((i, j) in ref):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                return True
    return False


def _scores(g, X, cands, score):
    if score == 'size':
        return [len(q.cells) for q in cands]
    if score == 'ink':
        return [sum(1 for a, b in q.cells if g[a][b] != q.ground) for q in cands]
    if score == 'growth':
        if X.split is None:
            return None
        ax, at, _ = X.split
        res = []
        for q in cands:
            pos = [a if ax == 'r' else b for a, b in q.cells]
            res.append(sum(1 for p in pos if p > at) - sum(1 for p in pos if p < at))
        return res
    if score == 'odd':
        if len(cands) < 3 or len(cands) > 60:
            return None
        res = []
        for q in cands:
            peers = [o for o in cands if o is not q and o.group == q.group]
            if len(peers) < 2:
                return None
            freq = sum(1 for o in peers if o.patch == q.patch)
            dist = 0
            for o in peers:
                if len(o.patch) == len(q.patch) and len(o.patch[0]) == len(q.patch[0]):
                    dist += sum(x != y for ra, rb in zip(q.patch, o.patch) for x, y in zip(ra, rb))
                else:
                    dist += len(q.patch) * len(q.patch[0])
            res.append((-freq, dist))
        return res
    if score == 'match':
        if len(cands) < 2 or len(cands) > 12:
            return None
        H, W = X.H, X.W
        edge = [q for q in cands if any(a in (0, H - 1) or b in (0, W - 1) for a, b in q.cells)]
        ref = edge[0] if len(edge) == 1 else max(cands, key=lambda q: len(q.cells))
        R = set(ref.cells)
        res = []
        for q in cands:
            if q is ref:
                res.append(-1)
                continue
            S = set(q.cells)
            r0 = min(a for a, _ in S)
            c0 = min(b for _, b in S)
            h = max(a for a, _ in S) - r0 + 1
            w = max(b for _, b in S) - c0 + 1
            mask = [[(r0 + i, c0 + j) in S for j in range(w)] for i in range(h)]
            res.append(1 if any(_scale_matches(mask, h, w, R, H, W, k) for k in (1, 2, 3, 4)
                                if k * h <= H and k * w <= W and k * k * len(S) >= len(R)) else 0)
        return res
    return None


# ----------------------------------------------------------------------------------------------- selection
def _straight(cells):
    (a0, b0), (a1, b1) = cells[0], cells[1]
    da, db = a1 - a0, b1 - b0
    if max(abs(da), abs(db)) != 1:
        return False
    return all(a == a0 + k * da and b == b0 + k * db for k, (a, b) in enumerate(cells))


def _select(cands, scores, sel, tie, H, W):
    """Winner per group: {group: cand} or None when a tie remains under tie=unique."""
    groups = {}
    for q, s in zip(cands, scores):
        groups.setdefault(q.group, []).append((s, q))
    win = {}
    for gk, items in groups.items():
        best = max(s for s, _ in items) if sel == 'max' else min(s for s, _ in items)
        tied = [q for s, q in items if s == best]
        if len(tied) > 1:
            if tie == 'unique':
                return None
            if tie == 'first':
                q = min(tied, key=lambda q: q.order)
            elif tie == 'last':
                q = max(tied, key=lambda q: q.order)
            else:
                cr, cc = (H - 1) / 2.0, (W - 1) / 2.0

                def d(q):
                    # straight run: distance from the grid centre to its full line; otherwise to its centroid
                    if q.cells and len(q.cells) >= 2 and _straight(q.cells):
                        (a0, b0), (a1, b1) = q.cells[0], q.cells[1]
                        da, db = a1 - a0, b1 - b0
                        return ((((cr - a0) * db - (cc - b0) * da) ** 2) / float(da * da + db * db), q.order)
                    n = float(len(q.cells))
                    return ((sum(a for a, _ in q.cells) / n - cr) ** 2 + (sum(b for _, b in q.cells) / n - cc) ** 2,
                            q.order)
                q = min(tied, key=d)
        else:
            q = tied[0]
        win[gk] = q
    return win


# ----------------------------------------------------------------------------------------------- renderers
def _render(g, X, out, oparam, wins, axis, nov=None):
    """wins: list of (selector-index, {group: cand}); oparam: output size (colour) or mark-colour roles;
    axis: the tile grouping ('all' | 'row' | 'col') used by the strip renderer."""
    if out == 'mark':
        res = [list(r) for r in g]
        for (_, win), role in zip(wins, oparam):
            colour = _role_colour(X, role, nov)
            if len(win) != 1 or colour is None:
                return None
            for a, b in list(win.values())[0].cells:
                res[a][b] = colour
        return res
    win = wins[0][1]
    if out in ('crop', 'colour', 'enlarge') and len(win) != 1:
        return None
    if out == 'crop':
        return [list(r) for r in list(win.values())[0].patch]
    if out == 'colour':
        oh, ow = oparam
        c = list(win.values())[0].colour
        return [[c] * ow for _ in range(oh)]
    L, lr, lc = X.lat
    R, C = _segments(X.H, lr), _segments(X.W, lc)
    if out == 'enlarge':
        p = list(win.values())[0].patch
        if len(p) != len(R) or len(p[0]) != len(C):
            return None
        res = [list(r) for r in g]
        for i, rs in enumerate(R):
            for j, cs in enumerate(C):
                for a in rs:
                    for b in cs:
                        res[a][b] = p[i][j]
        return res
    # strip: one winner per rank, written into the first tile slot of the rank axis (with its adjacent lines)
    if axis == 'row':
        c0, c1 = C[0][0], C[0][-1]
        lo = c0 - 1 if c0 - 1 in set(lc) else c0
        hi = c1 + 1 if c1 + 1 in set(lc) else c1
        res = [list(g[a][lo:hi + 1]) for a in range(X.H)]
        for i, rs in enumerate(R):
            p = win[i].patch
            for x, a in enumerate(rs):
                for y, b in enumerate(C[0]):
                    res[a][b - lo] = p[x][y]
        return res
    r0, r1 = R[0][0], R[0][-1]
    lo = r0 - 1 if r0 - 1 in set(lr) else r0
    hi = r1 + 1 if r1 + 1 in set(lr) else r1
    res = [list(g[a]) for a in range(lo, hi + 1)]
    for j, cs in enumerate(C):
        p = win[j].patch
        for x, a in enumerate(R[0]):
            for y, b in enumerate(cs):
                res[a - lo][b] = p[x][y]
    return res


def _program(kind, score, sels, tie, out, oparam, src, nov, cache=None):
    def fn(g):
        key = id(g)
        if cache is not None and key in cache:
            X, memo = cache[key]
        else:
            X, memo = _Ctx(g), {}
            if cache is not None:
                cache[key] = (X, memo)
        s = src
        if src is not None:  # role-bound source colour, resolved on this grid
            s = _role_colour(X, src)
            if s is None:
                return None
        ck = ('c', kind, s)
        if ck not in memo:
            memo[ck] = _cands(g, X, kind, s)
        cands = memo[ck]
        if not cands:
            return None
        sk = ('s', kind, s, score)
        if sk not in memo:
            memo[sk] = _scores(g, X, cands, score)
        sc = memo[sk]
        if sc is None:
            return None
        wins = []
        for i, sel in enumerate(sels):
            w = _select(cands, sc, sel, tie, X.H, X.W)
            if w is None:
                return None
            wins.append((i, w))
        return _render(g, X, out, oparam, wins, kind.partition('/')[2], nov)
    return fn


# ----------------------------------------------------------------------------------------------- family
KINDS = ['tiles/all', 'tiles/row', 'tiles/col', 'panels/solid', 'panels/open', 'colours', 'objects', 'regions',
         'runs/V', 'runs/H', 'runs/VH', 'runs/D']
SCORES = ['size', 'ink', 'odd', 'growth', 'match']
TIES = ['unique', 'first', 'last', 'centre']
KIND_SCORES = {'tiles': ('ink', 'size', 'odd'), 'panels': ('odd', 'ink', 'size'),
               'colours': ('size', 'growth', 'match', 'odd'), 'objects': ('size', 'odd', 'match', 'ink', 'growth'),
               'regions': ('ink', 'size'), 'runs': ('size',)}


def _mark_roles(Xs, tg, nov):
    """Mark-colour roles: for one mark the first role whose colour is, in every pair, the changed-to colour; for two
    marks the first role pair whose colours are exactly the changed-to colours of every pair (both assignments)."""
    m = max(len(t) for t in tg)
    if m == 1:
        for r in MARK_ROLES:
            if all(not t or t == {_role_colour(X, r, nov)} for X, t in zip(Xs, tg)):
                return [(('max',), (r,)), (('min',), (r,))]
        return []
    for r1, r2 in combinations(MARK_ROLES, 2):
        ok = True
        for X, t in zip(Xs, tg):
            cs = (_role_colour(X, r1, nov), _role_colour(X, r2, nov))
            if None in cs or cs[0] == cs[1] or not t <= set(cs):
                ok = False
                break
        if ok:
            return [(('max', 'min'), (r1, r2)), (('max', 'min'), (r2, r1))]
    return []


def _specs(train, nov):
    pairs = [(p['input'], p['output']) for p in train]
    same = all(len(i) == len(o) and len(i[0]) == len(o[0]) for i, o in pairs)
    outs = []
    if same:
        src, per, tg = set(), [], []
        for i, o in pairs:
            sp, tp = set(), set()
            for r in range(len(i)):
                for c in range(len(i[0])):
                    if i[r][c] != o[r][c]:
                        sp.add(i[r][c])
                        tp.add(o[r][c])
            per.append(sp)
            tg.append(tp)
            src |= sp
        if src and max(len(t) for t in tg) <= 2 and all(not (sp & tp) for sp, tp in zip(per, tg)):
            Xs = [_Ctx(i) for i, _ in pairs]
            marks = _mark_roles(Xs, tg, nov)
            # source colour menu: the roles that explain the changed colour of EVERY pair; the slot of pass 3's
            # literal changed colour (one source colour overall) now holds 'any non-background colour' (None)
            opts = []
            for role in SRC_ROLES:
                if all(not sp or sp == {_role_colour(X, role)} for sp, X in zip(per, Xs)):
                    opts.append(role)
            if len(src) == 1:
                opts.append(None)
            for sels, cols in marks:
                outs.append(('mark', cols, sels, tuple(opts)))
        outs.append(('enlarge', None, ('max',), None))
        outs.append(('enlarge', None, ('min',), None))
    else:
        uni = all(len({v for r in o for v in r}) == 1 for _, o in pairs)
        shapes = {(len(o), len(o[0])) for _, o in pairs}
        if uni and len(shapes) == 1:
            for sel in ('max', 'min'):
                outs.append(('colour', list(shapes)[0], (sel,), None))
        elif all(len(o) <= len(i) and len(o[0]) <= len(i[0]) for i, o in pairs):
            for sel in ('max', 'min'):
                outs.append(('crop', None, (sel,), None))
                outs.append(('strip', None, (sel,), None))
    for out, oparam, sels, opts in outs:
        for kind in KINDS:
            k = kind.split('/')[0]
            if out in ('enlarge', 'strip') and k != 'tiles':
                continue
            if out == 'enlarge' and kind != 'tiles/all':
                continue
            if out == 'strip' and kind == 'tiles/all':
                continue
            # the source colour only matters for runs; there every menu entry is tried, role-bound first
            srcs = opts if (k == 'runs' and out == 'mark') else (None,)
            for src in srcs:
                for score in KIND_SCORES[k]:
                    if score == 'odd' and sels[0] != 'max':
                        continue
                    for tie in TIES:
                        cost = (KINDS.index(kind) * 0.01 + SCORES.index(score) * 0.1 + TIES.index(tie) * 0.5
                                + (0.2 if sels[0] == 'min' else 0) + 1)
                        yield (kind, score, sels, tie, out, oparam, src, cost)


def fam(train):
    if not train or any(not p['input'] or not p['input'][0] or not p['output'] or not p['output'][0] for p in train):
        return
    cache = {}
    nov = CR.novel_colour(train)
    found, seen = [], set()
    for kind, score, sels, tie, out, oparam, src, cost in _specs(train, nov):
        fn = _program(kind, score, sels, tie, out, oparam, src, nov, cache)
        ok = True
        for p in train:
            try:
                if fn(p['input']) != p['output']:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if not ok:
            continue
        if out == 'mark':
            op = ':' + ','.join(_rname(r) for r in oparam)
        else:
            op = '' if oparam is None else ':' + ','.join(map(str, oparam))
        name = 'select[%s|%s|%s|%s|%s%s%s]' % (kind, score, '+'.join(sels), tie, out, op,
                                               '' if src is None else '@src=%s' % _rname(src))
        if (kind, score, sels, out, oparam) in seen:
            continue
        seen.add((kind, score, sels, out, oparam))
        found.append((cost, len(found), name, _program(kind, score, sels, tie, out, oparam, src, nov)))
        if len(found) >= 6:
            break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found[:3]:
        yield (name, cost, fn)


FAMILIES = [fam]
