"""Concept family: rearrange (test-blind; anti-unified from the member lines' code and train pairs only).

One generator: split the grid into parts (cells, connected components, or solid full-line walls), view it along a
sweep axis, give every moving part a new position by one step rule, and redraw the parts unchanged on a canvas.
  step = abut   parts are taken in runs (top-to-bottom order cut into runs, each run left to right); inside a run
                each part is shifted so its start end sits edge to edge right after the previous part's finish end;
                a new run starts under the previous one at the first part's column.  Cells with runs of sqrt(n)
                pack a sparse shape into a square (ca8de6ea); components with one run chain into a path (d017b73f);
                cells with one run per input row slide together along rows.
  step = slot   each part jumps along the sweep by whole slots (its distance to the start edge plus its width) to the
                first empty landing place (dd2401ed's wall).
Static material (everything that is not a part, for the wall unit) stays; static cells a part passes over may take
the colour of the static cells behind the part, under an induced recolour condition.
"""
from math import isqrt

CARD = "concept_rearrange"
CONCEPT = "rearrange"
MEMBERS = ["ca8de6ea", "d017b73f", "dd2401ed"]
READING = {
    "generator": "Split the grid into parts (single cells, connected components, or solid full-line walls) and, along "
                 "the sweep axis, move each part without altering it: either abut it -- its start end placed edge to "
                 "edge right after the previous part's finish end, the parts taken in runs (top-to-bottom order cut "
                 "into runs, each run left to right, a new run starting under the previous one) -- or jump it by "
                 "whole slots (its distance to the start edge plus its width) to the first empty place; everything "
                 "else stays, and static cells a part passes over may take the colour of the static cells behind it.",
    "stop": "One pass over the parts in sweep order (abut: the gaps between consecutive parts vanish; slot: first "
            "landing place k x slot away, k = 1, 2, ..., that is empty); the canvas is the input size, the input's "
            "cross size with the parts' extent along the sweep, or the bounding box of the result, as induced.",
    "params": "unit ∈ {cell, comp4, line, comp8} · sweep ∈ {lr, in, rl, tb, bt} (in = per grid, towards the far "
              "side from the edge the parts are nearer to) · step ∈ {abut, slot} · wrap ∈ {none, row, sqrt} (abut "
              "runs: one run / one run per top row / runs of ceil(sqrt n)) · canvas ∈ {keep, compact, bbox} · "
              "recolour ∈ {never, always, past_middle, captured_majority} · bg = most frequent input colour",
    "participants": "Parts: every non-background cell (cell), the 4/8-connected non-background components (comp4, "
                    "comp8), or the maximal bands of identical full single-colour lines across the sweep (line; all "
                    "other non-background cells are static). Ends of a part: the two degree-1 cells of a simple path, "
                    "else the unique (or unique degree<=1) cell of its first / last line along the sweep. Recolour "
                    "target: the most common static colour behind the moving part (else the colour map read off the "
                    "training diffs).",
    "preconditions": "Each training input has parts under the unit (abut: at least two, with identifiable ends and "
                     "disjoint extents along the sweep inside every run, landing without overlap; slot: an empty "
                     "landing place inside the grid); the redrawn result fits the induced canvas.",
}

UNITS = (("cell", 0), ("comp4", 1), ("line", 1), ("comp8", 2))
SWEEPS = (("lr", 0), ("in", 0), ("rl", 1), ("tb", 1), ("bt", 2))
STEPS = (("abut", 0), ("slot", 1))
WRAPS = (("none", 0), ("row", 1), ("sqrt", 2))
CANVASES = (("keep", 0), ("compact", 1), ("bbox", 1))
RECOLOURS = (("never", 0), ("always", 1), ("past_middle", 2), ("captured_majority", 3))


# ---------------------------------------------------------------- frame: every sweep is normalised to left-to-right

def _T(g):
    return [list(r) for r in zip(*g)]


def _F(g):
    return [list(r[::-1]) for r in g]


_TF = {"lr": (lambda g: [list(r) for r in g], lambda g: g), "rl": (_F, _F), "tb": (_T, _T),
       "bt": (lambda g: _F(_T(g)), lambda g: _T(_F(g)))}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _nbrs(conn):
    return tuple((a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (conn == 8 or not (a and b)))


# ---------------------------------------------------------------- participants

def _parts(g, bg, unit):
    """(parts, static): parts are lists of (r, c) sorted row-major; static cells stay where they are."""
    H, W = len(g), len(g[0])
    if unit == "cell":
        return [[(r, c)] for r in range(H) for c in range(W) if g[r][c] != bg], []
    if unit == "line":
        full = [g[0][c] if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(H)) else None for c in range(W)]
        parts, c = [], 0
        while c < W:
            e = c
            if full[c] is not None:
                while e + 1 < W and full[e + 1] == full[c]:
                    e += 1
                parts.append([(r, x) for r in range(H) for x in range(c, e + 1)])
            c = e + 1
        own = {p for cs in parts for p in cs}
        return parts, [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg and (r, c) not in own]
    N, seen, parts = _nbrs(int(unit[-1])), set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            seen.add((r, c))
            st, cs = [(r, c)], []
            while st:
                a, b = st.pop()
                cs.append((a, b))
                for dr, dc in N:
                    q = (a + dr, b + dc)
                    if 0 <= q[0] < H and 0 <= q[1] < W and q not in seen and g[q[0]][q[1]] != bg:
                        seen.add(q)
                        st.append(q)
            parts.append(sorted(cs))
    return parts, []


