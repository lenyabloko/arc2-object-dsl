"""g01 family -- RAY CASTING (computer graphics / optics).

Mechanism: every emitter object casts rays; a ray starts just outside the emitter, advances cell by cell in a
fixed direction and is painted until it leaves the grid or hits an obstacle (= any non-background cell of the
INPUT; rays never stop each other, they cross, and a fixed priority decides the crossing cell).

Everything below is induced from the task's own training pairs, from small declared finite domains:
  bg            most common colour of the input grid
  obstacle      {None} U {colours present in every training input}: cells of this colour are never emitters
                (they only block rays); with None every non-background object is an emitter
  objects       8-connected components of non-background, non-obstacle cells (any colours), each including its
                enclosed interior (so a ring of arms around a background centre is one object with a core)
  emitter model 'tips'  : an object = core + tips (a tip is a cell with <=1 orthogonal neighbour in the object).
                          Each tip is a pointer: the ray direction is the side of the core's bounding box the
                          tip lies on, the ray starts just beyond the tip.  (diamonds, block+corner pixels, ...)
                'block' : a plain object casts rays from its bounding box: corners -> the 4 diagonal
                          directions, edge midpoints -> the 4 orthogonal directions.
  directions    which of the 8 directions emit is induced: a direction whose exclusively covered cells are mostly
                changed cells emits, one whose exclusive cells are mostly unchanged does not (rays of a
                background-coloured emitter are invisible and give no evidence); undecidable directions are
                enumerated, fewer rays first.
  colour (per direction class orth / diag)  {'core' (dominant colour of the core), 'tip' (colour of the tip)}
                U {constants: colours of changed cells in the training outputs}
  raster of orthogonal rays  {'line', 'stair2cw', 'stair2ccw'}: straight, or a 4-connected staircase that
                alternates 2 cells outward and 2 cells sideways (chirality cw / ccw); diagonal rays are lines.
                (period 1 is deliberately absent: such a staircase contains the diagonal line, which makes the
                diagonal rays undecidable from training pairs)
  corner_block  {True, False}: a diagonal step is blocked when the two cells flanking that step are both obstacles
                (no corner cutting)
  priority      {'v>h', 'h>v'}: which class wins where a vertical and a horizontal ray cross
Nothing is hard coded: no coordinates, sizes, counts or colour numbers.
"""
from collections import Counter
from itertools import product

