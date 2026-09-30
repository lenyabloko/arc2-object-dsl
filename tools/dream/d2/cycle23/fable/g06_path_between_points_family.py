"""g06 "paths between two points" family.

Concept: LINE-PROBE WIRE ROUTING (Hightower / Mikami-Tabuchi line-search router) -- electronic design
automation, PCB / IC layout.

Mechanism (one router, applied to every member):
  a trace leaves the source pad and is routed toward the target pad(s) as straight runs.
  * At every cell the probe looks along the allowed directions (rectilinear or octilinear); if a target's entry
    is in clear line of sight it heads straight for the nearest one.
  * Otherwise it keeps its heading; when the run is blocked (obstacle or board edge) it escapes with the
    perpendicular turn that brings it closest to the target.
  * When it reaches a pad the pad becomes the new node: the router hops on to the nearest unvisited pad
    visible from that pad (daisy chain, trace as wide as the pad face) and stops when none is visible.
  * A stub segment is continued along its own axis (toward the target); a point/block pad with nothing in sight
    launches a probe in the direction of the nearest target.
  * Pad entry is either head-on (the run ends on the cell in front of the pad) or at 45 degrees (the run ends on
    the pad's diagonal neighbour facing the source) -- the octilinear PCB style.

Induced from the training pairs (finite domains):
  move set  in {4 (rectilinear), 8 (octilinear)}
  pad entry in {'onto' (head-on), 'diag' (45-degree)}
  source colour, target colour: colours present in every training input; everything else non-background is an
  obstacle; background = most frequent colour; path colour = the single colour of the changed cells.
"""

DIRS4 = ((0, 1), (1, 0), (0, -1), (-1, 0))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _bg(grid):
    cnt = {}
    for row in grid:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _components(grid, colour):
    """4-connected components of one colour, as lists of (r, c)."""
    H, W = len(grid), len(grid[0])
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if grid[r][c] != colour or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in DIRS4:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and grid[ny][nx] == colour and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            comps.append(comp)
    return comps


def _sgn(x):
    return (x > 0) - (x < 0)


