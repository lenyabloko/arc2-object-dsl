CARD = "e6de6e8f"
READING = ("The strip is a sequence of path tiles separated by empty columns; starting under a "
           "marker at the top centre, each vertical bar extends the path straight down by its "
           "height and each L-tile adds one horizontal 2-cell row that steps the path one column "
           "toward the side opposite its raised cell.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _pieces(g, bg):
    H, W = len(g), len(g[0])
    empty = [all(g[i][j] == bg for i in range(H)) for j in range(W)]
    pcs = []
    j = 0
    while j < W:
        if empty[j]:
            j += 1
            continue
        k = j
        while k < W and not empty[k]:
            k += 1
        pcs.append([[g[i][c] != bg for c in range(j, k)] for i in range(H)])
        j = k
    return pcs


def _steps(pcs):
    """Return list of steps: ('v', n) or ('h', width, dir)."""
    out = []
    for p in pcs:
        h, w = len(p), len(p[0])
        if w == 1:
            out.append(("v", sum(1 for r in p if r[0])))
            continue
        bottom = p[-1]
        top = p[0]
        if not all(bottom):
            return None
        tops = [c for c in range(w) if top[c]]
        if tops == [0]:
            out.append(("h", w, 1))
        elif tops == [w - 1]:
            out.append(("h", w, -1))
        else:
            return None
    return out


def _learn(train):
    # marker colour in output row 0, output width, path colour
    mk = set()
    widths = set()
    offs = set()
    for p in train:
        o = p["output"]
        widths.add(len(o[0]))
        cells = [(j, x) for j, x in enumerate(o[0]) if x != _bg(o)]
        if len(cells) != 1:
            return None
        mk.add(cells[0][1])
        offs.add(cells[0][0] - len(o[0]) // 2)
    if len(mk) != 1 or len(offs) != 1:
        return None
    return mk.pop(), (widths.pop() if len(widths) == 1 else None), offs.pop()


def _make(marker, W0, off):
    def fn(g):
        bg = 0 if any(0 in r for r in g) else _bg(g)
        col = [x for r in g for x in r if x != bg][0]
        st = _steps(_pieces(g, bg))
        if st is None:
            return [row[:] for row in g]
        # simulate path relative to start column 0
        rows = []
        x = 0
        for s in st:
            if s[0] == "v":
                for _ in range(s[1]):
                    rows.append([x])
            else:
                _, w, dr = s
                rows.append([x + dr * t for t in range(w)])
                x += dr * (w - 1)
        lo = min([0] + [c for r in rows for c in r])
        hi = max([0] + [c for r in rows for c in r])
        W = W0 if W0 is not None else 1
        while True:
            c0 = W // 2 + off
            if c0 + lo >= 0 and c0 + hi < W:
                break
            W += 2
        out = [[bg] * W for _ in range(len(rows) + 1)]
        out[0][c0] = marker
        for i, r in enumerate(rows):
            for c in r:
                out[i + 1][c0 + c] = col
        return out
    return fn


def fam(train):
    L = _learn(train)
    if L is None:
        return
    fn = _make(*L)
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("path_tiles", 3, fn)
    except Exception:
        pass


FAMILIES = [fam]
