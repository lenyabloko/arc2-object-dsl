CARD = "9f669b64"
READING = ("The small block lying between the base shape and the rectangular wall is shot away from "
           "the base to the grid edge, splitting the wall at its line so each half slides sideways "
           "just clear of the block's path.")

from itertools import permutations


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _objs(g, bg):
    d = {}
    for i, r in enumerate(g):
        for j, x in enumerate(r):
            if x != bg:
                d.setdefault(x, []).append((i, j))
    out = []
    for c, cells in d.items():
        rs = [a for a, b in cells]; cs = [b for a, b in cells]
        out.append({"c": c, "cells": cells, "r0": min(rs), "r1": max(rs), "c0": min(cs), "c1": max(cs)})
    return out


def _span(o, ax):
    # ax=0: motion along rows (vertical); returns (along0, along1, perp0, perp1)
    if ax == 0:
        return o["r0"], o["r1"], o["c0"], o["c1"]
    return o["c0"], o["c1"], o["r0"], o["r1"]


def _layout(objs):
    for p, a, b in permutations(objs, 3):
        for ax in (0, 1):
            pa0, pa1, pp0, pp1 = _span(p, ax)
            aa0, aa1, ap0, ap1 = _span(a, ax)
            ba0, ba1, bp0, bp1 = _span(b, ax)
            if not (ap0 <= pp1 and pp0 <= ap1 and bp0 <= pp1 and pp0 <= bp1):
                continue
            if aa1 < pa0 and pa1 < ba0:
                return p, a, b, ax
    return None


def _is_wall(o, p, ax):
    _, _, op0, op1 = _span(o, ax)
    _, _, pp0, pp1 = _span(p, ax)
    rect = len(o["cells"]) == (o["r1"] - o["r0"] + 1) * (o["c1"] - o["c0"] + 1)
    return (rect and (op1 - op0) > (pp1 - pp0), op1 - op0)


def fn(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    objs = _objs(g, bg)
    if len(objs) != 3:
        return [list(r) for r in g]
    lay = _layout(objs)
    if lay is None:
        return [list(r) for r in g]
    p, a, b, ax = lay
    # a is before p along the axis, b after; pick wall
    if _is_wall(a, p, ax) > _is_wall(b, p, ax):
        wall, sign = a, -1
    else:
        wall, sign = b, 1
    L = H if ax == 0 else W
    pa0, pa1, pp0, pp1 = _span(p, ax)
    shift = (L - 1 - pa1) if sign > 0 else -pa0
    pc2 = pp0 + pp1  # twice the centre
    out = [list(r) for r in g]
    for (i, j) in p["cells"] + wall["cells"]:
        out[i][j] = bg
    lo = [(i, j) for (i, j) in wall["cells"] if 2 * (j if ax == 0 else i) < pc2]
    hi = [(i, j) for (i, j) in wall["cells"] if 2 * (j if ax == 0 else i) >= pc2]
    k = (lambda c: c[1]) if ax == 0 else (lambda c: c[0])
    if lo:
        s = (pp0 - 1) - max(k(c) for c in lo)
        for (i, j) in lo:
            ni, nj = (i, j + s) if ax == 0 else (i + s, j)
            if 0 <= ni < H and 0 <= nj < W:
                out[ni][nj] = wall["c"]
    if hi:
        s = (pp1 + 1) - min(k(c) for c in hi)
        for (i, j) in hi:
            ni, nj = (i, j + s) if ax == 0 else (i + s, j)
            if 0 <= ni < H and 0 <= nj < W:
                out[ni][nj] = wall["c"]
    for (i, j) in p["cells"]:
        ni, nj = (i + shift, j) if ax == 0 else (i, j + shift)
        out[ni][nj] = p["c"]
    return out


def fam(train):
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("shoot_block_through_split_wall", 1.0, fn)


FAMILIES = [fam]
