CARD = "97c75046"
READING = ("The single marker cell slides straight toward the hole region until blocked, then "
           "keeps sliding diagonally forward (one fixed sideways sense) along the hole's edge while staying in contact "
           "with it, and is redrawn at the final position.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _make(contact8):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        order = sorted(cnt, key=lambda k: (-cnt[k], k))
        bg = order[0]
        mover = min(cnt, key=lambda k: (cnt[k], k))
        holes = [k for k in order if k != bg and k != mover]
        if not holes:
            return [r[:] for r in g]
        hole = holes[0]
        pos = [(i, j) for i in range(H) for j in range(W) if g[i][j] == mover][0]

        def inb(i, j):
            return 0 <= i < H and 0 <= j < W

        def is_hole(i, j):
            return inb(i, j) and g[i][j] == hole

        def free(i, j):
            return inb(i, j) and g[i][j] != hole

        nbs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if contact8:
            nbs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        def contact(i, j):
            return any(is_hole(i + a, j + b) for a, b in nbs)

        # phase 1: choose the orthogonal ray that reaches the hole region first
        best = None
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            i, j = pos
            k = 0
            while True:
                i += d[0]; j += d[1]; k += 1
                if not inb(i, j):
                    break
                if g[i][j] == hole:
                    if best is None or k < best[0]:
                        best = (k, d)
                    break
        if best is None:
            return [r[:] for r in g]
        d = best[1]
        i, j = pos
        while free(i + d[0], j + d[1]):
            i += d[0]; j += d[1]
        # phase 2: diagonal-forward slides while touching the hole region
        perps = [(d[1], d[0]), (-d[1], -d[0])]
        while True:
            moved = False
            for p in perps:
                ni, nj = i + d[0] + p[0], j + d[1] + p[1]
                if free(ni, nj) and contact(ni, nj):
                    i, j = ni, nj
                    moved = True
                    perps = [p]  # keep the chosen sideways direction
                    break
            if not moved:
                break
        out = [r[:] for r in g]
        out[pos[0]][pos[1]] = bg
        out[i][j] = mover
        return out
    return fn


def fam(train):
    for name, cost, fn in (("slide_contact4", 1, _make(False)), ("slide_contact8", 2, _make(True))):
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
            yield (name, cost, fn)


FAMILIES = [fam]
