"""Line expansion for dc2e9a9d: plane-mirror image formation (test-blind; train pairs only)."""
from collections import Counter

CARD = "dc2e9a9d"
LINE = ('Group family g12 -- "reflection / symmetric completion".: PLANE MIRROR (optics) -- image formation by plane mirrors. '
        "Every object point P in front of a mirror has a virtual image P' on the mirror's normal through P, at the same "
        "distance behind the mirror. (group family g12_reflection_completion)")
READING = {
    "generator": "Each object gets a plane mirror parallel to one of its bounding-box sides (the side opposite its "
                 "one-cell protrusion), a fixed induced distance beyond that side; every object cell P is copied to "
                 "its image P' = 2m - P across that line, coloured by an induced rule (here: one colour per mirror axis).",
    "stop": "One image per object (per mirror); image cells outside the grid are clipped, and only background cells "
            "are painted (or overwritten, if induced).",
    "params": "mirror ∈ {per-object bbox side, explicit full-length line in the grid, grid centre line} · "
              "side ∈ {opposite protrusion, toward protrusion, up, down, left, right} · "
              "offset ∈ {0, 1/2, 1, 3/2, 2} cells beyond the side · colour ∈ {same, const, by axis, by side} · "
              "conn ∈ {8, 4} · paint ∈ {bg-only, overwrite} · centre axis ∈ {v, h, both}",
    "participants": "objects = connected components of non-background cells (background = most frequent input colour); "
                    "protrusion side = the bbox side whose extreme row/column holds uniquely the fewest object cells; "
                    "explicit mirror = the single full row/column of one non-background colour.",
    "preconditions": "Output has the input's size and equals the input plus image cells; every training object has a "
                     "well-defined mirror side; the colour rule is consistent over all training images.",
}

SIDES = ("up", "down", "left", "right")
OPP = {"up": "down", "down": "up", "left": "right", "right": "left"}


# ---------------------------------------------------------------- helpers
def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _comps(g, bg, conn):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    if conn == 4:
        nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    else:
        nb = tuple((a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b)
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            seen[r][c] = True
            st, cells = [(r, c)], []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        st.append((ny, nx))
            out.append(cells)
    return out


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _protrusion_side(cells):
    r0, r1, c0, c1 = _bbox(cells)
    if r0 == r1 or c0 == c1:
        return None
    cnt = {"up": sum(1 for r, _ in cells if r == r0), "down": sum(1 for r, _ in cells if r == r1),
           "left": sum(1 for _, c in cells if c == c0), "right": sum(1 for _, c in cells if c == c1)}
    m = min(cnt.values())
    ss = [s for s in SIDES if cnt[s] == m]
    return ss[0] if len(ss) == 1 else None


def _mirror_side(cells, rule):
    if rule in SIDES:
        return rule
    p = _protrusion_side(cells)
    if p is None:
        return None
    return OPP[p] if rule == "opp_protrusion" else p


def _reflect(cells, side, k):
    """Image of cells across a mirror line k half-cells beyond the bbox side (2m = 2*edge +/- k)."""
    r0, r1, c0, c1 = _bbox(cells)
    if side == "down":
        M = 2 * r1 + k
        return [((r, c), (M - r, c)) for r, c in cells]
    if side == "up":
        M = 2 * r0 - k
        return [((r, c), (M - r, c)) for r, c in cells]
    if side == "right":
        M = 2 * c1 + k
        return [((r, c), (r, M - c)) for r, c in cells]
    M = 2 * c0 - k
    return [((r, c), (r, M - c)) for r, c in cells]


def _key(ckind, side):
    if ckind == "axis":
        return "h" if side in ("up", "down") else "v"
    if ckind == "side":
        return side
    return None


# ---------------------------------------------------------------- per-object mirror
def _images(g, conn, rule, k, paint):
    """Yield (side, [(src, dst)]) per object, dst inside grid and paintable."""
    H, W = len(g), len(g[0])
    bg = _bg(g)
    for cells in _comps(g, bg, conn):
        side = _mirror_side(cells, rule)
        if side is None:
            continue
        pts = [(s, d) for s, d in _reflect(cells, side, k)
               if 0 <= d[0] < H and 0 <= d[1] < W and (paint == "over" or g[d[0]][d[1]] == bg)]
        yield side, pts


def _make_obj(conn, rule, k, ckind, cmap, paint):
    fallback = Counter(cmap.values()).most_common(1)[0][0] if cmap else None

    def fn(g):
        out = [list(row) for row in g]
        for side, pts in _images(g, conn, rule, k, paint):
            if ckind == "same":
                for (sr, sc), (dr, dc) in pts:
                    out[dr][dc] = g[sr][sc]
            else:
                col = cmap.get(_key(ckind, side), fallback)
                if col is None:
                    continue
                for _, (dr, dc) in pts:
                    out[dr][dc] = col
        return out
    return fn


def _induce_cmap(train, conn, rule, k, ckind, paint):
    cmap = {}
    for p in train:
        g, o = p["input"], p["output"]
        for side, pts in _images(g, conn, rule, k, paint):
            cols = {o[dr][dc] for _, (dr, dc) in pts}
            if not cols:
                continue
            if len(cols) != 1:
                return None
            col = cols.pop()
            key = _key(ckind, side)
            if cmap.setdefault(key, col) != col:
                return None
    return cmap


# ---------------------------------------------------------------- explicit mirror line
def _explicit_line(g, bg):
    H, W = len(g), len(g[0])
    lines = []
    for r in range(H):
        if g[r][0] != bg and all(v == g[r][0] for v in g[r]):
            lines.append(("row", r))
    for c in range(W):
        if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(H)):
            lines.append(("col", c))
    return lines[0] if len(lines) == 1 else None


