"""Prior family "turtle_path_walk" (test-blind; anti-unified from the member programs and their train pairs only).

One generator: agents (seed cells of an induced colour, every seed cell, the elbow cells of objects, or the grid
corner of a blank grid) set off with an initial heading and move one cell per step over a free board.  At each
step one pluggable turn rule picks the move:
  block  -- go straight; when blocked turn by the chirality (spiral / corridor runner), stop when still blocked;
  bug    -- prefer the home heading, else sidestep perpendicular to it (wall hugging, Bug-0), stop when both blocked;
  stair  -- alternate home step / sidestep (staircase), sidestepping early when the home step is blocked;
  reflect-- diagonal ray that bounces off every flat surface it touches (axis flip), reverses at a pointed corner.
Blocked = the next cell is off-grid (a wall, or an exit that ends the walk) or occupied (input objects, plus the
trails already drawn when occupancy is 'out'); gap=1 also keeps one free cell between the walker and occupied
cells.  Every trail cell gets an event role (start, line, turn, resume, hit = the obstacle that caused a turn,
end); each role's colour is induced from the training pairs as keep, the agent's colour, the tint (colour of
the last surface bounced off) or one literal colour.
Members it was fitted on: 28e73c20 (corner, block, gap 1), 69889d6e (stair), 7ec998c9 (both ways along the
column, bug, parity chirality), 891232d6 (bug with hit / turn / resume / end roles), 99fa7670 (bug, trails
block, bottom-up order), 142ca369 (reflect from elbows, tint).
"""
from collections import Counter

CARD = "prior_turtle_path_walk"
CONCEPT = "turtle_path_walk"
MEMBERS = ["142ca369", "28e73c20", "3490cc26", "3e6067c3", "5545f144", "69889d6e", "7ec998c9", "88bcf3b4",
           "891232d6", "8b28cd80", "97c75046", "992798f6", "99fa7670", "cb2d8a2c", "e6de6e8f", "e87109e9"]
READING = {
    "generator": "Agents (seed cells, object elbows or the corner of a blank grid) walk one cell per step from "
                 "an initial heading; a pluggable turn rule (turn by a chirality when blocked, prefer the home "
                 "heading else sidestep, alternate home step and sidestep, or bounce diagonally off surfaces) "
                 "picks each move, and every trail cell is painted with the colour induced for its event role "
                 "(start, line, turn, resume, hit obstacle, end) as keep, agent colour, bounce tint or a literal.",
    "stop": "A walker stops when its next step leaves the grid (edge=exit), when every move its rule allows is "
            "blocked (boxed in), or on a repeated state; the last cell gets the 'end' role.",
    "params": "who ∈ {corner of blank grid, all seed cells, cells of colour K (K present in every train input), "
              "elbows} · heading ∈ {up, right, down, left, both ways vertical, both ways horizontal, elbow "
              "outward} · rule ∈ {block, bug, stair, reflect} · chirality ∈ {cw, ccw, cw on even r+c, cw on odd "
              "r+c} · edge ∈ {wall, exit} · gap ∈ {0, 1} · occupancy/order ∈ {input only, input+trails in "
              "reading order, input+trails in reverse order} · role colour ∈ {keep, agent, tint, literal}",
    "participants": "Background = most frequent input colour; seeds = non-background cells (of colour K when "
                    "chosen); elbows = cells with exactly two perpendicular same-colour 4-neighbours, heading "
                    "diagonally away from both arms; obstacles = all other non-background cells.",
    "preconditions": "Input and output have the same size, some cell changes, every cell a walker moves onto "
                     "changes colour (checked step by step for fast rejection), at most 16 walkers, and one "
                     "consistent role-colour map reproduces every training pair.",
}

DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))          # clockwise: up, right, down, left
MAXW = 16
PRIO = {"line": 0, "turn": 1, "resume": 1, "end": 2, "start": 3}


def _bg(g):
    cnt = Counter(v for r in g for v in r)
    return max(sorted(cnt), key=lambda k: cnt[k])


class _Abort(Exception):
    pass


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


def _agents(g, bg, who, heading):
    """List of (r, c, colour, home heading (dr, dc)) or None when the selector does not apply."""
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
    if who != "all":
        cells = [(r, c) for r, c in cells if g[r][c] == who]
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
    if chir == "cw":
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
        if gap:
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

    cur, last = d0, None
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
        side = _rot(d0, t)
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


