"""Group g03 "lines extended to a template length".

Concept: EXTRUSION ("extrude up to" a bounding face) -- CAD / solid modelling.
A cross-section profile is swept along a straight direction d until it meets the bounding face
(here: the grid border).  Every object that does not yet reach the border in direction d is
extruded beyond its front face; the swept profile is read from a REFERENCE:
  * ref='exemplar' : a complete copy of the same stroke that already reaches the border (the
                     "template"); the open copy is aligned with it at its back end and receives the
                     template's cells lying beyond its own front  ("extend to template length").
  * ref='self'     : the object's own front face (last `period` layers, repeated periodically).
                     If the object carries a marker (a minority colour on one side of its bounding
                     box) the extrusion direction is the marker's side and only the part of the face
                     within radius `win` of the marker is extruded (the die opening).
Parameters (finite domains, all induced from the task's training pairs):
  conn   in {4, 8}                          connectivity of objects
  ref    in {exemplar, self}
  dir    in {U, D, L, R, marker}            (marker = per-object side of its marker)
  period in {1, 2, 3}                       (self only)
  win    in {inf, depth-1, depth, 0}        window radius around marker; depth = object extent along d
  colour in {same} | {colours new in training outputs}
Background = most frequent input colour.  Extrusion paints background cells only.
"""
from collections import Counter

DIRS = {'U': (-1, 0), 'D': (1, 0), 'L': (0, -1), 'R': (0, 1)}


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg, conn):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if conn == 8:
        nb += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
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
            comps.append(cells)
    return comps


# ---- direction-relative coordinates: a = along d, y = across d -------------------------------
def _ay(rc, d):
    (r, c), (dr, dc) = rc, d
    return (r * dr + c * dc, c if dr else r)


def _rc(a, y, d):
    dr, dc = d
    return (a * dr, y) if dr else (y, a * dc)


def _amax(d, H, W):
    dr, dc = d
    return (H - 1 if dr > 0 else 0) if dr else (W - 1 if dc > 0 else 0)


def _marker(g, cells):
    cnt = Counter(g[r][c] for r, c in cells)
    if len(cnt) < 2:
        return None
    body = cnt.most_common(1)[0][0]
    return [(r, c) for r, c in cells if g[r][c] != body]


def _marker_dir(cells, mk):
    rs = [r for r, _ in cells]; cs = [c for _, c in cells]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    sides = []
    if all(r == r0 for r, _ in mk): sides.append(('U', c1 - c0))
    if all(r == r1 for r, _ in mk): sides.append(('D', c1 - c0))
    if all(c == c0 for _, c in mk): sides.append(('L', r1 - r0))
    if all(c == c1 for _, c in mk): sides.append(('R', r1 - r0))
    if not sides:
        return None
    if len(sides) > 1:                      # corner: take the side lying on the longer edge
        sides.sort(key=lambda s: -s[1])
        if sides[0][1] == sides[1][1]:
            return None
    return sides[0][0]


def _extrude(g, P):
    conn, ref, dname, period, win, colour = P
    H, W = len(g), len(g[0])
    bg = _bg(g)
    out = [row[:] for row in g]
    comps = _components(g, bg, conn)
    paint = []                               # (r, c, colour)
    if ref == 'exemplar':
        d = DIRS[dname]
        amax = _amax(d, H, W)
        info = []
        for cells in comps:
            ay = [(_ay(rc, d), g[rc[0]][rc[1]]) for rc in cells]
            A = [a for (a, _), _ in ay]
            back = min(A)
            ymin = min(y for (a, y), _ in ay if a == back)
            info.append((ay, back, max(A), ymin))
        exemplars = [i for i in info if i[2] == amax]
        if not exemplars:
            return None
        for ay, back, front, ymin in info:
            if front == amax:
                continue
            own = set(p for p, _ in ay)
            best = None
            for e_ay, e_back, _, e_ymin in exemplars:
                sa, sy = back - e_back, ymin - e_ymin
                moved = [((a + sa, y + sy), v) for (a, y), v in e_ay]
                ov = sum(1 for p, _ in moved if p in own)
                if best is None or ov > best[0]:
                    best = (ov, moved)
            for (a, y), v in best[1]:
                if a > front:
                    paint.append((_rc(a, y, d), v))
    else:
        for cells in comps:
            mk = _marker(g, cells)
            if dname == 'marker':
                if not mk:
                    continue
                dn = _marker_dir(cells, mk)
                if dn is None:
                    continue
            else:
                dn = dname
            d = DIRS[dn]
            amax = _amax(d, H, W)
            ay = {}
            for rc in cells:
                ay[_ay(rc, d)] = g[rc[0]][rc[1]]
            A = [a for a, _ in ay]
            front, back = max(A), min(A)
            if front == amax or front - back + 1 < period:
                continue
            ylo, yhi = -10 ** 9, 10 ** 9
            if mk and win != 'inf':
                depth = front - back + 1
                rad = {'depth-1': depth - 1, 'depth': depth, '0': 0}[win]
                ys = [_ay(rc, d)[1] for rc in mk]
                ylo, yhi = min(ys) - rad, max(ys) + rad
            layers = {}
            for (a, y), v in ay.items():
                if a > front - period and ylo <= y <= yhi:
                    layers.setdefault(a, []).append((y, v))
            a = front + 1
            while a <= amax:
                src = front - period + 1 + (a - front - 1) % period
                for y, v in layers.get(src, ()):
                    paint.append((_rc(a, y, d), v))
                a += 1
    for (r, c), v in paint:
        if 0 <= r < H and 0 <= c < W and out[r][c] == bg:
            out[r][c] = v if colour == 'same' else colour
    return out


def _params(colours):
    for conn in (4, 8):
        for colour in ['same'] + colours:
            for dn in ('U', 'D', 'L', 'R'):         # a complete exemplar, when present, is preferred
                yield (conn, 'exemplar', dn, 1, 'inf', colour)
            for dn in ('marker', 'U', 'D', 'L', 'R'):
                for period in (1, 2, 3):
                    for win in ('inf', 'depth-1', 'depth', '0'):
                        if dn != 'marker' and win != 'inf':
                            continue
                        yield (conn, 'self', dn, period, win, colour)


def fam_extrusion(train):
    # quick rejection: same shape, only background cells change, something changes
    new_colours = set()
    changed = False
    for p in train:
        I, O = p['input'], p['output']
        if len(I) != len(O) or any(len(a) != len(b) for a, b in zip(I, O)):
            return
        bg = _bg(I)
        for a, b in zip(I, O):
            for x, y in zip(a, b):
                if x != y:
                    if x != bg:
                        return
                    changed = True
                    new_colours.add(y)
    if not changed:
        return
    in_colours = set(v for p in train for row in p['input'] for v in row)
    consts = sorted(c for c in new_colours if c not in in_colours) if len(new_colours) == 1 else []
    consts += sorted(c for c in new_colours if c in in_colours and len(new_colours) == 1)
    for P in _params(consts):
        def fn(g, P=P):
            return _extrude(g, P)
        try:
            if all(fn(p['input']) == p['output'] for p in train):
                conn, ref, dn, period, win, colour = P
                yield (f"cad:extrusion[conn={conn},ref={ref},dir={dn},period={period},win={win},colour={colour}]", 3, fn)
                return
        except Exception:
            continue


FAMILIES = (fam_extrusion,)
