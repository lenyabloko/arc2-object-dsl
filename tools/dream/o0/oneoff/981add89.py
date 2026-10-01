CARD = "981add89"
READING = ("Each non-background marker on the edge row shoots a line across the grid: background "
           "cells on that line take the marker colour, cells already of the marker colour become "
           "background, and cells of any other colour take the marker colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _lr(g):
    return [list(r[::-1]) for r in g]


def _ud(g):
    return [list(r) for r in g[::-1]]


_ORIENT = [
    ("top", lambda g: [list(r) for r in g], lambda g: [list(r) for r in g]),
    ("bottom", _ud, _ud),
    ("left", _T, _T),
    ("right", lambda g: _T(_lr(g)), lambda g: _lr(_T(g))),
]


def _core(g):
    bg = _bg(g)
    out = [list(r) for r in g]
    for j, m in enumerate(g[0]):
        if m == bg:
            continue
        for i in range(1, len(g)):
            out[i][j] = bg if g[i][j] == m else m
    return out


def _make(fwd, inv):
    def fn(g):
        return inv(_core(fwd(g)))
    return fn


def fam(train):
    for name, fwd, inv in _ORIENT:
        fn = _make(fwd, inv)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("edge_marker_xor_lines_" + name, 1.0, fn)
        except Exception:
            pass


FAMILIES = [fam]
