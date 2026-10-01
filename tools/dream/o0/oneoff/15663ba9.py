CARD = "15663ba9"
READING = ("On each closed one-pixel-wide outline, convex corner pixels (bend pointing outward) and concave corner pixels "
           "(bend pointing inward) are recoloured with two colours learned from training; all else is unchanged.")


def _outside(g):
    h, w = len(g), len(g[0])
    out = [[False] * w for _ in range(h)]
    st = [(r, c) for r in range(h) for c in range(w)
          if (r in (0, h - 1) or c in (0, w - 1)) and g[r][c] == 0]
    for r, c in st:
        out[r][c] = True
    while st:
        r, c = st.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and not out[rr][cc] and g[rr][cc] == 0:
                out[rr][cc] = True
                st.append((rr, cc))
    return out


def _kinds(g):
    h, w = len(g), len(g[0])
    outs = _outside(g)
    K = [[None] * w for _ in range(h)]
    for r in range(h):
        for c in range(w):
            v = g[r][c]
            if v == 0:
                continue
            nb = []
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == v:
                    nb.append((dr, dc))
            if len(nb) != 2:
                continue
            (a, b), (e, f) = nb
            if a + e == 0 and b + f == 0:
                continue  # straight
            dr, dc = a + e, b + f
            rr, cc = r + dr, c + dc
            inside = 0 <= rr < h and 0 <= cc < w and not outs[rr][cc]
            K[r][c] = 'convex' if inside else 'concave'
    return K


def fam(train):
    mapping = {}
    try:
        for p in train:
            I, O = p["input"], p["output"]
            if len(I) != len(O) or len(I[0]) != len(O[0]):
                return
            K = _kinds(I)
            for r in range(len(I)):
                for c in range(len(I[0])):
                    k = K[r][c]
                    if k is None:
                        if I[r][c] != O[r][c]:
                            return
                    else:
                        if mapping.setdefault(k, O[r][c]) != O[r][c]:
                            return
    except Exception:
        return

    def fn(g):
        K = _kinds(g)
        out = [row[:] for row in g]
        for r in range(len(g)):
            for c in range(len(g[0])):
                k = K[r][c]
                if k is not None and k in mapping:
                    out[r][c] = mapping[k]
        return out

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("corner_convexity_recolour", 1, fn)


FAMILIES = [fam]
