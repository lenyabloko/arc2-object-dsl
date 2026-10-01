CARD = "456873bc"
READING = ("The pattern is a self-similar fractal (tile T placed, with one-cell gaps, at the positions of T's own "
           "cells); the occluding block is replaced by the reconstructed fractal and the cell of block (i,j) at "
           "relative position (i,j) is marked with the new colour wherever it is filled.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(mask_col, mark_col):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = {}
        for r in g:
            for x in r:
                if x != mask_col:
                    cnt[x] = cnt.get(x, 0) + 1
        bg = max(cnt, key=lambda k: cnt[k])
        fgs = [c for c in cnt if c != bg]
        if len(fgs) != 1:
            return None
        fg = fgs[0]

        best = None
        for h in range(1, H):
            if best:
                break
            if any(g[r][c] not in (bg, mask_col) for r in range(h, H, h + 1) for c in range(W)):
                continue
            for w in range(1, W):
                if any(g[r][c] not in (bg, mask_col) for c in range(w, W, w + 1) for r in range(H)):
                    continue
                blocks = {}
                for r0 in range(0, H, h + 1):
                    for c0 in range(0, W, w + 1):
                        if r0 + h > H or c0 + w > W:
                            continue
                        blk = tuple(tuple(g[r0 + i][c0 + j] for j in range(w)) for i in range(h))
                        if any(x == mask_col for row in blk for x in row):
                            continue
                        if all(x == bg for row in blk for x in row):
                            continue
                        key = tuple(tuple(1 if x == fg else 0 for x in row) for row in blk)
                        blocks[key] = blocks.get(key, 0) + 1
                if not blocks:
                    continue
                T = max(blocks, key=lambda k: blocks[k])
                if all(not v for row in T for v in row):
                    continue
                res = _build(g, T, bg, fg, mask_col, mark_col)
                if res is not None:
                    best = res
                    break
        return best
    return fn


def _build(g, T, bg, fg, mask_col, mark_col):
        H, W = len(g), len(g[0])
        h, w = len(T), len(T[0])
        out = [[bg] * W for _ in range(H)]
        for r in range(H):
            bi, ri = divmod(r, h + 1)
            if ri == h or bi >= h:
                continue
            for c in range(W):
                bj, rj = divmod(c, w + 1)
                if rj == w or bj >= w:
                    continue
                if T[bi][bj] and T[ri][rj]:
                    out[r][c] = mark_col if (ri, rj) == (bi, bj) else fg
        # reconstruction must agree with every visible (non-mask) cell, up to the marks
        for r in range(H):
            for c in range(W):
                if g[r][c] == mask_col:
                    continue
                v = fg if out[r][c] == mark_col else out[r][c]
                if v != g[r][c]:
                    return None
        return out


def fam(train):
    ins = set()
    outs = set()
    for p in train:
        for r in p["input"]:
            ins.update(r)
        for r in p["output"]:
            outs.update(r)
    gone = sorted(ins - outs)
    new = sorted(outs - ins)
    for m in gone:
        for k in new:
            fn = _make(m, k)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("self_similar_fractal_fill_mark", 1.0, fn)


FAMILIES = [fam]
