CARD = "aa300dc3"
READING = ("The longest unbroken diagonal run (either direction) of open cells inside the wall-coloured "
           "grid is painted with the mark colour induced from training (ties: the line nearest the "
           "grid centre).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _runs(g, open_col):
    H, W = len(g), len(g[0])
    runs = []
    for dr, dc in ((1, 1), (1, -1)):
        for r in range(H):
            for c in range(W):
                if g[r][c] != open_col:
                    continue
                pr, pc = r - dr, c - dc
                if 0 <= pr < H and 0 <= pc < W and g[pr][pc] == open_col:
                    continue  # not a run start
                cells = []
                a, b = r, c
                while 0 <= a < H and 0 <= b < W and g[a][b] == open_col:
                    cells.append((a, b))
                    a += dr
                    b += dc
                runs.append(cells)
    return runs


def _line_dist(run, H, W):
    """Distance (in diagonal-index units) of the run's full line from the grid centre."""
    (r0, c0), (r1, c1) = run[0], run[-1]
    cr, cc = (H - 1) / 2.0, (W - 1) / 2.0
    if len(run) > 1 and (c1 - c0) * (r1 - r0) < 0:  # anti-diagonal
        return abs((r0 + c0) - (cr + cc))
    return abs((r0 - c0) - (cr - cc))


def _apply(g, open_col, mark, tie):
    runs = _runs(g, open_col)
    out = [list(r) for r in g]
    if not runs:
        return out
    H, W = len(g), len(g[0])
    m = max(len(x) for x in runs)
    best = [x for x in runs if len(x) == m]
    if tie == "centre":
        best.sort(key=lambda x: (_line_dist(x, H, W), x[0]))
        pick = best[0]
    else:  # middle of the tied runs in scan order
        pick = best[(len(best) - 1) // 2]
    for a, b in pick:
        out[a][b] = mark
    return out


def _learn(train):
    open_col = mark = None
    for p in train:
        g, o = p["input"], p["output"]
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return None
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] != o[r][c]:
                    if open_col is None:
                        open_col, mark = g[r][c], o[r][c]
                    elif (open_col, mark) != (g[r][c], o[r][c]):
                        return None
    if open_col is None:
        return None
    return open_col, mark


def fam(train):
    L = _learn(train)
    if L is None:
        return
    open_col, mark = L

    for tie in ("centre", "middle"):
        def fn(g, open_col=open_col, mark=mark, tie=tie):
            return _apply(g, open_col, mark, tie)

        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("longest_diagonal_run_tie_" + tie, 1, fn)


FAMILIES = [fam]
