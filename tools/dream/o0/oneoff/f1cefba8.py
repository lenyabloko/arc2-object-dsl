CARD = "f1cefba8"
READING = ("Each notch where the inner rectangle's colour pokes into the frame marks a row or column: "
           "the notch is repaired, that line is drawn in the frame colour across the inner rectangle and "
           "in the inner colour outside the frame out to the grid edges.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _analyse(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg]
    if not cells:
        return None
    R0 = min(i for i, _ in cells); R1 = max(i for i, _ in cells)
    C0 = min(j for _, j in cells); C1 = max(j for _, j in cells)
    A = g[R0][C0]  # frame colour
    inner = [(i, j) for i, j in cells if g[i][j] != A]
    if not inner:
        return None
    B = g[inner[0][0]][inner[0][1]]
    bset = set(inner)
    prot = []
    core = []
    for i, j in inner:
        nb = sum((i + di, j + dj) in bset for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        (prot if nb <= 1 else core).append((i, j))
    if not core:
        return None
    r0 = min(i for i, _ in core); r1 = max(i for i, _ in core)
    c0 = min(j for _, j in core); c1 = max(j for _, j in core)
    return bg, A, B, (R0, R1, C0, C1), (r0, r1, c0, c1), prot


def _make(outside_full):
    def fn(g):
        H, W = len(g), len(g[0])
        res = _analyse(g)
        out = [r[:] for r in g]
        if res is None:
            return out
        bg, A, B, (R0, R1, C0, C1), (r0, r1, c0, c1), prot = res
        rlines, clines = [], []
        for i, j in prot:
            out[i][j] = A
            if r0 <= i <= r1:
                rlines.append(i)
            else:
                clines.append(j)
        for i in rlines:
            for j in range(c0, c1 + 1):
                out[i][j] = A
            for j in list(range(0, C0)) + list(range(C1 + 1, W)):
                if outside_full or out[i][j] == bg:
                    out[i][j] = B
        for j in clines:
            for i in range(r0, r1 + 1):
                out[i][j] = A
            for i in list(range(0, R0)) + list(range(R1 + 1, H)):
                if outside_full or out[i][j] == bg:
                    out[i][j] = B
        return out
    return fn


def fam(train):
    for outside_full in (False, True):
        fn = _make(outside_full)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("notch_lines_%s" % ("over" if outside_full else "bgonly"), 1 + outside_full, fn)
        except Exception:
            pass


FAMILIES = [fam]
