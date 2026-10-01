CARD = "22233c11"
READING = ("Each object made of two equal squares touching at a corner gets two new squares of the same size "
           "added diagonally outside the two empty corners of its bounding box, in the marker colour.")
from collections import Counter


def _bg(train):
    c = Counter()
    for p in train:
        for row in p["input"]:
            c.update(row)
    return c.most_common(1)[0][0]


def _new_colour(train):
    cols = set()
    for p in train:
        a = {v for r in p["input"] for v in r}
        b = {v for r in p["output"] for v in r}
        cols |= (b - a)
    return cols.pop() if len(cols) == 1 else None


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            col = g[r][c]
            stack = [(r, c)]
            seen[r][c] = True
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            out.append(cells)
    return out


def _make(bg, mark, gap):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        for cells in _components(g, bg):
            rs = [y for y, _ in cells]
            cs = [x for _, x in cells]
            r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
            h, w = r1 - r0 + 1, c1 - c0 + 1
            if h != w or h % 2:
                continue
            s = h // 2
            cs_set = set(cells)
            if len(cells) != 2 * s * s:
                continue
            main = (r0, c0) in cs_set
            if main:
                blocks = [(r0 - s - gap, c1 + 1 + gap), (r1 + 1 + gap, c0 - s - gap)]
            else:
                blocks = [(r0 - s - gap, c0 - s - gap), (r1 + 1 + gap, c1 + 1 + gap)]
            for br, bc in blocks:
                for y in range(br, br + s):
                    for x in range(bc, bc + s):
                        if 0 <= y < H and 0 <= x < W and out[y][x] == bg:
                            out[y][x] = mark
        return out
    return fn


def fam(train):
    bg = _bg(train)
    mark = _new_colour(train)
    if mark is None:
        return
    for gap in (0, 1, 2):
        fn = _make(bg, mark, gap)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("diag_pair_corner_blocks_gap%d" % gap, 1 + gap, fn)
        except Exception:
            pass


FAMILIES = [fam]
