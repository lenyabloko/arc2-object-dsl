CARD = "98c475bf"
READING = ("The existing full-width line (with its colour's decoration) is erased, and every pair of "
           "edge markers becomes a full-width line of the marker colour carrying that colour's "
           "decoration, learned from the training grids, at the same relative rows and columns.")


def _mode(vals):
    cnt = {}
    for x in vals:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _analyse(g):
    """Return (border, bg, lines{colour:row}, markers[(colour,row)])."""
    H, W = len(g), len(g[0])
    border = g[0][0]
    if not all(g[i][0] == border and g[i][W - 1] == border for i in range(H)):
        return None
    inner = [g[i][j] for i in range(H) for j in range(1, W - 1)]
    bg = _mode(inner)
    cnt = {}
    for i in range(H):
        for j in range(1, W - 1):
            c = g[i][j]
            if c != bg:
                cnt[c] = cnt.get(c, 0) + 1
    lines, markers = {}, []
    for i in range(H):
        a, b = g[i][1], g[i][W - 2]
        if a == b and a != bg:
            rowcnt = sum(1 for j in range(1, W - 1) if g[i][j] == a)
            if rowcnt == 2 and cnt.get(a, 0) == 2 * sum(
                    1 for k in range(H) if g[k][1] == a and g[k][W - 2] == a):
                markers.append((a, i))
            else:
                lines[a] = i
    return border, bg, lines, markers


def _library(train):
    lib = {}
    for p in train:
        for g in (p["input"], p["output"]):
            an = _analyse(g)
            if an is None:
                continue
            _, bg, lines, _ = an
            W = len(g[0])
            for c, r in lines.items():
                cells = set()
                for i in range(len(g)):
                    for j in range(1, W - 1):
                        if g[i][j] == c:
                            cells.add((i - r, j))
                if c in lib and lib[c] != cells:
                    # keep the larger consistent description
                    if len(cells) <= len(lib[c]):
                        continue
                lib[c] = cells
    return lib


def _make(lib):
    def fn(g):
        an = _analyse(g)
        if an is None:
            return [list(r) for r in g]
        border, bg, lines, markers = an
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        for c in lines:
            for i in range(H):
                for j in range(1, W - 1):
                    if g[i][j] == c:
                        out[i][j] = bg
        for c, r in markers:
            for j in range(1, W - 1):
                out[r][j] = bg
        for c, r in markers:
            if c in lib:
                for di, j in lib[c]:
                    i = r + di
                    if 0 <= i < H and 1 <= j < W - 1:
                        out[i][j] = c
            else:
                for j in range(1, W - 1):
                    out[r][j] = c
        return out
    return fn


def fam(train):
    try:
        lib = _library(train)
        fn = _make(lib)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("markers_to_decorated_lines", 1.0, fn)
    except Exception:
        pass


FAMILIES = [fam]
