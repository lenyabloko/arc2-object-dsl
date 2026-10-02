"""Line expansion for 2faf500b: shapes split open along a band of marker cells (test-blind; train pairs only)."""
from collections import Counter

CARD = "2faf500b"
LINE = ("Each shape is crossed by a band of marker cells spanning it fully; the marker cells vanish and the shape splits "
        "along the band, each half (taking its half of the band) sliding away from the band by half the band's thickness.")
READING = {
    "generator": "For every shape crossed by a straight band of marker cells, erase the marker cells, cut the shape through the middle "
                 "of the band, and redraw each half (with its half of the band) shifted away from the cut by half the band's thickness, "
                 "so the band's rows/columns end up empty; shapes without a band are redrawn unchanged.",
    "stop": "Each half moves exactly once, by half the band thickness (an odd band gives the top/left half the floor and the "
            "bottom/right half the ceiling); cells pushed off the grid are dropped.",
    "params": "marker ∈ {vanishing colour: present in every train input, absent from every train output; per-shape minority colour} · "
              "connectivity ∈ {4, 8} · shift = half band thickness (fixed by the line)",
    "participants": "background = most frequent colour of the grid; shapes = connected components of non-background cells; "
                    "markers = shape cells of the marker colour; band = the rows (or columns) holding the shape's markers, chosen "
                    "where they lie strictly inside the shape and the markers reach both sides of the shape across it "
                    "(if both orientations qualify the thinner band wins, a tie leaves the shape unchanged).",
    "preconditions": "Output has the input's size; every train input holds at least one shape with such a band; the marker colour is "
                     "determinable (unique vanishing colour, or a two-colour shape with a strict minority colour).",
}


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _objects(g, bg, conn):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    if conn == 4:
        nb = ((1, 0), (-1, 0), (0, 1), (0, -1))
    else:
        nb = tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)
    objs = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg: continue
            seen[r][c] = True
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            objs.append(sorted(cells))
    return objs


def _marker_of(g, cells, mode, mcol):
    if mode == "vanish":
        return mcol
    cnt = Counter(g[r][c] for r, c in cells)
    if len(cnt) != 2: return None
    (a, na), (b, nb) = cnt.most_common()
    return b if nb < na else None


def _band(cells, marks):
    """-> (axis, lo, hi) with axis 0 = horizontal band (rows lo..hi), 1 = vertical band (cols lo..hi); or None."""
    if not marks: return None
    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    mr0 = min(r for r, _ in marks); mr1 = max(r for r, _ in marks)
    mc0 = min(c for _, c in marks); mc1 = max(c for _, c in marks)
    cands = []
    if r0 < mr0 and mr1 < r1 and mc0 == c0 and mc1 == c1:
        cands.append((mr1 - mr0 + 1, 0, mr0, mr1))
    if c0 < mc0 and mc1 < c1 and mr0 == r0 and mr1 == r1:
        cands.append((mc1 - mc0 + 1, 1, mc0, mc1))
    if not cands: return None
    cands.sort()
    if len(cands) == 2 and cands[0][0] == cands[1][0]: return None
    _, axis, lo, hi = cands[0]
    return axis, lo, hi


def _plan(g, mode, mcol, conn):
    """-> (bg, list of (cells, band-or-None, marker colour)), or None."""
    bg = _bg(g)
    plan = []
    for cells in _objects(g, bg, conn):
        m = _marker_of(g, cells, mode, mcol)
        band = None
        if m is not None and m != bg:
            marks = [(r, c) for r, c in cells if g[r][c] == m]
            if len(marks) < len(cells):
                band = _band(cells, marks)
        plan.append((cells, band, m))
    return bg, plan


def solve(g, mode, mcol, conn):
    H, W = len(g), len(g[0])
    bg, plan = _plan(g, mode, mcol, conn)
    out = [[bg] * W for _ in range(H)]
    for cells, band, _ in plan:
        if band is None:
            for r, c in cells: out[r][c] = g[r][c]
    for cells, band, m in plan:
        if band is None: continue
        axis, lo, hi = band
        t = hi - lo + 1
        a = t // 2           # band lines kept by the top/left half (= its shift)
        b = t - a            # band lines kept by the bottom/right half (= its shift)
        cut = lo + a
        for r, c in cells:
            v = g[r][c]
            if v == m: continue
            k = r if axis == 0 else c
            d = -a if k < cut else b
            nr, nc = (r + d, c) if axis == 0 else (r, c + d)
            if 0 <= nr < H and 0 <= nc < W:
                out[nr][nc] = v
    return out


def _vanishing_colour(train):
    ins = None; outs = set()
    for p in train:
        s = {v for row in p["input"] for v in row} - {_bg(p["input"])}
        ins = s if ins is None else ins & s
        outs |= {v for row in p["output"] for v in row}
    cand = sorted((ins or set()) - outs)
    return cand[0] if len(cand) == 1 else None


def fam(train):
    if not train: return
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]): return
    vc = _vanishing_colour(train)
    variants = []
    for mode in ("vanish", "minority"):
        if mode == "vanish" and vc is None: continue
        for conn in (4, 8):
            variants.append((mode, vc if mode == "vanish" else None, conn))
    k = 0
    for mode, mcol, conn in variants:
        try:
            if not all(any(b is not None for _, b, _ in _plan(p["input"], mode, mcol, conn)[1]) for p in train):
                continue
            fn = (lambda mode, mcol, conn: (lambda g: solve(g, mode, mcol, conn)))(mode, mcol, conn)
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("bandsplit:%s:c%d" % (mode, conn), 10 + k, fn)
            k += 1


FAMILIES = [fam]
