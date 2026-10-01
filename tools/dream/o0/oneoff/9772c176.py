CARD = "9772c176"
READING = ("On every side of each shape grow an outward stepped pyramid in the new colour: "
           "a cell is added when the three cells beneath it (towards the shape) are filled.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _rot(g):
    # rotate 90 degrees clockwise
    return [list(r) for r in zip(*g[::-1])]


def _grow_up(filled):
    H, W = len(filled), len(filled[0])
    f = [r[:] for r in filled]
    new = [[False] * W for _ in range(H)]
    for i in range(H - 2, -1, -1):
        for j in range(1, W - 1):
            if not f[i][j] and f[i + 1][j - 1] and f[i + 1][j] and f[i + 1][j + 1]:
                f[i][j] = True
                new[i][j] = True
    return new


def _make(newcol):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        bg = max(cnt, key=lambda k: cnt[k])
        base = [[x != bg for x in r] for r in g]
        out = [r[:] for r in g]
        cur = base
        # four directions via rotation; k rotations clockwise
        for k in range(4):
            new = _grow_up(cur)
            # map new back to the original frame: rotate counter-clockwise k times
            m = new
            for _ in range((4 - k) % 4):
                m = _rot(m)
            for i in range(H):
                for j in range(W):
                    if m[i][j] and out[i][j] == bg:
                        out[i][j] = newcol
            cur = _rot(cur)
        return out
    return fn


def fam(train):
    cols = set()
    for p in train:
        ic = set(x for r in p["input"] for x in r)
        oc = set(x for r in p["output"] for x in r)
        cols |= (oc - ic)
    for c in sorted(cols):
        fn = _make(c)
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != p["output"]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield ("pyramid_grow_col%d" % c, 1, fn)


FAMILIES = [fam]
