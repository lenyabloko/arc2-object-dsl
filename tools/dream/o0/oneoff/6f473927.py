CARD = "6f473927"
READING = ("The grid is extended sideways by its left-right mirror image with colours swapped by a learned "
           "map (background->new colour, shape->background), placed on the side where the shape touches the "
           "border.")


def _side(g):
    left = sum(1 for r in g if r[0] != 0)
    right = sum(1 for r in g if r[-1] != 0)
    return "left" if left > right else "right"


def _learn_map(train):
    cmap = {}
    for p in train:
        g, o = p["input"], p["output"]
        H, W = len(g), len(g[0])
        if len(o) != H or len(o[0]) != 2 * W:
            return None
        side = _side(g)
        half = [r[:W] for r in o] if side == "left" else [r[W:] for r in o]
        for i in range(H):
            for j in range(W):
                a = g[i][W - 1 - j]
                b = half[i][j]
                if cmap.setdefault(a, b) != b:
                    return None
    return cmap


def fam(train):
    cmap = _learn_map(train)
    if cmap is None:
        return

    def fn(g):
        W = len(g[0])
        out = []
        for r in g:
            m = [cmap.get(x, x) for x in r[::-1]]
            out.append(m + list(r) if _side(g) == "left" else list(r) + m)
        return out

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("mirror_recolour_on_touching_side", 1, fn)


FAMILIES = [fam]
