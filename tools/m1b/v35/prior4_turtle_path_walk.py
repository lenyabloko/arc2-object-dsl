"""Prior family "turtle_path_walk", version 3 (test-blind; specialised over FITTED BINDINGS, G68 / Fable v10b T65).

One generator: agents (seed cells of an induced colour, every seed cell, the rarest colour's cells, the elbow cells
of objects, or the grid corner of a blank grid) set off with an initial heading and move one cell per step over a
free board.  At each step one pluggable turn rule picks the move:
  block  -- go straight; when blocked turn by the chirality (spiral / corridor runner), stop when still blocked;
  bug    -- prefer the home heading, else sidestep perpendicular to it (wall hugging, Bug-0), stop when both blocked;
  stair  -- alternate home step / sidestep (staircase), sidestepping early when the home step is blocked;
  reflect-- diagonal ray that bounces off every flat surface it touches (axis flip), reverses at a pointed corner.
Blocked = the next cell is off-grid (a wall, or an exit that ends the walk) or occupied (input objects, plus the
trails already drawn when occupancy is 'out'); gap=1 keeps one free cell between the walker and occupied cells;
gap=marks:K grows every obstacle (4-connected non-background, non-agent component) by a clearance equal to its
number of K-coloured cells (Chebyshev), and those mark cells get the 'mark' role.  Every trail cell gets an event
role (start, line, turn, resume, hit = the obstacle that caused a turn, end); each role's colour is induced from
the training pairs as keep, the agent's colour, the tint (colour of the last surface bounced off; for 'mark', the
obstacle's own non-mark colour) or one literal colour.

BINDINGS (G68, priors4 / Fable v11 D38): every colour parameter is a declared role of colour_roles (CR) or a
role-bound value; no literal colour number is left.  Colour parameters and their roles:
  background           <- CR.background(g) (per-grid mode, ties -> lower colour; = the old mode)
  who = K (seed colour) <- CR.rank_colour(g, k), k in CR.RANKS | vanish (the single colour of
                          CR.vanishing_colours(train): ROLE-BOUND VALUE defined in this family) -- literal K removed
  gap = marks:K         <- same roles as who -- literal K removed
  event colour          <- keep | agent colour | tint (role-bound, as before) | CR.novel_colour(train) |
                          CR.background(g) | CR.rank_colour(g, k) -- the literal colour fallback is removed
  member    former literal               role it became
  --------  ---------------------------  ------------------------------------------------------------------------
  142ca369  (none: tint / keep)          -
  28e73c20  colour 3 (all event roles)   CR.novel_colour(train) (blank inputs, 3 new in every output)
  69889d6e  who = 2                      CR.rank_colour(g, -1) (2 is the least frequent ink colour in every input;
                                         the tie-rejecting 'rare' role failed on pair 0)
  7ec998c9  colour 1 (line/turn/end)     CR.novel_colour(train)
  891232d6  hit 8, line 2, resume 3,     LOST: needs literals 8, 2, 3, 4 (four colours new in the outputs: no single
            turn 4                       novel colour, and none is an input colour)
  99fa7670  (none: agent colour)         -
  cb2d8a2c  gap = marks:1                vanish (1 is in every input and in no output; its rank varies 1 / 2)
  heading/chirality literals (28e73c20 up/cw, 69889d6e cw, 7ec998c9 v, 99fa7670 right/cw) are not colours: unchanged.
Specialisation menu (priors3, unchanged apart from the colour roles):
  who     += rare  (unique least-frequent non-background colour)
  heading += edge  (inward normal of the single grid edge the agent sits on)
  chir    += open  (sidestep toward the nearer end of the blocking obstacle, re-chosen at every new block)
  gap     += marks:K (clearance <- number of K cells on the obstacle; mark colour <- obstacle's own colour)
Unfitted members (5545f144, 8b28cd80, e6de6e8f, e87109e9 size change; 3490cc26, 3e6067c3 graph/legend steps;
97c75046, 992798f6 diagonal slides / goal seeking; 88bcf3b4 rope re-laying) stay unfitted.
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_turtle_path_walk"
CONCEPT = "turtle_path_walk"
MEMBERS = ["142ca369", "28e73c20", "3490cc26", "3e6067c3", "5545f144", "69889d6e", "7ec998c9", "88bcf3b4",
           "891232d6", "8b28cd80", "97c75046", "992798f6", "99fa7670", "cb2d8a2c", "e6de6e8f", "e87109e9"]
READING = {
    "generator": "Agents (seed cells, the rarest colour, object elbows or the corner of a blank grid) walk one cell per step from "
                 "an initial heading; a pluggable turn rule (turn by a chirality when blocked, prefer the home "
                 "heading else sidestep, alternate home step and sidestep, or bounce diagonally off surfaces) "
                 "picks each move, and every trail cell is painted with the colour induced for its event role "
                 "(start, line, turn, resume, hit obstacle, end) as keep, agent colour, bounce tint or a literal.",
    "stop": "A walker stops when its next step leaves the grid (edge=exit), when every move its rule allows is "
            "blocked (boxed in), when the obstacle-end side is undecided (chir=open tie), or on a repeated "
            "state; the last cell gets the 'end' role.",
    "params": "who ∈ {corner of blank grid, all seed cells, rarest colour (role), cells of colour K (K = "
              "CR.rank_colour(g, k) or the single vanishing colour), elbows} · heading ∈ {inward normal of the agent's grid edge (role), up, "
              "right, down, left, both ways vertical, both ways horizontal, elbow outward (role)} · rule ∈ "
              "{block, bug, stair, reflect} · chirality ∈ {cw, ccw, cw on even r+c, cw on odd r+c, toward the "
              "blocking obstacle's nearer end (role)} · edge ∈ {wall, exit} · gap ∈ {0, 1, clearance = number "
              "of K marks on the obstacle (role, K as for who)} · occupancy/order ∈ {input only, input+trails in reading "
              "order, input+trails in reverse order} · role colour ∈ {keep, agent, tint, CR.novel_colour(train), "
              "CR.background(g), CR.rank_colour(g, k)}; no literal colours (G68).",
    "participants": "Background = CR.background(g); seeds = non-background cells (of colour K when "
                    "chosen); elbows = cells with exactly two perpendicular same-colour 4-neighbours, heading "
                    "diagonally away from both arms; obstacles = all other non-background cells (grown by "
                    "their own mark count when gap=marks:K; marks are repainted with the obstacle's colour).",
    "preconditions": "Input and output have the same size, some cell changes, every cell a walker moves onto "
                     "changes colour (checked step by step for fast rejection), every mark cell changes colour "
                     "(gap=marks:K), at most 16 walkers, a deterministic cap of 300000 walker steps per call, and "
                     "one consistent role-colour map reproduces every training pair.",
}

DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))          # clockwise: up, right, down, left
MAXW = 16
PRIO = {"line": 0, "turn": 1, "resume": 1, "end": 2, "start": 3}


def _bg(g):
    """background <- CR.background(g) (per-grid mode, ties -> lower colour)."""
    return CR.background(g)


# colour roles (G68): a seed / mark colour K and every event colour are roles, never literals
KROLES = tuple(("rank", k) for k in CR.RANKS) + (("vanish",),)
CROLES = (("novel",), ("background",)) + tuple(("rank", k) for k in CR.RANKS)


def _rname(role):
    return role[0] if len(role) == 1 else "%s%d" % role


def _rcol(g, role, rc, bg=None):
    """Resolve a colour role on grid g.  rc = role-bound constants learned from the training pairs:
    {'novel': CR.novel_colour(train), 'vanish': the single colour of CR.vanishing_colours(train)}."""
    if role[0] == "rank":
        return CR.rank_colour(g, role[1], CR.background(g) if bg is None else bg)
    if role[0] == "background":
        return CR.background(g) if bg is None else bg
    return rc.get(role[0])


def _consts(train):
    van = CR.vanishing_colours(train)
    return {"novel": CR.novel_colour(train), "vanish": next(iter(van)) if len(van) == 1 else None}


def _ccols(G, rc, bg=None):
    """Colour each event-colour role names on grid G."""
    return {r: _rcol(G, r, rc, bg) for r in CROLES}


class _Abort(Exception):
    pass


class _Budget(Exception):
    """Deterministic work cap: total walker steps per fam() call (keeps every task under 1 s)."""
    pass


BUDGET = 300000


def _elbows(g, bg):
    H, W = len(g), len(g[0])
    out = []
    for r in range(H):
        for c in range(W):
            col = g[r][c]
            if col == bg:
                continue
            nb = [(a, b) for a, b in DIRS if 0 <= r + a < H and 0 <= c + b < W and g[r + a][c + b] == col]
            if len(nb) == 2 and nb[0][0] * nb[1][0] + nb[0][1] * nb[1][1] == 0:
                out.append((r, c, -(nb[0][0] + nb[1][0]), -(nb[0][1] + nb[1][1])))
    return out


def _agents(g, bg, who, heading, rc=None):
    """List of (r, c, colour, home heading (dr, dc)) or None when the selector does not apply.
    who = 'corner' | 'all' | 'rare' | 'elbow' | a colour role (cells of the colour it names on g)."""
    H, W = len(g), len(g[0])
    cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    if who == "corner":
        if cells or not isinstance(heading, int):
            return None
        return [(0, 0, None, DIRS[heading])]
    if who == "elbow":
        if heading != "out":
            return None
        return [(r, c, g[r][c], (dr, dc)) for r, c, dr, dc in _elbows(g, bg)]
    if heading == "out":
        return None
    if who == "rare":
        cnt = Counter(g[r][c] for r, c in cells)
        if not cnt:
            return None
        lo = min(cnt.values())
        rare = [k for k in cnt if cnt[k] == lo]
        if len(rare) != 1:
            return None
        cells = [(r, c) for r, c in cells if g[r][c] == rare[0]]
    elif who != "all":
        K = _rcol(g, who, rc or {}, bg)
        if K is None or K == bg:
            return None
        cells = [(r, c) for r, c in cells if g[r][c] == K]
    if heading == "edge":
        out = []
        for r, c in cells:
            ns = [d for d, ok in ((DIRS[2], r == 0), (DIRS[0], r == H - 1), (DIRS[1], c == 0),
                                  (DIRS[3], c == W - 1)) if ok]
            if len(ns) != 1:
                return None
            out.append((r, c, g[r][c], ns[0]))
        return out
    if isinstance(heading, int):
        hs = [DIRS[heading]]
    elif heading == "v":
        hs = [DIRS[0], DIRS[2]]
    else:
        hs = [DIRS[3], DIRS[1]]
    return [(r, c, g[r][c], d) for r, c in cells for d in hs]


def _rot(d, t):
    return DIRS[(DIRS.index(d) + t) % 4]


def _walk(G, occ, bg, H, W, ag, P, chg):
    """One walker. Returns [(r, c, role, tint)] and hit cells. chg: changed-cell mask (None = no check)."""
    r, c, col, d0 = ag
    rule, chir, edge, gap = P["rule"], P["chir"], P["edge"], P["gap"]
    if chir in ("cw", "open"):
        t = 1
    elif chir == "ccw":
        t = -1
    else:
        t = 1 if ((r + c) % 2 == 0) == (chir == "par0") else -1
    trail = [[r, c, "start", col]]
    hits = []
    paint_occ = P["occ"] != "in"
    if paint_occ:
        occ[r][c] = True

    def state(y, x, d):
        ny, nx = y + d[0], x + d[1]
        if not (0 <= ny < H and 0 <= nx < W):
            return "edge"
        if occ[ny][nx]:
            return "obst"
        if gap == 1:
            ay, ax = ny + d[0], nx + d[1]
            if 0 <= ay < H and 0 <= ax < W and occ[ay][ax]:
                return "gap"
        return "free"

    def mark(role):
        e = trail[-1]
        if PRIO[role] >= PRIO[e[2]]:
            e[2] = role

    def move(d, tint):
        y, x = trail[-1][0] + d[0], trail[-1][1] + d[1]
        if chg is not None and not chg[y][x]:
            raise _Abort
        trail.append([y, x, "line", tint])
        if paint_occ:
            occ[y][x] = True

    if rule == "reflect":
        dr, dc = d0
        tint = col
        seen = set()
        y, x = r + dr, c + dc
        while 0 <= y < H and 0 <= x < W and not occ[y][x] and (y, x, dr, dc) not in seen:
            seen.add((y, x, dr, dc))
            if chg is not None and not chg[y][x]:
                raise _Abort
            vw = 0 <= y + dr < H and occ[y + dr][x]
            hw = 0 <= x + dc < W and occ[y][x + dc]
            if vw or hw:
                if vw:
                    tint = G[y + dr][x]
                    dr = -dr
                if hw:
                    tint = G[y][x + dc]
                    dc = -dc
                role = "turn"
            elif 0 <= y + dr < H and 0 <= x + dc < W and occ[y + dr][x + dc]:
                tint = G[y + dr][x + dc]
                dr, dc = -dr, -dc
                role = "turn"
            else:
                role = "line"
            trail.append([y, x, role, tint])
            y, x = y + dr, x + dc
        if len(trail) > 1:
            mark("end")
        return trail, hits

    def opent(y, x):
        """Rotation toward the nearer end of the obstacle blocking heading d0 (None when undecided)."""
        ks = []
        for s in (1, -1):
            sd = _rot(d0, s)
            yy, xx, k = y, x, 0
            while True:
                if state(yy, xx, sd) != "free":
                    k = None
                    break
                yy, xx, k = yy + sd[0], xx + sd[1], k + 1
                f = state(yy, xx, d0)
                if f == "free" or (f == "edge" and edge == "exit"):
                    break
            ks.append(k)
        a, b = ks
        if a is not None and (b is None or a < b):
            return 1
        if b is not None and (a is None or b < a):
            return -1
        return None

    cur, last = d0, None
    side = _rot(d0, t)
    seen = set()
    for _ in range(4 * H * W + 4):
        y, x = trail[-1][0], trail[-1][1]
        key = (y, x, cur, last)
        if key in seen:
            break
        seen.add(key)
        if rule == "block":
            s = state(y, x, cur)
            if s == "free":
                move(cur, col)
                last = cur
                continue
            if s == "edge" and edge == "exit":
                break
            nd = _rot(cur, t)
            if state(y, x, nd) != "free":
                break
            mark("turn")
            if s == "obst":
                hits.append((y + cur[0], x + cur[1]))
            cur = nd
            move(cur, col)
            last = cur
            continue
        s0 = state(y, x, d0)
        if rule == "stair" and last == d0:
            if state(y, x, side) != "free":
                break
            move(side, col)
            last = side
            continue
        if s0 == "free":
            if last is not None and last != d0 and rule == "bug":
                mark("resume")
            cur = d0
            move(d0, col)
            last = d0
            continue
        if s0 == "edge" and edge == "exit":
            break
        if chir == "open" and last != side:
            t = opent(y, x)
            if t is None:
                break
            side = _rot(d0, t)
        if state(y, x, side) != "free":
            break
        if last != side:
            mark("turn")
            if s0 == "obst":
                hits.append((y + d0[0], x + d0[1]))
        cur = side
        move(side, col)
        last = side
    if len(trail) > 1:
        mark("end")
    return trail, hits


def _dilate(mask, m, H, W):
    """Chebyshev dilation of a boolean mask by radius m (separable max filter)."""
    rows = []
    for row in mask:
        idx = [c for c in range(W) if row[c]]
        nr = [False] * W
        for c in idx:
            for x in range(max(0, c - m), min(W, c + m + 1)):
                nr[x] = True
        rows.append(nr)
    out = [[False] * W for _ in range(H)]
    for c in range(W):
        for r in range(H):
            if rows[r][c]:
                for y in range(max(0, r - m), min(H, r + m + 1)):
                    out[y][c] = True
    return out


def _marks(G, bg, ags, K):
    """Obstacles grown by their own count of K cells. Returns (occupancy, [(r, c, host colour)]) or None."""
    H, W = len(G), len(G[0])
    agc = {(a[0], a[1]) for a in ags}
    seen = [[False] * W for _ in range(H)]
    byrad = {}
    marks = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or G[r][c] == bg or (r, c) in agc:
                continue
            seen[r][c] = True
            stack, comp = [(r, c)], []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in DIRS:
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and G[ny][nx] != bg
                            and (ny, nx) not in agc):
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            mk = [(y, x) for y, x in comp if G[y][x] == K]
            m = len(mk)
            if m > max(H, W):
                return None
            host = Counter(G[y][x] for y, x in comp if G[y][x] != K)
            hc = max(sorted(host), key=lambda k: host[k]) if host else None
            marks.extend((y, x, hc) for y, x in mk)
            byrad.setdefault(m, []).extend(comp)
    if not marks:
        return None
    occ = [[False] * W for _ in range(H)]
    for m, cells in byrad.items():
        mask = [[False] * W for _ in range(H)]
        for y, x in cells:
            mask[y][x] = True
        if m:
            mask = _dilate(mask, m, H, W)
        for y in range(H):
            orow, mrow = occ[y], mask[y]
            for x in range(W):
                if mrow[x]:
                    orow[x] = True
    for y, x in agc:
        occ[y][x] = True
    return occ, marks


def _run(G, P, chg=None, ctx=None, rc=None):
    """All walkers on grid G. Returns (bg, records) with records = [(r, c, role, agent colour, tint)] in paint
    order, or None when the selector does not apply. ctx caches per-grid work (bg, occupancy, agents)."""
    H, W = len(G), len(G[0])
    if ctx is None:
        ctx = {}
    if "bg" not in ctx:
        ctx["bg"] = _bg(G)
        ctx["occ"] = [[v != ctx["bg"] for v in row] for row in G]
    bg = ctx["bg"]
    key = (P["who"], P["heading"])
    if key not in ctx:
        ctx[key] = _agents(G, bg, P["who"], P["heading"], rc)
    ags = ctx[key]
    if not ags or len(ags) > MAXW:
        return None
    gap = P["gap"]
    marks = []
    base = ctx["occ"]
    if isinstance(gap, tuple):
        mkey = (gap, frozenset((a[0], a[1]) for a in ags))     # depends on the agent cells, not headings
        if mkey not in ctx:
            K = _rcol(G, gap[1], rc or {}, bg)
            ctx[mkey] = None if K is None or K == bg else _marks(G, bg, ags, K)
        if ctx[mkey] is None:
            return None
        base, marks = ctx[mkey]
    if P["occ"] == "rev":
        ags = ags[::-1]
    occ = base if P["occ"] == "in" else [row[:] for row in base]
    recs = []
    for ag in ags:
        trail, hits = _walk(G, occ, bg, H, W, ag, P, chg)
        bud = ctx.get("budget")
        if bud is not None:
            bud[0] -= len(trail)
            if bud[0] < 0:
                raise _Budget
        for y, x, role, tint in trail:
            recs.append((y, x, role, ag[2], tint))
        for y, x in hits:
            recs.append((y, x, "hit", ag[2], G[y][x]))
    for y, x, hc in marks:
        recs.append((y, x, "mark", None, hc))
    return bg, recs


def _value(v, agent, tint, cols):
    kind, cr = v
    if kind == "agent":
        return agent
    if kind == "tint":
        return tint
    return cols.get(cr)                       # ("role", colour role) resolved on this grid


def _render(G, recs, vals, cols):
    out = [row[:] for row in G]
    for y, x, role, agent, tint in recs:
        v = vals.get(role)
        if v is None or v[0] == "keep":
            continue
        k = _value(v, agent, tint, cols)
        if k is None:
            return None
        out[y][x] = k
    return out


def _prep(train, rc):
    out = []
    for p in train:
        G, O = [list(r) for r in p["input"]], p["output"]
        chg = [[a != b for a, b in zip(ra, rb)] for ra, rb in zip(G, O)]
        out.append((G, O, chg, {"cols": _ccols(G, rc)}))
    return out


def _induce(prep, P, rc):
    """Event role -> colour value map consistent with every pair (last writer per cell), or None.  A value is
    keep | agent | tint | ("role", colour role) -- the colour role must name the output colour in every pair."""
    gap = P["gap"]
    if isinstance(gap, tuple):                # fast rejection: marks are repainted (observed binding)
        for G, O, chg, ctx in prep:
            key = ("mchg", gap[1])
            if key not in ctx:
                K = _rcol(G, gap[1], rc)
                ctx[key] = K is not None and all(chg[r][c] for r in range(len(G)) for c in range(len(G[0]))
                                                 if G[r][c] == K)
            if not ctx[key]:
                return None
    opts = {}                                 # role -> [keep ok, agent ok, tint ok, consistent colour roles]
    for G, O, chg, ctx in prep:
        cols = ctx["cols"]
        try:
            res = _run(G, P, chg, ctx, rc)
        except _Abort:
            return None
        if res is None:
            return None
        bg, recs = res
        last = {}
        for rec in recs:
            last[(rec[0], rec[1])] = rec
        for (y, x), (_, _, role, agent, tint) in last.items():
            o = O[y][x]
            st = opts.get(role)
            if st is None:
                st = opts[role] = [True, True, True, [r for r in CROLES if cols[r] is not None]]
            st[0] = st[0] and o == G[y][x]
            st[1] = st[1] and o == agent
            st[2] = st[2] and o == tint
            if st[3]:
                st[3] = [r for r in st[3] if cols[r] == o]
        for st in opts.values():                # early rejection after every pair
            if not (st[0] or st[1] or st[2] or st[3]):
                return None
    vals = {}
    for role, st in opts.items():
        if st[0]:
            vals[role] = ("keep", None)
        elif st[1]:
            vals[role] = ("agent", None)
        elif st[2]:
            vals[role] = ("tint", None)
        else:
            vals[role] = ("role", st[3][0])     # first consistent colour role in CROLES order
    return vals


def _make(P, vals, rc):
    def fn(grid):
        G = [list(r) for r in grid]
        try:
            res = _run(G, P, None, None, rc)
        except _Abort:
            return None
        if res is None:
            return None
        return _render(G, res[1], vals, _ccols(G, rc, res[0]))
    return fn


def _settings(train, rc):
    """Parameter grid with costs; role-bound values (who=rare, heading=edge, chir=open, gap=marks:K) cost less
    than (or as much as) the other values.  Seed / mark colour K is a role (G68): CR.rank_colour(g, k) or the
    single vanishing colour, offered when it names a non-background colour in every training input; a role naming
    the same colours as an earlier one in every training input is the same option (the first is kept)."""
    kroles, sigs, ksig = [], set(), {}
    for role in KROLES:
        sig = []
        for p in train:
            g = p["input"]
            bg = _bg(g)
            K = _rcol(g, role, rc, bg)
            sig.append(None if K == bg else K)
        sig = tuple(sig)
        if None in sig or sig in sigs:
            continue
        sigs.add(sig)
        kroles.append(role)
        ksig[role] = sig
    whos = ["corner", "all", "rare"] + kroles + ["elbow"]
    gaps = [0, 1] + [("marks", k) for k in kroles]
    out = []
    for wi, who in enumerate(whos):
        if who == "elbow":
            out.append((20, dict(who=who, heading="out", rule="reflect", chir="cw", edge="exit", gap=0, occ="in")))
            continue
        wc = 1 if isinstance(who, tuple) else 0
        for heading in ("edge", 0, 1, 2, 3, "v", "h"):
            if who == "corner" and not isinstance(heading, int):
                continue
            hc = 0 if heading == "edge" else (1 if isinstance(heading, int) else 2)
            for ri, rule in enumerate(("block", "bug", "stair")):
                for chir in ("cw", "ccw", "par0", "par1", "open"):
                    if chir == "open" and rule != "bug":
                        continue
                    cc = 2 if chir in ("par0", "par1") else (1 if chir == "open" else 0)
                    for ei, edge in enumerate(("wall", "exit")):
                        for gap in gaps:
                            if isinstance(gap, tuple):
                                if gap[1] == who or rule == "stair" or chir in ("par0", "par1"):
                                    continue
                                gc, occs = 1, ("in",)
                            else:
                                gc, occs = gap, ("in", "out", "rev")
                            for oi, occ in enumerate(occs):
                                cost = 10 + ri + cc + ei + gc + oi + hc + wc
                                out.append((cost, dict(who=who, heading=heading, rule=rule, chir=chir, edge=edge,
                                                       gap=gap, occ=occ)))
    out.sort(key=lambda s: s[0])
    return out


def fam(train):
    if not train:
        return
    for p in train:
        a, b = p["input"], p["output"]
        if not a or not a[0] or len(a) != len(b) or len(a[0]) != len(b[0]):
            return
        if a == b:
            return
    found = 0
    rc = _consts(train)
    prep = _prep(train, rc)
    budget = [BUDGET]
    for item in prep:
        item[3]["budget"] = budget
    for cost, P in _settings(train, rc):
        try:
            vals = _induce(prep, P, rc)
        except _Budget:
            return
        if vals is None:
            continue
        fn = _make(P, vals, rc)
        ok = True
        for G, O, chg, ctx in prep:            # verify on the cached per-grid context (no step check)
            try:
                res = _run(G, P, None, ctx, rc)
            except _Budget:
                return
            except Exception:
                res = None
            if res is None or _render(G, res[1], vals, ctx["cols"]) != O:
                ok = False
                break
        if not ok:
            continue
        sig = tuple(sorted(vals.items(), key=lambda kv: kv[0]))
        def pv(v):
            if isinstance(v, tuple) and v[0] == "marks":
                return "marks:" + _rname(v[1])
            if isinstance(v, tuple):
                return _rname(v)
            return v
        name = "walk[%s,roles=%s]" % (",".join("%s=%s" % (k, pv(v)) for k, v in P.items()),
                                       ",".join("%s:%s" % (k, v[0] if v[0] != "role" else _rname(v[1]))
                                                for k, v in sig))
        yield name, cost, fn
        found += 1
        if found >= 3:
            return


FAMILIES = [fam]