def _route(grid, bg, src_col, tgt_col, path_col, moves, entry, srcs=None, tgts=None):
    """Run the line-probe router; returns the routed grid or None when the grid has no single source pad."""
    H, W = len(grid), len(grid[0])
    dirs = DIRS8 if moves == 8 else DIRS4
    if srcs is None:
        srcs = _components(grid, src_col)
    if len(srcs) != 1:
        return None
    src = srcs[0]
    if tgts is None:
        tgts = _components(grid, tgt_col)
    if not tgts:
        return None
    rs = [r for r, _ in src]
    cs = [c for _, c in src]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    if (r1 - r0 + 1) * (c1 - c0 + 1) != len(src):   # the source pad must be a solid rectangle
        return None

    out = [row[:] for row in grid]
    visited = set()
    if moves == 8:
        def metric(a, b):
            return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    else:
        def metric(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def inside(r, c):
        return 0 <= r < H and 0 <= c < W

    def free(r, c):
        return inside(r, c) and out[r][c] == bg

    def centre(cells):
        return (sum(r for r, _ in cells) / len(cells), sum(c for _, c in cells) / len(cells))

    def goals(body):
        """cells that count as 'reached' for each unvisited target, relative to the current node"""
        g = {}
        bc = centre(body)
        for i, t in enumerate(tgts):
            if i in visited:
                continue
            if entry == 'onto':
                for cell in t:
                    g[cell] = i
            else:
                near = min(t, key=lambda cell: (metric(cell, bc), cell))
                gc = (near[0] + _sgn(bc[0] - near[0]), near[1] + _sgn(bc[1] - near[1]))
                if free(*gc) and gc not in g:
                    g[gc] = i
        return g

    def face(body, bodyset, d):
        return [cell for cell in body if (cell[0] + d[0], cell[1] + d[1]) not in bodyset]

    def ray(fc, d, goalmap):
        """line of sight from face fc along d: (free cells before the hit, target index, cells to draw) or None"""
        cur = list(fc)
        dist = 0
        drawn = []
        while True:
            cur = [(r + d[0], c + d[1]) for r, c in cur]
            if not all(inside(r, c) for r, c in cur):
                return None
            ids = set(goalmap.get(cell) for cell in cur)
            if len(ids) == 1 and None not in ids:
                i = next(iter(ids))
                if entry == 'onto':
                    return (dist, i, drawn)
                return (dist, i, drawn + cur)          # 45-degree entry: the entry cell is part of the trace
            if not all(out[r][c] == bg for r, c in cur):
                return None
            drawn.extend(cur)
            dist += 1

    # ---- initial state ---------------------------------------------------------------------------------------
    body, bodyset = src, set(src)
    gl = goals(body)
    if len(src) > 1 and (r0 == r1 or c0 == c1):
        # a stub segment: continue it along its own axis, toward the target
        axis = (0, 1) if r0 == r1 else (1, 0)
        sc = centre(src)
        tc = min((centre(t) for t in tgts), key=lambda p: (metric(p, sc), p))   # nearest target pad's centre
        best = None
        for d in (axis, (-axis[0], -axis[1])):
            lead = max(src, key=lambda cell: cell[0] * d[0] + cell[1] * d[1])
            proj = _sgn((tc[0] - sc[0]) * d[0] + (tc[1] - sc[1]) * d[1])
            run, (r, c) = 0, lead
            while free(r + d[0], c + d[1]):
                r, c, run = r + d[0], c + d[1], run + 1
            edge = (H - 1 - lead[0] if d[0] > 0 else lead[0]) if d[0] else (W - 1 - lead[1] if d[1] > 0 else lead[1])
            key = (proj, run, edge)
            if best is None or key > best[0]:
                best = (key, d, lead)
            elif key == best[0]:
                best = (key, None, None)
        if best[1] is None:
            return None
        heading, front, is_node, is_source = best[1], [best[2]], False, False
    else:
        heading, front, is_node, is_source = None, None, True, True

    # ---- routing loop ------------------------------------------------------------------------------------------
    steps = 0
    while steps < 4 * H * W:
        steps += 1
        if is_node:
            cand = dirs if len(body) == 1 else DIRS4
            faces = {d: face(body, bodyset, d) for d in cand}
        elif len(front) == 1:
            cand = [d for d in dirs if d != (-heading[0], -heading[1])]
            faces = {d: front for d in cand}
        else:
            cand = [heading]
            faces = {heading: front}
        best = None
        for d in cand:
            res = ray(faces[d], d, gl)
            if res is None:
                continue
            key = (res[0], 0 if d == heading else 1)
            if best is None or key < best[0]:
                best = (key, d, res)
        if best is not None:                                   # a target is in line of sight: go there
            _, d, (dist, i, drawn) = best
            for r, c in drawn:
                out[r][c] = path_col
            visited.add(i)
            body, bodyset = tgts[i], set(tgts[i])
            is_node, heading, is_source = True, d, False
            if len(visited) == len(tgts):
                break
            gl = goals(body)
            continue
        if is_node:
            if not is_source or not gl:                        # nothing visible from a pad: the chain ends
                break
            bc = centre(body)                                  # source pad: launch a probe toward the nearest goal
            near = min(gl, key=lambda g: (metric(g, bc), g))
            dr, dc = near[0] - bc[0], near[1] - bc[1]
            if moves == 8 and len(body) == 1:
                heading = (_sgn(dr), _sgn(dc))
            else:
                heading = (_sgn(dr), 0) if abs(dr) >= abs(dc) else (0, _sgn(dc))
            if heading == (0, 0):
                break
            front = face(body, bodyset, heading)
            is_node, is_source = False, False
            continue
        nxt = [(r + heading[0], c + heading[1]) for r, c in front]
        if all(free(r, c) for r, c in nxt):                    # keep the heading
            for r, c in nxt:
                out[r][c] = path_col
            front = nxt
            continue
        if len(front) > 1:                                     # a wide bus cannot turn
            break
        r, c = front[0]                                        # blocked: escape toward the target
        cands = []
        for d in dirs:
            if d == heading or d == (-heading[0], -heading[1]):
                continue
            nr, nc = r + d[0], c + d[1]
            if not free(nr, nc):
                continue
            cands.append((min(metric((nr, nc), g) for g in gl) if gl else 0, d))
        if not cands:
            break
        cands.sort()
        if len(cands) > 1 and cands[0][0] == cands[1][0]:      # no preferred escape direction
            break
        heading = cands[0][1]
    return out


def fam_line_probe_router(train):
    if not train:
        return
    pairs = []
    for p in train:
        i, o = p['input'], p['output']
        if not i or not i[0] or len(i) != len(o) or any(len(a) != len(b) for a, b in zip(i, o)):
            return
        bg = _bg(i)
        changed = [(r, c) for r in range(len(i)) for c in range(len(i[0])) if i[r][c] != o[r][c]]
        if not changed or any(i[r][c] != bg for r, c in changed):
            return
        pcs = {o[r][c] for r, c in changed}
        if len(pcs) != 1:
            return
        pairs.append((i, o, bg, pcs.pop()))
    colours = None
    for i, o, bg, pc in pairs:
        cs = {v for row in i for v in row} - {bg}
        colours = cs if colours is None else colours & cs
    if not colours or len(colours) < 2:
        return
    comp_cache = {}

    def comps(k, colour):
        key = (k, colour)
        if key not in comp_cache:
            comp_cache[key] = _components(pairs[k][0], colour)
        return comp_cache[key]

    # cheap necessary condition: the trace touches the source pad and some target pad in every pair
    changed_sets = []
    for i, o, bg, pc in pairs:
        ch = {(r, c) for r in range(len(i)) for c in range(len(i[0])) if i[r][c] != o[r][c]}
        changed_sets.append({(r + dr, c + dc) for r, c in ch for dr, dc in DIRS8} | ch)

    def touches(k, colour):
        return any(cell in changed_sets[k] for comp in comps(k, colour) for cell in comp)

    src_cands = [c for c in sorted(colours)
                 if all(len(comps(k, c)) == 1 and touches(k, c) for k in range(len(pairs)))]
    tgt_cands = [c for c in sorted(colours) if all(touches(k, c) for k in range(len(pairs)))]
    path_cols = {pc for _, _, _, pc in pairs}
    for src_col in src_cands:
        for tgt_col in tgt_cands:
            if tgt_col == src_col:
                continue
            # path colour: a constant, or the source / target colour when it varies across pairs
            specs = []
            if len(path_cols) == 1:
                specs.append(('const', next(iter(path_cols))))
            else:
                if all(pc == src_col for _, _, _, pc in pairs):
                    specs.append(('source', None))
                if all(pc == tgt_col for _, _, _, pc in pairs):
                    specs.append(('target', None))
            for spec in specs:
                for moves in (4, 8):
                    for entry in ('onto', 'diag'):
                        ok = True
                        for k, (i, o, bg, pc) in enumerate(pairs):
                            res = _route(i, bg, src_col, tgt_col, pc, moves, entry,
                                         srcs=comps(k, src_col), tgts=comps(k, tgt_col))
                            if res != o:
                                ok = False
                                break
                        if not ok:
                            continue

                        def fn(grid, src_col=src_col, tgt_col=tgt_col, spec=spec, moves=moves, entry=entry):
                            bg = _bg(grid)
                            pc = spec[1] if spec[0] == 'const' else (src_col if spec[0] == 'source' else tgt_col)
                            res = _route(grid, bg, src_col, tgt_col, pc, moves, entry)
                            return res if res is not None else [row[:] for row in grid]

                        name = ('eda:line_probe_router[moves=%d,entry=%s,src=%d,tgt=%d,path=%s]'
                                % (moves, entry, src_col, tgt_col, spec[1] if spec[0] == 'const' else spec[0]))
                        yield (name, 3, fn)
                        return


FAMILIES = (fam_line_probe_router,)
