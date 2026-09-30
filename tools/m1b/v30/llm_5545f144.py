"""Family for ARC task 5545f144 -- concept: WAYPOINT FOLLOWING (robotics / navigation).

Picture: a small mirror-symmetric vehicle (an arrow, a T, a fork ...) drives across the board.  Its
nose is the single pixel at the narrow end of its mirror axis.  The loose single dots are waypoints.
The vehicle drives in straight rook moves: from where its nose stands it goes to the nearest unvisited
waypoint in line with it (same row or column), turns to face the direction it drove, parks its nose on
that waypoint (the waypoint is consumed) and repeats until no waypoint is in line.  The input is a film
strip of key frames of this trip (panels split by full separator lines, or a single frame); the output
is the final frame: the vehicle at its last waypoint, facing its last direction of travel, plus any
waypoints it never reached.

Everything is induced from the training pairs / the grid itself:
  background   = most common colour of a panel
  separators   = full rows / columns of one non-background colour (none -> the grid is one frame)
  vehicle      = the largest 8-connected non-background component of a frame; waypoints = the rest
  nose/facing  = the unique pixel that alone is extreme in some direction d while the vehicle is
                 mirror symmetric about the line through it parallel to d
Declared finite parameter domains, chosen by fitting the training pairs:
  start  in {"first", "last"}           -- which key frame of the strip the trip is replayed from
  tie    in {"straight", "nearest"}     -- preference when several waypoints are in line
"""
from collections import Counter

DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))  # up, right, down, left (clockwise order)


