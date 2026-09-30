"""Family for ARC task de809cff -- concept: GROMMET (mechanics / sheet-metal & textiles).

The canvas shows overlapping rectangular sheets (layers) of a few colours, stacked like paper: where two sheets
overlap only the upper one is visible.  The picture is dirty: loose specks of sheet colour lie on the table or on
the wrong sheet, and some cells of each sheet are punched out (background showing through = holes).
The transformation cleans the picture and puts a grommet into every punched hole: the hole itself gets the
eyelet colour (mark), and its surrounding ring (the neighbourhood of the hole) is made of the partner sheet's
material.  Specks disappear (off-sheet -> background, on-sheet -> the sheet's colour).

Recovery of the sheets: per colour, a speck filter (2-core of the 4-adjacency graph = iterated pruning of cells
with < 2 same-colour neighbours; or a 2x2 morphological opening) removes the specks; every 4-connected component
of the filtered colour mask spans one sheet (its bounding box = the sheet, occluded parts included); a sheet lies
above another when its colour dominates their overlap (topological sort gives the painter's order).

Roles / parameters (all induced from train, finite domains):
  bg      : a colour present in every train input and output (canvas / table)
  mark    : a colour present in every train output and absent from every train input (eyelet colour)
  DENOISE : speck filter in ('core2', 'open2')
  RING    : neighbourhood of the grommet ring in ('moore', 'vonneumann')
Partner sheet colour of a sheet = the other sheet colour that shares the most boundary/overlap with it.
"""
from collections import Counter, deque

RINGS = {
    'moore': ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)),
    'vonneumann': ((-1, 0), (1, 0), (0, -1), (0, 1)),
}


def _opened(g, col, K):
    """Cells of colour `col` covered by some KxK block made entirely of `col` (morphological opening)."""
    H, W = len(g), len(g[0])
    keep = [[False] * W for _ in range(H)]
    for r in range(H - K + 1):
        for c in range(W - K + 1):
            if all(g[r + i][c + j] == col for i in range(K) for j in range(K)):
                for i in range(K):
                    for j in range(K):
                        keep[r + i][c + j] = True
    return keep


def _core(g, col, K):
    """K-core of the 4-adjacency graph of `col` cells: repeatedly prune cells with fewer than K same-colour
    4-neighbours (loose specks and spurs of specks fall away, sheet bodies stay)."""
    H, W = len(g), len(g[0])
    keep = [[g[y][x] == col for x in range(W)] for y in range(H)]
    changed = True
    while changed:
        changed = False
        for y in range(H):
            for x in range(W):
                if keep[y][x]:
                    n = sum(1 for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))
                            if 0 <= y + dy < H and 0 <= x + dx < W and keep[y + dy][x + dx])
                    if n < K:
                        keep[y][x] = False; changed = True
    return keep


DENOISE = {'core2': (_core, 2), 'open2': (_opened, 2)}


def _sheets(g, bg, dn):
    """Return list of sheets (colour, r0, r1, c0, c1)."""
    H, W = len(g), len(g[0])
    colours = sorted({v for row in g for v in row} - {bg})
    sheets = []
    for col in colours:
        f, k = DENOISE[dn]
        keep = f(g, col, k)
        seen = [[False] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if keep[r][c] and not seen[r][c]:
                    seen[r][c] = True
                    q = deque([(r, c)]); r0 = r1 = r; c0 = c1 = c
                    while q:
                        y, x = q.popleft()
                        r0, r1, c0, c1 = min(r0, y), max(r1, y), min(c0, x), max(c1, x)
                        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W and keep[ny][nx] and not seen[ny][nx]:
                                seen[ny][nx] = True; q.append((ny, nx))
                    sheets.append((col, r0, r1, c0, c1))
    return sheets


def _overlap(a, b):
    r0, r1 = max(a[1], b[1]), min(a[2], b[2])
    c0, c1 = max(a[3], b[3]), min(a[4], b[4])
    return (r0, r1, c0, c1) if r0 <= r1 and c0 <= c1 else None


def _stack(g, sheets):
    """Stacking order bottom -> top: sheet a lies above b when a's colour dominates their overlap; topological sort."""
    n = len(sheets)
    above = {i: set() for i in range(n)}          # above[b] = sheets lying on b
    indeg = [0] * n
    for i, a in enumerate(sheets):
        for j, b in enumerate(sheets):
            if i < j and a[0] != b[0]:
                ov = _overlap(a, b)
                if not ov:
                    continue
                cnt = Counter(g[y][x] for y in range(ov[0], ov[1] + 1) for x in range(ov[2], ov[3] + 1))
                lo, hi = (j, i) if cnt[a[0]] > cnt[b[0]] else (i, j)
                above[lo].add(hi); indeg[hi] += 1
    order, ready = [], [i for i in range(n) if indeg[i] == 0]
    while ready:
        i = ready.pop(0); order.append(i)
        for j in sorted(above[i]):
            indeg[j] -= 1
            if indeg[j] == 0:
                ready.append(j)
    order += [i for i in range(n) if i not in order]   # cycles (should not happen): keep index order
    return order


def _partner(sheets, idx):
    """Colour of the other-coloured sheet that touches/overlaps sheet idx the most (grown by one cell)."""
    a = sheets[idx]
    grown = (a[0], a[1] - 1, a[2] + 1, a[3] - 1, a[4] + 1)
    score = Counter()
    for j, b in enumerate(sheets):
        if b[0] == a[0]:
            continue
        ov = _overlap(grown, b)
        if ov:
            score[b[0]] += (ov[1] - ov[0] + 1) * (ov[3] - ov[2] + 1)
    if score:
        return max(score, key=lambda k: (score[k], -k))
    others = Counter(s[0] for s in sheets if s[0] != a[0])
    return others.most_common(1)[0][0] if others else a[0]


def _grommet(g, bg, mark, dn, ring):
    H, W = len(g), len(g[0])
    sheets = _sheets(g, bg, dn)
    owner = [[-1] * W for _ in range(H)]
    for i in _stack(g, sheets):                                      # paint bottom -> top
        col, r0, r1, c0, c1 = sheets[i]
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                owner[y][x] = i
    out = [[bg if owner[y][x] < 0 else sheets[owner[y][x]][0] for x in range(W)] for y in range(H)]
    holes = [(y, x) for y in range(H) for x in range(W) if owner[y][x] >= 0 and g[y][x] == bg]
    partner = {}
    for (y, x) in holes:
        i = owner[y][x]
        if i not in partner:
            partner[i] = _partner(sheets, i)
        for dy, dx in RINGS[ring]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                out[ny][nx] = partner[i]
    for (y, x) in holes:
        out[y][x] = mark
    return out


def fam_grommet(train):
    ins = [p["input"] for p in train]
    outs = [p["output"] for p in train]
    cin = [{v for row in g for v in row} for g in ins]
    cout = [{v for row in g for v in row} for g in outs]
    bgs = sorted(set.intersection(*cin) & set.intersection(*cout))
    marks = sorted(set.intersection(*cout) - set.union(*cin))
    if any(len(i) != len(o) or len(i[0]) != len(o[0]) for i, o in zip(ins, outs)):
        return
    for bg in bgs:
        for mark in marks:
            for dn in DENOISE:
                for ring in RINGS:
                    fn = (lambda bg, mark, dn, ring: lambda g: _grommet(g, bg, mark, dn, ring))(bg, mark, dn, ring)
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("mechanics:grommet[bg=%d,mark=%d,denoise=%s,ring=%s]" % (bg, mark, dn, ring), 3, fn)
                        return


FAMILIES = (fam_grommet,)
