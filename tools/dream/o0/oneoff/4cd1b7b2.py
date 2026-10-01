CARD = "4cd1b7b2"
READING = "Fill the holes so the grid becomes a Latin square: every row and every column contains each symbol exactly once."


def _hole_and_symbols(train):
    hole = None
    syms = set()
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        outs = set(x for r in p["output"] for x in r)
        missing = ins - outs
        if len(missing) != 1:
            return None, None
        h = next(iter(missing))
        if hole is None:
            hole = h
        elif hole != h:
            return None, None
        syms |= outs
    return hole, syms


def _make(hole, train_syms):
    def fn(g):
        n = len(g)
        if any(len(r) != n for r in g):
            return None
        syms = sorted(set(x for r in g for x in r if x != hole))
        if len(syms) < n:
            extra = sorted(s for s in train_syms if s not in syms)
            syms = sorted(syms + extra[: n - len(syms)])
        if len(syms) != n:
            return None
        out = [list(r) for r in g]
        empties = [(i, j) for i in range(n) for j in range(n) if out[i][j] == hole]
        rowu = [set(x for x in out[i] if x != hole) for i in range(n)]
        colu = [set(out[i][j] for i in range(n) if out[i][j] != hole) for j in range(n)]

        def bt(k):
            if k == len(empties):
                return True
            # choose most constrained empty cell
            best = None
            bestc = None
            for idx in range(k, len(empties)):
                i, j = empties[idx]
                c = [s for s in syms if s not in rowu[i] and s not in colu[j]]
                if best is None or len(c) < len(bestc):
                    best, bestc = idx, c
                    if len(c) <= 1:
                        break
            empties[k], empties[best] = empties[best], empties[k]
            i, j = empties[k]
            for s in bestc:
                out[i][j] = s
                rowu[i].add(s); colu[j].add(s)
                if bt(k + 1):
                    return True
                rowu[i].discard(s); colu[j].discard(s)
            out[i][j] = hole
            empties[k], empties[best] = empties[best], empties[k]
            return False

        return out if bt(0) else None
    return fn


def fam(train):
    hole, syms = _hole_and_symbols(train)
    if hole is None:
        return
    fn = _make(hole, syms)
    try:
        ok = all(fn(p["input"]) == p["output"] for p in train)
    except Exception:
        ok = False
    if ok:
        yield ("latin_square_fill", 1, fn)


FAMILIES = [fam]
