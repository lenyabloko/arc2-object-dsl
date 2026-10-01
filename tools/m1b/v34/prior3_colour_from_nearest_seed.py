"""Prior family v3: colour_from_nearest_seed  (RECOLOUR targets by the colour of their seed), specialised over
FITTED BINDINGS (Fable v10b T65 / G68).

One generator: pick the TARGET cells (cells of a target colour, optionally only interior / lone ones) and the
SEEDS (every other non-background cell, optionally without the wall colour); cut the grid into DOMAINS
(the whole canvas, the non-background structure a target belongs to, or the room of background+target cells
it lies in); inside each domain give the targets the colour of
    vote   : the plurality colour of the seeds contained in / touching the domain        (one colour per domain)
    cell   : the colour of the nearest seed of the domain, per target cell  (Voronoi; lattice or in-domain BFS)
    object : the colour of the nearest seed, per 8-connected target object (min distance over its cells)
Several colours at the minimum distance (or a plurality tie) is a TIE: the target keeps its colour or takes a
designated tie colour X.  Afterwards the seeds (or everything not painted) may be erased, and the painted target
objects may be cropped and lined up (pack) instead of being left in place.

Parameters (small finite domains, induced from the training pairs only; no stored sizes/coordinates):
    tc      in {constant colour c, dom (most frequent non-bg colour), bg}       the target colour
    shape   in {all, interior (8 neighbours non-bg), lone (no non-bg 8-neighbour), lone4 (no non-bg 4-neighbour),
                enclosed (its same-colour 4-component misses the border, e.g. holes)}
    excl    in {0, 1}   1 = the wall colour (most frequent seed colour) is not a seed
    domain  in {comp4, comp8 (components of non-bg cells; seeds inside), room (4-components of bg+target
                cells; seeds 8-adjacent), global (whole grid; all seeds)}
    unit    in {vote, cell, object}       metric in {manh, cheb (lattice distance), geo (4-step BFS inside the domain)}
    tie     in {keep, X}  (X read off the training outputs)
    post    in {none, seeds (erase seeds), all (erase every unpainted non-bg cell)}
    out     in {grid, pack (crop each target object, concatenate along the axis the objects are laid out),
                dock (move the target piece into the enclosed background room of its own bbox size, paint it
                there with domain = that room, crop the room plus its one-cell wall ring)}
    sym     in {none, point (the seeds are completed by their images under the half-turn about the centre of
                the domain's target bbox; a real seed wins over an image)}
Background = most frequent colour of the grid.

BINDINGS  (G68 table: every induced value of the v2 fit of each fitted member, with the ROLE that explains it;
           "literal" = no input role explains the value)
  09c534e7  tc = 1      <- dom (the structure colour = most frequent non-bg colour, every pair)
            shape       <- interior (target = structure cells whose 8 neighbours are all non-bg)
            seeds       <- the odd-colour marker cells inside a structure ; excl = 0
            domain      <- comp4 (the 4-connected non-bg structure the marker lies in)
            colour      <- vote = the structure's marker colour ; tie keep ; post none ; out grid
  50aad11f  tc = 6      <- dom (the shape colour = most frequent non-bg colour)
            seeds       <- lone marker cells of other colours ; domain room (the whole background)
            colour      <- object: nearest marker of each 8-connected shape (metric manh) ; tie keep
            out         <- pack: crop each shape, concatenate along the axis the shapes are laid out on
  e681b708  tc = 1      <- dom (the grid-line colour; the lone4 dots of that colour are the targets)
            shape       <- lone4 ; domain <- room (4-component of bg + dots cut by the grid lines)
            seeds       <- the coloured line ends / crossings touching the room
            colour      <- vote = plurality marker colour on the room's rim ; tie keep ; post none
  e9ac8c9e  tc = 5      <- dom (the block colour)
            seeds       <- the corner marker cells diagonal to the block ; domain comp8 (block + corners)
            colour      <- cell: nearest corner marker (metric manh; quadrants) ; tie keep
            post        <- seeds (markers erased)
  Literal -> role: the four target colours were literals in v2 (const preferred); each is explained by
  the role 'dom', so 'dom' (then 'bg') now comes first and a constant target colour is only the fallback.
  Every tie in the fitted members is 'keep' (the target's own colour); the literal tie colour X stays the
  fallback, no new tie roles were invented.
  Role-bound alternatives added (specialisation menu from bindings observed in the unfitted members'
  training pairs, each a shared step, no task constants):
    94414823  tc <- bg, shape <- enclosed (the frame's hole), seeds <- markers outside the frame,
              excl <- wall = frame colour (most frequent seed colour), unit cell (quadrants as in e9ac8c9e),
              sym <- point: a quadrant's seed <- the marker diagonally opposite (half-turn image about the
              hole's centre); same corner-marker -> quadrant binding as e9ac8c9e with the seed set completed.
    9aec4887  tc <- dom (the loose piece), seeds <- the four bars around a hole, unit cell (nearest bar),
              tie keep, position <- dock (the enclosed room of the piece's bbox size), output frame <- the room
              plus its wall ring (the crop role of 50aad11f's pack, applied to the room instead of the piece).
  Not reached (need a step outside this generator): 21897d95 (flood fill from nozzles + turn arrow),
  332202d5 (row-distance fill plus a swap of the line / crossing colours), 88207623 (mirror image of a shape
  across an axis, coloured by the marker on the far side).
"""
from collections import Counter
import time

