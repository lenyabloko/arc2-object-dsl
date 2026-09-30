"""dfadab01 -- cartography: map LEGEND (key) rendering.

A map carries point symbols (single-pixel markers) and, optionally, a legend entry: a drawn sign with its
marker placed diagonally just past the sign's far corner.  Rendering the map = take the legend off the sheet,
wipe every drawn object, and replace each point symbol by its sign (anchored with the marker at the sign's
near corner, clipped at the sheet edge).  Signs for markers with no legend entry on this sheet come from the
standard symbol set learned from the training maps (the "key" is induced, never hard-coded).

Parameters (finite, declared):
  corner  in {(0,0),(0,1),(1,0),(1,1)}  -- which glyph corner the marker occupies (legend marker sits beyond
                                          the opposite corner); covers all rotations / reflections
  size    in legend bbox sizes  U  {(k,k) : k in 2..6}  -- glyph frame for signs read from training outputs
Roles: background = most frequent input colour; marker colours = colours all of whose 8-connected
components are single pixels; everything else is drawn sign material.
"""
from collections import Counter

CORNERS = ((0, 0), (0, 1), (1, 0), (1, 1))
K_DOMAIN = (2, 3, 4, 5, 6)


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg, same_colour):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            if same_colour(g[ny][nx], col):
                                seen[ny][nx] = True
                                stack.append((ny, nx))
            comps.append(cells)
    return comps


def _analyse(g, corner):
    """-> bg, marker colours, list of (marker cell, colour), legends {marker cell: (colour, glyph)}"""
    bg = _bg(g)
    mono = _components(g, bg, lambda a, b: a == b)
    size_by_col = {}
    for comp in mono:
        col = g[comp[0][0]][comp[0][1]]
        size_by_col.setdefault(col, set()).add(len(comp))
    markers_cols = {col for col, s in size_by_col.items() if s == {1}}
    marks = [(comp[0], g[comp[0][0]][comp[0][1]]) for comp in mono
             if g[comp[0][0]][comp[0][1]] in markers_cols]
    # drawn signs: 8-connected blobs of non-marker material
    H, W = len(g), len(g[0])
    mask = [[g[r][c] if g[r][c] not in markers_cols else bg for c in range(W)] for r in range(H)]
    signs = _components(mask, bg, lambda a, b: True)
    dr, dc = corner
    legends = {}
    for cells in signs:
        r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
        c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
        lr = r1 + 1 if dr == 0 else r0 - 1          # beyond the corner opposite to the anchor corner
        lc = c1 + 1 if dc == 0 else c0 - 1
        if 0 <= lr < H and 0 <= lc < W and g[lr][lc] in markers_cols:
            glyph = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
            for y, x in cells:
                glyph[y - r0][x - c0] = g[y][x]
            legends[(lr, lc)] = (g[lr][lc], glyph)
    return bg, markers_cols, marks, legends


def _origin(r, c, h, w, corner):
    return r - corner[0] * (h - 1), c - corner[1] * (w - 1)


def _learn_key(train, corner, size):
    """standard symbol set: for each marker colour, the sign found in the training outputs."""
    key = {}
    for p in train:
        gi, go = p["input"], p["output"]
        bg, _, marks, legends = _analyse(gi, corner)
        H, W = len(go), len(go[0])
        for (r, c), m in marks:
            if (r, c) in legends:
                continue
            h, w = size
            r0, c0 = _origin(r, c, h, w, corner)
            if r0 < 0 or c0 < 0 or r0 + h > H or c0 + w > W:
                continue
            patch = [[go[r0 + y][c0 + x] for x in range(w)] for y in range(h)]
            if m in key and key[m] != patch:
                return None
            key[m] = patch
    return key


def _render(g, corner, key):
    bg, _, marks, legends = _analyse(g, corner)
    font = dict(key)
    for m, glyph in legends.values():
        font[m] = glyph                       # the sheet's own legend overrides the learned key
    H, W = len(g), len(g[0])
    out = [[bg] * W for _ in range(H)]
    for (r, c), m in marks:
        if (r, c) in legends or m not in font:
            continue
        glyph = font[m]
        h, w = len(glyph), len(glyph[0])
        r0, c0 = _origin(r, c, h, w, corner)
        for y in range(h):
            for x in range(w):
                v = glyph[y][x]
                if v != bg and 0 <= r0 + y < H and 0 <= c0 + x < W:
                    out[r0 + y][c0 + x] = v
    return out


def fam_legend(train):
    for corner in CORNERS:
        sizes = []
        for p in train:
            for _, glyph in _analyse(p["input"], corner)[3].values():
                s = (len(glyph), len(glyph[0]))
                if s not in sizes:
                    sizes.append(s)
        sizes += [(k, k) for k in K_DOMAIN if (k, k) not in sizes]
        for size in sizes:
            key = _learn_key(train, corner, size)
            if key is None:
                continue
            fn = (lambda corner, key: (lambda g: _render(g, corner, key)))(corner, key)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("cartography:legend[corner=%s,size=%dx%d,key=%s]"
                       % (corner, size[0], size[1], sorted(key)), 3, fn)
                return


FAMILIES = (fam_legend,)
