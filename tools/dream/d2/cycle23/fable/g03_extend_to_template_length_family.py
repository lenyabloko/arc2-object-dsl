"""g03 "lines extended to a template length"  --  one concept: EXTRUSION (CAD / solid modelling).

Mechanism.  Every object has a growth axis d and a front face (its extreme cell along d).  A profile is swept
(extruded) from that front face along d until it is exhausted or leaves the grid, painting only background cells.
The profile is read off a reference:
    ref=template : the task's template object (the longest object along d, i.e. the complete line, preferring the
                   partial's own colour) is laid over the partial object, rear to rear, with the lateral anchors
                   (rear cell = start of the rail, or a lateral bbox edge) aligned; every template cell that lies
                   beyond the partial's front is painted.  The sweep therefore stops exactly at the template's length.
    ref=self     : the object's own cross-section through its marker cell (the minority-coloured cell sitting on a
                   face; the face normal gives d), unfolded symmetrically about the marker, is swept to the grid edge.
The painted colour is the reference cell's colour (keep), one constant colour learned from the training outputs
(const) or the swept object's body colour (object).
Parameters (finite domains, all induced from the task's training pairs):
    dir in {R, L, D, U, marker}   ref in {template, self}   align in {rear, min, max}   fill in {keep, const, object}
"""
from collections import Counter

DIRS = {'R': (0, 1), 'L': (0, -1), 'D': (1, 0), 'U': (-1, 0)}


# ----------------------------------------------------------------------------------------------- grid utilities
def _bg(grids):
    cnt = Counter(v for g in grids for row in g for v in row)
    return cnt.most_common(1)[0][0]


def _components(g, bg):
    """8-connected components of non-background cells; each is {(r, c): colour}."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            stack, cells = [(r, c)], {}
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells[(y, x)] = g[y][x]
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            comps.append(cells)
    return comps


def _axis(d):
    """Coordinate change for growth direction d: (r, c) <-> (along, lateral)."""
    dr, dc = d
    if dr:
        return (lambda r, c: (r * dr, c)), (lambda a, l: (a * dr, l))
    return (lambda r, c: (c * dc, r)), (lambda a, l: (l, a * dc))


def _body_colour(cells):
    return Counter(cells.values()).most_common(1)[0][0]


def _marker_dirs(cells, m):
    """Directions d for which the marker m sits on a face of its object with material behind it."""
    out = []
    for name, (dr, dc) in DIRS.items():
        if (m[0] + dr, m[1] + dc) not in cells and (m[0] - dr, m[1] - dc) in cells:
            out.append(name)
    return out


# ----------------------------------------------------------------------------------------------- the sweeps
def _anchor(al, align):
    """(rear along-coordinate, lateral reference) of a cell set given in (along, lateral) coordinates.
    align=rear: lateral position of the rear-most cell (start of the rail); min/max: lateral bbox edge."""
    a0 = min(a for a, _ in al)
    if align == 'rear':
        return a0, min(l for a, l in al if a == a0)
    return a0, (min if align == 'min' else max)(l for _, l in al)


def _sweep_template(out, bg, P, T, d, align, colour_of):
    """Lay template T over partial P (rear to rear, lateral anchors `align`); paint T's cells beyond P's front."""
    H, W = len(out), len(out[0])
    to_al, to_rc = _axis(d)
    Ta = [(to_al(r, c), col) for (r, c), col in T.items()]
    Pa = [to_al(r, c) for (r, c) in P]
    a0T, lT = _anchor([a for a, _ in Ta], align)
    a0P, lP = _anchor(Pa, align)
    front = max(a for a, _ in Pa) - a0P
    for (a, l), col in Ta:
        ra = a - a0T
        if ra <= front:
            continue
        r, c = to_rc(a0P + ra, lP + (l - lT))
        if 0 <= r < H and 0 <= c < W and out[r][c] == bg:
            out[r][c] = colour_of(col, P)


def _sweep_self(out, bg, P, m, d, colour_of):
    """Unfold P's cross-section through marker m about m and sweep it along d to the grid edge."""
    H, W = len(out), len(out[0])
    dr, dc = d
    sec, (r, c) = [], m
    while (r, c) in P:
        sec.append(P[(r, c)])
        r, c = r - dr, c - dc
    t = len(sec)
    lr, lc = abs(dc), abs(dr)                      # lateral unit vector
    s = 1
    while True:
        r0, c0 = m[0] + s * dr, m[1] + s * dc
        if not (0 <= r0 < H and 0 <= c0 < W):
            break
        for j in range(-(t - 1), t):
            r, c = r0 + j * lr, c0 + j * lc
            if 0 <= r < H and 0 <= c < W and out[r][c] == bg:
                out[r][c] = colour_of(sec[abs(j)], P)
        s += 1


