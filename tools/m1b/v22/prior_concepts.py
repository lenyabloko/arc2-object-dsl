"""Prior concepts as lattice attributes (cycle 20, reviewer directive 2026-09-29).

Principle (Len): instead of enumerating conditions, fit the case into an outside prior - that is the purpose of
priors as inductive bias for MDL.  A prior concept is defined without reference to any task; its definition is
paid once here, so a rule that uses it is one term.  Several concepts come from lifting the grid into a richer
world: the grid is a view (a cut) of a 3D scene of rigid shapes that can move, fall, hide one another and fit
into one another.

Each concept is a node attribute 'P:<name>' added by occupancy2.prepare; the RDR learners then prefer a single
prior concept to a conjunction of surface attributes (see occupancy2.learn_*).

  P:cavity        a background region that is the cavity of ONE box shape (empty space that stays enclosed
                  under every independent rigid motion of the shapes; the frame is a cut, not a wall)
  P:free_<d>      the shape can move one step in direction d (up/down/left/right) without leaving the view
                  or hitting another shape (motion);  P:supported = not free_down (gravity)
  P:mirror_pair   another shape is this shape's mirror image (left-right or up-down) and the shape itself is
                  not symmetric on that axis (geometry: reflection)
  P:between       the shape lies between two other shapes of one colour on a common row or column
  P:key / P:lock  the shape fits exactly (translation) into a hole of another shape / has a hole that another
                  shape fits exactly (mechanics: lock and key)
  P:occluded      the shape is a rectangle partly hidden behind shapes touching it: its bbox is covered by the
                  shape plus the shapes in front (optics: amodal completion);  P:occluder = a shape in front
"""

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIRS = (("up", -1, 0), ("down", 1, 0), ("left", 0, -1), ("right", 0, 1))


def _bbox(pix):
    ys = [r for r, _ in pix]; xs = [c for _, c in pix]
    return min(ys), min(xs), max(ys), max(xs)


def _norm(pix):
    r0, c0, _, _ = _bbox(pix)
    return frozenset((r - r0, c - c0) for r, c in pix)


def _mirror(s, axis):
    h = max(r for r, _ in s) + 1; w = max(c for _, c in s) + 1
    return frozenset((r, w - 1 - c) for r, c in s) if axis == "lr" else frozenset((h - 1 - r, c) for r, c in s)


def _holes(pix):
    """components of cells enclosed by pix (not reachable from outside its bbox, 4-leak)."""
    r0, c0, r1, c1 = _bbox(pix)
    free = {(r, c) for r in range(r0 - 1, r1 + 2) for c in range(c0 - 1, c1 + 2)} - set(pix)
    st = [(r0 - 1, c0 - 1)]; seen = set(st)
    while st:
        r, c = st.pop()
        for dr, dc in N4:
            q = (r + dr, c + dc)
            if q in free and q not in seen:
                seen.add(q); st.append(q)
    inner = free - seen; out = []; done = set()
    for q in sorted(inner):
        if q in done: continue
        comp = {q}; st = [q]; done.add(q)
        while st:
            r, c = st.pop()
            for dr, dc in N4:
                x = (r + dr, c + dc)
                if x in inner and x not in done:
                    done.add(x); comp.add(x); st.append(x)
        out.append(frozenset(comp))
    return out