CARD = "prior3_colour_from_nearest_seed"
CONCEPT = "colour_from_nearest_seed"
MEMBERS = ['09c534e7', '21897d95', '332202d5', '50aad11f', '88207623', '94414823', '9aec4887', 'e681b708',
           'e9ac8c9e']
READING = {
    "generator": "cut the grid into domains (whole canvas, non-bg structure, or room of bg+target cells) and "
                 "recolour the target cells of each domain with the colour of its seed: plurality of the seeds "
                 "inside/touching the domain, or the nearest seed (BFS Manhattan/Chebyshev distance inside the "
                 "domain) per target cell or per target object; ties keep their colour or take a tie colour; "
                 "the seed set may be completed by its half-turn image about the target centre, and the target "
                 "piece may first be docked into the enclosed room of its size (output = that room + wall)",
    "stop": "every target of a domain that has a seed is painted; BFS stops at the domain border; targets "
            "with no reachable seed stay unchanged",
    "params": "tc in {dom, bg, const c (fallback)} . shape in {all, interior, lone, lone4, enclosed} . "
              "excl in {0,1} . domain in {comp4, comp8, room, global} . unit in {vote, cell, object} . "
              "metric in {manh, cheb, geo} . sym in {none, point} . tie in {keep, X} . "
              "post in {none, seeds, all} . out in {grid, pack, dock}",
    "participants": "background = most frequent colour; targets = cells of the target colour passing the shape "
                    "test; seeds = other non-bg cells (minus the wall colour if excl); domains = 4/8-components "
                    "of non-bg cells, 4-components of bg+target cells, or the whole grid; target objects = "
                    "8-components of target cells",
    "preconditions": "grid mode: same in/out size, every painted cell had one input colour per pair (the target "
                     "colour), every other changed cell was erased to bg; pack mode: smaller output, target "
                     "colour absent from the outputs; dock mode: smaller output = an enclosed bg room of the "
                     "target piece's bbox size plus its wall ring",
    "bindings": "tc <- dom (all four fitted members) ; seeds <- marker cells ; wall <- most frequent seed colour ; "
                "sym point: quadrant seed <- diagonally opposite marker (centre <- target bbox centre) ; "
                "dock: piece position <- enclosed room of equal bbox size, output <- room + wall ring",
}

_N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
_N8 = _N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
_BUDGET = 0.7
_SHAPES = ('all', 'interior', 'lone', 'lone4', 'enclosed')
_DOMAINS = ('comp4', 'comp8', 'room', 'global')
_UNITS = (('vote', None), ('cell', 'manh'), ('cell', 'cheb'), ('cell', 'geo'),
          ('object', 'manh'), ('object', 'cheb'), ('object', 'geo'))


# ----------------------------------------------------------------------------------------- participants
def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _resolve_tc(g, bg, mode):
    if mode == 'bg':
        return bg
    if mode == 'dom':
        c = Counter(v for r in g for v in r if v != bg)
        return c.most_common(1)[0][0] if c else None
    return mode


def _border_linked(g, H, W, col):
    """Cells of colour col 4-connected (through col) to the grid border."""
    st = [(i, j) for i in range(H) for j in range(W)
          if (i in (0, H - 1) or j in (0, W - 1)) and g[i][j] == col]
    seen = set(st)
    while st:
        a, b = st.pop()
        for da, db in _N4:
            x, y = a + da, b + db
            if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == col:
                seen.add((x, y))
                st.append((x, y))
    return seen


