CARD = "9caba7c3"
READING = ("Each solid 3x3 window (no background cells) whose centre is filler and whose ring holds "
           "marker cells is chosen greedily by most markers without overlapping; its centre is "
           "recoloured to one new colour and its non-marker ring cells to another.")

from itertools import permutations


def _colors(g):
    s = set()
    for r in g:
        s.update(r)
    return s


def _make(bg, fill, mark, cc, rc):
    def fn(g):
        H, W = len(g), len(g[0])
        cands = []
        for i in range(1, H - 1):
            for j in range(1, W - 1):
                if g[i][j] != fill:
                    continue
                win = [g[i + a][j + b] for a in (-1, 0, 1) for b in (-1, 0, 1)]
                if bg in win:
                    continue
                n = win.count(mark)
                if n:
                    cands.append((-n, i, j))
        cands.sort()
        chosen = []
        for n, i, j in cands:
            if all(abs(i - a) > 2 or abs(j - b) > 2 for a, b in chosen):
                chosen.append((i, j))
        out = [list(r) for r in g]
        for i, j in chosen:
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    if a == 0 and b == 0:
                        out[i][j] = cc
                    elif g[i + a][j + b] != mark:
                        out[i + a][j + b] = rc
        return out
    return fn


def fam(train):
    inc = set()
    newc = set()
    for p in train:
        ci = _colors(p["input"])
        inc |= ci
        newc |= _colors(p["output"]) - ci
    if len(inc) != 3 or len(newc) != 2:
        return
    found = 0
    for bg, fill, mark in permutations(sorted(inc)):
        for cc, rc in permutations(sorted(newc)):
            fn = _make(bg, fill, mark, cc, rc)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("greedy_ring_windows_%d%d%d_%d%d" % (bg, fill, mark, cc, rc), 1.0 + found, fn)
                found += 1
                if found >= 2:
                    return


FAMILIES = [fam]