def cavity_cells(grid, r):
    """cells of the cavities of box shapes (see module doc); r = the empty colour."""
    h, w = len(grid), len(grid[0]); out = set(); seen = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] != r or (y, x) in seen: continue
            comp = {(y, x)}; st = [(y, x)]; seen.add((y, x))
            while st:
                a, b = st.pop()
                for dy, dx in N4:
                    q = (a + dy, b + dx)
                    if 0 <= q[0] < h and 0 <= q[1] < w and q not in seen and grid[q[0]][q[1]] == r:
                        seen.add(q); comp.add(q); st.append(q)
            y0, x0, y1, x1 = _bbox(comp)
            if len(comp) != (y1 - y0 + 1) * (x1 - x0 + 1): continue
            ring = [(a, b) for a in range(y0 - 1, y1 + 2) for b in range(x0 - 1, x1 + 2)
                    if not (y0 <= a <= y1 and x0 <= b <= x1) and 0 <= a < h and 0 <= b < w]
            cols = {grid[a][b] for a, b in ring}
            if len(cols) != 1: continue
            wc = cols.pop(); ok = True
            for cy, cx, dy, dx in ((y0 - 1, x0 - 1, -1, -1), (y0 - 1, x1 + 1, -1, 1), (y1 + 1, x0 - 1, 1, -1), (y1 + 1, x1 + 1, 1, 1)):
                if not (0 <= cy < h and 0 <= cx < w): continue
                for ey, ex in ((cy + dy, cx), (cy, cx + dx)):
                    if 0 <= ey < h and 0 <= ex < w and grid[ey][ex] == wc: ok = False
            if ok: out |= comp
    return out


def concepts(nodes, grid, bg):
    H, W = len(grid), len(grid[0])
    n = len(nodes)
    pixs = [n_["pix"] for n_ in nodes]; cols = [n_["color"] for n_ in nodes]
    owner = {p: i for i, px in enumerate(pixs) for p in px}
    fg = [cols[i] != bg for i in range(n)]
    shapes = [_norm(px) for px in pixs]; boxes = [_bbox(px) for px in pixs]
    cav = cavity_cells(grid, bg) if any(c == bg for c in cols) else set()
    holes = [_holes(px) if fg[i] and len(px) >= 8 else [] for i, px in enumerate(pixs)]
    hole_shapes = [{_norm(hc) for hc in hs if all(grid[r][c] == bg for r, c in hc)} for hs in holes]
    out = [set() for _ in range(n)]
    for i in range(n):
        a = out[i]; px = pixs[i]
        if not fg[i]:
            if cav and px <= cav: a.add("P:cavity")
            continue
        # motion / gravity
        for d, dy, dx in DIRS:
            ok = True
            for r, c in px:
                q = (r + dy, c + dx)
                if not (0 <= q[0] < H and 0 <= q[1] < W): ok = False; break
                j = owner.get(q)
                if j is not None and j != i and fg[j]: ok = False; break
                if j is None and grid[q[0]][q[1]] != bg: ok = False; break
            if ok: a.add("P:free_" + d)
        if "P:free_down" not in a: a.add("P:supported")
        # geometry: reflection partner
        s = shapes[i]
        for ax in ("lr", "ud"):
            m = _mirror(s, ax)
            if m != s and any(j != i and fg[j] and shapes[j] == m for j in range(n)):
                a.add("P:mirror_pair"); break
        # between two same-colour shapes on a row / column
        r0, c0, r1, c1 = boxes[i]
        for colr in {cols[j] for j in range(n) if j != i and fg[j] and cols[j] is not None}:
            js = [j for j in range(n) if j != i and cols[j] == colr]
            row = [j for j in js if not (boxes[j][2] < r0 or boxes[j][0] > r1)]
            col = [j for j in js if not (boxes[j][3] < c0 or boxes[j][1] > c1)]
            if (any(boxes[j][3] < c0 for j in row) and any(boxes[j][1] > c1 for j in row)) or \
               (any(boxes[j][2] < r0 for j in col) and any(boxes[j][0] > r1 for j in col)):
                a.add("P:between"); break
        # mechanics: lock and key
        if any(j != i and s in hole_shapes[j] for j in range(n)): a.add("P:key")
        if hole_shapes[i] and any(j != i and fg[j] and shapes[j] in hole_shapes[i] for j in range(n)): a.add("P:lock")
        # optics: amodal completion of a partly hidden rectangle
        area = (r1 - r0 + 1) * (c1 - c0 + 1)
        if len(px) < area and area >= 4:
            covered = set(px); front = set()
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    j = owner.get((r, c))
                    if j is not None and j != i and fg[j]: covered.add((r, c)); front.add(j)
            if len(covered) == area and front and all(any((r + dy, c + dx) in px for r, c in pixs[j] for dy, dx in N4) for j in front):
                a.add("P:occluded")
                for j in front: out[j].add("P:occluder")
    return out
