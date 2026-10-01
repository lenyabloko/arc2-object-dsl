"""Line family for card de809cff (test-blind; written from the reviewer's line and train pairs only).

Reading: the scene is a few large solid colour regions on a background, sprinkled with noise.
"Free objects" are the noise cells that do not belong to the solid shape they sit in: stray
pixels / tiny blobs in the background, and one-cell bumps that stick out of a region (into the
background or into a neighbouring region). They are removed, i.e. repainted with the territory
they sit in. The remaining noise -- background-coloured holes inside a region -- is decorated:
the hole gets a marker colour and its surrounding ring is painted with the alternate colour,
i.e. the colour of the other region.

Territory test ("solid support"): a cell belongs to colour c when it has a c-neighbour
horizontally AND a c-neighbour vertically (this keeps region corners and edges, drops
one-cell protrusions and isolated pixels). Holes are counted as wildcards while deciding
support, so the cells between neighbouring holes are not mistaken for protrusions.
"""

CARD = "de809cff"
LINE = "remove free objects and decorate with  alternate color"
READING = {
    "generator": "Remove every free object (stray pixels in the background and one-cell bumps sticking out of a "
                 "region) by repainting it with the territory around it; then mark each background hole inside a "
                 "region with the marker colour and paint the ring around it with the other region's colour.",
    "stop": "One pass: each hole gets exactly one ring of the declared shape (clipped at the grid edge); "
            "rings may overwrite neighbouring cells of any colour, holes keep the marker on top.",
    "params": "bg in {constant induced from train, most frequent border colour} · mark in {new colour induced "
              "from train outputs, bg, alternate colour} · ring in {square r=1, plus r=1, square r=2, plus r=2} · "
              "alternate = the other region colour (if more than two regions: the region colour sharing the "
              "longest border with the hole's region)",
    "participants": "Regions: non-background colours, a cell belongs to colour c if it has a c-neighbour both "
                    "horizontally and vertically. Free objects: non-background cells failing that test for their "
                    "own colour, plus single-colour blobs that fit in a 2x2 box. Holes: background cells that pass "
                    "the test for some region colour (cells with >= 3 same-colour 4-neighbours count as that colour "
                    "while testing).",
    "preconditions": "Every train input has a background, at least two region colours and at least one hole; a "
                     "consistent marker colour is induced from the train outputs.",
}


def _border_bg(g):
    H, W = len(g), len(g[0])
    cnt = {}
    for r in range(H):
        for c in range(W):
            if r in (0, H - 1) or c in (0, W - 1):
                cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _supported(M, r, c, col):
    H, W = len(M), len(M[0])
    h = (c > 0 and M[r][c - 1] == col) or (c < W - 1 and M[r][c + 1] == col)
    if not h:
        return False
    return (r > 0 and M[r - 1][c] == col) or (r < H - 1 and M[r + 1][c] == col)


def _n4(H, W, r, c):
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < H and 0 <= cc < W:
            yield rr, cc


def _n8count(M, r, c, col):
    H, W = len(M), len(M[0])
    k = 0
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if (dr or dc) and 0 <= r + dr < H and 0 <= c + dc < W and M[r + dr][c + dc] == col:
                k += 1
    return k


def _wildcards(G, bg):
    """Background cells with >= 3 same-colour (non-bg) 4-neighbours, mapped to that colour."""
    H, W = len(G), len(G[0])
    M = [row[:] for row in G]
    for r in range(H):
        for c in range(W):
            if G[r][c] != bg:
                continue
            cnt = {}
            for rr, cc in _n4(H, W, r, c):
                v = G[rr][cc]
                if v != bg:
                    cnt[v] = cnt.get(v, 0) + 1
            best = [v for v in sorted(cnt) if cnt[v] >= 3]
            if best:
                M[r][c] = best[0]
    return M


def _pick(M, r, c, cands):
    return max(cands, key=lambda v: (_n8count(M, r, c, v), -v))