def most_common(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def split_frames(g):
    """Split a grid into panels at full uniform lines whose colour differs from the background."""
    H, W = len(g), len(g[0])
    bg = most_common(g)
    rows = [r for r in range(H) if len(set(g[r])) == 1 and g[r][0] != bg]
    cols = [c for c in range(W) if len({g[r][c] for r in range(H)}) == 1 and g[0][c] != bg]
    rb = [-1] + rows + [H]
    cb = [-1] + cols + [W]
    frames = []
    for a, b in zip(rb, rb[1:]):
        for c0, c1 in zip(cb, cb[1:]):
            if b - a > 1 and c1 - c0 > 1:
                frames.append([row[c0 + 1:c1] for row in g[a + 1:b]])
    return frames


def components(cells):
    cells = set(cells)
    comps = []
    while cells:
        s = cells.pop()
        comp, stack = [s], [s]
        while stack:
            r, c = stack.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    n = (r + dr, c + dc)
                    if n in cells:
                        cells.remove(n)
                        comp.append(n)
                        stack.append(n)
        comps.append(comp)
    return comps


def nose_of(body):
    """Return (nose, facing) of a mirror-symmetric vehicle, or None if not unique."""
    S = set(body)
    found = []
    for d in DIRS:
        key = lambda p: p[0] * d[0] + p[1] * d[1]
        m = max(key(p) for p in body)
        ext = [p for p in body if key(p) == m]
        if len(ext) != 1:
            continue
        nr, nc = ext[0]
        if d[0] == 0:   # horizontal axis: mirror across row nr
            sym = all((2 * nr - r, c) in S for r, c in S)
        else:           # vertical axis: mirror across column nc
            sym = all((r, 2 * nc - c) in S for r, c in S)
        if sym:
            found.append((ext[0], d))
    return found[0] if len(found) == 1 else None


def _peel_noses(body):
    """Yield (p, nose_of(body minus p)) for every p in body order where that nose is not None.

    Exactly equivalent to calling nose_of on each one-pixel-removed body, but incremental:
    per direction the extreme of the reduced body is read off the top-two key levels of the
    full body, and mirror symmetry of the reduced body follows from the (cached) set of
    asymmetric pixels of the full body about the same axis."""
    S = set(body)
    info = []
    for d in DIRS:
        levels = {}
        for p in body:
            levels.setdefault(p[0] * d[0] + p[1] * d[1], []).append(p)
        ks = sorted(levels, reverse=True)
        m = ks[0]
        info.append((d, m, levels[m], levels[ks[1]] if len(ks) > 1 else []))
    asym = {}

    def asym_of(horiz, a):
        key = (horiz, a)
        if key not in asym:
            if horiz:
                asym[key] = [q for q in body if (2 * a - q[0], q[1]) not in S][:2]
            else:
                asym[key] = [q for q in body if (q[0], 2 * a - q[1]) not in S][:2]
        return asym[key]

    for p in body:
        found = []
        for d, m, top, second in info:
            k = p[0] * d[0] + p[1] * d[1]
            if k == m:
                if len(top) == 1:
                    e = second[0] if len(second) == 1 else None
                elif len(top) == 2:
                    e = top[1] if top[0] == p else top[0]
                else:
                    e = None
            else:
                e = top[0] if len(top) == 1 else None
            if e is None:
                continue
            horiz = d[0] == 0
            a = e[0] if horiz else e[1]
            A = asym_of(horiz, a)
            if len(A) > 1 or (A and A[0] != p):
                continue
            mp = (2 * a - p[0], p[1]) if horiz else (p[0], 2 * a - p[1])
            if mp in S and mp != p:
                continue
            found.append((e, d))
        if len(found) == 1:
            yield p, found[0]


def read_frame(f):
    bg = most_common(f)
    cells = [(r, c) for r in range(len(f)) for c in range(len(f[0])) if f[r][c] != bg]
    if not cells:
        return None
    comps = sorted(components(cells), key=len, reverse=True)
    if len(comps[0]) < 2 or (len(comps) > 1 and len(comps[1]) == len(comps[0])):
        return None
    body = comps[0]
    nd = nose_of(body)
    if nd is None:
        # a waypoint may touch the vehicle diagonally: peel off one pixel so the rest stays a
        # connected mirror-symmetric vehicle (must be unambiguous)
        opts = []
        for p, ndp in _peel_noses(body):
            rest = [q for q in body if q != p]
            if len(components(rest)) == 1:
                opts.append((p, rest, ndp))
                if len(opts) > 1:
                    return None
        if len(opts) != 1:
            return None
        p, body, nd = opts[0]
        comps = [body, [p]] + comps[1:]
    nose, facing = nd
    colour = f[nose[0]][nose[1]]
    shape = [(r - nose[0], c - nose[1], f[r][c]) for r, c in body]   # offsets from nose
    waypoints = {p: f[p[0]][p[1]] for comp in comps[1:] for p in comp}
    return dict(bg=bg, H=len(f), W=len(f[0]), shape=shape, facing=facing, nose=nose,
                waypoints=waypoints, colour=colour)


def rotate(off, k):
    r, c = off
    for _ in range(k % 4):
        r, c = c, -r
    return r, c


def drive(st, tie, H, W):
    """Replay the trip; returns (nose, facing, remaining waypoints)."""
    pos, facing = st["nose"], st["facing"]
    left = dict(st["waypoints"])
    for _ in range(len(left) + 1):
        cands = []
        for d in DIRS:
            r, c, k = pos[0] + d[0], pos[1] + d[1], 1
            while 0 <= r < H and 0 <= c < W:
                if (r, c) in left:
                    cands.append((k, d, (r, c)))
                    break
                r, c, k = r + d[0], c + d[1], k + 1
        if not cands:
            break
        if tie == "straight":
            cands.sort(key=lambda t: (t[1] != facing, t[0], DIRS.index(t[1])))
        else:
            cands.sort(key=lambda t: (t[0], t[1] != facing, DIRS.index(t[1])))
        _, d, p = cands[0]
        del left[p]
        pos, facing = p, d
    return pos, facing, left


def render(st, pos, facing, left):
    H, W = st["H"], st["W"]
    out = [[st["bg"]] * W for _ in range(H)]
    for (r, c), v in left.items():
        out[r][c] = v
    k = (DIRS.index(facing) - DIRS.index(st["facing"])) % 4
    for dr, dc, v in st["shape"]:
        rr, cc = rotate((dr, dc), k)
        r, c = pos[0] + rr, pos[1] + cc
        if 0 <= r < H and 0 <= c < W:
            out[r][c] = v
    return out


def make(start, tie):
    def fn(g):
        frames = split_frames(g)
        if not frames:
            return None
        f = frames[-1] if start == "last" else frames[0]
        st = read_frame(f)
        if st is None:
            return None
        pos, facing, left = drive(st, tie, st["H"], st["W"])
        return render(st, pos, facing, left)
    return fn


def fam_waypoint_following(train):
    for start in ("first", "last"):
        for tie in ("straight", "nearest"):
            fn = make(start, tie)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("robotics:waypoint_following[start=%s,tie=%s]" % (start, tie), 3, fn)
                return


FAMILIES = (fam_waypoint_following,)
