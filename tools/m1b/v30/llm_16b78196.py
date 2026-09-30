"""Family for ARC task 16b78196 -- concept: JIGSAW (interlocking puzzle assembly; mechanics / joinery).

A wall (the single-colour component that spans the whole grid in one direction) has sockets cut into its faces.
The loose pieces are jigsaw pieces: along the axis across the wall each piece has two faces (near / far).  A face is
FLAT when it is a full straight edge (the bbox row is completely filled) -- a flat face is a puzzle border and is left
free.  Every non-flat face is a tab/blank profile that must be mated exactly with a complementary profile: either a
socket of the wall or the opposite face of another piece of the same width.  Two profiles mate when, column by column,
the depth of one plus the depth of the other is constant, i.e. the two parts close up with no gap and no overlap.
The pieces are therefore assembled (translation only) into columns (chains) that start in a wall socket and end in a
piece whose outer face is flat; every piece is used exactly once and nothing may overlap the wall, another piece, or
leave the grid.  Unmatched sockets stay empty.  The output is the wall plus the assembled pieces on background.

Roles: background = most common colour; wall = component whose bbox spans the full width (or height -- the grid is
transposed, solved and transposed back); pieces = every other connected single-colour component.
Induced parameters (small finite domains):
  conn   in {4, 8}                 -- connectivity used to cut the pieces out
  unique in {'first', 'unique'}    -- accept the first exact assembly vs. demand that the assembly is unique
"""
from collections import Counter


def _background(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg, conn):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            seen[r][c] = True
            stack, cells = [(r, c)], []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] == col:
                        seen[yy][xx] = True
                        stack.append((yy, xx))
            comps.append((col, cells))
    return comps


def _transpose(g):
    return [list(r) for r in zip(*g)]


class _Piece:
    def __init__(self, col, cells):
        self.col = col
        r0 = min(r for r, _ in cells); c0 = min(c for _, c in cells)
        self.cells = [(r - r0, c - c0) for r, c in cells]
        self.h = max(r for r, _ in self.cells) + 1
        self.w = max(c for _, c in self.cells) + 1
        top = [self.h] * self.w
        bot = [-1] * self.w
        for r, c in self.cells:
            top[c] = min(top[c], r)
            bot[c] = max(bot[c], r)
        self.top = top                                   # depth of the far-up face per column
        self.bot = [self.h - 1 - b for b in bot]         # depth of the down face per column

    def face(self, side):                                # side 'up' -> top profile, 'down' -> bottom profile
        return self.top if side == 'up' else self.bot


def _flat(profile):
    return all(d == 0 for d in profile)


def _const(xs):
    return len(set(xs)) == 1


class _Abort(Exception):
    pass


_BUDGET = 100000        # safety net only: search work units (every ARC task uses < 100); exceeded -> no assembly


