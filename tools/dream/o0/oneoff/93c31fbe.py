CARD = "93c31fbe"
READING = ("Each frame of four L-shaped corner brackets holds a half-pattern lying on one side of its centre line; "
           "the pattern is mirrored across that centre line to complete it, and all stray pixels outside the frames are erased.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            c = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == c:
                        seen[x][y] = True
                        st.append((x, y))
            out.append((c, cells))
    return out


def _corner(cells):
    if len(cells) != 3:
        return None
    r0 = min(a for a, _ in cells); c0 = min(b for _, b in cells)
    s = {(a - r0, b - c0) for a, b in cells}
    box = {(0, 0), (0, 1), (1, 0), (1, 1)}
    if not s <= box:
        return None
    miss = (box - s).pop()
    kind = {(1, 1): "TL", (1, 0): "TR", (0, 1): "BL", (0, 0): "BR"}[miss]
    return kind, r0, c0


def _frames(g, bg, avoid):
    comps = _comps(g, bg)
    bycol = {}
    for c, cells in comps:
        bycol.setdefault(c, []).append(cells)
    fcols = [c for c, L in bycol.items() if all(_corner(x) for x in L) and c not in avoid]
    if not fcols:
        fcols = [c for c, L in bycol.items() if all(_corner(x) for x in L)]
    corners = {}
    for c in fcols:
        for cells in bycol[c]:
            k, r0, c0 = _corner(cells)
            corners.setdefault((c, k), []).append((r0, c0))
    frames = []
    for c in fcols:
        for (r, q) in corners.get((c, "TL"), []):
            trs = sorted(x for x in corners.get((c, "TR"), []) if x[0] == r and x[1] > q)
            bls = sorted(x for x in corners.get((c, "BL"), []) if x[1] == q and x[0] > r)
            if not trs or not bls:
                continue
            q1 = trs[0][1] + 1
            r1 = bls[0][0] + 1
            frames.append((c, r, r1, q, q1))
    return frames, set(fcols)


def _make(avoid, mode):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        frames, fcols = _frames(g, bg, avoid)
        out = [[x if x in fcols else bg for x in r] for r in g]
        for (c, r0, r1, c0, c1) in frames:
            ir0, ir1, ic0, ic1 = r0 + 1, r1 - 1, c0 + 1, c1 - 1
            pix = [(i, j, g[i][j]) for i in range(ir0, ir1 + 1) for j in range(ic0, ic1 + 1)
                   if g[i][j] != bg and g[i][j] not in fcols]
            if not pix:
                continue
            sr, sc = ir0 + ir1, ic0 + ic1
            vert = all(2 * i < sr for i, _, _ in pix) or all(2 * i > sr for i, _, _ in pix)
            horz = all(2 * j < sc for _, j, _ in pix) or all(2 * j > sc for _, j, _ in pix)
            if mode == "one" and vert and horz:
                horz = False
            pts = list(pix)
            if horz:
                pts += [(i, sc - j, v) for i, j, v in pts]
            if vert:
                pts += [(sr - i, j, v) for i, j, v in pts]
            for i, j, v in pts:
                if 0 <= i < H and 0 <= j < W:
                    out[i][j] = v
        return out
    return fn


def fam(train):
    avoid = set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    avoid.add(x); avoid.add(y)
    bgs = {_bg(p["input"]) for p in train}
    avoid -= bgs
    seen = []
    for mode in ("both", "one"):
        fn = _make(avoid, mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("bracket_mirror_" + mode, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