def _shape_ok(g, H, W, bg, i, j, shape, linked=None):
    if shape == 'all':
        return True
    if shape == 'enclosed':
        return (i, j) not in linked
    if shape == 'interior':
        for di, dj in _N8:
            x, y = i + di, j + dj
            if not (0 <= x < H and 0 <= y < W) or g[x][y] == bg:
                return False
        return True
    nb = _N8 if shape == 'lone' else _N4
    for di, dj in nb:
        x, y = i + di, j + dj
        if 0 <= x < H and 0 <= y < W and g[x][y] != bg:
            return False
    return True


def _participants(g, tcmode, shape, excl, cache):
    key = ('P', tcmode, shape, excl)
    if key in cache:
        return cache[key]
    H, W = len(g), len(g[0])
    bg = cache['bg']
    res = None
    tcol = _resolve_tc(g, bg, tcmode)
    if tcol is not None and not (tcol == bg and shape not in ('all', 'enclosed')):
        linked = _border_linked(g, H, W, tcol) if shape == 'enclosed' else None
        T = [(i, j) for i in range(H) for j in range(W)
             if g[i][j] == tcol and _shape_ok(g, H, W, bg, i, j, shape, linked)]
        S = [((i, j), g[i][j]) for i in range(H) for j in range(W) if g[i][j] != bg and g[i][j] != tcol]
        if excl:
            sc = Counter(c for _, c in S)
            if len(sc) >= 2:
                wall = sc.most_common(1)[0][0]
                S = [s for s in S if s[1] != wall]
            else:
                S = None
        if T and S:
            res = (tcol, T, S)
    cache[key] = res
    return res


def _components(cells, nb):
    """Connected components of a set of cells (deterministic order)."""
    seen = set()
    out = []
    for c in sorted(cells):
        if c in seen:
            continue
        seen.add(c)
        st, comp = [c], []
        while st:
            a, b = st.pop()
            comp.append((a, b))
            for da, db in nb:
                q = (a + da, b + db)
                if q in cells and q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(comp)
    return out


def _domains(g, tcmode, shape, excl, domain, cache):
    """List of (targets in domain, seeds of domain, passable cell set or None)."""
    key = ('D', tcmode, shape, excl, domain)
    if key in cache:
        return cache[key]
    part = _participants(g, tcmode, shape, excl, cache)
    res = None
    if part is not None:
        tcol, T, S = part
        H, W = len(g), len(g[0])
        bg = cache['bg']
        if domain == 'global':
            res = [(T, S, None)]
        elif domain in ('comp4', 'comp8'):
            if tcol != bg:
                nb = _N4 if domain == 'comp4' else _N8
                cells = {(i, j) for i in range(H) for j in range(W) if g[i][j] != bg}
                Tset = set(T)
                seedcol = dict(S)
                res = []
                for comp in _components(cells, nb):
                    Td = [c for c in comp if c in Tset]
                    if not Td:
                        continue
                    Sd = [(c, seedcol[c]) for c in comp if c in seedcol]
                    res.append((Td, Sd, set(comp)))
        else:  # room
            Tset = set(T)
            cells = {(i, j) for i in range(H) for j in range(W) if g[i][j] == bg or (i, j) in Tset}
            seedcol = dict(S)
            res = []
            for comp in _components(cells, _N4):
                Td = [c for c in comp if c in Tset]
                if not Td:
                    continue
                touch = set()
                for a, b in comp:
                    for da, db in _N8:
                        q = (a + da, b + db)
                        if q in seedcol:
                            touch.add(q)
                Sd = [(q, seedcol[q]) for q in sorted(touch)]
                res.append((Td, Sd, set(comp)))
        if res is not None and not any(d[1] for d in res):
            res = None
    cache[key] = res
    return res


