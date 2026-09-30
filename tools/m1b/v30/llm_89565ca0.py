"""Family: topology:betti_number  (bar chart of the first Betti number of each coloured figure).

Concept (topology): every non-noise colour draws one line figure (a frame subdivided into cells).
Its first Betti number b1 = number of independent holes = number of enclosed faces.  Scattered
"noise" pixels and other figures' lines drawn on top occlude parts of a figure's lines; these are
amodally completed (an occluded run lying between two collinear pixels of the figure is restored)
before counting.  The answer is a horizontal bar chart: one bar per figure, bar length = b1,
bars sorted by b1 (tie-break induced), unused part of each row filled with the pad colour.

Induced parameters (small declared finite domains, chosen from the training pairs):
  pad    : role of the filler colour         in ("noise", "background")
  tie    : tie-break for equal b1            in TIE_KEYS
  width  : chart width                       in ("const" -> the constant training width, bars clipped,
                                                  "max"   -> width = the largest b1 in the grid)
  view   : orientation of the chart          in the 8 dihedral transforms
No coordinates, sizes, counts or colour numbers are stored.
"""
from collections import Counter


# ---------------------------------------------------------------- grid helpers
def _dihedral(g, k):
    if k & 4:
        g = [list(r) for r in zip(*g)]          # transpose
    if k & 1:
        g = [list(reversed(r)) for r in g]      # mirror left-right
    if k & 2:
        g = [list(r) for r in reversed(g)]      # mirror up-down
    return [list(r) for r in g]


def _components(cells):
    """4-connected components of a set of (r, c)."""
    seen, comps = set(), []
    for s in cells:
        if s in seen:
            continue
        seen.add(s)
        stack, comp = [s], []
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def _roles(g):
    """background = most frequent colour; noise = non-background colour whose pixels are the most
    scattered (smallest mean 4-connected component size); figures = the remaining colours."""
    cnt = Counter(v for row in g for v in row)
    bg = cnt.most_common(1)[0][0]
    others = [v for v in cnt if v != bg]
    if len(others) < 2:
        return None
    frag = {}
    for v in others:
        cells = {(r, c) for r, row in enumerate(g) for c, x in enumerate(row) if x == v}
        frag[v] = len(cells) / len(_components(cells))
    noise = min(others, key=lambda v: (frag[v], v))
    return bg, noise, [v for v in others if v != noise]


# ---------------------------------------------------------------- amodal completion + Betti number
def _completed_wall(g, colour, bg, noise):
    H, W = len(g), len(g[0])
    wall = [[g[r][c] == colour for c in range(W)] for r in range(H)]

    def occluder(r, c, horizontal_run):
        v = g[r][c]
        if v == noise:
            return True
        if v == bg or v == colour:
            return False
        # a foreign line crossing ours: its own colour continues perpendicular to our run
        nbrs = ((r - 1, c), (r + 1, c)) if horizontal_run else ((r, c - 1), (r, c + 1))
        return any(0 <= a < H and 0 <= b < W and g[a][b] == v for a, b in nbrs)

    changed = True
    while changed:
        changed = False
        for horizontal in (True, False):
            outer, inner = (H, W) if horizontal else (W, H)
            for i in range(outer):
                at = (lambda j: (i, j)) if horizontal else (lambda j: (j, i))
                last = None                      # index of last wall pixel seen on this line
                for j in range(inner):
                    r, c = at(j)
                    if wall[r][c]:
                        if last is not None and j - last > 1:
                            run = [at(k) for k in range(last + 1, j)]
                            if all(occluder(a, b, horizontal) for a, b in run):
                                for a, b in run:
                                    wall[a][b] = True
                                changed = True
                        last = j
                    elif not occluder(r, c, horizontal):
                        last = None
    return wall