def _make_explicit(paint):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        ln = _explicit_line(g, bg)
        if ln is None:
            return None
        out = [list(row) for row in g]
        kind, m = ln
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if v == bg or (kind == "row" and r == m) or (kind == "col" and c == m):
                    continue
                dr, dc = (2 * m - r, c) if kind == "row" else (r, 2 * m - c)
                if 0 <= dr < H and 0 <= dc < W and (paint == "over" or g[dr][dc] == bg):
                    out[dr][dc] = v
        return out
    return fn


# ---------------------------------------------------------------- grid-centre mirror (symmetric completion)
def _make_centre(axis):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [list(row) for row in g]
        steps = {"v": ("v",), "h": ("h",), "both": ("v", "h", "v")}[axis]
        for a in steps:
            src = [row[:] for row in out]
            for r in range(H):
                for c in range(W):
                    if src[r][c] == bg:
                        v = src[r][W - 1 - c] if a == "v" else src[H - 1 - r][c]
                        if v != bg:
                            out[r][c] = v
        return out
    return fn


# ---------------------------------------------------------------- family
def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    if not train:
        return
    for p in train:
        g, o = p["input"], p["output"]
        if len(g) != len(o) or len(g[0]) != len(o[0]) or g == o:
            return
    cands = []
    # per-object plane mirror at a bbox side
    for conn in (8, 4):
        for rule in ("opp_protrusion", "protrusion") + SIDES:
            # rule precondition: every training object must have a mirror side
            ok = all(_mirror_side(cells, rule) is not None
                     for p in train for cells in _comps(p["input"], _bg(p["input"]), conn))
            if not ok:
                continue
            for k in (0, 1, 2, 3, 4):
                for paint in ("bg", "over"):
                    for ci, ckind in enumerate(("same", "const", "axis", "side")):
                        cmap = {} if ckind == "same" else _induce_cmap(train, conn, rule, k, ckind, paint)
                        if cmap is None or (ckind != "same" and not cmap):
                            continue
                        fn = _make_obj(conn, rule, k, ckind, cmap, paint)
                        if not _fits(fn, train):
                            continue
                        cost = 10 + ci + abs(k - 1) + (paint == "over") + (conn == 4) + (rule in SIDES)
                        cm = ",".join("%s:%s" % (a, b) for a, b in sorted(cmap.items(), key=lambda t: str(t[0])))
                        name = "plane_mirror_obj[%s,k=%d/2,col=%s{%s},conn=%d,paint=%s]" % (rule, k, ckind, cm, conn, paint)
                        cands.append((cost, name, fn))
    # explicit mirror line present in the grid
    for paint in ("bg", "over"):
        fn = _make_explicit(paint)
        if _fits(fn, train):
            cands.append((8 + (paint == "over"), "plane_mirror_line[paint=%s]" % paint, fn))
    # grid-centre mirror
    for ai, axis in enumerate(("v", "h", "both")):
        fn = _make_centre(axis)
        if _fits(fn, train):
            cands.append((6 + ai, "plane_mirror_centre[%s]" % axis, fn))
    cands.sort(key=lambda t: (t[0], t[1]))
    for cost, name, fn in cands:
        yield name, cost, fn


FAMILIES = [fam]
