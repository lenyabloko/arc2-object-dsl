"""Prior family: dock_piece_by_matching (test-blind, induced from training pairs only).

Concept: FIT a loose piece to a target.  Loose pieces are lifted, turned by an allowed rigid motion and
translated to the placement where they match a target; the matched assembly is the answer.

One generator, written once:
  1. ROLES: background = most common colour; non-background cells are cut into components
     (conn 4/8; multi-colour or single-colour); a target body is chosen per criterion (below), the rest are
     loose pieces.
  2. SEARCH: every piece in every orientation of `motion` (translate | rotate | dihedral | dihedral with
     colour swap for mirrored two-colour pieces) is anchored on target cells (translations), and a
     placement is kept when it satisfies the criterion.
  3. CRITERION (frame alternatives, one parameter):
       cover     - a board (colour set whose bounding box holds only its colours and background) has holes =
                   background cells of its box; the pieces, each used once, cover the holes exactly (exact
                   cover, no overlap, area conserved);
       pocket    - a body (all cells of one colour) has pockets = background components of its box; a piece
                   fits when its cells inside the box are exactly whole pockets that open toward the piece's
                   side and nothing overlaps;
       marker    - the board (largest object) carries marker colours (its non-majority colours); a piece fits
                   where its marker cells coincide exactly with the board's marker cells inside its window;
       label     - a piece docks centred into the board slot whose label (number of background holes)
                   equals its own; its holes show the slot colour;
       connector - marker cells (colours that occur only as isolated cells) sit on piece edges; a piece docks
                   where its marker abuts a same-colour marker of an assembled piece on facing edges, the
                   pieces sliding toward each other (nearest pair first, each marker used once).
  4. RESULT: move pieces into place (erase originals) | recolour fitting pieces by a learned colour |
     crop to the board / assembly (or a strip along the docking axis).
"""
from collections import Counter
from functools import lru_cache

CARD = "prior_dock_piece_by_matching"
CONCEPT = "dock_piece_by_matching"
MEMBERS = ["16b78196", "1acc24af", "234bbc79", "4c3d4a41", "5dbc8537", "83eb0a57", "8698868d", "8b9c3697",
           "a25697e4", "a47bf94d", "e8686506", "e9fc42f2"]
READING = {
    "generator": ("Lift each loose piece, try its allowed rigid motions and translations against a target, keep the "
                  "placement where it exactly fills the target's holes/pockets, its marker cells coincide with the "
                  "target's markers, or its connector abuts a matching connector, then move it there (or recolour "
                  "it if it fits) and crop to the assembly when the output is the assembled shape."),
    "stop": ("each piece is placed at most once (cover: all pieces exactly fill all holes; pocket: each pocket "
             "takes at most one piece; connector: docking repeats until no free marker pair remains)."),
    "params": ("criterion in {cover, pocket, marker, connector, label} . motion in {translate, rotate, dihedral, "
               "dihedral-swap} . conn in {4,8} . split in {multi, mono} . pieces in {multi-colour comps, comps "
               "of the learned changing colour} . paint in {keep, body} . result in {move, recolour(learned "
               "colour), crop, inplace, strip}"),
    "participants": ("background = mode; board/body = colour set with a clean box (cover), every colour's "
                     "cells (pocket), largest object (marker), the region of most colours split into single-colour slots (label); pieces = remaining components; markers = board "
                     "minority colours or colours occurring only as isolated cells."),
    "preconditions": ("cover/marker/connector-crop: output smaller than input; pocket/inplace: same shape; "
                      "area conservation (cover); a single learned recolour pair (recolour); every piece "
                      "assembled (connector); at most 30 pieces and bounded search budget."),
}

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))

# (det, map) for the 8 lattice symmetries; proper motions first
_SYM = ((1, lambda r, c: (r, c)), (1, lambda r, c: (c, -r)), (1, lambda r, c: (-r, -c)),
        (1, lambda r, c: (-c, r)), (-1, lambda r, c: (r, -c)), (-1, lambda r, c: (-r, c)),
        (-1, lambda r, c: (c, r)), (-1, lambda r, c: (-c, -r)))
