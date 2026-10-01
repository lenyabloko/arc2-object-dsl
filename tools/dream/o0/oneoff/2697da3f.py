CARD = "2697da3f"
READING = "Crop the shape and place it as the left arm of a square of side 2w+h, then add its three 90-degree rotations about the centre to form a four-fold rotationally symmetric cross."


def _crop(g):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != 0]
    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _rot_cw(m):
    h, w = len(m), len(m[0])
    return [[m[h - 1 - c][r] for c in range(h)] for r in range(w)]


def _make(pre_rot):
    def fn(g):
        s = _crop(g)
        for _ in range(pre_rot):
            s = _rot_cw(s)
        h, w = len(s), len(s[0])
        N = 2 * w + h
        out = [[0] * N for _ in range(N)]
        for r in range(h):
            for c in range(w):
                if s[r][c]:
                    out[w + r][c] = s[r][c]
        res = [row[:] for row in out]
        cur = out
        for _ in range(3):
            cur = _rot_cw(cur)
            for r in range(N):
                for c in range(N):
                    if cur[r][c]:
                        res[r][c] = cur[r][c]
        return res
    return fn


def fam(train):
    names = ["left_arm", "left_arm_rot90", "left_arm_rot180", "left_arm_rot270"]
    for k in range(4):
        fn = _make(k)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("rot4_cross_" + names[k], 1 + k, fn)
        except Exception:
            pass


FAMILIES = [fam]