def _clean(g, bg):
    """Remove free objects; returns the territory grid (holes still background)."""
    H, W = len(g), len(g[0])
    colours = sorted({v for row in g for v in row if v != bg})
    G = [row[:] for row in g]
    # Peel in rounds: an unsupported cell is reassigned only to a colour supported by SOLID
    # neighbours (cells supported in their own colour, or wildcard holes), so noise next to
    # noise is resolved from the solid side inwards.
    for _ in range(H * W + 1):
        M = _wildcards(G, bg)
        U = [(r, c) for r in range(H) for c in range(W)
             if G[r][c] != bg and not _supported(M, r, c, G[r][c])]
        if not U:
            break
        Ms = [row[:] for row in M]
        for r, c in U:
            Ms[r][c] = None
        changes = {}
        for r, c in U:
            cands = [k for k in colours if _supported(Ms, r, c, k)]
            if cands:
                changes[(r, c)] = _pick(Ms, r, c, cands)
            elif not any(_supported(M, r, c, k) for k in colours):
                changes[(r, c)] = bg  # can never be part of a solid shape: a free object
        if not changes:
            changes = {p: bg for p in U}
        for (r, c), v in changes.items():
            G[r][c] = v
    # tiny blobs (fit in a 2x2 box) are free objects too
    seen = [[False] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if seen[r][c] or G[r][c] == bg:
                continue
            col = G[r][c]
            comp, stack = [], [(r, c)]
            seen[r][c] = True
            while stack:
                a, b = stack.pop()
                comp.append((a, b))
                for aa, bb in _n4(H, W, a, b):
                    if not seen[aa][bb] and G[aa][bb] == col:
                        seen[aa][bb] = True
                        stack.append((aa, bb))
            rs = [p[0] for p in comp]
            cs = [p[1] for p in comp]
            if max(rs) - min(rs) < 2 and max(cs) - min(cs) < 2:
                for a, b in comp:
                    G[a][b] = bg
    return G


def _holes(G, bg):
    H, W = len(G), len(G[0])
    colours = sorted({v for row in G for v in row if v != bg})
    M = _wildcards(G, bg)
    holes = {}
    for r in range(H):
        for c in range(W):
            if G[r][c] != bg:
                continue
            cands = [k for k in colours if _supported(M, r, c, k)]
            if cands:
                holes[(r, c)] = _pick(M, r, c, cands)
    return holes


def _alt_map(G, bg):
    H, W = len(G), len(G[0])
    colours = sorted({v for row in G for v in row if v != bg})
    alt = {}
    if len(colours) == 2:
        alt[colours[0]], alt[colours[1]] = colours[1], colours[0]
        return alt
    adj = {}
    for r in range(H):
        for c in range(W):
            a = G[r][c]
            if a == bg:
                continue
            for rr, cc in ((r + 1, c), (r, c + 1)):
                if rr < H and cc < W:
                    b = G[rr][cc]
                    if b != bg and b != a:
                        adj[(a, b)] = adj.get((a, b), 0) + 1
                        adj[(b, a)] = adj.get((b, a), 0) + 1
    for a in colours:
        others = [(adj.get((a, b), 0), -b) for b in colours if b != a and adj.get((a, b), 0) > 0]
        if others:
            alt[a] = -max(others)[1]
    return alt


RINGS = {
    "square1": [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc],
    "plus1": [(-1, 0), (1, 0), (0, -1), (0, 1)],
    "square2": [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3) if dr or dc],
    "plus2": [(dr, 0) for dr in (-2, -1, 1, 2)] + [(0, dc) for dc in (-2, -1, 1, 2)],
}


def _make(bg_mode, bg_const, mark_mode, mark_const, ring):
    offs = RINGS[ring]

    def fn(g):
        bg = bg_const if bg_mode == "const" else _border_bg(g)
        H, W = len(g), len(g[0])
        G = _clean(g, bg)
        holes = _holes(G, bg)
        alt = _alt_map(G, bg)
        out = [row[:] for row in G]
        for (r, c) in sorted(holes):
            a = alt.get(holes[(r, c)])
            if a is None:
                continue
            for dr, dc in offs:
                rr, cc = r + dr, c + dc
                if 0 <= rr < H and 0 <= cc < W and (rr, cc) not in holes:
                    out[rr][cc] = a
        for (r, c) in sorted(holes):
            if mark_mode == "new":
                out[r][c] = mark_const
            elif mark_mode == "alt" and holes[(r, c)] in alt:
                out[r][c] = alt[holes[(r, c)]]
            else:
                out[r][c] = bg
        return out
    return fn


def _induce(train):
    """(bg constant or None, new marker colour or None)."""
    in_cols = set()
    for p in train:
        for row in p["input"]:
            in_cols.update(row)
    new = set()
    for p in train:
        for row in p["output"]:
            new.update(v for v in row if v not in in_cols)
    mark = min(new) if len(new) == 1 else None
    bgs = set()
    if mark is not None:
        for p in train:
            gi, go = p["input"], p["output"]
            if len(gi) != len(go) or len(gi[0]) != len(go[0]):
                return None, None
            for r in range(len(gi)):
                for c in range(len(gi[0])):
                    if go[r][c] == mark:
                        bgs.add(gi[r][c])
    bg = min(bgs) if len(bgs) == 1 else None
    return bg, mark


def fam(train):
    if not train:
        return
    for p in train:
        if len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0]):
            return
    bg_const, mark_const = _induce(train)
    bg_modes = ([("const", bg_const)] if bg_const is not None else []) + [("border", None)]
    mark_modes = ([("new", mark_const)] if mark_const is not None else []) + [("bg", None), ("alt", None)]
    # preconditions under the primary bg choice
    bg0m, bg0c = bg_modes[0]
    for p in train:
        g = p["input"]
        bg = bg0c if bg0m == "const" else _border_bg(g)
        G = _clean(g, bg)
        if len({v for row in G for v in row if v != bg}) < 2 or not _holes(G, bg):
            return
    progs = []
    for bi, (bm, bc) in enumerate(bg_modes):
        for mi, (mm, mc) in enumerate(mark_modes):
            for ri, ring in enumerate(("square1", "plus1", "square2", "plus2")):
                name = "remove_free_decorate_holes[bg=%s,mark=%s,ring=%s]" % (
                    bm if bc is None else "%s:%d" % (bm, bc), mm if mc is None else "%s:%d" % (mm, mc), ring)
                progs.append((name, 1 + bi + mi + ri, _make(bm, bc, mm, mc, ring)))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
