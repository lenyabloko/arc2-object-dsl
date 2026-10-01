CARD = "50f325b5"
READING = ("The single shape drawn in the template colour is searched for, in any rotation, among cells of the source colour, and every match is repainted in the "
           "template colour.")


def _syms(cells, mode):
    # mode: 0 identity only, 1 rotations, 2 rotations + reflections
    res = []
    ks = {0: [0], 1: [0, 1, 2, 3], 2: list(range(8))}[mode]
    for k in ks:
        pts = []
        for a, b in cells:
            for _ in range(k & 3):
                a, b = b, -a
            if k & 4:
                a, b = b, a
            pts.append((a, b))
        ma = min(p[0] for p in pts); mb = min(p[1] for p in pts)
        s = tuple(sorted((a - ma, b - mb) for a, b in pts))
        if s not in res:
            res.append(s)
    return res


def _make(src, tmpl, mode):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == tmpl]
        if not cells:
            return [list(r) for r in g]
        variants = _syms(cells, mode)
        out = [list(r) for r in g]
        for v in variants:
            mh = max(a for a, _ in v); mw = max(b for _, b in v)
            for i in range(H - mh):
                for j in range(W - mw):
                    if all(g[i + a][j + b] == src for a, b in v):
                        for a, b in v:
                            out[i + a][j + b] = tmpl
        return out
    return fn


def fam(train):
    pairs = set()
    for p in train:
        gi, go = p["input"], p["output"]
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    pairs.add((a, b))
    if len(pairs) != 1:
        return
    src, tmpl = next(iter(pairs))
    for mode, name in ((1, "rotations"), (2, "dihedral"), (0, "identity")):
        fn = _make(src, tmpl, mode)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("template_match_%s" % name, 1 + mode, fn)


FAMILIES = [fam]
