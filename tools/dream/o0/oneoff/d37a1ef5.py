CARD = "d37a1ef5"
READING = ("Inside the rectangular frame, every empty cell outside the bounding box of the enclosed "
           "marks is filled with the frame colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _apply(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cnt = {}
    for r in g:
        for x in r:
            if x != bg:
                cnt[x] = cnt.get(x, 0) + 1
    frame = max(sorted(cnt), key=lambda k: cnt[k])
    fc = [(r, c) for r in range(H) for c in range(W) if g[r][c] == frame]
    r0 = min(a for a, _ in fc); r1 = max(a for a, _ in fc)
    c0 = min(b for _, b in fc); c1 = max(b for _, b in fc)
    inner = [(r, c) for r in range(r0 + 1, r1) for c in range(c0 + 1, c1)
             if g[r][c] != bg and g[r][c] != frame]
    out = [list(r) for r in g]
    if inner:
        a0 = min(a for a, _ in inner); a1 = max(a for a, _ in inner)
        b0 = min(b for _, b in inner); b1 = max(b for _, b in inner)
    else:
        a0, a1, b0, b1 = 1, 0, 1, 0
    for r in range(r0 + 1, r1):
        for c in range(c0 + 1, c1):
            if g[r][c] == bg and not (a0 <= r <= a1 and b0 <= c <= b1):
                out[r][c] = frame
    return out


def fam(train):
    try:
        if all(_apply(p["input"]) == p["output"] for p in train):
            yield ("frame_fill_outside_markbox", 1, _apply)
    except Exception:
        return


FAMILIES = [fam]
