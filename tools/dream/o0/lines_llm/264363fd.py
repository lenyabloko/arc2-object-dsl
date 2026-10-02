"""Line expansion for 264363fd: template legend -> stamp core + full-width arm lines at markers (test-blind; train pairs only)."""
from collections import Counter

CARD = "264363fd"
LINE = ("A small template in the background shows a marker's decoration; erase it, and at every marker inside the big "
        "rectangles stamp the template's 3x3 core and, along each axis where the template has arms, draw a line of the "
        "arm colour across the whole rectangle.")
READING = {
    "generator": "Erase the small template object; at every marker cell (template-centre colour) inside a big rectangle, draw a line "
                 "of the template's arm colour through the marker along each axis on which the template has arms, then stamp the "
                 "template's 3x3 core (its background cells transparent) centred on the marker.",
    "stop": "Each line runs from the marker in both directions until it leaves the rectangle containing the marker; "
            "the core is a single 3x3 stamp; all lines are drawn before any core so cores sit on top.",
    "params": "axes ∈ {horizontal, vertical, diagonal, anti-diagonal}, each present iff the template has a cell two steps from its centre "
              "in that direction (arm colour read there) · extent ∈ {full axis, only on arm sides} · order ∈ {lines then cores, cores then lines}",
    "participants": "background = most frequent colour; objects = 8-connected non-background components; rectangles = components that fill "
                    "their bounding box with one dominant colour plus isolated other-coloured cells (markers); template = a non-rectangle "
                    "component whose centre (bbox centre, else its unique marker-coloured cell) has a colour found as markers in rectangles.",
    "preconditions": "Output has the input's shape; at least one template and one rectangle with markers of a template's centre colour; "
                     "template centre colours are distinct between templates.",
}

DIRS8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]
AXES = [((-1, 0), (1, 0)), ((0, -1), (0, 1)), ((-1, -1), (1, 1)), ((-1, 1), (1, -1))]


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            seen[r][c] = True
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            comps.append(cells)
    return comps


def _as_rectangle(g, cells):
    """-> (dominant colour, set of marker cells) if the component is a filled rectangle with isolated odd cells, else None."""
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    if h < 3 or w < 3 or len(cells) != h * w:
        return None
    cnt = Counter(g[r][c] for r, c in cells)
    dom, n = cnt.most_common(1)[0]
    if n * 2 <= len(cells):
        return None
    odd = {(r, c) for r, c in cells if g[r][c] != dom}
    for r, c in odd:
        for dr, dc in DIRS8[:4]:
            if (r + dr, c + dc) in odd:
                return None
    return dom, odd


def _parse(g):
    bg = _bg(g)
    comps = _components(g, bg)
    rects, others = [], []
    for cells in comps:
        rr = _as_rectangle(g, cells)
        if rr is None:
            others.append(cells)
        else:
            rects.append((set(cells), rr[0], rr[1]))
    marker_cols = {g[r][c] for _, _, odd in rects for r, c in odd}
    if not marker_cols:
        return None
    templates = {}
    for cells in others:
        if len(cells) < 2:
            continue
        cs = set(cells)
        rs = [r for r, _ in cells]
        cl = [c for _, c in cells]
        centre = None
        if (max(rs) - min(rs)) % 2 == 0 and (max(cl) - min(cl)) % 2 == 0:
            cr, cc = (max(rs) + min(rs)) // 2, (max(cl) + min(cl)) // 2
            if (cr, cc) in cs and g[cr][cc] in marker_cols:
                centre = (cr, cc)
        if centre is None:
            cand = [(r, c) for r, c in cells if g[r][c] in marker_cols]
            if len(cand) == 1:
                centre = cand[0]
        if centre is None:
            continue
        cr, cc = centre
        mcol = g[cr][cc]
        if mcol in templates:
            return None
        core = {}
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if (cr + dr, cc + dc) in cs:
                    core[(dr, dc)] = g[cr + dr][cc + dc]
        arms = {}
        for dr, dc in DIRS8:
            p = (cr + 2 * dr, cc + 2 * dc)
            if p in cs:
                arms[(dr, dc)] = g[p[0]][p[1]]
        templates[mcol] = {"cells": cells, "core": core, "arms": arms}
    if not templates:
        return None
    if not any(g[r][c] in templates for _, _, odd in rects for r, c in odd):
        return None
    return bg, rects, templates


def _render(g, extent, order):
    P = _parse(g)
    if P is None:
        return None
    bg, rects, templates = P
    H, W = len(g), len(g[0])
    out = [list(row) for row in g]
    for t in templates.values():
        for r, c in t["cells"]:
            out[r][c] = bg
    jobs = []
    for region, _, odd in rects:
        for r, c in sorted(odd):
            if g[r][c] in templates:
                jobs.append((region, r, c, templates[g[r][c]]))

    def lines():
        for region, r, c, t in jobs:
            arms = t["arms"]
            for a, b in AXES:
                if a not in arms and b not in arms:
                    continue
                for d, e in ((a, b), (b, a)):
                    if d in arms:
                        col = arms[d]
                    elif extent == "axis":
                        col = arms[e]
                    else:
                        continue
                    y, x = r + d[0], c + d[1]
                    while (y, x) in region:
                        out[y][x] = col
                        y, x = y + d[0], x + d[1]

    def cores():
        for _, r, c, t in jobs:
            for (dr, dc), v in t["core"].items():
                y, x = r + dr, c + dc
                if 0 <= y < H and 0 <= x < W:
                    out[y][x] = v

    if order == "lines_core":
        lines(); cores()
    else:
        cores(); lines()
    return out


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        if _parse(gi) is None:
            return
    cost = 1
    for order in ("lines_core", "core_lines"):
        for extent in ("axis", "ray"):
            preds = [_render(p["input"], extent, order) for p in train]
            if all(pr == p["output"] for pr, p in zip(preds, train)):
                yield ("tmpl_stamp_lines[%s,%s]" % (order, extent), cost,
                       (lambda g, e=extent, o=order: _render(g, e, o)))
            cost += 1


FAMILIES = [fam]
