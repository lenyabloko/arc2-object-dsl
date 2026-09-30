"""Family for ARC task e8686506 -- concept: JIGSAW PUZZLE (geometry / tiling: exact cover of a board by polyomino pieces).

Reading of the task
-------------------
One figure is the puzzle board: its bounding box contains empty (background) cells -- the gaps.  Every other object
in the grid is a loose puzzle piece (a single-colour polyomino).  Solving the jigsaw means sliding every piece into
the board so that the pieces cover the gaps exactly, each piece used once, no overlaps.  The answer is the completed
board (cropped to its bounding box).

How the parts are found (no task constants):
  * background = most frequent colour of the input.
  * board      = the smallest set of colours C whose bounding box has exactly as many gap cells (cells not of a
                 colour in C) as there are piece cells outside C -- area conservation -- AND whose gaps admit an
                 exact cover by those pieces.  (A board may be several colours / several disconnected strokes.)
  * pieces     = connected single-colour components of every non-background colour not in C.
  * solver     = exact-cover backtracking: take the first uncovered gap cell in reading order and try every distinct
                 unused piece (in every allowed orientation) anchored there; first complete tiling wins.

Parameters (declared finite domains, induced from train; every exact fit is yielded, simplest first):
  motion in ("translate", "dihedral")   pieces only slide, or may also rotate / flip.
  conn   in (4, 8)                      adjacency used to cut the loose pieces.
  frame  in ("crop", "inplace")         answer is the board's bounding box, or the whole grid with the pieces moved.
"""

from collections import Counter

MOTIONS = ("translate", "dihedral")
CONNS = (4, 8)
FRAMES = ("crop", "inplace")


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, colours, conn):
    """Single-colour connected components of the given colours: list of (colour, frozenset(cells))."""
    H, W = len(g), len(g[0])
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        steps += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen = set()
    out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] not in colours:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], set()
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cells.add((y, x))
                for dy, dx in steps:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] == col:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            out.append((col, frozenset(cells)))
    return out


def _normalise(cells):
    """Offsets relative to the first cell in reading order (so the anchor is the piece's top-left-most cell)."""
    cells = sorted(cells)
    y0, x0 = cells[0]
    return tuple((y - y0, x - x0) for y, x in cells)


def _orientations(cells, motion):
    shapes = {_normalise(cells)}
    if motion == "dihedral":
        cur = list(cells)
        for _ in range(4):
            cur = [(x, -y) for y, x in cur]                     # rotate 90 degrees
            shapes.add(_normalise(cur))
            shapes.add(_normalise([(y, -x) for y, x in cur]))  # mirror
    return sorted(shapes)


def _tile(gaps, pieces, motion):
    """Exact cover of the gap set by the pieces.  Returns {cell: colour} or None."""
    kinds = {}                                   # identical pieces are interchangeable
    for col, cells in pieces:
        key = (col, _normalise(cells))
        if key not in kinds:
            kinds[key] = [col, _orientations(cells, motion), 0]
        kinds[key][2] += 1
    kinds = list(kinds.values())
    free = set(gaps)
    placed = {}
    budget = [200000]

    def solve():
        if not free:
            return True
        budget[0] -= 1
        if budget[0] < 0:
            return False
        anchor = min(free)                       # first uncovered gap cell in reading order
        for k in kinds:
            if k[2] == 0:
                continue
            for shape in k[1]:
                cells = [(anchor[0] + dy, anchor[1] + dx) for dy, dx in shape]
                if all(c in free for c in cells):
                    for c in cells:
                        free.discard(c)
                        placed[c] = k[0]
                    k[2] -= 1
                    if solve():
                        return True
                    k[2] += 1
                    for c in cells:
                        free.add(c)
                        del placed[c]
        return False

    return dict(placed) if solve() else None


def _subsets(items):
    items = sorted(items)
    out = []
    for m in range(1, 1 << len(items)):
        out.append([items[i] for i in range(len(items)) if m >> i & 1])
    out.sort(key=lambda s: (len(s), s))
    return out


def _solve(g, motion, conn, frame):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    colours = sorted({v for row in g for v in row} - {bg})
    count = Counter(v for row in g for v in row)
    if len(colours) > 10:
        return None
    for C in _subsets(colours):
        cs = set(C)
        board = [(r, c) for r in range(H) for c in range(W) if g[r][c] in cs]
        r0 = min(r for r, _ in board); r1 = max(r for r, _ in board)
        c0 = min(c for _, c in board); c1 = max(c for _, c in board)
        gaps = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] not in cs}
        piece_area = sum(count[v] for v in colours if v not in cs)
        if not gaps or len(gaps) != piece_area:          # area conservation
            continue
        pieces = _components(g, set(colours) - cs, conn)
        fill = _tile(gaps, pieces, motion)
        if fill is None:
            continue
        if frame == "crop":
            out = [[g[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            for (r, c), v in fill.items():
                out[r - r0][c - c0] = v
        else:
            out = [[bg if (g[r][c] != bg and g[r][c] not in cs) else g[r][c] for c in range(W)] for r in range(H)]
            for (r, c), v in fill.items():
                out[r][c] = v
        return out
    return None


def fam_jigsaw(train):
    for motion in MOTIONS:
        for frame in FRAMES:
            for conn in CONNS:
                def fn(g, motion=motion, conn=conn, frame=frame):
                    return _solve(g, motion, conn, frame)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("geometry:jigsaw[motion=%s,conn=%d,frame=%s]" % (motion, conn, frame), 3, fn)
                    break                                  # conn variants of one fit are redundant


FAMILIES = (fam_jigsaw,)
