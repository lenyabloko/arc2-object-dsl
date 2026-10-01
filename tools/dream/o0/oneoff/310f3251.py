CARD = "310f3251"
READING = "Mark the up-left diagonal neighbour of every coloured cell (wrapping around the tile) with a new colour on background cells, then tile the result to the output size."


def _ratio(train):
    rs = set()
    for p in train:
        hi, wi = len(p["input"]), len(p["input"][0])
        ho, wo = len(p["output"]), len(p["output"][0])
        if ho % hi or wo % wi:
            return None
        rs.add((ho // hi, wo // wi))
    return rs.pop() if len(rs) == 1 else None


def _newcol(train):
    s = None
    for p in train:
        ci = {v for row in p["input"] for v in row}
        co = {v for row in p["output"] for v in row}
        d = co - ci
        s = d if s is None else s & d
    return sorted(s) if s else []


def _make(ry, rx, dr, dc, mark, bg):
    def fn(g):
        h, w = len(g), len(g[0])
        t = [row[:] for row in g]
        for r in range(h):
            for c in range(w):
                if g[r][c] != bg and g[r][c] != mark:
                    rr, cc = (r + dr) % h, (c + dc) % w
                    if g[rr][cc] == bg:
                        t[rr][cc] = mark
        return [[t[r % h][c % w] for c in range(w * rx)] for r in range(h * ry)]
    return fn


def fam(train):
    rat = _ratio(train)
    cols = _newcol(train)
    if rat is None or len(cols) != 1:
        return
    mark = cols[0]
    cnt = {}
    for p in train:
        for row in p["input"]:
            for v in row:
                cnt[v] = cnt.get(v, 0) + 1
    bg = max(cnt, key=lambda k: cnt[k])
    found = 0
    for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)):
        fn = _make(rat[0], rat[1], dr, dc, mark, bg)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("diag_mark_tile_%d_%d" % (dr, dc), 1 + found, fn)
                found += 1
        except Exception:
            pass


FAMILIES = [fam]
