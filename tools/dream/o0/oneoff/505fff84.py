CARD = "505fff84"
READING = ("Every row that contains a start-marker colour followed later by an end-marker colour "
           "contributes the cells strictly between the two markers, stacked top to bottom.")


def _colors(train):
    cs = set()
    for p in train:
        for r in p["input"]:
            cs.update(r)
    return sorted(cs)


def _make(a, b, axis):
    def fn(g):
        rows = g if axis == 0 else [list(c) for c in zip(*g)]
        out = []
        for r in rows:
            if a in r:
                i = r.index(a)
                if b in r[i + 1:]:
                    j = r.index(b, i + 1)
                    out.append(list(r[i + 1:j]))
        if not out:
            return None
        if axis == 1:
            out = [list(c) for c in zip(*out)]
        return out
    return fn


def fam(train):
    cs = _colors(train)
    for axis in (0, 1):
        for a in cs:
            for b in cs:
                if a == b:
                    continue
                fn = _make(a, b, axis)
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
                    yield ("between_markers_%d_%d_ax%d" % (a, b, axis), 2, fn)


FAMILIES = [fam]
