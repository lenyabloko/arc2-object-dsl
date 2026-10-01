CARD = "58743b76"
READING = ("The small colour key sitting in the corner outside the framed field splits the field into "
           "matching equal blocks, and every dot in a block is recoloured to that block's key colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _solve(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    rows = [i for i in range(H) if any(x == bg for x in g[i])]
    cols = [j for j in range(W) if any(g[i][j] == bg for i in range(H))]
    r0, r1, c0, c1 = min(rows), max(rows), min(cols), max(cols)
    fh, fw = r1 - r0 + 1, c1 - c0 + 1
    krows = [i for i in range(H) if not (r0 <= i <= r1)]
    kcols = [j for j in range(W) if not (c0 <= j <= c1)]
    if not krows or not kcols:
        return None
    key = [[g[i][j] for j in kcols] for i in krows]
    kh, kw = len(key), len(key[0])
    if fh % kh or fw % kw:
        return None
    out = [row[:] for row in g]
    for i in range(r0, r1 + 1):
        for j in range(c0, c1 + 1):
            if g[i][j] != bg:
                out[i][j] = key[(i - r0) * kh // fh][(j - c0) * kw // fw]
    return out


def fam(train):
    ok = True
    for p in train:
        try:
            if _solve(p["input"]) != p["output"]:
                ok = False
                break
        except Exception:
            ok = False
            break
    if ok:
        yield ("corner_key_blocks", 0, _solve)


FAMILIES = [fam]
