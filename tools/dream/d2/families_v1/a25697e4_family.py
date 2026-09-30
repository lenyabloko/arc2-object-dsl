"""Family for ARC task a25697e4 -- concept: MORTISE AND TENON (mechanics / joinery), with
black-and-white ANTISYMMETRY (crystallography) for mirrored pieces.

Picture: single-colour blocks are *mortised* timbers -- a rectangle with a notch (mortise) cut out of it.
Two-colour pieces are loose joints: one colour part is the *tenon* whose shape is exactly the notch.
Each piece is lifted off the board, turned (rigid motion of the square lattice), and slid so that its
tenon fills the notch: after insertion the timber plus tenon is a solid rectangle, and the rest of
the piece (its shoulder) hangs outside on background.  If the piece had to be turned face-down
(an orientation-reversing motion, i.e. a mirror) its two colours are exchanged -- the Heesch/Shubnikov
black-and-white antisymmetry rule: improper isometries carry a colour reversal.

Everything is induced; nothing about coordinates, sizes or colour numbers is stored:
  background = most common colour of the input
  pieces     = 4-connected non-background components using >= 2 colours
  timbers    = everything else that is non-background (single-colour components)
  tenon      = whichever colour part of a piece fills a notch so that timber + tenon is a filled rectangle
               equal to the timber's own bounding box
Declared finite parameter domains, chosen by fitting the training pairs:
  motions in {"rotations", "dihedral"}  -- proper rotations only / rotations and reflections
  mirror  in {"carry", "swap"}          -- reflected piece keeps its colours / swaps its two colours
"""
from collections import Counter

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))

# (name, determinant, map) for the 8 symmetries of the square lattice; proper motions first
MOTIONS = (
    ("id", 1, lambda r, c: (r, c)),
    ("rot90", 1, lambda r, c: (c, -r)),
    ("rot180", 1, lambda r, c: (-r, -c)),
    ("rot270", 1, lambda r, c: (-c, r)),
    ("flipV", -1, lambda r, c: (-r, c)),
    ("flipH", -1, lambda r, c: (r, -c)),
    ("transpose", -1, lambda r, c: (c, r)),
    ("antitranspose", -1, lambda r, c: (-c, -r)),
)


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def components(g, bg):
    """4-connected components of non-background cells (colour-agnostic)."""
    H, W = len(g), len(g[0])
    seen, comps = set(), []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in DIRS:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            comps.append(comp)
    return comps


def fits_mortise(board, bg, plug):
    """plug: set of cells.  True (and the socket's rectangle) if the plug lies on background and,
    joined with the non-background cells it touches (transitively), forms a filled rectangle of a
    single timber colour whose bounding box is the timber's own bounding box."""
    H, W = len(board), len(board[0])
    stack, seen, timber = list(plug), set(plug), set()
    while stack:
        y, x = stack.pop()
        for dy, dx in DIRS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and board[ny][nx] != bg:
                seen.add((ny, nx))
                timber.add((ny, nx))
                stack.append((ny, nx))
    if not timber or len({board[y][x] for y, x in timber}) != 1:
        return None
    rows = [y for y, _ in timber]
    cols = [x for _, x in timber]
    r0, r1, c0, c1 = min(rows), max(rows), min(cols), max(cols)
    if any(not (r0 <= y <= r1 and c0 <= x <= c1) for y, x in plug):
        return None  # tenon must sit inside the timber's own outline, not extend it
    if len(timber) + len(plug) != (r1 - r0 + 1) * (c1 - c0 + 1):
        return None
    return (r0, r1, c0, c1)


def candidates(board, bg, piece_cells, motions, mirror):
    """All insertions of one piece: list of (socket_rect, {cell: colour})."""
    H, W = len(board), len(board[0])
    cols = sorted({v for _, _, v in piece_cells})
    out = []
    for _, det, f in MOTIONS:
        if motions == "rotations" and det < 0:
            continue
        if det < 0 and mirror == "swap":
            if len(cols) != 2:
                continue
            recol = {cols[0]: cols[1], cols[1]: cols[0]}
        else:
            recol = {k: k for k in cols}
        moved = [(f(r, c), v) for r, c, v in piece_cells]
        for tenon_col in cols:
            plug0 = [p for p, v in moved if v == tenon_col]
            rest0 = [(p, v) for p, v in moved if v != tenon_col]
            ar, ac = plug0[0]
            for hr in range(H):
                for hc in range(W):
                    if board[hr][hc] != bg:
                        continue
                    dr, dc = hr - ar, hc - ac
                    plug = set()
                    ok = True
                    for y, x in plug0:
                        y, x = y + dr, x + dc
                        if not (0 <= y < H and 0 <= x < W) or board[y][x] != bg:
                            ok = False
                            break
                        plug.add((y, x))
                    if not ok:
                        continue
                    shoulder = {}
                    for (y, x), v in rest0:
                        y, x = y + dr, x + dc
                        if not (0 <= y < H and 0 <= x < W) or board[y][x] != bg:
                            ok = False
                            break
                        shoulder[(y, x)] = recol[v]
                    if not ok:
                        continue
                    rect = fits_mortise(board, bg, plug)
                    if rect is None:
                        continue
                    placed = dict(shoulder)
                    for p in plug:
                        placed[p] = recol[tenon_col]
                    out.append((rect, placed))
    return out


def assemble(g, motions, mirror):
    bg = most_common_colour(g)
    comps = components(g, bg)
    pieces = [comp for comp in comps if len({g[r][c] for r, c in comp}) >= 2]
    if not pieces:
        return None
    board = [row[:] for row in g]
    for comp in pieces:
        for r, c in comp:
            board[r][c] = bg
    cands = [candidates(board, bg, [(r, c, g[r][c]) for r, c in comp], motions, mirror) for comp in pieces]

    # joint assignment: each piece into its own mortise, no two pieces overlapping
    order = sorted(range(len(pieces)), key=lambda i: len(cands[i]))
    choice = {}

    def solve(k, used_rects, used_cells):
        if k == len(order):
            return True
        i = order[k]
        if not cands[i]:
            choice[i] = None  # no mortise for this piece: it stays where it is
            return solve(k + 1, used_rects, used_cells)
        for rect, placed in cands[i]:
            if rect in used_rects or any(p in used_cells for p in placed):
                continue
            choice[i] = (rect, placed)
            if solve(k + 1, used_rects | {rect}, used_cells | set(placed)):
                return True
        return False

    if not solve(0, frozenset(), frozenset()):
        return None
    out = [row[:] for row in board]
    for i, comp in enumerate(pieces):
        if choice[i] is None:
            for r, c in comp:
                out[r][c] = g[r][c]
            continue
        for (y, x), v in choice[i][1].items():
            out[y][x] = v
    return out


def fam_mortise_tenon(train):
    for motions, mirror in (("rotations", "carry"), ("dihedral", "carry"), ("dihedral", "swap")):
        def fn(g, motions=motions, mirror=mirror):
            return assemble(g, motions, mirror)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("mechanics:mortise_tenon[motions=%s,mirror=%s]" % (motions, mirror), 3, fn)
        except Exception:
            continue


FAMILIES = (fam_mortise_tenon,)
