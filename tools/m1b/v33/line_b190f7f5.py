"""Line family for card b190f7f5 (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds two parts -- a colour pattern and a stamp shape (one colour).  The output
replicates the pattern at stamp resolution: every pattern cell becomes one block the size of the stamp,
holding the stamp's shape painted solid in that cell's colour (background cells give empty blocks).
The two parts are found as the two halves of the grid, the two sides of a separator line, two disjoint
colour groups, or (degenerate case) the pattern is its own stamp.  Which part is the stamp is decided by
colour (the single-colour part, or the colour that is the stamp in every training pair) or by position.
"""

CARD = "b190f7f5"
LINE = "replicate color pattern using solid color stamps"
READING = {
    "generator": "Blow the colour pattern up by the stamp's size: each pattern cell becomes a stamp-sized block "
                 "holding the stamp's shape painted solid in that cell's colour; background pattern cells give "
                 "empty (background) blocks.",
    "stop": "One block per pattern cell, so the output is (pattern rows x stamp rows [+ gaps]) by (pattern "
            "columns x stamp columns [+ gaps]); nothing is drawn outside those blocks.",
    "params": "split ∈ {halves (along the longer side, else the side that gives a valid stamp/pattern pair), "
              "separator line, disjoint colour groups, self} · stamp ∈ {the single-colour part, the part of the "
              "induced stamp colour, first part, second part} · crop stamp ∈ {no, yes} · gap ∈ {0, 1} · "
              "bg ∈ {input's most frequent colour, training outputs' common most frequent colour}",
    "participants": "Pattern: the part with the colours to replicate (not cropped: its background cells matter). "
                    "Stamp: the other part; its non-background cells form the shape. Parts come from splitting "
                    "the input (equal halves, or either side of a full uniform non-background line), from the "
                    "bounding boxes of one colour and of all other colours when they do not overlap, or the "
                    "input serves as both.",
    "preconditions": "The input splits into exactly one admissible (stamp, pattern) pair, both with some "
                     "non-background cell, and each training output has exactly the blown-up size and content.",
}


