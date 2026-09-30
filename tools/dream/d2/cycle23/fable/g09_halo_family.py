"""g09_halo family -- concept: BALLOON INFLATION (mechanics / lattice geometry).

Mechanism.  Every object (4-connected component of the object colour) anchors a balloon: a lattice-norm
ball concentric with the object's bounding box (L1 norm -> diamond, Linf norm -> square).  The balloon
inflates from the centre until one of three stop rules fires:
    ('w', k)  : it is k cells wider than the object on every side          (classic halo of width k)
    ('q', q)  : its diameter reaches q times the object's own norm-diameter (size-proportional halo;
                q=1 is the object's circumball, e.g. the diamond whose diagonal is a segment)
    ('obs',)  : it first touches an obstacle = any other non-background cell (contact stop)
Background cells inside the balloon are painted with the halo colour (induced); object and obstacle cells
are never overwritten; the balloon is clipped by the grid edge.  An object cut by the picture frame is
presumed to continue beyond it as a square (only when the task's objects are square).

Optional second layer (used only when the balloons alone leave output cells unexplained): each object also
casts a SHADOW of its own width in one of the four axis directions to the grid edge, in the second induced
colour, painted beneath the balloons.  (Needed by db93a21d; c97c0139 and ff72ca3e are pure balloons.)

Induced per task (all from finite domains):  background = most common input colour; object colour = a
non-background colour present in every input; norm in {Linf, L1}; stop rule in {w1,w2,w3,q1,q2,q3,obs};
frame completion in {on, off}; halo colour = the colour painted on former background cells;
shadow in {none} u {S,N,E,W} x {second new colour}.
"""
from collections import Counter

RULES = (('w', 1), ('w', 2), ('w', 3), ('q', 2), ('q', 3), ('q', 1), ('obs', 0))
NORMS = ('Linf', 'L1')
DIRS = ('S', 'N', 'E', 'W')


def _bg(grids):
    cnt = Counter()
    for g in grids:
        for row in g:
            cnt.update(row)
    return cnt.most_common(1)[0][0]


def _components(g, colour):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == colour and not seen[r][c]:
                seen[r][c] = True
                stack = [(r, c)]
                cells = []
                while stack:
                    y, x = stack.pop()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == colour:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                comps.append(cells)
    return comps


def _boxes(g, colour, complete):
    """(cells, r1, r2, c1, c2, extended) per object.  With `complete`, an object cut by the picture frame
    (touching an edge, bbox not square) is presumed to continue beyond the frame as a square."""
    H, W = len(g), len(g[0])
    res = []
    for cells in _components(g, colour):
        r1 = min(r for r, _ in cells); r2 = max(r for r, _ in cells)
        c1 = min(c for _, c in cells); c2 = max(c for _, c in cells)
        ext = False
        if complete:
            h, w = r2 - r1 + 1, c2 - c1 + 1
            if h < w:
                if r1 == 0 and r2 != H - 1:
                    r1, ext = r2 - (w - 1), True
                elif r2 == H - 1 and r1 != 0:
                    r2, ext = r1 + (w - 1), True
            elif w < h:
                if c1 == 0 and c2 != W - 1:
                    c1, ext = c2 - (h - 1), True
                elif c2 == W - 1 and c1 != 0:
                    c2, ext = c1 + (h - 1), True
        res.append((cells, r1, r2, c1, c2, ext))
    return res


def _square_objects(grids, colour):
    """Evidence for frame completion: every object clear of the frame has a square bounding box."""
    n = 0
    for g in grids:
        H, W = len(g), len(g[0])
        for cells, r1, r2, c1, c2, _ in _boxes(g, colour, False):
            if r1 == 0 or c1 == 0 or r2 == H - 1 or c2 == W - 1:
                continue
            if r2 - r1 != c2 - c1:
                return False
            n += 1
    return n > 0


def _d2(norm, r, c, cr2, cc2):
    """Distance from cell (r,c) to the (possibly half-integer) centre, in doubled units."""
    dr = abs(2 * r - cr2)
    dc = abs(2 * c - cc2)
    return dr + dc if norm == 'L1' else max(dr, dc)


def _balloon_mask(g, bg, obj, norm, rule, complete):
    """Set of background cells covered by the balloons of every object of colour obj."""
    H, W = len(g), len(g[0])
    boxes = _boxes(g, obj, complete)
    mask = set()
    if not boxes:
        return mask
    nonbg = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    kind, val = rule
    for cells, r1, r2, c1, c2, ext in boxes:
        cr2, cc2 = r1 + r2, c1 + c2
        if ext:                                                     # completed square / diamond
            R2 = max(r2 - r1, c2 - c1)
        else:
            R2 = max(_d2(norm, r, c, cr2, cc2) for r, c in cells)  # object's own norm-radius (doubled)
        strict = False
        if kind == 'w':
            lim = R2 + 2 * val
        elif kind == 'q':
            lim = val * R2 + (val - 1)                               # diameter = val * object diameter
        else:
            cellset = set(cells)
            ds = [_d2(norm, r, c, cr2, cc2) for r, c in nonbg if (r, c) not in cellset]
            if not ds:
                lim = 4 * (H + W)                                   # nothing to touch: fills the grid
            else:
                lim = min(ds)
                strict = True
        half = lim // 2 + 1
        for r in range(max(0, r1 - half), min(H, r2 + half + 1)):
            for c in range(max(0, c1 - half), min(W, c2 + half + 1)):
                if g[r][c] != bg:
                    continue
                d = _d2(norm, r, c, cr2, cc2)
                if (d < lim) if strict else (d <= lim):
                    mask.add((r, c))
    return mask


