CARD = "4612dd53"
READING = ("Inside the bounding box of the dotted figure, every row or column that is mostly filled is a broken "
           "line, and its gaps are filled with the new colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _dense(seq, fg):
    return 2 * sum(1 for x in seq if x == fg) > len(seq)


def _run2(seq, fg):
    return any(seq[i] == fg and seq[i + 1] == fg for i in range(len(seq) - 1))


def _make(fill, test):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg]
        if not cells:
            return [list(r) for r in g]
        cnt = {}
        for i, j in cells:
            cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
        fg = max(cnt, key=lambda k: cnt[k])
        r0 = min(i for i, _ in cells)
        r1 = max(i for i, _ in cells)
        c0 = min(j for _, j in cells)
        c1 = max(j for _, j in cells)
        out = [list(r) for r in g]
        for r in range(r0, r1 + 1):
            seq = g[r][c0:c1 + 1]
            if test(seq, fg):
                for c in range(c0, c1 + 1):
                    if g[r][c] == bg:
                        out[r][c] = fill
        for c in range(c0, c1 + 1):
            seq = [g[r][c] for r in range(r0, r1 + 1)]
            if test(seq, fg):
                for r in range(r0, r1 + 1):
                    if g[r][c] == bg:
                        out[r][c] = fill
        return out
    return fn


def fam(train):
    ins = set()
    outs = set()
    for p in train:
        for r in p["input"]:
            ins.update(r)
        for r in p["output"]:
            outs.update(r)
    new = sorted(outs - ins)
    if len(new) != 1:
        return
    fill = new[0]
    for name, test, cost in (("dense_lines", _dense, 1.0), ("run2_lines", _run2, 1.2)):
        fn = _make(fill, test)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("fill_gaps_" + name, cost, fn)


FAMILIES = [fam]
