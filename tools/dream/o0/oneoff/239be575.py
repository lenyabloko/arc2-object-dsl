CARD = "239be575"
READING = ("Output a single cell: the path colour if the two blocks are joined by a connected chain of path-colour "
           "cells, otherwise the background colour.")
from collections import Counter


def _params(train):
    bgc = Counter()
    outc = set()
    inc = set()
    for p in train:
        for r in p["input"]:
            bgc.update(r)
            inc |= set(r)
        for r in p["output"]:
            outc |= set(r)
    bg = bgc.most_common(1)[0][0]
    path = [c for c in outc if c != bg]
    if len(path) != 1:
        return None
    path = path[0]
    block = [c for c in inc if c not in (bg, path)]
    if len(block) != 1:
        return None
    return bg, path, block[0]


def _make(bg, path, block, diag):
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

    def fn(g):
        H, W = len(g), len(g[0])
        # label block components (4-connected)
        lab = {}
        n = 0
        for r in range(H):
            for c in range(W):
                if g[r][c] == block and (r, c) not in lab:
                    st = [(r, c)]
                    lab[(r, c)] = n
                    while st:
                        y, x = st.pop()
                        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W and g[ny][nx] == block and (ny, nx) not in lab:
                                lab[(ny, nx)] = n
                                st.append((ny, nx))
                    n += 1
        # flood through path + block cells starting from block 0
        start = [k for k, v in lab.items() if v == 0]
        seen = set(start)
        st = list(start)
        reached = {0}
        while st:
            y, x = st.pop()
            for dy, dx in nb:
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen:
                    v = g[ny][nx]
                    if v == path:
                        seen.add((ny, nx)); st.append((ny, nx))
                    elif v == block and lab[(ny, nx)] not in reached:
                        # entering another block only counts if we came from a path cell
                        if g[y][x] == path:
                            k = lab[(ny, nx)]
                            reached.add(k)
                            for cell, l in lab.items():
                                if l == k:
                                    seen.add(cell); st.append(cell)
        ok = n >= 2 and len(reached) == n
        return [[path if ok else bg]]
    return fn


def fam(train):
    pr = _params(train)
    if pr is None:
        return
    for diag, name, cost in ((True, "blocks_linked_by_path_8conn", 1), (False, "blocks_linked_by_path_4conn", 2)):
        fn = _make(*pr, diag)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
