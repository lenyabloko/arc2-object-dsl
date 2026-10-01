CARD = "d07ae81c"
READING = ("From every isolated seed cell draw both full diagonals across the grid, colouring each crossed "
           "cell with the seed colour that belongs to that cell's background region colour.")


def _analyse(g):
    H, W = len(g), len(g[0])
    region = set()
    for r in range(H):
        for c in range(W):
            for dr, dc in ((1, 0), (0, 1)):
                rr, cc = r + dr, c + dc
                if rr < H and cc < W and g[rr][cc] == g[r][c]:
                    region.add(g[r][c])
    seeds = [(r, c) for r in range(H) for c in range(W) if g[r][c] not in region]
    mapping = {}
    for r, c in seeds:
        cnt = {}
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if (dr or dc) and 0 <= rr < H and 0 <= cc < W and g[rr][cc] in region:
                    cnt[g[rr][cc]] = cnt.get(g[rr][cc], 0) + 1
        if cnt:
            reg = max(sorted(cnt), key=lambda k: cnt[k])
            mapping.setdefault(reg, g[r][c])
    return region, seeds, mapping


def _apply(g):
    H, W = len(g), len(g[0])
    region, seeds, mapping = _analyse(g)
    out = [list(r) for r in g]
    for r, c in seeds:
        for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            rr, cc = r + dr, c + dc
            while 0 <= rr < H and 0 <= cc < W:
                v = g[rr][cc]
                if v in mapping:
                    out[rr][cc] = mapping[v]
                rr += dr
                cc += dc
    return out


def fam(train):
    try:
        if all(_apply(p["input"]) == p["output"] for p in train):
            yield ("seed_diagonals_regionmap", 1, _apply)
    except Exception:
        return


FAMILIES = [fam]