ORTH = ((-1, 0), (0, 1), (1, 0), (0, -1))
DIAG = ((-1, -1), (-1, 1), (1, 1), (1, -1))
RASTERS = ('line', 'stair2cw', 'stair2ccw')


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg, obstacle):
    """8-connected components of solid cells (neither background nor obstacle colour, colour-agnostic), each
    object including its enclosed interior (cells not 4-reachable from the border through non-solid cells)."""
    H, W = len(g), len(g[0])
    solid = [[g[r][c] != bg and g[r][c] != obstacle for c in range(W)] for r in range(H)]
    # outside = non-solid cells 4-connected to the border; every other non-solid cell is a hole
    outside = [[False] * W for _ in range(H)]
    stack = [(r, c) for r in range(H) for c in (0, W - 1) if not solid[r][c]]
    stack += [(r, c) for c in range(W) for r in (0, H - 1) if not solid[r][c]]
    for r, c in stack:
        outside[r][c] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ORTH:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not solid[ny][nx] and not outside[ny][nx]:
                outside[ny][nx] = True
                stack.append((ny, nx))
    member = [[solid[r][c] or not outside[r][c] for c in range(W)] for r in range(H)]
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if not member[r][c] or (r, c) in seen:
                continue
            seen.add((r, c))
            stack = [(r, c)]
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and member[ny][nx]:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            comps.append(cells)
    return comps


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _ports(g, bg, obstacle, mode):
    """Ports: (start cell, direction, core colour, tip colour)."""
    ports = []
    for cells in _components(g, bg, obstacle):
        if mode == 'tips':
            if len(cells) < 2:
                continue
            cs = set(cells)
            tips = [p for p in cells if sum((p[0] + dr, p[1] + dc) in cs for dr, dc in ORTH) <= 1]
            tipset = set(tips)
            core = [p for p in cells if p not in tipset]
            if not core or not tips:
                continue
            rmin, rmax, cmin, cmax = _bbox(core)
            ccol = Counter(g[r][c] for r, c in core).most_common(1)[0][0]
            for r, c in tips:
                dr = -1 if r < rmin else (1 if r > rmax else 0)
                dc = -1 if c < cmin else (1 if c > cmax else 0)
                if dr == 0 and dc == 0:
                    continue
                ports.append(((r + dr, c + dc), (dr, dc), ccol, g[r][c]))
        else:
            rmin, rmax, cmin, cmax = _bbox(cells)
            ccol = Counter(g[r][c] for r, c in cells).most_common(1)[0][0]
            rmid = sorted({(rmin + rmax) // 2, (rmin + rmax + 1) // 2})
            cmid = sorted({(cmin + cmax) // 2, (cmin + cmax + 1) // 2})
            for dr, dc in ORTH:
                if dr:
                    for c in cmid:
                        ports.append((((rmin if dr < 0 else rmax) + dr, c), (dr, dc), ccol, ccol))
                else:
                    for r in rmid:
                        ports.append(((r, (cmin if dc < 0 else cmax) + dc), (dr, dc), ccol, ccol))
            for dr, dc in DIAG:
                ports.append((((rmin if dr < 0 else rmax) + dr, (cmin if dc < 0 else cmax) + dc), (dr, dc), ccol, ccol))
    return ports


def _trace(g, bg, start, d, raster, corner_block):
    """Cells of one ray, in order, until the border or an obstacle (a non-background INPUT cell)."""
    H, W = len(g), len(g[0])
    dr, dc = d
    cells = []
    if raster == 'line' or (dr and dc):
        r, c = start
        pr, pc = r - dr, c - dc
        while 0 <= r < H and 0 <= c < W and g[r][c] == bg:
            if corner_block and dr and dc and g[pr + dr][pc] != bg and g[pr][pc + dc] != bg:
                break
            cells.append((r, c))
            pr, pc = r, c
            r += dr
            c += dc
        return cells
    k = int(raster[5])
    s = (dc, -dr) if raster.endswith('cw') and not raster.endswith('ccw') else (-dc, dr)
    moves = [d] * (k - 1) + [s] * k
    period = [d] * k + [s] * k
    r, c = start
    i = 0
    while 0 <= r < H and 0 <= c < W and g[r][c] == bg:
        cells.append((r, c))
        if i < len(moves):
            mr, mc = moves[i]
        else:
            mr, mc = period[(i - len(moves)) % (2 * k)]
        i += 1
        r += mr
        c += mc
    return cells


def _cls(d):
    return 'D' if d[0] and d[1] else ('V' if d[0] else 'H')


def fam_ray_casting(train):
    if not train:
        return
    pairs = []
    for p in train:
        I, O = p['input'], p['output']
        if len(I) != len(O) or any(len(a) != len(b) for a, b in zip(I, O)):
            return
        bg = _bg(I)
        D = {(r, c) for r in range(len(I)) for c in range(len(I[0])) if I[r][c] != O[r][c]}
        if any(I[r][c] != bg for r, c in D):
            return  # rays only paint background cells; they never overwrite input objects
        pairs.append((I, O, bg, D))
    if all(not D for _, _, _, D in pairs):
        return
    consts = sorted({O[r][c] for _, O, _, D in pairs for r, c in D})
    colour_opts = ['core', 'tip'] + consts
    common_in = None
    for I, _, bg, _ in pairs:
        cols = {v for row in I for v in row if v != bg}
        common_in = cols if common_in is None else common_in & cols
    obstacles = [None] + sorted(common_in)

    for obstacle, mode in product(obstacles, ('tips', 'block')):
        ports_per_pair = [_ports(I, bg, obstacle, mode) for I, _, bg, _ in pairs]
        if any(D and not ports for (_, _, _, D), ports in zip(pairs, ports_per_pair)):
            continue
        has_orth = any(not (d[0] and d[1]) for ports in ports_per_pair for _, d, _, _ in ports)
        cache = {}
        for raster, corner_block in product(RASTERS, (True, False)):
            if raster != 'line' and not has_orth:
                continue  # raster only matters for orthogonal rays
            # trace every ray of every pair (an orthogonal ray depends only on the raster, a diagonal one only
            # on the corner rule)
            rays_per_pair = []
            for pi, ((I, O, bg, D), ports) in enumerate(zip(pairs, ports_per_pair)):
                rays = []
                for start, d, ccol, tcol in ports:
                    key = (pi, start, d, corner_block if (d[0] and d[1]) else raster)
                    if key not in cache:
                        cache[key] = _trace(I, bg, start, d, raster, corner_block)
                    rays.append((d, cache[key], ccol, tcol))
                rays_per_pair.append(rays)
            # which directions emit: a direction whose exclusively-covered cells are mostly changed cells must
            # emit, one whose exclusive cells are mostly unchanged must not; directions without exclusive cells
            # (or without any ray) are enumerated
            cover = {}
            for pi, rays in enumerate(rays_per_pair):
                for d, cells, ccol, _ in rays:
                    for cell in cells:
                        cover.setdefault((pi, cell), []).append((d, ccol))
            inD, outD = Counter(), Counter()
            for (pi, cell), lst in cover.items():
                if len({d for d, _ in lst}) == 1:
                    d, ccol = lst[0]
                    if cell in pairs[pi][3]:
                        inD[d] += 1
                    elif ccol != pairs[pi][2]:  # a background-coloured emitter's ray is invisible: no evidence
                        outD[d] += 1
            present = {d for rays in rays_per_pair for d, cells, _, _ in rays if cells}
            fixed_on = {d for d in present if inD[d] > outD[d]}
            fixed_off = {d for d in present if outD[d] > inD[d]}
            ambiguous = sorted(present - fixed_on - fixed_off)
            for bits in product((False, True), repeat=len(ambiguous)):  # parsimony: fewer rays first
                enabled = fixed_on | {d for d, b in zip(ambiguous, bits) if b} | (set(ORTH + DIAG) - present)
                if not (enabled & present):
                    continue
                if raster != 'line' and not any(_cls(d) != 'D' for d in enabled & present):
                    continue
                rays_pp = [[ray for ray in rays if ray[0] in enabled] for rays in rays_per_pair]
                # coverage: every changed cell lies on some ray
                if any(not D <= {cell for _, cells, _, _ in rays for cell in cells}
                       for (I, O, bg, D), rays in zip(pairs, rays_pp)):
                    continue
                # colour rule per class, checked on cells covered by exactly one ray
                used = {'O': any(_cls(d) != 'D' for d in enabled & present),
                        'D': any(_cls(d) == 'D' for d in enabled & present)}
                cand = {}
                for k in ('O', 'D'):
                    if not used[k]:
                        cand[k] = [None]
                        continue
                    cand[k] = []
                    for rule in colour_opts:
                        good = True
                        for (I, O, bg, D), rays in zip(pairs, rays_pp):
                            cnt = Counter(cell for _, cells, _, _ in rays for cell in cells)
                            for d, cells, ccol, tcol in rays:
                                if (_cls(d) == 'D') != (k == 'D'):
                                    continue
                                col = ccol if rule == 'core' else (tcol if rule == 'tip' else rule)
                                if any(cnt[cell] == 1 and O[cell[0]][cell[1]] != col for cell in cells):
                                    good = False
                                    break
                            if not good:
                                break
                        if good:
                            cand[k].append(rule)
                    if not cand[k]:
                        break
                if not cand['O'] or not cand['D']:
                    continue
                for col_o, col_d, prio in product(cand['O'], cand['D'], ('v>h', 'h>v')):
                    fn = _make(obstacle, mode, raster, corner_block, enabled, col_o, col_d, prio)
                    if all(fn(I) == O for I, O, _, _ in pairs):
                        dirs = ''.join('1' if d in enabled else '0' for d in ORTH + DIAG)
                        name = ('graphics:ray_casting[obstacle=%s,emitter=%s,orth=%s:%s,diag=%s,corner_block=%s,'
                                'prio=%s,dirs=%s]' % (obstacle, mode, raster, col_o, col_d, corner_block, prio, dirs))
                        yield (name, 3, fn)
                        return


def _make(obstacle, mode, raster, corner_block, enabled, col_o, col_d, prio):
    order = ('H', 'D', 'V') if prio == 'v>h' else ('V', 'D', 'H')

    def fn(I):
        bg = _bg(I)
        out = [row[:] for row in I]
        rays = []
        for start, d, ccol, tcol in _ports(I, bg, obstacle, mode):
            if d not in enabled:
                continue
            rule = col_d if _cls(d) == 'D' else col_o
            col = ccol if rule == 'core' else (tcol if rule == 'tip' else rule)
            rays.append((_cls(d), _trace(I, bg, start, d, raster, corner_block), col))
        for k in order:
            for cls, cells, col in rays:
                if cls == k:
                    for r, c in cells:
                        out[r][c] = col
        return out
    return fn


FAMILIES = (fam_ray_casting,)
