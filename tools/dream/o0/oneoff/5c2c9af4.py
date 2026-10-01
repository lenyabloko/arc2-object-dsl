CARD = "5c2c9af4"
READING = ("Three equally spaced diagonal dots define a centre (the middle dot) and a step; draw "
           "concentric square rings around the centre at every multiple of that step, clipped to the grid.")


def _rings(g):
    H, W = len(g), len(g[0])
    pts = [(i, j) for i in range(H) for j in range(W) if g[i][j] != 0]
    if len(pts) < 2:
        return None
    col = g[pts[0][0]][pts[0][1]]
    pts.sort()
    cr = sum(p[0] for p in pts) / len(pts)
    cc = sum(p[1] for p in pts) / len(pts)
    if cr != int(cr) or cc != int(cc):
        return None
    cr, cc = int(cr), int(cc)
    d = max(abs(pts[0][0] - cr), abs(pts[0][1] - cc))
    if d == 0:
        return None
    return [[col if max(abs(i - cr), abs(j - cc)) % d == 0 else 0 for j in range(W)] for i in range(H)]


def fam(train):
    try:
        if all(_rings(p["input"]) == p["output"] for p in train):
            yield "concentric_square_rings", 1, _rings
    except Exception:
        pass


FAMILIES = [fam]
