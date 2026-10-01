CARD = "b5bb5719"
READING = ("Below the seeded top row, each row is grown downward: a cell becomes coloured when both "
           "of its upper diagonal neighbours are coloured, its colour given by the pair rule learned "
           "from training (equal pair -> the other colour, unequal pair -> the right one).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _learn(train):
    table = {}
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return None
        bg = _bg(gi)
        H, W = len(go), len(go[0])
        for r in range(1, H):
            for c in range(W):
                if gi[r][c] != bg:
                    continue
                a = go[r - 1][c - 1] if c - 1 >= 0 else bg
                b = go[r - 1][c + 1] if c + 1 < W else bg
                if a == bg or b == bg:
                    continue
                k = (a, b)
                if table.get(k, go[r][c]) != go[r][c]:
                    return None
                table[k] = go[r][c]
    return table


def _make(table):
    cols = set()
    for (a, b), v in table.items():
        cols |= {a, b, v}

    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        for r in range(1, H):
            for c in range(1, W - 1):
                if out[r][c] != bg:
                    continue
                a, b = out[r - 1][c - 1], out[r - 1][c + 1]
                if a == bg or b == bg:
                    continue
                if (a, b) in table:
                    out[r][c] = table[(a, b)]
                elif a == b:
                    others = sorted(cols - {a})
                    if len(others) == 1:
                        out[r][c] = others[0]
                else:
                    out[r][c] = b
        return out
    return fn


def fam(train):
    table = _learn(train)
    if not table:
        return
    fn = _make(table)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("diag_pair_growth", 1.0, fn)


FAMILIES = [fam]
