"""38007db0 -- statistics: OUTLIER (odd one out).

The grid is a lattice of equal tiles separated by grid lines of one colour.  Along each rank of tiles
(each tile-row, or each tile-column) all tiles are copies of one motif except one: the outlier.  The
output is one rank-wide strip of the lattice (with its grid lines) holding, for every rank, that
rank's outlier tile.

Induced from training: lattice colour (the colour of the full-length grid lines, by role), the rank
axis ('row' = one outlier per tile-row, output is a vertical strip; 'col' = transposed).
Outlier = tile with the largest total Hamming distance to the other tiles of its rank (unique motif
when the rest agree); ties broken by global rarity of the motif, then by position.
"""


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _lattice(g):
    """Return (colour, row_lines, col_lines) of a lattice of full-length uniform lines, or None."""
    H, W = len(g), len(g[0])
    rows = {}
    for r in range(H):
        if len(set(g[r])) == 1:
            rows.setdefault(g[r][0], []).append(r)
    cols = {}
    for c in range(W):
        col = {g[r][c] for r in range(H)}
        if len(col) == 1:
            cols.setdefault(g[0][c], []).append(c)
    common = [k for k in rows if k in cols]
    if not common:
        return None
    k = max(common, key=lambda k: len(rows[k]) + len(cols[k]))
    return k, rows[k], cols[k]


def _segments(n, lines):
    """Maximal index runs in range(n) not on a line."""
    ls = set(lines)
    segs, cur = [], []
    for i in range(n):
        if i in ls:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        segs.append(cur)
    return segs


def _outlier_strip(g):
    """Rank = tile-row; returns strip grid (one tile column wide incl. its grid lines)."""
    lat = _lattice(g)
    if lat is None:
        return None
    k, rl, cl = lat
    H, W = len(g), len(g[0])
    rsegs, csegs = _segments(H, rl), _segments(W, cl)
    if len(csegs) < 2 or len({len(s) for s in csegs}) != 1 or len({len(s) for s in rsegs}) != 1:
        return None

    def tile(rs, cs):
        return tuple(tuple(g[r][c] for c in cs) for r in rs)

    tiles = [[tile(rs, cs) for cs in csegs] for rs in rsegs]
    freq = {}
    for row in tiles:
        for t in row:
            freq[t] = freq.get(t, 0) + 1

    def dist(a, b):
        return sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))

    # template strip: columns of the first tile column plus its adjacent grid lines
    c0, c1 = csegs[0][0], csegs[0][-1]
    lo = c0 - 1 if c0 - 1 in set(cl) else c0
    hi = c1 + 1 if c1 + 1 in set(cl) else c1
    out = [list(g[r][lo:hi + 1]) for r in range(H)]
    for ri, rs in enumerate(rsegs):
        row = tiles[ri]
        best = max(range(len(row)),
                   key=lambda j: (sum(dist(row[j], row[i]) for i in range(len(row)) if i != j),
                                  -freq[row[j]], -j))
        t = row[best]
        for a, r in enumerate(rs):
            for b, c in enumerate(csegs[0]):
                out[r][c - lo] = t[a][b]
    return out


def _make(axis):
    def fn(g):
        if axis == 'row':
            return _outlier_strip(g)
        s = _outlier_strip(_transpose(g))
        return None if s is None else _transpose(s)
    return fn


def fam_outlier(train):
    for axis in ('row', 'col'):
        fn = _make(axis)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("statistics:outlier[axis=%s]" % axis, 3, fn)


FAMILIES = (fam_outlier,)
