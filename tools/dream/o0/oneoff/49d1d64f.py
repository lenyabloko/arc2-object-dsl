CARD = "49d1d64f"
READING = ("The grid is framed by a one-cell border that repeats each edge cell outward, with the "
           "four corner cells left as background.")


def _make(corner):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [[corner] * (W + 2) for _ in range(H + 2)]
        for i in range(H + 2):
            for j in range(W + 2):
                ei = i in (0, H + 1)
                ej = j in (0, W + 1)
                if ei and ej:
                    continue
                si = min(max(i - 1, 0), H - 1)
                sj = min(max(j - 1, 0), W - 1)
                out[i][j] = g[si][sj]
        return out
    return fn


def fam(train):
    corners = set()
    for p in train:
        o = p["output"]
        corners.add(o[0][0])
    cands = sorted(corners) + [c for c in (0,) if c not in corners]
    for c in cands:
        fn = _make(c)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("edge_pad_corner%d" % c, 1, fn)
                return
        except Exception:
            pass


FAMILIES = [fam]
