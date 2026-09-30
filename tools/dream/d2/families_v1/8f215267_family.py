"""Family for 8f215267 -- concept: ABACUS (arithmetic / counting instrument).

Each hollow rectangle is an abacus frame whose midline is the rod.  Every loose piece (connected component) lying
outside the frames is a counter of its colour; it is "moved onto" the frame of the same colour as one bead.  Beads
are strung along the rod of the frame's long axis, starting at the end facing the loose pieces (or an absolute side),
with a fixed pitch.  Loose pieces are then cleared.  Pieces whose colour owns no frame are simply discarded.

All parameters are induced from training over small finite domains:
  conn   in {4, 8}               connectivity used to count loose pieces
  side   in {near, far, lo, hi}  which end of the rod the beads start from
  offset in {0, 1, 2}            empty cells between the frame wall and the first bead
  pitch  in {1, 2, 3}            distance between consecutive beads
Colours are by role only: background = most frequent colour; frame colour = colour of each hollow rectangle.
"""
from collections import Counter


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _components(g, conn, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    comps = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            c = g[i][j]
            stack, cells = [(i, j)], []
            seen[i][j] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == c:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append((c, cells))
    return comps


def _frame(g, c, cells, bg):
    """Return bbox (r0,c0,r1,c1) if cells form exactly the 1-thick border of their bbox with a bg interior."""
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
    if r1 - r0 < 2 or c1 - c0 < 2:
        return None
    border = {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)
              if y in (r0, r1) or x in (c0, c1)}
    if set(cells) != border:
        return None
    for y in range(r0 + 1, r1):
        for x in range(c0 + 1, c1):
            if g[y][x] != bg:
                return None
    return (r0, c0, r1, c1)


def _abacus(g, conn, side, offset, pitch):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    frames, loose = [], []
    for c, cells in _components(g, 4, bg):
        b = _frame(g, c, cells, bg)
        if b:
            frames.append((c, b))
    if not frames:
        return None
    fcells = set()
    for c, (r0, c0, r1, c1) in frames:
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                fcells.add((y, x))
    # loose pieces: counted with the induced connectivity on the grid with frames erased
    g2 = [[bg if (y, x) in fcells else g[y][x] for x in range(W)] for y in range(H)]
    loose = _components(g2, conn, bg)
    count = Counter(c for c, _ in loose)
    lc = [p for _, cells in loose for p in cells]
    out = [[bg] * W for _ in range(H)]
    for c, (r0, c0, r1, c1) in frames:
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                if y in (r0, r1) or x in (c0, c1):
                    out[y][x] = c
        ir0, ic0, ir1, ic1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
        horiz = (ic1 - ic0) >= (ir1 - ir0)
        if horiz:
            fixed = (ir0 + ir1) // 2
            lo, hi = ic0, ic1
            mid = (c0 + c1) / 2.0
            ncen = sum(x for _, x in lc) / len(lc) if lc else mid
        else:
            fixed = (ic0 + ic1) // 2
            lo, hi = ir0, ir1
            mid = (r0 + r1) / 2.0
            ncen = sum(y for y, _ in lc) / len(lc) if lc else mid
        if side == 'lo':
            from_hi = False
        elif side == 'hi':
            from_hi = True
        elif side == 'near':
            from_hi = ncen >= mid
        else:
            from_hi = ncen < mid
        n = count.get(c, 0)
        for k in range(n):
            pos = (hi - offset - k * pitch) if from_hi else (lo + offset + k * pitch)
            if not (lo <= pos <= hi):
                break
            if horiz:
                out[fixed][pos] = c
            else:
                out[pos][fixed] = c
    return out


def fam_abacus(train):
    for conn in (4, 8):
        for side in ('near', 'far', 'lo', 'hi'):
            for offset in (0, 1, 2):
                for pitch in (1, 2, 3):
                    fn = (lambda g, a=conn, s=side, o=offset, p=pitch: _abacus(g, a, s, o, p))
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("arithmetic:abacus[conn=%d,side=%s,offset=%d,pitch=%d]"
                               % (conn, side, offset, pitch), 3, fn)
                        return


FAMILIES = (fam_abacus,)