def _mode(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _cols(p, bg):
    return frozenset(v for row in p for v in row if v != bg)


def _crop(g, bg):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    if not cells:
        return None
    r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
    c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _candidates(g, bg, split):
    """List of (rank, A, B): ordered part pairs; smaller rank = preferred."""
    H, W = len(g), len(g[0])
    out = []
    if split == "halves":
        if W % 2 == 0 and W >= 2:
            out.append((0 if W >= H else 1, [r[:W // 2] for r in g], [r[W // 2:] for r in g]))
        if H % 2 == 0 and H >= 2:
            out.append((0 if H >= W else 1, [r[:] for r in g[:H // 2]], [r[:] for r in g[H // 2:]]))
    elif split == "separator":
        for axis in (0, 1):
            gg = g if axis == 0 else [list(t) for t in zip(*g)]
            n = len(gg)
            for s in sorted({gg[i][0] for i in range(n)} - {bg}):
                lines = [i for i in range(n) if all(v == s for v in gg[i])]
                if not lines or lines != list(range(lines[0], lines[-1] + 1)):
                    continue  # need one contiguous band
                if any(v == s for i in range(n) if i not in lines for v in gg[i]):
                    continue  # a separator colour is used only by the band
                a, b = lines[0], lines[-1]
                if a == 0 or b == n - 1:
                    continue
                A, B = gg[:a], gg[b + 1:]
                if axis == 1:
                    A = [list(t) for t in zip(*A)]; B = [list(t) for t in zip(*B)]
                out.append((0, [r[:] for r in A], [r[:] for r in B]))
    elif split == "objects":
        cells = {}
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                if v != bg:
                    cells.setdefault(v, []).append((r, c))
        if len(cells) >= 2:
            def box(pts):
                return (min(p[0] for p in pts), max(p[0] for p in pts),
                        min(p[1] for p in pts), max(p[1] for p in pts))
            for col in sorted(cells):
                bs = box(cells[col])
                br = box([p for k in cells if k != col for p in cells[k]])
                if bs[1] < br[0] or br[1] < bs[0] or bs[3] < br[2] or br[3] < bs[2]:
                    S = [row[bs[2]:bs[3] + 1] for row in g[bs[0]:bs[1] + 1]]
                    P = [row[br[2]:br[3] + 1] for row in g[br[0]:br[1] + 1]]
                    out.append((0, S, P))
    elif split == "self":
        out.append((0, g, [r[:] for r in g]))
    return out


def _roles(A, B, bg, sel, key):
    """(stamp, pattern) or None."""
    ca, cb = _cols(A, bg), _cols(B, bg)
    if not ca or not cb:
        return None
    if sel == "mono":
        if len(ca) == 1 and len(cb) != 1:
            return A, B
        if len(cb) == 1 and len(ca) != 1:
            return B, A
        return None
    if sel == "key":
        ka, kb = ca == {key}, cb == {key}
        if ka and not kb:
            return A, B
        if kb and not ka:
            return B, A
        return None
    if sel == "first":
        return A, B
    if sel == "second":
        return B, A
    return None


def _pick(g, bg, split, sel, key, crop):
    if split == "self":
        sel_ok = [(g, [r[:] for r in g])] if _cols(g, bg) else []
    else:
        found = []
        for rank, A, B in _candidates(g, bg, split):
            sp = _roles(A, B, bg, sel, key)
            if sp is not None:
                found.append((rank, sp))
        if not found:
            return None
        best = min(r for r, _ in found)
        sel_ok = [sp for r, sp in found if r == best]
    if len(sel_ok) != 1:
        return None  # no admissible pair, or ambiguous
    stamp, pat = sel_ok[0]
    if crop:
        stamp = _crop(stamp, bg)
        if stamp is None:
            return None
    return stamp, pat


def _render(pat, stamp, bg, gap):
    ph, pw, sh, sw = len(pat), len(pat[0]), len(stamp), len(stamp[0])
    H, W = ph * sh + (ph - 1) * gap, pw * sw + (pw - 1) * gap
    out = [[bg] * W for _ in range(H)]
    mask = [(a, b) for a in range(sh) for b in range(sw) if stamp[a][b] != bg]
    for i in range(ph):
        for j in range(pw):
            c = pat[i][j]
            if c == bg:
                continue
            y0, x0 = i * (sh + gap), j * (sw + gap)
            for a, b in mask:
                out[y0 + a][x0 + b] = c
    return out


def _make(split, sel, key, crop, gap, bgc):
    def fn(grid):
        bg = _mode(grid) if bgc is None else bgc
        sp = _pick(grid, bg, split, sel, key, crop)
        if sp is None:
            return None
        stamp, pat = sp
        return _render(pat, stamp, bg, gap)
    return fn


def _keys(train, bgs, split):
    """Colours that are the sole colour of some candidate part in every training input."""
    common = None
    for p, bg in zip(train, bgs):
        ks = set()
        for _, A, B in _candidates(p["input"], bg, split):
            for P in (A, B):
                cs = _cols(P, bg)
                if len(cs) == 1:
                    ks |= cs
        common = ks if common is None else common & ks
        if not common:
            return []
    return sorted(common or [])


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or not gi[0] or not go or not go[0]:
            return
        if len(go) * len(go[0]) <= len(gi) * len(gi[0]) // 2:
            return  # replication enlarges: the output is at least as large as one part
    bg_opts = [(None, 0)]
    outm = {_mode(p["output"]) for p in train}
    if len(outm) == 1:
        b = next(iter(outm))
        if any(_mode(p["input"]) != b for p in train):
            bg_opts.append((b, 1))
    found = []
    for bgc, bcost in bg_opts:
        bgs = [(_mode(p["input"]) if bgc is None else bgc) for p in train]
        for split, scost in (("halves", 0), ("separator", 1), ("objects", 2), ("self", 3)):
            sels = [("self", None, 0)] if split == "self" else (
                [("mono", None, 0)] + [("key", k, 1) for k in _keys(train, bgs, split)]
                + [("first", None, 2), ("second", None, 2)])
            for sel, key, ccost in sels:
                for crop in ((False,) if split == "objects" else (False, True)):
                    picks = [_pick(p["input"], bg, split, sel, key, crop) for p, bg in zip(train, bgs)]
                    if any(x is None for x in picks):
                        continue
                    for gap in (0, 1):
                        ok = True
                        for (stamp, pat), p, bg in zip(picks, train, bgs):
                            go = p["output"]
                            ph, pw, sh, sw = len(pat), len(pat[0]), len(stamp), len(stamp[0])
                            if (len(go), len(go[0])) != (ph * sh + (ph - 1) * gap, pw * sw + (pw - 1) * gap):
                                ok = False; break
                            if _render(pat, stamp, bg, gap) != go:
                                ok = False; break
                        if not ok:
                            continue
                        cost = 10 + scost + ccost + bcost + int(crop) + gap
                        name = "stamp_replicate[split=%s,stamp=%s%s,crop=%s,gap=%d,bg=%s]" % (
                            split, sel, "" if key is None else "(%d)" % key, "yes" if crop else "no", gap,
                            "input_mode" if bgc is None else "out_const(%d)" % bgc)
                        found.append((cost, len(found), name, (split, sel, key, crop, gap, bgc)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


FAMILIES = [fam]