def _run(G, P, chg=None, ctx=None):
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
        ctx[key] = _agents(G, bg, P["who"], P["heading"])
    ags = ctx[key]
    if not ags or len(ags) > MAXW:
        return None
    if P["occ"] == "rev":
        ags = ags[::-1]
    occ = ctx["occ"] if P["occ"] == "in" else [row[:] for row in ctx["occ"]]
    recs = []
    for ag in ags:
        trail, hits = _walk(G, occ, bg, H, W, ag, P, chg)
        for y, x, role, tint in trail:
            recs.append((y, x, role, ag[2], tint))
        for y, x in hits:
            recs.append((y, x, "hit", ag[2], G[y][x]))
    return bg, recs


def _value(v, agent, tint):
    kind, lit = v
    if kind == "agent":
        return agent
    if kind == "tint":
        return tint
    return lit


def _render(G, recs, vals):
    out = [row[:] for row in G]
    for y, x, role, agent, tint in recs:
        v = vals.get(role)
        if v is None or v[0] == "keep":
            continue
        k = _value(v, agent, tint)
        if k is None:
            return None
        out[y][x] = k
    return out


def _prep(train):
    out = []
    for p in train:
        G, O = [list(r) for r in p["input"]], p["output"]
        chg = [[a != b for a, b in zip(ra, rb)] for ra, rb in zip(G, O)]
        out.append((G, O, chg, {}))
    return out


def _induce(prep, P):
    """Role -> colour value map consistent with every pair (last writer per cell), or None."""
    obs = {}
    for G, O, chg, ctx in prep:
        try:
            res = _run(G, P, chg, ctx)
        except _Abort:
            return None
        if res is None:
            return None
        bg, recs = res
        last = {}
        for rec in recs:
            last[(rec[0], rec[1])] = rec
        for (y, x), (_, _, role, agent, tint) in last.items():
            obs.setdefault(role, []).append((G[y][x], O[y][x], agent, tint))
    vals = {}
    for role, lst in obs.items():
        if all(o == i for i, o, a, t in lst):
            vals[role] = ("keep", None)
        elif all(o == a for i, o, a, t in lst):
            vals[role] = ("agent", None)
        elif all(o == t for i, o, a, t in lst):
            vals[role] = ("tint", None)
        elif len({o for i, o, a, t in lst}) == 1:
            vals[role] = ("lit", lst[0][1])
        else:
            return None
    return vals


def _make(P, vals):
    def fn(grid):
        G = [list(r) for r in grid]
        try:
            res = _run(G, P)
        except _Abort:
            return None
        if res is None:
            return None
        return _render(G, res[1], vals)
    return fn


def _settings(train):
    common = None
    for p in train:
        bg = _bg(p["input"])
        cs = {v for row in p["input"] for v in row} - {bg}
        common = cs if common is None else common & cs
    whos = ["corner", "all"] + sorted(common) + ["elbow"]
    out = []
    for wi, who in enumerate(whos):
        if who == "elbow":
            for occ in ("in",):
                out.append((20, dict(who=who, heading="out", rule="reflect", chir="cw", edge="exit", gap=0,
                                     occ=occ)))
            continue
        for hi, heading in enumerate((0, 1, 2, 3, "v", "h")):
            for ri, rule in enumerate(("block", "bug", "stair")):
                for ci, chir in enumerate(("cw", "ccw", "par0", "par1")):
                    for ei, edge in enumerate(("wall", "exit")):
                        for gap in (0, 1):
                            for oi, occ in enumerate(("in", "out", "rev")):
                                cost = 10 + ri + (2 if ci > 1 else 0) + ei + gap + oi + (hi > 3)
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
    prep = _prep(train)
    for cost, P in _settings(train):
        vals = _induce(prep, P)
        if vals is None:
            continue
        fn = _make(P, vals)
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = tuple(sorted(vals.items(), key=lambda kv: kv[0]))
        name = "walk[%s,roles=%s]" % (",".join("%s=%s" % kv for kv in P.items()),
                                       ",".join("%s:%s" % (k, v[0] if v[0] != "lit" else v[1]) for k, v in sig))
        yield name, cost, fn
        found += 1
        if found >= 3:
            return


FAMILIES = [fam]
