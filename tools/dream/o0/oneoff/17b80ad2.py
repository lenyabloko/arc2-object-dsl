CARD = "17b80ad2"
READING = ("In every column whose edge cell (the bottom) is coloured, each empty cell takes the colour of "
           "the nearest coloured cell below it (scanning up from that edge cell), so the column becomes "
           "stacked bands; other columns are unchanged.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rot(g):
    # rotate 90 degrees clockwise
    return [list(r) for r in zip(*g[::-1])]


def _rotk(g, k):
    for _ in range(k % 4):
        g = _rot(g)
    return g


def _canon(g, bg, anchor):
    H, W = len(g), len(g[0])
    out = [list(r) for r in g]
    for c in range(W):
        b = g[H - 1][c]
        if b == bg or (anchor is not None and b != anchor):
            continue
        cur = b
        for r in range(H - 1, -1, -1):
            if g[r][c] != bg:
                cur = g[r][c]
            out[r][c] = cur
    return out


def _make(k, anchor):
    def fn(g):
        bg = _bg(g)
        h = _rotk(g, k)
        h = _canon(h, bg, anchor)
        return _rotk(h, 4 - k)
    return fn


def _fits(fn, train):
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return False
        except Exception:
            return False
    return True


def fam(train):
    # anchor colour: colour of edge cells that start a fill, induced from train (or any colour)
    anchors = [None]
    cols = set()
    for p in train:
        for r in p["input"]:
            cols.update(r)
    for a in sorted(cols):
        anchors.append(a)
    n = 0
    for k in range(4):
        for ai, a in enumerate(anchors):
            fn = _make(k, a)
            if _fits(fn, train):
                yield ("edge_fill_rot%d_anchor%s" % (k, a), k + (0 if a is None else 1), fn)
                n += 1
                if n >= 3:
                    return


FAMILIES = [fam]
