CARD = "984d8a3e"
READING = ("Each row reads left colour, middle colour, right colour; every middle-colour run is slid "
           "left (as far as the grid edge allows) so its right end lines up with the leftmost right "
           "end among all rows, and the left-colour cells it passes over move to just after it.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _lr(g):
    return [list(r[::-1]) for r in g]


def _mode(vals):
    cnt = {}
    for x in vals:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


_ORIENT = [
    ("left", lambda g: [list(r) for r in g], lambda g: [list(r) for r in g]),
    ("right", _lr, _lr),
    ("top", _T, _T),
    ("bottom", lambda g: _lr(_T(g)), lambda g: _T(_lr(g))),
]


def _core(g):
    W = len(g[0])
    A = _mode([r[0] for r in g])
    C = _mode([r[-1] for r in g])
    if A == C:
        return None
    parsed = []
    for r in g:
        i = 0
        while i < W and r[i] == A:
            i += 1
        j = i
        while j < W and r[j] != C:
            j += 1
        parsed.append((i, j))
    T = min(j for i, j in parsed)
    out = []
    for r, (i, j) in zip(g, parsed):
        b = j - i
        st = max(0, T - b)
        if st > i:
            st = i
        out.append([A] * st + list(r[i:j]) + [A] * (i - st) + list(r[j:]))
    return out


def _make(fwd, inv):
    def fn(g):
        r = _core(fwd(g))
        if r is None:
            return [list(x) for x in g]
        return inv(r)
    return fn


def fam(train):
    for name, fwd, inv in _ORIENT:
        fn = _make(fwd, inv)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("align_middle_run_to_min_end_" + name, 1.0, fn)
        except Exception:
            pass


FAMILIES = [fam]