def _shadow_mask(g, bg, obj, sdir, complete):
    H, W = len(g), len(g[0])
    mask = set()
    for cells, r1, r2, c1, c2, _ in _boxes(g, obj, complete):
        r1, r2, c1, c2 = max(r1, 0), min(r2, H - 1), max(c1, 0), min(c2, W - 1)
        if sdir == 'S':
            rows, cols = range(r2 + 1, H), range(c1, c2 + 1)
        elif sdir == 'N':
            rows, cols = range(0, r1), range(c1, c2 + 1)
        elif sdir == 'E':
            rows, cols = range(r1, r2 + 1), range(c2 + 1, W)
        else:
            rows, cols = range(r1, r2 + 1), range(0, c1)
        for r in rows:
            for c in cols:
                if g[r][c] == bg:
                    mask.add((r, c))
    return mask


def _apply(g, bg, obj, norm, rule, complete, hcol, shadow):
    out = [row[:] for row in g]
    if shadow is not None:
        sdir, scol = shadow
        for r, c in _shadow_mask(g, bg, obj, sdir, complete):
            out[r][c] = scol
    for r, c in _balloon_mask(g, bg, obj, norm, rule, complete):
        out[r][c] = hcol
    return out


def fam_balloon(train):
    if not train:
        return
    ins = [p['input'] for p in train]
    outs = [p['output'] for p in train]
    if any(len(i) != len(o) or len(i[0]) != len(o[0]) for i, o in zip(ins, outs)):
        return
    bg = _bg(ins)
    cols = None
    for g in ins:
        s = {v for row in g for v in row if v != bg}
        cols = s if cols is None else cols & s
    if not cols:
        return
    # changed cells per pair; objects/obstacles are never overwritten
    changed = []
    new = set()
    for g, o in zip(ins, outs):
        ch = {}
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] != o[r][c]:
                    if g[r][c] != bg:
                        return
                    ch[(r, c)] = o[r][c]
                    new.add(o[r][c])
        if not ch:
            return
        changed.append(ch)
    if not new or len(new) > 2:
        return
    for obj in sorted(cols):
        # frame completion is presumed when the task's objects are square; it is a no-op on training when no
        # object is cut by the frame, and falls back to the raw boxes if a completed training object misfits
        if _square_objects(ins, obj):
            cut = any(ext for g in ins for *_, ext in _boxes(g, obj, True))
            completes = (True, False) if cut else (True,)
        else:
            completes = (False,)
        for norm, rule, complete in ((n, r, c) for n in NORMS for r in RULES for c in completes):
            masks = [_balloon_mask(g, bg, obj, norm, rule, complete) for g in ins]
            if not any(masks):
                continue
            # every balloon cell must be a changed cell of one common halo colour
            hcols = set()
            ok = True
            for m, ch in zip(masks, changed):
                for cell in m:
                    if cell not in ch:
                        ok = False
                        break
                    hcols.add(ch[cell])
                if not ok or len(hcols) > 1:
                    ok = False
                    break
            if not ok:
                continue
            hcol = next(iter(hcols))
            rest = [set(ch) - m for m, ch in zip(masks, changed)]
            tag = (f'mechanics:balloon[{norm},{rule[0]}{rule[1] if rule[0] != "obs" else ""}'
                   f'{",frame-completed" if complete else ""},obj={obj},halo={hcol}]')
            if not any(rest):
                yield (tag, 3, (lambda g, a=(bg, obj, norm, rule, complete, hcol): _apply(g, *a, None)))
                continue
            if len(new) != 2:
                continue
            scol = next(iter(new - {hcol}))
            if any(ch[cell] != scol for rs, ch in zip(rest, changed) for cell in rs):
                continue
            for sdir in DIRS:
                good = True
                for g, m, rs, ch in zip(ins, masks, rest, changed):
                    sm = _shadow_mask(g, bg, obj, sdir, complete)
                    if (sm - m) != rs:            # shadow (beneath balloons) must explain the rest
                        good = False
                        break
                if good:
                    yield (tag + f'+shadow[{sdir},{scol}]', 3,
                           (lambda g, a=(bg, obj, norm, rule, complete, hcol, (sdir, scol)): _apply(g, *a)))
                    break


FAMILIES = (fam_balloon,)
