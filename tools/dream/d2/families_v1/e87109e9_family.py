"""Family for ARC task e87109e9 -- concept: TURTLE GRAPHICS (graphics: a turtle that goes FORWARD until blocked,
then turns LEFT or RIGHT by a colour-coded rule table).

Reading of the task
-------------------
A framed legend strip along one edge of the grid is a program listing: each framed cell shows one colour, placed at
one end of the cell; the end it sits at says whether that colour means "turn left" or "turn right".  The rest of
the grid is the playing field: a background with coloured walls and one small block of a colour that is not in the
legend (the turtle / pen).  From the block, a turtle of the block's width sets off in each of the four directions,
drawing with the block colour.  It moves forward over background (and over ink already drawn) until the next step
would enter a wall; it then turns left or right according to the legend entry of that wall's colour and carries on
from where it stands.  It stops at the grid edge (or at a wall whose colour is not in the legend).  The output is
the field with the drawing; the legend strip is dropped.

How everything is found (no task constants):
  * legend   = an edge band delimited by two full lines of one frame colour (grid tried in its 4 rotations, so the
               strip may lie on any side); its cells are the runs of non-frame lines inside the band; each cell's
               filler colour is the one common to all cells, its key colour is the other one, and the key's slot is
               which half of the cell (along the strip) it lies in.
  * field    = the grid minus the band; background = its most common colour.
  * pen      = field colour that is neither background nor a legend colour; each 4-connected block of it is a turtle
               whose width is the block's extent.
Parameters (declared finite domains, induced from train; first fit wins):
  first_slot_turn in {'L', 'R'}   what a key in the first half (reading order along the strip) means.
  keep_legend     in {False, True} whether the legend band stays in the output.
"""

from collections import Counter


def _rot(g):            # 90 degrees clockwise
    return [list(r) for r in zip(*g[::-1])]


def _unrot(g):          # 90 degrees counter-clockwise
    return [list(r) for r in zip(*g)][::-1]


def _legend_top(g):
    """If the grid starts with a framed legend band, return (k, frame, {colour: slot}); else None.
    Band = rows 0..k, rows 0 and k uniform in the frame colour."""
    H, W = len(g), len(g[0])
    F = g[0][0]
    if any(v != F for v in g[0]):
        return None
    k = next((r for r in range(1, H) if all(v == F for v in g[r])), None)
    if k is None or k < 2 or k >= H - 1:
        return None
    band = g[1:k]
    sep = [all(row[c] == F for row in band) for c in range(W)]
    cells, c = [], 0
    while c < W:
        if sep[c]:
            c += 1
            continue
        c0 = c
        while c < W and not sep[c]:
            c += 1
        cells.append((c0, c - 1))
    if len(cells) < 2:
        return None
    colsets = [set(row[x] for row in band for x in range(a, b + 1)) - {F} for a, b in cells]
    common = set.intersection(*colsets)
    if len(common) != 1:
        return None
    filler = common.pop()
    table = {}
    for (a, b), cs in zip(cells, colsets):
        keys = cs - {filler}
        if len(keys) != 1:
            return None
        key = keys.pop()
        xs = [x for row in band for x in range(a, b + 1) if row[x] == key]
        centre2 = a + b                       # twice the cell centre
        pos2 = 2 * sum(xs) / len(xs)          # twice the key's mean column
        if pos2 == centre2 or key in table:
            return None
        table[key] = 0 if pos2 < centre2 else 1
    return k, F, table


def _components(g, colour):
    H, W = len(g), len(g[0])
    seen, comps = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] != colour or (r, c) in seen:
                continue
            stack, cells = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == colour and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            comps.append(cells)
    return comps


def _turtle(field, table, first_slot_turn):
    H, W = len(field), len(field[0])
    bg = Counter(v for row in field for v in row).most_common(1)[0][0]
    pens = {v for row in field for v in row} - {bg} - set(table)
    if len(pens) != 1:
        return None
    pen = pens.pop()
    out = [row[:] for row in field]
    passable = (bg, pen)
    turn_of = {}
    for col, slot in table.items():
        turn_of[col] = first_slot_turn if slot == 0 else ('R' if first_slot_turn == 'L' else 'L')
    for cells in _components(field, pen):
        r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
        c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
        for d0 in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            rect, d, seen = (r0, r1, c0, c1), d0, set()
            while (rect, d) not in seen:
                seen.add((rect, d))
                a, b, c, e = rect
                n = (a + d[0], b + d[0], c + d[1], e + d[1])
                if n[0] < 0 or n[1] >= H or n[2] < 0 or n[3] >= W:
                    break                                           # left the field
                walls = Counter(field[y][x] for y in range(n[0], n[1] + 1) for x in range(n[2], n[3] + 1)
                                if field[y][x] not in passable)
                if walls:
                    t = turn_of.get(walls.most_common(1)[0][0])
                    if t is None:
                        break
                    d = (-d[1], d[0]) if t == 'L' else (d[1], -d[0])
                    continue
                rect = n
                for y in range(n[0], n[1] + 1):
                    for x in range(n[2], n[3] + 1):
                        out[y][x] = pen
    return out


def _make(first_slot_turn, keep_legend):
    def fn(g):
        g = [list(r) for r in g]
        for q in range(4):
            leg = _legend_top(g)
            if leg is not None:
                k, F, table = leg
                field = _turtle(g[k + 1:], table, first_slot_turn)
                if field is None:
                    return None
                res = (g[:k + 1] + field) if keep_legend else field
                for _ in range(q):
                    res = _unrot(res)
                return res
            g = _rot(g)
        return None
    return fn


def fam_turtle(train):
    for first_slot_turn in ('L', 'R'):
        for keep_legend in (False, True):
            fn = _make(first_slot_turn, keep_legend)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("graphics:turtle[first_slot=%s,keep_legend=%s]" % (first_slot_turn, keep_legend), 3, fn)
                return


FAMILIES = (fam_turtle,)
