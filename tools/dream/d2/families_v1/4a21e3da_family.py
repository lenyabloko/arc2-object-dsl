"""Family for 4a21e3da -- graphics / technical drawing: EXPLODED VIEW (sectioned by cutting-plane lines).

Concept: every marker pixel on the grid border is the end-mark of a cutting-plane line (as in a drafting
section view).  The cutting plane runs perpendicular to the marker's edge, across the object, and is drawn in
the marker colour from the marker up to the last object pixel it meets; object pixels lying on the plane stay
put (the section).  The object is thereby cut into pieces, and the drawing is "exploded": each piece is
translated rigidly away from the cutting plane(s) out to the frame, i.e. to the frame corner of its side
(along an axis with no cutting plane it slides towards the marker edge).  With two perpendicular planes the
piece whose corner touches no marker edge is the cut-away quarter of a classic sectional view and is removed.

Roles (no colour numbers): background = most frequent colour; marker colour(s) = non-background colours whose
pixels all lie on the border (not at a corner); object = every other non-background pixel.
Declared finite parameter domains, induced from the training pairs:
    extent  in ('object', 'frame')  -- plane line drawn to the far object pixel on it, or to the far frame edge
    cutaway in (True, False)        -- remove the piece whose target corner touches no marker edge
"""
from collections import Counter

EXTENTS = ('object', 'frame')
CUTAWAYS = (True, False)


def _explode(g, extent, cutaway):
    H, W = len(g), len(g[0])
    cnt = Counter(v for row in g for v in row)
    bg = cnt.most_common(1)[0][0]
    on_border = lambda r, c: r in (0, H - 1) or c in (0, W - 1)
    cells = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                cells.setdefault(g[r][c], []).append((r, c))
    marker_cols = {k for k, ps in cells.items() if all(on_border(r, c) for r, c in ps)}
    obj = {(r, c) for k, ps in cells.items() if k not in marker_cols for r, c in ps}
    if not obj or not marker_cols:
        return None
    beams = []  # (axis, index, source edge, marker (r,c))
    for k in marker_cols:
        for r, c in cells[k]:
            edges = [e for e, t in (('top', r == 0), ('bottom', r == H - 1), ('left', c == 0), ('right', c == W - 1)) if t]
            if len(edges) != 1:
                return None  # corner marker: plane orientation undefined
            e = edges[0]
            beams.append(('v', c, e, (r, c)) if e in ('top', 'bottom') else ('h', r, e, (r, c)))
    vs = [b for b in beams if b[0] == 'v']
    hs = [b for b in beams if b[0] == 'h']
    if len(vs) > 1 or len(hs) > 1:
        return None
    out = [[bg] * W for _ in range(H)]
    sources = {b[2] for b in beams}
    # 1. cutting-plane lines (object pixels on the plane stay, background on the plane takes the marker colour)
    on_plane = set()
    for axis, idx, edge, (mr, mc) in beams:
        line = [(r, idx) for r in range(H)] if axis == 'v' else [(idx, c) for c in range(W)]
        if edge in ('bottom', 'right'):
            line = line[::-1]
        hit = [i for i, p in enumerate(line) if p in obj]
        stop = (hit[-1] if hit else -1) if extent == 'object' else len(line) - 1
        for i, (r, c) in enumerate(line):
            if (r, c) in obj:
                on_plane.add((r, c))
                out[r][c] = g[r][c]
            elif i <= stop:
                out[r][c] = g[mr][mc]
        out[mr][mc] = g[mr][mc]
    # 2. pieces: object pixels off the planes, grouped by side of each plane
    pieces = {}
    for (r, c) in obj - on_plane:
        sx = (-1 if c < vs[0][1] else 1) if vs else (-1 if hs[0][2] == 'left' else 1)
        sy = (-1 if r < hs[0][1] else 1) if hs else (-1 if vs[0][2] == 'top' else 1)
        pieces.setdefault((sy, sx), []).append((r, c))
    # 3. explode each piece rigidly to the frame corner on its side
    for (sy, sx), ps in pieces.items():
        touches = {'top' if sy < 0 else 'bottom', 'left' if sx < 0 else 'right'}
        if cutaway and not (touches & sources):
            continue
        r0, r1 = min(r for r, _ in ps), max(r for r, _ in ps)
        c0, c1 = min(c for _, c in ps), max(c for _, c in ps)
        dr = -r0 if sy < 0 else H - 1 - r1
        dc = -c0 if sx < 0 else W - 1 - c1
        for r, c in ps:
            out[r + dr][c + dc] = g[r][c]
    return out


def fam_exploded_view(train):
    for extent in EXTENTS:
        for cutaway in CUTAWAYS:
            fn = (lambda e, k: (lambda g: _explode(g, e, k)))(extent, cutaway)
            try:
                ok = all(fn(p['input']) == p['output'] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ('drafting:exploded_view[extent=%s,cutaway=%s]' % (extent, cutaway), 3, fn)
                return


FAMILIES = (fam_exploded_view,)
