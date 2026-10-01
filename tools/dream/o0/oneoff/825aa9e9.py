CARD = "825aa9e9"
READING = "Loose shapes fall toward the ground (the colours touching the bottom edge) and stop one empty row short of it, while shapes landing on other fallen shapes stack directly on them."

from collections import Counter


def _comps(g, cells_ok):
    H, W = len(g), len(g[0])
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or not cells_ok(r, c):
                continue
            col = g[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen \
                            and cells_ok(ny, nx) and g[ny][nx] == col:
                        seen.add((ny, nx))
                        stack.append((ny, nx))
            comps.append(comp)
    return comps


def _rot(g, k):
    for _ in range(k):
        g = [list(row) for row in zip(*g[::-1])]
    return g


def _fall_down(g, bg, gap):
    H, W = len(g), len(g[0])
    ground_cols = set(v for v in g[H - 1] if v != bg)
    terrain = set((r, c) for r in range(H) for c in range(W) if g[r][c] in ground_cols)
    comps = _comps(g, lambda r, c: g[r][c] != bg and g[r][c] not in ground_cols)
    out = [[bg if (r, c) not in terrain else g[r][c] for c in range(W)] for r in range(H)]
    placed = set()
    comps.sort(key=lambda cm: -max(r for r, _ in cm))
    for cm in comps:
        cmset = set(cm)
        d = 0
        while True:
            nd = d + 1
            ok = True
            for (r, c) in cm:
                nr = r + nd
                # cell itself must be free
                if nr >= H or (nr, c) in terrain or (nr, c) in placed:
                    ok = False
                    break
                # keep `gap` empty rows above terrain / bottom edge
                for k in range(1, gap + 1):
                    rr = nr + k
                    if rr >= H or (rr, c) in terrain:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
            d = nd
        for (r, c) in cm:
            out[r + d][c] = g[r][c]
            placed.add((r + d, c))
    return out


def _make(bg, gap, k):
    def fn(g):
        gg = _rot(g, k)
        res = _fall_down(gg, bg, gap)
        return _rot(res, (4 - k) % 4)
    return fn


def _bg_candidates(train):
    common = None
    for p in train:
        s = set(v for row in p["input"] for v in row)
        common = s if common is None else common & s
    tot = Counter(v for p in train for row in p["input"] for v in row)
    return sorted(common or [], key=lambda v: -tot[v])


def fam(train):
    for bg in _bg_candidates(train):
        for gap in (0, 1, 2):
            for k in (0, 1, 2, 3):
                fn = _make(bg, gap, k)
                try:
                    if all(fn(p["input"]) == p["output"] for p in train):
                        yield ("fall_bg%d_gap%d_rot%d" % (bg, gap, k), 1 + gap + k, fn)
                except Exception:
                    pass


FAMILIES = [fam]
