"""Family for ARC task 4c416de3 -- concept: MIRROR STAMP (graphics: a sprite/rubber stamp re-applied with reflection).

Reading of the task
-------------------
The grid holds rectangular frames (outlines in the frame colour, possibly clipped by the grid border) on a background.
One frame corner already carries a decoration (the exemplar "stamp"): a single-colour shape that sits on/over the
corner and reaches outside the frame.  Other corners carry only an ink dot: one cell of some colour on the corner's
inward diagonal.  Each dotted corner receives the exemplar stamp, mirrored so that it fits that corner's orientation,
inked in the dot's colour.  Nothing else changes.

How the pieces are found (no task constants):
  * background = most frequent colour; frame colour = second most frequent colour (roles, per grid).
  * corner     = cell c with inward orientation (si, sj) whose two inward arms c+k(si,0), c+k(0,sj), k=1..arm, are frame
                 or ink cells (each arm containing frame), the corner cell itself frame or ink, the two outward
                 neighbours not frame and the inward diagonal neighbour not frame (so decorated corners still count).
  * ink blobs  = 8-connected single-colour components of non-background, non-frame cells; a blob belongs to the corner
                 whose inward diagonal ray (starting one cell outside the corner) meets it first.
  * exemplar   = a corner's blob that has a cell on or outside the frame lines; its cells in the corner's local,
                 orientation-normalised coordinates form the stamp.
  * target     = a corner's blob lying strictly inside the frame; the nearest exemplar's stamp is painted there.

Parameters (finite declared domains, induced from train; every fitting combination is yielded):
  mode in ('mirror', 'rotate')   how the stamp is re-oriented between corners (axis reflection vs 90-degree turns).
  arm  in (2, 3)                 cells of each frame arm that must be present to recognise a corner.
"""

from collections import Counter

DIAG = ((1, 1), (1, -1), (-1, -1), (-1, 1))  # inward orientations, clockwise from top-left corner


def _roles(g):
    cnt = Counter(v for row in g for v in row).most_common()
    bg = cnt[0][0]
    fr = cnt[1][0] if len(cnt) > 1 else None
    return bg, fr


def _corners(g, fr, bg, arm):
    H, W = len(g), len(g[0])
    at = lambda r, c: g[r][c] if 0 <= r < H and 0 <= c < W else None
    solid = lambda v: v is not None and v != bg          # frame or ink
    out = []
    for r in range(H):
        for c in range(W):
            if not solid(g[r][c]):
                continue
            for si, sj in DIAG:
                a1 = [at(r + k * si, c) for k in range(1, arm + 1)]
                a2 = [at(r, c + k * sj) for k in range(1, arm + 1)]
                if not all(solid(v) for v in a1 + a2):
                    continue
                if fr not in a1 or fr not in a2:
                    continue
                if at(r - si, c) == fr or at(r, c - sj) == fr or at(r + si, c + sj) == fr:
                    continue
                out.append((r, c, si, sj))
    return out


def _blobs(g, fr, bg):
    H, W = len(g), len(g[0])
    lab, blobs = {}, []
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v in (bg, fr) or (r, c) in lab:
                continue
            idx, stack, cells = len(blobs), [(r, c)], []
            lab[(r, c)] = idx
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in lab and g[ny][nx] == v:
                            lab[(ny, nx)] = idx
                            stack.append((ny, nx))
            blobs.append((v, cells))
    return lab, blobs


def _local(cell, corner):
    r, c, si, sj = corner
    return ((cell[0] - r) * si, (cell[1] - c) * sj)


def _reorient(uv, src, dst, mode):
    """Map local coords of a stamp read at corner orientation src to corner orientation dst."""
    if mode == 'rotate':
        q = (DIAG.index(dst) - DIAG.index(src)) % 4
        return (uv[1], uv[0]) if q % 2 else uv
    return uv  # mirror: local coords are already reflection-normalised


def _apply(g, mode, arm):
    bg, fr = _roles(g)
    if fr is None:
        return [row[:] for row in g]
    H, W = len(g), len(g[0])
    corners = _corners(g, fr, bg, arm)
    lab, blobs = _blobs(g, fr, bg)
    # assign each blob to the corner whose inward diagonal meets it first
    best = {}
    for ci, (r, c, si, sj) in enumerate(corners):
        k = -1
        while True:
            y, x = r + k * si, c + k * sj
            if not (0 <= y < H and 0 <= x < W):
                break
            if (y, x) in lab:
                b = lab[(y, x)]
                if b not in best or k < best[b][0]:
                    best[b] = (k, ci)
                break
            if k >= 1 and g[y][x] == fr:
                break
            k += 1
    exemplars, targets = [], []
    for b, (k, ci) in best.items():
        col, cells = blobs[b]
        loc = [_local(p, corners[ci]) for p in cells]
        if any(u <= 0 or v <= 0 for u, v in loc):
            exemplars.append((ci, loc))
        else:
            targets.append((ci, col))
    out = [row[:] for row in g]
    if not exemplars:
        return out
    for ci, col in targets:
        r, c, si, sj = corners[ci]
        eci, loc = min(exemplars, key=lambda e: (abs(corners[e[0]][0] - r) + abs(corners[e[0]][1] - c), e[0]))
        src = corners[eci][2:]
        for uv in loc:
            u, v = _reorient(uv, src, (si, sj), mode)
            y, x = r + u * si, c + v * sj
            if 0 <= y < H and 0 <= x < W:
                out[y][x] = col
    return out


def fam_mirror_stamp(train):
    for mode in ('mirror', 'rotate'):
        for arm in (2, 3):
            fn = (lambda m, a: (lambda g: _apply(g, m, a)))(mode, arm)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("graphics:mirror_stamp[mode=%s,arm=%d]" % (mode, arm), 3, fn)
                break


FAMILIES = (fam_mirror_stamp,)
