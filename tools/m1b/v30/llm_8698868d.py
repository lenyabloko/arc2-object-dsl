"""Family for ARC task 8698868d -- concept: GENUS (topology; first Betti number = number of holes).

Picture: a *board* of tiled solid panels, each panel marked with a few background-coloured pinholes, and a
set of loose solid *tiles* elsewhere on the background, each pierced by background holes.  The number of
pinholes on a panel is its genus label; every loose tile has a genus (its number of holes).  Each tile is
slotted into the panel with the same genus: the panel keeps its colour as a frame, the tile is inset in its
centre, and the tile's holes show the panel colour through them.  The output is the board alone.

Everything is induced from the input / training pairs:
  background = most common colour of the input
  board      = the non-background 4-connected region made of the most colours (ties: the largest);
               panels = its same-colour 4-connected parts; tiles = every other non-background region
  genus      = number of connected components of background cells inside an object's bounding box
Declared finite parameter domain, chosen by fitting the training pairs:
  conn in {4, 8}  -- the connectivity used to count holes (a diagonal touch joins holes only under 8)
"""
from collections import Counter

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def components(cells, nbrs):
    """Connected components of a set of (r, c) cells."""
    cells, out = set(cells), []
    while cells:
        s = cells.pop()
        comp, stack = [s], [s]
        while stack:
            r, c = stack.pop()
            for dr, dc in nbrs:
                q = (r + dr, c + dc)
                if q in cells:
                    cells.remove(q)
                    comp.append(q)
                    stack.append(q)
        out.append(comp)
    return out


def bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def genus(g, bg, box, nbrs):
    r0, c0, r1, c1 = box
    holes = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == bg]
    return len(components(holes, nbrs))


def slot_tiles(g, conn):
    H, W = len(g), len(g[0])
    bg = most_common_colour(g)
    nbrs = N4 if conn == 4 else N8
    fg = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    regions = components(fg, N4)
    if len(regions) < 2:
        return None
    board = max(regions, key=lambda comp: (len({g[r][c] for r, c in comp}), len(comp)))
    tiles = [comp for comp in regions if comp is not board]

    # panels: same-colour parts of the board
    by_col = {}
    for r, c in board:
        by_col.setdefault(g[r][c], []).append((r, c))
    panels = [p for cells in by_col.values() for p in components(cells, N4)]
    if len(panels) != len(tiles):
        return None

    tile_info = {}
    for t in tiles:
        box = bbox(t)
        k = genus(g, bg, box, nbrs)
        if k in tile_info:  # genus must identify the tile uniquely
            return None
        tile_info[k] = box

    R0, C0, R1, C1 = bbox(board)
    out = [row[C0:C1 + 1] for row in g[R0:R1 + 1]]
    used = set()
    for p in panels:
        pr0, pc0, pr1, pc1 = pbox = bbox(p)
        colour = g[p[0][0]][p[0][1]]
        k = genus(g, bg, pbox, nbrs)
        if k not in tile_info or k in used:
            return None
        used.add(k)
        tr0, tc0, tr1, tc1 = tile_info[k]
        ph, pw, th, tw = pr1 - pr0 + 1, pc1 - pc0 + 1, tr1 - tr0 + 1, tc1 - tc0 + 1
        if th > ph or tw > pw:
            return None
        for r in range(pr0, pr1 + 1):
            for c in range(pc0, pc1 + 1):
                out[r - R0][c - C0] = colour
        orow, ocol = pr0 + (ph - th) // 2, pc0 + (pw - tw) // 2
        for dr in range(th):
            for dc in range(tw):
                v = g[tr0 + dr][tc0 + dc]
                out[orow + dr - R0][ocol + dc - C0] = colour if v == bg else v
    return out


def fam_genus(train):
    for conn in (4, 8):
        fn = (lambda cn: (lambda g: slot_tiles(g, cn)))(conn)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("topology:genus[conn=%d]" % conn, 3, fn)


FAMILIES = (fam_genus,)
