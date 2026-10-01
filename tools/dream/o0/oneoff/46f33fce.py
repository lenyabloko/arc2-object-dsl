CARD = "46f33fce"
READING = ("Each coloured cell sits on a sparse lattice (every second row/column); the lattice is "
           "compressed to a small grid and every cell is blown up into a k-by-k block.")


def _sample(g, s, o):
    return [row[o::s] for row in g[o::s]]


def _up(g, k):
    out = []
    for row in g:
        r = []
        for x in row:
            r.extend([x] * k)
        for _ in range(k):
            out.append(list(r))
    return out


def _make(s, o, k):
    def fn(g):
        return _up(_sample(g, s, o), k)
    return fn


def fam(train):
    found = []
    for s in (1, 2, 3):
        for o in range(s):
            for k in range(1, 7):
                fn = _make(s, o, k)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    found.append(("lattice_s%d_o%d_up%d" % (s, o, k), s + k, fn))
    found.sort(key=lambda t: t[1])
    for f in found[:3]:
        yield f


FAMILIES = [fam]