def betti1(g, colour, bg, noise):
    """number of bounded faces (holes) of the completed figure of `colour`."""
    H, W = len(g), len(g[0])
    wall = _completed_wall(g, colour, bg, noise)
    free = {(r, c) for r in range(H) for c in range(W) if not wall[r][c]}
    holes = 0
    for comp in _components(free):
        if not any(r in (0, H - 1) or c in (0, W - 1) for r, c in comp):
            holes += 1
    return holes


_FIG_CACHE = {}


def _figures(g):
    """memoised by grid content (pure function of g; the result is never mutated by callers)."""
    try:
        key = tuple(tuple(r) for r in g)
        hash(key)
    except TypeError:
        return _figures_raw(g)
    hit = _FIG_CACHE.get(key)
    if hit is None:
        try:
            hit = (True, _figures_raw(g))
        except Exception as e:                   # re-raise the same failure on every call
            hit = (False, e)
        if len(_FIG_CACHE) > 256:
            _FIG_CACHE.clear()
        _FIG_CACHE[key] = hit
    if hit[0]:
        return hit[1]
    raise hit[1]


def _figures_raw(g):
    roles = _roles(g)
    if roles is None:
        return None
    bg, noise, figs = roles
    out = []
    for v in figs:
        cells = [(r, c) for r, row in enumerate(g) for c, x in enumerate(row) if x == v]
        rs, cs = [r for r, _ in cells], [c for _, c in cells]
        out.append({"colour": v, "b1": betti1(g, v, bg, noise), "top": min(rs), "left": min(cs),
                    "area": (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)})
    return bg, noise, [f for f in out if f["b1"] > 0]


TIE_KEYS = {
    "colour": lambda f: f["colour"],
    "left": lambda f: f["left"],
    "top": lambda f: f["top"],
    "area_desc": lambda f: -f["area"],
    "area_asc": lambda f: f["area"],
}


def _chart(g, pad_role, tie, width, view):
    info = _figures(g)
    if not info or not info[2]:
        return None
    bg, noise, figs = info
    pad = noise if pad_role == "noise" else bg
    figs = sorted(figs, key=lambda f: (f["b1"], TIE_KEYS[tie](f)))
    w = max(f["b1"] for f in figs) if width == "max" else width
    rows = [[f["colour"]] * min(f["b1"], w) + [pad] * (w - min(f["b1"], w)) for f in figs]
    return _dihedral(rows, view)


def _may_fit(p):
    """necessary conditions for _chart(p["input"], ...) == p["output"] under ANY parameters:
    the input has >= 3 colours (bg, noise, >= 1 figure), every output colour occurs in the input,
    and one output side equals the number of charted figures (<= #input colours - 2)."""
    try:
        g, out = p["input"], p["output"]
        cols = {v for row in g for v in row}
        if len(cols) < 3:
            return False
        if not {v for row in out for v in row} <= cols:
            return False
        R = len(out)
        if R and all(len(row) == len(out[0]) for row in out):
            if min(R, len(out[0])) > len(cols) - 2:
                return False
    except Exception:
        return True
    return True


def fam_betti_number(train):
    shapes = [(len(p["output"]), len(p["output"][0])) for p in train]
    if not all(_may_fit(p) for p in train):
        return
    for width_mode in ("const", "max"):
        found = False
        for view in range(8):
            if width_mode == "const":
                # constant bar-axis length shared by every training output (bars clipped to it)
                axis = {s[0] if view & 4 else s[1] for s in shapes}
                if len(axis) != 1:
                    continue
                width = axis.pop()
            else:
                width = "max"
            for pad_role in ("noise", "background"):
                for tie in TIE_KEYS:
                    def fn(g, pad_role=pad_role, tie=tie, width=width, view=view):
                        return _chart(g, pad_role, tie, width, view)
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("topology:betti_number[pad=%s,tie=%s,width=%s,view=%d]"
                               % (pad_role, tie, width_mode, view), 3, fn)
                        found = True
                        break
                if found:
                    break
            if found:
                break


FAMILIES = (fam_betti_number,)
