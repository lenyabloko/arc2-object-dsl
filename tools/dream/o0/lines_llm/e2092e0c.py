"""Reviewer line family for ARC card e2092e0c (template search + framing).

A small pattern sits in one corner of the grid, fenced off from the rest by an
L made of a separator colour (one full row-arm and one full column-arm meeting
at the L's elbow).  That pattern is searched for elsewhere in the grid; every
copy found is enclosed in a one-cell frame of the separator colour (painted
over whatever was there, clipped at the border).  Everything else stays.
"""

CARD = "e2092e0c"
LINE = ("The small pattern fenced off by a separator-coloured L in a corner is searched for elsewhere "
        "in the grid, and its copy is enclosed in a one-cell frame of the separator colour.")

READING = {
    "generator": "The pattern enclosed between a grid corner and a separator-coloured L is located "
                 "elsewhere in the grid, and a one-cell-wide rectangular frame of the separator colour "
                 "is painted around each copy found.",
    "stop": "One frame per copy found outside the fenced corner block; frame cells outside the grid are "
            "clipped; if no copy is found the grid is returned unchanged.",
    "params": "separator ∈ {any colour forming the L (per grid), fixed colour induced from train} · "
              "match ∈ {exact (all cells equal), foreground (pattern's non-background cells equal)} · "
              "isometry ∈ {identity, any of the 8 rotations/reflections}",
    "participants": "Background = most frequent colour; the fence = smallest-area L in any of the four "
                    "corners whose row-arm runs from the grid edge to the elbow and whose column-arm runs "
                    "from the grid edge to the elbow, all in one non-background colour; the pattern = the "
                    "rectangle between the corner and the L; copies = equal-size windows elsewhere (not "
                    "overlapping the fenced block) matching the pattern.",
    "preconditions": "Input and output have the same size; every train input has such a corner L "
                     "enclosing a pattern with at least one non-background, non-separator cell; every "
                     "train output equals the input with the frames added.",
}

_CORNERS = ("tl", "tr", "bl", "br")


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _cell(g, corner, i, j):
    """Read cell (i, j) in the frame of reference where `corner` is the origin."""
    H, W = len(g), len(g[0])
    r = i if corner in ("tl", "tr") else H - 1 - i
    c = j if corner in ("tl", "bl") else W - 1 - j
    return g[r][c]


def _fences(g, bg):
    """All corner Ls: (area, corner_index, ph, pw, sep, r0, c0) with pattern at (r0, c0)."""
    H, W = len(g), len(g[0])
    out = []
    for ci, corner in enumerate(_CORNERS):
        for ph in range(1, H - 1):
            for pw in range(1, W - 1):
                s = _cell(g, corner, ph, pw)
                if s == bg:
                    continue
                if any(_cell(g, corner, ph, j) != s for j in range(pw)):
                    continue
                if any(_cell(g, corner, i, pw) != s for i in range(ph)):
                    continue
                vals = [_cell(g, corner, i, j) for i in range(ph) for j in range(pw)]
                if not any(v != bg and v != s for v in vals):
                    continue
                r0 = 0 if corner in ("tl", "tr") else H - ph
                c0 = 0 if corner in ("tl", "bl") else W - pw
                out.append((ph * pw, ci, ph, pw, s, r0, c0))
    out.sort()
    return out


def _pick_fence(g, bg, sep_fixed):
    for f in _fences(g, bg):
        if sep_fixed is None or f[4] == sep_fixed:
            return f
    return None


def _rot(p):
    return [list(r) for r in zip(*p[::-1])]


def _isos(p, iso):
    if iso == "id":
        return [p]
    res = []
    q = p
    for _ in range(4):
        for cand in (q, [row[::-1] for row in q]):
            if cand not in res:
                res.append(cand)
        q = _rot(q)
    return res


def _matches(g, pat, r, c, bg, match):
    for i, row in enumerate(pat):
        gr = g[r + i]
        for j, v in enumerate(row):
            if match == "fg" and v == bg:
                continue
            if gr[c + j] != v:
                return False
    return True


def _apply(g, sep_fixed, match, iso):
    H, W = len(g), len(g[0])
    out = [list(row) for row in g]
    bg = _bg(g)
    f = _pick_fence(g, bg, sep_fixed)
    if f is None:
        return out
    _, ci, ph, pw, s, r0, c0 = f
    corner = _CORNERS[ci]
    pat = [list(g[r0 + i][c0:c0 + pw]) for i in range(ph)]
    # fenced block = pattern + L arms (one extra row and column towards the interior)
    br0 = r0 if corner in ("tl", "tr") else r0 - 1
    bc0 = c0 if corner in ("tl", "bl") else c0 - 1
    br1, bc1 = br0 + ph + 1, bc0 + pw + 1  # exclusive
    hits = []
    for p in _isos(pat, iso):
        h, w = len(p), len(p[0])
        for r in range(H - h + 1):
            for c in range(W - w + 1):
                if r < br1 and r + h > br0 and c < bc1 and c + w > bc0:
                    continue
                if _matches(g, p, r, c, bg, match):
                    hits.append((r, c, h, w))
    for r, c, h, w in hits:
        for rr in range(r - 1, r + h + 1):
            for cc in range(c - 1, c + w + 1):
                if rr in (r - 1, r + h) or cc in (c - 1, c + w):
                    if 0 <= rr < H and 0 <= cc < W:
                        out[rr][cc] = s
    return out


def _make(sep_fixed, match, iso):
    return lambda grid: _apply(grid, sep_fixed, match, iso)


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or not gi[0] or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    # precondition: every train input has a corner fence; collect separator colours
    seps = None
    for p in train:
        g = p["input"]
        fs = _fences(g, _bg(g))
        if not fs:
            return
        cs = {f[4] for f in fs}
        seps = cs if seps is None else seps & cs
    sep_opts = [(None, 0)] + [(c, 1) for c in sorted(seps or [])]

    fits = []
    for match, mcost in (("exact", 0), ("fg", 1)):
        for iso, icost in (("id", 0), ("d4", 2)):
            for sep, scost in sep_opts:
                name = ("corner_fence_find_frame[sep=%s,match=%s,iso=%s]"
                        % ("auto" if sep is None else "c%d" % sep, match, iso))
                cost = 10 + mcost + icost + scost
                fn = _make(sep, match, iso)
                ok, changed = True, False
                for p in train:
                    try:
                        pred = fn(p["input"])
                    except Exception:
                        ok = False
                        break
                    if pred != [list(r) for r in p["output"]]:
                        ok = False
                        break
                    if pred != [list(r) for r in p["input"]]:
                        changed = True
                if ok and changed:
                    fits.append((name, cost, fn))
    fits.sort(key=lambda t: t[1])
    for t in fits:
        yield t


FAMILIES = [fam]