def _ends(cs, conn):
    """(start, finish) options in preference order; [] when the ends cannot be identified."""
    S = set(cs)
    if len(S) == 1:
        return [(cs[0], cs[0])]
    N = _nbrs(conn)
    deg = {p: sum((p[0] + a, p[1] + b) in S for a, b in N) for p in S}
    ep = sorted(p for p in S if deg[p] == 1)
    if len(ep) == 2 and all(deg[p] == 2 for p in S if p not in ep):            # simple path
        a, b = ep
        return [(a, b)] if a[1] < b[1] else [(b, a)] if b[1] < a[1] else [(a, b), (b, a)]

    def pick(col):
        L = sorted(p for p in S if p[1] == col)
        L1 = [p for p in L if deg[p] <= 1]
        return L[0] if len(L) == 1 else L1[0] if len(L1) == 1 else None

    s, f = pick(min(c for _, c in S)), pick(max(c for _, c in S))
    return [] if s is None or f is None else [(s, f)]


# ---------------------------------------------------------------- step rules -> list of (part, dr, dc)

def _cmin(cs):
    return min(c for _, c in cs)


def _cmax(cs):
    return max(c for _, c in cs)


def _abut(parts, wrap, conn):
    P = sorted(parts, key=lambda cs: cs[0])                                    # top-to-bottom order
    if len(P) < 2:
        raise ValueError("fewer than two parts")
    if wrap == "none":
        runs = [P]
    elif wrap == "sqrt":
        s = isqrt(len(P))
        s += s * s < len(P)
        runs = [P[i:i + s] for i in range(0, len(P), s)]
    else:                                                                     # one run per top row
        runs = []
        for cs in P:
            if runs and runs[-1][0][0][0] == cs[0][0]:
                runs[-1].append(cs)
            else:
                runs.append([cs])
    moves, occ, c0, nxt = [], set(), 0, 0
    for ri, run in enumerate(runs):
        run = sorted(run, key=lambda cs: (_cmin(cs), cs[0][0]))                # each run left to right
        if any(_cmax(a) >= _cmin(b) for a, b in zip(run, run[1:])):
            raise ValueError("extents overlap along the sweep")
        fin = None
        for cs in run:
            opts = _ends(cs, conn)
            if not opts:
                raise ValueError("ends not identifiable")
            if fin is None:                                                   # run head
                s, f = opts[0]
                if ri == 0:
                    dr, dc, c0 = 0, 0, _cmin(cs)
                else:
                    dr, dc = nxt - cs[0][0], c0 - _cmin(cs)
            else:
                s, f = min(opts, key=lambda o: (abs(fin[0] - o[0][0]), o[0][0]))
                dr, dc = fin[0] - s[0], fin[1] + 1 - s[1]
            for r, c in cs:
                if (r + dr, c + dc) in occ:
                    raise ValueError("overlap")
                occ.add((r + dr, c + dc))
            moves.append((cs, dr, dc))
            fin = (f[0] + dr, f[1] + dc)
        nxt = max(r for r, _ in occ) + 1
    return moves


def _slot(parts, static, W):
    occ = set(static) | {p for cs in parts for p in cs}
    moves = []
    for cs in sorted(parts, key=lambda cs: (_cmin(cs), cs[0])):
        x = _cmin(cs)
        w = _cmax(cs) - x + 1
        k, d = 1, None
        while x + k * (x + w) + w <= W:
            if all((r, c + k * (x + w)) not in occ for r, c in cs):
                d = k * (x + w)
                break
            k += 1
        if d is None:
            raise ValueError("no empty slot")
        occ.difference_update(cs)
        occ.update((r, c + d) for r, c in cs)
        moves.append((cs, 0, d))
    return moves


# ---------------------------------------------------------------- passed-over static cells (any step)