MOTIONS = {"translate": 1, "rotate": 4, "dihedral": 8, "dihedral-swap": 8}
MAXP = 30


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _comps(g, bg, conn=4, mono=False, skip=None):
    """Components of non-background cells as dicts {(r, c): colour}, in reading order of first cell."""
    H, W = len(g), len(g[0])
    nb = N8 if conn == 8 else N4
    seen = set()
    out = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg or (skip and skip(r, c)):
                continue
            col = g[r][c]
            seen.add((r, c))
            st, cells = [(r, c)], {}
            while st:
                y, x = st.pop()
                cells[(y, x)] = g[y][x]
                for dy, dx in nb:
                    q = (y + dy, x + dx)
                    if (0 <= q[0] < H and 0 <= q[1] < W and q not in seen and g[q[0]][q[1]] != bg
                            and (not mono or g[q[0]][q[1]] == col) and not (skip and skip(*q))):
                        seen.add(q)
                        st.append(q)
            out.append(cells)
    return out


def _cc(cells, nb=N4):
    cells = set(cells)
    out = []
    for s in sorted(cells):
        if s not in cells:
            continue
        cells.discard(s)
        st, comp = [s], [s]
        while st:
            y, x = st.pop()
            for dy, dx in nb:
                q = (y + dy, x + dx)
                if q in cells:
                    cells.discard(q)
                    comp.append(q)
                    st.append(q)
        out.append(comp)
    return out


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _norm(items):
    """items: [((r, c), v)] -> tuple sorted, first cell in reading order at (0, 0)."""
    items = sorted(items)
    (r0, c0), _ = items[0]
    return tuple(((r - r0, c - c0), v) for (r, c), v in items)


def _orients(cells, motion):
    """Distinct oriented copies of a piece {cell: colour} -> list of normalised tuples."""
    out = []
    cols = sorted(set(cells.values()))
    for k, (det, f) in enumerate(_SYM[:MOTIONS[motion]]):
        rec = {v: v for v in cols}
        if det < 0 and motion == "dihedral-swap":
            if len(cols) != 2:
                continue
            rec = {cols[0]: cols[1], cols[1]: cols[0]}
        o = _norm([(f(r, c), rec[v]) for (r, c), v in cells.items()])
        if o not in out:
            out.append(o)
    return out


# ------------------------------------------------------------------ criterion: cover (exact cover of holes)
def _tile(holes, pieces, motion, budget):
    kinds = {}
    for p in pieces:
        key = _norm(list(p.items()))
        if key not in kinds:
            kinds[key] = [_orients(p, motion), 0]
        kinds[key][1] += 1
    kinds = [kinds[k] for k in sorted(kinds)]
    free = set(holes)
    placed = {}

    def solve():
        if not free:
            return True
        budget[0] -= 1
        if budget[0] < 0:
            return False
        ar, ac = min(free)
        for k in kinds:
            if not k[1]:
                continue
            for o in k[0]:
                cells = [((ar + r, ac + c), v) for (r, c), v in o]
                if all(q in free for q, _ in cells):
                    for q, v in cells:
                        free.discard(q)
                        placed[q] = v
                    k[1] -= 1
                    if solve():
                        return True
                    k[1] += 1
                    for q, _ in cells:
                        free.add(q)
                        del placed[q]
        return False

    return dict(placed) if solve() else None


