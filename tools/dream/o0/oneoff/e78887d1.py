CARD = "e78887d1"
READING = ("The input is a stack of strips of coloured glyphs, each slot keeping its colour while the "
           "shapes rotate one slot left from strip to strip; the output is the next strip, i.e. the last "
           "strip with every shape moved one slot left (cyclically) and recoloured to its new slot.")


def _strip_h(g):
    H = len(g)
    for h in range(1, H):
        if (H - 1) % (h + 1):
            continue
        k = (H - 1) // (h + 1)
        if all(not any(g[i * (h + 1)]) for i in range(k + 1)) and \
           all(any(any(g[r]) for r in range(i * (h + 1) + 1, (i + 1) * (h + 1))) for i in range(k)):
            return h, k
    return None


def _slot_w(g):
    W = len(g[0])
    best = None
    for w in range(1, W + 1):
        if (W + 1) % (w + 1):
            continue
        n = (W + 1) // (w + 1)
        if any(any(g[i][s * (w + 1) - 1] for i in range(len(g))) for s in range(1, n)):
            continue
        ok = True
        for s in range(n):
            cs = {g[i][j] for i in range(len(g)) for j in range(s * (w + 1), s * (w + 1) + w)} - {0}
            if len(cs) != 1:
                ok = False
                break
        if ok:
            best = (w, n)
            break
    return best


def _make(direction):
    def fn(g):
        sh = _strip_h(g)
        sw = _slot_w(g)
        if sh is None or sw is None:
            return [list(r) for r in g]
        h, k = sh
        w, n = sw
        top = (k - 1) * (h + 1) + 1
        strip = [g[top + r] for r in range(h)]
        colours = []
        shapes = []
        for s in range(n):
            c0 = s * (w + 1)
            cs = {strip[r][c0 + c] for r in range(h) for c in range(w)} - {0}
            colours.append(cs.pop() if cs else 0)
            shapes.append([[1 if strip[r][c0 + c] else 0 for c in range(w)] for r in range(h)])
        out = [[0] * len(g[0]) for _ in range(h)]
        for s in range(n):
            src = shapes[(s + direction) % n]
            c0 = s * (w + 1)
            for r in range(h):
                for c in range(w):
                    if src[r][c]:
                        out[r][c0 + c] = colours[s]
        return out
    return fn


def fam(train):
    for name, d in (("shift_shapes_left", 1), ("shift_shapes_right", -1)):
        fn = _make(d)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1.0, fn)
        except Exception:
            pass


FAMILIES = [fam]
