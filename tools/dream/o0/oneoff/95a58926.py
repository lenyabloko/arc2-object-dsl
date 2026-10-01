CARD = "95a58926"
READING = ("Erase the scattered noise and redraw the full grid lines in the line colour, "
           "painting every line crossing with the noise colour.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _make(mode):
    # mode 0: a line row/col contains no background; mode 1: background is a minority
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        bg = max(cnt, key=lambda k: cnt[k])
        others = sorted((k for k in cnt if k != bg), key=lambda k: (-cnt[k], k))
        line = others[0]
        noise = others[1] if len(others) > 1 else line

        def is_line(cells):
            nb = sum(1 for x in cells if x == bg)
            return nb == 0 if mode == 0 else 2 * nb < len(cells)

        rows = [i for i in range(H) if is_line(g[i])]
        cols = [j for j in range(W) if is_line([g[i][j] for i in range(H)])]
        out = [[bg] * W for _ in range(H)]
        for i in rows:
            for j in range(W):
                out[i][j] = line
        for j in cols:
            for i in range(H):
                out[i][j] = line
        for i in rows:
            for j in cols:
                out[i][j] = noise
        return out
    return fn


def fam(train):
    for name, cost, fn in (("gridlines_nobg", 1, _make(0)), ("gridlines_majority", 2, _make(1))):
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
