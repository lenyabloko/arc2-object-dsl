CARD = "e7a25a18"
READING = ("Crop to the rectangular frame and scale the small coloured block inside it up by an integer "
           "factor so that it exactly fills the frame's interior.")


def _crop_bbox(g, bg=0):
    pts = [(i, j) for i, r in enumerate(g) for j, x in enumerate(r) if x != bg]
    if not pts:
        return None
    r0 = min(p[0] for p in pts); r1 = max(p[0] for p in pts)
    c0 = min(p[1] for p in pts); c1 = max(p[1] for p in pts)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _fn(g):
    f = _crop_bbox(g)
    if f is None:
        return [list(r) for r in g]
    H, W = len(f), len(f[0])
    fc = f[0][0]
    t = 0
    while t < min(H, W) // 2 and all(x == fc for x in f[t]) and all(f[i][t] == fc for i in range(H)):
        t += 1
    inner = [row[t:W - t] for row in f[t:H - t]]
    ih, iw = len(inner), len(inner[0]) if inner else 0
    cont = _crop_bbox(inner)
    out = [list(r) for r in f]
    if cont is None:
        return out
    ch, cw = len(cont), len(cont[0])
    if ih % ch or iw % cw:
        return out
    sy, sx = ih // ch, iw // cw
    for i in range(ih):
        for j in range(iw):
            out[t + i][t + j] = cont[i // sy][j // sx]
    return out


def fam(train):
    try:
        if all(_fn(p["input"]) == p["output"] for p in train):
            yield ("frame_crop_scale_content", 1.0, _fn)
    except Exception:
        pass


FAMILIES = [fam]