def _events(g, bg, moves, static):
    """Per moved part: ([(cell, colour-or-None)], past_middle, captured_majority) over the static cells it passed."""
    W, st, ev = len(g[0]), set(static), []
    for cs, dr, dc in moves:
        if not dc or not st:
            continue
        x, w = _cmin(cs), _cmax(cs) - _cmin(cs) + 1
        nx, rows, own = x + dc, {r for r, _ in cs}, {g[r][c] for r, c in cs}
        lo, hi = (x + w, nx) if dc > 0 else (nx + w, x)
        behind = (lambda c: c < x) if dc > 0 else (lambda c: c >= x + w)
        ahead = (lambda c: c >= nx + w) if dc > 0 else (lambda c: c < nx)
        cnt = {}
        for r, c in static:
            if behind(c) and g[r][c] not in own:
                cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
        tgt = max(sorted(cnt), key=lambda k: cnt[k]) if cnt else None
        cap = [((r, c), tgt) for r, c in sorted(st) if r in rows and lo <= c < hi and g[r][c] != tgt]
        if not cap:
            continue
        cols = {g[r][c] for (r, c), _ in cap}
        left = sum(1 for r, c in static if ahead(c) and g[r][c] in cols)
        past = (2 * nx + w - 1 > W - 1) if dc > 0 else (2 * nx + w - 1 < W - 1)
        ev.append((cap, past, len(cap) > left))
    return ev


# ---------------------------------------------------------------- the whole program: place, recolour, draw

def _place(grid, unit, sweep, step, wrap):
    """Mode-independent part of the program: (g, bg, inverse frame, moves, static, events)."""
    tfs = [sweep] if sweep != "in" else ["lr", "rl", "tb", "bt"]
    for t in tfs:
        fwd, inv = _TF[t]
        g = fwd(grid)
        bg = _bg(g)
        parts, static = _parts(g, bg, unit)
        if not parts:
            continue
        if sweep == "in" and min(_cmin(cs) for cs in parts) + max(_cmax(cs) for cs in parts) >= len(g[0]) - 1:
            continue                                                          # parts not nearer the start edge
        conn = 8 if unit == "comp8" else 4
        moves = _abut(parts, wrap, conn) if step == "abut" else _slot(parts, static, len(g[0]))
        return g, bg, inv, moves, static, _events(g, bg, moves, static)
    raise ValueError("no parts")


def _fit_axis(lo, hi, n):
    if n is None:
        return lo, hi - lo + 1
    off = lo if lo < 0 else hi - n + 1 if hi >= n else 0
    if hi - off >= n or lo - off < 0:
        raise ValueError("does not fit the canvas")
    return off, n


def _draw(placed, recolour, canvas, cmap):
    g, bg, inv, moves, static, events = placed
    cells = {(r, c): g[r][c] for r, c in static}
    for cs, dr, dc in moves:
        for r, c in cs:
            if (r + dr, c + dc) in cells:
                raise ValueError("overlap")
            cells[(r + dr, c + dc)] = g[r][c]
    for cap, past, major in events:
        if recolour == "always" or (recolour == "past_middle" and past) or (recolour == "captured_majority" and major):
            for p, t in cap:
                v = t if t is not None else cmap.get(cells[p])
                if v is not None:
                    cells[p] = v
    rows, cols = [r for r, _ in cells], [c for _, c in cells]
    H, W = len(g), len(g[0])
    r0, oh = _fit_axis(min(rows), max(rows), None if canvas == "bbox" else H)
    c0, ow = _fit_axis(min(cols), max(cols), W if canvas == "keep" else None)
    out = [[bg] * ow for _ in range(oh)]
    for (r, c), v in cells.items():
        out[r - r0][c - c0] = v
    return inv(out)


def _program(unit, sweep, step, wrap, canvas, recolour, cmap):
    def fn(grid):
        return _draw(_place(grid, unit, sweep, step, wrap), recolour, canvas, cmap)
    return fn


def _diff_map(train):
    """Consistent non-background -> non-background colour map over changed cells of same-shape pairs, else {}."""
    m = {}
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return {}
        bg = _bg(a)
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y and bg not in (x, y):
                    if m.setdefault(x, y) != y:
                        return {}
    return m


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs or any(not i or not i[0] or not o or not o[0] for i, o in pairs):
        return
    if any(all(v == _bg(i) for r in i for v in r) for i, _ in pairs):
        return                                                                # nothing to rearrange
    cmap, found = _diff_map(train), []
    for unit, cu in UNITS:
        for sweep, cs_ in SWEEPS:
            for step, ct in STEPS:
                for wrap, cw in (WRAPS if step == "abut" else WRAPS[:1]):
                    try:
                        placed = [_place(i, unit, sweep, step, wrap) for i, _ in pairs]
                    except Exception:
                        continue
                    captures = any(pl[5] for pl in placed)
                    for canvas, cc in CANVASES:
                        for recolour, cr in (RECOLOURS if captures else RECOLOURS[:1]):
                            try:
                                ok = all(_draw(pl, recolour, canvas, cmap) == o for pl, (_, o) in zip(placed, pairs))
                            except Exception:
                                ok = False
                            if ok:
                                cost = 10 + cu + cs_ + ct + cw + cc + cr
                                name = "rearrange[unit=%s,sweep=%s,step=%s,wrap=%s,canvas=%s,recolour=%s]" % (
                                    unit, sweep, step, wrap, canvas, recolour)
                                found.append((cost, name, _program(unit, sweep, step, wrap, canvas, recolour, cmap)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, name, fn in found:
        yield name, cost, fn


FAMILIES = [fam]
