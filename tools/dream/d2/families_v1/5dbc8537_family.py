"""Family for ARC task 5dbc8537 -- concept: JIGSAW PUZZLE (geometry / polyomino exact-cover tiling).

Picture: the grid holds a *board* and a *tray*.  The board is a solid slab of one colour (the frame
colour) perforated by holes of the tray's background colour.  The tray is background scattered with
loose pieces (connected blobs of any non-background colours, possibly multi-coloured).  The pieces are
dropped into the holes -- each piece used exactly once, never overlapping, never sticking out -- so that
they cover the holes exactly (an exact cover / jigsaw).  The answer is the completed board.

Everything is induced; nothing about the task's sizes, colours or positions is stored:
  background = the most common colour outside the board
  board      = bounding box of a frame colour c such that the box holds only c and background, some
               cells lie outside it, and the pieces outside tile its background cells exactly
Declared finite parameter domains, chosen in order by fitting the training pairs:
  conn    in (4, 8)                    -- adjacency that glues cells into one piece
  motions in ("translate", "rotate", "dihedral")   -- rigid motions a piece may undergo when placed
If the tiling is not unique, the tie-break keeps the solution found first by filling the holes in
reading order and trying pieces in reading order of where they lie in the tray.
"""
from collections import Counter
import sys

sys.setrecursionlimit(10000)


def _cells_of(g, colour):
    return [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == colour]


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _components(g, bg, skip, conn):
    """Connected blobs of non-background cells outside the box `skip`, in reading order of first cell."""
    H, W = len(g), len(g[0])
    r0, r1, c0, c1 = skip
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if conn == 8:
        nb += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg or (r0 <= r <= r1 and c0 <= c <= c1):
                continue
            stack, blob = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                blob.append((y, x, g[y][x]))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg
                            and not (r0 <= ny <= r1 and c0 <= nx <= c1)):
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            comps.append(blob)
    return comps


def _normalise(blob):
    """Shift so that the first cell in reading order sits at (0, 0)."""
    blob = sorted(blob)
    ar, ac, _ = blob[0]
    return tuple((r - ar, c - ac, v) for r, c, v in blob)


MOTIONS = {
    "translate": [lambda r, c: (r, c)],
    "rotate": [lambda r, c: (r, c), lambda r, c: (c, -r), lambda r, c: (-r, -c), lambda r, c: (-c, r)],
}
MOTIONS["dihedral"] = MOTIONS["rotate"] + [lambda r, c, f=f: f(r, -c) for f in MOTIONS["rotate"]]


def _orientations(blob, motion):
    out = []
    for f in MOTIONS[motion]:
        o = _normalise([f(r, c) + (v,) for r, c, v in blob])
        if o not in out:
            out.append(o)
    return out


def _tile(holes, pieces, motion):
    """Exact cover of the hole cells by every piece, each used once.  Returns {cell: colour} or None."""
    holes = set(holes)
    if sum(len(p) for p in pieces) != len(holes):
        return None
    order = sorted(holes)
    kinds, count = [], []
    for p in pieces:  # identical pieces are interchangeable: group them to avoid symmetric search
        key = _normalise(p)
        for i, (k, _) in enumerate(kinds):
            if k == key:
                count[i] += 1
                break
        else:
            kinds.append((key, _orientations(p, motion)))
            count.append(1)
    filled = {}
    budget = [200000]

    def search(pos):
        while pos < len(order) and order[pos] in filled:
            pos += 1
        if pos == len(order):
            return True
        budget[0] -= 1
        if budget[0] < 0:
            return False
        ar, ac = order[pos]
        for i, (_, orients) in enumerate(kinds):
            if not count[i]:
                continue
            for o in orients:
                cells = [(ar + r, ac + c, v) for r, c, v in o]
                if all((r, c) in holes and (r, c) not in filled for r, c, _ in cells):
                    for r, c, v in cells:
                        filled[(r, c)] = v
                    count[i] -= 1
                    if search(pos + 1):
                        return True
                    count[i] += 1
                    for r, c, _ in cells:
                        del filled[(r, c)]
        return False

    return dict(filled) if search(0) else None


def complete_board(g, conn, motion):
    H, W = len(g), len(g[0])
    colours = Counter(v for row in g for v in row)
    cands = []
    for frame in colours:
        box = _bbox(_cells_of(g, frame))
        r0, r1, c0, c1 = box
        outside = Counter(g[r][c] for r in range(H) for c in range(W)
                          if not (r0 <= r <= r1 and c0 <= c <= c1))
        if not outside:
            continue
        bg = outside.most_common(1)[0][0]
        if bg == frame:
            continue
        inside = {g[r][c] for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
        if not inside <= {frame, bg} or bg not in inside:
            continue
        cands.append(((r1 - r0 + 1) * (c1 - c0 + 1), frame, bg, box))
    for _, frame, bg, box in sorted(cands, key=lambda t: -t[0]):
        r0, r1, c0, c1 = box
        holes = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == bg]
        pieces = _components(g, bg, box, conn)
        if not pieces:
            continue
        fill = _tile(holes, pieces, motion)
        if fill is None:
            continue
        return [[fill.get((r, c), g[r][c]) for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    return None


def fam_jigsaw(train):
    for motion in ("translate", "rotate", "dihedral"):
        for conn in (4, 8):
            def fn(g, conn=conn, motion=motion):
                return complete_board(g, conn, motion)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("geometry:jigsaw[conn=%d,motion=%s]" % (conn, motion), 3, fn)
                return


FAMILIES = (fam_jigsaw,)
