"""Group g04 "shadows cast from objects"  --  concept: CAST SHADOW (optics, parallel projection).

Mechanism (one for every member): every object is opaque and lit by a parallel beam; it casts a shadow
on the ground along the light direction.  The shadow of an object is the projection of its far face
(the cells whose neighbour along the light direction is outside the object), extended for a length that
is a property of the object (its "height": infinite, number of distinct colours, number of cells, ...),
painted in a shadow colour (a fixed shadow colour, or the colour of the far-face cell) onto background
cells only.  Where the ground is stepped -- the lines (rows/columns) of "marker" cells -- the shadow is
displaced laterally by one cell at every step, away from (or toward) the marker that makes the step.

Everything is induced from the training pairs of THIS task, from finite domains:
    marker colour      : None or any colour present in the training inputs
    light direction    : fixed down/up/right/left, "inward" from the edge the object touches,
                         or "away from the marker light source"
    shadow length      : to the grid edge | #distinct colours | #cells | extent along | extent across | 1
    shadow colour      : same as the casting cell | the one new colour of the training outputs
    lateral deflection : none | away from marker | toward marker (one cell per marker line crossed)
    obstacles          : shadow stops at the first non-background cell | passes over it
No coordinates, sizes, counts or colour numbers are hard-coded.
"""
from collections import Counter

DIRS = {'down': (1, 0), 'up': (-1, 0), 'right': (0, 1), 'left': (0, -1)}
EDGE_DIR = {'top': 'down', 'bottom': 'up', 'left': 'right', 'right': 'left'}
LENGTH_RULES = ('edge', 'ncolours', 'ncells', 'along', 'across', 'one')
MAX_YIELDS = 4


def _sign(x):
    return (x > 0) - (x < 0)