# ----------------------------------------------------------------------------------------------- program builder
def _make(bg, dir_mode, ref, align, fill, const):
    def colour_of(col, P):
        if fill == 'const':
            return const
        if fill == 'object':
            return _body_colour(P)
        return col

    def fn(g):
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        comps = _components(g, bg)
        if not comps:
            return out
        if ref == 'template':
            if dir_mode == 'marker':
                # per-object direction from its marker; template = longest object along that direction
                for P in comps:
                    body = _body_colour(P)
                    for m, col in P.items():
                        if col == body:
                            continue
                        ds = _marker_dirs(P, m)
                        if len(ds) != 1:
                            continue
                        d = DIRS[ds[0]]
                        T = _template_for(P, comps, d)
                        if T is not None:
                            _sweep_template(out, bg, P, T, d, align, colour_of)
            else:
                d = DIRS[dir_mode]
                for P in comps:
                    T = _template_for(P, comps, d)
                    if T is not None:
                        _sweep_template(out, bg, P, T, d, align, colour_of)
        else:  # ref == 'self'
            for P in comps:
                body = _body_colour(P)
                for m, col in P.items():
                    if col == body:
                        continue
                    if dir_mode == 'marker':
                        ds = _marker_dirs(P, m)
                        if len(ds) != 1:
                            continue
                        d = DIRS[ds[0]]
                    else:
                        d = DIRS[dir_mode]
                    _sweep_self(out, bg, P, m, d, colour_of)
        return out
    return fn


def _extent(P, d):
    to_al, _ = _axis(d)
    al = [to_al(r, c)[0] for (r, c) in P]
    return max(al) - min(al) + 1


def _template_for(P, comps, d):
    """The complete line P is a partial copy of: the longest object along d that is longer than P, preferring
    objects of P's own colour; None when P is itself (one of) the longest."""
    eP = _extent(P, d)
    longer = [(T, _extent(T, d)) for T in comps if T is not P and _extent(T, d) > eP]
    if not longer:
        return None
    same = [(T, e) for T, e in longer if _body_colour(T) == _body_colour(P)]
    return max(same or longer, key=lambda te: (te[1], len(te[0])))[0]


# ----------------------------------------------------------------------------------------------- the family
def fam_extrusion(train):
    if not train or any(len(p['output']) != len(p['input']) or len(p['output'][0]) != len(p['input'][0])
                        for p in train):
        return
    bg = _bg([p['input'] for p in train])
    # cells that change must only ever be painted over background, and a 'const' colour must be unique
    added = Counter()
    for p in train:
        for r, row in enumerate(p['input']):
            for c, v in enumerate(row):
                w = p['output'][r][c]
                if w != v:
                    if v != bg:
                        return                      # extrusion never overwrites material
                    added[w] += 1
    if not added:
        return
    const = next(iter(added)) if len(added) == 1 else None
    fills = ['keep', 'object'] + (['const'] if const is not None else [])
    for dir_mode in ('R', 'L', 'D', 'U', 'marker'):
        for ref in ('template', 'self'):
            for align in (('rear', 'min', 'max') if ref == 'template' else ('-',)):
                for fill in fills:
                    fn = _make(bg, dir_mode, ref, align, fill, const)
                    try:
                        ok = all(fn(p['input']) == p['output'] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        tag = f"dir={dir_mode},ref={ref}" + (f",align={align}" if ref == 'template' else '') \
                              + f",fill={fill}" + (f":{const}" if fill == 'const' else '')
                        yield (f"cad:extrusion[{tag}]", 3, fn)
                        return


FAMILIES = (fam_extrusion,)