# ----------------------------------------------------------------------------------------- distance field
def _field(H, W, Sd, P, metric, Td):
    """Multi-source BFS: dist and bitmask of seed colours at the minimum distance.  manh / cheb are the
    plain lattice distances (4- / 8-step BFS over the whole grid), geo the 4-step distance inside the domain P.
    Stops once every target of the domain is settled."""
    nb = _N8 if metric == 'cheb' else _N4
    if metric != 'geo':
        P = None
    left = set(Td)
    dist, mask = {}, {}
    frontier = []
    for c, col in Sd:
        if c in mask:
            mask[c] |= 1 << col
        else:
            dist[c] = 0
            mask[c] = 1 << col
            frontier.append(c)
            left.discard(c)
    d = 0
    while frontier and left:
        nxt = []
        d1 = d + 1
        for (i, j) in frontier:
            m = mask[(i, j)]
            for di, dj in nb:
                x, y = i + di, j + dj
                if not (0 <= x < H and 0 <= y < W):
                    continue
                q = (x, y)
                if P is not None and q not in P:
                    continue
                dq = dist.get(q)
                if dq is None:
                    dist[q] = d1
                    mask[q] = m
                    nxt.append(q)
                    left.discard(q)
                elif dq == d1:
                    mask[q] |= m
        frontier = nxt
        d = d1
    return dist, mask




def _sym_seeds(H, W, Td, Sd):
    """Complete the seed set by its half-turn image about the centre of the targets' bbox (a real seed wins)."""
    rs = [a for a, _ in Td]
    cs = [b for _, b in Td]
    cy2, cx2 = min(rs) + max(rs), min(cs) + max(cs)
    have = set(c for c, _ in Sd)
    extra = []
    for (i, j), col in Sd:
        q = (cy2 - i, cx2 - j)
        if 0 <= q[0] < H and 0 <= q[1] < W and q not in have:
            extra.append((q, col))
    return list(Sd) + extra


def _paint(g, tcmode, shape, excl, domain, unit, metric, cache, sym='none'):
    """-> (paint {cell: colour}, ties [cell]) or None."""
    key = ('A', tcmode, shape, excl, domain, unit, metric, sym)
    if key in cache:
        return cache[key]
    doms = _domains(g, tcmode, shape, excl, domain, cache)
    res = None
    if doms is not None:
        H, W = len(g), len(g[0])
        paint, ties = {}, []
        for Td, Sd, P in doms:
            if not Sd:
                continue
            if unit == 'vote':
                top = Counter(c for _, c in Sd).most_common()
                if len(top) > 1 and top[0][1] == top[1][1]:
                    ties.extend(Td)
                else:
                    for t in Td:
                        paint[t] = top[0][0]
                continue
            if sym == 'point':
                Sd = _sym_seeds(H, W, Td, Sd)
            dist, mask = _field(H, W, Sd, P, metric, Td)
            if unit == 'cell':
                for t in Td:
                    m = mask.get(t, 0)
                    if not m:
                        continue
                    if m & (m - 1):
                        ties.append(t)
                    else:
                        paint[t] = m.bit_length() - 1
            else:
                for obj in _components(set(Td), _N8):
                    best, m = None, 0
                    for t in obj:
                        dt = dist.get(t)
                        if dt is None:
                            continue
                        if best is None or dt < best:
                            best, m = dt, mask[t]
                        elif dt == best:
                            m |= mask[t]
                    if not m:
                        continue
                    if m & (m - 1):
                        ties.extend(obj)
                    else:
                        col = m.bit_length() - 1
                        for t in obj:
                            paint[t] = col
        if paint or ties:
            res = (paint, ties)
    cache[key] = res
    return res


# ----------------------------------------------------------------------------------------- rendering
def _render(g, bg, S, T, paint, ties, tie, post):
    out = [list(r) for r in g]
    if post == 'seeds':
        for (i, j), _ in S:
            out[i][j] = bg
    elif post == 'all':
        keep = set(paint)
        keep.update(ties)
        for i, r in enumerate(out):
            for j in range(len(r)):
                if r[j] != bg and (i, j) not in keep:
                    r[j] = bg
    for (i, j), c in paint.items():
        out[i][j] = c
    if tie != 'keep':
        for i, j in ties:
            out[i][j] = tie
    return out


def _pack(g, bg, T, paint, ties, tie):
    tieset = set(ties)
    infos = []
    for obj in _components(set(T), _N8):
        rs = [a for a, _ in obj]
        cs = [b for _, b in obj]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        crop = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
        for a, b in obj:
            v = paint.get((a, b))
            if v is None:
                v = tie if ((a, b) in tieset and tie != 'keep') else g[a][b]
            crop[a - r0][b - c0] = v
        infos.append((r0, r1, c0, c1, crop))
    if not infos:
        return None

    def disjoint(k0, k1):
        s = sorted(infos, key=lambda t: t[k0])
        return all(s[i][k1] < s[i + 1][k0] for i in range(len(s) - 1))

    if disjoint(2, 3):
        s = sorted(infos, key=lambda t: t[2])
        H = max(len(t[4]) for t in s)
        out = [[] for _ in range(H)]
        for t in s:
            cr = t[4]
            w = len(cr[0])
            for i in range(H):
                out[i].extend(cr[i] if i < len(cr) else [bg] * w)
        return out
    if disjoint(0, 1):
        s = sorted(infos, key=lambda t: t[0])
        W = max(len(t[4][0]) for t in s)
        out = []
        for t in s:
            for row in t[4]:
                out.append(list(row) + [bg] * (W - len(row)))
        return out
    return None




