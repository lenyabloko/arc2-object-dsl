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


def _kinds(pieces, motion):
    kinds = {}                                   # identical pieces are interchangeable
    for col, cells in pieces:
        key = (col, _normalise(cells))
        if key not in kinds:
            kinds[key] = [col, _orientations(cells, motion), 0]
        kinds[key][2] += 1
    return list(kinds.values())


def _tile(gaps, pieces, motion):
    """Exact cover of the gap set by the pieces.  Returns {cell: colour} or None."""
    kinds = _kinds(pieces, motion)
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


# ---------------------------------------------------------------------------------------------------------------
# Speed layer (does not change what is computed).  Per grid we cache the boards that pass area conservation; the
# tiling of a board depends only on (grid, board, conn, motion), so it is cached too.  Area conservation needs no
# grid scan: every cell of a colour in C lies inside C's bounding box, so |gaps| = bbox_area - |cells of C|.
# ---------------------------------------------------------------------------------------------------------------

_GRID_CACHE = {}
_CACHE_MAX = 64


def _analyse(g):
    key = tuple(tuple(row) for row in g)
    info = _GRID_CACHE.get(key)
    if info is not None:
        return info
    bg = _bg(g)
    H, W = len(g), len(g[0])
    colours = sorted({v for row in g for v in row} - {bg})
    count = Counter(v for row in g for v in row)
    boxes = {}
    for r in range(H):
        row = g[r]
        for c in range(W):
            v = row[c]
            b = boxes.get(v)
            if b is None:
                boxes[v] = [r, r, c, c]
            else:
                if r > b[1]:
                    b[1] = r
                if c < b[2]:
                    b[2] = c
                if c > b[3]:
                    b[3] = c
    boards = []                                           # area-conserving boards, in the original subset order
    if len(colours) <= 10:
        total = sum(count[v] for v in colours)
        for C in _subsets(colours):
            r0 = min(boxes[v][0] for v in C); r1 = max(boxes[v][1] for v in C)
            c0 = min(boxes[v][2] for v in C); c1 = max(boxes[v][3] for v in C)
            inside = sum(count[v] for v in C)
            ngaps = (r1 - r0 + 1) * (c1 - c0 + 1) - inside
            piece_area = total - inside
            if ngaps <= 0 or ngaps != piece_area:         # area conservation
                continue
            boards.append((tuple(C), r0, r1, c0, c1))
    info = {"bg": bg, "H": H, "W": W, "colours": colours, "count": count, "boards": boards,
            "gaps": {}, "tile": {}}
    if len(_GRID_CACHE) >= _CACHE_MAX:
        _GRID_CACHE.clear()
    _GRID_CACHE[key] = info
    return info


def _gaps_of(g, info, i):
    gaps = info["gaps"].get(i)
    if gaps is None:
        C, r0, r1, c0, c1 = info["boards"][i]
        cs = set(C)
        gaps = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] not in cs}
        info["gaps"][i] = gaps
    return gaps


def _fill_of(g, info, i, motion, conn):
    key = (i, motion, conn)
    tc = info["tile"]
    if key in tc:
        return tc[key]
    C = info["boards"][i][0]
    gaps = _gaps_of(g, info, i)
    pieces = _components(g, set(info["colours"]) - set(C), conn)
    fill = _tile(gaps, pieces, motion)
    tc[key] = fill
    return fill


