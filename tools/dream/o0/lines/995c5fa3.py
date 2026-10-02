"""Line family for card 995c5fa3 (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds a row (or column) of n monochrome shapes on a background. Each shape stands
for one colour (a lookup shape -> colour learned from the training pairs). The output is a square made
of n equal horizontal stripes, stripe i painted with the colour of shape i (shapes taken in their
order along the line they sit on), so the square's side is n times the stripe thickness (thickness 1
in 995c5fa3: three shapes -> a 3x3 square of three one-row stripes).

The family is generic over: the background colour, how shapes are cut out (connected components or
blocks between all-background separator lines), whether the shape key includes its colour, the stripe
orientation, the order of the shapes, and the square size (n x thickness, or the shapes' own side).
"""

CARD = "995c5fa3"
LINE = "each monochrome shape corresponds to one horizontal colored stripe together forming  a square of the same size."
READING = {
    "generator": "Each monochrome shape in the input is replaced by one horizontal stripe whose colour is "
                 "the colour that shape stands for (a shape -> colour lookup learned from the training "
                 "pairs); the stripes are stacked in the order of the shapes and together form a square "
                 "whose side is the number of shapes times the stripe thickness.",
    "stop": "One stripe per shape, each spanning the full square width; drawing stops after the last "
            "shape, when the stripes fill the square.",
    "params": "bg in {0, most frequent colour, colours of all-background separator lines} · "
              "cut in {component(8-conn. non-bg), band(blocks between all-bg rows/cols)} · "
              "key in {mask, colour+mask} · orient in {horizontal, vertical} · order in {forward, reverse} "
              "along the axis the shapes are spread on · size in {count (side = n*t, t induced), "
              "shape (side = shape side)} · lookup key -> colour induced from train "
              "(unseen key at test: nearest known mask by cell agreement)",
    "participants": "Shapes: the non-background objects (one colour each), found as connected components "
                    "or as blocks between background separator lines; each is keyed by its mask inside its "
                    "bounding box. Stripes: rows of the output square, read off the training outputs to "
                    "build the lookup.",
    "preconditions": "Every training input splits into n >= 1 monochrome shapes; every training output is "
                     "a square made of n equal uniform stripes; the induced shape -> colour lookup is "
                     "consistent across all training pairs.",
}


# ---------------------------------------------------------------- basics

def _dims(g):
    return len(g), (len(g[0]) if g else 0)


def _bg_candidates(g):
    H, W = _dims(g)
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    out = [0]
    if cnt:
        out.append(max(sorted(cnt), key=lambda c: cnt[c]))
    for r in range(H):
        if len(set(g[r])) == 1:
            out.append(g[r][0])
    for c in range(W):
        col = {g[r][c] for r in range(H)}
        if len(col) == 1:
            out.append(g[0][c])
    seen, res = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return res


def _components(g, bg):
    H, W = _dims(g)
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] == bg:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] != bg:
                            seen.add((yy, xx))
                            stack.append((yy, xx))
            comps.append(cells)
    return comps


def _bands(g, bg):
    """Blocks between all-background rows and all-background columns (cells of the block that are non-bg)."""
    H, W = _dims(g)
    rows_bg = [all(v == bg for v in g[r]) for r in range(H)]
    cols_bg = [all(g[r][c] == bg for r in range(H)) for c in range(W)]

    def runs(flags):
        out, start = [], None
        for i, f in enumerate(flags + [True]):
            if not f and start is None:
                start = i
            elif f and start is not None:
                out.append((start, i))
                start = None
        return out

    blocks = []
    for r0, r1 in runs(rows_bg):
        for c0, c1 in runs(cols_bg):
            cells = [(r, c) for r in range(r0, r1) for c in range(c0, c1) if g[r][c] != bg]
            if cells:
                blocks.append(cells)
    return blocks


def _shapes(g, bg, cut):
    """List of shapes: dict(colour, mask, box). None if some shape is not monochrome."""
    parts = _components(g, bg) if cut == "component" else _bands(g, bg)
    shapes = []
    for cells in parts:
        cols = {g[r][c] for r, c in cells}
        if len(cols) != 1:
            return None
        r0 = min(r for r, _ in cells)
        r1 = max(r for r, _ in cells)
        c0 = min(c for _, c in cells)
        c1 = max(c for _, c in cells)
        cs = set(cells)
        mask = tuple("".join("1" if (r, c) in cs else "0" for c in range(c0, c1 + 1))
                     for r in range(r0, r1 + 1))
        shapes.append({"colour": cols.pop(), "mask": mask, "box": (r0, c0, r1, c1)})
    return shapes


def _ordered(shapes, order):
    """Order shapes along the axis they are spread on (columns if they share a row band, rows if they
    share a column band, reading order otherwise)."""
    if not shapes:
        return shapes

    def overlap_all(lo, hi):
        return max(s["box"][lo] for s in shapes) <= min(s["box"][hi] for s in shapes)

    if overlap_all(0, 2):            # all share some row -> a horizontal line of shapes
        key = lambda s: (s["box"][1], s["box"][0])
    elif overlap_all(1, 3):          # all share some column -> a vertical line of shapes
        key = lambda s: (s["box"][0], s["box"][1])
    else:
        key = lambda s: (s["box"][0], s["box"][1])
    res = sorted(shapes, key=key)
    if order == "reverse":
        res.reverse()
    return res


def _key(s, keymode):
    return s["mask"] if keymode == "mask" else (s["colour"], s["mask"])