def _enclosed_rooms(g, H, W, bg):
    """4-components of background cells that do not touch the grid border."""
    linked = _border_linked(g, H, W, bg)
    cells = {(i, j) for i in range(1, H - 1) for j in range(1, W - 1) if g[i][j] == bg and (i, j) not in linked}
    return _components(cells, _N4)


def _dock(g, bg, tcol):
    """Move the target piece (all target cells, else each 8-connected target object) into the enclosed background
    room whose bbox has the piece's size.  -> (moved grid, crop box = room bbox grown by its wall ring) or None.
    Every docked piece must find exactly one such room; the crop box is the union over the docked rooms."""
    if tcol is None or tcol == bg:
        return None
    H, W = len(g), len(g[0])
    T = [(i, j) for i in range(H) for j in range(W) if g[i][j] == tcol]
    if not T:
        return None
    rooms = []
    for comp in _enclosed_rooms(g, H, W, bg):
        rs = [a for a, _ in comp]
        cs = [b for _, b in comp]
        rooms.append((min(rs), min(cs), max(rs) - min(rs) + 1, max(cs) - min(cs) + 1, set(comp)))
    if not rooms:
        return None

    def bbox(cells):
        rs = [a for a, _ in cells]
        cs = [b for _, b in cells]
        return min(rs), min(cs), max(rs) - min(rs) + 1, max(cs) - min(cs) + 1

    def place(pieces):
        moves = []
        used = set()
        for pc in pieces:
            r0, c0, h, w = bbox(pc)
            cand = [k for k, rm in enumerate(rooms) if rm[2] == h and rm[3] == w and k not in used
                    and all((a - r0 + rm[0], b - c0 + rm[1]) in rm[4] for a, b in pc)]
            if len(cand) != 1:
                return None
            used.add(cand[0])
            rm = rooms[cand[0]]
            moves.append((pc, rm[0] - r0, rm[1] - c0))
        return moves, used

    pl = place([T])
    if pl is None:
        objs = _components(set(T), _N8)
        if len(objs) < 2:
            return None
        pl = place(objs)
        if pl is None:
            return None
    moves, used = pl
    out = [list(r) for r in g]
    for pc, _, _ in moves:
        for a, b in pc:
            out[a][b] = bg
    for pc, dr, dc in moves:
        for a, b in pc:
            out[a + dr][b + dc] = tcol
    R0 = min(rooms[k][0] for k in used) - 1
    C0 = min(rooms[k][1] for k in used) - 1
    R1 = max(rooms[k][0] + rooms[k][2] for k in used)
    C1 = max(rooms[k][1] + rooms[k][3] for k in used)
    return out, (R0, C0, R1 - R0 + 1, C1 - C0 + 1)


def _crop(g, box):
    r0, c0, h, w = box
    return [list(g[i][c0:c0 + w]) for i in range(r0, r0 + h)]


def _docked(g, bg, tcmode, cache):
    """Cached docking of the target piece; -> (moved grid, its own cache, crop box) or None."""
    key = ('K', tcmode)
    if key not in cache:
        d = _dock(g, bg, _resolve_tc(g, bg, tcmode))
        cache[key] = None if d is None else (d[0], {'bg': bg}, d[1])
    return cache[key]


def _make(tcmode, shape, excl, domain, unit, metric, sym, tie, post, outmode):
    def fn(g):
        try:
            cache = {'bg': _bg(g)}
            bg = cache['bg']
            box = None
            if outmode == 'dock':
                d = _docked(g, bg, tcmode, cache)
                if d is None:
                    return None
                g, cache, box = d
            r = _paint(g, tcmode, shape, excl, domain, unit, metric, cache, sym)
            if r is None:
                return None
            paint, ties = r
            tcol, T, S = _participants(g, tcmode, shape, excl, cache)
            if outmode == 'pack':
                return _pack(g, bg, T, paint, ties, tie)
            out = _render(g, bg, S, T, paint, ties, tie, post)
            return _crop(out, box) if box else out
        except Exception:
            return None
    return fn


