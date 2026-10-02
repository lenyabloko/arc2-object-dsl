"""Reviewer line family for ARC card 7ed72f31 (optics: mirror reflection).

Each object (connected non-background component) consists of a shape glued
to a "mirror" made of cells of one role colour.  The mirror's fixed-point set
decides the isometry applied to the shape:
  * one mirror cell            -> point mirror (central inversion through it)
  * straight segment (row)     -> reflection across that row
  * straight segment (column)  -> reflection across that column
  * straight segment (diagonal / anti-diagonal) -> reflection across it
The reflected copy is painted into the grid (clipped at the border); the
original shape and the mirror stay where they are.
"""

CARD = "7ed72f31"
LINE = ("Family for 7ed72f31: optics:mirror_reflection.: Each object is a shape glued to a \"mirror\" "
        "(cells of one role colour). The mirror's fixed-point set decides the isometry: a single mirror "
        "cell is a point mirror (central inversion through it), a straight mirror segment (row, column or "
        "diagonal) is a plane mirror (axial reflection across its line).")

READING = {
    "generator": "For every object, the non-mirror cells are copied through the object's mirror: "
                 "central inversion through a single mirror cell, or axial reflection across the line of a "
                 "straight mirror segment (row, column, diagonal or anti-diagonal); the copy is painted "
                 "onto the grid while the original stays.",
    "stop": "One reflected copy per object; cells falling outside the grid are clipped; objects without a "
            "mirror, with only mirror cells, or with a non-straight mirror are left unchanged.",
    "params": "mirror_colour ∈ {fixed role colour induced from train, per-grid colour shared by all "
              "objects} · connectivity ∈ {8, 4} · paint ∈ {over, background-only}",
    "participants": "Background = most frequent colour of the grid; objects = connected components of "
                    "non-background cells (multi-colour); mirror = the object's cells of the role colour; "
                    "shape = the object's remaining cells.",
    "preconditions": "Grid sizes are unchanged; a role colour exists that occurs in the train inputs; "
                     "every train output equals the input with the reflected copies added.",
}

_DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
_DIRS4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _objects(g, bg, conn):
    h, w = len(g), len(g[0])
    dirs = _DIRS8 if conn == 8 else _DIRS4
    seen = [[False] * w for _ in range(h)]
    objs = []
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == bg:
                continue
            seen[r][c] = True
            stack = [(r, c)]
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in dirs:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            objs.append(comp)
    return objs


def _isometry(mirror):
    """Return a cell map for the mirror's fixed-point set, or None if not straight."""
    cells = sorted(mirror)
    if len(cells) == 1:
        r0, c0 = cells[0]
        return lambda r, c: (2 * r0 - r, 2 * c0 - c)
    rows = {r for r, _ in cells}
    cols = {c for _, c in cells}
    n = len(cells)
    if len(rows) == 1:
        cs = sorted(cols)
        if cs[-1] - cs[0] != n - 1:
            return None
        r0 = cells[0][0]
        return lambda r, c: (2 * r0 - r, c)
    if len(cols) == 1:
        rs = sorted(rows)
        if rs[-1] - rs[0] != n - 1:
            return None
        c0 = cells[0][1]
        return lambda r, c: (r, 2 * c0 - c)
    diffs = {r - c for r, c in cells}
    if len(diffs) == 1:
        rs = sorted(rows)
        if len(rs) != n or rs[-1] - rs[0] != n - 1:
            return None
        k = diffs.pop()
        return lambda r, c: (c + k, r - k)
    sums = {r + c for r, c in cells}
    if len(sums) == 1:
        rs = sorted(rows)
        if len(rs) != n or rs[-1] - rs[0] != n - 1:
            return None
        s = sums.pop()
        return lambda r, c: (s - c, s - r)
    return None


def _shared_colour(g, bg, conn):
    """Per-grid role colour: the non-bg colour present in every multi-colour object."""
    objs = [o for o in _objects(g, bg, conn) if len({g[r][c] for r, c in o}) > 1]
    if not objs:
        return None
    common = None
    for o in objs:
        cs = {g[r][c] for r, c in o}
        common = cs if common is None else common & cs
    if common is None or len(common) != 1:
        return None
    return next(iter(common))


def _apply(g, colour_of, conn, paint):
    h, w = len(g), len(g[0])
    bg = _bg(g)
    mc = colour_of(g, bg, conn)
    out = [list(row) for row in g]
    if mc is None or mc == bg:
        return out
    for obj in _objects(g, bg, conn):
        mirror = [(r, c) for r, c in obj if g[r][c] == mc]
        shape = [(r, c) for r, c in obj if g[r][c] != mc]
        if not mirror or not shape:
            continue
        iso = _isometry(mirror)
        if iso is None:
            continue
        for r, c in shape:
            nr, nc = iso(r, c)
            if 0 <= nr < h and 0 <= nc < w:
                if paint == "over" or out[nr][nc] == bg:
                    out[nr][nc] = g[r][c]
    return out


def _make(colour_of, conn, paint):
    return lambda grid: _apply(grid, colour_of, conn, paint)


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or not gi[0] or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    # candidate fixed role colours: non-bg colours present in every train input
    cand = None
    for p in train:
        g = p["input"]
        bg = _bg(g)
        cs = {v for row in g for v in row} - {bg}
        cand = cs if cand is None else cand & cs
    cand = sorted(cand or [])

    variants = []
    for conn in (8, 4):
        for paint in ("over", "under"):
            extra = (0 if conn == 8 else 2) + (0 if paint == "over" else 1)
            for c in cand:
                variants.append((f"mirror_reflection[mirror=c{c},conn={conn},paint={paint}]",
                                 10 + extra, (lambda cc: (lambda g, bg, cn: cc))(c), conn, paint))
            variants.append((f"mirror_reflection[mirror=shared,conn={conn},paint={paint}]",
                             11 + extra, _shared_colour, conn, paint))

    fits = []
    for name, cost, colour_of, conn, paint in variants:
        fn = _make(colour_of, conn, paint)
        ok = True
        changed = False
        for p in train:
            try:
                pred = fn(p["input"])
            except Exception:
                ok = False
                break
            if pred != [list(r) for r in p["output"]]:
                ok = False
                break
            if pred != [list(r) for r in p["input"]]:
                changed = True
        if ok and changed:
            fits.append((name, cost, fn))
    fits.sort(key=lambda t: t[1])
    for t in fits:
        yield t


FAMILIES = [fam]
