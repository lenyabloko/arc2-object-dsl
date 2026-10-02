"""Line expansion for 4e45f183: board of tiles rearranged by where each tile's pattern sits inside it (test-blind; train pairs only)."""
from collections import Counter

CARD = "4e45f183"
LINE = "The 3x3 board of tiles is rearranged so each tile moves to the board position that its pattern occupies inside the tile (top-left pattern -> top-left slot, symmetric pattern -> centre)."
READING = {
    "generator": "Cut the board into its equal tiles; for each tile locate its pattern (the non-background cells) relative to the tile's own centre "
                 "and copy the whole tile, unchanged, into the board slot at that relative position (a pattern centred on the tile, e.g. a symmetric one, goes to the centre slot).",
    "stop": "Every tile is drawn exactly once into its slot; separators/frame are kept; empty tiles (no pattern) fill the slots left over in reading order.",
    "params": "board ∈ {separator lines, equal k x k split with k ∈ {2,3,4,5}} · bg ∈ {majority over all tiles, majority per tile} · "
              "locator ∈ {centroid of pattern cells, bounding-box centre} · quantizer ∈ {sign vs tile centre (3-slot axes only), uniform bins over the tile}",
    "participants": "tiles = maximal blocks of cells between full uniform separator rows/columns of one colour (or equal blocks of a k x k split), all the same size; "
                    "background = majority colour of the tile cells; pattern = the tile's non-background cells.",
    "preconditions": "The board splits into an R x C array (R, C >= 2) of equal-size tiles; output has the input's shape; "
                     "the tile-to-slot map induced by pattern positions is a bijection among non-empty tiles.",
}


# ---------------------------------------------------------------- board finding
def _runs(flags):
    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None: start = i
        if not f and start is not None:
            out.append((start, i)); start = None
    return out


def board_sep(g):
    """Tiles delimited by full uniform rows/cols of one separator colour -> (rows[(a,b)], cols[(a,b)]) or None."""
    H, W = len(g), len(g[0])
    best = None
    for s in sorted({v for row in g for v in row}):
        sr = [all(v == s for v in g[r]) for r in range(H)]
        sc = [all(g[r][c] == s for r in range(H)) for c in range(W)]
        if not any(sr) and not any(sc): continue
        rows = _runs([not f for f in sr])
        cols = _runs([not f for f in sc])
        if len(rows) < 2 or len(cols) < 2: continue
        if len({b - a for a, b in rows}) != 1 or len({b - a for a, b in cols}) != 1: continue
        n = len(rows) * len(cols)
        if best is None or n > best[0]: best = (n, rows, cols)
    return None if best is None else (best[1], best[2])


def board_split(g, k):
    H, W = len(g), len(g[0])
    if H % k or W % k or H // k < 2 or W // k < 2: return None
    h, w = H // k, W // k
    return [(i * h, (i + 1) * h) for i in range(k)], [(j * w, (j + 1) * w) for j in range(k)]


# ---------------------------------------------------------------- pattern location
def _locate(cells, h, w, loc):
    """-> (2*row_pos, 2*col_pos) in doubled tile coordinates (exact integers / fractions avoided)."""
    if loc == "centroid":
        n = len(cells)
        return (2 * sum(r for r, _ in cells), n), (2 * sum(c for _, c in cells), n)
    rs = [r for r, _ in cells]; cs = [c for _, c in cells]
    return (min(rs) + max(rs), 1), (min(cs) + max(cs), 1)


def _quant(pos, size, k, quant):
    num, den = pos  # position = num / (2*den) in cell coordinates
    if quant == "sign":
        # compare against tile centre (size-1)/2  ->  num/den vs (size-1)
        d = num - den * (size - 1)
        return 0 if d < 0 else (2 if d > 0 else 1)
    # uniform bins: index = floor((pos + 0.5) / size * k) = floor((num + den) * k / (2*den*size))
    return min(k - 1, max(0, ((num + den) * k) // (2 * den * size)))


def solve(g, board, bgmode, loc, quant):
    H, W = len(g), len(g[0])
    bd = board_sep(g) if board == "sep" else board_split(g, int(board[5:]))
    if bd is None: return None
    rows, cols = bd
    R, C = len(rows), len(cols)
    if quant == "sign" and (R != 3 or C != 3): return None
    h, w = rows[0][1] - rows[0][0], cols[0][1] - cols[0][0]
    tiles = {}
    for i, (r0, r1) in enumerate(rows):
        for j, (c0, c1) in enumerate(cols):
            tiles[(i, j)] = [row[c0:c1] for row in g[r0:r1]]
    if bgmode == "global":
        cnt = Counter(v for t in tiles.values() for row in t for v in row)
        gbg = cnt.most_common(1)[0][0]
    dest, empty = {}, []
    for key in sorted(tiles):
        t = tiles[key]
        bg = gbg if bgmode == "global" else Counter(v for row in t for v in row).most_common(1)[0][0]
        cells = [(r, c) for r in range(h) for c in range(w) if t[r][c] != bg]
        if not cells:
            empty.append(key); continue
        pr, pc = _locate(cells, h, w, loc)
        dest[key] = (_quant(pr, h, R, quant), _quant(pc, w, C, quant))
    if len(set(dest.values())) != len(dest): return None
    free = [s for s in sorted(tiles) if s not in set(dest.values())]
    for key, s in zip(empty, free): dest[key] = s
    out = [list(row) for row in g]
    for key, (si, sj) in dest.items():
        r0, c0 = rows[si][0], cols[sj][0]
        t = tiles[key]
        for r in range(h):
            for c in range(w):
                out[r0 + r][c0 + c] = t[r][c]
    return out


BOARDS = ["sep", "split2", "split3", "split4", "split5"]


def fam(train):
    if not train: return
    if any(len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0]) for p in train): return
    k = 0
    for board in BOARDS:
        for quant in ("sign", "bins"):
            for loc in ("centroid", "bbox"):
                for bgmode in ("global", "tile"):
                    fn = (lambda b, bm, l, q: (lambda g: solve(g, b, bm, l, q)))(board, bgmode, loc, quant)
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("tilepos:%s:%s:%s:%s" % (board, quant, loc, bgmode), 10 + k, fn)
                        k += 1


FAMILIES = [fam]