# ----------------------------------------------------------------------------------------- induction
def _tc_modes(ins, outs, bgs, painted_cols, mode):
    """Target-colour modes consistent with the training pairs.  Role-bound modes first (dom, then bg); a
    constant colour only when no role resolves to the same colours on every input (G68 specialisation)."""
    doms = []
    for g, bg in zip(ins, bgs):
        c = Counter(v for r in g for v in r if v != bg)
        doms.append(c.most_common(1)[0][0] if c else None)
    modes = []
    if mode == 'grid':
        cols = [pc for pc in painted_cols if pc is not None]
        if not cols:
            return []
        if all(pc is None or pc == d for pc, d in zip(painted_cols, doms)):
            modes.append('dom')
        if all(pc is None or pc == b for pc, b in zip(painted_cols, bgs)):
            modes.append('bg')
        if len(set(cols)) == 1:
            modes.append(cols[0])
    elif mode == 'pack':
        outcols = set(v for g in outs for r in g for v in r)
        common = set.intersection(*[set(v for r in g for v in r) for g in ins]) - set(bgs) - outcols
        if all(d is not None and d not in set(v for r in o for v in r) for d, o in zip(doms, outs)):
            modes.append('dom')
        modes.extend(sorted(common))
    else:  # dock: the piece colour may survive (ties keep it)
        if all(d is not None for d in doms):
            modes.append('dom')
        modes.extend(sorted(set.intersection(*[set(v for r in g for v in r) for g in ins]) - set(bgs)))
    # drop modes that resolve to the same colours on every input as an earlier mode
    seen, res = set(), []
    for m in modes:
        sig = tuple(_resolve_tc(g, bg, m) for g, bg in zip(ins, bgs))
        if sig not in seen:
            seen.add(sig)
            res.append(m)
    return res


def fam(train):
    t0 = time.time()
    if not train:
        return
    ins = [p['input'] for p in train]
    outs = [p['output'] for p in train]
    if any(not g or not g[0] for g in ins + outs):
        return
    same = all(len(a) == len(b) and len(a[0]) == len(b[0]) for a, b in zip(ins, outs))
    bgs = [_bg(g) for g in ins]
    painted = []
    erased = False
    caches = [{'bg': bg} for bg in bgs]
    plans = []          # (outmode, tc modes, posts, per-tc (grids, caches, boxes))
    if same:
        painted_cols = []
        for a, b, bg in zip(ins, outs, bgs):
            cells, cols = [], set()
            for i, (ra, rb) in enumerate(zip(a, b)):
                for j, (x, y) in enumerate(zip(ra, rb)):
                    if x != y:
                        if y == bg:
                            erased = True
                        else:
                            cells.append((i, j))
                            cols.add(x)
            if len(cols) > 1:
                return
            painted.append(cells)
            painted_cols.append(cols.pop() if cols else None)
        if not any(painted):
            return
        tcs = _tc_modes(ins, outs, bgs, painted_cols, 'grid')
        posts = ('seeds', 'all') if erased else ('none',)
        plans.append(('grid', tcs, posts, {m: (ins, caches, None) for m in tcs}))
    else:
        if any(len(b) * len(b[0]) >= len(a) * len(a[0]) for a, b in zip(ins, outs)):
            return
        painted = [None] * len(ins)
        tcs = _tc_modes(ins, outs, bgs, None, 'pack')
        if tcs:
            plans.append(('pack', tcs, ('none',), {m: (ins, caches, None) for m in tcs}))
        dk = {}
        for m in _tc_modes(ins, outs, bgs, None, 'dock'):
            gs, cs, bs = [], [], []
            for g, o, bg, cache in zip(ins, outs, bgs, caches):
                d = _docked(g, bg, m, cache)
                if d is None or d[2][2:] != (len(o), len(o[0])):
                    break
                gs.append(d[0]); cs.append(d[1]); bs.append(d[2])
            else:
                dk[m] = (gs, cs, bs)
        if dk:
            plans.append(('dock', list(dk), ('none',), dk))
    fits = []
    for outmode, tcs, posts, data in plans:
        for ti, tcmode in enumerate(tcs):
            gs, cs, boxes = data[tcmode]
            for si, shape in enumerate(_SHAPES):
                if outmode != 'grid' and shape != 'all':
                    continue
                if outmode == 'grid' and shape != 'all':
                    # every painted cell must pass the shape test
                    good = True
                    for g, bg, cells in zip(ins, bgs, painted):
                        if not cells:
                            continue
                        H, W = len(g), len(g[0])
                        linked = (_border_linked(g, H, W, g[cells[0][0]][cells[0][1]])
                                  if shape == 'enclosed' else None)
                        if not all(_shape_ok(g, H, W, bg, i, j, shape, linked) for i, j in cells):
                            good = False
                            break
                    if not good:
                        continue
                for excl in (0, 1):
                    for di, domain in enumerate(_DOMAINS):
                        for ui, (unit, metric) in enumerate(_UNITS):
                            if outmode == 'pack' and unit != 'object':
                                continue
                            if domain == 'global' and metric == 'geo':
                                continue
                            if outmode == 'dock' and domain != 'room':
                                continue        # the docked piece's domain is bound to the room it was docked into
                            for yi, sym in enumerate(('none', 'point')):
                                if sym == 'point' and unit == 'vote':
                                    continue
                                if time.time() - t0 > _BUDGET:
                                    break
                                prog = _check(gs, outs, bgs, painted, cs, boxes, tcmode, shape, excl, domain,
                                              unit, metric, sym, posts, outmode)
                                if prog is None:
                                    continue
                                tie, post = prog
                                cost = (1 + 0.3 * ti + 0.2 * si + 0.3 * excl + 0.1 * di + 0.15 * ui
                                        + 0.3 * yi + (0.2 if tie != 'keep' else 0) + (0.1 if post == 'all' else 0)
                                        + (1 if outmode != 'grid' else 0))
                                name = ('recolour:nearest_seed[tc=%s,shape=%s,excl=%d,domain=%s,unit=%s%s,sym=%s,'
                                        'tie=%s,post=%s,out=%s]'
                                        % (tcmode, shape, excl, domain, unit,
                                           ',metric=%s' % metric if metric else '', sym, tie, post, outmode))
                                fits.append((cost, len(fits), name,
                                             _make(tcmode, shape, excl, domain, unit, metric, sym, tie, post,
                                                   outmode)))
    fits.sort(key=lambda f: (f[0], f[1]))
    for cost, _, name, fn in fits[:3]:
        yield (name, cost, fn)


