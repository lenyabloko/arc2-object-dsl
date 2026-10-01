CARD = "27a28665"
READING = "The output is a 1x1 cell whose colour is determined by the shape (binary mask) of the coloured cells, looked up from the training pairs."


def _mask(g):
    return tuple(tuple(1 if v else 0 for v in r) for r in g)


def _d8(m):
    out = []
    a = [list(r) for r in m]
    for _ in range(4):
        a = [list(r) for r in zip(*a[::-1])]
        out.append(tuple(tuple(r) for r in a))
        out.append(tuple(tuple(r[::-1]) for r in a))
    return out


def fam(train):
    table = {}
    for p in train:
        m = _mask(p['input']); o = p['output']
        if table.get(m, o) != o:
            return
        table[m] = o
    # symmetry-closed table (only if consistent)
    sym = {}
    ok = True
    for m, o in table.items():
        for mm in _d8(m):
            if sym.get(mm, o) != o:
                ok = False
            sym[mm] = o

    def f_exact(g):
        m = _mask(g)
        if m in table:
            return [list(r) for r in table[m]]
        if ok and m in sym:
            return [list(r) for r in sym[m]]
        # nearest mask by Hamming distance
        best = min(table, key=lambda k: sum(a != b for ra, rb in zip(k, m) for a, b in zip(ra, rb)) if len(k) == len(m) else 10 ** 9)
        return [list(r) for r in table[best]]
    yield ('mask_lookup', 1, f_exact)


FAMILIES = [fam]
