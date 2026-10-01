CARD = "782b5218"
READING = ("A wall of one colour crosses the grid; in every column everything above the "
           "wall's top cell is erased to background and everything below it (except wall "
           "cells) is flooded with the grid's other colour.")


def _rot(g):
    # rotate clockwise
    return [list(r) for r in zip(*g[::-1])]


def _rot_k(g, k):
    for _ in range(k % 4):
        g = _rot(g)
    return g


def _make(bg, wall, k):
    def fn(g):
        h = _rot_k(g, k)
        H, W = len(h), len(h[0])
        cols = set(v for row in h for v in row) - {bg, wall}
        if len(cols) != 1:
            return None
        fill = cols.pop()
        out = [[bg] * W for _ in range(H)]
        for c in range(W):
            seen = False
            for r in range(H):
                v = h[r][c]
                if v == wall:
                    seen = True
                    out[r][c] = wall
                elif seen:
                    out[r][c] = fill
        return _rot_k(out, (4 - k) % 4)
    return fn


def fam(train):
    ins = [p["input"] for p in train]
    common = set(range(10))
    for g in ins:
        common &= set(v for row in g for v in row)
    found = []
    for bg in sorted(common):
        for wall in sorted(common):
            if wall == bg:
                continue
            for k in range(4):
                fn = _make(bg, wall, k)
                try:
                    if all(fn(p["input"]) == p["output"] for p in train):
                        found.append(("wall_shadow_bg%d_w%d_r%d" % (bg, wall, k), 1 + k, fn))
                except Exception:
                    pass
    found.sort(key=lambda t: t[1])
    for f in found[:3]:
        yield f


FAMILIES = [fam]
