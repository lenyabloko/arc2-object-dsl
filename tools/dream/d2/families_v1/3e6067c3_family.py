"""Family for 3e6067c3 -- graph theory: WALK.

The framed boxes are the vertices of a grid graph (two boxes are adjacent when they face each other across an
unobstructed background corridor).  The row/column of isolated single cells (the legend) spells a walk as a
sequence of vertex labels (the colour of each box's inner patch).  Each step of the walk is drawn as an edge: the
corridor between the two consecutive boxes, as wide as their patches, is painted with the tail vertex's colour.

Everything is induced by role: background = most common colour of the grid; a box = a multi-cell non-background
component whose majority colour is its frame and whose remaining colour is its label; the legend = the singleton
non-background cells, which must be collinear.  The only parameter is the legend reading order, chosen from the
finite domain {forward, reverse} by exact fit on the training pairs (it also absorbs tail/head painting, since
reading the walk backwards and painting with the head colour is the same drawing).
"""
from collections import Counter

ORDERS = ('forward', 'reverse')


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append(cells)
    return comps


def _analyse(g):
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]
    boxes, singles = [], []
    for cells in _components(g, bg):
        if len(cells) == 1:
            singles.append(cells[0])
            continue
        cnt = Counter(g[y][x] for y, x in cells)
        frame = cnt.most_common(1)[0][0]
        patch = [(y, x) for y, x in cells if g[y][x] != frame]
        if not patch:
            continue
        label = Counter(g[y][x] for y, x in patch).most_common(1)[0][0]
        ys, xs = [y for y, _ in cells], [x for _, x in cells]
        pys, pxs = [y for y, _ in patch], [x for _, x in patch]
        boxes.append(dict(label=label, r0=min(ys), r1=max(ys), c0=min(xs), c1=max(xs),
                          pr0=min(pys), pr1=max(pys), pc0=min(pxs), pc1=max(pxs)))
    # legend: collinear singleton cells, read along their common line
    if not singles:
        return bg, boxes, None
    if len({y for y, _ in singles}) == 1:
        legend = [g[y][x] for y, x in sorted(singles, key=lambda p: p[1])]
    elif len({x for _, x in singles}) == 1:
        legend = [g[y][x] for y, x in sorted(singles)]
    else:
        return bg, boxes, None
    return bg, boxes, legend


def _corridor(g, bg, a, b):
    """Cells of the unobstructed background corridor joining facing boxes a and b (None if not adjacent)."""
    # horizontal adjacency: patch rows overlap, boxes separated in columns
    r0, r1 = max(a['pr0'], b['pr0']), min(a['pr1'], b['pr1'])
    if r0 <= r1:
        if a['c1'] < b['c0']:
            cs = range(a['c1'] + 1, b['c0'])
        elif b['c1'] < a['c0']:
            cs = range(b['c1'] + 1, a['c0'])
        else:
            cs = None
        if cs is not None:
            cells = [(y, x) for y in range(r0, r1 + 1) for x in cs]
            if all(g[y][x] == bg for y, x in cells):
                return cells
    c0, c1 = max(a['pc0'], b['pc0']), min(a['pc1'], b['pc1'])
    if c0 <= c1:
        if a['r1'] < b['r0']:
            rs = range(a['r1'] + 1, b['r0'])
        elif b['r1'] < a['r0']:
            rs = range(b['r1'] + 1, a['r0'])
        else:
            rs = None
        if rs is not None:
            cells = [(y, x) for y in rs for x in range(c0, c1 + 1)]
            if all(g[y][x] == bg for y, x in cells):
                return cells
    return None


def _find_walk(g, bg, boxes, seq):
    """Backtracking search for boxes b0..bn with labels seq[i] and consecutive boxes adjacent."""
    by_label = {}
    for i, b in enumerate(boxes):
        by_label.setdefault(b['label'], []).append(i)
    adj = {}

    def corr(i, j):
        if (i, j) not in adj:
            adj[(i, j)] = adj[(j, i)] = _corridor(g, bg, boxes[i], boxes[j])
        return adj[(i, j)]

    def dfs(path):
        k = len(path)
        if k == len(seq):
            return path
        for j in by_label.get(seq[k], []):
            if k == 0 or (j != path[-1] and corr(path[-1], j) is not None):
                res = dfs(path + [j])
                if res:
                    return res
        return None

    path = dfs([])
    if path is None:
        return None
    return [(corr(path[k], path[k + 1]), seq[k]) for k in range(len(path) - 1)]


def _make(order):
    def fn(g):
        bg, boxes, legend = _analyse(g)
        if legend is None or len(legend) < 2:
            return None
        seq = legend if order == 'forward' else legend[::-1]
        edges = _find_walk(g, bg, boxes, seq)
        if edges is None:
            return None
        out = [row[:] for row in g]
        for cells, colour in edges:          # paint each step with its tail vertex's colour
            for y, x in cells:
                out[y][x] = colour
        return out
    return fn


def fam_graph_walk(train):
    for order in ORDERS:
        fn = _make(order)
        try:
            ok = all(fn(p['input']) == p['output'] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ('graph:walk[order=%s,paint=tail]' % order, 3, fn)


FAMILIES = (fam_graph_walk,)
