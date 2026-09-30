"""Family for ARC b5ca7ac4 -- concept: ELECTROPHORESIS (physics / physical chemistry).

A grid is a gel; every framed rectangle ("particle": a one-cell-thick border of one colour around a uniform core)
carries a charge given by its border colour.  Each charge species migrates toward its electrode (a grid edge) and
the particles of one species pile up flush against that edge and against each other in arrival order (nearest
first), like bands at an electrode.  Different species drift independently (they pass through each other).

Induced from train: background (most frequent colour), the direction (electrode) of every border colour, chosen
from the finite domain {left, right, up, down, stay}.  Nothing about sizes, counts or coordinates is stored.
"""
from collections import Counter
from itertools import product

DIRS = {'L': (0, -1), 'R': (0, 1), 'U': (-1, 0), 'D': (1, 0), '0': (0, 0)}


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _particles(g, bg):
    """Parse the grid into non-overlapping framed rectangles: border one colour f != bg, interior (>=1 cell)
    uniform colour != f.  Returns list of (r, c, h, w, f, core) or None if some non-bg cell is left unexplained."""
    H, W = len(g), len(g[0])
    used = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            f = g[r][c]
            if f == bg or used[r][c]:
                continue
            best = None
            wmax = 0
            while c + wmax < W and g[r][c + wmax] == f and not used[r][c + wmax]:
                wmax += 1
            hmax = 0
            while r + hmax < H and g[r + hmax][c] == f and not used[r + hmax][c]:
                hmax += 1
            for h in range(hmax, 2, -1):
                for w in range(wmax, 2, -1):
                    if any(g[r + h - 1][c + j] != f or used[r + h - 1][c + j] for j in range(w)):
                        continue
                    if any(g[r + i][c + w - 1] != f or used[r + i][c + w - 1] for i in range(h)):
                        continue
                    core = {g[r + i][c + j] for i in range(1, h - 1) for j in range(1, w - 1)}
                    if len(core) != 1 or f in core:
                        continue
                    best = (r, c, h, w, f, core.pop())
                    break
                if best:
                    break
            if best is None:
                return None
            for i in range(best[2]):
                for j in range(best[3]):
                    used[r + i][c + j] = True
            out.append(best)
    return out


def _migrate(g, bg, charge):
    parts = _particles(g, bg)
    if parts is None:
        return None
    H, W = len(g), len(g[0])
    placed = []
    for species in sorted({p[4] for p in parts}):
        d = charge.get(species)
        if d is None:
            return None
        dr, dc = DIRS[d]
        group = [p for p in parts if p[4] == species]
        # nearest to the electrode first
        group.sort(key=lambda p: -(p[0] * dr + p[1] * dc + (p[2] - 1) * max(dr, 0) + (p[3] - 1) * max(dc, 0)))
        settled = []
        for (r, c, h, w, f, k) in group:
            def free(rr, cc):
                if rr < 0 or cc < 0 or rr + h > H or cc + w > W:
                    return False
                return all(rr + h <= R or R + HH <= rr or cc + w <= C or C + WW <= cc
                           for (R, C, HH, WW, _, _) in settled)
            if (dr, dc) != (0, 0):
                while free(r + dr, c + dc):
                    r, c = r + dr, c + dc
            settled.append((r, c, h, w, f, k))
        placed.extend(settled)
    out = [[bg] * W for _ in range(H)]
    for (r, c, h, w, f, k) in placed:
        for i in range(h):
            for j in range(w):
                out[r + i][c + j] = f if i in (0, h - 1) or j in (0, w - 1) else k
    return out


def fam_electrophoresis(train):
    bgs = [_bg(p["input"]) for p in train]
    species = set()
    for p, bg in zip(train, bgs):
        parts = _particles(p["input"], bg)
        if not parts:
            return
        species |= {q[4] for q in parts}
    species = sorted(species)
    if len(species) > 4:
        return
    for combo in product('LRUD0', repeat=len(species)):
        if all(d == '0' for d in combo):
            continue
        charge = dict(zip(species, combo))

        def fn(g, charge=charge):
            return _migrate(g, _bg(g), charge)

        if all(fn(p["input"]) == p["output"] for p in train):
            tag = ','.join(f'{s}->{d}' for s, d in charge.items())
            yield (f"physics:electrophoresis[{tag}]", 3, fn)
            return


FAMILIES = (fam_electrophoresis,)