def _check(gs, outs, bgs, painted, caches, boxes, tcmode, shape, excl, domain, unit, metric, sym, posts, outmode):
    """Return (tie, post) if the program reproduces every training pair, else None.  gs / caches are the
    inputs (or the docked inputs, with their crop boxes) the program paints on."""
    results = []
    tie = None
    for k, (g, o, bg) in enumerate(zip(gs, outs, bgs)):
        r = _paint(g, tcmode, shape, excl, domain, unit, metric, caches[k], sym)
        if r is None:
            return None
        paint, ties = r
        if outmode != 'pack':
            r0, c0 = boxes[k][:2] if boxes else (0, 0)
            Ho, Wo = len(o), len(o[0])
            # every painted cell (inside the output window) must be painted with the right colour
            for (a, b), col in paint.items():
                a, b = a - r0, b - c0
                if 0 <= a < Ho and 0 <= b < Wo and o[a][b] != col:
                    return None
            tv = [(o[i - r0][j - c0], g[i][j]) for i, j in ties if 0 <= i - r0 < Ho and 0 <= j - c0 < Wo]
            if tv:
                if all(x == y for x, y in tv):
                    v = 'keep'
                elif len(set(x for x, _ in tv)) == 1:
                    v = tv[0][0]
                else:
                    return None
                if tie is None:
                    tie = v
                elif tie != v:
                    return None
        results.append(r)
    if tie is None:
        tie = 'keep'
    for post in posts:
        ok = True
        for k, (g, o, bg) in enumerate(zip(gs, outs, bgs)):
            paint, ties = results[k]
            tcol, T, S = _participants(g, tcmode, shape, excl, caches[k])
            if outmode == 'pack':
                pred = _pack(g, bg, T, paint, ties, tie)
            else:
                pred = _render(g, bg, S, T, paint, ties, tie, post)
                if boxes:
                    pred = _crop(pred, boxes[k])
            if pred != o:
                ok = False
                break
        if ok:
            return tie, post
    return None


FAMILIES = [fam]
