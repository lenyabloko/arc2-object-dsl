CARD = "fc754716"
READING = ("The single coloured cell is erased and its colour is drawn as a one-cell frame around "
           "the border of the grid.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _frame(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    others = [x for r in g for x in r if x != bg]
    col = others[0] if others else bg
    return [[col if (r in (0, H - 1) or c in (0, W - 1)) else bg for c in range(W)] for r in range(H)]


def fam(train):
    try:
        if all(_frame(p["input"]) == p["output"] for p in train):
            yield ("border_frame", 1, _frame)
    except Exception:
        pass


FAMILIES = [fam]
