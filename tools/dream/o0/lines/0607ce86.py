"""Line family for card 0607ce86 (test-blind; written from the reviewer's line and train pairs only).

Reading of "denoise square lattice": the input holds a rectangular lattice (nr rows x nc columns, both >= 2)
of copies of one tile, the copies separated by background gutters, and noise pixels are sprinkled both over
the tiles and over the background. The output keeps the grid, finds the lattice and redraws it clean: every
copy becomes the cell-wise majority tile, and everything outside the copies becomes background.

Finding the lattice (per grid, no constants): a lattice is (row start, tile height, row period, row count) x
(col start, tile width, col period, col count) with period > size (a gutter of at least one line) and count >= 2.
Its cost is the number of cells the clean redraw would change. Row structures are first scored on full-width
rows and column structures on full-height columns (fast, prefix sums over per-offset vote tables); the best
few of each axis are then combined and scored exactly in 2D. Least cost wins; ties go to the smaller tile.
"""

CARD = "0607ce86"
LINE = "denoise square lattice"
READING = {
    "generator": "Find the rectangular lattice of repeated tiles hidden under the noise and redraw it clean: "
                 "every tile copy becomes the cell-wise majority vote of all copies, and every cell outside the "
                 "copies becomes background.",
    "stop": "One pass: each lattice cell is written once; the lattice has exactly the rows and columns of copies "
            "found in the input (no extension beyond them, nothing drawn in the gutters or margins).",
    "params": "bg in {colour induced from train outputs, most frequent input colour} · outside in {clear, keep} · "
              "lattice = (row start, tile height, row period, row count) x (col start, tile width, col period, "
              "col count), period > size, count >= 2, chosen per grid by least number of changed cells "
              "(ties: smaller tile)",
    "participants": "The tile copies: the cells of the chosen lattice, found by minimum-change search over all "
                    "lattices that fit the grid; the noise: every cell that disagrees with the majority tile or "
                    "lies outside the copies and is not background.",
    "preconditions": "Input and output have the same size in every train pair; each train input admits a lattice "
                     "of at least 2x2 copies separated by gutters; the clean redraw reproduces the train outputs.",
}

_K = 24  # how many best structures per axis go to the exact 2D scoring (search breadth, not a task constant)


def _mode(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _axis_candidates(g, bg):
    """Score (start, size, period, count) structures along the row axis of g on full-width rows.
    cost = N_nonbg + sum_{a<size} G[p][n][start+a]  with G = (copies - majority count - nonbg count) summed over columns."""
    H, W = len(g), len(g[0])
    nb = [sum(1 for v in row if v != bg) for row in g]
    N = sum(nb)
    out = []
    for p in range(2, H):
        nmax = (H - 1) // p + 1
        # Gt[n][s]: per-offset gain for rows s, s+p, ..., s+(n-1)p
        Gt = {}
        for s in range(H):
            cnts = [dict() for _ in range(W)]
            best = [0] * W
            tot = 0
            nbs = 0
            for i in range(nmax):
                r = s + i * p
                if r >= H:
                    break
                row = g[r]
                nbs += nb[r]
                for c in range(W):
                    d = cnts[c]
                    k = d.get(row[c], 0) + 1
                    d[row[c]] = k
                    if k > best[c]:
                        tot += k - best[c]
                        best[c] = k
                n = i + 1
                if n >= 2:
                    Gt.setdefault(n, [0] * H)[s] = n * W - tot - nbs
        for n, arr in Gt.items():
            pre = [0]
            for v in arr:
                pre.append(pre[-1] + v)
            for h in range(1, p):
                for r0 in range(0, H - (n - 1) * p - h + 1):
                    cost = N + pre[r0 + h] - pre[r0]
                    out.append((cost, h, -n, r0, p, (r0, h, p, n)))
    out.sort()
    return [t[-1] for t in out[:_K]]


def _transpose(g):
    return [list(col) for col in zip(*g)]


def _score2d(g, bg, N, rs, cs, colfreq):
    r0, h, pr, nr = rs
    c0, w, pc, nc = cs
    cost = N
    tile = [[bg] * w for _ in range(h)]
    for a in range(h):
        for b in range(w):
            d = {}
            nbc = 0
            for i in range(nr):
                row = g[r0 + i * pr + a]
                for j in range(nc):
                    v = row[c0 + j * pc + b]
                    d[v] = d.get(v, 0) + 1
                    if v != bg:
                        nbc += 1
            m = max(d.values())
            col = max((k for k in d if d[k] == m), key=lambda k: (colfreq.get(k, 0), -k))
            tile[a][b] = col
            cost += nr * nc - m - nbc
    return cost, tile


def _find_lattice(g, bg):
    H, W = len(g), len(g[0])
    if H < 5 or W < 5:
        return None
    rows = _axis_candidates(g, bg)
    cols = _axis_candidates(_transpose(g), bg)
    if not rows or not cols:
        return None
    N = sum(1 for row in g for v in row if v != bg)
    colfreq = {}
    for row in g:
        for v in row:
            colfreq[v] = colfreq.get(v, 0) + 1
    best = None
    for rs in rows:
        for cs in cols:
            cost, tile = _score2d(g, bg, N, rs, cs, colfreq)
            key = (cost, rs[1] * cs[1], -(rs[3] * cs[3]), rs[0], cs[0], rs[2], cs[2])
            if best is None or key < best[0]:
                best = (key, rs, cs, tile)
    return best


def _make(bg_mode, bg_const, outside):
    def fn(grid):
        g = [list(r) for r in grid]
        bg = bg_const if bg_mode == "const" else _mode(g)
        found = _find_lattice(g, bg)
        if found is None:
            raise ValueError("no lattice")
        _, (r0, h, pr, nr), (c0, w, pc, nc), tile = found
        out = [[bg] * len(g[0]) for _ in g] if outside == "clear" else [row[:] for row in g]
        for i in range(nr):
            for j in range(nc):
                for a in range(h):
                    for b in range(w):
                        out[r0 + i * pr + a][c0 + j * pc + b] = tile[a][b]
        return out
    return fn


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if not gi or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    outs_bg = {_mode(p["output"]) for p in train}
    bg_modes = ([("const", min(outs_bg))] if len(outs_bg) == 1 else []) + [("mode", None)]
    progs = []
    for bi, (bm, bc) in enumerate(bg_modes):
        for oi, outside in enumerate(("clear", "keep")):
            name = "denoise_lattice[bg=%s,outside=%s]" % (bm if bc is None else "%s:%d" % (bm, bc), outside)
            progs.append((name, 1 + bi + oi, _make(bm, bc, outside)))
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