def _render(g, info, i, fill, frame):
    C, r0, r1, c0, c1 = info["boards"][i]
    cs = set(C)
    if frame == "crop":
        out = [[g[r][c] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        for (r, c), v in fill.items():
            out[r - r0][c - c0] = v
    else:
        bg, H, W = info["bg"], info["H"], info["W"]
        out = [[bg if (g[r][c] != bg and g[r][c] not in cs) else g[r][c] for c in range(W)] for r in range(H)]
        for (r, c), v in fill.items():
            out[r][c] = v
    return out


def _could_match(g, info, i, target, frame):
    """Necessary condition for _render(g, info, i, fill, frame) == target for ANY exact cover `fill`: the shape and
    every non-gap cell are fixed, and the gap cells carry exactly the colour multiset of the pieces (all pieces are
    used, since the gap area equals the piece area)."""
    C, r0, r1, c0, c1 = info["boards"][i]
    cs = set(C)
    if frame == "crop":
        h, w, oy, ox = r1 - r0 + 1, c1 - c0 + 1, r0, c0
    else:
        h, w, oy, ox = info["H"], info["W"], 0, 0
    if not isinstance(target, list) or len(target) != h:
        return False
    for row in target:
        if not isinstance(row, list) or len(row) != w:
            return False
    bg = info["bg"]
    need = Counter({v: info["count"][v] for v in info["colours"] if v not in cs})
    got = Counter()
    for y in range(h):
        trow = target[y]
        grow = g[y + oy]
        for x in range(w):
            r, c = y + oy, x + ox
            v = grow[c]
            if r0 <= r <= r1 and c0 <= c <= c1 and v not in cs:   # gap cell
                got[trow[x]] += 1
            else:
                base = v if frame == "crop" else (bg if (v != bg and v not in cs) else v)
                if trow[x] != base:
                    return False
    return got == need


def _fits_plan(g, target, frame):
    """Indices of the boards to try for the fit check, or None if no board can produce `target`."""
    info = _analyse(g)
    cand = [i for i in range(len(info["boards"])) if _could_match(g, info, i, target, frame)]
    if not cand:
        return None
    return info, cand[-1], set(cand)


class _GiveUp(Exception):
    pass


def _guided(g, info, i, motion, conn, frame, target):
    """Decide cheaply what the budgeted search of _tile would mean for `target` on candidate board i, following the
    same depth-first order as _tile.  Returns
       "EMPTY" -- the board has no exact cover at all (so _tile returns None whatever its budget);
       "FALSE" -- an exact cover exists and the first one in _tile's order has a piece whose colour differs from
                  target (so _tile returns either None or a grid != target);
       None    -- undecided (the first cover matches target, or a step cap was hit): caller runs the real search.
    Colour-consistent branches are followed in _tile's order; for a colour-inconsistent branch only the existence of
    any cover in its subtree matters, which a piece-first search with symmetry breaking decides quickly."""
    C, r0, r1, c0, c1 = info["boards"][i]
    gaps = _gaps_of(g, info, i)
    kinds = _kinds(_components(g, set(info["colours"]) - set(C), conn), motion)
    oy, ox = (r0, c0) if frame == "crop" else (0, 0)
    want = {(r, c): target[r - oy][c - ox] for (r, c) in gaps}
    bit = {cell: 1 << n for n, cell in enumerate(sorted(gaps))}
    big = [n for n, k in enumerate(kinds) if len(k[1][0]) > 1]
    masks = {}
    for n in big:
        seen, lst = set(), []
        for shape in kinds[n][1]:
            for (ar, ac) in sorted(gaps):
                m = 0
                for dy, dx in shape:
                    b = bit.get((ar + dy, ac + dx))
                    if b is None:
                        m = 0
                        break
                    m |= b
                if m and m not in seen:
                    seen.add(m)
                    lst.append(m)
        masks[n] = lst
    counts = [k[2] for k in kinds]
    last = {}
    steps = [20000]

    def exists(free):                                  # any exact cover of `free` by the remaining pieces?
        steps[0] -= 1
        if steps[0] < 0:
            raise _GiveUp()
        best = None
        for n in big:
            cnt = counts[n]
            if cnt == 0:
                continue
            lst = masks[n]
            valid = [j for j in range(last.get(n, -1) + 1, len(lst)) if lst[j] & free == lst[j]]
            if len(valid) < cnt:
                return False
            if best is None or len(valid) < len(best[1]):
                best = (n, valid)
        if best is None:                               # only single cells left: area conservation => they fit
            return True
        n, valid = best
        save = last.get(n, -1)
        counts[n] -= 1
        try:
            for j in valid:
                last[n] = j
                if exists(free & ~masks[n][j]):
                    return True
            return False
        finally:
            counts[n] += 1
            last[n] = save

    free = set(gaps)

    def walk():
        if not free:
            return None                                # first cover matches target: needs the real search
        steps[0] -= 1
        if steps[0] < 0:
            raise _GiveUp()
        anchor = min(free)
        for n, k in enumerate(kinds):
            if counts[n] == 0:
                continue
            for shape in k[1]:
                cells = [(anchor[0] + dy, anchor[1] + dx) for dy, dx in shape]
                if all(c in free for c in cells):
                    for c in cells:
                        free.discard(c)
                    counts[n] -= 1
                    try:
                        if all(want[c] == k[0] for c in cells):
                            res = walk()
                        else:
                            fm = 0
                            for c in free:
                                fm |= bit[c]
                            last.clear()
                            res = "FALSE" if exists(fm) else "EMPTY"
                    finally:
                        counts[n] += 1
                        for c in cells:
                            free.add(c)
                    if res != "EMPTY":
                        return res
        return "EMPTY"

    try:
        return walk()
    except (_GiveUp, RecursionError):
        return None


def _fits(g, target, plan, motion, conn, frame):
    """Same truth value as _solve(g, motion, conn, frame) == target: the first board that tiles decides; boards after
    the last candidate can only give None or a grid different from target."""
    info, last, cand = plan
    for i in range(last + 1):
        if i in cand:
            verdict = _guided(g, info, i, motion, conn, frame, target)
            if verdict == "EMPTY":
                continue                               # _tile would return None
            if verdict == "FALSE" and i == last:
                return False                           # None or a wrong grid, and no later board can match
        fill = _fill_of(g, info, i, motion, conn)
        if fill is None:
            continue
        return _render(g, info, i, fill, frame) == target
    return False


def _solve(g, motion, conn, frame):
    info = _analyse(g)
    for i in range(len(info["boards"])):
        fill = _fill_of(g, info, i, motion, conn)
        if fill is None:
            continue
        return _render(g, info, i, fill, frame)
    return None


def fam_jigsaw(train):
    for motion in MOTIONS:
        for frame in FRAMES:
            for conn in CONNS:
                def fn(g, motion=motion, conn=conn, frame=frame):
                    return _solve(g, motion, conn, frame)
                try:
                    plans = [_fits_plan(p["input"], p["output"], frame) for p in train]
                    ok = all(pl is not None for pl in plans) and \
                        all(_fits(p["input"], p["output"], pl, motion, conn, frame) for p, pl in zip(train, plans))
                except Exception:
                    ok = False
                if ok:
                    yield ("geometry:jigsaw[motion=%s,conn=%d,frame=%s]" % (motion, conn, frame), 3, fn)
                    break                                  # conn variants of one fit are redundant


FAMILIES = (fam_jigsaw,)