def _assemble_h(g, bg, wall_cells, pieces, mode):
    """Horizontal wall: pieces stack upward on its top face or downward from its bottom face.
    Returns the output grid, or None when no exact assembly exists (or, in 'unique' mode, when it is ambiguous)."""
    H, W = len(g), len(g[0])
    wall = set(wall_cells)
    wtop = [min((r for r, c in wall if c == x), default=None) for x in range(W)]
    wbot = [max((r for r, c in wall if c == x), default=None) for x in range(W)]
    n = len(pieces)
    solutions = set()
    # identical pieces (same colour, same shape) are interchangeable: trying a second identical piece at the same
    # search node explores a subset of the grids the first one explored, so it is skipped (exact pruning).
    keys = [(p.col, tuple(sorted(p.cells))) for p in pieces]
    mounts_cache = {}
    work = [0]

    def tick(k):
        work[0] += k
        if work[0] > _BUDGET:
            raise _Abort()

    def place(occ, p, r0, c0):
        tick(1 + (len(occ) >> 5))
        new = dict(occ)
        for r, c in p.cells:
            y, x = r0 + r, c0 + c
            if not (0 <= y < H and 0 <= x < W) or (y, x) in wall or (y, x) in occ:
                return None
            new[(y, x)] = p.col
        return new

    def wall_mounts(p, side):
        k = (id(p), side)
        if k not in mounts_cache:
            mounts_cache[k] = _wall_mounts(p, side)
        return mounts_cache[k]

    def _wall_mounts(p, side):
        """Rows/cols where p's wall-facing (non-flat) face closes exactly onto the wall surface.
        side 'up': p stands on the wall's top face; 'down': p hangs from its bottom face."""
        face = p.bot if side == 'up' else p.top
        if _flat(face):
            return []
        surf_all = wtop if side == 'up' else wbot
        out = []
        for c0 in range(0, W - p.w + 1):
            surf = surf_all[c0:c0 + p.w]
            if any(s is None for s in surf):
                continue
            if side == 'up':      # bottom-most cell of column c lands just above the wall
                vals = [surf[c] - 1 - (p.h - 1 - face[c]) for c in range(p.w)]
            else:                 # top-most cell of column c lands just below the wall
                vals = [surf[c] + 1 - face[c] for c in range(p.w)]
            if _const(vals):
                out.append((vals[0], c0))
        return out

    def extend(occ, used, need, prev, r0, c0, side):
        """prev is placed at (r0, c0); continue the chain outward (side) until a flat outer face closes it."""
        outer = prev.top if side == 'up' else prev.bot
        if _flat(outer):
            return search(occ, used) if need in used else False
        tried = set()
        for j in range(n):
            if j in used:
                continue
            tick(1)
            if keys[j] in tried:
                continue
            tried.add(keys[j])
            q = pieces[j]
            inner = q.bot if side == 'up' else q.top
            if q.w != prev.w or _flat(inner):
                continue
            if side == 'up':
                vals = [r0 + outer[c] - 1 - (q.h - 1 - inner[c]) for c in range(q.w)]
            else:
                vals = [r0 + prev.h - 1 - outer[c] + 1 - inner[c] for c in range(q.w)]
            if not _const(vals):
                continue
            new = place(occ, q, vals[0], c0)
            if new is not None and extend(new, used | {j}, need, q, vals[0], c0, side):
                return True
        return False

    def search(occ, used):
        if len(used) == n:
            out = [[bg] * W for _ in range(H)]
            for r, c in wall:
                out[r][c] = g[r][c]
            for (r, c), v in occ.items():
                out[r][c] = v
            solutions.add(tuple(map(tuple, out)))
            return mode == 'first' or len(solutions) > 1
        need = min(k for k in range(n) if k not in used)   # canonical: next chain must contain this piece
        tried = set()
        for s in range(n):
            if s in used:
                continue
            tick(1)
            if keys[s] in tried:
                continue
            tried.add(keys[s])
            p = pieces[s]
            for side in ('up', 'down'):
                for r0, c0 in wall_mounts(p, side):
                    new = place(occ, p, r0, c0)
                    if new is not None and extend(new, used | {s}, need, p, r0, c0, side):
                        return True
        return False

    try:
        search({}, frozenset())
    except _Abort:
        return None
    if not solutions or (mode == 'unique' and len(solutions) != 1):
        return None
    return [list(r) for r in next(iter(solutions))]


def _solve(g, conn, mode):
    bg = _background(g)
    H, W = len(g), len(g[0])
    comps = _components(g, bg, conn)
    walls_h = [cc for cc in comps if len({c for _, c in cc[1]}) == W]
    walls_v = [cc for cc in comps if len({r for r, _ in cc[1]}) == H]
    if len(walls_h) == 1 and not walls_v:
        wall, flip = walls_h[0], False
    elif len(walls_v) == 1 and not walls_h:
        wall, flip = walls_v[0], True
    else:
        return None
    if flip:
        g = _transpose(g)
        wall = (wall[0], [(c, r) for r, c in wall[1]])
    pieces = [_Piece(col, cells) for col, cells in _components(g, bg, conn) if sorted(cells) != sorted(wall[1])]
    # exact shortcut: a piece with both faces flat has no wall mount and cannot extend a chain, so it can never be
    # placed and the full search would (slowly) find no assembly.
    if any(_flat(p.top) and _flat(p.bot) for p in pieces):
        return None
    out = _assemble_h(g, bg, wall[1], pieces, mode)
    if out is None:
        return None
    return _transpose(out) if flip else out


def _pair_possible(p):
    """Exact necessary condition for _solve(input) == output: _solve only returns None or a grid of the input's shape
    holding the wall plus every piece moved by translation (no overlap), i.e. the same multiset of colours."""
    gi, go = p["input"], p["output"]
    if not isinstance(go, list) or len(go) != len(gi) or not gi:
        return False
    W = len(gi[0])
    if any(len(r) != W for r in gi):
        return True                                      # ragged input: make no claim
    if any(not isinstance(r, list) or len(r) != W for r in go):
        return False
    return Counter(v for r in gi for v in r) == Counter(v for r in go for v in r)


def fam_jigsaw(train):
    try:
        if not all(_pair_possible(p) for p in train):
            return
    except Exception:
        pass
    for conn in (4, 8):
        for mode in ('unique', 'first'):
            fn = (lambda cn, md: (lambda g: _solve(g, cn, md)))(conn, mode)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("mechanics:jigsaw[conn=%d,assembly=%s]" % (conn, mode), 3, fn)
                return


FAMILIES = (fam_jigsaw,)