def _components(grid, bg, marker):
    """8-connected components of cells that are neither background nor marker."""
    H, W = len(grid), len(grid[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            v = grid[r][c]
            if seen[r][c] or v == bg or v == marker:
                continue
            stack = [(r, c)]
            seen[r][c] = True
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx]:
                            w = grid[ny][nx]
                            if w != bg and w != marker:
                                seen[ny][nx] = True
                                stack.append((ny, nx))
            comps.append(cells)
    return comps


def _object_direction(cells, dir_rule, H, W, markers):
    """Light direction for one object under the direction rule; None if the rule does not apply."""
    if dir_rule in DIRS:
        return DIRS[dir_rule]
    if dir_rule == 'inward':
        edges = set()
        for r, c in cells:
            if r == 0: edges.add('top')
            if r == H - 1: edges.add('bottom')
            if c == 0: edges.add('left')
            if c == W - 1: edges.add('right')
        if len(edges) != 1:
            return None
        return DIRS[EDGE_DIR[edges.pop()]]
    if dir_rule == 'from_marker':          # marker cells are the light source: shadow points away from it
        if not markers:
            return None
        lr = sum(r for r, _ in markers) / len(markers)
        lc = sum(c for _, c in markers) / len(markers)
        orr = sum(r for r, _ in cells) / len(cells)
        oc = sum(c for _, c in cells) / len(cells)
        dr, dc = orr - lr, oc - lc
        if abs(dr) == abs(dc):
            return None
        return (_sign(dr), 0) if abs(dr) > abs(dc) else (0, _sign(dc))
    return None


def _object_length(cells, grid, bg, d, rule):
    if rule == 'edge':
        return 10 ** 6
    if rule == 'one':
        return 1
    if rule == 'ncells':
        return len(cells)
    if rule == 'ncolours':
        return len({grid[r][c] for r, c in cells})
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    hr, wc = max(rs) - min(rs) + 1, max(cs) - min(cs) + 1
    vertical = d[0] != 0
    if rule == 'along':
        return hr if vertical else wc
    if rule == 'across':
        return wc if vertical else hr
    return 0


def _paths(grid, bg, cells, d, markers, deflect):
    """Shadow rays of one object: list of (colour of casting cell, [cells along the ray until it leaves the grid])."""
    H, W = len(grid), len(grid[0])
    dr, dc = d
    cellset = set(cells)
    by_along = {}
    if deflect:
        for mr, mc in markers:
            a, l = (mr, mc) if dr else (mc, mr)
            by_along.setdefault(a, []).append(l)
    out = []
    for r, c in cells:
        if (r + dr, c + dc) in cellset:
            continue                        # not on the far face
        col = grid[r][c]
        y, x = r, c
        ray = []
        while True:
            y += dr
            x += dc
            if by_along:
                a, l = (y, x) if dr else (x, y)
                ms = by_along.get(a)
                if ms:
                    s = sum(_sign(l - lm) for lm in ms)
                    if deflect == 'toward':
                        s = -s
                    if dr:
                        x += s
                    else:
                        y += s
            if not (0 <= y < H and 0 <= x < W):
                break
            ray.append((y, x))
        out.append((col, ray))
    return out


def _make_fn(bg, marker, dir_rule, deflect, length_rule, colour_rule, obstacle):
    def fn(grid):
        H, W = len(grid), len(grid[0])
        out = [row[:] for row in grid]
        markers = [(r, c) for r in range(H) for c in range(W) if grid[r][c] == marker] if marker is not None else []
        for cells in _components(grid, bg, marker):
            d = _object_direction(cells, dir_rule, H, W, markers)
            if d is None:
                raise ValueError('direction rule does not apply')
            n = _object_length(cells, grid, bg, d, length_rule)
            for col, ray in _paths(grid, bg, cells, d, markers, deflect):
                paint = col if colour_rule[0] == 'same' else colour_rule[1]
                k = 0
                for (y, x) in ray:
                    if k >= n:
                        break
                    if grid[y][x] != bg:
                        if obstacle == 'stop':
                            break
                        k += 1
                        continue
                    if out[y][x] == bg:
                        out[y][x] = paint
                    k += 1
        return out
    return fn


def fam_shadow(train):
    if not train:
        return
    # --- quick structural rejection -------------------------------------------------------------
    for p in train:
        i, o = p['input'], p['output']
        if len(i) != len(o) or any(len(a) != len(b) for a, b in zip(i, o)):
            return
    cnt = Counter(v for p in train for row in p['input'] for v in row)
    bg = cnt.most_common(1)[0][0]
    changed_cols = set()
    n_changed = 0
    for p in train:
        i, o = p['input'], p['output']
        for a, b in zip(i, o):
            for u, v in zip(a, b):
                if u != v:
                    if u != bg:
                        return                  # input objects must be preserved
                    changed_cols.add(v)
                    n_changed += 1
    if n_changed == 0:
        return
    colour_rules = [('same',)]
    if len(changed_cols) == 1:
        colour_rules.append(('fixed', next(iter(changed_cols))))
    input_colours = sorted(c for c in cnt if c != bg)
    marker_cands = [None] + input_colours
    # 'inward' first: when it fits it is the more general reading of a fixed direction seen in training
    dir_rules = ['inward', 'down', 'up', 'right', 'left', 'from_marker']
    # a shadow can only be cast onto background: the changed cells of every pair are known up front
    changed = [{(r, c) for r, (a, b) in enumerate(zip(p['input'], p['output'])) for c, (u, v) in enumerate(zip(a, b)) if u != v}
               for p in train]

    n_yield = 0
    for deflect in (None, 'away', 'toward'):
        for marker in marker_cands:
            if deflect and marker is None:
                continue
            per_pair = []
            ok = True
            for p in train:
                g = p['input']
                H, W = len(g), len(g[0])
                markers = [(r, c) for r in range(H) for c in range(W) if g[r][c] == marker] if marker is not None else []
                comps = _components(g, bg, marker)
                if not comps:
                    ok = False
                    break
                per_pair.append((g, p['output'], H, W, markers, comps))
            if not ok:
                continue
            for dir_rule in dir_rules:
                if dir_rule == 'from_marker' and marker is None:
                    continue
                cands = [(lr, cr, ob) for lr in LENGTH_RULES for cr in colour_rules for ob in ('stop', 'pass')]
                # filter the candidate (length, colour, obstacle) rules pair by pair; stop at the first empty set
                for pi, (g, o, H, W, markers, comps) in enumerate(per_pair):
                    rays = []
                    for cells in comps:
                        d = _object_direction(cells, dir_rule, H, W, markers)
                        if d is None:
                            cands = []
                            break
                        rays.append((cells, d, _paths(g, bg, cells, d, markers, deflect)))
                    if not cands:
                        break
                    # every changed cell must lie on some ray (otherwise no rule can paint it)
                    covered = set()
                    for _, _, prs in rays:
                        for _, ray in prs:
                            covered.update(ray)
                    if not changed[pi] <= covered:
                        cands = []
                        break
                    survivors = []
                    for lr, cr, ob in cands:
                        out = [row[:] for row in g]
                        for cells, d, prs in rays:
                            n = _object_length(cells, g, bg, d, lr)
                            for col, ray in prs:
                                paint = col if cr[0] == 'same' else cr[1]
                                k = 0
                                for (y, x) in ray:
                                    if k >= n:
                                        break
                                    if g[y][x] != bg:
                                        if ob == 'stop':
                                            break
                                        k += 1
                                        continue
                                    if out[y][x] == bg:
                                        out[y][x] = paint
                                    k += 1
                        if out == o:
                            survivors.append((lr, cr, ob))
                    cands = survivors
                    if not cands:
                        break
                for length_rule, colour_rule, obstacle in cands:
                    fn = _make_fn(bg, marker, dir_rule, deflect, length_rule, colour_rule, obstacle)
                    if all(fn(p['input']) == p['output'] for p in train):
                        name = ('optics:cast_shadow[marker=%s,dir=%s,len=%s,colour=%s,deflect=%s,obstacle=%s]'
                                % (marker, dir_rule, length_rule,
                                   colour_rule[0] if colour_rule[0] == 'same' else colour_rule[1],
                                   deflect or 'none', obstacle))
                        yield (name, 3 if n_yield == 0 else 4, fn)
                        n_yield += 1
                        if n_yield >= MAX_YIELDS:
                            return


FAMILIES = (fam_shadow,)
