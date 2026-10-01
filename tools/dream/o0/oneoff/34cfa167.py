CARD = "34cfa167"
READING = ("Two equal squares mark opposite corners of a rectangle: the square is copied to the other two "
           "corners, the striped pattern beside the first square is tiled (mirror-periodically) along all "
           "four edges between the corners, and each edge gets an outer line in its first stripe's colour.")


def _mc(xs):
    cnt = {}
    for x in xs:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _comps(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == col and (r, c) not in seen:
                st = [(r, c)]
                seen.add((r, c))
                cells = []
                while st:
                    y, x = st.pop()
                    cells.append((y, x))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and g[yy][xx] == col and (yy, xx) not in seen:
                            seen.add((yy, xx))
                            st.append((yy, xx))
                out.append(cells)
    return out


def _rect(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
    if (r1 - r0 + 1) * (c1 - c0 + 1) != len(cells):
        return None
    return r0, c0, r1 - r0 + 1, c1 - c0 + 1


def _unit(seq, bg, mode):
    # seq: list of stripe tuples read outward from the square
    last = max(i for i, s in enumerate(seq) if any(x != bg for x in s))
    p = seq[:last + 1]
    if mode == "mirror":
        u = p + p[::-1][1:-1]
    else:
        u = p + [tuple([bg] * len(p[0]))]
    return u if u else p


def _find(g, bg):
    H, W = len(g), len(g[0])
    colors = sorted(set(x for r in g for x in r) - {bg})
    for K in colors:
        comps = _comps(g, K)
        if len(comps) != 2:
            continue
        rects = [_rect(c) for c in comps]
        if None in rects or rects[0][2:] != rects[1][2:]:
            continue
        for A, B in ((rects[0], rects[1]), (rects[1], rects[0])):
            ra, ca, h, w = A
            rb, cb = B[0], B[1]
            if not (rb >= ra + h + 1 or rb + h + 1 <= ra) or not (cb >= ca + w + 1 or cb + w + 1 <= ca):
                continue
            dy = 1 if rb > ra else -1
            dx = 1 if cb > ca else -1
            hc = ca + w if dx > 0 else ca - 1
            vr = ra + h if dy > 0 else ra - 1
            if not (0 <= hc < W and 0 <= vr < H):
                continue
            if all(g[r][hc] == bg for r in range(ra, ra + h)):
                continue
            if all(g[vr][c] == bg for c in range(ca, ca + w)):
                continue
            return K, A, B, dy, dx
    return None


def _apply(g, mode, lines):
    H, W = len(g), len(g[0])
    bg = _mc([x for r in g for x in r])
    f = _find(g, bg)
    if f is None:
        return None
    K, A, B, dy, dx = f
    ra, ca, h, w = A
    rb, cb = B[0], B[1]
    # horizontal span (columns strictly between the squares), ordered outward from A
    if dx > 0:
        hspan = list(range(ca + w, cb))
    else:
        hspan = list(range(ca - 1, cb + w - 1, -1))
    if dy > 0:
        vspan = list(range(ra + h, rb))
    else:
        vspan = list(range(ra - 1, rb + h - 1, -1))
    if not hspan or not vspan:
        return None
    hseq = [tuple(g[r][c] for r in range(ra, ra + h)) for c in hspan]
    vseq = [tuple(g[r][c] for c in range(ca, ca + w)) for r in vspan]
    hu = _unit(hseq, bg, mode)
    vu = _unit(vseq, bg, mode)
    out = [[bg] * W for _ in range(H)]
    # corners
    for (r0, c0) in ((ra, ca), (ra, cb), (rb, ca), (rb, cb)):
        for i in range(h):
            for j in range(w):
                if 0 <= r0 + i < H and 0 <= c0 + j < W:
                    out[r0 + i][c0 + j] = K
    # horizontal bands at A rows and B rows
    for rbase in (ra, rb):
        for k, c in enumerate(hspan):
            st = hu[k % len(hu)]
            for i in range(h):
                out[rbase + i][c] = st[i]
    for cbase in (ca, cb):
        for k, r in enumerate(vspan):
            st = vu[k % len(vu)]
            for j in range(w):
                out[r][cbase + j] = st[j]
    if lines:
        hcol = hu[0][0]
        vcol = vu[0][0]
        top_out = ra - 1 if dy > 0 else ra + h
        bot_out = rb + h if dy > 0 else rb - 1
        for rr in (top_out, bot_out):
            if 0 <= rr < H:
                for c in hspan:
                    out[rr][c] = hcol
        left_out = ca - 1 if dx > 0 else ca + w
        right_out = cb + w if dx > 0 else cb - 1
        for cc in (left_out, right_out):
            if 0 <= cc < W:
                for r in vspan:
                    out[r][cc] = vcol
    return out


def fam(train):
    for mode in ("mirror", "gap"):
        for lines in (True, False):
            ok = True
            for p in train:
                if _apply(p["input"], mode, lines) != p["output"]:
                    ok = False
                    break
            if ok:
                def fn(g, mode=mode, lines=lines):
                    return _apply(g, mode, lines)
                yield ("corners_%s_%s" % (mode, "lines" if lines else "nolines"), 4, fn)


FAMILIES = [fam]
