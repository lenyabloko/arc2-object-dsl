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


def board_components(board, bg):
    """Label the 4-connected non-background components of the (piece-free) board.
    Returns (label grid with -1 on background, [(colour set, size, r0, r1, c0, c1)])."""
    H, W = len(board), len(board[0])
    lab = [[-1] * W for _ in range(H)]
    info = []
    for r in range(H):
        for c in range(W):
            if board[r][c] == bg or lab[r][c] >= 0:
                continue
            k = len(info)
            lab[r][c] = k
            stack, n, colours = [(r, c)], 0, set()
            r0 = r1 = r
            c0 = c1 = c
            while stack:
                y, x = stack.pop()
                n += 1
                colours.add(board[y][x])
                if y < r0: r0 = y
                if y > r1: r1 = y
                if x < c0: c0 = x
                if x > c1: c1 = x
                for dy, dx in DIRS:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and lab[ny][nx] < 0 and board[ny][nx] != bg:
                        lab[ny][nx] = k
                        stack.append((ny, nx))
            info.append((frozenset(colours), n, r0, r1, c0, c1))
    return lab, info


def fits_mortise_fast(lab, info, H, W, plug):
    """Exactly fits_mortise(board, bg, plug) for a plug of background cells: the flood-filled timber is
    the union of the board components touching the plug, so work on precomputed component summaries."""
    labels = set()
    for y, x in plug:
        for dy, dx in DIRS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W:
                k = lab[ny][nx]
                if k >= 0:
                    labels.add(k)
    if not labels:
        return None
    colours, n = set(), 0
    r0 = c0 = 1 << 30
    r1 = c1 = -1
    for k in labels:
        cs, sz, a0, a1, b0, b1 = info[k]
        colours |= cs
        n += sz
        if a0 < r0: r0 = a0
        if a1 > r1: r1 = a1
        if b0 < c0: c0 = b0
        if b1 > c1: c1 = b1
    if len(colours) != 1:
        return None
    if any(not (r0 <= y <= r1 and c0 <= x <= c1) for y, x in plug):
        return None
    if n + len(plug) != (r1 - r0 + 1) * (c1 - c0 + 1):
        return None
    return (r0, r1, c0, c1)


def candidates(board, bg, piece_cells, motions, mirror, binfo=None):
    """All insertions of one piece: list of (socket_rect, {cell: colour})."""
    H, W = len(board), len(board[0])
    if binfo is None:
        binfo = board_components(board, bg)
    lab, info = binfo
    if not info:
        return []  # no timber at all: no plug can touch one, so nothing fits
    # background cells touching a timber: any fitting plug contains at least one of them
    front = [(y, x) for y in range(H) for x in range(W) if board[y][x] == bg and any(
        0 <= y + dy < H and 0 <= x + dx < W and lab[y + dy][x + dx] >= 0 for dy, dx in DIRS)]
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
        mr0 = min(p[0] for p, _ in moved)
        mr1 = max(p[0] for p, _ in moved)
        mc0 = min(p[1] for p, _ in moved)
        mc1 = max(p[1] for p, _ in moved)
        # translations keeping the whole moved piece on the board (others fail the bounds checks)
        dr_lo, dr_hi, dc_lo, dc_hi = -mr0, H - 1 - mr1, -mc0, W - 1 - mc1
        if dr_lo > dr_hi or dc_lo > dc_hi:
            continue
        for tenon_col in cols:
            plug0 = [p for p, v in moved if v == tenon_col]
            rest0 = [(p, v) for p, v in moved if v != tenon_col]
            # translations putting some plug cell next to a timber, in the original row-major anchor order
            shifts = sorted({(qy - py, qx - px) for py, px in plug0 for qy, qx in front
                             if dr_lo <= qy - py <= dr_hi and dc_lo <= qx - px <= dc_hi})
            for dr, dc in shifts:
                plug = set()
                ok = True
                for y, x in plug0:
                    y, x = y + dr, x + dc
                    if board[y][x] != bg:
                        ok = False
                        break
                    plug.add((y, x))
                if not ok:
                    continue
                shoulder = {}
                for (y, x), v in rest0:
                    y, x = y + dr, x + dc
                    if board[y][x] != bg:
                        ok = False
                        break
                    shoulder[(y, x)] = recol[v]
                if not ok:
                    continue
                rect = fits_mortise_fast(lab, info, H, W, plug)
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
    binfo = board_components(board, bg)
    cands = [candidates(board, bg, [(r, c, g[r][c]) for r, c in comp], motions, mirror, binfo) for comp in pieces]

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


def may_fit(train):
    """Necessary conditions shared by every parameter setting (cheap rejection of unrelated tasks):
    the output keeps the input's shape, the input has at least one two-colour piece, every timber cell
    is left untouched, and cells that are background once the pieces are lifted receive only the
    background or a piece colour."""
    for p in train:
        g, o = p["input"], p["output"]
        H, W = len(g), len(g[0])
        if len(o) != H or any(len(row) != W for row in o):
            return False
        bg = most_common_colour(g)
        piece_cells, piece_cols = set(), set()
        for comp in components(g, bg):
            cs = {g[r][c] for r, c in comp}
            if len(cs) >= 2:
                piece_cells.update(comp)
                piece_cols |= cs
        if not piece_cells:
            return False
        for r in range(H):
            for c in range(W):
                v, w = g[r][c], o[r][c]
                if v != bg and (r, c) not in piece_cells:
                    if w != v:
                        return False
                elif w != bg and w not in piece_cols:
                    return False
    return True


def fam_mortise_tenon(train):
    try:
        if not may_fit(train):
            return
    except Exception:
        pass
    for motions, mirror in (("rotations", "carry"), ("dihedral", "carry"), ("dihedral", "swap")):
        def fn(g, motions=motions, mirror=mirror):
            return assemble(g, motions, mirror)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("mechanics:mortise_tenon[motions=%s,mirror=%s]" % (motions, mirror), 3, fn)
        except Exception:
            continue


FAMILIES = (fam_mortise_tenon,)
