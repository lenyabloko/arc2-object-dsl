CARD = "5d588b4d"
READING = ("A bar of length n becomes the run sequence 1,2,..,n,..,2,1 of its colour, each run followed "
           "by one blank, written row-major into rows of the input width (as many rows as needed, zero-padded).")


def _seq(g):
    W = len(g[0])
    cells = [x for r in g for x in r if x != 0]
    if not cells:
        return None
    c, n = cells[0], len(cells)
    lens = list(range(1, n + 1)) + list(range(n - 1, 0, -1))
    s = []
    for k in lens:
        s += [c] * k + [0]
    h = -(-len(s) // W)
    s += [0] * (h * W - len(s))
    return [s[i * W:(i + 1) * W] for i in range(h)]


def fam(train):
    try:
        if all(_seq(p["input"]) == p["output"] for p in train):
            yield "pyramid_runs_rowmajor", 1, _seq
    except Exception:
        pass


FAMILIES = [fam]
