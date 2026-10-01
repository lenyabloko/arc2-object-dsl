CARD = "5ecac7f7"
READING = ("Separator columns cut the grid into K equal panels; output column j is copied from panel "
           "floor((j+0.5)*K/w), i.e. left third from the first panel, middle from the second, right from the third.")


def _panels(g):
    H, W = len(g), len(g[0])
    for s in sorted({g[0][j] for j in range(W)}):
        seps = [j for j in range(W) if all(g[i][j] == s for i in range(H))]
        if not seps:
            continue
        spans, prev = [], -1
        for k in seps + [W]:
            if k - prev > 1:
                spans.append((prev + 1, k))
            prev = k
        if len(spans) >= 2 and len({b - a for a, b in spans}) == 1:
            return spans
    return None


def _make(rule):
    def fn(g):
        sp = _panels(g)
        if sp is None:
            return None
        K, w = len(sp), sp[0][1] - sp[0][0]
        out = []
        for i in range(len(g)):
            row = []
            for j in range(w):
                p = rule(j, w, K)
                row.append(g[i][sp[p][0] + j])
            out.append(row)
        return out
    return fn


def _prop(j, w, K):
    return min(K - 1, (2 * j + 1) * K // (2 * w))


def fam(train):
    for name, cost, rule in (("proportional_panel_columns", 1, _prop),):
        fn = _make(rule)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield name, cost, fn
        except Exception:
            pass


FAMILIES = [fam]