def _cover(g, conn, split, motion, frame):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    cnt = Counter(v for row in g for v in row)
    colours = sorted(set(cnt) - {bg})
    if not colours:
        return None
    subsets = sorted((s for s in range(1, 1 << len(colours)) if bin(s).count("1") <= 3),
                     key=lambda s: (bin(s).count("1"), s))
    budget = [60000]
    for s in subsets:
        C = {colours[i] for i in range(len(colours)) if s >> i & 1}
        if len(C) == len(colours):
            continue
        cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] in C]
        r0, r1, c0, c1 = _bbox(cells)
        holes, clean = [], True
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                v = g[r][c]
                if v == bg:
                    holes.append((r, c))
                elif v not in C:
                    clean = False
                    break
            if not clean:
                break
        if not clean or not holes:
            continue
        area = sum(cnt[v] for v in colours) - sum(1 for _ in cells)
        if area != len(holes):
            continue
        inside = lambda r, c: r0 <= r <= r1 and c0 <= c <= c1
        pieces = _comps(g, bg, conn, split == "mono", skip=inside)
        if not pieces or len(pieces) > MAXP:
            continue
        fill = _tile(holes, pieces, motion, budget)
        if budget[0] < 0:
            return None
        if fill is None:
            continue
        if frame == "crop":
            return [[fill.get((r, c), g[r][c]) for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        out = [[g[r][c] if inside(r, c) else bg for c in range(W)] for r in range(H)]
        for (r, c), v in fill.items():
            out[r][c] = v
        return out
    return None


# ------------------------------------------------------------------ criterion: pocket (piece fills a notch)
def _pocket(g, sel, motion, result, pcol=None, newcol=None):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    comps = _comps(g, bg, 4, False)
    if sel == "multi":
        pieces = [p for p in comps if len(set(p.values())) >= 2]
    else:
        pieces = [p for p in comps if set(p.values()) == {pcol}]
    if len(pieces) > MAXP:
        return None
    if not pieces:
        return [row[:] for row in g]
    board = [row[:] for row in g]
    for p in pieces:
        for (r, c) in p:
            board[r][c] = bg
    bodies = []      # (box, pocket_of: cell -> id, pockets: list of (cells, sides))
    bycol = {}
    for r in range(H):
        for c in range(W):
            if board[r][c] != bg:
                bycol.setdefault(board[r][c], []).append((r, c))
    for col in sorted(bycol):
        r0, r1, c0, c1 = box = _bbox(bycol[col])
        gaps = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if board[r][c] == bg]
        pk = []
        pof = {}
        for comp in _cc(gaps):
            sides = set()
            for r, c in comp:
                if r == r0: sides.add("t")
                if r == r1: sides.add("b")
                if c == c0: sides.add("l")
                if c == c1: sides.add("r")
            for q in comp:
                pof[q] = len(pk)
            pk.append((comp, sides))
        if pk:
            bodies.append((box, pof, pk))
    if not bodies:
        return None
    cands = []
    for p in pieces:
        pr0, pr1, pc0, pc1 = _bbox(p)
        orients = _orients(p, motion)
        cl = []
        seen = set()
        for bi, (box, pof, pk) in enumerate(bodies):
            r0, r1, c0, c1 = box
            facing = set()          # sides of the body box beyond which the piece's centre lies
            if pr0 + pr1 < 2 * r0: facing.add("t")
            if pr0 + pr1 > 2 * r1: facing.add("b")
            if pc0 + pc1 < 2 * c0: facing.add("l")
            if pc0 + pc1 > 2 * c1: facing.add("r")
            if not facing:
                continue
            for pi, (pcells, sides) in enumerate(pk):
                if not (sides & facing):
                    continue
                ar, ac = min(pcells)
                for o in orients:
                    for (sr, sc), _ in o:
                        dr, dc = ar - sr, ac - sc
                        placed = {}
                        hit = Counter()
                        ok = True
                        for (r, c), v in o:
                            y, x = r + dr, c + dc
                            if not (0 <= y < H and 0 <= x < W) or board[y][x] != bg:
                                ok = False
                                break
                            if r0 <= y <= r1 and c0 <= x <= c1:
                                k = pof.get((y, x))
                                if k is None:
                                    ok = False
                                    break
                                hit[k] += 1
                            placed[(y, x)] = v
                        if not ok or not hit:
                            continue
                        if any(n != len(pk[k][0]) or not (pk[k][1] & facing) for k, n in hit.items()):
                            continue
                        key = tuple(sorted(placed.items()))
                        if key in seen:
                            continue
                        seen.add(key)
                        cl.append((frozenset((bi, k) for k in hit), placed))
        cands.append(cl)
    out = [row[:] for row in g]
    if result == "recolour":
        for p, cl in zip(pieces, cands):
            if cl:
                for (r, c) in p:
                    out[r][c] = newcol
        return out
    order = sorted(range(len(pieces)), key=lambda i: len(cands[i]))
    choice = {}
    budget = [20000]

    def solve(k, used_pk, used_cells):
        if k == len(order):
            return True
        budget[0] -= 1
        if budget[0] < 0:
            return False
        i = order[k]
        if not cands[i]:
            choice[i] = None
            return solve(k + 1, used_pk, used_cells)
        for pks, placed in cands[i]:
            if pks & used_pk or any(q in used_cells for q in placed):
                continue
            choice[i] = placed
            if solve(k + 1, used_pk | pks, used_cells | set(placed)):
                return True
        return False

    if not solve(0, frozenset(), frozenset()):
        return None
    out = [row[:] for row in board]
    for i, p in enumerate(pieces):
        src = p if choice[i] is None else choice[i]
        for (r, c), v in src.items():
            out[r][c] = v
    return out


# ------------------------------------------------------------------ criterion: marker coincidence on a board
def _marker(g, motion):
    bg = _bg(g)
    comps = _comps(g, bg, 4, False)
    if len(comps) < 2 or len(comps) > MAXP:
        return None
    area = lambda p: (lambda b: (b[1] - b[0] + 1) * (b[3] - b[2] + 1))(_bbox(p))
    comps.sort(key=lambda p: (-area(p), -len(p)))
    board = comps[0]
    R0, R1, C0, C1 = _bbox(board)
    BH, BW = R1 - R0 + 1, C1 - C0 + 1
    bc = Counter(board.values())
    main = bc.most_common(1)[0][0]
    keys = set(bc) - {main}
    if not keys:
        return None
    ref = [[g[r][c] for c in range(C0, C1 + 1)] for r in range(R0, R1 + 1)]
    out = [row[:] for row in ref]
    for p in comps[1:]:
        best = None
        for o in _orients(p, motion):
            cells = dict(o)
            mr = min(r for r, _ in cells)
            mc = min(c for _, c in cells)
            cells = {(r - mr, c - mc): v for (r, c), v in cells.items()}
            h = max(r for r, _ in cells) + 1
            w = max(c for _, c in cells) + 1
            if h > BH or w > BW:
                continue
            pk = {q: v for q, v in cells.items() if v in keys}
            if not pk:
                continue
            for oy in range(BH - h + 1):
                for ox in range(BW - w + 1):
                    good = True
                    for y in range(h):
                        row = ref[oy + y]
                        for x in range(w):
                            bv = row[ox + x]
                            pv = pk.get((y, x))
                            if (bv in keys) != (pv is not None) or (pv is not None and pv != bv):
                                good = False
                                break
                        if not good:
                            break
                    if good:
                        best = (oy, ox, cells)
                        break
                if best:
                    break
            if best:
                break
        if best:
            oy, ox, cells = best
            for (y, x), v in cells.items():
                out[oy + y][ox + x] = v
    return out


# ------------------------------------------------------------------ criterion: connector adjacency (assembly)
def _connector(g, conn, paint, frame):
    res = _assemble(tuple(map(tuple, g)), conn)
    if res is None:
        return None
    bg, H, W, pieces, info, marks_col, shift, occ, axes = res
    occ = dict(occ)
    if paint == "body":
        for i, s in shift.items():
            body = info[i][4]
            for (r, c), v in pieces[i].items():
                if v in marks_col:
                    occ[(r + s[0], c + s[1])] = body
    rs = [r for r, _ in occ]
    cs = [c for _, c in occ]
    R0, R1, C0, C1 = min(rs), max(rs), min(cs), max(cs)
    if frame == "strip":
        if axes == {"h"}:
            if R0 < 0 or R1 >= H:
                return None
            R0, R1 = 0, H - 1
        elif axes == {"v"}:
            if C0 < 0 or C1 >= W:
                return None
            C0, C1 = 0, W - 1
        else:
            return None
    out = [[bg] * (C1 - C0 + 1) for _ in range(R1 - R0 + 1)]
    for (r, c), v in occ.items():
        out[r - R0][c - C0] = v
    return out


@lru_cache(maxsize=64)
def _assemble(g, conn):
    """Dock pieces by same-colour markers on facing edges, nearest pair first; shared by paint/frame."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    pieces = _comps(g, bg, conn, False)
    if len(pieces) < 2 or len(pieces) > MAXP:
        return None
    # marker colours: colours that occur only as isolated cells and in at least two pieces (a partner exists)
    singles = {}
    holders = Counter()
    for p in pieces:
        for v in set(p.values()):
            holders[v] += 1
        for (r, c), v in p.items():
            iso = all(g[r + dy][c + dx] != v for dy, dx in N4 if 0 <= r + dy < H and 0 <= c + dx < W)
            singles[v] = singles.get(v, True) and iso
    marks_col = {v for v, s in singles.items() if s and holders[v] >= 2}
    if not marks_col:
        return None
    pieces = [p for p in pieces if any(v not in marks_col for v in p.values())]
    if len(pieces) < 2:
        return None
    info = []
    marks = []
    for i, p in enumerate(pieces):
        r0, r1, c0, c1 = _bbox(p)
        body = Counter(v for v in p.values() if v not in marks_col).most_common(1)[0][0]
        info.append((r0, r1, c0, c1, body))
        for (r, c), v in p.items():
            if v in marks_col:
                ds = []
                if r == r0: ds.append((-1, 0))
                if r == r1: ds.append((1, 0))
                if c == c0: ds.append((0, -1))
                if c == c1: ds.append((0, 1))
                marks.append((i, (r, c), v, ds))
    if len(marks) > 2 * MAXP:
        return None
    start = min(range(len(pieces)), key=lambda i: (-len(pieces[i]), info[i][2], info[i][0]))
    shift = {start: (0, 0)}
    occ = dict(pieces[start])
    used = set()
    axes = set()
    while True:
        cand = []
        for mi, (i, ci, col, di) in enumerate(marks):
            if i not in shift or mi in used:
                continue
            for mj, (j, cj, colj, dj) in enumerate(marks):
                if j in shift or mj in used or colj != col:
                    continue
                disp = (cj[0] - ci[0], cj[1] - ci[1])
                dist = abs(disp[0]) + abs(disp[1])
                for d in di:
                    if (-d[0], -d[1]) in dj:     # facing edges; prefer the side the partner lies on
                        cand.append((dist, -(d[0] * disp[0] + d[1] * disp[1]), mi, mj, d))
        if not cand:
            break
        cand.sort()
        placed = False
        for _, _, mi, mj, d in cand:
            i, ci = marks[mi][0], marks[mi][1]
            j, cj = marks[mj][0], marks[mj][1]
            si = shift[i]
            tgt = (ci[0] + si[0] + d[0], ci[1] + si[1] + d[1])
            sj = (tgt[0] - cj[0], tgt[1] - cj[1])
            if any((r + sj[0], c + sj[1]) in occ for (r, c) in pieces[j]):
                continue
            shift[j] = sj
            for (r, c), v in pieces[j].items():
                occ[(r + sj[0], c + sj[1])] = v
            used.add(mi)
            used.add(mj)
            axes.add("h" if d[0] == 0 else "v")
            placed = True
            break
        if not placed:
            break
    if len(shift) != len(pieces):
        return None
    return bg, H, W, pieces, info, marks_col, shift, occ, axes


# ------------------------------------------------------------------ criterion: equal label (hole count)
def _holes(g, bg, cells, nb):
    r0, r1, c0, c1 = _bbox(cells)
    return len(_cc([(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if g[r][c] == bg], nb))


def _label(g, conn):
    """Board = the region of most colours; slots = its single-colour parts; each loose piece docks centred
    into the slot whose label (number of background holes) equals its own; its holes show the slot colour."""
    bg = _bg(g)
    nb = N8 if conn == 8 else N4
    regions = _comps(g, bg, 4, False)
    if len(regions) < 2 or len(regions) > MAXP:
        return None
    bi = max(range(len(regions)), key=lambda i: (len(set(regions[i].values())), len(regions[i]), -i))
    board = regions[bi]
    pieces = [p for i, p in enumerate(regions) if i != bi]
    slots = []
    for col in sorted(set(board.values())):
        slots += [(col, comp) for comp in _cc([q for q, v in board.items() if v == col])]
    if len(slots) != len(pieces):
        return None
    lab = {}
    for p in pieces:
        k = _holes(g, bg, list(p), nb)
        if k in lab:
            return None
        lab[k] = _bbox(list(p))
    R0, R1, C0, C1 = _bbox(list(board))
    out = [row[C0:C1 + 1] for row in g[R0:R1 + 1]]
    used = set()
    for col, comp in slots:
        k = _holes(g, bg, comp, nb)
        if k not in lab or k in used:
            return None
        used.add(k)
        pr0, pr1, pc0, pc1 = _bbox(comp)
        tr0, tr1, tc0, tc1 = lab[k]
        ph, pw, th, tw = pr1 - pr0 + 1, pc1 - pc0 + 1, tr1 - tr0 + 1, tc1 - tc0 + 1
        if th > ph or tw > pw:
            return None
        for r in range(pr0, pr1 + 1):
            for c in range(pc0, pc1 + 1):
                out[r - R0][c - C0] = col
        orow, ocol = pr0 + (ph - th) // 2 - R0, pc0 + (pw - tw) // 2 - C0
        for dr in range(th):
            for dc in range(tw):
                v = g[tr0 + dr][tc0 + dc]
                out[orow + dr][ocol + dc] = col if v == bg else v
    return out


# ------------------------------------------------------------------ fitting
def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def _recolour_pair(train):
    pairs = set()
    for p in train:
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    pairs.add((a, b))
    return pairs.pop() if len(pairs) == 1 else None


def fam(train, max_out=3):
    if not train:
        return
    same = all(len(p["input"]) == len(p["output"]) and len(p["input"][0]) == len(p["output"][0]) for p in train)
    smaller = all(len(p["output"]) * len(p["output"][0]) < len(p["input"]) * len(p["input"][0]) for p in train)
    if same and all(p["input"] == p["output"] for p in train):
        return
    progs = []
    if same:
        rc = _recolour_pair(train)
        if rc is not None:
            for motion in ("rotate", "dihedral"):
                progs.append(("dock:pocket[pieces=colour,motion=%s,result=recolour]" % motion, 2.0,
                              lambda g, m=motion, a=rc[0], b=rc[1]: _pocket(g, "colour", m, "recolour", a, b)))
        for motion in ("translate", "rotate", "dihedral", "dihedral-swap"):
            progs.append(("dock:pocket[pieces=multi,motion=%s,result=move]" % motion, 2.0 + 0.1 * MOTIONS[motion],
                          lambda g, m=motion: _pocket(g, "multi", m, "move")))
        for motion in ("translate", "dihedral"):
            for conn in (4, 8):
                progs.append(("dock:cover[conn=%d,split=mono,motion=%s,frame=inplace]" % (conn, motion), 3.0,
                              lambda g, cn=conn, m=motion: _cover(g, cn, "mono", m, "inplace")))
    if smaller:
        for motion in ("translate", "rotate", "dihedral"):
            for split in ("multi", "mono"):
                for conn in (4, 8):
                    progs.append(("dock:cover[conn=%d,split=%s,motion=%s,frame=crop]" % (conn, split, motion),
                                  1.0 + 0.1 * MOTIONS[motion] + 0.05 * (conn == 8) + 0.05 * (split == "mono"),
                                  lambda g, cn=conn, sp=split, m=motion: _cover(g, cn, sp, m, "crop")))
        for motion in ("translate", "dihedral"):
            progs.append(("dock:marker[motion=%s,result=crop]" % motion, 1.5 + 0.1 * MOTIONS[motion],
                          lambda g, m=motion: _marker(g, m)))
        for conn in (4, 8):
            progs.append(("dock:label[holes=conn%d,result=crop]" % conn, 2.2 + 0.05 * (conn == 8),
                          lambda g, cn=conn: _label(g, cn)))
        for frame in ("crop", "strip"):
            for paint in ("keep", "body"):
                for conn in (4, 8):
                    progs.append(("dock:connector[conn=%d,paint=%s,frame=%s]" % (conn, paint, frame),
                                  1.8 + 0.1 * (paint == "body") + 0.1 * (frame == "strip") + 0.05 * (conn == 8),
                                  lambda g, cn=conn, pt=paint, fr=frame: _connector(g, cn, pt, fr)))
    progs.sort(key=lambda t: t[1])
    n = 0
    for name, cost, fn in progs:
        if _fits(fn, train):
            yield (name, cost, fn)
            n += 1
            if n >= max_out:
                return


FAMILIES = [fam]
