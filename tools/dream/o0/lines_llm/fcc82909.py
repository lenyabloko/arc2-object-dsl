"""Reviewer line family for ARC card fcc82909 (g04 shadows / geometric optics: ray casting).

Every source object (connected non-background component, multi-colour allowed)
emits parallel rays in one direction d: one ray per 'front' cell, i.e. per
object cell whose neighbour in direction d lies outside the object.  Each ray
starts at that neighbour and travels along d, painting the shadow colour onto
the grid, for a length that is either a constant, unlimited (to the border),
or an attribute of the emitting object (number of distinct colours, number of
cells, depth along d, breadth across d).  Obstacles (other objects' cells in
the input) either stop the ray, are passed under (not painted), or are painted
over; the emitter's own cells always stop its rays.  All parameters are induced
by enumerating a small declared domain and keeping the settings that
reproduce every training pair.
"""
from collections import Counter

CARD = "fcc82909"
LINE = ('Group g04 ("shadows cast from objects") -- one family: geometric optics / ray casting.: '
        'Concept (optics / computer graphics): RAY CASTING. Every source object emits parallel rays in a '
        "direction d (one ray per 'front' cell of the object, i.e. (group family g04_shadow)")

READING = {
    "generator": "Every object casts a shadow: from each of its front cells (object cells whose neighbour in "
                 "direction d is outside the object) a straight ray of the shadow colour is drawn along d, "
                 "starting just outside the object.",
    "stop": "A ray stops after L cells, where L is a constant, unlimited, or an attribute of its object "
            "(number of distinct colours, cell count, depth along d, breadth across d); it is clipped at the "
            "grid border, always stops at its own object, and at other objects either stops, passes under, "
            "or paints over.",
    "params": "d ∈ {down, up, right, left, 4 diagonals} · L ∈ {n_colours, n_cells, depth, breadth, ∞, k "
              "(k from run lengths seen in train diffs)} · colour ∈ {fixed induced colour, colour of the "
              "front cell, object's majority colour} · occlusion ∈ {stop, under, over} · connectivity ∈ {8, 4}",
    "participants": "Background = most frequent colour of the grid; source objects = connected components "
                    "(8- or 4-connected) of non-background cells, any mix of colours; front cells found per "
                    "object from d; obstacles = non-background cells of the input.",
    "preconditions": "Input and output grids have the same size in every train pair; the output differs from "
                     "the input only by the drawn rays (all objects stay); at least one pair changes.",
}

_DIRS = [("down", (1, 0)), ("up", (-1, 0)), ("right", (0, 1)), ("left", (0, -1)),
         ("downright", (1, 1)), ("downleft", (1, -1)), ("upright", (-1, 1)), ("upleft", (-1, -1))]
_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
_N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def _bg(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _objects(g, bg, conn):
    h, w = len(g), len(g[0])
    nb = _N8 if conn == 8 else _N4
    seen = [[False] * w for _ in range(h)]
    objs = []
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == bg:
                continue
            seen[r][c] = True
            stack, comp = [(r, c)], []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in nb:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            objs.append(sorted(comp))
    return objs


def _length(g, obj, d, lmode, k):
    dr, dc = d
    if lmode == "inf":
        return None
    if lmode == "const":
        return k
    if lmode == "ncol":
        return len({g[r][c] for r, c in obj})
    if lmode == "ncell":
        return len(obj)
    if lmode == "depth":
        return len({r * dr + c * dc for r, c in obj})
    if lmode == "breadth":
        return len({r * dc - c * dr for r, c in obj})
    raise ValueError(lmode)


def _make(d, lmode, k, cmode, ccol, occ, conn):
    dr, dc = d

    def fn(grid):
        g = [list(r) for r in grid]
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [r[:] for r in g]
        for obj in _objects(g, bg, conn):
            cells = set(obj)
            L = _length(g, obj, d, lmode, k)
            if cmode == "majority":
                cnt = Counter(g[r][c] for r, c in obj)
                maj = max(sorted(cnt), key=lambda v: cnt[v])
            for r, c in obj:
                nr, nc = r + dr, c + dc
                if (nr, nc) in cells:
                    continue  # not a front cell
                col = ccol if cmode == "fixed" else (g[r][c] if cmode == "source" else maj)
                steps = 0
                while 0 <= nr < H and 0 <= nc < W and (L is None or steps < L):
                    if (nr, nc) in cells:
                        break  # own body blocks
                    v = g[nr][nc]
                    if v != bg:
                        if occ == "stop":
                            break
                        if occ == "over":
                            out[nr][nc] = col
                    else:
                        out[nr][nc] = col
                    steps += 1
                    nr += dr
                    nc += dc
        return out

    return fn


def _run_lengths(train):
    """Lengths of straight runs of changed cells (rows, columns, diagonals) in the train diffs."""
    ks = set()
    for p in train:
        gi, go = p["input"], p["output"]
        H, W = len(gi), len(gi[0])
        ch = {(r, c) for r in range(H) for c in range(W) if gi[r][c] != go[r][c]}
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            for r, c in ch:
                if (r - dr, c - dc) in ch:
                    continue
                n = 0
                while (r + n * dr, c + n * dc) in ch:
                    n += 1
                ks.add(n)
    return sorted(ks)


def fam(train):
    if not train:
        return
    changed = False
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or not gi[0] or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        if gi != go:
            changed = True
    if not changed:
        return

    # shadow colour candidates: a single colour shared by every changed cell in every pair
    newcols = set()
    for p in train:
        gi, go = p["input"], p["output"]
        for r in range(len(gi)):
            for c in range(len(gi[0])):
                if gi[r][c] != go[r][c]:
                    newcols.add(go[r][c])
    cmodes = []
    if len(newcols) == 1:
        cmodes.append(("fixed", next(iter(newcols)), 0))
    cmodes += [("source", None, 1), ("majority", None, 1)]

    lmodes = [("ncol", 0, 0), ("ncell", 0, 0), ("depth", 0, 0), ("breadth", 0, 0), ("inf", 0, 1)]
    lmodes += [("const", k, 2) for k in _run_lengths(train)[:12]]

    targets = [[list(r) for r in p["output"]] for p in train]
    variants = []
    for di, (dname, d) in enumerate(_DIRS):
        dcost = 0 if di < 4 else 2
        for conn, ccost in ((8, 0), (4, 1)):
            for occ, ocost in (("stop", 0), ("under", 1), ("over", 2)):
                for cmode, ccol, cc in cmodes:
                    for lmode, k, lc in lmodes:
                        cost = 10 + dcost + ccost + ocost + cc + lc
                        lname = f"const{k}" if lmode == "const" else lmode
                        cname = f"c{ccol}" if cmode == "fixed" else cmode
                        name = (f"ray_cast[d={dname},L={lname},colour={cname},occ={occ},conn={conn}]")
                        variants.append((cost, di, name, (d, lmode, k, cmode, ccol, occ, conn)))
    variants.sort(key=lambda t: (t[0], t[1]))

    for cost, _, name, args in variants:
        fn = _make(*args)
        ok = True
        for p, tgt in zip(train, targets):
            try:
                if fn(p["input"]) != tgt:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield (name, cost, fn)


FAMILIES = [fam]