def _side(shapes, size, t):
    n = len(shapes)
    if size == "count":
        return n * t
    return max(max(s["box"][2] - s["box"][0], s["box"][3] - s["box"][1]) + 1 for s in shapes)


def _stripe_bounds(side, n):
    return [(i * side // n, (i + 1) * side // n) for i in range(n)]


def _read_stripes(out, n, orient):
    """Colours of n equal uniform stripes making up a square output, or None."""
    H, W = _dims(out)
    if H != W or n == 0 or H < n:
        return None
    cols = []
    for a, b in _stripe_bounds(H, n):
        if b <= a:
            return None
        if orient == "horizontal":
            vals = {out[r][c] for r in range(a, b) for c in range(W)}
        else:
            vals = {out[r][c] for r in range(H) for c in range(a, b)}
        if len(vals) != 1:
            return None
        cols.append(vals.pop())
    return cols


def _agree(m1, m2):
    """Cell agreement between two masks (aligned at the top-left; size mismatch penalised)."""
    h = max(len(m1), len(m2))
    w = max(len(m1[0]) if m1 else 0, len(m2[0]) if m2 else 0)
    score = 0
    for r in range(h):
        for c in range(w):
            a = m1[r][c] if r < len(m1) and c < len(m1[r]) else "x"
            b = m2[r][c] if r < len(m2) and c < len(m2[r]) else "y"
            score += 1 if a == b else 0
    return score


# ---------------------------------------------------------------- program

def _make(bg_mode, cut, keymode, orient, order, size, t, lookup):
    known = sorted(lookup.items(), key=lambda kv: repr(kv[0]))

    def colour_of(s):
        k = _key(s, keymode)
        if k in lookup:
            return lookup[k]
        best, bestsc = None, -1
        for kk, v in known:
            m = kk if keymode == "mask" else kk[1]
            sc = _agree(m, s["mask"]) + (0 if keymode == "mask" or kk[0] == s["colour"] else -1)
            if sc > bestsc:
                best, bestsc = v, sc
        return best

    def fn(g):
        bg = _pick_bg(g, bg_mode)
        shapes = _shapes(g, bg, cut)
        if not shapes:
            return [list(row) for row in g]
        shapes = _ordered(shapes, order)
        n = len(shapes)
        side = _side(shapes, size, t)
        if side < n:
            side = n
        out = [[0] * side for _ in range(side)]
        for (a, b), s in zip(_stripe_bounds(side, n), shapes):
            col = colour_of(s)
            for i in range(a, b):
                for j in range(side):
                    if orient == "horizontal":
                        out[i][j] = col
                    else:
                        out[j][i] = col
        return out
    return fn


def _pick_bg(g, bg_mode):
    if bg_mode == "zero":
        return 0
    cands = _bg_candidates(g)
    if bg_mode == "frequent":
        return cands[1] if len(cands) > 1 else cands[0]
    # separator: first colour filling a whole row/column that is not the most frequent one, else 0
    seps = cands[2:]
    return seps[0] if seps else 0


def fam(train):
    if not train:
        return
    found = []
    for bi, bg_mode in enumerate(("zero", "frequent", "separator")):
        for ci, cut in enumerate(("component", "band")):
            per_pair = []
            ok = True
            for p in train:
                sh = _shapes(p["input"], _pick_bg(p["input"], bg_mode), cut)
                if not sh:
                    ok = False
                    break
                per_pair.append(sh)
            if not ok:
                continue
            for oi, orient in enumerate(("horizontal", "vertical")):
                for ri, order in enumerate(("forward", "reverse")):
                    stripes = []
                    for p, sh in zip(train, per_pair):
                        st = _read_stripes(p["output"], len(sh), orient)
                        if st is None:
                            stripes = None
                            break
                        stripes.append(st)
                    if stripes is None:
                        continue
                    for si, size in enumerate(("count", "shape")):
                        t = None
                        if size == "count":
                            ts = {len(p["output"]) // len(sh) for p, sh in zip(train, per_pair)}
                            if len(ts) != 1 or any(len(p["output"]) % len(sh) for p, sh in zip(train, per_pair)):
                                continue
                            t = ts.pop()
                        for ki, keymode in enumerate(("mask", "colour+mask")):
                            lookup = {}
                            bad = False
                            for sh, st in zip(per_pair, stripes):
                                for s, col in zip(_ordered(sh, order), st):
                                    k = _key(s, keymode)
                                    if lookup.get(k, col) != col:
                                        bad = True
                                        break
                                    lookup[k] = col
                                if bad:
                                    break
                            if bad:
                                continue
                            fn = _make(bg_mode, cut, keymode, orient, order, size, t, dict(lookup))
                            try:
                                fits = all(fn(p["input"]) == p["output"] for p in train)
                            except Exception:
                                fits = False
                            if not fits:
                                continue
                            cost = 1 + bi + ci + 2 * oi + ri + si + ki
                            name = "shape_stripes(bg=%s,cut=%s,key=%s,orient=%s,order=%s,size=%s%s)" % (
                                bg_mode, cut, keymode, orient, order, size,
                                ",t=%d" % t if t is not None else "")
                            found.append((cost, len(found), name, fn))
    found.sort(key=lambda x: (x[0], x[1]))
    seen = set()
    for cost, _, name, fn in found:
        if name in seen:
            continue
        seen.add(name)
        yield name, cost, fn


FAMILIES = [fam]
